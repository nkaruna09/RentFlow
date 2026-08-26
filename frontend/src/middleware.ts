import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const dashboardPaths = ["/", "/properties", "/units", "/tenants", "/leases", "/payments", "/maintenance"];

export function middleware(request: NextRequest) {
  const isDashboard = dashboardPaths.some(
    (path) => request.nextUrl.pathname === path || (path !== "/" && request.nextUrl.pathname.startsWith(`${path}/`)),
  );
  if (!isDashboard) return NextResponse.next();

  const expiresAt = Number(request.cookies.get("rentflow_session")?.value);
  if (Number.isFinite(expiresAt) && expiresAt > Date.now()) return NextResponse.next();

  const loginUrl = new URL("/login", request.url);
  loginUrl.searchParams.set("next", `${request.nextUrl.pathname}${request.nextUrl.search}`);
  return NextResponse.redirect(loginUrl);
}

export const config = {
  matcher: ["/", "/properties/:path*", "/units/:path*", "/tenants/:path*", "/leases/:path*", "/payments/:path*", "/maintenance/:path*"],
};
