const questionInput = document.getElementById("question");
const askButton = document.getElementById("ask-button");
const loading = document.getElementById("loading");
const errorBox = document.getElementById("error");
const answerPanel = document.getElementById("answer-panel");
const answerContent = document.getElementById("answer-content");
const sourcesList = document.getElementById("sources-list");
const importButton = document.getElementById("import-button");
const urlInput = document.getElementById("url-input");
const importMessage = document.getElementById("import-message");

document.querySelectorAll(".suggestion").forEach((button) => {
  button.addEventListener("click", () => {
    questionInput.value = button.dataset.question || "";
    questionInput.focus();
  });
});

function showError(message) {
  errorBox.textContent = message;
  errorBox.classList.remove("hidden");
}

function setBusy(busy) {
  askButton.disabled = busy;
  loading.classList.toggle("hidden", !busy);
}
async function renderFormattedAnswer(element, answer) {
  const markdown = answer || "";

  if (
    typeof marked === "undefined" ||
    typeof DOMPurify === "undefined"
  ) {
    element.textContent = markdown;
    return;
  }

  // Convert Markdown into safe HTML.
  const html = marked.parse(markdown);
  element.innerHTML = DOMPurify.sanitize(html);

  // Render LaTeX equations after inserting the HTML.
  if (window.MathJax) {
    await MathJax.startup.promise;
    MathJax.typesetClear([element]);
    await MathJax.typesetPromise([element]);
  }
}

askButton.addEventListener("click", async () => {
  const question = questionInput.value.trim();
  errorBox.classList.add("hidden");
  if (!question) {
    showError("Please enter a question first.");
    questionInput.focus();
    return;
  }
  setBusy(true);
  answerPanel.classList.add("hidden");
  try {
    const response = await fetch("/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question })
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Request failed.");
    await renderFormattedAnswer(answerContent, data.answer);
    sourcesList.replaceChildren();
    (data.sources || []).forEach((source) => {
      const card = document.createElement("article");
      card.className = "source-card";
      const title = document.createElement("div");
      title.className = "source-title";
      const label = document.createElement("span");
      label.textContent = `${source.source} · chunk ${source.chunk_number}`;
      const score = document.createElement("span");
      score.className = "score";
      score.textContent = `Similarity ${source.score}`;
      title.append(label, score);
      const text = document.createElement("p");
      text.className = "source-text";
      text.textContent = source.text;
      card.append(title, text);
      sourcesList.append(card);
    });
    answerPanel.classList.remove("hidden");
    answerPanel.scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (error) {
    showError(error.message || "Something went wrong. Check the terminal for details.");
  } finally {
    setBusy(false);
  }
});

questionInput.addEventListener("keydown", (event) => {
  if ((event.ctrlKey || event.metaKey) && event.key === "Enter") askButton.click();
});

importButton.addEventListener("click", async () => {
  const url = urlInput.value.trim();
  importMessage.textContent = "";
  errorBox.classList.add("hidden");
  if (!url) {
    importMessage.style.color = "#a52b2b";
    importMessage.textContent = "Enter a public URL first.";
    return;
  }
  importButton.disabled = true;
  importMessage.style.color = "#6e7b8e";
  importMessage.textContent = "Fetching and processing material…";
  try {
    const response = await fetch("/api/import-url", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url })
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Import failed.");
    importMessage.style.color = "#287a5c";
    importMessage.textContent = `${data.message} Searchable chunks: ${data.chunk_count}.`;
    document.getElementById("document-count").textContent = data.document_count;
    document.getElementById("chunk-count").textContent = data.chunk_count;
    urlInput.value = "";
  } catch (error) {
    importMessage.style.color = "#a52b2b";
    importMessage.textContent = error.message || "Could not import this URL.";
  } finally {
    importButton.disabled = false;
  }
});
