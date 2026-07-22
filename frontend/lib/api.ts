/**
 * Typed client for the Kampher API. Mirrors backend/app/schemas/api.py —
 * if a shape changes there, it changes here.
 */

const API_URL =
  process.env.NEXT_PUBLIC_API_URL ??
  (process.env.NODE_ENV === "production"
    ? "https://kampher-api.onrender.com"
    : "http://localhost:8000");

// Server-rendered pages should never hold the document behind a sleeping API.
// Interactive browser searches can wait longer; public pages fail fast into
// their cached or useful empty state.
const READ_TIMEOUT_MS = typeof window === "undefined" ? 8_000 : 15_000;

export type Source =
  | "reddit"
  | "x"
  | "github_issues"
  | "github_discussions"
  | "hackernews"
  | "stackoverflow"
  | "lobsters"
  | "devto"
  | "discord"
  | "producthunt";

export type ScoreKind =
  | "pain"
  | "trend"
  | "opportunity"
  | "competition"
  | "novelty"
  | "revenue_potential"
  | "virality_potential"
  | "market_size"
  | "confidence";

export interface Score {
  kind: ScoreKind;
  value: number;
  confidence: number;
  reasoning: string;
  evidence: { posts?: { post_id: string; quote?: string | null }[] };
}

export interface OpportunitySummary {
  id: string;
  slug: string;
  title: string;
  thesis: string;
  status: string;
  composite_score: number;
  industry_slug: string | null;
  created_at: string;
}

export interface PostRef {
  id: string;
  source: Source;
  title: string | null;
  url: string;
  community?: string | null;
}

export interface OpportunityDetail extends OpportunitySummary {
  description: string;
  target_customer: string | null;
  suggested_solution: string | null;
  meta: Record<string, unknown>;
  scores: Score[];
  evidence_posts: PostRef[];
}

export interface OpportunityPage {
  items: OpportunitySummary[];
  next_cursor: string | null;
}

export interface Post {
  id: string;
  source: Source;
  url: string;
  title: string | null;
  body: string;
  community: string | null;
  posted_at: string;
  metrics: Record<string, number>;
  language: string | null;
  has_pain_signal: boolean | null;
}

export interface SearchResult {
  post: Post;
  score: number;
  matched_by: string;
}

export interface SearchResponse {
  query: string;
  mode: string;
  results: SearchResult[];
}

export interface ChatResponse {
  answer: string;
  cited_posts: { id: string; source: Source; title: string | null; url: string }[];
  cited_opportunities: { id: string; slug: string; title: string }[];
}

export interface Trend {
  cluster_id: string;
  label: string;
  canonical_statement: string;
  support_count: number;
  avg_severity: number;
  velocity: number;
  acceleration: number;
  mention_count: number;
  window_start: string;
}

export interface Report {
  id: string;
  opportunity_id: string;
  content_md: string;
  sections: Record<string, unknown>;
  model: string | null;
  created_at: string;
}

export interface Industry {
  id: string;
  slug: string;
  name: string;
}

export interface InsightCount {
  label: string;
  count: number;
}

export interface InsightDay {
  date: string;
  count: number;
}

export interface InsightsOverview {
  total_posts: number;
  posts_last_7_days: number;
  latest_collected_at: string | null;
  source_counts: InsightCount[];
  top_communities: InsightCount[];
  daily_activity: InsightDay[];
}

export interface TechPollOption {
  label: string;
  percentage: number;
  rank: number;
}

export interface TechSurvey {
  slug: string;
  publisher: string;
  title: string;
  year: number;
  sample_size: number;
  geography: string;
  field_start: string | null;
  field_end: string | null;
  source_url: string;
  methodology_url: string;
  license: string | null;
  reliability_score: number;
  bias_note: string;
}

export interface TechPoll {
  id: string;
  key: string;
  category: string;
  question: string;
  audience: string;
  response_count: number | null;
  note: string | null;
  survey: TechSurvey;
  options: TechPollOption[];
}

export interface TechPollOverview {
  total_surveys: number;
  total_respondents: number;
  categories: string[];
  polls: TechPoll[];
}

async function get<T>(path: string, revalidate = 60): Promise<T | null> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), READ_TIMEOUT_MS);
  try {
    const response = await fetch(`${API_URL}${path}`, {
      next: { revalidate },
      signal: controller.signal,
    });
    if (!response.ok) return null;
    return (await response.json()) as T;
  } catch {
    return null;
  } finally {
    clearTimeout(timeout);
  }
}

export const api = {
  opportunities: (params?: { industry?: string; cursor?: string; limit?: number }) => {
    const query = new URLSearchParams();
    if (params?.industry) query.set("industry", params.industry);
    if (params?.cursor) query.set("cursor", params.cursor);
    if (params?.limit) query.set("limit", String(params.limit));
    const suffix = query.size ? `?${query}` : "";
    return get<OpportunityPage>(`/opportunities${suffix}`);
  },

  opportunity: (slug: string) =>
    get<OpportunityDetail>(`/opportunities/${encodeURIComponent(slug)}`),

  report: (slug: string) =>
    get<Report>(`/reports/by-opportunity/${encodeURIComponent(slug)}`),

  trends: (limit = 25) => get<Trend[]>(`/trends?limit=${limit}`),

  industries: () => get<Industry[]>(`/industries`, 3600),

  insights: () => get<InsightsOverview>(`/insights/overview`, 300),

  techPolls: (category?: string) =>
    get<TechPollOverview>(
      `/tech-polls${category ? `?category=${encodeURIComponent(category)}` : ""}`,
      3600,
    ),

  search: (q: string, mode: string, filters?: { community?: string; source?: string }) => {
    const query = new URLSearchParams({ q, mode });
    if (filters?.community) query.set("community", filters.community);
    if (filters?.source) query.set("source", filters.source);
    return get<SearchResponse>(`/search?${query}`, 0);
  },

  signalPreview: () =>
    get<SearchResponse>("/search?q=manual%20workaround&mode=keyword", 300),

  chat: async (question: string): Promise<ChatResponse | null> => {
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 25_000);
    try {
      const response = await fetch(`${API_URL}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
        signal: controller.signal,
      });
      if (!response.ok) return null;
      return (await response.json()) as ChatResponse;
    } catch {
      return null;
    } finally {
      window.clearTimeout(timeout);
    }
  },
};

export const SOURCE_LABELS: Record<string, string> = {
  reddit: "Reddit",
  x: "X",
  github_issues: "GitHub Issues",
  github_discussions: "GitHub Discussions",
  hackernews: "Hacker News",
  stackoverflow: "Stack Overflow",
  lobsters: "Lobsters",
  devto: "Dev.to",
};
