"use client";

interface ErrorBannerProps {
  message: string;
  isApiDown?: boolean;
}

/**
 * Error banner with a reload button.
 * Used on pages where server-side fetches fail (backend down, network error, etc.)
 */
export default function ErrorBanner({ message, isApiDown = false }: ErrorBannerProps) {
  return (
    <div className="rounded-2xl bg-white p-8 text-center card-soft ring-1 ring-red-200">
      <p className="text-2xl mb-3">⚠️</p>
      <p className="text-sm font-semibold text-red-600 mb-1">
        {isApiDown ? "서버 연결 실패" : "데이터 로드 오류"}
      </p>
      <p className="text-sm text-ink-muted mb-6">
        {isApiDown ? "데이터 서버에 연결할 수 없습니다." : message}
      </p>
      <button
        onClick={() => window.location.reload()}
        className="inline-flex items-center gap-2 rounded-full bg-coral px-6 py-2.5 text-sm font-semibold text-white transition hover:bg-coral/90 min-h-[44px]"
      >
        다시 시도
      </button>
      {isApiDown && (
        <p className="mt-4 text-xs text-ink-faint">
          백엔드 서버가 응답하지 않습니다. 잠시 후 다시 시도해 주세요.
        </p>
      )}
    </div>
  );
}
