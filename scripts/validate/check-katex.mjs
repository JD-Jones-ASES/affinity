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
    else if (name.endsWith(".solution.json") || name.endsWith(".structure.json")) out.push(p);
  }
  return out;
}

// Inline $...$ math segments inside an authored prose string (definitions, notes).
function inlineMath(prefix, s) {
  const out = [];
  const parts = String(s ?? "").split(/(\$[^$]+\$)/g);
  parts.forEach((p, i) => {
    if (p.length > 2 && p.startsWith("$") && p.endsWith("$")) out.push([`${prefix}[$${i}]`, p.slice(1, -1)]);
  });
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

// Collect LaTeX in a structure lesson (ADR-0045): the molecule's formula symbol (display), plus any inline
// $…$ math in the scenario, the four step prose blocks, the misconception, the polarity reason, and the
// assumptions — the authored prose surfaces a reader sees rendered.
function structureLatex(les) {
  const out = [];
  if (les.molecule?.latex) out.push(["molecule.latex", les.molecule.latex]);
  out.push(...inlineMath("scenario", les.scenario));
  (les.steps ?? []).forEach((s, i) => out.push(...inlineMath(`steps[${i}].prose`, s.prose)));
  if (les.misconception?.claim) out.push(...inlineMath("misconception.claim", les.misconception.claim));
  if (les.molecule?.polarity_reason) out.push(...inlineMath("molecule.polarity_reason", les.molecule.polarity_reason));
  (les.assumptions ?? []).forEach((a, i) => out.push(...inlineMath(`assumptions[${i}].claim`, a.claim)));
  return out;
}

// Collect LaTeX in a reference object (concept entry or valence table).
function referenceLatex(ref) {
  const out = [];
  if (ref.kind === "concept") {
    if (ref.latex) out.push(["latex", ref.latex]);
    out.push(...inlineMath("definition", ref.definition));
  } else if (ref.kind === "valence-table") {
    (ref.elements ?? []).forEach((e, i) => e.common_ion?.latex && out.push([`elements[${i}].common_ion.latex`, e.common_ion.latex]));
    (ref.polyatomic ?? []).forEach((p, i) => p.latex && out.push([`polyatomic[${i}].latex`, p.latex]));
    (ref.charge_balance ?? []).forEach((c, i) => c.latex && out.push([`charge_balance[${i}].latex`, c.latex]));
  } else if (ref.kind === "reaction-family") {
    // ADR-0035: the general form, and every example's balanced equation, net-ionic view, and species symbol
    if (ref.general_form_latex) out.push(["general_form_latex", ref.general_form_latex]);
    (ref.examples ?? []).forEach((ex, i) => {
      if (ex.equation?.latex) out.push([`examples[${i}].equation.latex`, ex.equation.latex]);
      if (ex.net_ionic?.latex) out.push([`examples[${i}].net_ionic.latex`, ex.net_ionic.latex]);
      (ex.species ?? []).forEach((s, j) => s.latex && out.push([`examples[${i}].species[${j}].latex`, s.latex]));
    });
  } else if (ref.kind === "species") {
    // ADR-0038: the species symbol, plus any inline $…$ in the authored summary/notes
    if (ref.latex) out.push(["latex", ref.latex]);
    out.push(...inlineMath("summary", ref.summary));
    (ref.notes ?? []).forEach((n, i) => out.push(...inlineMath(`notes[${i}]`, n)));
  } else if (ref.kind === "formula") {
    // ADR-0039: the equation statement, every authored rearrangement, and inline $…$ in the summary/domain
    if (ref.statement) out.push(["statement", ref.statement]);
    (ref.rearrangements ?? []).forEach((r, i) => out.push([`rearrangements[${i}]`, r]));
    out.push(...inlineMath("summary", ref.summary));
    if (ref.domain) out.push(...inlineMath("domain", ref.domain));
  } else if (ref.kind === "molecule") {
    // ADR-0044: the molecule's formula symbol, plus any inline $…$ in the authored summary / polarity reason / notes
    if (ref.latex) out.push(["latex", ref.latex]);
    out.push(...inlineMath("summary", ref.summary));
    if (ref.polarity_reason) out.push(...inlineMath("polarity_reason", ref.polarity_reason));
    (ref.notes ?? []).forEach((n, i) => out.push(...inlineMath(`notes[${i}]`, n)));
  }
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
// reference objects live under derived/reference/*.json (not *.solution.json)
let refFiles = [];
try {
  const rd = join(derived, "reference");
  refFiles = readdirSync(rd).filter((n) => n.endsWith(".json")).map((n) => join(rd, n));
} catch { /* no reference yet */ }

const fail = (file, where, msg) => {
  console.error(`KATEX FAILED — ${file} ${where}: ${msg}`);
  process.exit(1);
};

let count = 0;
const render = (rel, where, latex) => {
  try {
    katex.renderToString(latex, { throwOnError: true, displayMode: true });
    count++;
  } catch (e) {
    fail(rel, where, `${e.message} — '${latex}'`);
  }
};

for (const file of files) {
  const rel = file.slice(ROOT.length + 1).replaceAll("\\", "/");
  const obj = JSON.parse(readFileSync(file, "utf8"));
  const strings = file.endsWith(".structure.json") ? structureLatex(obj) : latexStrings(obj);
  for (const [where, latex] of strings) render(rel, where, latex);
}
for (const file of refFiles) {
  const rel = file.slice(ROOT.length + 1).replaceAll("\\", "/");
  const ref = JSON.parse(readFileSync(file, "utf8"));
  for (const [where, latex] of referenceLatex(ref)) render(rel, where, latex);
}

console.log(`check-katex: ${count} LaTeX string(s) render.`);
