import Link from "next/link";
import { getPitcher } from "@/lib/api";
import type { PitcherDetail } from "@/types";
import RadarChart from "@/components/RadarChart";
import Footer from "@/components/Footer";
import { AxisScoreBar } from "@/components/ScoreBar";
import ErrorBanner from "@/components/ErrorBanner";

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

export default async function PitcherPage({ params }: Props) {
  const pitcherId = parseInt(params.id, 10);
  let pitcher: PitcherDetail | null = null;
  let error: string | null = null;
  let isApiDown = false;

  try {
    pitcher = await getPitcher(pitcherId);
  } catch (e) {
    const msg = e instanceof Error ? e.message : "투수 정보를 불러올 수 없습니다.";
    error = msg;
    isApiDown = msg.includes("fetch failed") || msg.includes("ECONNREFUSED") || msg.includes("ENOTFOUND");
  }

  const face = pitcher?.face_scores ?? null;
  const fortune = pitcher?.today_fortune ?? null;
  const axisTotals =
    face && fortune
      ? AXIS_META.map((a) => face[a.key] + fortune[a.key])
      : [];
  const grandTotal = axisTotals.reduce((s, v) => s + v, 0);

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

        {error ? (
          <ErrorBanner message={error} isApiDown={isApiDown} />
        ) : !pitcher ? (
          <div className="rounded-2xl bg-white p-8 text-center card-soft ring-1 ring-black/5">
            <p className="text-ink-muted">투수를 찾을 수 없습니다.</p>
          </div>
        ) : (
          <div className="space-y-6">
            {/* Profile card */}
            <div className="card-soft rounded-2xl bg-white p-6 ring-1 ring-black/5 sm:p-8">
              <div className="flex items-start gap-5">
                <div className="flex h-20 w-20 flex-shrink-0 items-center justify-center rounded-2xl bg-coral-light">
                  <span className="text-3xl font-bold text-coral">
                    {pitcher.name.charAt(0)}
                  </span>
                </div>
                <div className="flex-1">
                  <div className="text-xs text-ink-faint">{pitcher.team}</div>
                  <h1 className="mt-0.5 text-3xl font-bold text-ink">
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

            {face && fortune ? (
              <>
                {/* Total score */}
                <div className="card-soft rounded-2xl bg-white p-6 ring-1 ring-black/5">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-xs font-medium text-coral">
                        오늘의 FACEMETRICS 총점
                      </p>
                      <div className="mt-1 text-5xl font-bold text-ink">
                        {grandTotal}
                        <span className="ml-1 text-base font-normal text-ink-faint">
                          / 100
                        </span>
                      </div>
                    </div>
                    {fortune.lucky_inning && (
                      <div className="text-center">
                        <p className="text-xs text-ink-faint">럭키 이닝</p>
                        <div className="mt-1 text-3xl font-bold text-coral">
                          {fortune.lucky_inning}
                          <span className="text-base font-normal text-ink-faint">
                            회
                          </span>
                        </div>
                      </div>
                    )}
                  </div>
                  {fortune.daily_summary && (
                    <p className="mt-4 rounded-lg bg-coral-light px-4 py-3 text-sm italic text-ink-muted">
                      &ldquo;{fortune.daily_summary}&rdquo;
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
                      homeScores={axisTotals}
                      awayScores={[10, 10, 10, 10, 10]}
                      homeName={pitcher.name}
                      awayName="평균"
                      homeTotal={grandTotal}
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
                    {AXIS_META.map((axis) => {
                      const faceScore = face[axis.key];
                      const fortuneScore = fortune[axis.key];
                      const axisTotal = faceScore + fortuneScore;
                      const faceDetail = face[`${axis.key}_detail`];
                      const fortuneReading = fortune[`${axis.key}_reading`];
                      return (
                        <div key={axis.key}>
                          <div className="mb-3 flex items-center justify-between gap-2">
                            <div className="flex items-center gap-2">
                              <span>{axis.icon}</span>
                              <span className="text-sm font-semibold text-ink">
                                {axis.label} · {axis.labelEn}
                              </span>
                            </div>
                            <span className="text-sm font-bold text-coral">
                              {axisTotal} / 20
                            </span>
                          </div>
                          <AxisScoreBar
                            homeScore={axisTotal}
                            awayScore={20 - axisTotal}
                          />
                          <div className="mt-3 grid gap-3 text-[11px] leading-relaxed sm:grid-cols-2">
                            {faceDetail && (
                              <div className="rounded-lg bg-coral-light p-3">
                                <p className="font-semibold text-coral mb-1">
                                  관상 {faceScore}점
                                </p>
                                <p className="text-ink-muted">{faceDetail}</p>
                              </div>
                            )}
                            {fortuneReading && (
                              <div className="rounded-lg bg-mint-light p-3">
                                <p className="font-semibold text-mint-dark mb-1">
                                  오늘 운세 {fortuneScore}점
                                </p>
                                <p className="text-ink-muted">
                                  {fortuneReading}
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
