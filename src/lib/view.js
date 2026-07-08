// Build-time view prep: deep-render the verified solution's LaTeX to HTML so the player islands receive
// ready-to-display HTML and never ship KaTeX to the browser (ADR-0001). Presentation only — every value
// came from ChemKernel; this layer renders, it does not compute chemistry.
import { inline, tex } from "./katex.js";

const SUB = { "0": "₀", "1": "₁", "2": "₂", "3": "₃", "4": "₄", "5": "₅", "6": "₆", "7": "₇", "8": "₈", "9": "₉" };
const SUP = { "0": "⁰", "1": "¹", "2": "²", "3": "³", "4": "⁴", "5": "⁵", "6": "⁶", "7": "⁷", "8": "⁸", "9": "⁹", "+": "⁺", "-": "⁻" };

// Format an ASCII species/ion token ("CaCl2", "CO3^2-", "Na^+") to Unicode for compact display (chips,
// spectator lists, slider labels). Digits after atoms subscript; a trailing ^<n><sign> charge superscripts.
// This is text typography, not chemistry — the identities come from the producer.
export function prettyIon(tok) {
  if (tok == null) return tok;
  let core = String(tok);
  let charge = "";
  const m = core.match(/\^(\d*)([+-])$/);
  if (m) {
    core = core.slice(0, m.index);
    charge = [...(m[1] || "")].map((d) => SUP[d] ?? d).join("") + (SUP[m[2]] ?? m[2]);
  }
  const body = core.replace(/\d+/g, (s) => [...s].map((d) => SUB[d] ?? d).join(""));
  return body + charge;
}

const PHASE = { s: "(s)", l: "(l)", g: "(g)", aq: "(aq)" };
export function phaseTag(p) {
  return PHASE[p] ?? "";
}

// Replace known formula tokens inside generated/authored prose with their Unicode form (CaCl2 → CaCl₂).
// Only the exact tokens the producer used are touched (longest first, plain replaceAll — no regex), so
// measurement numbers ("50.0 mL", "0.100 M") are never subscripted; $…$ math segments are left for KaTeX.
// Typography only; the identities came from the producer and the committed derived/ stays ASCII (the
// parity/gym gates compare those strings).
export function prettyText(text, tokens) {
  if (text == null) return text;
  const toks = [...new Set(tokens)].filter(Boolean).sort((a, b) => b.length - a.length);
  return String(text)
    .split(/(\$[^$]+\$)/g)
    .map((part) => {
      if (part.length > 2 && part.startsWith("$") && part.endsWith("$")) return part;
      let out = part;
      for (const tok of toks) out = out.replaceAll(tok, prettyIon(tok));
      return out;
    })
    .join("");
}

