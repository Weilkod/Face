import type { Metadata } from "next";
import "@/app/globals.css";

export const metadata: Metadata = {
  title: "FACEMETRICS · 관상과 운세로 보는 오늘의 승리투수",
  description: "KBO 선발 투수 매치업을 관상과 운세로 분석하는 엔터테인먼트 서비스",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ko">
      <body className="min-h-screen antialiased bg-bg text-ink">
        {children}
      </body>
    </html>
  );
}
