export type SavedSearchMode = "hybrid" | "semantic" | "keyword";

export interface SavedSearch {
  id: string;
  query: string;
  mode: SavedSearchMode;
  createdAt: string;
  lastCheckedAt: string;
  notifications: boolean;
}

const STORAGE_KEY = "kampher.saved-searches.v1";
const MAX_SAVED_SEARCHES = 100;
const MAX_QUERY_LENGTH = 500;
const MODES = new Set<SavedSearchMode>(["hybrid", "semantic", "keyword"]);

function isSavedSearch(value: unknown): value is SavedSearch {
  if (!value || typeof value !== "object") return false;
  const search = value as Partial<SavedSearch>;
  return (
    typeof search.id === "string" &&
    typeof search.query === "string" &&
    search.query.length > 0 &&
    search.query.length <= MAX_QUERY_LENGTH &&
    typeof search.mode === "string" &&
    MODES.has(search.mode as SavedSearchMode) &&
    typeof search.createdAt === "string" &&
    !Number.isNaN(Date.parse(search.createdAt)) &&
    typeof search.lastCheckedAt === "string" &&
    !Number.isNaN(Date.parse(search.lastCheckedAt)) &&
    typeof search.notifications === "boolean"
  );
}

export function readSavedSearches(): SavedSearch[] {
  if (typeof window === "undefined") return [];
  try {
    const value = window.localStorage.getItem(STORAGE_KEY);
    if (!value) return [];
    const parsed: unknown = JSON.parse(value);
    return Array.isArray(parsed)
      ? parsed.filter(isSavedSearch).slice(0, MAX_SAVED_SEARCHES)
      : [];
  } catch {
    return [];
  }
}

function writeSavedSearches(searches: SavedSearch[]): void {
  window.localStorage.setItem(
    STORAGE_KEY,
    JSON.stringify(searches.filter(isSavedSearch).slice(0, MAX_SAVED_SEARCHES)),
  );
  window.dispatchEvent(new Event("kampher:saved-searches"));
}

export function saveSearch(query: string, mode: SavedSearchMode): SavedSearch {
  const normalized = query.trim().slice(0, MAX_QUERY_LENGTH);
  const searches = readSavedSearches();
  const existing = searches.find(
    (search) => search.query.toLowerCase() === normalized.toLowerCase() && search.mode === mode,
  );
  if (existing) return existing;

  const now = new Date().toISOString();
  const search: SavedSearch = {
    id: crypto.randomUUID(),
    query: normalized,
    mode,
    createdAt: now,
    lastCheckedAt: now,
    notifications: false,
  };
  writeSavedSearches([search, ...searches]);
  return search;
}

export function removeSavedSearch(id: string): SavedSearch[] {
  const searches = readSavedSearches().filter((search) => search.id !== id);
  writeSavedSearches(searches);
  return searches;
}

export function updateSavedSearch(
  id: string,
  patch: Partial<Pick<SavedSearch, "lastCheckedAt" | "notifications">>,
): SavedSearch[] {
  const searches = readSavedSearches().map((search) =>
    search.id === id ? { ...search, ...patch } : search,
  );
  writeSavedSearches(searches);
  return searches;
}

export function hasSavedSearch(query: string, mode: string): boolean {
  const normalized = query.trim().toLowerCase();
  return readSavedSearches().some(
    (search) => search.query.toLowerCase() === normalized && search.mode === mode,
  );
}
