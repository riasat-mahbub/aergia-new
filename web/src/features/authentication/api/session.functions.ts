import { createServerFn } from "@tanstack/react-start";
import { getRequest, setResponseHeader } from "@tanstack/react-start/server";
import type { SessionResolveResponse } from "@/features/authentication/types";

const CSRF_COOKIE = "aergia_csrf";

function readCookie(cookieHeader: string, name: string): string | null {
  const prefix = `${name}=`;
  for (const part of cookieHeader.split(";")) {
    const value = part.trim();
    if (value.startsWith(prefix)) return decodeURIComponent(value.slice(prefix.length));
  }
  return null;
}

function setCookiesFromApi(response: Response) {
  const apiHeaders = response.headers as Headers & { getSetCookie?: () => string[] };
  const cookies = apiHeaders.getSetCookie?.() ?? [];
  if (cookies.length > 0) {
    setResponseHeader("set-cookie", cookies);
  }
}

/**
 * Resolve the browser's HttpOnly session through FastAPI during Start SSR.
 * The handler forwards only request metadata and cookies; the token values
 * stay inside the server-to-server hop and are never serialized to React.
 */
export const resolveSession = createServerFn({ method: "POST" }).handler(async () => {
  const request = getRequest();
  const cookieHeader = request.headers.get("cookie") ?? "";
  const csrfToken = readCookie(cookieHeader, CSRF_COOKIE);
  const requestOrigin = request.headers.get("origin")
    ?? process.env.AERGIA_FRONTEND_ORIGIN
    ?? "http://localhost:8000";
  const apiOrigin = process.env.AERGIA_API_ORIGIN ?? "http://localhost:8000";

  const headers = new Headers({
    accept: "application/json",
    cookie: cookieHeader,
    origin: requestOrigin,
  });
  if (csrfToken) headers.set("x-csrf-token", csrfToken);

  const response = await fetch(`${apiOrigin}/api/v1/auth/resolve`, {
    method: "POST",
    headers,
    redirect: "manual",
  });
  setCookiesFromApi(response);
  setResponseHeader("cache-control", "private, no-store");
  setResponseHeader("vary", "Cookie");

  if (!response.ok) {
    throw new Error(`FastAPI session resolution failed (${response.status})`);
  }
  return await response.json() as SessionResolveResponse;
});
