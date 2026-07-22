import Link from "next/link";
import { notFound } from "next/navigation";
import ReactMarkdown from "react-markdown";

import { ScoreBar, ScoreChip } from "@/components/score-chip";
import { api, SOURCE_LABELS, type Score } from "@/lib/api";
import { formatDate, SCORE_LABELS } from "@/lib/utils";

export default async function OpportunityPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const [opportunity, report] = await Promise.all([
    api.opportunity(slug),
    api.report(slug),
  ]);
  if (!opportunity) notFound();

  const ordered = orderScores(opportunity.scores);
  const meta = opportunity.meta as {
    tam_band?: string;
    comparables?: string[];
    known_competitors?: string[];
  };

  return (
    <div className="mx-auto max-w-[1280px] px-4 py-10 sm:px-8 sm:py-14">
      <Link className="font-mono text-[10px] uppercase tracking-[0.14em] text-faint transition-colors hover:text-ember" href="/feed">
        ← Opportunity feed
      </Link>

      {/* Briefing masthead */}
      <header className="mt-6 border border-fg bg-surface">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-fg bg-fg px-5 py-3 text-ink sm:px-8">
          <span className="font-mono text-[9px] uppercase tracking-[0.15em]">
            Opportunity brief / {opportunity.industry_slug ?? "uncategorized"}
          </span>
          <span className="font-mono text-[9px] uppercase tracking-[0.15em] text-fgmuted">
            filed {formatDate(opportunity.created_at)}
          </span>
        </div>
        <div className="grid sm:grid-cols-[1fr_auto] sm:items-end">
          <div className="p-5 sm:p-8">
            <h1 className="max-w-3xl font-display text-3xl font-extrabold tracking-tight sm:text-4xl">
              {opportunity.title}
            </h1>
            <p className="mt-5 max-w-2xl border-l-2 border-ember pl-4 text-base leading-7 text-muted">
              {opportunity.thesis}
            </p>
          </div>
          <div className="border-t border-line p-5 sm:border-l sm:border-t-0 sm:p-8">
            <ScoreChip label="composite score" size="lg" value={opportunity.composite_score} />
          </div>
        </div>
      </header>

      <div className="mt-10 grid gap-10 lg:grid-cols-[1.25fr_0.75fr]">
        <div>
          {/* Narrative */}
          <section className="max-w-2xl space-y-4 text-[15px] leading-7 text-fg">
            {opportunity.description.split("\n\n").map((paragraph, index) => (
              <p key={index}>{paragraph}</p>
            ))}
          </section>

          {/* Score breakdown — every number ships with its reasoning. */}
          <section className="mt-12">
            <div className="border-b-2 border-fg pb-3">
              <p className="editorial-label text-ember">Scoring dossier</p>
              <h2 className="mt-2 font-display text-3xl font-semibold tracking-[-0.045em]">
                Why these scores
              </h2>
            </div>
            <div>
              {ordered.map((score) => (
                <details className="group border-b border-line py-4" key={score.kind} open={score.kind === "pain"}>
                  <summary className="grid cursor-pointer list-none grid-cols-[8.5rem_1fr_auto] items-center gap-4 sm:grid-cols-[10rem_1fr_5rem_4rem]">
                    <span className="text-sm font-medium">
                      {SCORE_LABELS[score.kind] ?? score.kind}
                    </span>
                    <ScoreBar value={score.value} />
                    <ScoreChip value={score.value} />
                    <span className="hidden text-right font-mono text-[10px] text-faint sm:block">
                      ±{Math.round((1 - score.confidence) * 100)}
                    </span>
                  </summary>
                  <p className="mt-4 max-w-2xl text-sm leading-6 text-muted sm:pl-[10rem]">
                    {score.reasoning}
                  </p>
                </details>
              ))}
            </div>
          </section>

          {/* Evidence ledger */}
          {opportunity.evidence_posts.length > 0 ? (
            <section className="mt-12">
              <div className="border-b-2 border-fg pb-3">
                <p className="editorial-label text-ember">Primary sources</p>
                <h2 className="mt-2 font-display text-3xl font-semibold tracking-[-0.045em]">
                  Evidence
                </h2>
              </div>
              <ul>
                {opportunity.evidence_posts.map((post, index) => (
                  <li key={post.id}>
                    <a
                      className="group grid grid-cols-[2.5rem_1fr] items-baseline gap-3 border-b border-line py-4 sm:grid-cols-[2.5rem_1fr_auto]"
                      href={post.url}
                      rel="noreferrer"
                      target="_blank"
                    >
                      <span className="font-mono text-[10px] text-faint">
                        [{index + 1}]
                      </span>
                      <span className="text-sm font-medium leading-snug transition-colors group-hover:text-ember">
                        {post.title ?? "untitled post"}
                      </span>
                      <span className="col-start-2 font-mono text-[9px] uppercase tracking-[0.12em] text-faint sm:col-start-3">
                        {SOURCE_LABELS[post.source] ?? post.source}
                        {post.community ? ` / ${post.community}` : ""}
                      </span>
                    </a>
                  </li>
                ))}
              </ul>
            </section>
          ) : null}

          {/* Full report */}
          {report ? (
            <section className="mt-12">
              <div className="border-b-2 border-fg pb-3">
                <p className="editorial-label text-ember">Deep dive</p>
                <h2 className="mt-2 font-display text-3xl font-semibold tracking-[-0.045em]">
                  Full report
                </h2>
              </div>
              <div className="mt-6 max-w-2xl space-y-4 text-[15px] leading-7 text-fg [&_h1]:font-display [&_h1]:text-2xl [&_h1]:font-semibold [&_h2]:mt-8 [&_h2]:font-display [&_h2]:text-xl [&_h2]:font-semibold [&_li]:ml-5 [&_li]:list-disc [&_strong]:font-semibold">
                <ReactMarkdown>{report.content_md}</ReactMarkdown>
              </div>
            </section>
          ) : null}
        </div>

        {/* Fact rail */}
        <aside className="h-fit border border-fg bg-surface lg:sticky lg:top-24">
          <p className="border-b border-fg bg-panel px-5 py-3 font-mono text-[9px] uppercase tracking-[0.15em]">
            Brief facts
          </p>
          <dl className="divide-y divide-line">
            {opportunity.target_customer ? (
              <FactRow label="Target customer" value={opportunity.target_customer} />
            ) : null}
            {opportunity.suggested_solution ? (
              <FactRow label="First product" value={opportunity.suggested_solution} />
            ) : null}
            {meta.tam_band ? <FactRow label="TAM band" mono value={meta.tam_band} /> : null}
            {meta.comparables?.length ? (
              <FactRow label="Sizing anchors" value={meta.comparables.join(", ")} />
            ) : null}
            <FactRow
              label="Known competitors"
              value={meta.known_competitors?.length ? meta.known_competitors.join(", ") : "None identified in evidence"}
            />
          </dl>
        </aside>
      </div>
    </div>
  );
}

function FactRow({ label, value, mono = false }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="px-5 py-4">
      <dt className="editorial-label">{label}</dt>
      <dd className={`mt-2 text-sm leading-6 ${mono ? "font-mono" : ""}`}>{value}</dd>
    </div>
  );
}

const SCORE_ORDER = [
  "pain",
  "trend",
  "novelty",
  "competition",
  "revenue_potential",
  "market_size",
  "virality_potential",
  "opportunity",
  "confidence",
];

function orderScores(scores: Score[]): Score[] {
  return [...scores].sort(
    (a, b) => SCORE_ORDER.indexOf(a.kind) - SCORE_ORDER.indexOf(b.kind),
  );
}
