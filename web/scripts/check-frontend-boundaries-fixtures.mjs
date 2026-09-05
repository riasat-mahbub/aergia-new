import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { collectViolations } from "./check-frontend-boundaries.mjs";

function writeFixture(files) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "aergia-boundary-"));
  const srcDir = path.join(root, "src");
  for (const [relativePath, source] of Object.entries(files)) {
    const filePath = path.join(srcDir, relativePath);
    fs.mkdirSync(path.dirname(filePath), { recursive: true });
    fs.writeFileSync(filePath, source);
  }
  return { root, srcDir };
}

function runFixture(name, files, expected) {
  const { root, srcDir } = writeFixture(files);
  try {
    const violations = collectViolations(srcDir);
    assert.equal(
      violations.some((violation) => violation.includes(expected)),
      true,
      `${name}: expected a violation containing ${expected}; got ${violations.join(" | ")}`,
    );
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
}

function runPassingFixture(name, files) {
  const { root, srcDir } = writeFixture(files);
  try {
    const violations = collectViolations(srcDir);
    assert.deepEqual(violations, [], `${name}: expected no violations; got ${violations.join(" | ")}`);
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
}

runPassingFixture("feature-public-entrypoint", {
  "routes/index.tsx": 'import { HomePage } from "@/features/home"; export default HomePage;',
  "features/home/index.ts": 'export { HomePage } from "./pages/HomePage";',
  "features/home/pages/HomePage.tsx": "export function HomePage() { return null; }",
});

runFixture(
  "shared-pure-framework",
  { "shared/cv/bad.ts": 'import { useState } from "react"; export const bad = useState;' },
  "pure shared code but imports framework/transport package",
);

runFixture(
  "shared-feature",
  {
    "features/home/index.ts": "export const home = {};",
    "shared/ui/bad.tsx": 'import { home } from "@/features/home"; export default home;',
  },
  "shared code must not import feature module features/home/index.ts",
);

runFixture(
  "route-feature-private",
  {
    "routes/index.tsx": 'import { HomePage } from "@/features/home/pages/HomePage"; export default HomePage;',
    "features/home/index.ts": 'export { HomePage } from "./pages/HomePage";',
    "features/home/pages/HomePage.tsx": "export function HomePage() { return null; }",
  },
  "must import home through its public feature entrypoint",
);

runFixture(
  "feature-cross-private",
  {
    "features/home/index.ts": 'import { Settings } from "@/features/settings/pages/SettingsPage"; export { Settings };',
    "features/settings/index.ts": 'export { Settings } from "./pages/SettingsPage";',
    "features/settings/pages/SettingsPage.tsx": "export const Settings = {};",
  },
  "must import settings through its public feature entrypoint",
);

runFixture(
  "domain-react",
  { "features/home/domain/bad.ts": 'import { useState } from "react"; export const bad = useState;' },
  "domain code must not import framework/state package",
);

runFixture(
  "domain-ui",
  {
    "features/home/domain/bad.ts": 'import Widget from "@/features/home/components/Widget"; export default Widget;',
    "features/home/components/Widget.tsx": "export default function Widget() { return null; }",
  },
  "domain code must not import UI, API, state, or route module",
);

runFixture(
  "api-state",
  {
    "features/home/api/bad.ts": 'import { useHomeStore } from "@/features/home/state/store"; export { useHomeStore };',
    "features/home/state/store.ts": "export const useHomeStore = {};",
  },
  "API code must not import UI, pages, hooks, or state module",
);

runFixture(
  "state-ui",
  {
    "features/home/state/bad.ts": 'import Widget from "@/features/home/components/Widget"; export default Widget;',
    "features/home/components/Widget.tsx": "export default function Widget() { return null; }",
  },
  "state code must not import UI module",
);

runFixture(
  "generated-direct",
  {
    "generated/schema.ts": "export interface Document {}",
    "features/home/pages/HomePage.tsx": 'import type { Document } from "@/generated/schema"; export const page = {} as Document;',
  },
  "must import generated schema types through shared/cv/schema.ts",
);

console.log("Frontend boundary fixtures passed.");
