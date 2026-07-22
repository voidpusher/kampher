import Link from "next/link";

import { api } from "@/lib/api";
import { heatColor } from "@/lib/utils";

export const metadata = { title: "Trend explorer" };

export default async function TrendsPage() {
  const trends = await api.trends(40);

  return (
    <div className="mx-auto max-w-[1280px] px-4 py-12 sm:px-8 sm:py-16">
      <div className="border-b border-fg pb-8">
      <p className="editorial-label">Historical signal velocity</p>
      <h1 className="mt-3 font-display text-3xl font-extrabold tracking-tight sm:text-4xl">Trend explorer</h1>
      <p className="mt-3 text-sm text-muted">
        Pain clusters ranked by velocity — how fast each problem is being
        talked about, and whether it&apos;s accelerating.
      </p>
      </div>

      {!trends || trends.length === 0 ? (
        <div className="mt-12 max-w-2xl rounded-xl border border-line bg-surface p-7">
          <p className="editorial-label text-ember">Trend history is accumulating</p>
          <p className="mt-3 text-sm leading-6 text-muted">
            Trend rankings publish after the same problem has enough observations across multiple collection windows. The raw 14-day activity view is available now.
          </p>
          <Link className="editorial-link mt-5 inline-flex" href="/insights">
            View corpus activity →
          </Link>
        </div>
      ) : (
        <div className="mt-10 overflow-x-auto">
          <table className="w-full min-w-[720px] border-y hairline text-sm">
            <thead>
              <tr className="border-b hairline font-mono text-[10px] uppercase tracking-[0.2em] text-faint">
                <th className="py-3 pr-4 text-left font-normal">Problem</th>
                <th className="px-4 py-3 text-right font-normal">Mentions</th>
                <th className="px-4 py-3 text-right font-normal">Velocity /day</th>
                <th className="px-4 py-3 text-right font-normal">Acceleration</th>
                <th className="px-4 py-3 text-right font-normal">Severity</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {trends.map((trend) => (
                <tr key={trend.cluster_id}>
                  <td className="max-w-md py-4 pr-4 leading-snug">
                    {trend.canonical_statement}
                    <span className="mt-1 block font-mono text-[10px] text-faint">
                      {trend.support_count} supporting posts
                    </span>
                  </td>
                  <td className="px-4 py-4 text-right font-mono tabular-nums">
                    {trend.mention_count}
                  </td>
                  <td
                    className="px-4 py-4 text-right font-mono tabular-nums"
                    style={{ color: heatColor(50 + trend.velocity * 25) }}
                  >
                    {trend.velocity >= 0 ? "+" : ""}
                    {trend.velocity.toFixed(2)}
                  </td>
                  <td className="px-4 py-4 text-right font-mono tabular-nums text-muted">
                    {trend.acceleration >= 0 ? "+" : ""}
                    {trend.acceleration.toFixed(2)}
                  </td>
                  <td className="px-4 py-4 text-right font-mono tabular-nums text-muted">
                    {(trend.avg_severity * 100).toFixed(0)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
