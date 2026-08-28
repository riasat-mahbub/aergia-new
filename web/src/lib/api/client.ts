import axios, { type AxiosRequestConfig } from "axios";
import { useToastStore } from "../store/uiStore";
import { forgetAllKeys } from "../llm/keys";

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
        const csrfToken = readCookie("aergia_csrf");
        await axios.post(
          "/api/v1/auth/refresh",
          null,
          {
            withCredentials: true,
            headers: csrfToken ? { "X-CSRF-Token": csrfToken } : undefined,
          },
        );
        return client(originalRequest);
      } catch {
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
        forgetAllKeys();
        window.location.href = "/login";
      }
    }

    if (error.response?.status && error.response.status !== 401) {
      const detail = error.response?.data?.detail;
      const message = typeof detail === "string" && detail.length < 300
        ? detail
        : "An error occurred";
      useToastStore.getState().addToast(message, "error");
    }

    return Promise.reject(error);
  },
);

export default client;
