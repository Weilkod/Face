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

function backendBaseUrl(): string {
  return (
    process.env.INTERNAL_API_URL ??
    process.env.NEXT_PUBLIC_API_URL ??
    "http://localhost:8000"
  );
}

// Belt-and-suspenders guard against `..` traversal. In Next.js 14.2.3 this
// is unreachable in practice — the router normalizes raw `..` before
// populating `params.path`, and URL-encoded `%2e%2e` returns its own 404
// before our handler runs. We keep the guard so a future Next.js version
// with different normalization rules can't silently turn this proxy into
// an SSRF vector. The `/api/` prefix in the target URL is separately
// hardcoded, so even without this guard an attacker can only reach paths
// under `/api/*` on the upstream.
const TRAVERSAL_PATTERNS = [/\.\./, /%2e%2e/i, /%2E%2E/];

function hasPathTraversal(segments: string[]): boolean {
  return segments.some((seg) =>
    TRAVERSAL_PATTERNS.some((re) => re.test(seg)),
  );
}

export async function GET(
  request: NextRequest,
  context: { params: { path: string[] } },
): Promise<NextResponse> {
  const pathSegments = context.params.path ?? [];
  if (hasPathTraversal(pathSegments)) {
    return NextResponse.json(
      { detail: "invalid path" },
      { status: 400 },
    );
  }

  const search = request.nextUrl.search ?? "";
  const target = `${backendBaseUrl()}/api/${pathSegments.join("/")}${search}`;

  try {
    const upstream = await fetch(target, {
      headers: { accept: "application/json" },
      // Server-side Data Cache keyed on the target URL — lets multiple
      // viewers share one upstream hit for 60s. Matches the SSR
      // `revalidate: 300` in `api.ts` order-of-magnitude; short enough
      // to pick up the 11:00 KST daily publish within one minute.
      next: { revalidate: 60 },
    });
    const body = await upstream.text();
    const contentType =
      upstream.headers.get("content-type") ?? "application/json";
    // Note: we intentionally don't set `Cache-Control` here. Next.js 14's
    // Route Handler pipeline strips custom Cache-Control from dynamic
    // handlers (we read `request.nextUrl.search`, which makes the route
    // dynamic). The primary dedup comes from the inner `fetch(…, {
    // next: { revalidate: 60 } })` call above — multiple viewers share
    // one upstream hit for 60s via Next.js's server-side Data Cache.
    // Browser-side caching is left to Next.js defaults (no explicit
    // header), which means repeat expands within the same viewport
    // round-trip to the edge — cheap relative to the upstream call.
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
