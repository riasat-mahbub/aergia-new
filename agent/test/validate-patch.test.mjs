import test from "node:test";
import assert from "node:assert/strict";

import { validatePatch } from "../tools/validate-patch.mjs";

const evidence = {
  protocol_version: 1,
  base_revision: 3,
  base_hash: "a".repeat(64),
  supported_operations: ["replace_description", "report_gap"],
  cv: {
    sections: [
      {
        id: "experience",
        data: [{ id: "entry-1", description: "Built APIs." }],
      },
    ],
  },
  library: [],
};

test("validates a patch against the exchanged evidence snapshot", () => {
  assert.deepEqual(
    validatePatch(
      {
        protocol_version: 1,
        base_revision: 3,
        base_hash: "a".repeat(64),
        changes: [{
          operation: "replace_description",
          section_id: "experience",
          entry_id: "entry-1",
          value: "Built dependable APIs.",
        }],
      },
      evidence,
    ),
    { valid: true, operation_count: 1 },
  );
});
test("rejects an operation that the server did not advertise", () => {
  assert.throws(
    () => validatePatch(
      {
        protocol_version: 1,
        base_revision: 3,
        base_hash: "a".repeat(64),
        changes: [{ operation: "remove_entry", section_id: "experience", entry_id: "entry-1" }],
      },
      evidence,
    ),
    /not advertised/,
  );
});

test("validates profile rich-text targets without an entry ID", () => {
  const profileEvidence = {
    ...evidence,
    supported_operations: ["replace_rich_text"],
    cv: {
      sections: [{
        id: "profile",
        type: "profile",
        data: { summary: "Reliable engineer." },
      }],
    },
  };
  const patch = {
    protocol_version: 1,
    base_revision: 3,
    base_hash: "a".repeat(64),
    changes: [{
      operation: "replace_rich_text",
      section_id: "profile",
      field: "summary",
      value: "Reliable platform engineer.",
    }],
  };

  assert.deepEqual(validatePatch(patch, profileEvidence), { valid: true, operation_count: 1 });
});
