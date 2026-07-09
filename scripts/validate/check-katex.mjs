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
    else if (name.endsWith(".solution.json") || name.endsWith(".structure.json") || name.endsWith(".comparison.json") || name.endsWith(".equilibrium.json") || name.endsWith(".prediction.json") || name.endsWith(".kinetics.json") || name.endsWith(".electrochemistry.json")) out.push(p);
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

// Collect LaTeX in a comparison lesson (ADR-0047): each row's molecule symbol (display), plus any inline $…$
// in the scenario, trend claim, takeaway, misconception, and assumptions.
function comparisonLatex(les) {
  const out = [];
  (les.rows ?? []).forEach((r, i) => r.latex && out.push([`rows[${i}].latex`, r.latex]));
  out.push(...inlineMath("scenario", les.scenario));
  if (les.trend?.claim) out.push(...inlineMath("trend.claim", les.trend.claim));
  if (les.takeaway) out.push(...inlineMath("takeaway", les.takeaway));
  if (les.misconception?.claim) out.push(...inlineMath("misconception.claim", les.misconception.claim));
  (les.assumptions ?? []).forEach((a, i) => out.push(...inlineMath(`assumptions[${i}].claim`, a.claim)));
  return out;
}

// Collect LaTeX in an equilibrium lesson (ADR-0048): the reaction (⇌) display, the mass-action expression, each
// ICE species symbol, plus any inline $…$ in the scenario, assumptions, and misconception.
function equilibriumLatex(les) {
  const out = [];
  if (les.reaction?.latex) out.push(["reaction.latex", les.reaction.latex]);
  if (les.equilibrium_constant?.expression_latex) out.push(["equilibrium_constant.expression_latex", les.equilibrium_constant.expression_latex]);
  (les.ice?.species ?? []).forEach((s, i) => s.latex && out.push([`ice.species[${i}].latex`, s.latex]));
  // titration subtype: the neutralization equation is rendered (view.js → neutralizationHtml) — gate it too (B3)
  if (les.titration?.neutralization_latex) out.push(["titration.neutralization_latex", les.titration.neutralization_latex]);
  out.push(...inlineMath("scenario", les.scenario));
  (les.assumptions ?? []).forEach((a, i) => out.push(...inlineMath(`assumptions[${i}].claim`, a.claim)));
  if (les.misconception?.claim) out.push(...inlineMath("misconception.claim", les.misconception.claim));
  return out;
}

// Collect LaTeX in a prediction lesson (ADR-0048, 9th increment): the dissolution reaction (⇌) display, the Kₛₚ
// and Q expressions, each source's formula + ion symbol, plus any inline $…$ in the scenario/assumptions/misconception.
function predictionLatex(les) {
  const out = [];
  if (les.reaction?.latex) out.push(["reaction.latex", les.reaction.latex]);
  for (const k of ["salt_latex", "cation_latex", "anion_latex"]) if (les.reaction?.[k]) out.push([`reaction.${k}`, les.reaction[k]]);
  if (les.equilibrium_constant?.expression_latex) out.push(["equilibrium_constant.expression_latex", les.equilibrium_constant.expression_latex]);
  if (les.quotient?.expression_latex) out.push(["quotient.expression_latex", les.quotient.expression_latex]);
  for (const s of ["cation_source", "anion_source"]) {
    const src = les.mixing?.[s];
    if (src?.formula_latex) out.push([`mixing.${s}.formula_latex`, src.formula_latex]);
    if (src?.ion_latex) out.push([`mixing.${s}.ion_latex`, src.ion_latex]);
  }
  out.push(...inlineMath("scenario", les.scenario));
  (les.assumptions ?? []).forEach((a, i) => out.push(...inlineMath(`assumptions[${i}].claim`, a.claim)));
  if (les.misconception?.claim) out.push(...inlineMath("misconception.claim", les.misconception.claim));
  return out;
}

