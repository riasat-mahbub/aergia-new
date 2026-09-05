import { existsSync, readFileSync, unlinkSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";

// TanStack Start's Nitro handler renders every application route. Vite still
// emits a client index shell, but serving that file at `/` would bypass the
// Start SSR handler and skip request-scoped auth resolution.
const shellPath = resolve(process.cwd(), ".output/public/index.html");
if (existsSync(shellPath)) unlinkSync(shellPath);

// Nitro embeds a public-asset manifest in its generated server entry. Remove
// the shell there too, otherwise the static middleware still wins `/` and
// attempts to read the deleted file before the Start route handler runs.
const serverEntryPath = resolve(process.cwd(), ".output/server/index.mjs");
if (existsSync(serverEntryPath)) {
  const serverEntry = readFileSync(serverEntryPath, "utf8");
  const marker = '\t"/index.html": {';
  const start = serverEntry.indexOf(marker);
  if (start >= 0) {
    const end = serverEntry.indexOf("\n\t},", start);
    if (end >= 0) {
      writeFileSync(serverEntryPath, `${serverEntry.slice(0, start)}${serverEntry.slice(end + 4)}`);
    }
  }
}
