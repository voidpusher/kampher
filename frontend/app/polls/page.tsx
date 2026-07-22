import Link from "next/link";

import { api, TechPoll } from "@/lib/api";
import { cn } from "@/lib/utils";

export const metadata = { title: "Tech polls" };

const number = new Intl.NumberFormat("en-US");

function PollCard({ poll, index }: { poll: TechPoll; index: number }) {
  return (
    <article className="group border-t hairline py-8 first:border-t-0 lg:grid lg:grid-cols-[minmax(220px,0.75fr)_minmax(320px,1.25fr)] lg:gap-12 lg:py-10">
      <div>
        <div className="flex items-center gap-3 font-mono text-[10px] uppercase tracking-[0.2em] text-faint">
          <span>{String(index + 1).padStart(2, "0")}</span>
          <span className="h-px w-6 bg-line" />
          <span className="text-accent">{poll.category}</span>
        </div>
        <h2 className="mt-4 max-w-lg font-display text-2xl leading-snug sm:text-3xl">
          {poll.question}
        </h2>
        <p className="mt-4 text-xs leading-relaxed text-muted">
          {poll.audience}
          {poll.note ? ` · ${poll.note}` : ""}
        </p>
      </div>

      <div className="mt-8 space-y-5 lg:mt-0">
        {poll.options.map((option) => (
          <div key={option.label}>
            <div className="flex items-baseline justify-between gap-4 text-sm">
              <span className="leading-tight text-fg">{option.label}</span>
              <span className="font-mono text-xs tabular-nums text-muted">
                {option.percentage.toFixed(1)}%
              </span>
            </div>
            <div className="mt-2 h-1 bg-line">
              <div
                className="h-full origin-left bg-ember transition-transform duration-500 group-hover:scale-x-[1.01]"
                style={{ width: `${option.percentage}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </article>
  );
}

export default async function PollsPage({
  searchParams,
}: {
  searchParams: Promise<{ category?: string }>;
}) {
  const { category } = await searchParams;
  const overview = await api.techPolls(category);

  if (!overview) {
    return (
      <div className="mx-auto max-w-6xl px-6 py-12">
        <p className="font-mono text-xs uppercase tracking-[0.18em] text-faint">
          Poll evidence is temporarily unavailable. Please try again shortly.
        </p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-6xl px-6 py-12 sm:py-16">
      <section className="border-b border-fg pb-12">
        <div className="grid gap-10 lg:grid-cols-[1.35fr_0.65fr] lg:items-end">
          <div>
            <p className="font-mono text-[10px] uppercase tracking-[0.24em] text-accent">
              Published survey evidence
            </p>
            <h1 className="mt-4 max-w-3xl font-display text-5xl leading-[0.98] sm:text-6xl">
              What developers say,
              <span className="block text-muted">at research scale.</span>
            </h1>
            <p className="mt-6 max-w-2xl text-sm leading-relaxed text-muted">
              Reliable tech polls add the broad market view to Kampher&apos;s live conversation
              signals. Every result keeps its sample, dates, methodology, and known bias attached.
            </p>
          </div>
          <div className="grid grid-cols-2 gap-px border hairline bg-line">
            <div className="bg-ink p-5">
              <p className="font-display text-3xl tabular-nums">
                {number.format(overview.total_respondents)}
              </p>
              <p className="mt-2 font-mono text-[9px] uppercase tracking-[0.18em] text-faint">
                Survey respondents
              </p>
            </div>
            <div className="bg-ink p-5">
              <p className="font-display text-3xl tabular-nums">{overview.polls.length}</p>
              <p className="mt-2 font-mono text-[9px] uppercase tracking-[0.18em] text-faint">
                Evidence cards
              </p>
            </div>
          </div>
        </div>
      </section>

      <section className="flex flex-col gap-6 border-b hairline py-6 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-wrap gap-2" aria-label="Poll categories">
          {["All", ...overview.categories].map((item) => {
            const active = item === "All" ? !category : item.toLowerCase() === category?.toLowerCase();
            return (
              <Link
                className={cn(
                  "border px-3.5 py-2 font-mono text-[10px] uppercase tracking-[0.14em] transition-colors",
                  active
                    ? "border-fg bg-fg text-ink"
                    : "border-line text-faint hover:border-muted hover:text-fg",
                )}
                href={item === "All" ? "/polls" : `/polls?category=${encodeURIComponent(item)}`}
                key={item}
              >
                {item}
              </Link>
            );
          })}
        </div>
        <span className="font-mono text-[9px] uppercase tracking-[0.18em] text-faint">
          Aggregates, not live voting
        </span>
      </section>

      <section>
        {overview.polls.length ? (
          overview.polls.map((poll, index) => <PollCard index={index} key={poll.id} poll={poll} />)
        ) : (
          <p className="py-16 text-sm text-muted">No polls are available in this category.</p>
        )}
      </section>

      {overview.polls[0] ? (
        <aside className="grid gap-8 border-y hairline py-8 sm:grid-cols-[0.75fr_1.25fr]">
          <div>
            <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-accent">
              Source ledger
            </p>
            <h2 className="mt-3 font-display text-2xl">
              {overview.polls[0].survey.publisher} {overview.polls[0].survey.year}
            </h2>
            <p className="mt-2 text-xs text-muted">
              {number.format(overview.polls[0].survey.sample_size)} responses ·{" "}
              {overview.polls[0].survey.geography}
            </p>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="border-l-2 border-ember pl-2.5 font-mono text-[9px] uppercase tracking-[0.16em] text-accent">
                {Math.round(overview.polls[0].survey.reliability_score * 100)}% source quality
              </span>
              {overview.polls[0].survey.license ? (
                <span className="font-mono text-[9px] uppercase tracking-[0.14em] text-faint">
                  {overview.polls[0].survey.license}
                </span>
              ) : null}
            </div>
            <p className="mt-4 max-w-2xl text-sm leading-relaxed text-muted">
              <span className="text-fg">Sampling caveat:</span>{" "}
              {overview.polls[0].survey.bias_note}
            </p>
            <div className="mt-5 flex gap-5 text-xs">
              <a className="text-muted transition-colors hover:text-accent" href={overview.polls[0].survey.source_url} rel="noreferrer" target="_blank">
                View source ↗
              </a>
              <a className="text-muted transition-colors hover:text-accent" href={overview.polls[0].survey.methodology_url} rel="noreferrer" target="_blank">
                Read methodology ↗
              </a>
            </div>
          </div>
        </aside>
      ) : null}
    </div>
  );
}
