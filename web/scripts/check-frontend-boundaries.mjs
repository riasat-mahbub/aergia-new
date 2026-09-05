import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const defaultSrcDir = path.resolve(scriptDir, "../src");
const sourceExtensions = new Set([".js", ".jsx", ".ts", ".tsx"]);

// These shared modules contain framework-independent logic. Browser adapters,
// UI components, and React hooks intentionally live outside this list.
const pureSharedPrefixes = [
  "shared/cv/",
  "shared/rich-text/",
  "shared/security/",
];

function walk(directory) {
  if (!fs.existsSync(directory)) return [];
  const entries = fs.readdirSync(directory, { withFileTypes: true });
  const files = [];
  for (const entry of entries) {
    if (entry.name === "node_modules" || entry.name === "dist" || entry.name.startsWith(".")) continue;
    const entryPath = path.join(directory, entry.name);
    if (entry.isDirectory()) {
      files.push(...walk(entryPath));
    } else if (sourceExtensions.has(path.extname(entry.name)) && !entry.name.endsWith(".d.ts")) {
      files.push(entryPath);
    }
  }
  return files;
}

function resolveImport(importer, specifier, srcDir) {
  let candidate;
  if (specifier.startsWith("@/")) {
    candidate = path.join(srcDir, specifier.slice(2));
  } else if (specifier.startsWith(".")) {
    candidate = path.resolve(path.dirname(importer), specifier);
  } else {
    return null;
  }

  const candidates = [candidate];
  for (const extension of sourceExtensions) candidates.push(`${candidate}${extension}`);
  for (const extension of sourceExtensions) candidates.push(path.join(candidate, `index${extension}`));
  return candidates.find((filePath) => fs.existsSync(filePath) && fs.statSync(filePath).isFile()) ?? null;
}

function relativeSourcePath(filePath, srcDir) {
  return path.relative(srcDir, filePath).split(path.sep).join("/");
}

function featureOwner(filePath) {
  const segments = filePath.split("/");
  return segments[0] === "features" && segments[1] ? segments[1] : null;
}

function featureBoundary(filePath) {
  const segments = filePath.split("/");
  return segments[0] === "features" && segments[2] ? segments[2] : null;
}

function isFeaturePublicEntry(filePath, owner) {
  return filePath === `features/${owner}/index.ts` || filePath === `features/${owner}/index.tsx`;
}

function isPathIn(relativePath, prefix) {
  return relativePath === prefix || relativePath.startsWith(`${prefix}/`);
}

function isPureShared(relativePath) {
  return pureSharedPrefixes.some((prefix) => relativePath.startsWith(prefix));
}

function importSpecifiers(source) {
  const specifiers = new Set();
  const patterns = [
    /\bfrom\s*["']([^"']+)["']/g,
    /\bimport\s*["']([^"']+)["']/g,
    /\bimport\s*\(\s*["']([^"']+)["']\s*\)/g,
  ];
  for (const pattern of patterns) {
    for (const match of source.matchAll(pattern)) specifiers.add(match[1]);
  }
  return specifiers;
}

function isFrameworkPackage(specifier) {
  return ["react", "react-dom", "react-router-dom", "zustand"].some(
    (prefix) => specifier === prefix || specifier.startsWith(`${prefix}/`),
  );
}

