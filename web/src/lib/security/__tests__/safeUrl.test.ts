import { describe, expect, it } from "vitest";

import { safeExternalUrl, safeLinkUrl } from "../safeUrl";

describe("safe URL helpers", () => {
  it("allows HTTP(S) URLs and normalizes bare hosts", () => {
    expect(safeExternalUrl("  https://example.com/jobs  ")).toBe("https://example.com/jobs");
    expect(safeExternalUrl("example.com/jobs")).toBe("https://example.com/jobs");
  });

  it.each(["javascript:alert(1)", "data:text/html,boom", "vbscript:msgbox(1)", "https://user:pass@example.com"]) (
    "rejects unsafe external URL %s",
    (value) => expect(safeExternalUrl(value)).toBeNull(),
  );

  it("allows contact schemes only through the generic link helper", () => {
    expect(safeExternalUrl("mailto:ada@example.com")).toBeNull();
    expect(safeLinkUrl("mailto:ada@example.com")).toBe("mailto:ada@example.com");
    expect(safeLinkUrl("tel:+123456789")).toBe("tel:+123456789");
  });
});
