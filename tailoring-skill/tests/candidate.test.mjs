import test from "node:test";
import assert from "node:assert/strict";

import {
  materializeCandidate,
  validateCandidate,
} from "../skills/aergia-tailor/scripts/validate-candidate.mjs";

const context = {
  protocol_version: 2,
  templates: [{ id: "generic-minimal", manifest: {} }],
};

const candidate = {
  title: "Platform Engineer",
  template_id: "generic-minimal",
  sections: [{
    id: "profile",
    type: "profile",
    title: "Profile",
    enabled: true,
    data: { name: "Ada", summary: "Platform engineer" },
    style: { subsection: { text_align: "left" } },
  }],
  customizations: { spacing: "compact" },
};

test("validates a complete candidate and preserves customization data", () => {
  assert.deepEqual(validateCandidate(candidate, context), { valid: true, section_count: 1 });
  assert.deepEqual(materializeCandidate(candidate), candidate);
});

test("rejects a candidate with an unavailable template or duplicate section", () => {
  assert.throws(() => validateCandidate({ ...candidate, template_id: "unknown" }, context), /template/);
  assert.throws(() => validateCandidate({ ...candidate, sections: [candidate.sections[0], candidate.sections[0]] }, context), /unique/);
});

test("requires exactly one enabled profile section", () => {
  assert.throws(() => validateCandidate({ ...candidate, sections: [] }, context), /sections/);
  assert.throws(() => validateCandidate({ ...candidate, sections: [{ ...candidate.sections[0], enabled: false }] }, context), /profile/);
});

test("materialization gives new rich-text blocks stable IDs without changing claims", () => {
  const raw = {
    ...candidate,
    sections: [{
      ...candidate.sections[0],
      data: {
        ...candidate.sections[0].data,
        summary: [{ type: "bullet_list", items: [{ text: "Built a platform" }] }],
      },
    }],
  };

  const first = materializeCandidate(raw);
  const second = materializeCandidate(raw);
  assert.deepEqual(first, second);
  assert.equal(first.sections[0].data.summary[0].id, second.sections[0].data.summary[0].id);
  assert.equal(first.sections[0].data.summary[0].items[0].id, second.sections[0].data.summary[0].items[0].id);
  assert.equal(first.sections[0].data.summary[0].items[0].text, "Built a platform");
  assert.equal(raw.sections[0].data.summary[0].id, undefined);
});
