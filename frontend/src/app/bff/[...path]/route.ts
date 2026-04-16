import { NextRequest, NextResponse } from "next/server";

// Route Segment Config — tell Next.js this handler's responses are
// cacheable for 60s at the Segment Cache layer. Whether Next.js passes
// through a browser-facing `Cache-Control` header on top of this is
// version-dependent (14.2 strips it on dynamic handlers regardless), so
// we rely on the Data Cache layer for dedup and leave browser caching
// to whatever Next.js decides.
export const revalidate = 60;

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
//
// We match on full segment equality (not substring) so a legitimate path
// segment like `photo%2e%2ejpg` — "photo..jpg" URL-encoded — doesn't
// false-positive.
function hasPathTraversal(segments: string[]): boolean {
  return segments.some((seg) => {
    if (seg === "..") return true;
    const lower = seg.toLowerCase();
    return lower === "%2e%2e";
  });
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
    // Not setting Cache-Control: verified via smoke test that Next.js
    // 14.2.3 strips it from dynamic Route Handler responses regardless
    // of how it's set (constructor headers, `response.headers.set`, or
    // `export const revalidate = 60` at segment level). Primary dedup
    // comes from the inner `fetch(…, { next: { revalidate: 60 } })`
    // Data Cache — one upstream hit per 60s across all viewers.
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
