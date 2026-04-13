import Image from "next/image";
import Link from "next/link";
import { getTodayMatchups } from "@/lib/api";
import type { MatchupSummary } from "@/types";
import MatchupCard from "@/components/MatchupCard";
import Footer from "@/components/Footer";

function formatDateKo(dateStr: string): string {
  const d = new Date(dateStr);
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  const days = ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"];
  const day = days[d.getDay()];
  return `${mm} / ${dd} · ${day}`;
}

export default async function TodayMatchupsPage() {
  let matchups: MatchupSummary[] = [];
  let error: string | null = null;

  try {
    matchups = await getTodayMatchups();
  } catch (e) {
    error = e instanceof Error ? e.message : "데이터를 불러올 수 없습니다.";
  }

  const today = formatDateKo(new Date().toISOString().split("T")[0]);

  return (
    <main className="min-h-screen antialiased bg-bg">
      {/* Hero */}
      <section className="flex min-h-[60vh] items-center justify-center bg-bg">
        <div className="mx-auto w-full max-w-3xl px-4 text-center sm:px-6">
          <Image
            src="/header_image.png"
            alt="FACEMETRICS"
            width={480}
            height={180}
            className="mx-auto mb-6 w-full max-w-md"
            priority
          />
          <p className="mb-0.5 text-xs font-light text-ink-muted md:text-base">
            KBO · 2026 · SEASON
          </p>
          <h1
            className="text-[3.15rem] font-bold tracking-tight text-[#0A192F] md:text-[4.2rem]"
          >
            FACEMETRICS
          </h1>
          <p className="mt-3 text-lg text-ink-muted md:text-xl">
            관상과 운세로 보는 오늘의 승리투수
          </p>
          <p className="mt-5 text-base italic text-[#B8860B]">
            &ldquo;확률이 반반이면 관상이 답이다&rdquo;
          </p>
          <nav className="mt-8 flex items-center justify-center gap-6 text-xs text-ink-muted">
            <Link href="/" className="hover:text-coral transition-colors">
              오늘의 매치업
            </Link>
            <Link href="/history" className="hover:text-coral transition-colors">
              히스토리
            </Link>
          </nav>
        </div>
      </section>

      {/* Matchup list */}
      <section className="bg-bg pb-24">
        <div className="mx-auto max-w-3xl px-4 sm:px-6">
          <div className="mb-8 flex items-end justify-between">
            <div>
              <p className="text-sm font-medium text-coral">
                Today&apos;s Matchups
              </p>
              <h2 className="mt-1 text-2xl font-bold text-ink md:text-3xl">
                오늘의 매치업
              </h2>
            </div>
            <span className="text-xs text-ink-faint">{today}</span>
          </div>

          {error ? (
            <div className="rounded-2xl bg-white p-8 text-center card-soft ring-1 ring-black/5">
              <p className="text-ink-muted">{error}</p>
            </div>
          ) : matchups.length === 0 ? (
            <div className="rounded-2xl bg-white p-8 text-center card-soft ring-1 ring-black/5">
              <p className="text-ink-muted">
                오늘 예정된 매치업이 없습니다.
              </p>
            </div>
          ) : (
            <div className="grid gap-6">
              {matchups.map((matchup, i) => (
                <MatchupCard
                  key={matchup.matchup_id}
                  summary={matchup}
                  animationDelay={i * 0.1}
                />
              ))}
            </div>
          )}
        </div>
      </section>

      <Footer />
    </main>
  );
}