// Deep-clone the solution and attach *Html / *Pretty fields the islands render. The raw scenario is dropped
// after rendering so authoring markup ($…$, **emphasis**) never ships in the hydration props.
export function renderSolution(sol) {
  const s = structuredClone(sol);

  // the lesson's known formula tokens (given species with and without phase, precipitate, leftovers) — used
  // to subscript authored/generated prose without ever touching measurement numbers
  const stripPhase = (id) => String(id).replace(/\((?:s|l|g|aq)\)$/, "");
  const lessonTokens = [
    ...(s.given ?? []).flatMap((g) => [g.species, stripPhase(g.species)]),
    s.result?.precipitate?.species,
    ...(s.result?.leftover ?? []).map((l) => l.species),
  ];

  s.scenarioHtml = inline(prettyText(s.scenario, lessonTokens));
  delete s.scenario;

  s.assumptions = (s.assumptions ?? []).map((a) => ({ ...a, claimHtml: inline(prettyText(a.claim, lessonTokens)) }));

  for (const key of ["molecular", "complete_ionic", "net_ionic"]) {
    s.equations[key].html = tex(s.equations[key].latex);
  }
  s.equations.spectatorsPretty = (s.equations.spectators ?? []).map(prettyIon);

  s.ledger.species = s.ledger.species.map((r) => ({
    ...r,
    symbolHtml: tex(r.latex, false),
    idPretty: prettyIon(r.id),
    phaseTag: phaseTag(r.phase),
  }));
  s.ledger.limitingPretty = (s.ledger.limiting ?? []).map(prettyIon);

  // reuse the producer's (upright, ADR-0025) LaTeX from the matching ledger row rather than rebuilding it
  const precipRow = s.ledger.species.find((r) => r.id === s.result.precipitate.species);
  s.result.precipitate.symbolHtml = precipRow ? precipRow.symbolHtml
    : tex(s.result.precipitate.species.replace(/(\d+)/g, "_{$1}"), false);
  s.result.precipitate.idPretty = prettyIon(s.result.precipitate.species);
  s.result.limiting_speciesPretty = (s.result.limiting_species ?? []).map(prettyIon);
  s.result.leftover = (s.result.leftover ?? []).map((l) => ({ ...l, idPretty: prettyIon(l.species) }));

  if (s.misconception) s.misconception.claimHtml = inline(prettyText(s.misconception.claim, lessonTokens));
  if (s.solubility_basis) {
    s.solubility_basis.statementHtml = inline(s.solubility_basis.statement);
    s.solubility_basis.idPretty = prettyIon(s.solubility_basis.species);
  }

  s.given = (s.given ?? []).map((g) => ({ ...g, idPretty: prettyIon(g.species) }));

  // Practice text: subscript the formula tokens the generator embedded (brief §6.1). The token set is the
  // interactive block's — the same identities the practice generator drew from.
  if (s.practice && s.interactive) {
    const tokens = [s.interactive.cation.source, s.interactive.anion.source, s.interactive.product.id];
    s.practice.questions = s.practice.questions.map((q) => ({
      ...q,
      prompt: prettyText(q.prompt, tokens),
      explain: prettyText(q.explain, tokens),
      // categorical questions carry a `choices` menu; numeric ones (ADR-0032) a `diagnostics` catalogue
      choices: q.choices && q.choices.map((c) => ({
        ...c,
        display: prettyText(c.display, tokens),
        misconception: prettyText(c.misconception, tokens),
      })),
      diagnostics: q.diagnostics && q.diagnostics.map((d) => ({
        ...d,
        misconception: prettyText(d.misconception, tokens),
      })),
    }));
  }

  return s;
}

// Gym view prep: subscript the formula tokens the producer emitted (brief §6.1, ADR-0025). Conversion
// problems carry a single substance token; nomenclature problems carry `subscript_tokens` (the compound
// formula + distractor formulas + ion ids). Prompt, explanation, AND choices go through prettyText — names
// (no digits) pass through untouched, formulas get subscripted, measurement numbers are never matched.
export function renderGym(gym) {
  const g = structuredClone(gym);
  g.problems = g.problems.map((p) => {
    const tokens = p.subscript_tokens?.length
      ? p.subscript_tokens
      : [p.derivation?.inputs?.substance].filter(Boolean);
    return {
      ...p,
      prompt: prettyText(p.prompt, tokens),
      explain: prettyText(p.explain, tokens),
      // chain step notes can name species (e.g. "× (1 mol H2 / 2 mol HCl)") — subscript them too; the
      // numeric values and units carry no formula tokens, so they pass through untouched.
      chain: p.chain && p.chain.map((st) => ({ ...st, note: prettyText(st.note, tokens) })),
      // choice problems (categorical) carry a menu; numeric problems (ADR-0032) carry a diagnostics catalogue
      // instead — prettify whichever is present.
      choices: p.choices && p.choices.map((c) => ({
        ...c,
        display: prettyText(c.display, tokens),
        misconception: prettyText(c.misconception, tokens),
      })),
      diagnostics: p.diagnostics && p.diagnostics.map((d) => ({
        ...d,
        misconception: prettyText(d.misconception, tokens),
      })),
    };
  });
  return g;
}

