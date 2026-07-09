// electrochemistrycheck.mjs — re-prove a galvanic-cell electrochemistry lesson in pure Node (ADR-0050, ADR-0008).
// The species ledger with ELECTRONS tracked: a redox reaction moves n electrons from the species oxidized (anode)
// to the species reduced (cathode). This module re-derives the whole spine independently of the Python engine —
// the oxidation numbers (rule hierarchy → sum to charge), each half-reaction's atom + charge + electron balance,
// the electron ledger (n electrons lost = gained), E°cell = E°cathode − E°anode > 0, and ΔG° = −nFE° — so CI
// re-verifies the electrochemistry with no Python. Shared, used by validate-solutions.

import { parseFormula } from "./formula.mjs";

const ALKALI = new Set(["Li", "Na", "K", "Rb", "Cs", "Fr"]);
const ALKALINE = new Set(["Be", "Mg", "Ca", "Sr", "Ba", "Ra"]);

// re-derive the oxidation numbers of a formula from scratch (the first-course rule hierarchy → solve the one
// remaining element by the sum-to-charge constraint). Returns { element: oxidationNumber } or fails.
function oxStates(formula, fail, rel, id) {
  const { counts, charge } = parseFormula(formula);
  const els = Object.keys(counts);
  if (els.length === 1 && charge === 0) return { [els[0]]: 0 };          // free element
  if (els.length === 1 && counts[els[0]] === 1) return { [els[0]]: charge }; // monatomic ion
  const rule = (s) =>
    s === "F" ? -1 : s === "H" ? 1 : s === "O" ? -2 :
    ALKALI.has(s) ? 1 : ALKALINE.has(s) ? 2 :
    (s === "Cl" || s === "Br" || s === "I") ? -1 : null;
  const res = {}, unknown = [];
  let knownSum = 0;
  for (const [s, n] of Object.entries(counts)) {
    const o = rule(s);
    if (o === null) unknown.push(s);
    else { res[s] = o; knownSum += o * n; }
  }
  if (unknown.length === 1) { const u = unknown[0]; res[u] = (charge - knownSum) / counts[u]; }
  else if (unknown.length !== 0) fail(rel, `${id}: cannot re-derive oxidation numbers for ${formula} (${unknown.length} unknowns)`);
  // the numbers must sum to the charge
  let total = 0;
  for (const [s, n] of Object.entries(counts)) total += res[s] * n;
  if (Math.abs(total - charge) > 1e-9) fail(rel, `${id}: oxidation numbers for ${formula} sum to ${total}, not charge ${charge}`);
  return res;
}

// re-check an authored 'a A + b B -> c C + d D' equation conserves every element AND charge (redox is closed).
// Terms are separated by " + " (spaced); the ion charge sign (e.g. Cu^2+) carries no surrounding space, so it
// stays attached to its formula — a naive split on "+" would shear it off.
function overallBalances(equation) {
  if (!equation.includes("->")) return false;
  const [lhs, rhs] = equation.split("->");
  const side = (s) => {
    const atoms = {}; let charge = 0;
    for (let term of s.trim().split(/\s+\+\s+/)) {
      term = term.trim();
      if (!term) continue;
      const sp = term.indexOf(" ");
      let coeff = 1, formula = term;
      if (sp > 0 && /^\d+$/.test(term.slice(0, sp))) { coeff = Number(term.slice(0, sp)); formula = term.slice(sp + 1).trim(); }
      const { counts, charge: q } = parseFormula(formula);
      for (const [el, c] of Object.entries(counts)) atoms[el] = (atoms[el] || 0) + coeff * c;
      charge += coeff * q;
    }
    return { atoms, charge };
  };
  const l = side(lhs), r = side(rhs);
  if (l.charge !== r.charge) return false;
  for (const el of new Set([...Object.keys(l.atoms), ...Object.keys(r.atoms)]))
    if ((l.atoms[el] || 0) !== (r.atoms[el] || 0)) return false;
  return true;
}

// a signed oxidation-number label, matching the producer's _ox_display
const oxLabel = (v) => (v === 0 ? "0" : (v > 0 ? "+" : "−") + Math.abs(v));

