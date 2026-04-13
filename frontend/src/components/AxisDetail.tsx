"use client";

import type { AxisScore } from "@/types";
import { AxisScoreBar } from "./ScoreBar";

interface AxisDetailProps {
  icon: string;
  label: string;
  labelEn: string;
  homeName: string;
  awayName: string;
  home: AxisScore;
  away: AxisScore;
  animationDelay?: number;
}

export default function AxisDetail({
  icon,
  label,
  labelEn,
  homeName,
  awayName,
  home,
  away,
  animationDelay = 0,
}: AxisDetailProps) {
  return (
    <div className="rounded-xl border border-black/5 bg-white p-5">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span>{icon}</span>
          <span className="text-sm font-semibold text-ink">
            {label} · {labelEn}
          </span>
        </div>
        <div className="flex items-center gap-1.5 text-[11px] font-semibold">
          <span className="text-coral">
            ({home.total}, {homeName})
          </span>
          <span className="text-mint-dark">
            ({away.total}, {awayName})
          </span>
        </div>
      </div>

      <AxisScoreBar
        homeScore={home.total}
        awayScore={away.total}
        animationDelay={animationDelay}
      />

      <div className="mt-4 grid gap-3 text-[11px] leading-relaxed sm:grid-cols-2">
        <div className="rounded-lg bg-coral-light p-3">
          <div className="mb-2 text-[11px] font-semibold text-coral">
            {homeName}
          </div>
          {home.face_detail && (
            <p className="text-ink-muted">
              <span className="emoji">🙂</span>{" "}
              <span className="font-semibold text-coral">
                관상 {home.face} :
              </span>{" "}
              {home.face_detail}
            </p>
          )}
          {home.fortune_reading && (
            <p className="mt-1.5 text-ink-muted">
              <span className="font-semibold text-coral">
                ✨ 운세 {home.fortune} :
              </span>{" "}
              {home.fortune_reading}
            </p>
          )}
        </div>
        <div className="rounded-lg bg-mint-light p-3">
          <div className="mb-2 text-[11px] font-semibold text-mint-dark">
            {awayName}
          </div>
          {away.face_detail && (
            <p className="text-ink-muted">
              <span className="emoji">🙂</span>{" "}
              <span className="font-semibold text-mint-dark">
                관상 {away.face} :
              </span>{" "}
              {away.face_detail}
            </p>
          )}
          {away.fortune_reading && (
            <p className="mt-1.5 text-ink-muted">
              <span className="font-semibold text-mint-dark">
                ✨ 운세 {away.fortune} :
              </span>{" "}
              {away.fortune_reading}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
