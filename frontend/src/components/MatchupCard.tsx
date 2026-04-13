"use client";

import { useState } from "react";
import type { MatchupSummary, MatchupDetail } from "@/types";
import { getMatchupDetail } from "@/lib/api";
import ScoreBar from "./ScoreBar";
import RadarChart from "./RadarChart";
import AxisDetail from "./AxisDetail";
import ShareButton from "./ShareButton";

interface MatchupCardProps {
  summary: MatchupSummary;
  animationDelay?: number;
}

const AXIS_META = [
  { key: "command" as const, icon: "🎯", label: "제구력", labelEn: "Command" },
  { key: "stuff" as const, icon: "💥", label: "구위", labelEn: "Stuff" },
  { key: "composure" as const, icon: "🧘", label: "멘탈", labelEn: "Composure" },
  { key: "dominance" as const, icon: "👑", label: "지배력", labelEn: "Dominance" },
  { key: "destiny" as const, icon: "✨", label: "운명력", labelEn: "Destiny" },
] as const;

export default function MatchupCard({
  summary,
  animationDelay = 0,
}: MatchupCardProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [detail, setDetail] = useState<MatchupDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);

  const {
    matchup_id,
    home_pitcher,
    away_pitcher,
    home_total,
    away_total,
    predicted_winner,
    winner_comment,
    stadium,
    game_time,
    series_label,
  } = summary;

  async function handleExpand() {
    const next = !isOpen;
    setIsOpen(next);
    if (next && detail === null && !detailLoading) {
      setDetailLoading(true);
      setDetailError(null);
      try {
        const d = await getMatchupDetail(matchup_id);
        setDetail(d);
      } catch (e) {
        setDetailError(e instanceof Error ? e.message : "상세 정보를 불러올 수 없습니다.");
      } finally {
        setDetailLoading(false);
      }
    }
  }

  const isHomeWinner = predicted_winner === home_pitcher.name;
  const winnerTotal = isHomeWinner ? home_total : away_total;
  const loserTotal = isHomeWinner ? away_total : home_total;

  const homeInitial = home_pitcher.name.charAt(0);
  const awayInitial = away_pitcher.name.charAt(0);

  const seriesBadgeColor =
    series_label?.includes("더블") ? "bg-emerald-100 text-emerald-800"
    : series_label?.includes("개막") ? "bg-orange-100 text-orange-800"
    : "bg-blue-100 text-blue-800";

  const homeRadar = detail
    ? [
        detail.home_scores.command.total,
        detail.home_scores.stuff.total,
        detail.home_scores.composure.total,
        detail.home_scores.dominance.total,
        detail.home_scores.destiny.total,
      ]
    : null;

  const awayRadar = detail
    ? [
        detail.away_scores.command.total,
        detail.away_scores.stuff.total,
        detail.away_scores.composure.total,
        detail.away_scores.dominance.total,
        detail.away_scores.destiny.total,
      ]
    : null;

  return (
    <div
      className="fade-up"
      style={{ animationDelay: `${animationDelay}s` }}
    >
      <div className="card-soft rounded-2xl bg-white p-6 ring-1 ring-black/5 sm:p-8">

        {/* Summary row */}
        <div className="mb-6 flex items-center justify-between gap-2">
          {game_time && stadium && (
            <span className="inline-flex items-center rounded-full bg-gray-100 px-3 py-1 text-xs font-medium text-gray-700">
              {game_time} · {stadium}
            </span>
          )}
          {series_label && (
            <span
              className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-medium ${seriesBadgeColor}`}
            >
              {series_label}
            </span>
          )}
        </div>

        {/* Team vs Team */}
        <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-4">
          {/* Home pitcher */}
          <div className="flex items-center gap-3">
            <div className="flex h-14 w-14 flex-shrink-0 items-center justify-center rounded-2xl bg-coral-light">
              <span className="text-xl font-bold text-coral">{homeInitial}</span>
            </div>
            <div>
              <div className="text-[11px] text-ink-faint">{home_pitcher.team}</div>
              <div className="text-xl font-bold text-ink">{home_pitcher.name}</div>
              <div className="mt-0.5 text-[11px] text-ink-muted">
                ♟ {home_pitcher.zodiac_sign} · {home_pitcher.chinese_zodiac}띠
              </div>
            </div>
          </div>

          <span className="text-xs font-medium text-ink-faint">VS</span>

          {/* Away pitcher */}
          <div className="flex items-center justify-end gap-3">
            <div className="text-right">
              <div className="text-[11px] text-ink-faint">{away_pitcher.team}</div>
              <div className="text-xl font-bold text-ink">{away_pitcher.name}</div>
              <div className="mt-0.5 text-[11px] text-ink-muted">
                ♟ {away_pitcher.zodiac_sign} · {away_pitcher.chinese_zodiac}띠
              </div>
            </div>
            <div className="flex h-14 w-14 flex-shrink-0 items-center justify-center rounded-2xl bg-mint-light">
              <span className="text-xl font-bold text-mint-dark">{awayInitial}</span>
            </div>
          </div>
        </div>

        {/* Total score bar */}
        <div className="mt-6 flex items-center justify-between gap-4">
          <div className="flex items-baseline gap-1">
            <span className="text-4xl font-bold text-coral">{home_total}</span>
            <span className="text-xs text-ink-faint">점</span>
          </div>
          <div className="flex-1">
            <ScoreBar homeScore={home_total} awayScore={away_total} />
          </div>
          <div className="flex items-baseline gap-1">
            <span className="text-xs text-ink-faint">점</span>
            <span className="text-4xl font-bold text-mint-dark">{away_total}</span>
          </div>
        </div>

        {/* Prediction label */}
        <div className="mt-5 flex items-center justify-between border-t border-gray-100 pt-4">
          <span className="text-xs text-ink-muted">오늘의 FACEMETRICS 예측</span>
          <span
            className={`text-sm font-semibold ${
              isHomeWinner ? "text-coral" : "text-mint-dark"
            }`}
          >
            ⭐ {predicted_winner} 승
          </span>
        </div>

        {/* Expand button */}
        <button
          onClick={handleExpand}
          className="mt-4 flex min-h-[44px] w-full items-center justify-center gap-2 rounded-full bg-coral-light py-3 text-xs font-semibold text-coral transition hover:bg-coral/15"
          aria-expanded={isOpen}
        >
          <span>{isOpen ? "접기" : "FACEMETRICS 상세"}</span>
          <svg
            className={`h-3 w-3 transition-transform duration-300 ${isOpen ? "rotate-180" : ""}`}
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth={2.5}
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <polyline points="6 9 12 15 18 9" />
          </svg>
        </button>

        {/* Share card download (uses /api/og/matchup/[id] @vercel/og endpoint) */}
        <ShareButton summary={summary} />

        {/* Expanded detail */}
        {isOpen && (
          <div className="mt-8 space-y-8">

            {/* Loading state */}
            {detailLoading && (
              <div className="flex items-center justify-center py-12">
                <div className="h-8 w-8 animate-spin rounded-full border-2 border-coral border-t-transparent" />
              </div>
            )}

            {/* Error state */}
            {detailError && (
              <div className="rounded-2xl bg-red-50 p-6 text-center text-sm text-red-600">
                {detailError}
              </div>
            )}

            {/* Detail content */}
            {detail && homeRadar && awayRadar && (
              <>
                {/* Radar chart */}
                <div className="rounded-2xl border border-black/5 bg-gray-50 p-6">
                  <div className="mb-4 flex items-center justify-center gap-3">
                    <div className="h-px w-8 bg-coral/30" />
                    <span className="text-[11px] font-semibold uppercase tracking-[0.25em] text-coral">
                      Five Elements
                    </span>
                    <div className="h-px w-8 bg-coral/30" />
                  </div>
                  <RadarChart
                    homeScores={homeRadar}
                    awayScores={awayRadar}
                    homeName={home_pitcher.name}
                    awayName={away_pitcher.name}
                    homeTotal={home_total}
                    awayTotal={away_total}
                    animated={true}
                  />
                </div>

                {/* 5-axis detail blocks */}
                <div className="space-y-4">
                  {AXIS_META.map((axis, i) => (
                    <AxisDetail
                      key={axis.key}
                      icon={axis.icon}
                      label={axis.label}
                      labelEn={axis.labelEn}
                      homeName={home_pitcher.name}
                      awayName={away_pitcher.name}
                      home={detail.home_scores[axis.key]}
                      away={detail.away_scores[axis.key]}
                      animationDelay={i * 0.05}
                    />
                  ))}
                </div>

                {/* Chemistry analysis */}
                {detail.chemistry && (
                  <div className="rounded-2xl border border-coral/20 bg-coral-light p-6">
                    <div className="mb-3 flex items-center gap-2">
                      <span>⚔️</span>
                      <span className="text-[11px] font-semibold uppercase tracking-wider text-coral">
                        상성 분석 · Chemistry
                      </span>
                    </div>
                    <p className="text-sm leading-relaxed text-ink-muted">
                      <span className="font-semibold text-ink">띠:</span>{" "}
                      {detail.chemistry.zodiac_detail}
                    </p>
                    <p className="mt-1 text-sm leading-relaxed text-ink-muted">
                      <span className="font-semibold text-ink">원소:</span>{" "}
                      {detail.chemistry.element_detail}
                    </p>
                    <p className="mt-3 text-xs italic text-ink-faint">
                      {detail.chemistry.chemistry_comment}
                    </p>
                  </div>
                )}

                {/* Winner card */}
                <div className="stripes rounded-2xl bg-coral p-10 text-center">
                  <div className="relative">
                    <div className="mb-4 text-[11px] font-semibold uppercase tracking-[0.4em] text-white/80">
                      오늘의 FACEMETRICS 승자
                    </div>
                    <div className="flex items-center justify-center gap-4">
                      <span className="text-2xl">⭐</span>
                      <h3 className="text-4xl font-bold text-white sm:text-5xl">
                        {predicted_winner}
                      </h3>
                      <span className="text-2xl">⭐</span>
                    </div>
                    <div className="mt-3 flex items-center justify-center gap-3 text-xl font-bold">
                      <span className="text-white">{winnerTotal}</span>
                      <span className="text-base font-medium text-white/70">vs</span>
                      <span className="text-white/80">{loserTotal}</span>
                    </div>
                    {winner_comment && (
                      <p className="mx-auto mt-5 max-w-sm text-sm italic text-white/90">
                        &ldquo;{winner_comment}&rdquo;
                      </p>
                    )}
                    <div className="mt-8 flex items-center justify-center gap-6 text-[11px] font-medium text-white/80">
                      {detail.home_scores.lucky_inning != null && (
                        <div className="flex items-center gap-2">
                          <span>🎰</span>
                          <span>
                            {home_pitcher.name} · {detail.home_scores.lucky_inning}회
                          </span>
                        </div>
                      )}
                      {detail.home_scores.lucky_inning != null &&
                        detail.away_scores.lucky_inning != null && (
                          <span className="h-1 w-1 rounded-full bg-white/50" />
                        )}
                      {detail.away_scores.lucky_inning != null && (
                        <div className="flex items-center gap-2">
                          <span>🎰</span>
                          <span>
                            {away_pitcher.name} · {detail.away_scores.lucky_inning}회
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
