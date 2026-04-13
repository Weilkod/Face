"use client";

interface ScoreBarProps {
  homeScore: number;
  awayScore: number;
  maxScore?: number;
  animationDelay?: number;
}

export default function ScoreBar({
  homeScore,
  awayScore,
  maxScore = 20,
  animationDelay = 0,
}: ScoreBarProps) {
  const total = homeScore + awayScore;
  const homePct = total > 0 ? (homeScore / total) * 100 : 50;
  const awayPct = total > 0 ? (awayScore / total) * 100 : 50;

  return (
    <div className="relative h-2 overflow-hidden rounded-full bg-gray-100">
      <div
        className="bar-fill absolute left-0 top-0 h-full rounded-full bg-coral"
        style={
          {
            "--pct": `${homePct}%`,
            animationDelay: `${animationDelay}s`,
          } as React.CSSProperties
        }
      />
      <div
        className="bar-fill absolute right-0 top-0 h-full rounded-full bg-mint"
        style={
          {
            "--pct": `${awayPct}%`,
            animationDelay: `${animationDelay + 0.25}s`,
          } as React.CSSProperties
        }
      />
    </div>
  );
}

interface AxisScoreBarProps {
  homeScore: number;
  awayScore: number;
  animationDelay?: number;
}

export function AxisScoreBar({
  homeScore,
  awayScore,
  animationDelay = 0,
}: AxisScoreBarProps) {
  const pctHome = (homeScore / 20) * 100;
  const pctAway = (awayScore / 20) * 100;

  return (
    <div className="flex items-center gap-3">
      <span className="w-6 text-right text-sm font-bold text-coral">
        {homeScore}
      </span>
      <div className="relative h-2 flex-1 overflow-hidden rounded-full bg-coral-light">
        <div
          className="bar-fill h-full rounded-full bg-coral"
          style={
            {
              "--pct": `${pctHome}%`,
              animationDelay: `${animationDelay}s`,
            } as React.CSSProperties
          }
        />
      </div>
      <div className="relative h-2 flex-1 overflow-hidden rounded-full bg-mint-light">
        <div
          className="bar-fill ml-auto h-full rounded-full bg-mint"
          style={
            {
              "--pct": `${pctAway}%`,
              animationDelay: `${animationDelay + 0.2}s`,
            } as React.CSSProperties
          }
        />
      </div>
      <span className="w-6 text-sm font-bold text-mint-dark">{awayScore}</span>
    </div>
  );
}
