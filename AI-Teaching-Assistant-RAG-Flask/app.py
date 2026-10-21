import os
import re
import ipaddress
from io import BytesIO
from urllib.parse import urlparse, urljoin

from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from google import genai
from google.genai import types

load_dotenv()
app = Flask(__name__)

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
CHUNK_SIZE = 800
CHUNK_OVERLAP = 150
TOP_K = 3
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
MAX_UPLOAD_BYTES = 12 * 1024 * 1024

# Store URL imports in memory for the current server process.
url_documents = {}


def split_text(text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    text = re.sub(r"\s+", " ", text or "").strip()
    if not text:
        return []
    result = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk = text[start:end].strip()
        if chunk:
            result.append(chunk)
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return result


def extract_pdf(content):
    reader = PdfReader(BytesIO(content))
    return "\n".join(page.extract_text() or "" for page in reader.pages).strip()


def validate_public_url(url):
    parsed = urlparse((url or "").strip())
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValueError("Enter a complete public http:// or https:// URL.")
    host = parsed.hostname.lower()
    if host == "localhost" or host.endswith(".local"):
        raise ValueError("Local URLs are not allowed.")
    try:
        ip = ipaddress.ip_address(host)
        if not ip.is_global:
            raise ValueError("Private or non-public IP addresses are not allowed.")
    except ValueError as exc:
        if "not allowed" in str(exc):
            raise
        # Domain name, not an IP address.
    return url.strip()


def fetch_url_text(url):
    current = validate_public_url(url)
    headers = {"User-Agent": "PMA-AI-Teaching-Assistant/1.0"}
    with requests.Session() as session:
        for _ in range(4):
            response = session.get(current, headers=headers, timeout=(8, 25), allow_redirects=False)
            if response.is_redirect or response.is_permanent_redirect:
                location = response.headers.get("Location")
                response.close()
                if not location:
                    raise ValueError("Redirect did not include a destination.")
                current = validate_public_url(urljoin(current, location))
                continue
            response.raise_for_status()
            content_type = response.headers.get("Content-Type", "").lower()
            content = response.content
            response.close()
            if len(content) > MAX_UPLOAD_BYTES:
                raise ValueError("The page or file exceeds the 12 MB limit.")
            if "application/pdf" in content_type or current.lower().split("?")[0].endswith(".pdf"):
                text = extract_pdf(content)
            elif "text/plain" in content_type or current.lower().split("?")[0].endswith(".txt"):
                text = content.decode("utf-8", errors="replace")
            else:
                soup = BeautifulSoup(content, "html.parser")
                for element in soup(["script", "style", "nav", "footer", "header", "noscript"]):
                    element.decompose()
                text = soup.get_text(separator=" ", strip=True)
            if not text.strip():
                raise ValueError("No readable text found. The page may be scanned or image-only.")
            return text, current
    raise ValueError("Too many redirects.")


def read_local_documents():
    folder = os.path.join(os.path.dirname(__file__), "documents")
    result = []
    if not os.path.isdir(folder):
        return result
    for name in sorted(os.listdir(folder)):
        path = os.path.join(folder, name)
        if not os.path.isfile(path):
            continue
        extension = os.path.splitext(name)[1].lower()
        try:
            if extension in (".txt", ".md"):
                with open(path, "r", encoding="utf-8") as file:
                    text = file.read()
            elif extension == ".pdf":
                with open(path, "rb") as file:
                    text = extract_pdf(file.read())
            else:
                continue
            if text.strip():
                result.append({"name": name, "text": text})
        except Exception:
            app.logger.exception("Could not read document %s", name)
    return result


def build_index():
    documents = read_local_documents()
    documents.extend({"name": name, "text": text} for name, text in url_documents.items())
    chunks = []
    for document in documents:
        for index, chunk in enumerate(split_text(document["text"])):
            chunks.append({
                "source": document["name"],
                "chunk_number": index + 1,
                "text": chunk,
            })
    return documents, chunks


_model = None


def get_embedding_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBEDDING_MODEL)
    return _model


def retrieve(question, chunks, model):
    if not chunks:
        return []
    chunk_vectors = model.encode(
        [item["text"] for item in chunks],
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    question_vector = model.encode([question], convert_to_numpy=True, normalize_embeddings=True)
    scores = cosine_similarity(question_vector, chunk_vectors)[0]
    indices = scores.argsort()[::-1][:min(TOP_K, len(chunks))]
    return [{**chunks[i], "score": float(scores[i])} for i in indices]


def generate_answer(question, retrieved, api_key):
    client = genai.Client(api_key=api_key)
    context = "\n\n".join(
        f"[Source: {item['source']}, chunk {item['chunk_number']}]\n{item['text']}"
        for item in retrieved
    )
    prompt = f"""You are an AI Teaching Assistant for Probability Models and Applications.
Explain concepts simply but accurately for an MTech student. Use the supplied context as the main source.
If the context is insufficient, say so and then give a careful general explanation where possible.
Use LaTeX for equations when helpful and include a worked example when appropriate.
Do not invent citations.

CONTEXT:
{context}

STUDENT QUESTION:
{question}
"""
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0.2, max_output_tokens=1800),
    )
    return response.text or "The model returned an empty answer."


@app.get("/")
def index():
    documents, chunks = build_index()
    return render_template(
        "index.html",
        document_count=len(documents),
        chunk_count=len(chunks),
        gemini_model=GEMINI_MODEL,
    )


@app.post("/api/ask")
def ask():
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return jsonify({"error": "Gemini API key is missing. Add GEMINI_API_KEY to your .env file."}), 400
    data = request.get_json(silent=True) or {}
    question = (data.get("question") or "").strip()
    if not question:
        return jsonify({"error": "Please enter a question."}), 400
    try:
        documents, chunks = build_index()
        if not chunks:
            return jsonify({"error": "No course material found. Add files to the documents folder or import a URL."}), 400
        model = get_embedding_model()
        retrieved = retrieve(question, chunks, model)
        answer = generate_answer(question, retrieved, api_key)
        sources = [{
            "source": item["source"],
            "chunk_number": item["chunk_number"],
            "score": round(item["score"], 3),
            "text": item["text"],
        } for item in retrieved]
        return jsonify({"answer": answer, "sources": sources})
    except Exception as exc:
        app.logger.exception("Question processing failed")
        return jsonify({"error": f"Could not generate an answer: {str(exc)}"}), 500


@app.post("/api/import-url")
def import_url():
    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()
    if not url:
        return jsonify({"error": "Enter a URL first."}), 400
    try:
        text, final_url = fetch_url_text(url)
        url_documents[final_url] = text
        documents, chunks = build_index()
        return jsonify({
            "message": "Material imported successfully.",
            "url": final_url,
            "document_count": len(documents),
            "chunk_count": len(chunks),
        })
    except Exception as exc:
        return jsonify({"error": f"Could not import URL: {str(exc)}"}), 400


@app.get("/api/status")
def status():
    documents, chunks = build_index()
    return jsonify({
        "document_count": len(documents),
        "chunk_count": len(chunks),
        "sources": [doc["name"] for doc in documents],
    })


if __name__ == "__main__":
    # Local development server. Do not expose the debug server to the public internet.
    app.run(host="127.0.0.1", port=5000, debug=False)
