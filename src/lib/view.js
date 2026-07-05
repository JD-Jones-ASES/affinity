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

// Deep-clone the solution and attach *Html / *Pretty fields the islands render. The raw scenario is dropped
// after rendering so authoring markup ($…$, **emphasis**) never ships in the hydration props.
export function renderSolution(sol) {
  const s = structuredClone(sol);

  s.scenarioHtml = inline(s.scenario);
  delete s.scenario;

  s.assumptions = (s.assumptions ?? []).map((a) => ({ ...a, claimHtml: inline(a.claim) }));

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

  s.result.precipitate.symbolHtml = tex(s.result.precipitate.species.replace(/(\d+)/g, "_{$1}"), false);
  s.result.precipitate.idPretty = prettyIon(s.result.precipitate.species);
  s.result.limiting_speciesPretty = (s.result.limiting_species ?? []).map(prettyIon);
  s.result.leftover = (s.result.leftover ?? []).map((l) => ({ ...l, idPretty: prettyIon(l.species) }));

  if (s.misconception) s.misconception.claimHtml = inline(s.misconception.claim);
  if (s.solubility_basis) {
    s.solubility_basis.statementHtml = inline(s.solubility_basis.statement);
    s.solubility_basis.idPretty = prettyIon(s.solubility_basis.species);
  }

  s.given = (s.given ?? []).map((g) => ({ ...g, idPretty: prettyIon(g.species) }));

  return s;
}

// Deep-render the Valence Table's LaTeX to HTML (build-time) so the ValenceTable island ships no KaTeX.
export function renderValenceTable(t) {
  const v = structuredClone(t);
  v.elements = v.elements.map((e) => ({
    ...e,
    ...(e.common_ion ? { common_ion: { ...e.common_ion, latexHtml: tex(e.common_ion.latex, false), pretty: prettyIon(e.common_ion.id) } } : {}),
  }));
  v.polyatomic = v.polyatomic.map((p) => ({ ...p, latexHtml: tex(p.latex, false), pretty: prettyIon(p.id) }));
  v.charge_balance = v.charge_balance.map((c) => ({
    ...c, latexHtml: tex(c.latex, false), cationPretty: prettyIon(c.cation), anionPretty: prettyIon(c.anion),
  }));
  return v;
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
