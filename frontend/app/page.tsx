import Link from "next/link";

import { FlipCard, Reveal, Scene, SceneLayer, Tilt3D } from "@/components/motion";
import { ScoreChip } from "@/components/score-chip";
import { api, SOURCE_LABELS } from "@/lib/api";

export default async function LandingPage() {
  const [page, insights, evidencePage] = await Promise.all([
    api.opportunities({ limit: 4 }),
    api.insights(),
    api.search("frustrated manual workaround tool", "keyword"),
  ]);
  const opportunities = page?.items ?? [];
  const sources = insights?.source_counts ?? [];
  const evidence = evidencePage?.results.slice(0, 8) ?? [];

  return (
    <div className="overflow-x-clip">
      {/* ── Hero: stickers, outlined type, tilted console ──────────── */}
      <section className="relative mx-auto grid max-w-[1400px] items-center gap-14 px-4 pb-24 pt-14 sm:px-6 lg:grid-cols-[1.05fr_0.95fr] lg:pt-20">
        {/* Depth stage: one quiet shape parked in the far margin — it
            parallaxes against the pointer without crowding the text. */}
        <Scene aria-hidden="true" className="pointer-events-none absolute inset-0 -z-10 overflow-visible" perspective={800}>
          <SceneLayer className="absolute bottom-6 right-[2%] max-md:hidden" depth={44}>
            <div className="h-12 w-12 rotate-45 border-2 border-fg bg-ember shadow-hard-sm" />
          </SceneLayer>
        </Scene>
        <div className="editorial-enter">
          <div className="flex flex-wrap gap-3">
            <span className="sticker floaty" style={{ "--floaty-rotate": "-3deg" } as React.CSSProperties}>
              <span className="h-2 w-2 rounded-full bg-alarm" /> Live signal
            </span>
            <span className="sticker floaty-delayed bg-surface" style={{ "--floaty-rotate": "2deg" } as React.CSSProperties}>
              100% public data
            </span>
          </div>
          <h1 className="mt-8 font-display text-[clamp(3.4rem,8vw,7.5rem)] uppercase leading-[0.92]">
            <span className="text-3d-ember-xl block">The internet</span>
            <span className="outline-text block">is screaming</span>
            <span className="block bg-fg px-3 text-yolk">what to build.</span>
          </h1>
          <p className="mt-8 max-w-xl text-lg font-medium leading-8 text-muted">
            Kampher hoards public technical conversations, sniffs out real
            pain, and turns repeated complaints into ranked, receipt-backed
            product opportunities.
          </p>
          <div className="mt-9 flex flex-wrap items-center gap-4">
            <Link className="editorial-button" href="/feed">
              Show me opportunities
            </Link>
            <Link className="editorial-button-secondary" href="/search">
              Dig the evidence
            </Link>
          </div>
        </div>

        {/* The console: paper-stacked, follows the pointer in 3D */}
        <Tilt3D className="rotate-1" maxDeg={8}>
          <div className="paper-stack border-2 border-fg bg-surface">
          <div className="flex items-center justify-between border-b-2 border-fg bg-fg px-5 py-3 text-ink">
            <span className="font-mono text-[11px] font-bold uppercase tracking-[0.12em] text-yolk">
              Scrape-o-meter
            </span>
            <span className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.1em] text-fgmuted">
              <span className="h-2 w-2 rounded-full bg-alarm" /> ingesting
            </span>
          </div>
          <div className="divide-y-2 divide-line">
            {sources.slice(0, 4).map((source, index) => (
              <div className="flex items-center gap-4 px-5 py-3.5" key={source.label}>
                <span className="w-9 font-display text-lg text-faint">{String(index + 1).padStart(2, "0")}</span>
                <span className="w-32 shrink-0 text-sm font-bold">
                  {SOURCE_LABELS[source.label] ?? source.label}
                </span>
                <span className="h-3 grow border-2 border-fg bg-surface">
                  <span
                    className="block h-full bg-ember"
                    style={{
                      width: `${Math.max(8, (source.count / Math.max(...sources.map((s) => s.count), 1)) * 100)}%`,
                    }}
                  />
                </span>
                <span className="w-14 text-right font-mono text-xs font-bold tabular-nums">
                  {format(source.count)}
                </span>
              </div>
            ))}
          </div>
          <div className="border-t-2 border-fg bg-panel px-5 py-2.5">
            <p className="font-mono text-[10px] font-bold uppercase tracking-[0.12em]">
              Freshly intercepted
            </p>
          </div>
          <ul className="divide-y-2 divide-line">
            {evidence.slice(0, 3).map(({ post }) => (
              <li className="flex items-baseline justify-between gap-4 px-5 py-3" key={post.id}>
                <p className="truncate text-sm font-medium">{post.title || truncate(post.body, 60)}</p>
                <span className="shrink-0 border-2 border-fg bg-yolk px-2 py-0.5 font-mono text-[10px] font-bold uppercase">
                  {SOURCE_LABELS[post.source] ?? post.source}
                </span>
              </li>
            ))}
            {!evidence.length ? (
              <li className="px-5 py-5 text-sm font-medium text-muted">
                Collector syncing — next sweep incoming.
              </li>
            ) : null}
          </ul>
          </div>
        </Tilt3D>
      </section>

      {/* ── The tape: tilted marquee of raw evidence ───────────────── */}
      <section aria-label="Recently intercepted evidence" className="relative -mx-2 -rotate-1 border-y-4 border-fg bg-ember py-3 text-white">
        {evidence.length ? (
          <div className="ticker flex w-max items-center gap-10">
            {[...evidence, ...evidence].map(({ post }, index) => (
              <span aria-hidden={index >= evidence.length} className="flex items-center gap-4 whitespace-nowrap" key={`${post.id}-${index}`}>
                <span className="font-mono text-[11px] font-bold uppercase tracking-[0.1em] text-yolk">
                  {SOURCE_LABELS[post.source] ?? post.source}
                </span>
                <span className="text-sm font-bold">{truncate(post.title ?? post.body, 80)}</span>
                <span aria-hidden="true" className="text-yolk">★</span>
              </span>
            ))}
          </div>
        ) : (
          <p className="px-6 font-mono text-[11px] font-bold uppercase tracking-[0.14em]">
            Tape starts rolling with the next sweep
          </p>
        )}
      </section>

      {/* ── Stats: three tilted cards ──────────────────────────────── */}
      <section className="mx-auto max-w-[1400px] px-4 py-24 sm:px-6">
        <div className="grid gap-8 sm:grid-cols-3">
          <Reveal delay={0}>
            <FlipCard
              back={<StatBack note="that is a lot of complaining" />}
              front={
                <StatCard
                  label="Conversations hoarded"
                  rotate="-rotate-2"
                  value={insights ? format(insights.total_posts) : "—"}
                />
              }
            />
          </Reveal>
          <Reveal delay={0.12}>
            <FlipCard
              back={<StatBack note="still warm from the internet" />}
              front={
                <StatCard
                  fill="bg-yolk"
                  label="Fresh this week"
                  rotate="rotate-1"
                  value={insights ? format(insights.posts_last_7_days) : "—"}
                />
              }
            />
          </Reveal>
          <Reveal delay={0.24}>
            <FlipCard
              back={<StatBack note="they never see us coming" />}
              front={
                <StatCard
                  fill="bg-fg text-ink"
                  label="Sources under watch"
                  rotate="-rotate-1"
                  value={insights ? String(sources.length) : "—"}
                  valueClass="text-3d-ember text-yolk"
                />
              }
            />
          </Reveal>
        </div>
      </section>

      {/* ── Process: alternating full-bleed color fields ───────────── */}
      <section>
        {[
          {
            step: "01",
            title: "Catch the complaint",
            body: "Scheduled collectors grab technical conversations before the feeds bury them.",
            classes: "bg-yolk text-fg",
            num: "text-fg text-3d-ember",
          },
          {
            step: "02",
            title: "Hoard the history",
            body: "Every sweep piles into a searchable corpus instead of replacing yesterday with today.",
            classes: "bg-ink text-fg",
            num: "text-fg text-3d-ember",
          },
          {
            step: "03",
            title: "Connect the pattern",
            body: "Semantic retrieval finds the same unmet need even when people rant about it differently.",
            classes: "bg-ember text-white",
            num: "text-yolk text-3d-ink",
          },
          {
            step: "04",
            title: "Keep the receipts",
            body: "Every direction ships with its original threads, scores, and citations stapled on.",
            classes: "bg-fg text-ink",
            num: "text-ink text-3d-ember",
          },
        ].map((item) => (
          <div className={`border-t-4 border-fg ${item.classes}`} key={item.step}>
            <Reveal>
              <div className="mx-auto grid max-w-[1400px] grid-cols-[4rem_1fr] items-center gap-6 px-4 py-10 sm:grid-cols-[8rem_1fr_1fr] sm:gap-10 sm:px-6">
                <span className={`font-display text-5xl sm:text-7xl ${item.num}`}>{item.step}</span>
                <h3 className="font-display text-3xl uppercase leading-none sm:text-4xl">
                  {item.title}
                </h3>
                <p className="col-span-2 max-w-xl text-base font-medium leading-7 sm:col-span-1">
                  {item.body}
                </p>
              </div>
            </Reveal>
          </div>
        ))}
      </section>

      {/* ── Opportunities ──────────────────────────────────────────── */}
      <section className="mx-auto max-w-[1400px] px-4 py-24 sm:px-6">
        <div className="flex flex-wrap items-end justify-between gap-6">
          <h2 className="font-display text-4xl uppercase leading-none sm:text-6xl">
            Signals worth<br />
            <span className="outline-text">investigating</span>
          </h2>
          <Link className="editorial-link" href="/feed">
            Full feed →
          </Link>
        </div>

        {opportunities.length ? (
          <ol className="mt-12 space-y-6">
            {opportunities.map((opportunity, index) => (
              <li key={opportunity.id}>
                <Reveal delay={index * 0.08}>
                <Link
                  className="shadow-hard-sm group grid grid-cols-[3.5rem_1fr] items-center gap-5 border-2 border-fg bg-surface px-6 py-6 transition-all hover:-translate-y-1 hover:bg-panel sm:grid-cols-[5rem_1fr_auto]"
                  href={`/opportunities/${opportunity.slug}`}
                >
                  <span className="font-display text-4xl text-faint transition-colors group-hover:text-ember sm:text-5xl">
                    {String(index + 1).padStart(2, "0")}
                  </span>
                  <span>
                    <span className="font-display text-2xl uppercase leading-none tracking-wide transition-colors group-hover:text-ember">
                      {opportunity.title}
                    </span>
                    <span className="mt-2 block max-w-2xl text-sm font-medium leading-6 text-muted">
                      {opportunity.thesis}
                    </span>
                  </span>
                  <span className="col-start-2 sm:col-start-3 sm:justify-self-end">
                    <ScoreChip value={opportunity.composite_score} />
                  </span>
                </Link>
                </Reveal>
              </li>
            ))}
          </ol>
        ) : (
          <div className="shadow-hard mt-12 grid gap-6 border-2 border-fg bg-surface p-8 sm:grid-cols-[1fr_auto] sm:items-center">
            <div>
              <span className="sticker -rotate-2">Synthesis desk calibrating</span>
              <h3 className="mt-5 font-display text-3xl uppercase leading-none">
                The evidence corpus is live now.
              </h3>
              <p className="mt-3 max-w-xl text-sm font-medium leading-6 text-muted">
                Search thousands of conversations, or ask Kampher to turn a
                market into a cited problem brief.
              </p>
            </div>
            <Link className="editorial-button" href="/chat">
              Find me a problem
            </Link>
          </div>
        )}
      </section>

      {/* ── CTA slab ───────────────────────────────────────────────── */}
      <section className="border-t-4 border-fg bg-fg py-20 text-ink">
        <Reveal>
        <div className="mx-auto max-w-[1400px] px-4 text-center sm:px-6">
          <h2 className="font-display text-[clamp(2.6rem,6vw,5.5rem)] uppercase leading-[0.9]">
            <span className="text-3d-ember text-yolk">Stop guessing.</span>{" "}
            <span className="outline-text-white">Start listening.</span>
          </h2>
          <p className="mx-auto mt-6 max-w-xl text-base font-medium leading-7 text-fgmuted">
            Ask Kampher for problems worth solving — every answer arrives with
            the receipts attached.
          </p>
          <div className="mt-10 flex justify-center">
            <Link className="editorial-button" href="/chat">
              Ask your first question
            </Link>
          </div>
        </div>
        </Reveal>
      </section>
    </div>
  );
}

function StatBack({ note }: { note: string }) {
  return (
    <div className="shadow-hard flex h-full items-center justify-center border-2 border-fg bg-ember p-7 text-center">
      <p className="font-display text-2xl uppercase leading-tight text-white">
        {note}
      </p>
    </div>
  );
}

function StatCard({
  label,
  value,
  rotate,
  fill = "bg-surface",
  valueClass = "",
}: {
  label: string;
  value: string;
  rotate: string;
  fill?: string;
  valueClass?: string;
}) {
  return (
    <div className={`extrude border-2 border-fg p-7 transition-transform hover:rotate-0 ${fill} ${rotate}`}>
      <p className="font-mono text-[11px] font-bold uppercase tracking-[0.12em]">{label}</p>
      <p className={`mt-3 font-display text-6xl leading-none sm:text-7xl ${valueClass}`}>{value}</p>
    </div>
  );
}

function truncate(value: string, max: number) {
  const clean = value.replace(/\s+/g, " ").trim();
  return clean.length > max ? `${clean.slice(0, max - 1)}…` : clean;
}

function format(value: number) {
  return new Intl.NumberFormat("en-US", {
    notation: value > 9999 ? "compact" : "standard",
    maximumFractionDigits: 1,
  }).format(value);
}
