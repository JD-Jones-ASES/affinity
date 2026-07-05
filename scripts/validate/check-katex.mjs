// check-katex.mjs — every LaTeX string in the committed solutions must render through KaTeX (ADR-0008). The
// build-time renderer (src/lib/katex.js) uses throwOnError:false so a bad string would silently ship as an
// error node; this gate renders every string with throwOnError:true and FAILS THE BUILD on any that don't,
// so a survived string is known-good. Pure Node — no Python. Fails loud (exit 1).

import { readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";
import katex from "katex";

const ROOT = process.cwd();

function walk(dir) {
  const out = [];
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) out.push(...walk(p));
    else if (name.endsWith(".solution.json")) out.push(p);
  }
  return out;
}

// Collect every LaTeX-bearing string in a solution, with a path for error reporting.
function latexStrings(sol) {
  const out = [];
  for (const k of ["molecular", "complete_ionic", "net_ionic"]) {
    if (sol.equations?.[k]?.latex) out.push([`equations.${k}.latex`, sol.equations[k].latex]);
  }
  (sol.ledger?.species ?? []).forEach((s, i) => {
    if (s.latex) out.push([`ledger.species[${i}].latex`, s.latex]);
  });
  return out;
}

const derived = join(ROOT, "derived");
let files = [];
try {
  files = walk(derived);
} catch {
  console.error("no derived/ directory — run `npm run produce` first");
  process.exit(1);
}

const fail = (file, where, msg) => {
  console.error(`KATEX FAILED — ${file} ${where}: ${msg}`);
  process.exit(1);
};

let count = 0;
for (const file of files) {
  const rel = file.slice(ROOT.length + 1).replaceAll("\\", "/");
  const sol = JSON.parse(readFileSync(file, "utf8"));
  for (const [where, latex] of latexStrings(sol)) {
    try {
      katex.renderToString(latex, { throwOnError: true, displayMode: true });
      count++;
    } catch (e) {
      fail(rel, where, `${e.message} — '${latex}'`);
    }
  }
}

console.log(`check-katex: ${count} LaTeX string(s) render.`);
