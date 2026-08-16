import { describe, expect, it } from "vitest";
import {
  libraryKindForSectionType,
  sectionTypeForLibraryKind,
} from "../library";

describe("library section-kind mapping", () => {
  it("maps renderer section types to library kinds", () => {
    expect(libraryKindForSectionType("skills")).toBe("skill");
    expect(libraryKindForSectionType("projects")).toBe("project");
    expect(libraryKindForSectionType("languages")).toBe("language");
    expect(libraryKindForSectionType("certifications")).toBe("certification");
    expect(libraryKindForSectionType("research")).toBe("research");
  });

  it("maps library kinds to renderer section types", () => {
    expect(sectionTypeForLibraryKind("skill")).toBe("skills");
    expect(sectionTypeForLibraryKind("project")).toBe("projects");
    expect(sectionTypeForLibraryKind("language")).toBe("languages");
    expect(sectionTypeForLibraryKind("certification")).toBe("certifications");
    expect(sectionTypeForLibraryKind("research")).toBe("research");
  });
});
