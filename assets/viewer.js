import {
  clearResumeStrip,
  formatDate,
  getResumeStripId,
  loadCatalog,
  saveResumeStrip,
  viewerUrl,
} from "./catalog.js";

const stripImage = document.querySelector("#strip-image");
const stripDate = document.querySelector("#strip-date");
const stripType = document.querySelector("#strip-type");
const stripDescription = document.querySelector("#strip-description");
const previousButton = document.querySelector("#previous-strip");
const nextButton = document.querySelector("#next-strip");
const progress = document.querySelector("#reader-progress");
const notice = document.querySelector("#reader-notice");
const loading = document.querySelector("#reader-loading");
const reader = document.querySelector("#reader");
const errorPanel = document.querySelector("#page-error");

let catalog;
let stripById;
let currentIndex = -1;

function setNavigationState(button, targetIndex) {
  const isAvailable = targetIndex >= 0 && targetIndex < catalog.strips.length;
  button.disabled = !isAvailable;
  button.dataset.targetIndex = isAvailable ? String(targetIndex) : "";
}

function preload(index) {
  if (index < 0 || index >= catalog.strips.length) return;
  const image = new Image();
  image.src = catalog.strips[index].path;
}

function showStrip(index, updateAddress = true) {
  if (index < 0 || index >= catalog.strips.length) return;

  currentIndex = index;
  const strip = catalog.strips[index];
  const humanDate = formatDate(strip.date);

  stripDate.textContent = humanDate;
  stripType.textContent = strip.type === "sunday" ? "Sunday" : "Daily";
  stripType.className = `strip-type strip-type--${strip.type}`;
  stripDescription.hidden = !strip.descriptionHtml;
  stripDescription.innerHTML = strip.descriptionHtml || "";
  progress.textContent = `${(index + 1).toLocaleString()} of ${catalog.strips.length.toLocaleString()}`;
  stripImage.alt = `${strip.type === "sunday" ? "Sunday" : "Daily"} comic strip for ${humanDate}`;
  stripImage.classList.add("is-loading");
  stripImage.src = strip.path;

  setNavigationState(previousButton, index - 1);
  setNavigationState(nextButton, index + 1);

  if (updateAddress) {
    history.replaceState({ stripId: strip.id }, "", viewerUrl(strip.id));
  }
  document.title = `${humanDate} — Doonesbury Archive`;

  stripImage.onload = () => {
    if (catalog.strips[currentIndex]?.id !== strip.id) return;
    stripImage.classList.remove("is-loading");
    saveResumeStrip(strip.id);
  };
  stripImage.onerror = () => {
    if (catalog.strips[currentIndex]?.id !== strip.id) return;
    stripImage.classList.remove("is-loading");
    notice.textContent = "This strip image could not be loaded.";
    notice.hidden = false;
  };

  preload(index - 1);
  preload(index + 1);
}

function navigateFromButton(event) {
  const targetIndex = Number(event.currentTarget.dataset.targetIndex);
  if (Number.isInteger(targetIndex)) {
    notice.hidden = true;
    showStrip(targetIndex);
  }
}

function requestedStripId() {
  return new URLSearchParams(window.location.search).get("strip");
}

function selectInitialIndex() {
  const requestedId = requestedStripId();
  if (requestedId && stripById.has(requestedId)) {
    return stripById.get(requestedId).index;
  }

  const resumeId = getResumeStripId();
  if (resumeId && stripById.has(resumeId)) {
    if (requestedId) {
      notice.textContent = "That strip was not found. Your saved reading position is shown instead.";
      notice.hidden = false;
    }
    return stripById.get(resumeId).index;
  }

  if (resumeId) clearResumeStrip();
  if (requestedId) {
    notice.textContent = "That strip was not found. The archive begins here.";
    notice.hidden = false;
  }
  return 0;
}

async function initialize() {
  try {
    catalog = await loadCatalog();
    stripById = new Map(
      catalog.strips.map((strip, index) => [strip.id, { ...strip, index }]),
    );
    loading.hidden = true;
    reader.hidden = false;
    showStrip(selectInitialIndex());
  } catch (error) {
    loading.hidden = true;
    errorPanel.textContent = error instanceof Error ? error.message : "The archive could not be loaded.";
    errorPanel.hidden = false;
  }
}

previousButton.addEventListener("click", navigateFromButton);
nextButton.addEventListener("click", navigateFromButton);
document.addEventListener("keydown", (event) => {
  if (event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) return;
  if (event.key === "ArrowLeft" && !previousButton.disabled) {
    event.preventDefault();
    previousButton.click();
  } else if (event.key === "ArrowRight" && !nextButton.disabled) {
    event.preventDefault();
    nextButton.click();
  }
});

initialize();
