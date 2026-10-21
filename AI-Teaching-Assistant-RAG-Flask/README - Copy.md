# AI Teaching Assistant for Probability Models and Applications using RAG

This version uses a separate HTML/CSS/JavaScript frontend and a Python Flask backend. The backend retrieves relevant course-note passages using sentence embeddings and cosine similarity, then asks Gemini to generate a response grounded in those passages.

## Folder structure

```text
AI-Teaching-Assistant-RAG-Flask/
├── app.py
├── requirements.txt
├── README.md
├── .env.example
├── setup_windows.bat
├── run_app.bat
├── templates/
│   └── index.html
├── static/
│   ├── style.css
│   └── script.js
└── documents/
    └── probability_notes.txt
```

## Requirements

- Windows 10/11
- Python 3.12 recommended. Python 3.14 may not yet be supported by every machine-learning dependency.
- Internet access for package/model downloads and Gemini API requests
- A Gemini API key

## Setup on Windows

1. Extract the ZIP file.
2. Open the **inner project folder** in VS Code—the folder containing `app.py`, `setup_windows.bat`, and `requirements.txt`.
3. Copy `.env.example` and rename the copy to `.env`.
4. Edit `.env` and add your own key:
   ```dotenv
   GEMINI_API_KEY=your_actual_key_here
   GEMINI_MODEL=gemini-2.5-flash
   ```
   Obtain a key from https://aistudio.google.com/apikey. Never share your key or upload `.env` to GitHub.
5. If Python 3.12 is installed, run `setup_windows.bat`. If only Python 3.14 is installed, you may try:
   ```powershell
   py -3 -m venv .venv
   .\.venv\Scripts\python.exe -m pip install --upgrade pip
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   ```
   Some ML dependencies may not support Python 3.14 yet. If installation fails, install Python 3.12 and recreate the environment.
6. Start the app:
   ```powershell
   .\.venv\Scripts\python.exe app.py
   ```
   Or double-click `run_app.bat`.
7. Open http://127.0.0.1:5000 in your browser.

## Adding course material

Place `.txt`, `.md`, or text-based `.pdf` files in `documents/`. The app reads local files when a request is processed. You can also import a public webpage, PDF, or text URL from the interface. URL imports are held in server memory and are lost when the Python server restarts.

Scanned PDFs require OCR before text can be extracted.

## Troubleshooting

- **Missing Gemini API key:** Ensure `.env` is next to `app.py` and contains `GEMINI_API_KEY=...`.
- **Model not available:** Set `GEMINI_MODEL` to a model available to your Gemini API key.
- **Package install fails:** Use Python 3.12, confirm internet access, and inspect the pip error.
- **First question is slow:** The sentence-transformer model downloads on first use.
- **Port is occupied:** Change `port=5000` at the bottom of `app.py` to an unused port, then restart.

## RAG workflow

1. Read local notes and URL-imported text.
2. Split text into 800-character chunks with 150-character overlap.
3. Embed chunks using `all-MiniLM-L6-v2`.
4. Retrieve the top three passages by cosine similarity.
5. Send those passages and the question to Gemini.
6. Return the answer and source passages to the browser.

## Security notes

This is a local educational demo, not a production-hardened web service. Import only URLs you trust. Do not expose the development server to the public internet. Do not commit or share `.env`. Verify generated answers against official course notes.
