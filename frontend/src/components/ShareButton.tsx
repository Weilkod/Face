"use client";

import { useState } from "react";
import type { MatchupSummary } from "@/types";

interface ShareButtonProps {
  summary: MatchupSummary;
}

/**
 * Builds a deep link to the @vercel/og share-card endpoint
 * (`/api/og/matchup/[id]`) with all the data needed to render the card baked
 * into the query string. We pass the data via querystring (rather than having
 * the OG route fetch from the backend) so the route stays edge-only and
 * deterministic — Vercel can cache it without a backend round-trip.
 */
export function buildShareUrl(summary: MatchupSummary): string {
  const params = new URLSearchParams({
    home: summary.home_pitcher.name,
    away: summary.away_pitcher.name,
    homeTeam: summary.home_pitcher.team,
    awayTeam: summary.away_pitcher.team,
    homeTotal: String(summary.home_total),
    awayTotal: String(summary.away_total),
  });
  if (summary.predicted_winner) params.set("winner", summary.predicted_winner);
  if (summary.stadium) params.set("stadium", summary.stadium);
  if (summary.game_time) params.set("time", summary.game_time);
  return `/api/og/matchup/${summary.matchup_id}?${params.toString()}`;
}

export default function ShareButton({ summary }: ShareButtonProps) {
  // `idle` → ready to click, `loading` → fetching the PNG bytes,
  // `done` → successful download (resets after a second), `error` → blob fetch failed.
  const [state, setState] = useState<"idle" | "loading" | "done" | "error">(
    "idle",
  );

  async function handleSave() {
    setState("loading");
    try {
      const res = await fetch(buildShareUrl(summary));
      if (!res.ok) throw new Error(`OG endpoint returned ${res.status}`);
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `facemetrics-matchup-${summary.matchup_id}.png`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      setState("done");
      setTimeout(() => setState("idle"), 1500);
    } catch (e) {
      console.error("[ShareButton] failed to download OG card", e);
      setState("error");
      setTimeout(() => setState("idle"), 2000);
    }
  }

  const label =
    state === "loading"
      ? "이미지 생성 중..."
      : state === "done"
      ? "저장 완료!"
      : state === "error"
      ? "다시 시도"
      : "공유 이미지 저장";

  return (
    <button
      type="button"
      onClick={handleSave}
      disabled={state === "loading"}
      className="mt-3 flex min-h-[44px] w-full items-center justify-center gap-2 rounded-full border border-coral/30 bg-white py-3 text-xs font-semibold text-coral transition hover:bg-coral-light disabled:cursor-wait disabled:opacity-70"
    >
      <svg
        className="h-3.5 w-3.5"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth={2.2}
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden
      >
        <path d="M4 12v7a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-7" />
        <polyline points="16 6 12 2 8 6" />
        <line x1="12" y1="2" x2="12" y2="15" />
      </svg>
      <span>{label}</span>
    </button>
  );
}
