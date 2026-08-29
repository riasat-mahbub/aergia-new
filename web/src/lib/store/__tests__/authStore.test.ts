import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("../../api/client", () => ({
  default: {
    post: vi.fn(),
    get: vi.fn(),
  },
  refreshSession: vi.fn(),
}));

import client, { refreshSession } from "../../api/client";
import { useAuthStore } from "../authStore";

const mockPost = vi.mocked(client.post);
const mockGet = vi.mocked(client.get);
const mockRefreshSession = vi.mocked(refreshSession);

describe("authStore", () => {
  beforeEach(() => {
    useAuthStore.setState({
      isAuthenticated: false,
      isLoading: false,
    });
    localStorage.clear();
    sessionStorage.clear();
    vi.clearAllMocks();
  });

  describe("login", () => {
    it("marks the session authenticated without persisting tokens", async () => {
      mockPost.mockResolvedValueOnce({ data: { message: "Logged in" } });

      await useAuthStore.getState().login("test@example.com", "password");

      expect(useAuthStore.getState().isAuthenticated).toBe(true);
      expect(localStorage.getItem("access_token")).toBeNull();
      expect(localStorage.getItem("refresh_token")).toBeNull();
      expect(mockPost).toHaveBeenCalledWith("/auth/login", { email: "test@example.com", password: "password" });
    });

    it("should throw on login failure", async () => {
      mockPost.mockRejectedValueOnce(new Error("Invalid credentials"));

      await expect(
        useAuthStore.getState().login("test@example.com", "wrong")
      ).rejects.toThrow();

      expect(useAuthStore.getState().isAuthenticated).toBe(false);
      expect(useAuthStore.getState().isLoading).toBe(false);
    });
  });

  describe("register", () => {
    it("does not authenticate after registration", async () => {
      mockPost.mockResolvedValueOnce({ data: undefined });

      await useAuthStore.getState().register("test@example.com", "password");

      expect(useAuthStore.getState().isAuthenticated).toBe(false);
    });

    it("includes the Turnstile token when provided", async () => {
      mockPost.mockResolvedValueOnce({ data: undefined });

      await useAuthStore.getState().register("test@example.com", "password", "turnstile-token");

      expect(mockPost).toHaveBeenCalledWith("/auth/register", {
        email: "test@example.com",
        password: "password",
        turnstile_token: "turnstile-token",
      });
    });

    it("should throw on register failure", async () => {
      mockPost.mockRejectedValueOnce(new Error("Email exists"));

      await expect(
        useAuthStore.getState().register("exists@example.com", "password")
      ).rejects.toThrow();
    });
  });

  describe("logout", () => {
    it("clears the in-memory session and legacy storage keys", async () => {
      useAuthStore.setState({ isAuthenticated: true });
      localStorage.setItem("access_token", "legacy-access");
      localStorage.setItem("refresh_token", "legacy-refresh");
      mockPost.mockResolvedValueOnce({ data: undefined });

      await useAuthStore.getState().logout();

      expect(useAuthStore.getState().isAuthenticated).toBe(false);
      expect(localStorage.getItem("access_token")).toBeNull();
      expect(localStorage.getItem("refresh_token")).toBeNull();
    });

    it("clears the session even if the server call fails", async () => {
      useAuthStore.setState({ isAuthenticated: true });
      mockPost.mockRejectedValueOnce(new Error("Network error"));

      await useAuthStore.getState().logout();

      expect(useAuthStore.getState().isAuthenticated).toBe(false);
    });
  });

  describe("hydrate", () => {
    it("restores auth state from the HttpOnly-cookie session check", async () => {
      localStorage.setItem("access_token", "legacy-token");
      localStorage.setItem("refresh_token", "legacy-refresh");
      mockGet.mockResolvedValueOnce({ data: { authenticated: true } });

      await useAuthStore.getState().hydrate();

      expect(useAuthStore.getState().isAuthenticated).toBe(true);
      expect(localStorage.getItem("access_token")).toBeNull();
      expect(localStorage.getItem("refresh_token")).toBeNull();
      expect(mockGet).toHaveBeenCalledWith("/auth/session");
    });

    it("sets isAuthenticated false when the cookie session is absent", async () => {
      mockGet.mockResolvedValueOnce({ data: { authenticated: false } });
      mockRefreshSession.mockRejectedValueOnce(new Error("No refresh cookie"));

      await useAuthStore.getState().hydrate();

      expect(useAuthStore.getState().isAuthenticated).toBe(false);
    });

    it("refreshes an expired access session during hydration", async () => {
      mockGet.mockResolvedValueOnce({ data: { authenticated: false } });
      mockRefreshSession.mockResolvedValueOnce();

      await useAuthStore.getState().hydrate();

      expect(useAuthStore.getState().isAuthenticated).toBe(true);
      expect(mockRefreshSession).toHaveBeenCalledTimes(1);
    });

    it("coalesces concurrent hydration calls", async () => {
      let resolveSession: ((value: { data: { authenticated: boolean } }) => void) | undefined;
      mockGet.mockReturnValueOnce(new Promise((resolve) => {
        resolveSession = resolve;
      }));

      const first = useAuthStore.getState().hydrate();
      const second = useAuthStore.getState().hydrate();

      expect(first).toBe(second);
      resolveSession?.({ data: { authenticated: true } });
      await first;
      expect(mockGet).toHaveBeenCalledTimes(1);
    });

    it("does not let stale hydration overwrite a later login", async () => {
      let resolveSession: ((value: { data: { authenticated: boolean } }) => void) | undefined;
      mockGet.mockReturnValueOnce(new Promise((resolve) => {
        resolveSession = resolve;
      }));
      const hydration = useAuthStore.getState().hydrate();
      mockPost.mockResolvedValueOnce({ data: { message: "Logged in" } });

      await useAuthStore.getState().login("test@example.com", "password");
      resolveSession?.({ data: { authenticated: false } });
      await hydration;

      expect(useAuthStore.getState().isAuthenticated).toBe(true);
    });
  });
});
