import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  createApplication,
  generateApplication,
  listApplications,
  recomputeApplicationRelevance,
  updateApplication,
} from "../applications";

vi.mock("../client", () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}));

import client from "../client";

beforeEach(() => vi.clearAllMocks());

describe("applications API", () => {
  it("uses the shared client and preserves snake_case payloads", async () => {
    vi.mocked(client.get).mockResolvedValue({ data: [] } as never);
    vi.mocked(client.post).mockResolvedValue({ data: { id: "app-1" } } as never);
    vi.mocked(client.patch).mockResolvedValue({ data: { id: "app-1", status: "applied" } } as never);

    await listApplications();
    await createApplication({ company: "Acme", role: "Engineer", job_description: "Python" });
    await updateApplication("app-1", { status: "applied", applied_at: "2026-01-01T00:00:00Z" });
    await generateApplication("app-1");
    await recomputeApplicationRelevance("app-1");

    expect(client.get).toHaveBeenCalledWith("/applications");
    expect(client.post).toHaveBeenNthCalledWith(1, "/applications", { company: "Acme", role: "Engineer", job_description: "Python" });
    expect(client.patch).toHaveBeenCalledWith("/applications/app-1", { status: "applied", applied_at: "2026-01-01T00:00:00Z" });
    expect(client.post).toHaveBeenNthCalledWith(2, "/applications/app-1/generate");
    expect(client.post).toHaveBeenNthCalledWith(3, "/applications/app-1/relevance");
  });
});
