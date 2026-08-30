import { beforeEach, describe, expect, it, vi } from "vitest";

const { axiosPost, axiosClient, responseUse } = vi.hoisted(() => {
  const requestUse = vi.fn();
  const responseUse = vi.fn();
  const axiosClient = vi.fn();
  Object.assign(axiosClient, {
    interceptors: {
      request: { use: requestUse },
      response: { use: responseUse },
    },
  });
  return {
    axiosPost: vi.fn(),
    axiosClient,
    responseUse,
  };
});

vi.mock("axios", () => ({
  default: {
    create: vi.fn(() => axiosClient),
    post: axiosPost,
  },
}));

vi.mock("../../store/uiStore", () => ({
  useToastStore: { getState: vi.fn() },
}));

vi.mock("../../llm/keys", () => ({
  forgetAllKeys: vi.fn(),
}));

import { refreshSession } from "../client";

const responseError = responseUse.mock.calls[0][1] as (error: unknown) => Promise<unknown>;

describe("API client refresh", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("coalesces concurrent refresh calls", async () => {
    let resolveRefresh: (() => void) | undefined;
    axiosPost.mockReturnValueOnce(new Promise<void>((resolve) => {
      resolveRefresh = resolve;
    }));

    const first = refreshSession();
    const second = refreshSession();

    expect(first).toBe(second);
    expect(axiosPost).toHaveBeenCalledTimes(1);
    resolveRefresh?.();
    await first;
  });

  it("makes concurrent 401 retries await the same refresh", async () => {
    let resolveRefresh: (() => void) | undefined;
    axiosPost.mockReturnValueOnce(new Promise<void>((resolve) => {
      resolveRefresh = resolve;
    }));
    axiosClient.mockResolvedValue({ data: { ok: true } });

    const first = responseError({
      config: { url: "/api/v1/cvs", method: "get" },
      response: { status: 401 },
    });
    const second = responseError({
      config: { url: "/api/v1/applications", method: "get" },
      response: { status: 401 },
    });

    expect(axiosPost).toHaveBeenCalledTimes(1);
    resolveRefresh?.();
    await Promise.all([first, second]);
    expect(axiosClient).toHaveBeenCalledTimes(2);
  });
});