// Exact ×100 integer for a two-decimal string ("3.98" → 398) so the bonding mode's ΔEN subtraction and
// threshold comparisons run on integers in the browser — no float noise (ADR-0033, the tally discipline).
function cents(s) {
  const [whole, frac = ""] = String(s).split(".");
  return Number(whole) * 100 + Number((frac + "00").slice(0, 2));
}

// Deep-render the Valence Table's LaTeX to HTML (build-time) so the ValenceTable island ships no KaTeX.
export function renderValenceTable(t) {
  const v = structuredClone(t);
  const renderIon = (i) => ({ ...i, latexHtml: tex(i.latex, false), pretty: prettyIon(i.id) });
  v.elements = v.elements.map((e) => ({
    ...e,
    ...(e.common_ion ? { common_ion: renderIon(e.common_ion) } : {}),
    ...(e.other_ions ? { other_ions: e.other_ions.map(renderIon) } : {}),
    // exact integer electronegativity for the bonding mode's browser-side ΔEN arithmetic
    ...(e.electronegativity != null ? { enCents: cents(e.electronegativity) } : {}),
  }));
  v.polyatomic = v.polyatomic.map((p) => ({ ...p, latexHtml: tex(p.latex, false), pretty: prettyIon(p.id) }));
  v.charge_balance = v.charge_balance.map((c) => ({
    ...c, latexHtml: tex(c.latex, false), cationPretty: prettyIon(c.cation), anionPretty: prettyIon(c.anion),
    ...(c.mistake ? { mistake: { ...c.mistake, pretty: prettyIon(c.mistake.formula) } } : {}),
  }));
  if (v.bonding) {
    v.bonding.classes = v.bonding.classes.map((c) => ({
      ...c,
      ...(c.min != null ? { minCents: cents(c.min) } : {}),
      ...(c.max != null ? { maxCents: cents(c.max) } : {}),
    }));
  }
  return v;
}

// Render a reaction-family entry (ADR-0035): each example's balanced equation + net-ionic view render at
// build time (upright producer LaTeX, ADR-0025); prose (summary, conditions, misconceptions, per-example
// evidence + redox reason) gets its formula tokens subscripted — the same view discipline as lessons/gyms.
export function renderReactionFamily(f) {
  const r = structuredClone(f);
  // prose tokens: emitted by the producer (every example's species + author-declared intermediates like
  // H2CO3 that never appear as a species), falling back to the example union for older data.
  const famTokens = r.prose_tokens?.length ? r.prose_tokens : r.examples.flatMap((ex) => ex.subscript_tokens ?? []);
  r.summaryPretty = prettyText(r.summary, famTokens);
  r.general_formPretty = prettyText(r.general_form, famTokens);
  r.general_formHtml = r.general_form_latex ? tex(r.general_form_latex, false) : null;
  r.conditions = (r.conditions ?? []).map((c) => prettyText(c, famTokens));
  r.misconceptions = r.misconceptions.map((m) => ({
    claim: prettyText(m.claim, famTokens),
    refute: prettyText(m.refute, famTokens),
  }));
  r.examples = r.examples.map((ex) => ({
    ...ex,
    equationHtml: tex(ex.equation.latex, false),
    netHtml: ex.net_ionic ? tex(ex.net_ionic.latex, false) : null,
    evidencePretty: prettyText(ex.evidence, ex.subscript_tokens ?? []),
    redoxReasonPretty: ex.redox_reason ? prettyText(ex.redox_reason, ex.subscript_tokens ?? []) : null,
    spectatorsPretty: (ex.spectators ?? []).map(prettyIon),
  }));
  return r;
}

// Render a concept entry (definition may carry inline $…$; latex is a standalone display formula).
export function renderConcept(c) {
  return {
    ...c,
    definitionHtml: inline(c.definition),
    latexHtml: c.latex ? tex(c.latex) : null,
    termPretty: prettyIon(c.term),
  };
}
