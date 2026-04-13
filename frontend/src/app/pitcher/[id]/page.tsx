import Link from "next/link";
import { getPitcher } from "@/lib/api";
import type { PitcherDetail } from "@/types";
import RadarChart from "@/components/RadarChart";
import Footer from "@/components/Footer";
import { AxisScoreBar } from "@/components/ScoreBar";

interface Props {
  params: { id: string };
}

const AXIS_META = [
  { key: "command" as const, icon: "🎯", label: "제구력", labelEn: "Command" },
  { key: "stuff" as const, icon: "💥", label: "구위", labelEn: "Stuff" },
  { key: "composure" as const, icon: "🧘", label: "멘탈", labelEn: "Composure" },
  { key: "dominance" as const, icon: "👑", label: "지배력", labelEn: "Dominance" },
  { key: "destiny" as const, icon: "✨", label: "운명력", labelEn: "Destiny" },
] as const;

type AxisKey = (typeof AXIS_META)[number]["key"];

interface AxisRow {
  key: AxisKey;
  face: number;
  fortune: number;
  total: number;
  face_detail: string | null;
  fortune_reading: string | null;
}

/**
 * Combine face_scores + today_fortune into per-axis rows for rendering.
 *
 * The backend returns face_scores (season-fixed) and today_fortune (per-game)
 * as two independent nullable blocks — see CLAUDE.md §2. We merge them here
 * into the 5-axis structure the UI needs, leaving missing values at 0.
 */
function buildAxisRows(pitcher: PitcherDetail): AxisRow[] {
  const face = pitcher.face_scores;
  const fortune = pitcher.today_fortune;
  return AXIS_META.map(({ key }) => {
    const f = face ? face[key] : 0;
    const r = fortune ? fortune[key] : 0;
    const faceDetailKey = `${key}_detail` as
      | "command_detail"
      | "stuff_detail"
      | "composure_detail"
      | "dominance_detail"
      | "destiny_detail";
    const fortuneReadingKey = `${key}_reading` as
      | "command_reading"
      | "stuff_reading"
      | "composure_reading"
      | "dominance_reading"
      | "destiny_reading";
    return {
      key,
      face: f,
      fortune: r,
      total: f + r,
      face_detail: face ? face[faceDetailKey] : null,
      fortune_reading: fortune ? fortune[fortuneReadingKey] : null,
    };
  });
}

