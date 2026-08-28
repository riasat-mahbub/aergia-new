import { describe, expect, it } from "vitest";
import type { Application } from "../../../lib/api/applications";
import { applicationMatchesSearch, isFollowUpOverdue, isFollowUpToday } from "../applicationPresentation";

const application = {
  id: "app-1",
  cv_id: null,
  company: "Example Labs",
  role: "Platform Engineer",
  job_url: null,
  job_description: "Python and FastAPI",
  notes: null,
  status: "interview",
  applied_at: "2026-01-10T00:00:00Z",
  next_follow_up_at: "2026-01-15",
  generation_status: "pending",
  generation_error: null,
  extracted_keywords: [],
  relevance: {
    score: 82,
    matched_weight: 4,
    total_weight: 5,
    matched_keywords: ["Python"],
    missing_keywords: [],
    evidence: [],
    algorithm_version: "keyword-v1",
  },
  algorithm_version: "keyword-v1",
  fits_one_page: null,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-11T00:00:00Z",
} as Application;

describe("application search", () => {
  it("supports free text and field operators", () => {
    expect(applicationMatchesSearch(application, "example python")).toBe(true);
    expect(applicationMatchesSearch(application, "company:example status:interview relevance:>=80")).toBe(true);
    expect(applicationMatchesSearch(application, "after:2026-01-01 before:2026-01-20")).toBe(true);
    expect(applicationMatchesSearch(application, "status:rejected")).toBe(false);
    expect(applicationMatchesSearch(application, "relevance:<80")).toBe(false);
  });

  it("supports follow-up buckets", () => {
    expect(applicationMatchesSearch({ ...application, next_follow_up_at: null }, "followup:none")).toBe(true);
    expect(isFollowUpOverdue("2026-01-14", new Date(2026, 0, 15))).toBe(true);
    expect(isFollowUpToday("2026-01-15", new Date(2026, 0, 15))).toBe(true);
  });
});
