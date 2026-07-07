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
  it("sends the manifest verbatim and the CV layout via customizations, not layout_config", async () => {
    render(
      <UserTemplateRenderer
        templateId="generic-modern"
        instances={INSTANCES}
        manifest={MANIFEST}
        layoutConfig={{ zones: [{ id: "main", styles: { width: "full" } }], placement: { sec_profile: "main" } }}
        customizations={{ accent_color: "#aabbcc" }}
      />
    );
    await act(async () => { await Promise.resolve(); });

    expect(mockPost).toHaveBeenCalledTimes(1);
    const [url, rawPayload] = mockPost.mock.calls[0];
    const payload = rawPayload as Record<string, any>; // test-built object; narrow once
    expect(url).toBe("/render/html");
    expect(payload.manifest).toEqual(MANIFEST);
    expect(payload.manifest).not.toHaveProperty("layout_config");
    expect(payload.cv_sections).toEqual(INSTANCES);
    expect(payload.customizations.layout).toEqual({
      zones: [{ id: "main", styles: { width: "full" } }],
      placement: { sec_profile: "main" },
    });
    expect(payload.customizations.accent_color).toBe("#aabbcc");
  });

  it("falls back to the manifest zones when no CV layout exists", async () => {
    render(
      <UserTemplateRenderer
        templateId="generic-modern"
        instances={INSTANCES}
        manifest={MANIFEST}
        customizations={{}}
      />
    );
    await act(async () => { await Promise.resolve(); });

    expect(mockPost).toHaveBeenCalledTimes(1);
    const [, rawPayload] = mockPost.mock.calls[0];
    const payload = rawPayload as Record<string, any>; // test-built object; narrow once
    expect(payload.manifest).toEqual(MANIFEST);
    expect(payload.cv_sections).toEqual(INSTANCES);
    expect(payload.customizations.layout.zones).toEqual(MANIFEST.zones);
  });

  it("sends a null manifest with the CV layout when the template manifest is unavailable", async () => {
    // This is the template-switch window: BuilderPage nulls templateManifest
    // before refetching. The payload must not fabricate a manifest-less
    // object that fails TemplateManifest validation ("name Field required").
    render(
      <UserTemplateRenderer
        templateId="generic-classic"
        instances={INSTANCES}
        layoutConfig={{ zones: [{ id: "main", styles: {} }], placement: { sec_profile: "main" } }}
        customizations={{}}
      />
    );
    await act(async () => { await Promise.resolve(); });

    expect(mockPost).toHaveBeenCalledTimes(1);
    const [, rawPayload] = mockPost.mock.calls[0];
    const payload = rawPayload as Record<string, any>; // test-built object; narrow once
    expect(payload.manifest).toBeNull();
    expect(payload.cv_sections).toEqual(INSTANCES);
    expect(payload.customizations.layout.placement).toEqual({ sec_profile: "main" });
  });

  it("does not call the render endpoint when neither manifest nor layout has zones", async () => {
    render(
      <UserTemplateRenderer
        templateId="generic-modern"
        instances={INSTANCES}
        customizations={{}}
      />
    );
    await act(async () => { await Promise.resolve(); });

    expect(mockPost).not.toHaveBeenCalled();
  });
});