// Collect LaTeX in a kinetics lesson (ADR-0049): the balanced reaction (→), the rate law, the integrated rate law,
// the half-life relation, the reactant symbol, plus any inline $…$ in the scenario/assumptions/misconception.
function kineticsLatex(les) {
  const out = [];
  if (les.reaction?.equation_latex) out.push(["reaction.equation_latex", les.reaction.equation_latex]);
  if (les.reaction?.reactant_latex) out.push(["reaction.reactant_latex", les.reaction.reactant_latex]);
  if (les.rate_law?.statement_latex) out.push(["rate_law.statement_latex", les.rate_law.statement_latex]);
  if (les.integrated?.law_latex) out.push(["integrated.law_latex", les.integrated.law_latex]);
  if (les.half_life?.relation_latex) out.push(["half_life.relation_latex", les.half_life.relation_latex]);
  out.push(...inlineMath("scenario", les.scenario));
  (les.assumptions ?? []).forEach((a, i) => out.push(...inlineMath(`assumptions[${i}].claim`, a.claim)));
  if (les.misconception?.claim) out.push(...inlineMath("misconception.claim", les.misconception.claim));
  return out;
}

// Collect LaTeX in an electrochemistry lesson (ADR-0050): the overall reaction (→), the two half-reactions, the
// oxidation-number species symbols, the cell notation, plus any inline $…$ in the scenario/assumptions/misconception.
function electrochemistryLatex(les) {
  const out = [];
  if (les.reaction?.equation_latex) out.push(["reaction.equation_latex", les.reaction.equation_latex]);
  if (les.half_reactions?.oxidation?.equation_latex) out.push(["half_reactions.oxidation", les.half_reactions.oxidation.equation_latex]);
  if (les.half_reactions?.reduction?.equation_latex) out.push(["half_reactions.reduction", les.half_reactions.reduction.equation_latex]);
  (les.oxidation_states?.species ?? []).forEach((s, i) => out.push([`oxidation_states.species[${i}].latex`, s.latex]));
  if (les.cell?.notation_latex) out.push(["cell.notation_latex", les.cell.notation_latex]);
  out.push(...inlineMath("scenario", les.scenario));
  (les.assumptions ?? []).forEach((a, i) => out.push(...inlineMath(`assumptions[${i}].claim`, a.claim)));
  if (les.misconception?.claim) out.push(...inlineMath("misconception.claim", les.misconception.claim));
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
    // the variable-charge ions' chips are rendered too (ValenceTable.svelte → other_ions latexHtml) — gate them (B3)
    (ref.elements ?? []).forEach((e, i) => (e.other_ions ?? []).forEach((o, j) => o.latex && out.push([`elements[${i}].other_ions[${j}].latex`, o.latex])));
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
    // the disclosed model assumptions are rendered on the formula sheet (formulas.astro → claimHtml, inline $…$) — gate them (B3)
    (ref.assumptions ?? []).forEach((a, i) => out.push(...inlineMath(`assumptions[${i}].claim`, a.claim)));
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
  const strings = file.endsWith(".structure.json") ? structureLatex(obj)
    : file.endsWith(".comparison.json") ? comparisonLatex(obj)
    : file.endsWith(".equilibrium.json") ? equilibriumLatex(obj)
    : file.endsWith(".prediction.json") ? predictionLatex(obj)
    : file.endsWith(".kinetics.json") ? kineticsLatex(obj)
    : file.endsWith(".electrochemistry.json") ? electrochemistryLatex(obj) : latexStrings(obj);
  for (const [where, latex] of strings) render(rel, where, latex);
}
for (const file of refFiles) {
  const rel = file.slice(ROOT.length + 1).replaceAll("\\", "/");
  const ref = JSON.parse(readFileSync(file, "utf8"));
  for (const [where, latex] of referenceLatex(ref)) render(rel, where, latex);
}

console.log(`check-katex: ${count} LaTeX string(s) render.`);
