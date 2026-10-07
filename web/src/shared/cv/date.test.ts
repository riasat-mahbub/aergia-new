import assert from "node:assert/strict";
import test from "node:test";

import { DATE_STYLE_OPTIONS, formatDateRange } from "./date.ts";

test("date format presets separate endpoints with a spaced en dash", () => {
  assert.equal(DATE_STYLE_OPTIONS.length, 10);
  assert.ok(DATE_STYLE_OPTIONS.every((option) => option.rangeSep === " – "));
});

test("saved preset punctuation is normalized while a distinct separator is preserved", () => {
  assert.equal(
    formatDateRange("2021-03", "2022-01", false, { key: "YYYY-MM", rangeSep: "-" }),
    "2021-03 – 2022-01",
  );
  assert.equal(
    formatDateRange("2021-03", "2022-01", false, { key: "MM/YYYY", rangeSep: "/" }),
    "03/2021 – 01/2022",
  );
  assert.equal(
    formatDateRange("2021-03", "2022-01", false, { key: "MM/YYYY", rangeSep: " to " }),
    "03/2021 to 01/2022",
  );
  assert.equal(
    formatDateRange("2021-03", null, true, { key: "MM/YYYY", rangeSep: " to " }),
    "03/2021 to Present",
  );
});
