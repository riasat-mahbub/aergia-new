import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, act } from "@testing-library/react";
import UserTemplateRenderer from "../UserTemplateRenderer";

vi.mock("../../../lib/api/client", () => ({
  default: {
    post: vi.fn().mockResolvedValue({ data: { html: "<html><body>ok</body></html>" } }),
  },
}));

import client from "../../../lib/api/client";

const mockPost = vi.mocked(client.post);

const MANIFEST = {
  manifest_version: 2,
  name: "Modern",
  zones: [{ id: "sidebar", label: null, styles: { width: "narrow" } }],
  placement: { profile: "sidebar" },
  global_styles: { accent_color: "#2563eb", body_font: "sans-serif", heading_font: "sans-serif" },
};

const INSTANCES = [{ id: "sec_profile", type: "profile", title: "Profile", enabled: true, data: {} }];

beforeEach(() => {
  mockPost.mockReset();
  mockPost.mockResolvedValue({ data: { html: "<html><body>ok</body></html>" } });
});

describe("UserTemplateRenderer — preview render payload (Phase 7 wire)", () => {
  it("passes customizations.layout through to the render endpoint verbatim", async () => {
    const customizations = {
      accent_color: "#aabbcc",
      layout: {
        zones: [{ id: "main", styles: { width: "full" } }],
        placement: { sec_profile: "main" },
      },
    };
    render(
      <UserTemplateRenderer
        instances={INSTANCES}
        manifest={MANIFEST}
        customizations={customizations}
      />
    );
    await act(async () => { await Promise.resolve(); });

    expect(mockPost).toHaveBeenCalledTimes(1);
    const [url, rawPayload] = mockPost.mock.calls[0];
    const payload = rawPayload as Record<string, any>;
    expect(url).toBe("/render/html");
    expect(payload.manifest).toEqual(MANIFEST);
    expect(payload.manifest).not.toHaveProperty("layout_config");
    expect(payload.cv_sections).toEqual(INSTANCES);
    expect(payload.customizations).toEqual(customizations);
  });

  it("sends a null manifest with the CV layout when the template manifest is unavailable", async () => {
    // Template-switch window: BuilderPage nulls templateManifest before
    // refetching. The payload must not fabricate a manifest-less object
    // that fails TemplateManifest validation.
    const customizations = {
      layout: {
        zones: [{ id: "main", styles: {} }],
        placement: { sec_profile: "main" },
      },
    };
    render(
      <UserTemplateRenderer
        instances={INSTANCES}
        customizations={customizations}
      />
    );
    await act(async () => { await Promise.resolve(); });

    expect(mockPost).toHaveBeenCalledTimes(1);
    const [, rawPayload] = mockPost.mock.calls[0];
    const payload = rawPayload as Record<string, any>;
    expect(payload.manifest).toBeNull();
    expect(payload.cv_sections).toEqual(INSTANCES);
    expect(payload.customizations.layout.placement).toEqual({ sec_profile: "main" });
  });

  it("does not call the render endpoint when customizations.layout has no zones", async () => {
    render(
      <UserTemplateRenderer
        instances={INSTANCES}
        manifest={MANIFEST}
        customizations={{}}
      />
    );
    await act(async () => { await Promise.resolve(); });

    expect(mockPost).not.toHaveBeenCalled();
  });
});
