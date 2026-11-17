const byId = (id) => document.getElementById(id);
const form = byId("analysis-form");
const fileInput = byId("resume-file");
const dropzone = byId("dropzone");
const analysisButton = byId("analyze-button");
const loadingRow = byId("loading-row");
const results = byId("results");
let analysis = null;
let toastTimer;
let useOptimizedForExport = false;
let pdfPreviewUrl = null;

function toast(message, error = false) {
  const element = byId("toast");
  element.textContent = message;
  element.classList.toggle("error", error);
  element.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => element.classList.remove("show"), 3400);
}

function setFile(file) {
  if (!file) return;
  const extension = file.name.split(".").pop().toLowerCase();
  if (!(["pdf", "docx"].includes(extension))) {
    fileInput.value = "";
    toast("Choose a PDF or DOCX file.", true);
    return;
  }
  if (file.size > 8 * 1024 * 1024) {
    fileInput.value = "";
    toast("The maximum file size is 8 MB.", true);
    return;
  }
  byId("file-title").textContent = file.name;
  byId("file-description").textContent = `${(file.size / 1024).toFixed(0)} KB · ready to analyze`;
  dropzone.classList.add("has-file");
}

fileInput.addEventListener("change", () => setFile(fileInput.files[0]));
for (const eventName of ["dragenter", "dragover"]) {
  dropzone.addEventListener(eventName, (event) => { event.preventDefault(); dropzone.classList.add("drag-over"); });
}
for (const eventName of ["dragleave", "drop"]) {
  dropzone.addEventListener(eventName, (event) => { event.preventDefault(); dropzone.classList.remove("drag-over"); });
}
dropzone.addEventListener("drop", (event) => {
  const file = event.dataTransfer.files[0];
  if (!file) return;
  const transfer = new DataTransfer();
  transfer.items.add(file);
  fileInput.files = transfer.files;
  setFile(file);
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const file = fileInput.files[0];
  const jobDescription = byId("job-description").value.trim();
  if (!file) return toast("Choose your resume document first.", true);
  if (jobDescription.length < 20) return toast("Add a job description with at least 20 characters.", true);
  const payload = new FormData();
  payload.append("file", file);
  payload.append("job_description", jobDescription);
  payload.append("target_role", byId("target-role").value);
  analysisButton.disabled = true;
  loadingRow.hidden = false;
  try {
    const response = await fetch("/api/analyze", { method: "POST", body: payload });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Analysis could not be completed.");
    analysis = data;
    renderAnalysis(data);
    results.hidden = false;
    results.scrollIntoView({ behavior: "smooth", block: "start" });
    toast("Analysis complete. Review the evidence and suggested edits below.");
  } catch (error) {
    toast(error.message || "The service is unavailable. Try again shortly.", true);
  } finally {
    analysisButton.disabled = false;
    loadingRow.hidden = true;
  }
});

function renderAnalysis(data) {
  const ats = data.ats;
  const match = ats.matching;
  byId("result-title").textContent = data.target_role ? `Alignment for ${data.target_role}` : "Your alignment summary";
  byId("overall-score").textContent = ats.overall_score;
  byId("score-ring").style.setProperty("--score", `${ats.overall_score * 3.6}deg`);
  byId("score-label").textContent = ats.overall_score >= 75 ? "Strong role alignment" : ats.overall_score >= 48 ? "Some signals align" : "Room to strengthen alignment";
  byId("keyword-score").textContent = `${ats.keyword_coverage}%`;
  byId("score-method").textContent = ats.score_method;
  byId("matched-count").textContent = `${match.matched_keywords.length} matched`;
  renderChips("matched-keywords", match.matched_keywords, "", "No job-description terms were identified.");
  renderChips("missing-keywords", match.missing_keywords, "missing", "No missing terms identified.");
  const recommendations = byId("recommendation-list");
  recommendations.replaceChildren();
  for (const recommendation of ats.recommendations) {
    const item = document.createElement("li");
    item.textContent = recommendation;
    recommendations.append(item);
  }
  byId("original-text").value = data.resume_text;
  byId("optimized-text").value = data.compression.optimized_text;
  renderDuplicateSuggestions([]);
  renderResearch(data.research);
  byId("optimization-results").hidden = true;
  useOptimizedForExport = false;
  byId("review-status").textContent = "Proposed changes ready for review";
}

function renderChips(id, items, className, emptyText) {
  const container = byId(id);
  container.replaceChildren();
  if (!items.length) {
    const empty = document.createElement("span");
    empty.className = "empty-chip";
    empty.textContent = emptyText;
    container.append(empty);
    return;
  }
  for (const value of items) {
    const chip = document.createElement("span");
    chip.className = `chip ${className}`.trim();
    chip.textContent = value;
    container.append(chip);
  }
}