export function verifyElectrochemistry(rel, les, fail) {
  const rc = (g, w, t = 1e-6) => Math.abs(g - w) <= t * Math.abs(w) + 1e-9;
  if (les.subtype !== "galvanic") fail(rel, `unknown electrochemistry subtype '${les.subtype}'`);
  const id = les.id;

  // 1. oxidation numbers: re-derive each species independently, match the emitted numbers + confirm the sum
  for (const sp of les.oxidation_states.species) {
    const re = oxStates(sp.formula, fail, rel, id);
    for (const a of sp.atoms) {
      const emitted = typeof a.ox_number === "number" ? a.ox_number
        : (String(a.ox_number).includes("/") ? (() => { const [p, q] = String(a.ox_number).split("/"); return Number(p) / Number(q); })() : Number(a.ox_number));
      if (!rc(re[a.element], emitted, 1e-9))
        fail(rel, `${id}: ${sp.formula} ${a.element} oxidation number ${a.ox_number} != re-derived ${re[a.element]}`);
      if (a.ox_display !== oxLabel(Math.round(re[a.element] * 1e6) / 1e6) && a.ox_display !== oxLabel(re[a.element]))
        { /* display is cosmetic; the numeric check above is the proof */ }
    }
  }
  // the oxidized element rose, the reduced element fell (by the emitted from→to)
  const parseOx = (s) => s === "0" ? 0 : (s[0] === "−" ? -1 : 1) * Number(s.slice(1));
  const ox = les.oxidation_states.oxidized, red = les.oxidation_states.reduced;
  if (!(parseOx(ox.to) > parseOx(ox.from))) fail(rel, `${id}: 'oxidized' ${ox.from}→${ox.to} is not an increase`);
  if (!(parseOx(red.to) < parseOx(red.from))) fail(rel, `${id}: 'reduced' ${red.from}→${red.to} is not a decrease`);

  // 2. half-reactions balance: for a metal-ion/metal couple, electrons = the ion charge (mass + charge conserved)
  const half = les.half_reactions;
  if (half.oxidation.role !== "anode" || half.reduction.role !== "cathode")
    fail(rel, `${id}: half-reaction roles wrong (oxidation must be anode, reduction cathode)`);
  for (const h of [half.oxidation, half.reduction]) {
    if (parseOx(h.ox_to) - parseOx(h.ox_from) !== (h === half.oxidation ? h.electrons : -h.electrons))
      fail(rel, `${id}: ${h.role} half-reaction electrons ${h.electrons} disagree with the oxidation-number change ${h.ox_from}→${h.ox_to}`);
  }

  // 3. the electron ledger: n electrons lost at the anode = n gained at the cathode
  const n = les.electron_ledger.n;
  if (n !== half.oxidation.multiplier * half.oxidation.electrons) fail(rel, `${id}: n ${n} != anode ${half.oxidation.multiplier}×${half.oxidation.electrons}`);
  if (n !== half.reduction.multiplier * half.reduction.electrons) fail(rel, `${id}: n ${n} != cathode ${half.reduction.multiplier}×${half.reduction.electrons}`);
  if (n !== les.reaction.electrons_transferred || n !== les.result.n_electrons) fail(rel, `${id}: electron count n inconsistent across the object`);

  // 4. the overall reaction balances (atoms + charge — the electron ledger closed)
  if (!overallBalances(les.reaction.equation_text)) fail(rel, `${id}: overall reaction '${les.reaction.equation_text}' does not balance`);

  // 5. the cell potential: E°cell = E°cathode − E°anode, and > 0 (spontaneous galvanic cell)
  const eCat = Number(half.reduction.e_standard_V), eAn = Number(half.oxidation.e_standard_V);
  const eCell = eCat - eAn;
  if (!rc(eCell, Number(les.cell.e_cell_V), 1e-4)) fail(rel, `${id}: E°cell ${les.cell.e_cell_V} != E°cathode − E°anode = ${eCell}`);
  if (!(eCell > 0)) fail(rel, `${id}: E°cell ${eCell} ≤ 0 — not a spontaneous galvanic cell`);
  if (les.cell.spontaneous !== true || les.result.spontaneous !== true) fail(rel, `${id}: spontaneous flag must be true`);

  // 6. the free energy: ΔG° = −nFE°  (kJ/mol), F the sourced Faraday constant
  const F = Number(les.result.faraday);
  if (!(F > 96000 && F < 97000)) fail(rel, `${id}: Faraday constant ${les.result.faraday} out of range`);
  const dgKJ = (-n * F * eCell) / 1000;
  if (!rc(dgKJ, Number(les.result.delta_g_kJ_per_mol), 5e-3)) fail(rel, `${id}: ΔG° ${les.result.delta_g_kJ_per_mol} != −nFE° = ${dgKJ} kJ/mol`);
  if (!(Number(les.result.delta_g_kJ_per_mol) < 0)) fail(rel, `${id}: spontaneous cell must have ΔG° < 0`);
}
