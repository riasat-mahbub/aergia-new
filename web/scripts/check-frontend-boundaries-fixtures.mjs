import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { collectViolations } from "./check-frontend-boundaries.mjs";

function runFixture(name, files, expected) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), `aergia-boundary-${name}-`));
  const srcDir = path.join(root, "src");
  try {
    for (const [relativePath, source] of Object.entries(files)) {
      const filePath = path.join(srcDir, relativePath);
      fs.mkdirSync(path.dirname(filePath), { recursive: true });
      fs.writeFileSync(filePath, source);
    }
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
  const root = fs.mkdtempSync(path.join(os.tmpdir(), `aergia-boundary-${name}-`));
  const srcDir = path.join(root, "src");
  try {
    for (const [relativePath, source] of Object.entries(files)) {
      const filePath = path.join(srcDir, relativePath);
      fs.mkdirSync(path.dirname(filePath), { recursive: true });
      fs.writeFileSync(filePath, source);
    }
    const violations = collectViolations(srcDir);
    assert.deepEqual(violations, [], `${name}: expected no violations; got ${violations.join(" | ")}`);
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
}

runFixture(
  "pure-react",
  {
    "app/page.tsx": "export default function Page() { return null; }",
    "lib/cv/bad.ts": 'import { useState } from "react"; export const bad = useState;',
  },
  "pure but imports framework/transport package",
);

runFixture(
  "contract-service",
  {
    "app/page.tsx": "export default function Page() { return null; }",
    "services/http.ts": "export const request = {};",
    "contracts/bad.ts": 'import { request } from "@/services/http"; export const bad = request;',
  },
  "contract imports services/http.ts",
);

runFixture(
  "service-store",
  {
    "app/page.tsx": "export default function Page() { return null; }",
    "store/session.ts": "export const session = {};",
    "services/bad.ts": 'import { session } from "@/store/session"; export const bad = session;',
  },
  "service imports store/session.ts",
);

runFixture(
  "shared-component-app",
  {
    "app/page.tsx": "export default function Page() { return null; }",
    "components/bad.tsx": 'import Page from "@/app/page"; export default Page;',
  },
  "shared component imports app module app/page.tsx",
);

runPassingFixture("feature-public-entrypoint", {
  "routes/index.tsx": 'import { HomePage } from "@/features/home"; export default HomePage;',
  "features/home/index.ts": 'export { HomePage } from "./pages/HomePage";',
  "features/home/pages/HomePage.tsx": "export function HomePage() { return null; }",
});

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
  "domain-react",
  {
    "features/home/domain/bad.ts": 'import { useState } from "react"; export const bad = useState;',
  },
  "domain code must not import framework/state/transport package",
);

console.log("Frontend boundary fixtures passed.");
