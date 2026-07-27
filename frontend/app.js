const API_BASE = ""; // same-origin: frontend is served by the FastAPI app itself
const POLL_INTERVAL_MS = 2500;

const form = document.getElementById("analyze-form");
const urlInput = document.getElementById("url-input");
const analyzeButton = document.getElementById("analyze-button");
const errorBanner = document.getElementById("error-banner");
const progressSection = document.getElementById("progress-section");
const stageList = document.getElementById("stage-list");
const resultsSection = document.getElementById("results-section");
const scoreValue = document.getElementById("score-value");
const readinessLevel = document.getElementById("readiness-level");
const issuesHigh = document.getElementById("issues-high");
const issuesMedium = document.getElementById("issues-medium");
const issuesLow = document.getElementById("issues-low");
const recommendationsCount = document.getElementById("recommendations-count");
const downloadButton = document.getElementById("download-button");
const workflowWarning = document.getElementById("workflow-warning");

let pollTimer = null;

function showError(message) {
  errorBanner.textContent = message;
  errorBanner.hidden = false;
}

function hideError() {
  errorBanner.hidden = true;
  errorBanner.textContent = "";
}

function setBusy(busy) {
  analyzeButton.disabled = busy;
  analyzeButton.textContent = busy ? "Analyzing..." : "Analyze Website";
}

function renderStages(stages) {
  stageList.innerHTML = "";
  for (const stage of stages) {
    const item = document.createElement("li");
    item.className = `stage--${stage.status}`;

    const icon = document.createElement("span");
    icon.className = `stage-icon stage-icon--${stage.status}`;

    const label = document.createElement("span");
    label.textContent = stage.label;

    item.appendChild(icon);
    item.appendChild(label);
    stageList.appendChild(item);
  }
}

function readinessLabel(score) {
  if (score >= 80) return "Excellent";
  if (score >= 60) return "Good";
  if (score >= 40) return "Fair";
  if (score >= 20) return "Poor";
  return "Critical";
}

function renderResults(status) {
  resultsSection.hidden = false;

  const score = status.score ?? 0;
  scoreValue.textContent = `${score.toFixed(1)}`;
  readinessLevel.textContent = readinessLabel(score);

  issuesHigh.textContent = status.high;
  issuesMedium.textContent = status.medium;
  issuesLow.textContent = status.low;
  recommendationsCount.textContent = status.recommendations_count;

  if (status.report_url) {
    downloadButton.href = `${API_BASE}${status.report_url}`;
    downloadButton.hidden = false;
  } else {
    downloadButton.hidden = true;
  }

  if (status.error || (status.workflow_errors && status.workflow_errors.length > 0)) {
    const parts = [];
    if (status.error) parts.push(status.error);
    if (status.workflow_errors && status.workflow_errors.length > 0) {
      parts.push(`${status.workflow_errors.length} non-fatal issue(s) were recorded during analysis.`);
    }
    workflowWarning.textContent = parts.join(" ");
    workflowWarning.hidden = false;
  } else {
    workflowWarning.hidden = true;
  }
}

async function pollStatus(jobId) {
  let response;
  try {
    response = await fetch(`${API_BASE}/api/analyze/${jobId}/status`);
  } catch (err) {
    showError("Lost connection to the ARAS server. Please try again.");
    setBusy(false);
    return;
  }

  if (!response.ok) {
    showError("Unable to retrieve analysis status.");
    setBusy(false);
    return;
  }

  const status = await response.json();
  renderStages(status.stages);

  if (status.status === "running") {
    pollTimer = window.setTimeout(() => pollStatus(jobId), POLL_INTERVAL_MS);
    return;
  }

  setBusy(false);

  if (status.status === "failed") {
    showError(status.error || "The analysis failed unexpectedly.");
    return;
  }

  renderResults(status);
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  hideError();
  resultsSection.hidden = true;
  workflowWarning.hidden = true;

  if (pollTimer) {
    window.clearTimeout(pollTimer);
    pollTimer = null;
  }

  const url = urlInput.value.trim();
  setBusy(true);
  progressSection.hidden = false;
  renderStages([
    { key: "evidence", label: "Evidence collection", status: "running" },
    { key: "analysis", label: "Website analysis", status: "pending" },
    { key: "security", label: "Security evaluation", status: "pending" },
    { key: "recommendation", label: "Recommendation generation", status: "pending" },
    { key: "report", label: "Report generation", status: "pending" },
  ]);

  let response;
  try {
    response = await fetch(`${API_BASE}/api/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url }),
    });
  } catch (err) {
    showError("Unable to reach the ARAS server. Please try again.");
    setBusy(false);
    progressSection.hidden = true;
    return;
  }

  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    showError(body.detail || "Invalid request.");
    setBusy(false);
    progressSection.hidden = true;
    return;
  }

  const { job_id: jobId } = await response.json();
  pollStatus(jobId);
});
