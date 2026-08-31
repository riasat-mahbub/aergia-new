import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  cancelTailoringSession,
  createTailoringSession,
  getTailoringSessionStatus,
} from "../tailoring";

vi.mock("../client", () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

import client from "../client";

beforeEach(() => vi.clearAllMocks());

describe("tailoring API", () => {
  it("creates a prompt-bearing session through the application endpoint", async () => {
    vi.mocked(client.post).mockResolvedValue({ data: { session_id: "session-1" } } as never);

    await createTailoringSession("application-1");

    expect(client.post).toHaveBeenCalledWith("/applications/application-1/tailoring-sessions");
  });

  it("uses browser-authenticated status and cancellation endpoints", async () => {
    vi.mocked(client.get).mockResolvedValue({ data: { status: "exchanged" } } as never);
    vi.mocked(client.post).mockResolvedValue({ data: { status: "cancelled" } } as never);

    await getTailoringSessionStatus("session-1");
    await cancelTailoringSession("session-1");

    expect(client.get).toHaveBeenCalledWith("/tailoring/sessions/session-1");
    expect(client.post).toHaveBeenCalledWith("/tailoring/sessions/session-1/cancel");
  });
});
