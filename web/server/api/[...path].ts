import { defineEventHandler, getRouterParam, proxyRequest } from "h3";

/**
 * Keep the browser on one origin while FastAPI remains a private upstream.
 * Nitro relays request cookies, CSRF headers, bodies, status codes, and
 * Set-Cookie responses without exposing the upstream origin to the client.
 */
export default defineEventHandler((event) => {
  const apiOrigin = process.env.AERGIA_API_ORIGIN ?? "http://localhost:8000";
  const path = getRouterParam(event, "path") ?? "";
  const query = event.url.search;
  return proxyRequest(event, `${apiOrigin}/api/${path}${query}`);
});
