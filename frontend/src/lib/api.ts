import type {
  MatchupDetail,
  MatchupSummary,
  PitcherDetail,
  PitcherScores,
  PitcherSummary,
  FaceScoreDetail,
  FortuneScoreDetail,
  AccuracyStats,
  HistoryMatchup,
  HistoryResponse,
} from "@/types";
import {
  MOCK_MATCHUPS,
  MOCK_ACCURACY,
  MOCK_HISTORY_MATCHUPS,
} from "@/data/mockMatchups";

const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const USE_MOCK = process.env.NEXT_PUBLIC_USE_MOCK === "true";

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

/**
 * Split a combined MatchupDetail-style PitcherScores into the face_scores +
 * today_fortune shape the real backend returns from /api/pitcher/{id}.
 *
 * Mock-only helper — the real backend already returns the split shape so
 * this has no production counterpart.
 */
function splitPitcherScoresForMock(
  pitcher: PitcherSummary,
  scores: PitcherScores,
  gameDate: string
): { face: FaceScoreDetail; fortune: FortuneScoreDetail } {
  const season = Number(gameDate.slice(0, 4));
  return {
    face: {
      season,
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
      overall_impression: `${pitcher.name}의 관상은 오늘의 매치업을 이끄는 든든한 얼굴이다`,
      analyzed_at: `${gameDate}T00:00:00`,
    },
    fortune: {
      game_date: gameDate,
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
    },
  };
}

export async function getPitcher(id: number): Promise<PitcherDetail> {
  if (USE_MOCK) {
    const matchup = MOCK_MATCHUPS.find(
      (m) =>
        m.home_pitcher.pitcher_id === id || m.away_pitcher.pitcher_id === id
    );
    if (!matchup) throw new Error(`Pitcher ${id} not found`);
    const isHome = matchup.home_pitcher.pitcher_id === id;
    const pitcher = isHome ? matchup.home_pitcher : matchup.away_pitcher;
    const scores = isHome ? matchup.home_scores : matchup.away_scores;
    const { face, fortune } = splitPitcherScoresForMock(
      pitcher,
      scores,
      matchup.game_date
    );
    return {
      ...pitcher,
      birth_date: matchup.game_date,
      blood_type: null,
      face_scores: face,
      today_fortune: fortune,
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
