// scan-text.mjs — the provider-agnostic gate (ADR-0004). Affinity must not name any specific course, exam,
// or standards body: committed text says "beginning chemistry / first-year college and advanced high-school
// chemistry." This greps every committed text file for banned terms and FAILS THE BUILD on a hit, so the
// constraint is enforced, not merely a convention. The gitignored brief and JD.md are not part of the shipped
// artifact and are not scanned. This file excludes itself, since it necessarily lists the terms.
//
// The list is SEEDED FROM THE SIBLING (ADR-0004) — the generic exam-board terms. Extend it when the owner
// confirms the specific board mapping (which lives only in the private brief).

import { readdirSync, statSync, readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve, relative, join } from "node:path";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..", "..");
const SELF = resolve(dirname(fileURLToPath(import.meta.url)), "scan-text.mjs");

// "Big Idea" only as the proper-noun framework — case-sensitive, so it does not flag ordinary prose.
// Bare "AP" is case-sensitive uppercase with word boundaries.
const BANNED = [
  { re: /\bAdvanced Placement\b/i, label: "Advanced Placement" },
  { re: /\bCollege Board\b/i, label: "College Board" },
  { re: /\bBig Idea(?:s| \d)\b/, label: "Big Idea framework" },
  { re: /\bAP\b/, label: "bare 'AP'" },
];

const SCAN_EXT = new Set([
  ".md", ".markdown", ".toml", ".json", ".astro", ".svelte", ".js", ".mjs", ".cjs",
  ".ts", ".tsx", ".css", ".html", ".txt", ".yml", ".yaml", ".py",
]);
const SKIP_DIRS = new Set([
  "node_modules", ".git", "dist", ".astro", ".vite", ".venv", "__pycache__",
  ".pytest_cache", ".tmp.driveupload", ".tmp.drivedownload", ".claude",
]);
// Gitignored internal docs (never published) legitimately hold course-framed material and are not scanned.
const SKIP_FILES = new Set([
  resolve(ROOT, "package-lock.json"),
  resolve(ROOT, "JD.md"),
  resolve(ROOT, "PROJECT_BRIEF.md"),
  SELF,
]);

function walk(dir) {
  const out = [];
  for (const name of readdirSync(dir)) {
    if (SKIP_DIRS.has(name)) continue;
    const p = join(dir, name);
    const st = statSync(p);
    if (st.isDirectory()) out.push(...walk(p));
    else if (SCAN_EXT.has(name.slice(name.lastIndexOf("."))) && !SKIP_FILES.has(p)) out.push(p);
  }
  return out;
}

const hits = [];
for (const file of walk(ROOT)) {
  const rel = relative(ROOT, file).replace(/\\/g, "/");
  const lines = readFileSync(file, "utf8").split(/\r?\n/);
  lines.forEach((line, i) => {
    for (const { re, label } of BANNED) {
      if (re.test(line)) hits.push(`${rel}:${i + 1}  [${label}]  ${line.trim().slice(0, 100)}`);
    }
  });
}

if (hits.length) {
  console.error(`\nPROVIDER-AGNOSTIC SCAN FAILED (${hits.length} banned-term hit(s)):`);
  for (const h of hits) console.error("  - " + h);
  console.error("\nAffinity ships provider-agnostic. Use 'beginning chemistry' and topic names, not board/exam names.");
  process.exit(1);
}
console.log("scan-text: OK — no banned course/exam/standards-body terms found.");