export default async function PitcherPage({ params }: Props) {
  const pitcherId = parseInt(params.id, 10);
  let pitcher: PitcherDetail | null = null;
  let error: string | null = null;

  try {
    pitcher = await getPitcher(pitcherId);
  } catch (e) {
    error = e instanceof Error ? e.message : "투수 정보를 불러올 수 없습니다.";
  }

  const axisRows = pitcher ? buildAxisRows(pitcher) : [];
  const totalScore = axisRows.reduce((sum, a) => sum + a.total, 0);
  const hasAnyScore =
    pitcher?.face_scores != null || pitcher?.today_fortune != null;
  const todayFortune = pitcher?.today_fortune ?? null;

  return (
    <main className="min-h-screen antialiased bg-bg">
      <div className="mx-auto max-w-3xl px-4 py-8 sm:px-6">
        {/* Back navigation */}
        <Link
          href="/"
          className="mb-8 inline-flex items-center gap-2 text-xs font-medium text-ink-muted hover:text-coral transition-colors"
        >
          <svg
            className="h-3 w-3"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth={2.5}
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <polyline points="15 18 9 12 15 6" />
          </svg>
          오늘의 매치업으로 돌아가기
        </Link>

        {error || !pitcher ? (
          <div className="rounded-2xl bg-white p-8 text-center card-soft ring-1 ring-black/5">
            <p className="text-ink-muted">{error ?? "투수를 찾을 수 없습니다."}</p>
          </div>
        ) : (
          <div className="space-y-6">
            {/* Profile card */}
            <div className="card-soft rounded-2xl bg-white p-6 ring-1 ring-black/5 sm:p-8">
              <div className="flex items-start gap-4 sm:gap-5">
                <div className="flex h-16 w-16 flex-shrink-0 items-center justify-center rounded-2xl bg-coral-light sm:h-20 sm:w-20">
                  <span className="text-2xl font-bold text-coral sm:text-3xl">
                    {pitcher.name.charAt(0)}
                  </span>
                </div>
                <div className="min-w-0 flex-1">
                  <div className="text-xs text-ink-faint">{pitcher.team}</div>
                  <h1 className="mt-0.5 break-words text-2xl font-bold text-ink sm:text-3xl">
                    {pitcher.name}
                  </h1>
                  {pitcher.name_en && (
                    <div className="text-sm text-ink-muted">{pitcher.name_en}</div>
                  )}
                  <div className="mt-3 flex flex-wrap gap-2">
                    <span className="inline-flex items-center rounded-full bg-gray-100 px-3 py-1 text-xs font-medium text-gray-700">
                      {pitcher.zodiac_sign}자리 ({pitcher.zodiac_element})
                    </span>
                    <span className="inline-flex items-center rounded-full bg-gray-100 px-3 py-1 text-xs font-medium text-gray-700">
                      {pitcher.chinese_zodiac}띠
                    </span>
                    {pitcher.blood_type && (
                      <span className="inline-flex items-center rounded-full bg-gray-100 px-3 py-1 text-xs font-medium text-gray-700">
                        {pitcher.blood_type}형
                      </span>
                    )}
                    {pitcher.birth_date && (
                      <span className="inline-flex items-center rounded-full bg-gray-100 px-3 py-1 text-xs font-medium text-gray-700">
                        {pitcher.birth_date}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            </div>

            {hasAnyScore ? (
              <>
                {/* Total score */}
                <div className="card-soft rounded-2xl bg-white p-6 ring-1 ring-black/5">
                  <div className="flex items-center justify-between gap-3">
                    <div className="min-w-0">
                      <p className="text-xs font-medium text-coral">
                        오늘의 FACEMETRICS 총점
                      </p>
                      <div className="mt-1 text-4xl font-bold text-ink sm:text-5xl">
                        {totalScore}
                        <span className="ml-1 text-base font-normal text-ink-faint">
                          / 100
                        </span>
                      </div>
                    </div>
                    {todayFortune?.lucky_inning != null && (
                      <div className="text-center">
                        <p className="text-xs text-ink-faint">럭키 이닝</p>
                        <div className="mt-1 text-3xl font-bold text-coral">
                          {todayFortune.lucky_inning}
                          <span className="text-base font-normal text-ink-faint">
                            회
                          </span>
                        </div>
                      </div>
                    )}
                  </div>
                  {todayFortune?.daily_summary && (
                    <p className="mt-4 rounded-lg bg-coral-light px-4 py-3 text-sm italic text-ink-muted">
                      &ldquo;{todayFortune.daily_summary}&rdquo;
                    </p>
                  )}
                </div>

                {/* Radar chart */}
                <div className="card-soft rounded-2xl bg-white p-6 ring-1 ring-black/5">
                  <div className="mb-4 flex items-center justify-center gap-3">
                    <div className="h-px w-8 bg-coral/30" />
                    <span className="text-[11px] font-semibold uppercase tracking-[0.25em] text-coral">
                      Five Elements
                    </span>
                    <div className="h-px w-8 bg-coral/30" />
                  </div>
                  <div className="mx-auto max-w-xs">
                    <RadarChart
                      homeScores={axisRows.map((a) => a.total)}
                      awayScores={[10, 10, 10, 10, 10]}
                      homeName={pitcher.name}
                      awayName="평균"
                      homeTotal={totalScore}
                      awayTotal={50}
                      animated={false}
                    />
                  </div>
                </div>

                {/* 5-axis breakdown */}
                <div className="card-soft rounded-2xl bg-white p-6 ring-1 ring-black/5 sm:p-8">
                  <h2 className="mb-6 text-sm font-semibold text-ink">
                    관상 · 운세 상세 분석
                  </h2>
                  <div className="space-y-6">
                    {axisRows.map((row) => {
                      const meta = AXIS_META.find((m) => m.key === row.key)!;
                      return (
                        <div key={row.key}>
                          <div className="mb-3 flex items-center justify-between gap-2">
                            <div className="flex min-w-0 items-center gap-2">
                              <span>{meta.icon}</span>
                              <span className="truncate text-sm font-semibold text-ink">
                                {meta.label} · {meta.labelEn}
                              </span>
                            </div>
                            <span className="flex-shrink-0 text-sm font-bold text-coral">
                              {row.total} / 20
                            </span>
                          </div>
                          <AxisScoreBar
                            homeScore={row.total}
                            awayScore={20 - row.total}
                          />
                          <div className="mt-3 grid gap-3 text-[11px] leading-relaxed sm:grid-cols-2">
                            {row.face_detail && (
                              <div className="rounded-lg bg-coral-light p-3">
                                <p className="mb-1 font-semibold text-coral">
                                  관상 {row.face}점
                                </p>
                                <p className="text-ink-muted">
                                  {row.face_detail}
                                </p>
                              </div>
                            )}
                            {row.fortune_reading && (
                              <div className="rounded-lg bg-mint-light p-3">
                                <p className="mb-1 font-semibold text-mint-dark">
                                  오늘 운세 {row.fortune}점
                                </p>
                                <p className="text-ink-muted">
                                  {row.fortune_reading}
                                </p>
                              </div>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </>
            ) : (
              <div className="rounded-2xl bg-white p-8 text-center card-soft ring-1 ring-black/5">
                <p className="text-ink-muted">
                  오늘의 점수가 아직 집계되지 않았습니다.
                </p>
              </div>
            )}
          </div>
        )}
      </div>
      <Footer />
    </main>
  );
}
