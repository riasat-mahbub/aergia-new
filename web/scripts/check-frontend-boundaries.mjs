import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const defaultSrcDir = path.resolve(scriptDir, "../src");
const sourceExtensions = new Set([".js", ".jsx", ".ts", ".tsx"]);
const privateFolderNames = new Set([
  "_components",
  "_constants",
  "_hooks",
  "_lib",
  "_services",
  "_stores",
  "_types",
]);
const legacyRouteFolderNames = new Set([
  "components",
  "constants",
  "hooks",
  "lib",
  "services",
  "stores",
  "types",
  "providers",
]);

// These directories contain behavior that must remain framework- and
// transport-independent. `lib/browser` is intentionally excluded because it
// is an explicit DOM adapter rather than a pure utility.
const pureLibPrefixes = [
  "lib/cv/",
  "lib/library/",
  "lib/llm/",
  "lib/rich-text/",
  "lib/security/",
  "lib/validators/",
];

function walk(directory) {
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

function walkDirectories(directory) {
  const entries = fs.readdirSync(directory, { withFileTypes: true });
  const directories = [];
  for (const entry of entries) {
    if (entry.name === "node_modules" || entry.name === "dist" || entry.name.startsWith(".")) continue;
    if (!entry.isDirectory()) continue;
    const entryPath = path.join(directory, entry.name);
    directories.push(entryPath, ...walkDirectories(entryPath));
  }
  return directories;
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

function privateOwner(filePath, srcDir) {
  const relativePath = relativeSourcePath(filePath, srcDir);
  const segments = relativePath.split("/");
  if (segments[0] !== "app") return null;
  const privateIndex = segments.findIndex((segment) => privateFolderNames.has(segment));
  if (privateIndex < 0) return null;
  return segments.slice(0, privateIndex).join("/");
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

function isPureLib(relativePath) {
  return pureLibPrefixes.some((prefix) => relativePath.startsWith(prefix));
}

function isPathIn(relativePath, prefix) {
  return relativePath === prefix || relativePath.startsWith(`${prefix}/`);
}

function isReactOrStatePackage(specifier) {
  return ["react", "react-dom", "react-router-dom", "zustand", "axios"].some(
    (prefix) => specifier === prefix || specifier.startsWith(`${prefix}/`),
  );
}

function dependencyViolations(importerPath, targetPath, specifier, source) {
  const violations = [];
  const importerIsPure = isPureLib(importerPath);

  if (importerIsPure) {
    if (isReactOrStatePackage(specifier)) {
      violations.push(`${importerPath} is pure but imports framework/transport package ${specifier}`);
    }
  }
  if (!targetPath) return violations;

  const targetIsApp = isPathIn(targetPath, "app");
  const targetIsComponents = isPathIn(targetPath, "components");
  const targetIsStore = isPathIn(targetPath, "store");
  const targetIsServices = isPathIn(targetPath, "services");

  if (importerIsPure) {
    if (targetIsApp || targetIsComponents || targetIsStore || targetIsServices) {
      violations.push(`${importerPath} is pure but imports ${targetPath}`);
    }
  }

  if (importerPath.startsWith("contracts/") && (targetIsApp || targetIsComponents || targetIsStore || targetIsServices)) {
    violations.push(`${importerPath} contract imports ${targetPath}`);
  }
  if (importerPath.startsWith("services/") && (targetIsApp || targetIsComponents || targetIsStore)) {
    violations.push(`${importerPath} service imports ${targetPath}`);
  }
  if (importerPath.startsWith("store/") && (targetIsApp || targetIsComponents)) {
    violations.push(`${importerPath} store imports ${targetPath}`);
  }
  if (importerPath.startsWith("components/") && targetIsApp) {
    violations.push(`${importerPath} shared component imports app module ${targetPath}`);
  }

  return violations;
}

export function collectViolations(srcDir = defaultSrcDir) {
  const appDir = path.join(srcDir, "app");
  const violations = [];

  for (const directory of walkDirectories(appDir)) {
    if (legacyRouteFolderNames.has(path.basename(directory))) {
      violations.push(`${relativeSourcePath(directory, srcDir)} uses a legacy route folder name; use an underscore-prefixed private folder`);
    }
  }

  for (const importer of walk(srcDir)) {
    const importerPath = relativeSourcePath(importer, srcDir);
    const source = fs.readFileSync(importer, "utf8");
    if (isPureLib(importerPath) && /\b(?:window|document|navigator)\s*(?:[.[]|\()/u.test(source)) {
      violations.push(`${importerPath} is pure but reaches browser globals`);
    }
    for (const specifier of importSpecifiers(source)) {
      const target = resolveImport(importer, specifier, srcDir);
      const targetPath = target ? relativeSourcePath(target, srcDir) : null;
      violations.push(...dependencyViolations(importerPath, targetPath, specifier, source));
      if (!target) continue;
      const owner = privateOwner(target, srcDir);
      if (owner && !importerPath.startsWith(`${owner}/`)) {
        violations.push(`${importerPath} imports ${targetPath}, which is private to ${owner}`);
      }
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
  console.log("Frontend boundary check passed: route privacy and layer direction are valid.");
}
