import type {
  MatchupDetail,
  MatchupSummary,
  PitcherProfile,
  AccuracyStats,
  HistoryMatchup,
} from "@/types";
import {
  MOCK_MATCHUPS,
  MOCK_ACCURACY,
  MOCK_HISTORY_MATCHUPS,
} from "@/data/mockMatchups";

const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const USE_MOCK = process.env.NEXT_PUBLIC_USE_MOCK === "true" || true;

async function fetchJson<T>(path: string): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    next: { revalidate: 300 },
  });
  if (!res.ok) {
    throw new Error(`API error ${res.status}: ${path}`);
  }
  return res.json() as Promise<T>;
}

export async function getTodayMatchups(): Promise<MatchupSummary[]> {
  if (USE_MOCK) return MOCK_MATCHUPS;
  return fetchJson<MatchupSummary[]>("/api/today");
}

export async function getMatchupDetail(id: number): Promise<MatchupDetail> {
  if (USE_MOCK) {
    const found = MOCK_MATCHUPS.find((m) => m.matchup_id === id);
    if (!found) throw new Error(`Matchup ${id} not found`);
    return found;
  }
  return fetchJson<MatchupDetail>(`/api/matchup/${id}`);
}

export async function getPitcher(id: number): Promise<PitcherProfile> {
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
    return {
      ...pitcher,
      birth_date: null,
      blood_type: null,
      hand: null,
      scores,
    };
  }
  return fetchJson<PitcherProfile>(`/api/pitcher/${id}`);
}

export async function getHistory(date: string): Promise<HistoryMatchup[]> {
  if (USE_MOCK) return MOCK_HISTORY_MATCHUPS;
  return fetchJson<HistoryMatchup[]>(`/api/history?date=${date}`);
}

export async function getAccuracy(): Promise<AccuracyStats> {
  if (USE_MOCK) return MOCK_ACCURACY;
  return fetchJson<AccuracyStats>("/api/accuracy");
}
