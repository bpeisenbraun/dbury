import {
  clearResumeStrip,
  formatNumber,
  getResumeStripId,
  loadCatalog,
  viewerUrl,
} from "./catalog.js";

const yearGrid = document.querySelector("#year-grid");
const resumePanel = document.querySelector("#resume-panel");
const resumeLink = document.querySelector("#resume-link");
const resumeDetail = document.querySelector("#resume-detail");
const archiveSummary = document.querySelector("#archive-summary");
const errorPanel = document.querySelector("#page-error");

function renderYears(catalog) {
  const fragment = document.createDocumentFragment();
  for (const year of catalog.years) {
    const link = document.createElement("a");
    link.className = "year-card";
    link.href = viewerUrl(year.firstStripId);

    const label = document.createElement("strong");
    label.textContent = year.year;
    const total = document.createElement("span");
    total.textContent = `${formatNumber(year.count)} strips`;
    const breakdown = document.createElement("small");
    breakdown.textContent = `${formatNumber(year.dailyCount)} daily · ${formatNumber(year.sundayCount)} Sunday`;

    link.append(label, total, breakdown);
    fragment.append(link);
  }
  yearGrid.replaceChildren(fragment);
}

function renderResume(catalog, stripById) {
  const resumeId = getResumeStripId();
  const strip = resumeId ? stripById.get(resumeId) : null;
  if (!strip) {
    if (resumeId) clearResumeStrip();
    resumePanel.hidden = true;
    return;
  }

  resumeLink.href = viewerUrl(strip.id);
  resumeDetail.textContent = `${strip.type === "sunday" ? "Sunday" : "Daily"} · ${strip.date}`;
  resumePanel.hidden = false;
}

async function initialize() {
  try {
    const catalog = await loadCatalog();
    const stripById = new Map(catalog.strips.map((strip) => [strip.id, strip]));
    archiveSummary.textContent = `${formatNumber(catalog.archive.totalCount)} strips · ${catalog.archive.firstDate.slice(0, 4)}–${catalog.archive.lastDate.slice(0, 4)}`;
    renderYears(catalog);
    renderResume(catalog, stripById);
  } catch (error) {
    yearGrid.hidden = true;
    errorPanel.textContent = error instanceof Error ? error.message : "The archive could not be loaded.";
    errorPanel.hidden = false;
  }
}

initialize();
