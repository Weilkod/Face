import { NextRequest, NextResponse } from "next/server";

/**
 * Backend-for-frontend proxy.
 *
 * Forwards GET `/bff/<path>` to `${BACKEND}/api/<path>` server-side so the
 * browser never needs to know the backend URL. Using a proxy here (instead
 * of the browser hitting the backend directly via `NEXT_PUBLIC_API_URL`)
 * means the FE works even when:
 *   - `NEXT_PUBLIC_API_URL` isn't baked into the bundle (e.g. Preview
 *     deployments) — SSR used `INTERNAL_API_URL`, so the list loaded, but
 *     the browser fell back to `http://localhost:8000` and got
 *     "Failed to fetch" when expanding a card.
 *   - CORS / network-level isolation blocks the cross-origin call.
 *
 * Server-side routes (SSR, server components) still reach the backend
 * directly via `api.ts`; this proxy only handles browser-originated calls.
 */

export const dynamic = "force-dynamic";

function backendBaseUrl(): string {
  return (
    process.env.INTERNAL_API_URL ??
    process.env.NEXT_PUBLIC_API_URL ??
    "http://localhost:8000"
  );
}

export async function GET(
  request: NextRequest,
  context: { params: { path: string[] } },
): Promise<NextResponse> {
  const pathSegments = context.params.path ?? [];
  const search = request.nextUrl.search ?? "";
  const target = `${backendBaseUrl()}/api/${pathSegments.join("/")}${search}`;

  try {
    const upstream = await fetch(target, {
      headers: { accept: "application/json" },
      // Short SSR-like cache; enough for same-viewport repeat expands.
      next: { revalidate: 60 },
    });
    const body = await upstream.text();
    const contentType =
      upstream.headers.get("content-type") ?? "application/json";
    return new NextResponse(body, {
      status: upstream.status,
      headers: { "content-type": contentType },
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    return NextResponse.json(
      { detail: `bff upstream unreachable: ${message}` },
      { status: 502 },
    );
  }
}
