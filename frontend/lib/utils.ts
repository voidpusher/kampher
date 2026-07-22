import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Map a 0-100 score to a solid ink. Three steps only, so color stays
 * information: gray = weak, violet = signal, red = exceptional (>=75).
 */
export function heatColor(score: number): string {
  if (score >= 75) return "#FF2E00";
  if (score >= 40) return "#6C2BD9";
  return "#9E9E9E";
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export const SCORE_LABELS: Record<string, string> = {
  pain: "Pain",
  trend: "Trend",
  opportunity: "Opportunity",
  competition: "Competition",
  novelty: "Novelty",
  revenue_potential: "Revenue potential",
  virality_potential: "Virality",
  market_size: "Market size",
  confidence: "Confidence",
};
