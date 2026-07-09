// scan-text.mjs — the provider-agnostic gate (ADR-0004). Affinity must not name any specific course, exam,
// or standards body: committed text says "beginning chemistry / first-year college and advanced high-school
// chemistry." This greps every committed text file for banned terms and FAILS THE BUILD on a hit, so the
// constraint is enforced, not merely a convention. The gitignored brief and JD.md are not part of the shipped
// artifact and are not scanned. This file excludes itself, since it necessarily lists the terms.
//
// The list started SEEDED FROM THE SIBLING (ADR-0004), then broadened at v1.0.0 (ADR-0053, review item B10) to
// the ADR-0004 policy in full: ANY specific course, exam, board, or standards body — the major English-language
// families (the UK upper-secondary + general-certificate qualifications and their awarding bodies, the
// international diploma programme, the US science-standards framework, the Scottish + vocational qualifications).
// Two rules keep it safe: (1) each literal is split with a single-character class (e.g. `G[C]SE`) so THIS source
// file never carries a contiguous banned term — defence in depth, since it also excludes itself from the scan;
// (2) short acronyms match uppercase-only and word-bounded, so ordinary prose ("a lab", "cap"), an `ib` loop
// variable, or a Roman-numeral group tag cannot false-positive. The specific mapping still lives only in the brief.

import { readdirSync, statSync, readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve, relative, join } from "node:path";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..", "..");
const SELF = resolve(dirname(fileURLToPath(import.meta.url)), "scan-text.mjs");

// "Big Idea" only as the proper-noun framework — case-sensitive, so it does not flag ordinary prose.
// Bare "AP" is case-sensitive uppercase with word boundaries.
const BANNED = [
  // Sibling-seeded set (ADR-0004).
  { re: /\bAdvanced Placement\b/i, label: "Advanced Placement" },
  { re: /\bCollege Board\b/i, label: "College Board" },
  { re: /\bBig Idea(?:s| \d)\b/, label: "Big Idea framework" },
  { re: /\bAP\b/, label: "bare 'AP'" },
  // v1.0.0 breadth (ADR-0053 / B10) — literals split with a char class; short acronyms uppercase-only + \b.
  { re: /\bAS?-[Ll]evels?\b/, label: "UK upper-secondary qualification" },
  { re: /\bO-[Ll]evels?\b/, label: "UK ordinary-level qualification" },
  { re: /\bI?G[C]SEs?\b/, label: "UK general-secondary certificate" },
  { re: /\bBacca[l]aureate\b/i, label: "international diploma programme" },
  { re: /\bIB\b/, label: "international diploma programme (acronym)" },
  { re: /\bNG[S]S\b/, label: "US science-standards framework" },
  { re: /\bA[Q]A\b/, label: "UK exam board" },
  { re: /\bOC[R]\b/, label: "UK exam board" },
  { re: /\bEde[x]cel\b/i, label: "UK/Pearson exam board" },
  { re: /\bWJ[E]C\b/, label: "Welsh exam board" },
  { re: /\bCC[E]A\b/, label: "Northern Ireland exam board" },
  { re: /\bEdu[q]as\b/i, label: "UK exam-board brand" },
  { re: /\bCA[I]E\b/, label: "international assessment board" },
  { re: /\bS[Q]A\b/, label: "Scottish qualifications body" },
  { re: /\bBT[E]C\b/, label: "UK vocational qualification" },
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
