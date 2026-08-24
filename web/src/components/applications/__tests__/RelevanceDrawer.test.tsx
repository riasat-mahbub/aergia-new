import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import RelevanceDrawer from "../RelevanceDrawer";
import type { RequirementRelevanceResult } from "../../../lib/api/applications";

const relevance: RequirementRelevanceResult = {
  status: "evaluated",
  score: 80,
  required_score: 100,
  preferred_score: 50,
  matched_weight: 4,
  total_weight: 5,
  covered_requirements: 1,
  total_requirements: 2,
  requirements: [
    {
      requirement: {
        id: "req-001",
        text: "Python",
        normalized: "python",
        canonical: "python",
        type: "hard_skill",
        required: true,
        weight: 2,
      },
      covered: true,
      score: 1,
      matched_by: ["taxonomy"],
      best_evidence: {
        section_type: "skills",
        library_entry_id: null,
        source_row_id: "cv-row",
        field_path: "sections[1].data[0].items",
        snippet: "Python",
        method: "taxonomy",
        score: 1,
      },
    },
    {
      requirement: {
        id: "req-002",
        text: "Rust",
        normalized: "rust",
        canonical: "rust",
        type: "hard_skill",
        required: false,
        weight: 1,
      },
      covered: false,
      score: 0,
      matched_by: [],
      best_evidence: null,
    },
  ],
  algorithm_version: "requirement-v1",
};

describe("RelevanceDrawer", () => {
  it("shows requirement coverage and strongest evidence", () => {
    render(<RelevanceDrawer open relevance={relevance} onClose={vi.fn()} />);

    expect(screen.getByText((_, element) => element?.textContent?.replace(/\s+/g, " ").trim() === "1 of 2 requirements covered")).toBeInTheDocument();
    expect(screen.getAllByText("Python")).not.toHaveLength(0);
    expect(screen.getByText(/skills.*sections\[1\]\.data\[0\]\.items.*taxonomy/)).toBeInTheDocument();
    expect(screen.getByText("Rust")).toBeInTheDocument();
    expect(screen.getByText("No supporting CV evidence.")).toBeInTheDocument();
  });

  it("explains that a pending result is not a zero score", () => {
    render(
      <RelevanceDrawer
        open
        relevance={{ ...relevance, status: "not_evaluated", score: null, requirements: [] }}
        onClose={vi.fn()}
      />,
    );

    expect(screen.getByText(/Generate the CV before relevance is evaluated/i)).toBeInTheDocument();
  });
});
