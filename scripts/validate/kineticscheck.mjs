// kineticscheck.mjs — re-prove a first-order kinetics lesson in pure Node (ADR-0049, ADR-0008). The species ledger
// with the extent evolving in TIME: a first-order reactant decays by the integrated rate law [A](t) = [A]₀·e^(−kt),
// with half-life t½ = ln2/k (independent of [A]₀). This module re-derives the whole spine independently of the
// Python engine — the reaction balance, every curve point's c(t), the half-life relation k·t½ = ln2, and the
// halving landmarks c(n·t½) = c₀/2ⁿ — so CI re-verifies the kinetics with no Python. Shared, used by validate-solutions.

import { parseFormula } from "./formula.mjs";

const LN2 = Math.log(2);

// re-check an authored 'aA + bB -> cC + dD' equation conserves every element (regime-1), re-parsing each formula.
function balanceOk(equation) {
  if (!equation.includes("->")) return false;
  const [lhs, rhs] = equation.split("->");
  const sideCounts = (side) => {
    const totals = {};
    for (let term of side.split("+")) {
      term = term.trim();
      if (!term) continue;
      const sp = term.indexOf(" ");
      let coeff = 1, formula = term;
      if (sp > 0 && /^\d+$/.test(term.slice(0, sp))) { coeff = Number(term.slice(0, sp)); formula = term.slice(sp + 1).trim(); }
      const { counts } = parseFormula(formula);
      for (const [el, c] of Object.entries(counts)) totals[el] = (totals[el] || 0) + coeff * c;
    }
    return totals;
  };
  const l = sideCounts(lhs), r = sideCounts(rhs);
  for (const el of new Set([...Object.keys(l), ...Object.keys(r)])) if ((l[el] || 0) !== (r[el] || 0)) return false;
  return true;
}

// Re-derive + verify one first-order kinetics lesson (ADR-0049). `fail(rel, msg)` exits.
export function verifyKinetics(rel, les, fail) {
  const rc = (g, w, t = 1e-6) => Math.abs(g - w) <= t * Math.abs(w) + 1e-12;
  if (les.subtype !== "first-order") fail(rel, `unknown kinetics subtype '${les.subtype}'`);
  const k = Number(les.rate_law.k_value);
  const c0 = Number(les.integrated.initial_molarity_M);
  if (!(k > 0)) fail(rel, `rate constant k ${les.rate_law.k_value} is not positive`);
  if (!(c0 > 0)) fail(rel, `initial molarity ${les.integrated.initial_molarity_M} is not positive`);
  if (les.rate_law.order !== 1) fail(rel, `rate_law.order ${les.rate_law.order} is not 1 (first-order lesson)`);

  // 1. the reaction conserves every element (re-parsed in pure Node)
  if (!balanceOk(les.reaction.equation_text)) fail(rel, `reaction '${les.reaction.equation_text}' does not balance`);

  // 2. the half-life relation: t½ = ln2/k, so k·t½ = ln2 — independent of c₀
  const tHalf = Number(les.half_life.seconds);
  if (!(tHalf > 0)) fail(rel, `half_life.seconds ${les.half_life.seconds} is not positive`);
  if (!rc(k * tHalf, LN2, 1e-3)) fail(rel, `k·t½ = ${k * tHalf} != ln2 = ${LN2} (half-life relation)`);
  if (!rc(tHalf, LN2 / k, 1e-3)) fail(rel, `t½ ${les.half_life.seconds} != ln2/k = ${LN2 / k}`);
  if (!rc(Number(les.half_life.k_times_thalf), LN2, 1e-4))
    fail(rel, `half_life.k_times_thalf ${les.half_life.k_times_thalf} != ln2 = ${LN2}`);

  // 3. the integrated rate law: every curve point c(t) = c₀·e^(−kt), at t = (half_lives)·t½
  if (!(les.curve.points.length >= 3)) fail(rel, "kinetics curve needs ≥ 3 points");
  for (const p of les.curve.points) {
    const t = Number(p.t_seconds);
    if (!rc(t, Number(p.half_lives) * tHalf, 1e-4)) fail(rel, `curve point t ${p.t_seconds} != ${p.half_lives}·t½`);
    const cExp = c0 * Math.exp(-k * t);
    if (!rc(Number(p.concentration_M), cExp, 1e-4))
      fail(rel, `curve t=${p.t_seconds}s: [A] ${p.concentration_M} != c₀·e^(−kt) = ${cExp}`);
    if (!rc(Number(p.percent_remaining_display), (cExp / c0) * 100, 5e-3))
      fail(rel, `curve t=${p.t_seconds}s: percent_remaining ${p.percent_remaining_display} != ${(cExp / c0) * 100}`);
  }

  // 4. half-life CONSTANT (the first-order signature): c(n·t½) = c₀/2ⁿ — successive half-lives equal, whatever remains
  if (!(les.result.landmarks.length >= 3)) fail(rel, "kinetics needs ≥ 3 halving landmarks");
  for (const lm of les.result.landmarks) {
    const n = lm.half_lives;
    const cExp = c0 / Math.pow(2, n);                        // exact for a constant half-life
    if (!rc(Number(lm.concentration_M), cExp, 1e-3))
      fail(rel, `landmark ${n}·t½: [A] ${lm.concentration_M} != c₀/2^${n} = ${cExp}`);
    if (!rc(cExp, c0 * Math.exp(-k * n * tHalf), 1e-3))
      fail(rel, `landmark ${n}: c₀/2^${n} != c₀·e^(−k·${n}·t½) — the integrated law and the halving disagree`);
    const pctDecomposed = 100 - (cExp / c0) * 100;
    if (!rc(Number(lm.percent_decomposed_display), pctDecomposed, 5e-3))
      fail(rel, `landmark ${n}: percent_decomposed ${lm.percent_decomposed_display} != ${pctDecomposed}`);
  }
}
