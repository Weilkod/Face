export interface PitcherSummary {
  pitcher_id: number;
  name: string;
  name_en: string | null;
  team: string;
  chinese_zodiac: string;
  zodiac_sign: string;
  zodiac_element: string;
  profile_photo: string | null;
}

export interface AxisScore {
  face: number; // 0~10
  fortune: number; // 0~10
  total: number; // face + fortune
  face_detail: string | null;
  fortune_reading: string | null;
}

export interface PitcherScores {
  command: AxisScore;
  stuff: AxisScore;
  composure: AxisScore;
  dominance: AxisScore;
  destiny: AxisScore;
  total: number;
  lucky_inning: number | null;
  daily_summary: string | null;
}

export interface Chemistry {
  zodiac_detail: string;
  element_detail: string;
  chemistry_score: number;
  chemistry_comment: string;
}

export interface MatchupSummary {
  matchup_id: number;
  home_team: string;
  away_team: string;
  stadium: string | null;
  home_pitcher: PitcherSummary;
  away_pitcher: PitcherSummary;
  home_total: number;
  away_total: number;
  predicted_winner: string | null;
  winner_comment: string | null;
  chemistry_score: number;
}

export interface MatchupDetail extends MatchupSummary {
  game_date: string;
  home_scores: PitcherScores;
  away_scores: PitcherScores;
  chemistry: Chemistry;
}

export interface FaceScoreDetail {
  season: number;
  command: number;
  stuff: number;
  composure: number;
  dominance: number;
  destiny: number;
  command_detail: string | null;
  stuff_detail: string | null;
  composure_detail: string | null;
  dominance_detail: string | null;
  destiny_detail: string | null;
  overall_impression: string | null;
  analyzed_at: string;
}

export interface FortuneScoreDetail {
  game_date: string;
  command: number;
  stuff: number;
  composure: number;
  dominance: number;
  destiny: number;
  command_reading: string | null;
  stuff_reading: string | null;
  composure_reading: string | null;
  dominance_reading: string | null;
  destiny_reading: string | null;
  daily_summary: string | null;
  lucky_inning: number | null;
}

export interface PitcherDetail extends PitcherSummary {
  birth_date: string;
  blood_type: string | null;
  face_scores: FaceScoreDetail | null;
  today_fortune: FortuneScoreDetail | null;
}

export interface PeriodAccuracy {
  total: number;
  correct: number;
  accuracy_rate: number;
}

export interface AccuracyStats {
  total_predictions: number;
  correct_predictions: number;
  accuracy_rate: number;
  recent_7_days: PeriodAccuracy;
}

export interface HistoryMatchup extends MatchupSummary {
  game_date: string;
  actual_winner: string | null;
  prediction_correct: boolean | null;
}
