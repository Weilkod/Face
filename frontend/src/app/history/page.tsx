import Link from "next/link";
import { getHistory, getAccuracy } from "@/lib/api";
import type { HistoryMatchup, AccuracyStats } from "@/types";
import Footer from "@/components/Footer";
import ScoreBar from "@/components/ScoreBar";
import ErrorBanner from "@/components/ErrorBanner";

interface Props {
  searchParams: { date?: string };
}

function formatDateKo(dateStr: string): string {
  const d = new Date(dateStr);
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  const days = ["일", "월", "화", "수", "목", "금", "토"];
  const day = days[d.getDay()];
  return `${d.getFullYear()}년 ${mm}월 ${dd}일 (${day})`;
}

function yesterday(): string {
  const d = new Date();
  d.setDate(d.getDate() - 1);
  return d.toISOString().split("T")[0];
}

export default async function HistoryPage({ searchParams }: Props) {
  const date = searchParams.date ?? yesterday();
  let matchups: HistoryMatchup[] = [];
  let accuracy: AccuracyStats | null = null;
  let error: string | null = null;
  let isApiDown = false;

  try {
    [matchups, accuracy] = await Promise.all([
      getHistory(date),
      getAccuracy(),
    ]);
  } catch (e) {
    const msg = e instanceof Error ? e.message : "데이터를 불러올 수 없습니다.";
    error = msg;
    isApiDown = msg.includes("fetch failed") || msg.includes("ECONNREFUSED") || msg.includes("ENOTFOUND");
  }

  const correctCount = matchups.filter((m) => m.prediction_correct).length;
  const totalWithResult = matchups.filter(
    (m) => m.actual_winner !== null
  ).length;

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

        {/* Header */}
        <div className="mb-8">
          <p className="text-sm font-medium text-coral">History</p>
          <h1 className="mt-1 text-2xl font-bold text-ink md:text-3xl">
            과거 매치업 기록
          </h1>
        </div>

        {/* Date picker */}
        <form method="GET" className="mb-8">
          <div className="flex items-center gap-3">
            <input
              type="date"
              name="date"
              defaultValue={date}
              max={new Date().toISOString().split("T")[0]}
              className="rounded-xl border border-black/10 bg-white px-4 py-2.5 text-sm text-ink shadow-sm outline-none focus:border-coral focus:ring-1 focus:ring-coral"
            />
            <button
              type="submit"
              className="min-h-[44px] rounded-xl bg-coral px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-coral-dark"
            >
              조회
            </button>
          </div>
        </form>

        {/* Accuracy stats */}
        {accuracy && (
          <div className="mb-8 grid grid-cols-2 gap-4 sm:grid-cols-4">
            <div className="card-soft rounded-2xl bg-white p-5 ring-1 ring-black/5 text-center">
              <div className="text-2xl font-bold text-coral">
                {accuracy.accuracy_rate.toFixed(1)}%
              </div>
              <div className="mt-1 text-xs text-ink-faint">누적 적중률</div>
            </div>
            <div className="card-soft rounded-2xl bg-white p-5 ring-1 ring-black/5 text-center">
              <div className="text-2xl font-bold text-ink">
                {accuracy.total_predictions}
              </div>
              <div className="mt-1 text-xs text-ink-faint">총 예측</div>
            </div>
            <div className="card-soft rounded-2xl bg-white p-5 ring-1 ring-black/5 text-center">
              <div className="text-2xl font-bold text-mint-dark">
                {accuracy.correct_predictions}
              </div>
              <div className="mt-1 text-xs text-ink-faint">적중</div>
            </div>
            {totalWithResult > 0 && (
              <div className="card-soft rounded-2xl bg-white p-5 ring-1 ring-black/5 text-center">
                <div className="text-2xl font-bold text-ink">
                  {correctCount}/{totalWithResult}
                </div>
                <div className="mt-1 text-xs text-ink-faint">
                  {formatDateKo(date).slice(0, 10)} 적중
                </div>
              </div>
            )}
          </div>
        )}

        {/* Date label */}
        <p className="mb-4 text-sm font-medium text-ink-muted">
          {formatDateKo(date)} 매치업
        </p>

        {error ? (
          <ErrorBanner message={error} isApiDown={isApiDown} />
        ) : matchups.length === 0 ? (
          <div className="rounded-2xl bg-white p-8 text-center card-soft ring-1 ring-black/5">
            <p className="text-ink-muted">해당 날짜에 경기 기록이 없습니다.</p>
          </div>
        ) : (
          <div className="grid gap-4">
            {matchups.map((matchup) => {
              const isHomeWinner = matchup.predicted_winner === matchup.home_pitcher.name;
              const isCorrect = matchup.prediction_correct;
              const hasResult = matchup.actual_winner !== null;

              return (
                <div
                  key={matchup.matchup_id}
                  className="card-soft rounded-2xl bg-white p-5 ring-1 ring-black/5"
                >
                  {/* Header row */}
                  <div className="mb-4 flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      {matchup.game_time && matchup.stadium && (
                        <span className="inline-flex items-center rounded-full bg-gray-100 px-2.5 py-0.5 text-xs font-medium text-gray-700">
                          {matchup.game_time} · {matchup.stadium}
                        </span>
                      )}
                    </div>
                    {hasResult ? (
                      <span
                        className={`inline-flex items-center gap-1 rounded-full px-3 py-1 text-xs font-semibold ${
                          isCorrect
                            ? "bg-mint-light text-mint-dark"
                            : "bg-red-50 text-red-600"
                        }`}
                      >
                        {isCorrect ? "✅ 적중" : "❌ 빗나감"}
                      </span>
                    ) : (
                      <span className="inline-flex items-center rounded-full bg-gray-100 px-3 py-1 text-xs font-medium text-gray-500">
                        결과 집계 전
                      </span>
                    )}
                  </div>

                  {/* Pitchers */}
                  <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-3">
                    <div className="flex items-center gap-2">
                      <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-xl bg-coral-light">
                        <span className="text-base font-bold text-coral">
                          {matchup.home_pitcher.name.charAt(0)}
                        </span>
                      </div>
                      <div>
                        <div className="text-[10px] text-ink-faint">
                          {matchup.home_pitcher.team}
                        </div>
                        <div className="text-base font-bold text-ink">
                          {matchup.home_pitcher.name}
                        </div>
                      </div>
                    </div>
                    <span className="text-xs font-medium text-ink-faint">
                      VS
                    </span>
                    <div className="flex items-center justify-end gap-2">
                      <div className="text-right">
                        <div className="text-[10px] text-ink-faint">
                          {matchup.away_pitcher.team}
                        </div>
                        <div className="text-base font-bold text-ink">
                          {matchup.away_pitcher.name}
                        </div>
                      </div>
                      <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-xl bg-mint-light">
                        <span className="text-base font-bold text-mint-dark">
                          {matchup.away_pitcher.name.charAt(0)}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Score bar */}
                  <div className="mt-4 flex items-center gap-3">
                    <span className="text-xl font-bold text-coral">
                      {matchup.home_total}
                    </span>
                    <div className="flex-1">
                      <ScoreBar
                        homeScore={matchup.home_total}
                        awayScore={matchup.away_total}
                      />
                    </div>
                    <span className="text-xl font-bold text-mint-dark">
                      {matchup.away_total}
                    </span>
                  </div>

                  {/* Prediction vs actual */}
                  <div className="mt-4 flex items-center justify-between border-t border-gray-100 pt-3 text-xs">
                    <span className="text-ink-faint">
                      예측:{" "}
                      <span
                        className={`font-semibold ${
                          isHomeWinner ? "text-coral" : "text-mint-dark"
                        }`}
                      >
                        ⭐ {matchup.predicted_winner} 승
                      </span>
                    </span>
                    {hasResult && (
                      <span className="text-ink-faint">
                        실제:{" "}
                        <span className="font-semibold text-ink">
                          {matchup.actual_winner} 승
                        </span>
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
      <Footer />
    </main>
  );
}
