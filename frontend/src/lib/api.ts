import type {
  MatchupDetail,
  MatchupSummary,
  PitcherDetail,
  FaceScoreDetail,
  FortuneScoreDetail,
  AccuracyStats,
  HistoryMatchup,
  HistoryResponse,
  TodayResponse,
} from "@/types";
import {
  MOCK_MATCHUPS,
  MOCK_ACCURACY,
  MOCK_HISTORY_MATCHUPS,
} from "@/data/mockMatchups";

// Public URL — baked at build time, used by the browser as a fallback when
// the same-origin BFF proxy isn't available (e.g. local dev mounted on a
// different port). In production (Vercel FE + Railway BE) the browser
// normally hits the `/bff/*` proxy (same origin, no CORS/env dependency).
const PUBLIC_API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// Server-side-only override. Docker Compose sets this to the backend
// service name (http://backend:8000) because `localhost` inside the FE
// container resolves to the FE container itself, not the BE. In
// non-containerised deploys this is unset and we fall through to
// PUBLIC_API_URL.
const INTERNAL_API_URL =
  process.env.INTERNAL_API_URL ?? PUBLIC_API_URL;

// Server (SSR/server components) → direct backend hit (fast, private network).
// Browser → same-origin BFF proxy (`/bff/<rest>` strips the `/api/` prefix
// the path arrives with) so we don't depend on `NEXT_PUBLIC_API_URL` being
// baked into the bundle or CORS being configured.
function resolveUrl(path: string): string {
  if (typeof window === "undefined") {
    return `${INTERNAL_API_URL}${path}`;
  }
  if (path.startsWith("/api/")) {
    return `/bff/${path.slice("/api/".length)}`;
  }
  return `${PUBLIC_API_URL}${path}`;
}

const USE_MOCK = process.env.NEXT_PUBLIC_USE_MOCK === "true";

const MOCK_SEASON = 2026;
const MOCK_GAME_DATE = "2026-04-14";
const MOCK_ANALYZED_AT = "2026-04-14T00:00:00Z";

async function fetchJson<T>(path: string): Promise<T> {
  const url = resolveUrl(path);
  let res: Response;
  try {
    res = await fetch(url, {
      next: { revalidate: 300 },
    });
  } catch (networkErr) {
    // Surface a clean message for ECONNREFUSED / fetch failed scenarios
    const detail = networkErr instanceof Error ? networkErr.message : String(networkErr);
    throw new Error(`fetch failed: ${detail}`);
  }
  if (!res.ok) {
    throw new Error(`API error ${res.status}: ${path}`);
  }
  return res.json() as Promise<T>;
}

// Classifies an error thrown by fetchJson as an API-is-down vs other error.
// Network failures and HTTP 5xx count as "down" (ErrorBanner renders a
// friendly outage message instead of leaking the raw error text).
export function isApiDownError(e: unknown): boolean {
  const msg = e instanceof Error ? e.message : String(e);
  return (
    /fetch failed|ECONNREFUSED|ENOTFOUND/.test(msg) ||
    /API error 5\d\d/.test(msg)
  );
}

export async function getTodayMatchups(): Promise<MatchupSummary[]> {
  if (USE_MOCK) return MOCK_MATCHUPS;
  const response = await fetchJson<TodayResponse>("/api/today");
  return response.matchups;
}

export async function getMatchupDetail(id: number): Promise<MatchupDetail> {
  if (USE_MOCK) {
    const found = MOCK_MATCHUPS.find((m) => m.matchup_id === id);
    if (!found) throw new Error(`Matchup ${id} not found`);
    return found;
  }
  return fetchJson<MatchupDetail>(`/api/matchup/${id}`);
}

export async function getPitcher(id: number): Promise<PitcherDetail> {
  if (USE_MOCK) {
    const matchup = MOCK_MATCHUPS.find(
      (m) =>
        m.home_pitcher.pitcher_id === id || m.away_pitcher.pitcher_id === id
    );
    if (!matchup) throw new Error(`Pitcher ${id} not found`);
    const pitcher =
      matchup.home_pitcher.pitcher_id === id
        ? matchup.home_pitcher
        : matchup.away_pitcher;
    const scores =
      matchup.home_pitcher.pitcher_id === id
        ? matchup.home_scores
        : matchup.away_scores;
    const face_scores: FaceScoreDetail = {
      season: MOCK_SEASON,
      command: scores.command.face,
      stuff: scores.stuff.face,
      composure: scores.composure.face,
      dominance: scores.dominance.face,
      destiny: scores.destiny.face,
      command_detail: scores.command.face_detail,
      stuff_detail: scores.stuff.face_detail,
      composure_detail: scores.composure.face_detail,
      dominance_detail: scores.dominance.face_detail,
      destiny_detail: scores.destiny.face_detail,
      overall_impression: null,
      analyzed_at: MOCK_ANALYZED_AT,
    };
    const today_fortune: FortuneScoreDetail = {
      game_date: MOCK_GAME_DATE,
      command: scores.command.fortune,
      stuff: scores.stuff.fortune,
      composure: scores.composure.fortune,
      dominance: scores.dominance.fortune,
      destiny: scores.destiny.fortune,
      command_reading: scores.command.fortune_reading,
      stuff_reading: scores.stuff.fortune_reading,
      composure_reading: scores.composure.fortune_reading,
      dominance_reading: scores.dominance.fortune_reading,
      destiny_reading: scores.destiny.fortune_reading,
      daily_summary: scores.daily_summary,
      lucky_inning: scores.lucky_inning,
    };
    return {
      ...pitcher,
      birth_date: null,
      blood_type: null,
      face_scores,
      today_fortune,
    };
  }
  return fetchJson<PitcherDetail>(`/api/pitcher/${id}`);
}

export async function getHistory(date: string): Promise<HistoryMatchup[]> {
  if (USE_MOCK) return MOCK_HISTORY_MATCHUPS;
  const response = await fetchJson<HistoryResponse>(`/api/history?date=${date}`);
  return response.matchups as HistoryMatchup[];
}

export async function getAccuracy(): Promise<AccuracyStats> {
  if (USE_MOCK) return MOCK_ACCURACY;
  return fetchJson<AccuracyStats>("/api/accuracy");
}
