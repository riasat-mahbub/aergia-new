import test from "node:test";
import assert from "node:assert/strict";

import { checkJobDescription } from "../tools/jd-check.mjs";
import { verifyFacts } from "../tools/verify-cv-facts.mjs";

test("JD check separates supported skills from gaps and exposes inconclusive state", () => {
  const result = checkJobDescription(
    { description: "Requirements\nPython and Kubernetes experience required" },
    { sections: [{ data: [{ description: "Built Python services." }] }] },
    [],
  );

  assert.equal(result.inconclusive, false);
  assert.deepEqual(
    result.requirements.map((requirement) => [requirement.requirement, requirement.supportedByResume, requirement.gap]),
    [["kubernetes", false, true], ["python", true, false]],
  );
});
test("fact check rejects a new unsupported numeric claim", () => {
  const result = verifyFacts(
    { sections: [{ data: [{ description: "Improved API performance." }] }] },
    { sections: [{ data: [{ description: "Improved API performance by 47%." }] }] },
    { cv: { sections: [{ data: [{ description: "Improved API performance." }] }] }, library: [] },
    { changes: [{ operation: "rewrite_rich_text", evidence: [] }] },
  );

  assert.equal(result.status, "fail");
  assert.equal(result.findings[0].value, "47%");
});

test("fact check does not borrow a number from another CV entry", () => {
  const before = {
    sections: [{
      id: "experience",
      type: "experience",
      data: [
        { id: "job-a", description: "Improved API performance." },
        { id: "job-b", description: "Reduced latency by 32%." },
      ],
    }],
  };
  const after = {
    sections: [{
      id: "experience",
      type: "experience",
      data: [
        { id: "job-a", description: "Improved API performance by 32%." },
        { id: "job-b", description: "Reduced latency by 32%." },
      ],
    }],
  };
  const result = verifyFacts(
    before,
    after,
    { cv: before, library: [] },
    { changes: [{ operation: "replace_description", section_id: "experience", entry_id: "job-a" }] },
  );

  assert.equal(result.status, "fail");
  assert.equal(result.findings[0].value, "32%");
});
