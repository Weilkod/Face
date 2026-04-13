import { ImageResponse } from "@vercel/og";
import type { NextRequest } from "next/server";

// Edge runtime is required for @vercel/og — Satori + resvg.wasm don't run in
// the Node serverless runtime by default. This also keeps the share-card
// endpoint cheap to invoke from social-media crawlers and from in-app
// "save image" buttons.
export const runtime = "edge";

// Standard OG dimensions — Twitter/X, KakaoTalk, Facebook all expect 1200x630.
const WIDTH = 1200;
const HEIGHT = 630;

// Tailwind tokens hard-coded — Satori does not understand Tailwind class
// strings, only inline `style` props. Keep these in sync with
// `frontend/tailwind.config.ts` `colors` section.
const COLOR = {
  bg: "#f7f7f7",
  card: "#ffffff",
  coral: "#F26B4E",
  coralLight: "#FEF3F0",
  mint: "#059669",
  mintLight: "#D1FAE5",
  ink: "#111827",
  inkMuted: "#6B7280",
  inkFaint: "#9CA3AF",
} as const;

// All query params are optional; when missing we render a friendly
// placeholder so accidental hits never produce a 500.
function param(req: NextRequest, key: string, fallback: string = ""): string {
  return req.nextUrl.searchParams.get(key) ?? fallback;
}

function paramInt(req: NextRequest, key: string, fallback: number): number {
  const raw = req.nextUrl.searchParams.get(key);
  if (raw == null) return fallback;
  const n = Number.parseInt(raw, 10);
  return Number.isFinite(n) ? n : fallback;
}

export async function GET(
  req: NextRequest,
  { params }: { params: { id: string } },
) {
  // Query params drive the card. We accept everything from the URL so the
  // route stays a pure function of (id, querystring) and Vercel can edge-cache
  // it aggressively without ever hitting the backend.
  const matchupId = params.id;
  const homeName = param(req, "home", "투수 A");
  const awayName = param(req, "away", "투수 B");
  const homeTeam = param(req, "homeTeam", "");
  const awayTeam = param(req, "awayTeam", "");
  const homeTotal = paramInt(req, "homeTotal", 0);
  const awayTotal = paramInt(req, "awayTotal", 0);
  const winner = param(req, "winner", "");
  const stadium = param(req, "stadium", "");
  const gameTime = param(req, "time", "");

  const isHomeWinner = winner === homeName;
  const winnerColor = isHomeWinner ? COLOR.coral : COLOR.mint;

  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          backgroundColor: COLOR.bg,
          padding: 56,
          fontFamily: "sans-serif",
        }}
      >
        {/* Header */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            marginBottom: 28,
          }}
        >
          <div style={{ display: "flex", flexDirection: "column" }}>
            <span
              style={{
                fontSize: 22,
                color: COLOR.coral,
                letterSpacing: 4,
                fontWeight: 600,
              }}
            >
              FACEMETRICS
            </span>
            <span style={{ fontSize: 18, color: COLOR.inkMuted, marginTop: 4 }}>
              관상과 운세로 보는 오늘의 승리투수
            </span>
          </div>
          {(stadium || gameTime) && (
            <div
              style={{
                display: "flex",
                fontSize: 18,
                color: COLOR.inkMuted,
                backgroundColor: "#ffffff",
                borderRadius: 999,
                padding: "10px 22px",
              }}
            >
              {[gameTime, stadium].filter(Boolean).join(" · ")}
            </div>
          )}
        </div>

        {/* Match card */}
        <div
          style={{
            flex: 1,
            display: "flex",
            flexDirection: "column",
            backgroundColor: COLOR.card,
            borderRadius: 32,
            padding: 48,
            boxShadow: "0 8px 32px rgba(17,24,39,0.06)",
          }}
        >
          {/* Pitcher row */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
            }}
          >
            {/* Home */}
            <div
              style={{
                flex: 1,
                display: "flex",
                alignItems: "center",
                gap: 24,
              }}
            >
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  width: 96,
                  height: 96,
                  borderRadius: 24,
                  backgroundColor: COLOR.coralLight,
                  fontSize: 48,
                  fontWeight: 700,
                  color: COLOR.coral,
                }}
              >
                {homeName.charAt(0) || "?"}
              </div>
              <div style={{ display: "flex", flexDirection: "column" }}>
                {homeTeam && (
                  <span style={{ fontSize: 18, color: COLOR.inkFaint }}>
                    {homeTeam}
                  </span>
                )}
                <span
                  style={{
                    fontSize: 44,
                    fontWeight: 700,
                    color: COLOR.ink,
                    marginTop: 2,
                  }}
                >
                  {homeName}
                </span>
              </div>
            </div>

            {/* VS */}
            <div
              style={{
                display: "flex",
                fontSize: 24,
                color: COLOR.inkFaint,
                fontWeight: 600,
                margin: "0 24px",
              }}
            >
              VS
            </div>

            {/* Away */}
            <div
              style={{
                flex: 1,
                display: "flex",
                alignItems: "center",
                justifyContent: "flex-end",
                gap: 24,
              }}
            >
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "flex-end",
                }}
              >
                {awayTeam && (
                  <span style={{ fontSize: 18, color: COLOR.inkFaint }}>
                    {awayTeam}
                  </span>
                )}
                <span
                  style={{
                    fontSize: 44,
                    fontWeight: 700,
                    color: COLOR.ink,
                    marginTop: 2,
                  }}
                >
                  {awayName}
                </span>
              </div>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  width: 96,
                  height: 96,
                  borderRadius: 24,
                  backgroundColor: COLOR.mintLight,
                  fontSize: 48,
                  fontWeight: 700,
                  color: COLOR.mint,
                }}
              >
                {awayName.charAt(0) || "?"}
              </div>
            </div>
          </div>

          {/* Score row */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 32,
              marginTop: 56,
            }}
          >
            <span
              style={{
                fontSize: 120,
                fontWeight: 800,
                color: COLOR.coral,
                lineHeight: 1,
              }}
            >
              {homeTotal}
            </span>
            <span
              style={{
                fontSize: 36,
                color: COLOR.inkFaint,
                fontWeight: 500,
              }}
            >
              :
            </span>
            <span
              style={{
                fontSize: 120,
                fontWeight: 800,
                color: COLOR.mint,
                lineHeight: 1,
              }}
            >
              {awayTotal}
            </span>
          </div>

          {/* Winner pill */}
          {winner && (
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                marginTop: 32,
              }}
            >
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 12,
                  backgroundColor: winnerColor,
                  color: "#ffffff",
                  borderRadius: 999,
                  padding: "16px 36px",
                  fontSize: 26,
                  fontWeight: 700,
                }}
              >
                <span>★</span>
                <span>오늘의 FACEMETRICS 승자 · {winner}</span>
              </div>
            </div>
          )}
        </div>

        {/* Footer / disclaimer */}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            marginTop: 24,
            fontSize: 16,
            color: COLOR.inkFaint,
          }}
        >
          <span>matchup #{matchupId}</span>
          <span>엔터테인먼트 목적 · 베팅과 무관</span>
        </div>
      </div>
    ),
    {
      width: WIDTH,
      height: HEIGHT,
      // Cache aggressively at the edge: the card is a deterministic function
      // of the URL, and matchup totals are frozen by the 11:00 KST publish
      // job, so a 1-hour s-maxage is safe.
      headers: {
        "cache-control": "public, max-age=60, s-maxage=3600, stale-while-revalidate=86400",
      },
    },
  );
}
