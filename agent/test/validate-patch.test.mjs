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

test("targets the fresh scaffold while keeping CV evidence on the source CV", () => {
  const freshEvidence = {
    ...evidence,
    supported_operations: ["replace_rich_text"],
    cv: {
      sections: [{
        id: "source-experience",
        type: "experience",
        data: [{ id: "source-entry", description: "Built API services." }],
      }],
    },
    target_cv: {
      id: "tailoring-target-session-1",
      title: "Fresh draft",
      sections: [{
        id: "target-profile",
        type: "profile",
        data: { summary: "" },
      }],
    },
  };
  const patch = {
    protocol_version: 1,
    base_revision: 3,
    base_hash: "a".repeat(64),
    changes: [{
      operation: "replace_rich_text",
      section_id: "target-profile",
      field: "summary",
      value: "Built reliable API services.",
      evidence: [{
        source: "cv",
        section_id: "source-experience",
        entry_id: "source-entry",
        field_path: "description",
      }],
    }],
  };

  assert.deepEqual(validatePatch(patch, freshEvidence), { valid: true, operation_count: 1 });
});

test("accepts a bounded web citation on a prose replacement", () => {
  const webEvidence = {
    ...evidence,
    supported_operations: ["replace_rich_text"],
  };
  const patch = {
    protocol_version: 1,
    base_revision: 3,
    base_hash: "a".repeat(64),
    changes: [{
      operation: "replace_rich_text",
      section_id: "experience",
      entry_id: "entry-1",
      field: "description",
      value: "Built Python API services.",
      evidence: [{
        source: "web",
        url: "https://example.com/technical-guide",
        title: "Technical guide",
        excerpt: "Python API services are used in this contextual example.",
      }],
    }],
  };

  assert.deepEqual(validatePatch(patch, webEvidence), { valid: true, operation_count: 1 });
});

test("validates a prose rewrite of a newly added Library row", () => {
  const libraryEvidence = {
    ...evidence,
    supported_operations: ["add_library_entry", "replace_description"],
    cv: {
      sections: [{
        id: "experience",
        type: "experience",
        data: [],
      }],
    },
    library: [{
      id: "library-1",
      kind: "experience",
      content_hash: "b".repeat(64),
      payload: [{ id: "library-row-1", description: "Built supported systems." }],
    }],
  };
  const libraryCitation = {
    source: "library",
    library_entry_id: "library-1",
    source_row_id: "library-row-1",
    source_hash: "b".repeat(64),
    field_path: "description",
  };
  const patch = {
    protocol_version: 1,
    base_revision: 3,
    base_hash: "a".repeat(64),
    changes: [
      {
        operation: "add_library_entry",
        section_id: "experience",
        entry_id: "tailored-entry-1",
        library_entry_id: "library-1",
        source_row_id: "library-row-1",
        evidence: [libraryCitation],
      },
      {
        operation: "replace_description",
        section_id: "experience",
        entry_id: "tailored-entry-1",
        value: "Built dependable platform systems.",
        evidence: [libraryCitation],
      },
    ],
  };

  assert.deepEqual(validatePatch(patch, libraryEvidence), { valid: true, operation_count: 2 });
});

test("validates auditable section creation, replacement, and ordering", () => {
  const structuralEvidence = {
    ...evidence,
    supported_operations: ["create_section", "replace_section", "reorder_sections"],
    cv: {
      sections: [{
        id: "source-experience",
        type: "experience",
        data: [{ id: "source-entry", company: "Example Labs", description: "Built APIs." }],
      }],
    },
    target_cv: {
      id: "tailoring-target-session-1",
      title: "Fresh draft",
      sections: [
        { id: "target-profile", type: "profile", data: { summary: "" } },
        { id: "target-experience", type: "experience", enabled: false, data: [] },
      ],
    },
  };
  const proof = {
    source: "cv",
    section_id: "source-experience",
    entry_id: "source-entry",
    field_path: "*",
  };
  const patch = {
    protocol_version: 1,
    base_revision: 3,
    base_hash: "a".repeat(64),
    changes: [
      {
        operation: "create_section",
        section: {
          id: "target-highlights",
          type: "extras",
          title: "Highlights",
          enabled: true,
          data: [{
            id: "highlight-1",
            title: "Selected work",
            fields: [{ label: "Evidence", value: "Built APIs." }],
          }],
        },
        reason: "Expose a concise evidence-backed highlights section.",
        evidence: [proof],
      },
      {
        operation: "replace_section",
        section_id: "target-experience",
        section: {
          id: "target-experience",
          type: "experience",
          title: "Selected Experience",
          enabled: true,
          data: [{
            id: "experience-1",
            company: "Example Labs",
            position: "Engineer",
            description: "Built APIs.",
          }],
        },
        reason: "Replace the empty scaffold with the relevant role.",
        evidence: [proof],
      },
      {
        operation: "reorder_sections",
        section_ids: ["target-profile", "target-highlights", "target-experience"],
        reason: "Place the most relevant evidence before the role details.",
        evidence: [proof],
      },
    ],
  };

  assert.deepEqual(validatePatch(patch, structuralEvidence), { valid: true, operation_count: 3 });
});

test("requires proof for broad structural changes and rejects unknown section types", () => {
  const structuralEvidence = {
    ...evidence,
    supported_operations: ["create_section"],
    target_cv: {
      id: "tailoring-target-session-1",
      title: "Fresh draft",
      sections: [{ id: "target-profile", type: "profile", data: { summary: "" } }],
    },
  };
  const base = {
    protocol_version: 1,
    base_revision: 3,
    base_hash: "a".repeat(64),
  };
  assert.throws(
    () => validatePatch({
      ...base,
      changes: [{
        operation: "create_section",
        section: { id: "new-section", type: "extras", title: "New", data: [] },
        reason: "",
        evidence: [],
      }],
    }, structuralEvidence),
    /requires a non-empty reason/,
  );
  assert.throws(
    () => validatePatch({
      ...base,
      changes: [{
        operation: "create_section",
        section: { id: "new-section", type: "awards", title: "Awards", data: [] },
        reason: "Add awards.",
        evidence: [{
          source: "cv",
          section_id: "experience",
          entry_id: "entry-1",
          field_path: "*",
        }],
      }],
    }, structuralEvidence),
    /cannot be rendered/,
  );
});
