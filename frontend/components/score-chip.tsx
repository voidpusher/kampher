import { heatColor } from "@/lib/utils";

/**
 * The signal meter: scores rendered as stepped solid blocks, like a print
 * halftone. Flat by construction — no gradients, no translucency. Blocks
 * fill gray→blue→print-red as the score crosses 40 and 75; color is
 * information, never decoration.
 */
export function SignalMeter({
  value,
  blocks = 10,
  className = "",
}: {
  value: number;
  blocks?: number;
  className?: string;
}) {
  const clamped = Math.max(Math.min(value, 100), 0);
  const filled = Math.round((clamped / 100) * blocks);
  const color = heatColor(clamped);
  return (
    <span
      aria-label={`score ${Math.round(clamped)} out of 100`}
      className={`flex items-center gap-[3px] ${className}`}
      role="img"
    >
      {Array.from({ length: blocks }, (_, index) => (
        <span
          aria-hidden="true"
          className="h-2.5 w-1"
          key={index}
          style={{ background: index < filled ? color : "#D9D4C5" }}
        />
      ))}
    </span>
  );
}

/** Score number + meter, used in ledger rows and briefing headers. */
export function ScoreChip({
  value,
  label,
  size = "md",
}: {
  value: number;
  label?: string;
  size?: "md" | "lg";
}) {
  const color = heatColor(value);
  return (
    <span className={size === "lg" ? "inline-flex flex-col items-end gap-2" : "inline-flex items-center gap-3"}>
      <span
        className={
          size === "lg"
            ? "font-display text-5xl font-semibold tracking-[-0.06em] tabular-nums"
            : "font-mono text-sm font-medium tabular-nums"
        }
        style={{ color }}
      >
        {Math.round(value)}
      </span>
      <SignalMeter blocks={size === "lg" ? 14 : 8} value={value} />
      {label ? (
        <span className="font-mono text-[9px] uppercase tracking-[0.15em] text-faint">
          {label}
        </span>
      ) : null}
    </span>
  );
}

/** Full-width meter for score breakdown rows. */
export function ScoreBar({ value }: { value: number }) {
  return <SignalMeter blocks={24} className="w-full justify-between" value={value} />;
}
