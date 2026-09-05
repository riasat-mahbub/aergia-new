import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const srcDir = path.resolve(scriptDir, "../src");
const appDir = path.join(srcDir, "app");
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

function resolveImport(importer, specifier) {
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

function relativeSourcePath(filePath) {
  return path.relative(srcDir, filePath).split(path.sep).join("/");
}

function privateOwner(filePath) {
  const relativePath = relativeSourcePath(filePath);
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

const violations = [];
for (const directory of walkDirectories(appDir)) {
  if (legacyRouteFolderNames.has(path.basename(directory))) {
    violations.push(`${relativeSourcePath(directory)} uses a legacy route folder name; use an underscore-prefixed private folder`);
  }
}

for (const importer of walk(srcDir)) {
  const importerPath = relativeSourcePath(importer);
  const source = fs.readFileSync(importer, "utf8");
  for (const specifier of importSpecifiers(source)) {
    const target = resolveImport(importer, specifier);
    if (!target) continue;
    const owner = privateOwner(target);
    if (!owner) continue;
    if (!importerPath.startsWith(`${owner}/`)) {
      violations.push(`${importerPath} imports ${relativeSourcePath(target)}, which is private to ${owner}`);
    }
  }
}

if (violations.length > 0) {
  console.error("Frontend boundary check failed:");
  for (const violation of violations) console.error(`- ${violation}`);
  process.exit(1);
}

console.log("Frontend boundary check passed: route-private modules stay within their owning app subtree.");