function renderResearch(research) {
  const metrics = research.metrics;
  byId("research-compression").textContent = `${metrics.compression_percent}%`;
  byId("research-keywords").textContent = `${metrics.keyword_coverage_percent}%`;
  byId("research-retention").textContent = `${metrics.information_retention_percent}%`;
  byId("research-status").textContent = "Calculated from this resume and its optimized text.";
}

function renderDuplicateSuggestions(suggestions) {
  const panel = byId("duplicate-review");
  const list = byId("duplicate-list");
  list.replaceChildren();
  panel.hidden = suggestions.length === 0;
  for (const suggestion of suggestions) {
    const item = document.createElement("li");
    const message = document.createElement("p");
    const examples = document.createElement("small");
    message.textContent = suggestion.message;
    examples.textContent = `${suggestion.related_text} / ${suggestion.text}`;
    item.append(message, examples);
    list.append(item);
  }
}

byId("optimize-button").addEventListener("click", async () => {
  if (!analysis) return toast("Analyze a resume before optimizing it.", true);
  const button = byId("optimize-button");
  button.disabled = true;
  try {
    const response = await fetch("/api/optimize", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ resume_text: analysis.resume_text, job_description: byId("job-description").value.trim() }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Optimization failed.");
    byId("original-count").textContent = data.original_word_count;
    byId("optimized-count").textContent = data.optimized_word_count;
    byId("optimized-text").value = data.optimized_text;
    renderDuplicateSuggestions(data.duplicate_suggestions || []);
    useOptimizedForExport = true;
    byId("optimization-results").hidden = false;
    byId("review-status").textContent = "Proposed changes ready for review";
    byId("optimization-results").scrollIntoView({ behavior: "smooth", block: "start" });
    toast("Optimization is ready. Review the wording before using or exporting it.");
  } catch (error) {
    toast(error.message || "Optimization failed.", true);
  } finally {
    button.disabled = false;
  }
});

byId("accept-edits").addEventListener("click", () => {
  useOptimizedForExport = true;
  byId("review-status").textContent = "Optimized version selected for export";
  toast("Optimized version selected. You can still edit it before export.");
});
byId("reject-edits").addEventListener("click", () => {
  useOptimizedForExport = false;
  byId("optimized-text").value = analysis?.resume_text || "";
  byId("review-status").textContent = "Original version selected for export";
  toast("Original version selected for export.");
});

function selectedResumeText() {
  return useOptimizedForExport ? byId("optimized-text").value : analysis?.resume_text || "";
}

async function requestPdf() {
  const response = await fetch("/api/export/pdf", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text: selectedResumeText() }),
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Could not create the PDF.");
  }
  return response.blob();
}

byId("preview-pdf").addEventListener("click", async () => {
  if (!selectedResumeText()) return toast("Analyze and optimize a resume before previewing it.", true);
  try {
    const pdf = await requestPdf();
    if (pdfPreviewUrl) URL.revokeObjectURL(pdfPreviewUrl);
    pdfPreviewUrl = URL.createObjectURL(pdf);
    byId("pdf-preview-frame").src = pdfPreviewUrl;
    byId("pdf-preview-dialog").showModal();
  } catch (error) {
    toast(error.message || "PDF preview failed.", true);
  }
});

byId("close-pdf-preview").addEventListener("click", () => byId("pdf-preview-dialog").close());
byId("pdf-preview-dialog").addEventListener("close", () => {
  byId("pdf-preview-frame").src = "about:blank";
  if (pdfPreviewUrl) URL.revokeObjectURL(pdfPreviewUrl);
  pdfPreviewUrl = null;
});

async function downloadPdf() {
  const selected = selectedResumeText();
  if (!selected) return toast("There is no resume content to export yet.", true);
  try {
    const blob = await requestPdf();
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "resumeiq-optimized.pdf";
    link.click();
    URL.revokeObjectURL(url);
    toast("PDF download started.");
  } catch (error) {
    toast(error.message || "Export failed.", true);
  }
}
byId("download-pdf").addEventListener("click", downloadPdf);
byId("new-analysis").addEventListener("click", () => {
  form.reset();
  analysis = null;
  fileInput.value = "";
  byId("file-title").textContent = "Drop your resume here";
  byId("file-description").innerHTML = "or <u>browse files</u>";
  useOptimizedForExport = false;
  dropzone.classList.remove("has-file");
  results.hidden = true;
  if (byId("pdf-preview-dialog").open) byId("pdf-preview-dialog").close();
  byId("research-compression").textContent = "Not calculated";
  byId("research-keywords").textContent = "Not calculated";
  byId("research-retention").textContent = "Not calculated";
  byId("research-status").textContent = "Analyze a resume to calculate its metrics. No sample values are shown.";
  window.scrollTo({ top: byId("workspace").offsetTop - 80, behavior: "smooth" });
});

fetch("/api/health").catch(() => toast("Can’t reach the ResumeIQ service right now.", true));