import Link from "next/link";

import { api, SOURCE_LABELS } from "@/lib/api";

export const metadata = { title: "Corpus insights" };

const number = new Intl.NumberFormat("en-US");

function ActivityChart({ points }: { points: { date: string; count: number }[] }) {
  const width = 720;
  const height = 180;
  const maximum = Math.max(...points.map((point) => point.count), 1);
  const chartPoints = points
    .map((point, index) => {
      const x = points.length === 1 ? 0 : (index / (points.length - 1)) * width;
      const y = height - (point.count / maximum) * (height - 20);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");

  return (
    <div className="mt-8">
      <svg
        aria-label="Fourteen-day conversation activity"
        className="h-48 w-full overflow-visible"
        preserveAspectRatio="none"
        role="img"
        viewBox={`0 0 ${width} ${height}`}
      >
        <polyline
          fill="none"
          points={chartPoints}
          stroke="#bef264"
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth="3"
          vectorEffect="non-scaling-stroke"
        />
      </svg>
      <div className="mt-3 flex justify-between font-mono text-[10px] uppercase tracking-[0.16em] text-faint">
        <span>{points[0]?.date}</span>
        <span>{number.format(maximum)} peak conversations</span>
        <span>{points.at(-1)?.date}</span>
      </div>
    </div>
  );
}

export default async function InsightsPage() {
  const insights = await api.insights();

  if (!insights) {
    return (
      <div className="mx-auto max-w-6xl px-6 py-12">
        <p className="font-mono text-xs uppercase tracking-[0.18em] text-faint">
          Insights are temporarily unavailable. Please try again shortly.
        </p>
      </div>
    );
  }

  const sourceMaximum = Math.max(...insights.source_counts.map((item) => item.count), 1);

  return (
    <div className="mx-auto max-w-6xl px-6 py-12 sm:py-16">
      <section className="border-b hairline pb-10">
        <div className="flex flex-col justify-between gap-8 md:flex-row md:items-end">
          <div>
            <p className="font-mono text-[10px] uppercase tracking-[0.24em] text-accent">
              Live corpus intelligence
            </p>
            <h1 className="mt-3 max-w-2xl font-display text-4xl leading-tight sm:text-5xl">
              See what the internet is talking about now.
            </h1>
          </div>
          <div className="max-w-sm text-sm leading-relaxed text-muted">
            Raw activity from every connected source—useful before any AI interpretation.
            Updated automatically each morning.
          </div>
        </div>
      </section>

      <section className="grid gap-px border-b hairline bg-line sm:grid-cols-3">
        <div className="bg-ink py-8 sm:pr-8">
          <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-faint">
            Indexed conversations
          </p>
          <p className="mt-3 font-display text-5xl tabular-nums">
            {number.format(insights.total_posts)}
          </p>
        </div>
        <div className="bg-ink py-8 sm:px-8">
          <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-faint">
            Published in 7 days
          </p>
          <p className="mt-3 font-display text-5xl tabular-nums text-accent">
            {number.format(insights.posts_last_7_days)}
          </p>
        </div>
        <div className="bg-ink py-8 sm:pl-8">
          <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-faint">
            Last cloud sweep
          </p>
          <p className="mt-4 text-lg text-fg">
            {insights.latest_collected_at
              ? new Date(insights.latest_collected_at).toLocaleString("en-IN", {
                  dateStyle: "medium",
                  timeStyle: "short",
                  timeZone: "Asia/Kolkata",
                })
              : "No sweep recorded"}
          </p>
        </div>
      </section>

      <section className="grid gap-12 py-12 lg:grid-cols-[1.4fr_0.8fr]">
        <div>
          <div className="flex items-end justify-between gap-4">
            <div>
              <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-faint">
                Velocity
              </p>
              <h2 className="mt-2 font-display text-2xl">14-day activity</h2>
            </div>
            <Link className="text-xs text-muted transition-colors hover:text-accent" href="/search">
              Search the corpus →
            </Link>
          </div>
          <ActivityChart points={insights.daily_activity} />
        </div>

        <div className="border-t hairline pt-6 lg:border-l lg:border-t-0 lg:pl-10 lg:pt-0">
          <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-faint">
            Source mix
          </p>
          <div className="mt-6 space-y-5">
            {insights.source_counts.map((source) => (
              <div key={source.label}>
                <div className="flex items-center justify-between text-sm">
                  <span>{SOURCE_LABELS[source.label] ?? source.label}</span>
                  <span className="font-mono text-xs tabular-nums text-muted">
                    {number.format(source.count)}
                  </span>
                </div>
                <progress
                  aria-label={`${SOURCE_LABELS[source.label] ?? source.label} share`}
                  className="mt-2 h-1 w-full accent-[#bef264]"
                  max={sourceMaximum}
                  value={source.count}
                />
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="border-t hairline pt-10">
        <div className="flex items-baseline justify-between gap-4">
          <h2 className="font-display text-2xl">Most active communities</h2>
          <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-faint">
            All-time indexed volume
          </span>
        </div>
        <div className="mt-6 grid gap-px border hairline bg-line sm:grid-cols-2 lg:grid-cols-4">
          {insights.top_communities.map((community, index) => (
            <div className="group bg-ink p-5 transition-colors hover:bg-panel" key={community.label}>
              <div className="flex items-center justify-between">
                <span className="font-mono text-[10px] text-faint">{String(index + 1).padStart(2, "0")}</span>
                <span className="font-mono text-xs tabular-nums text-muted">
                  {number.format(community.count)}
                </span>
              </div>
              <p className="mt-8 truncate text-sm transition-colors group-hover:text-accent">
                {community.label}
              </p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
