import axios, { type AxiosRequestConfig } from "axios";

const client = axios.create({
  baseURL: "/api/v1",
  headers: { "Content-Type": "application/json" },
  withCredentials: true,
});

function readCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const prefix = `${encodeURIComponent(name)}=`;
  const cookie = document.cookie.split("; ").find((entry) => entry.startsWith(prefix));
  return cookie ? decodeURIComponent(cookie.slice(prefix.length)) : null;
}

function hasMutatingMethod(method: string | undefined): boolean {
  return method !== undefined && ["post", "put", "patch", "delete"].includes(method.toLowerCase());
}

let refreshPromise: Promise<void> | null = null;
let apiErrorHandler: ((message: string) => void) | null = null;
let unauthorizedHandler: (() => void) | null = null;

/**
 * Register an application-level error reporter without coupling the HTTP
 * client to a particular UI or state library. The returned disposer is safe
 * to call when the provider unmounts.
 */
export function setApiErrorHandler(handler: ((message: string) => void) | null): () => void {
  apiErrorHandler = handler;
  return () => {
    if (apiErrorHandler === handler) apiErrorHandler = null;
  };
}

/** Register the app-owned response to an unrecoverable authenticated request. */
export function setUnauthorizedHandler(handler: (() => void) | null): () => void {
  unauthorizedHandler = handler;
  return () => {
    if (unauthorizedHandler === handler) unauthorizedHandler = null;
  };
}

export function refreshSession(): Promise<void> {
  if (refreshPromise) return refreshPromise;

  const csrfToken = readCookie("aergia_csrf");
  refreshPromise = axios.post(
    "/api/v1/auth/refresh",
    null,
    {
      withCredentials: true,
      headers: csrfToken ? { "X-CSRF-Token": csrfToken } : undefined,
    },
  ).then(() => undefined).finally(() => {
    refreshPromise = null;
  });
  return refreshPromise;
}

client.interceptors.request.use((config) => {
  if (hasMutatingMethod(config.method)) {
    const csrfToken = readCookie("aergia_csrf");
    if (csrfToken) {
      config.headers.set("X-CSRF-Token", csrfToken);
    }
  }
  return config;
});

client.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config as (AxiosRequestConfig & { _retry?: boolean }) | undefined;
    const requestUrl = originalRequest?.url || "";
    const isAuthRequest = requestUrl.includes("/auth/login")
      || requestUrl.includes("/auth/refresh")
      || requestUrl.includes("/auth/session");

    if (error.response?.status === 401 && originalRequest && !originalRequest._retry && !isAuthRequest) {
      originalRequest._retry = true;
      try {
        await refreshSession();
        return client(originalRequest);
      } catch {
        unauthorizedHandler?.();
      }
    }

    if (error.response?.status && error.response.status !== 401) {
      const detail = error.response?.data?.detail;
      const message = typeof detail === "string" && detail.length < 300
        ? detail
        : "An error occurred";
      apiErrorHandler?.(message);
    }

    return Promise.reject(error);
  },
);

export default client;