function dependencyViolations(importerPath, targetPath, specifier) {
  const violations = [];
  const importerFeature = featureOwner(importerPath);
  const targetFeature = targetPath ? featureOwner(targetPath) : null;
  const importerBoundary = featureBoundary(importerPath);
  const importerIsRoute = isPathIn(importerPath, "routes");
  const importerIsShared = isPathIn(importerPath, "shared");
  const importerIsPureShared = isPureShared(importerPath);

  if (importerIsPureShared && (isFrameworkPackage(specifier) || specifier === "axios")) {
    violations.push(`${importerPath} is pure shared code but imports framework/transport package ${specifier}`);
  }
  if (specifier === "axios" && importerPath !== "shared/api/client.ts") {
    violations.push(`${importerPath} must use the shared API client instead of configuring axios directly`);
  }
  if (importerBoundary === "domain" && isFrameworkPackage(specifier)) {
    violations.push(`${importerPath} domain code must not import framework/state package ${specifier}`);
  }
  if (!targetPath) return violations;

  const targetIsRoutes = isPathIn(targetPath, "routes");
  const targetIsFeatures = isPathIn(targetPath, "features");

  if (targetIsFeatures) {
    const isPublicEntry = targetFeature && isFeaturePublicEntry(targetPath, targetFeature);
    if ((importerIsRoute || (importerFeature && importerFeature !== targetFeature)) && !isPublicEntry) {
      violations.push(`${importerPath} must import ${targetFeature} through its public feature entrypoint`);
    }
    if (importerIsShared) {
      violations.push(`${importerPath} shared code must not import feature module ${targetPath}`);
    }
  }
  if ((importerIsShared || importerIsRoute || importerFeature) && targetIsRoutes) {
    violations.push(`${importerPath} must not import route module ${targetPath}`);
  }
  if (targetPath === "generated/schema.ts" && importerPath !== "shared/cv/schema.ts") {
    violations.push(`${importerPath} must import generated schema types through shared/cv/schema.ts`);
  }

  if (importerBoundary === "domain") {
    if (
      isPathIn(targetPath, "routes") ||
      isPathIn(targetPath, "shared/ui") ||
      isPathIn(targetPath, "shared/cv-editor") ||
      ["components", "pages", "hooks", "api", "state"].includes(featureBoundary(targetPath))
    ) {
      violations.push(`${importerPath} domain code must not import UI, API, state, or route module ${targetPath}`);
    }
  }
  if (importerBoundary === "api") {
    if (["components", "pages", "hooks", "state"].includes(featureBoundary(targetPath))) {
      violations.push(`${importerPath} API code must not import UI, pages, hooks, or state module ${targetPath}`);
    }
    if (isPathIn(targetPath, "shared/ui") || isPathIn(targetPath, "shared/cv-editor")) {
      violations.push(`${importerPath} API code must not import UI module ${targetPath}`);
    }
  }
  if (importerBoundary === "state") {
    if (["components", "pages"].includes(featureBoundary(targetPath))) {
      violations.push(`${importerPath} state code must not import UI module ${targetPath}`);
    }
    if (isPathIn(targetPath, "shared/ui") || isPathIn(targetPath, "shared/cv-editor")) {
      violations.push(`${importerPath} state code must not import UI module ${targetPath}`);
    }
  }

  return violations;
}

export function collectViolations(srcDir = defaultSrcDir) {
  const violations = [];
  for (const legacyRoot of ["app", "components", "contracts", "lib", "services", "store"]) {
    if (fs.existsSync(path.join(srcDir, legacyRoot))) {
      violations.push(`web/src/${legacyRoot} must not exist; move code to features or shared`);
    }
  }

  for (const importer of walk(srcDir)) {
    const importerPath = relativeSourcePath(importer, srcDir);
    const source = fs.readFileSync(importer, "utf8");
    if (featureOwner(importerPath) && importerPath.endsWith("/index.ts") && /export\s+\*\s+from/u.test(source)) {
      violations.push(`${importerPath} must use explicit public exports instead of export *`);
    }
    if (isPureShared(importerPath) && /\b(?:window|document|navigator)\s*(?:[.[]|\()/u.test(source)) {
      violations.push(`${importerPath} is pure shared code but reaches browser globals`);
    }
    if (featureBoundary(importerPath) === "domain" && /\b(?:window|document|navigator)\s*(?:[.[]|\()/u.test(source)) {
      violations.push(`${importerPath} domain code must not reach browser globals`);
    }
    for (const specifier of importSpecifiers(source)) {
      const target = resolveImport(importer, specifier, srcDir);
      const targetPath = target ? relativeSourcePath(target, srcDir) : null;
      violations.push(...dependencyViolations(importerPath, targetPath, specifier));
    }
  }

  return violations;
}

if (process.argv[1] && path.resolve(process.argv[1]) === path.resolve(fileURLToPath(import.meta.url))) {
  const violations = collectViolations();
  if (violations.length > 0) {
    console.error("Frontend boundary check failed:");
    for (const violation of violations) console.error(`- ${violation}`);
    process.exit(1);
  }
  console.log("Frontend boundary check passed: routes, features, and shared layers are valid.");
}
