import test from "node:test";
import assert from "node:assert/strict";

import { buildFixedPatch, parseArgs } from "../src/cli.mjs";

test("parses a session code and server options", () => {
  assert.deepEqual(
    parseArgs(["session-code", "--server", "http://localhost:8000/", "--no-submit"]),
    {
      code: "session-code",
      server: "http://localhost:8000",
      value: null,
      submit: false,
      help: false,
    },
  );
});

test("builds the fixed replacement patch from a sanitized evidence packet", () => {
  const patch = buildFixedPatch({
    cv: {
      sections: [
        { id: "profile", data: { name: "Ada" } },
        { id: "experience", data: [{ id: "entry-1", description: "Built APIs." }] },
      ],
    },
  }, "Built reliable APIs.");

  assert.deepEqual(patch, {
    protocol_version: 1,
    changes: [{
      operation: "replace_description",
      section_id: "experience",
      entry_id: "entry-1",
      value: "Built reliable APIs.",
      reason: "Fixed protocol prototype patch",
    }],
  });
});
