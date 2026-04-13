"use client";

interface RadarChartProps {
  homeScores: number[];
  awayScores: number[];
  homeName: string;
  awayName: string;
  homeTotal: number;
  awayTotal: number;
  animated?: boolean;
}

const LABELS = ["제구력", "구위", "멘탈", "지배력", "운명력"];
const CX = 170;
const CY = 180;
const MAX_R = 130;

function toPoint(ratio: number, index: number): [number, number] {
  const angle = ((-90 + index * 72) * Math.PI) / 180;
  const r = MAX_R * ratio;
  return [CX + r * Math.cos(angle), CY + r * Math.sin(angle)];
}

function toPoly(data: number[]): string {
  return data.map((v, i) => toPoint(v / 20, i).join(",")).join(" ");
}

export default function RadarChart({
  homeScores,
  awayScores,
  homeName,
  awayName,
  homeTotal,
  awayTotal,
  animated = true,
}: RadarChartProps) {
  const rings = [0.25, 0.5, 0.75, 1].map((rr, ri) => {
    const points = [0, 1, 2, 3, 4]
      .map((i) => toPoint(rr, i).join(","))
      .join(" ");
    return (
      <polygon
        key={ri}
        points={points}
        fill="none"
        stroke={`rgba(17,24,39,${rr === 1 ? 0.18 : 0.08})`}
        strokeWidth={1}
      />
    );
  });

  const axes = [0, 1, 2, 3, 4].map((i) => {
    const [x, y] = toPoint(1, i);
    return (
      <line
        key={i}
        x1={CX}
        y1={CY}
        x2={x}
        y2={y}
        stroke="rgba(17,24,39,0.08)"
        strokeWidth={1}
      />
    );
  });

  const labelEls = LABELS.map((label, i) => {
    const [x, y] = toPoint(1.22, i);
    const h = homeScores[i] ?? 0;
    const a = awayScores[i] ?? 0;
    return (
      <text
        key={i}
        x={x}
        y={y}
        textAnchor="middle"
        fontFamily="Pretendard Variable, Pretendard, sans-serif"
      >
        <tspan x={x} dy="-4" fontSize={12} fontWeight={600} fill="#111827">
          {label}
        </tspan>
        <tspan x={x} dy={15} fontSize={9} fontWeight={700} fill="#F26B4E">
          {h}
        </tspan>
        <tspan fontSize={9} fill="#9CA3AF">
          {" "}
          /{" "}
        </tspan>
        <tspan fontSize={9} fontWeight={700} fill="#059669">
          {a}
        </tspan>
      </text>
    );
  });

  const dotEls = LABELS.map((_, i) => {
    const [hx, hy] = toPoint((homeScores[i] ?? 0) / 20, i);
    const [ax, ay] = toPoint((awayScores[i] ?? 0) / 20, i);
    return (
      <g key={i}>
        <circle
          cx={hx}
          cy={hy}
          r={3.5}
          fill="#F26B4E"
          stroke="#ffffff"
          strokeWidth={1.5}
        />
        <circle
          cx={ax}
          cy={ay}
          r={3.5}
          fill="#059669"
          stroke="#ffffff"
          strokeWidth={1.5}
        />
      </g>
    );
  });

  return (
    <div>
      <div className="mx-auto max-w-sm">
        <svg
          viewBox="0 0 340 360"
          className={`h-full w-full${animated ? " radar-in" : ""}`}
          style={{ aspectRatio: "340/360" }}
        >
          <circle
            cx={CX}
            cy={CY}
            r={MAX_R + 10}
            fill="rgba(242,107,78,0.03)"
          />
          {rings}
          {axes}
          <polygon
            points={toPoly(awayScores)}
            fill="#059669"
            fillOpacity={0.18}
            stroke="#059669"
            strokeWidth={2}
            strokeLinejoin="round"
          />
          <polygon
            points={toPoly(homeScores)}
            fill="#F26B4E"
            fillOpacity={0.22}
            stroke="#F26B4E"
            strokeWidth={2}
            strokeLinejoin="round"
          />
          {dotEls}
          {labelEls}
        </svg>
      </div>

      <div className="mt-4 flex items-center justify-center gap-6 text-xs">
        <div className="flex items-center gap-2">
          <span className="h-2.5 w-2.5 rounded-sm bg-coral" />
          <span className="text-ink">{homeName}</span>
          <span className="font-bold text-coral">{homeTotal}</span>
        </div>
        <div className="h-3 w-px bg-black/10" />
        <div className="flex items-center gap-2">
          <span className="h-2.5 w-2.5 rounded-sm bg-mint" />
          <span className="text-ink">{awayName}</span>
          <span className="font-bold text-mint-dark">{awayTotal}</span>
        </div>
      </div>
    </div>
  );
}
