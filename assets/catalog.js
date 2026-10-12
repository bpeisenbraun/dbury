const COOKIE_NAME = "doonesbury_reader_position";
const ONE_YEAR_SECONDS = 60 * 60 * 24 * 365;

export async function loadCatalog() {
  const response = await fetch("data/catalog.json", { cache: "no-cache" });
  if (!response.ok) {
    throw new Error(`The archive catalog could not be loaded (${response.status}).`);
  }

  const catalog = await response.json();
  if (catalog.version !== 1 || !Array.isArray(catalog.strips) || !Array.isArray(catalog.years)) {
    throw new Error("The archive catalog has an unsupported format.");
  }
  return catalog;
}

export function getResumeStripId() {
  const prefix = `${COOKIE_NAME}=`;
  const entry = document.cookie
    .split(";")
    .map((part) => part.trim())
    .find((part) => part.startsWith(prefix));

  if (!entry) return null;

  try {
    return decodeURIComponent(entry.slice(prefix.length));
  } catch {
    clearResumeStrip();
    return null;
  }
}

export function saveResumeStrip(stripId) {
  document.cookie = `${COOKIE_NAME}=${encodeURIComponent(stripId)}; Max-Age=${ONE_YEAR_SECONDS}; Path=/; SameSite=Lax`;
}

export function clearResumeStrip() {
  document.cookie = `${COOKIE_NAME}=; Max-Age=0; Path=/; SameSite=Lax`;
}

export function viewerUrl(stripId) {
  return `viewer.html?strip=${encodeURIComponent(stripId)}`;
}

export function formatDate(isoDate) {
  const safeDate = new Date(`${isoDate}T12:00:00`);
  return new Intl.DateTimeFormat(undefined, {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
  }).format(safeDate);
}

export function formatNumber(value) {
  return new Intl.NumberFormat().format(value);
}
