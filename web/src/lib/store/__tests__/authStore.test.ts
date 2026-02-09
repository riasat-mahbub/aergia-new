import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("../../api/client", () => ({
  default: {
    post: vi.fn(),
  },
}));

import client from "../../api/client";
import { useAuthStore } from "../authStore";

const mockClient = vi.mocked(client.post);

describe("authStore", () => {
  beforeEach(() => {
    useAuthStore.setState({
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
      isLoading: false,
    });
    localStorage.clear();
    vi.clearAllMocks();
  });

  describe("login", () => {
    it("should set tokens and isAuthenticated on success", async () => {
      mockClient.mockResolvedValueOnce({
        data: { access_token: "abc", refresh_token: "def", token_type: "bearer" },
      });

      await useAuthStore.getState().login("test@example.com", "password");

      const state = useAuthStore.getState();
      expect(state.accessToken).toBe("abc");
      expect(state.refreshToken).toBe("def");
      expect(state.isAuthenticated).toBe(true);
      expect(localStorage.getItem("access_token")).toBe("abc");
      expect(localStorage.getItem("refresh_token")).toBe("def");
    });

    it("should throw on login failure", async () => {
      mockClient.mockRejectedValueOnce(new Error("Invalid credentials"));

      await expect(
        useAuthStore.getState().login("test@example.com", "wrong")
      ).rejects.toThrow();

      const state = useAuthStore.getState();
      expect(state.isAuthenticated).toBe(false);
      expect(state.isLoading).toBe(false);
    });
  });

  describe("register", () => {
    it("should not set tokens on register", async () => {
      mockClient.mockResolvedValueOnce({ data: undefined });

      await useAuthStore.getState().register("test@example.com", "password");

      const state = useAuthStore.getState();
      expect(state.accessToken).toBeNull();
      expect(state.isAuthenticated).toBe(false);
    });

    it("should throw on register failure", async () => {
      mockClient.mockRejectedValueOnce(new Error("Email exists"));

      await expect(
        useAuthStore.getState().register("exists@example.com", "password")
      ).rejects.toThrow();
    });
  });

  describe("logout", () => {
    it("should clear tokens and set isAuthenticated false", async () => {
      useAuthStore.setState({
        accessToken: "abc",
        refreshToken: "def",
        isAuthenticated: true,
      });
      localStorage.setItem("access_token", "abc");
      localStorage.setItem("refresh_token", "def");

      mockClient.mockResolvedValueOnce({ data: undefined });

      await useAuthStore.getState().logout();

      const state = useAuthStore.getState();
      expect(state.accessToken).toBeNull();
      expect(state.refreshToken).toBeNull();
      expect(state.isAuthenticated).toBe(false);
      expect(localStorage.getItem("access_token")).toBeNull();
      expect(localStorage.getItem("refresh_token")).toBeNull();
    });

    it("should clear tokens even if server call fails", async () => {
      useAuthStore.setState({
        accessToken: "abc",
        refreshToken: "def",
        isAuthenticated: true,
      });
      localStorage.setItem("access_token", "abc");

      mockClient.mockRejectedValueOnce(new Error("Network error"));

      await useAuthStore.getState().logout();

      const state = useAuthStore.getState();
      expect(state.accessToken).toBeNull();
      expect(state.isAuthenticated).toBe(false);
    });
  });

  describe("hydrate", () => {
    it("should restore auth state from localStorage", () => {
      localStorage.setItem("access_token", "stored_token");
      localStorage.setItem("refresh_token", "stored_refresh");

      useAuthStore.getState().hydrate();

      const state = useAuthStore.getState();
      expect(state.accessToken).toBe("stored_token");
      expect(state.refreshToken).toBe("stored_refresh");
      expect(state.isAuthenticated).toBe(true);
    });

    it("should set isAuthenticated false when no token", () => {
      useAuthStore.getState().hydrate();

      const state = useAuthStore.getState();
      expect(state.isAuthenticated).toBe(false);
    });
  });
});
