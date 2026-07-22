import Link from "next/link";

import { ScoreChip } from "@/components/score-chip";
import { api, SOURCE_LABELS } from "@/lib/api";
import { formatDate } from "@/lib/utils";

export const metadata = { title: "Opportunity feed" };

export default async function FeedPage({
  searchParams,
}: {
  searchParams: Promise<{ industry?: string; cursor?: string }>;
}) {
  const params = await searchParams;
  const [page, industries, earlySignals] = await Promise.all([
    api.opportunities({ industry: params.industry, cursor: params.cursor, limit: 30 }),
    api.industries(),
    api.search("frustrated workaround missing feature difficult manual", "keyword"),
  ]);

  return (
    <div className="mx-auto max-w-[1200px] px-4 py-12 sm:px-6 sm:py-16">
      <header className="max-w-2xl">
        <span className="sticker -rotate-2">Ranked intelligence</span>
        <h1 className="mt-5 font-display text-5xl uppercase leading-[0.9] sm:text-7xl">
          Opportunity<br />
          <span className="outline-text">feed</span>
        </h1>
        <p className="mt-5 text-base font-medium leading-7 text-muted">
          Ranked by composite score — open any row for the full reasoning and
          evidence.
        </p>
      </header>

      {/* Sector filter */}
      {industries && industries.length > 0 ? (
        <nav aria-label="Filter by industry" className="mt-8 flex flex-wrap gap-2">
          <FilterChip active={!params.industry} href="/feed" label="All sectors" />
          {industries.map((industry) => (
            <FilterChip
              active={params.industry === industry.slug}
              href={`/feed?industry=${industry.slug}`}
              key={industry.slug}
              label={industry.name}
            />
          ))}
        </nav>
      ) : null}

      {/* The list */}
      {!page ? (
        <div className="card mt-10 border-alarm p-8">
          <h2 className="font-display text-xl font-bold tracking-tight">
            The intelligence API is temporarily unavailable.
          </h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-muted">
            The evidence corpus is preserved. Try Search or retry this page shortly.
          </p>
          <Link className="editorial-button mt-5 inline-flex" href="/search">
            Search evidence
          </Link>
        </div>
      ) : page.items.length === 0 ? (
        <div className="mt-10">
        <div className="card mt-10 grid gap-6 p-8 sm:grid-cols-[1fr_auto] sm:items-center">
          <div>
            <h2 className="font-display text-xl font-bold tracking-tight">
              The ranked feed is being calibrated.
            </h2>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-muted">
              Generated opportunities publish after their pain clusters and
              scores pass review. Search thousands of indexed conversations
              now, or ask for a cited product brief.
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <Link className="editorial-button-secondary" href="/search">
              Search evidence
            </Link>
            <Link className="editorial-button" href="/chat">
              Ask Kampher
            </Link>
          </div>
        </div>
          {earlySignals?.results.length ? (
            <section className="mt-12" aria-labelledby="early-signals-title">
              <div className="flex flex-wrap items-end justify-between gap-4 border-b-2 border-fg pb-4">
                <div>
                  <p className="editorial-label text-ember">Live evidence / unscored</p>
                  <h2 id="early-signals-title" className="mt-2 font-display text-2xl uppercase">
                    Early problem signals
                  </h2>
                </div>
                <Link className="editorial-link" href="/search">Explore the corpus →</Link>
              </div>
              <ol className="divide-y divide-line">
                {earlySignals.results.slice(0, 8).map(({ post, matched_by }, index) => (
                  <li key={post.id}>
                    <a className="group grid gap-3 py-5 sm:grid-cols-[3rem_1fr_auto] sm:items-start" href={post.url} rel="noreferrer" target="_blank">
                      <span className="font-display text-xl text-faint">{String(index + 1).padStart(2, "0")}</span>
                      <span>
                        <span className="block font-medium leading-snug group-hover:text-ember">{post.title ?? post.body.split("\n")[0] ?? "Untitled conversation"}</span>
                        {post.body ? <span className="mt-1 line-clamp-2 block text-sm leading-6 text-muted">{post.body}</span> : null}
                      </span>
                      <span className="font-mono text-[9px] uppercase tracking-[0.14em] text-faint">
                        {SOURCE_LABELS[post.source] ?? post.source} · {matched_by}
                      </span>
                    </a>
                  </li>
                ))}
              </ol>
            </section>
          ) : null}
        </div>
      ) : (
        <ol className="mt-10 space-y-5">
          {page.items.map((opportunity, index) => (
            <li key={opportunity.id}>
              <Link
                className="shadow-hard-sm group flex items-center gap-5 border-2 border-fg bg-surface px-6 py-5 transition-all hover:-translate-y-1 hover:bg-panel"
                href={`/opportunities/${opportunity.slug}`}
              >
                <span className="hidden w-14 shrink-0 font-display text-3xl text-faint transition-colors group-hover:text-ember sm:block">
                  {String(index + 1).padStart(2, "0")}
                </span>
                <span className="min-w-0 grow">
                  <span className="block font-display text-xl uppercase leading-tight tracking-wide transition-colors group-hover:text-ember">
                    {opportunity.title}
                  </span>
                  <span className="mt-1.5 block max-w-2xl text-sm font-medium leading-6 text-muted">
                    {opportunity.thesis}
                  </span>
                  <span className="mt-2.5 flex flex-wrap items-center gap-2.5">
                    {opportunity.industry_slug ? (
                      <span className="border-2 border-fg bg-yolk px-2 py-0.5 font-mono text-[10px] font-bold uppercase">
                        {opportunity.industry_slug}
                      </span>
                    ) : null}
                    <span className="font-mono text-[10px] uppercase text-faint">
                      filed {formatDate(opportunity.created_at)}
                    </span>
                  </span>
                </span>
                <ScoreChip value={opportunity.composite_score} />
              </Link>
            </li>
          ))}
        </ol>
      )}

      {page?.next_cursor ? (
        <div className="mt-8">
          <Link
            className="editorial-button-secondary"
            href={`/feed?${new URLSearchParams({
              ...(params.industry ? { industry: params.industry } : {}),
              cursor: page.next_cursor,
            })}`}
          >
            Next page →
          </Link>
        </div>
      ) : null}
    </div>
  );
}

function FilterChip({
  href,
  active,
  label,
}: {
  href: string;
  active: boolean;
  label: string;
}) {
  return (
    <Link
      className={
        active
          ? "border-2 border-fg bg-fg px-3 py-1.5 font-mono text-[11px] font-bold uppercase tracking-[0.08em] text-yolk"
          : "border-2 border-fg bg-surface px-3 py-1.5 font-mono text-[11px] font-bold uppercase tracking-[0.08em] text-fg transition-colors hover:bg-panel"
      }
      href={href}
    >
      {label}
    </Link>
  );
}
