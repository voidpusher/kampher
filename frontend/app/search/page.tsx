"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useState } from "react";
import { motion } from "framer-motion";
import { api, SOURCE_LABELS, type SearchResponse } from "@/lib/api";
import { hasSavedSearch, saveSearch, type SavedSearchMode } from "@/lib/saved-searches";
import { cn } from "@/lib/utils";

const MODES = [
  { id: "hybrid", label: "Hybrid" },
  { id: "semantic", label: "Semantic" },
  { id: "keyword", label: "Keyword" },
] as const;

export default function SearchPage() {
  return (
    <Suspense fallback={<div className="mx-auto max-w-5xl px-4 py-16 font-mono text-xs uppercase tracking-[0.16em] text-faint">Loading search…</div>}>
      <SearchRoute />
    </Suspense>
  );
}

function SearchRoute() {
  const searchParams = useSearchParams();
  return <SearchInterface key={searchParams.toString()} searchParams={searchParams} />;
}

function SearchInterface({ searchParams }: { searchParams: ReturnType<typeof useSearchParams> }) {
  const initialCommunity = searchParams.get("community");
  const initialQuery = searchParams.get("q")?.trim() ?? "";
  const requestedMode = searchParams.get("mode") ?? "hybrid";
  const initialMode = MODES.some((item) => item.id === requestedMode)
    ? requestedMode
    : "hybrid";

  const [query, setQuery] = useState(initialQuery);
  const [mode, setMode] = useState<string>(initialMode);
  const [response, setResponse] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [saved, setSaved] = useState(false);
  const [community] = useState<string | null>(initialCommunity);
  const failed = searched && !loading && response === null;

  const execute = useCallback(
    async (searchQuery: string, activeMode: string, activeCommunity: string | null) => {
      if (searchQuery.length < 2 && !activeCommunity) return;
      setLoading(true);
      setSearched(true);
      const result = await api.search(searchQuery, activeMode, {
        community: activeCommunity ?? undefined,
      });
      setResponse(result);
      setLoading(false);
    },
    [],
  );

  const run = useCallback(
    async (nextMode?: string) => {
      await execute(query.trim(), nextMode ?? mode, community);
    },
    [community, execute, mode, query],
  );

  useEffect(() => {
    if (!initialCommunity && initialQuery.length < 2) return;
    const timer = window.setTimeout(() => {
      void execute(initialQuery, initialMode, initialCommunity);
    }, 0);
    return () => window.clearTimeout(timer);
  }, [execute, initialCommunity, initialMode, initialQuery]);

  return (
    <div className="mx-auto max-w-5xl px-4 py-12 sm:px-8 sm:py-16">
      <div className="border-b border-fg pb-8">
      <p className="editorial-label">Corpus retrieval / indexed conversations</p>
      <h1 className="mt-3 font-display text-3xl font-extrabold tracking-tight sm:text-4xl">Search the signal</h1>
      <p className="mt-3 text-sm text-muted">
        Keyword hits the words; semantic hits the meaning; hybrid fuses both.
      </p>
      </div>

      <form
        className="mt-8"
        onSubmit={(event) => {
          event.preventDefault();
          void run();
        }}
      >
        <div className="flex gap-3">
          <input
            value={query}
            onChange={(event) => {
              const nextQuery = event.target.value;
              setQuery(nextQuery);
              setSaved(hasSavedSearch(nextQuery, mode));
            }}
            placeholder={community ? `Search within ${community}…` : "developer complaints about authentication…"}
            className="field-control w-full"
            aria-label="Search query"
          />
          <button
            type="submit"
            disabled={loading || (query.trim().length < 2 && !community)}
            className="editorial-button shrink-0 disabled:opacity-40"
          >
            {loading ? "Searching…" : "Search"}
          </button>
        </div>
        <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
          <div className="flex gap-1">
            {MODES.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => {
                  setMode(item.id);
                  setSaved(hasSavedSearch(query, item.id));
                  if (searched) void run(item.id);
                }}
                className={cn(
                  "border px-3 py-1.5 font-mono text-[10px] uppercase tracking-[0.1em]",
                  mode === item.id ? "border-fg bg-fg text-ink" : "border-line text-faint hover:border-fg hover:text-fg",
                )}
              >
                {item.label}
              </button>
            ))}
          </div>
          <button
            className={cn(
              "border border-line px-3 py-1.5 font-mono text-[10px] uppercase tracking-[0.14em] transition-colors",
              saved
                ? "border-ember text-ember"
                : "text-muted hover:border-muted hover:text-fg",
            )}
            disabled={saved || query.trim().length < 2}
            onClick={() => {
              saveSearch(query.trim(), mode as SavedSearchMode);
              setSaved(true);
            }}
            type="button"
          >
            {saved ? "Saved to watchlist" : "+ Save search"}
          </button>
        </div>
      </form>

      {community ? (
        <div className="mt-6 flex flex-wrap items-center justify-between gap-3 border-2 border-fg bg-panel px-4 py-3">
          <p className="font-mono text-[10px] font-medium uppercase tracking-[0.14em]">
            Browsing community / <span className="text-ember">{community}</span>
          </p>
          <Link className="editorial-link text-xs" href="/search">
            Clear community →
          </Link>
        </div>
      ) : null}

      <div className="mt-10">
        {failed ? (
          <div className="rounded-lg border border-line bg-surface p-5">
            <p className="text-sm font-medium text-fg">Search is temporarily unavailable.</p>
            <p className="mt-2 text-sm text-muted">Your query is still here. Retry when the connection is restored.</p>
            <button className="editorial-link mt-4" onClick={() => void run()} type="button">
              Retry search →
            </button>
          </div>
        ) : null}
        {searched && !loading && response && response.results.length === 0 ? (
          <p className="font-mono text-xs text-faint">
            {community && !query
              ? "NO INDEXED CONVERSATIONS FOUND FOR THIS COMMUNITY."
              : "NO MATCHES — try semantic mode, or broaden the phrasing."}
          </p>
        ) : null}
        <ul className="divide-y divide-line">
          {(response?.results ?? []).map((result, index) => (
            <motion.li
              key={result.post.id}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.03, duration: 0.25 }}
            >
              <a
                href={result.post.url}
                target="_blank"
                rel="noreferrer"
                className="group block py-5"
              >
                <div className="flex items-baseline justify-between gap-4">
                  <span className="font-medium leading-snug group-hover:text-ember">
                    {result.post.title ?? firstLine(result.post.body)}
                  </span>
                  <span className="shrink-0 font-mono text-[10px] uppercase tracking-[0.15em] text-faint">
                    {result.matched_by}
                  </span>
                </div>
                {result.post.title && result.post.body ? (
                  <p className="mt-1 line-clamp-2 max-w-2xl text-sm leading-relaxed text-muted">
                    {result.post.body}
                  </p>
                ) : null}
                <p className="mt-2 font-mono text-[10px] uppercase tracking-[0.15em] text-faint">
                  {SOURCE_LABELS[result.post.source] ?? result.post.source}
                  {result.post.community ? ` · ${result.post.community}` : ""}
                  {result.post.has_pain_signal ? " · pain signal" : ""}
                </p>
              </a>
            </motion.li>
          ))}
        </ul>
      </div>
    </div>
  );
}

function firstLine(body: string): string {
  const line = body.split("\n")[0] ?? "";
  return line.length > 120 ? line.slice(0, 119) + "…" : line || "untitled";
}
