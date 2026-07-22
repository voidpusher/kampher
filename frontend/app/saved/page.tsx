"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";

import { api, SOURCE_LABELS, type SearchResponse } from "@/lib/api";
import {
  readSavedSearches,
  removeSavedSearch,
  updateSavedSearch,
  type SavedSearch,
} from "@/lib/saved-searches";

interface SearchState {
  loading: boolean;
  response: SearchResponse | null;
}

export default function SavedSearchesPage() {
  const [searches, setSearches] = useState<SavedSearch[]>([]);
  const [results, setResults] = useState<Record<string, SearchState>>({});
  const [checking, setChecking] = useState(false);

  useEffect(() => {
    // Browser storage is intentionally hydrated after mount to keep SSR deterministic.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setSearches(readSavedSearches());
  }, []);

  const checkAll = useCallback(async () => {
    const current = readSavedSearches();
    if (current.length === 0) return;
    setChecking(true);
    setResults(
      Object.fromEntries(current.map((search) => [search.id, { loading: true, response: null }])),
    );

    const responses = await Promise.all(
      current.map(async (search) => ({
        search,
        response: await api.search(search.query, search.mode),
      })),
    );

    setResults(
      Object.fromEntries(
        responses.map(({ search, response }) => [search.id, { loading: false, response }]),
      ),
    );
    setChecking(false);

    for (const { search, response } of responses) {
      if (
        typeof Notification === "undefined" ||
        !search.notifications ||
        !response ||
        Notification.permission !== "granted"
      ) {
        continue;
      }
      const unseen = response.results.filter(
        (result) => new Date(result.post.posted_at) > new Date(search.lastCheckedAt),
      ).length;
      if (unseen > 0) {
        new Notification(`Kampher found ${unseen} new match${unseen === 1 ? "" : "es"}`, {
          body: search.query,
        });
      }
    }
  }, []);

  const totalUnseen = useMemo(
    () =>
      searches.reduce((total, search) => {
        const response = results[search.id]?.response;
        if (!response) return total;
        return (
          total +
          response.results.filter(
            (result) => new Date(result.post.posted_at) > new Date(search.lastCheckedAt),
          ).length
        );
      }, 0),
    [results, searches],
  );

  return (
    <div className="mx-auto max-w-5xl px-4 py-12 sm:px-8 sm:py-16">
      <div className="flex flex-col justify-between gap-6 border-b border-fg pb-10 sm:flex-row sm:items-end">
        <div>
          <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-accent">
            Personal signal desk
          </p>
          <h1 className="mt-3 font-display text-3xl font-extrabold tracking-tight sm:text-4xl">Saved searches</h1>
          <p className="mt-2 max-w-xl text-sm leading-relaxed text-muted">
            Watch recurring needs without an account. Searches remain private in this browser.
          </p>
        </div>
        {searches.length > 0 ? (
          <button
            className="editorial-button disabled:opacity-50"
            disabled={checking}
            onClick={() => void checkAll()}
            type="button"
          >
            {checking ? "Checking live sources…" : "Check all now"}
          </button>
        ) : null}
      </div>

      {totalUnseen > 0 ? (
        <div className="mt-8 flex items-center justify-between border-l-2 border-ember px-5 py-3">
          <span className="text-sm text-ember">{totalUnseen} unseen matches across your watchlist</span>
          <span className="h-2 w-2 animate-pulse bg-ember" />
        </div>
      ) : null}

      {searches.length === 0 ? (
        <div className="py-24 text-center">
          <p className="font-display text-2xl text-muted">Your watchlist is quiet.</p>
          <p className="mx-auto mt-3 max-w-md text-sm leading-relaxed text-faint">
            Search for a customer problem, technology, or recurring complaint and save it here.
          </p>
          <Link
            className="editorial-link mt-7 inline-flex"
            href="/search"
          >
            Find a signal →
          </Link>
        </div>
      ) : (
        <div className="divide-y divide-line">
          {searches.map((search, index) => {
            const state = results[search.id];
            const unseen =
              state?.response?.results.filter(
                (result) => new Date(result.post.posted_at) > new Date(search.lastCheckedAt),
              ) ?? [];
            return (
              <motion.article
                animate={{ opacity: 1, y: 0 }}
                className="py-8"
                initial={{ opacity: 0, y: 10 }}
                key={search.id}
                transition={{ delay: index * 0.05 }}
              >
                <div className="flex flex-col justify-between gap-5 sm:flex-row sm:items-start">
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <h2 className="text-lg font-medium">{search.query}</h2>
                      <span className="border border-line px-2 py-1 font-mono text-[9px] uppercase tracking-[0.14em] text-faint">
                        {search.mode}
                      </span>
                      {unseen.length > 0 ? (
                        <span className="bg-ember px-2 py-0.5 font-mono text-[9px] font-semibold text-ink">
                          {unseen.length} new
                        </span>
                      ) : null}
                    </div>
                    <p className="mt-2 font-mono text-[10px] uppercase tracking-[0.14em] text-faint">
                      Watched since {new Date(search.createdAt).toLocaleDateString("en-IN")}
                    </p>
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    <button
                      className="border border-line px-3 py-1.5 text-xs text-muted transition-colors hover:border-fg hover:text-fg"
                      onClick={async () => {
                        if (typeof Notification === "undefined") return;
                        if (Notification.permission === "default") {
                          await Notification.requestPermission();
                        }
                        if (Notification.permission === "granted") {
                          setSearches(
                            updateSavedSearch(search.id, {
                              notifications: !search.notifications,
                            }),
                          );
                        }
                      }}
                      type="button"
                    >
                      {search.notifications ? "Alerts on" : "Enable alerts"}
                    </button>
                    <button
                      className="border border-transparent px-3 py-1.5 text-xs text-faint transition-colors hover:border-line hover:text-fg"
                      onClick={() => {
                        setSearches(removeSavedSearch(search.id));
                        setResults((current) => {
                          const next = { ...current };
                          delete next[search.id];
                          return next;
                        });
                      }}
                      type="button"
                    >
                      Remove
                    </button>
                  </div>
                </div>

                {state?.loading ? (
                  <p className="mt-6 font-mono text-[10px] uppercase tracking-[0.16em] text-faint">
                    Checking the live index…
                  </p>
                ) : null}

                {state?.response ? (
                  <div className="mt-6 grid gap-px border hairline bg-line sm:grid-cols-2">
                    {state.response.results.slice(0, 4).map((result) => (
                      <a
                        className="group bg-ink p-4 transition-colors hover:bg-surface"
                        href={result.post.url}
                        key={result.post.id}
                        rel="noreferrer"
                        target="_blank"
                      >
                        <p className="line-clamp-2 text-sm leading-snug group-hover:text-ember">
                          {result.post.title ?? result.post.body.split("\n")[0] ?? "Untitled"}
                        </p>
                        <p className="mt-3 font-mono text-[9px] uppercase tracking-[0.14em] text-faint">
                          {SOURCE_LABELS[result.post.source] ?? result.post.source}
                          {result.post.community ? ` · ${result.post.community}` : ""}
                        </p>
                      </a>
                    ))}
                  </div>
                ) : null}

                {state?.response ? (
                  <button
                    className="mt-4 text-xs text-muted transition-colors hover:text-ember"
                    onClick={() => {
                      const now = new Date().toISOString();
                      setSearches(updateSavedSearch(search.id, { lastCheckedAt: now }));
                    }}
                    type="button"
                  >
                    Mark checked now
                  </button>
                ) : null}
              </motion.article>
            );
          })}
        </div>
      )}
    </div>
  );
}
