// kineticscheck.mjs — re-prove a kinetics lesson in pure Node (ADR-0049, ADR-0008). The species ledger with the
// extent evolving in TIME, for orders 0, 1, 2:
//   order 0:  [A] = [A]₀ − kt          t½ = [A]₀/2k     (successive half-lives HALVE; [A]=0 at t=[A]₀/k)
//   order 1:  [A] = [A]₀·e^(−kt)       t½ = ln2/k       (successive half-lives are EQUAL — the signature)
//   order 2:  1/[A] = 1/[A]₀ + kt      t½ = 1/k[A]₀     (successive half-lives DOUBLE)
// This module re-derives the whole spine independently of the Python engine — the reaction balance, every curve
// point's c(t), the order's t½ relation, the halving landmarks c(reach c₀/2ⁿ), and the successive-half-life
// progression — so CI re-verifies the kinetics with no Python. k is in its native units (s⁻¹ or min⁻¹); the time
// base (min → 60 s) comes from the k unit. Shared, used by validate-solutions.

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

// the integrated rate laws + half-life + its inverse (all in the k's native time unit).
function concAt(order, c0, k, t) {
  if (order === 0) return Math.max(c0 - k * t, 0);
  if (order === 1) return c0 * Math.exp(-k * t);
  return c0 / (1 + k * c0 * t);
}
function halfLife(order, c0, k) {
  if (order === 0) return c0 / (2 * k);
  if (order === 1) return LN2 / k;
  return 1 / (k * c0);
}
function timeToReach(order, c0, k, c) {
  if (order === 0) return (c0 - c) / k;
  if (order === 1) return Math.log(c0 / c) / k;
  return (1 / c - 1 / c0) / k;
}

// Re-derive + verify one kinetics lesson (ADR-0049). `fail(rel, msg)` exits.
export function verifyKinetics(rel, les, fail) {
  const rc = (g, w, t = 1e-6) => Math.abs(g - w) <= t * Math.abs(w) + 1e-12;
  const order = les.rate_law.order;
  if (![0, 1, 2].includes(order)) fail(rel, `rate_law.order ${order} is not 0, 1, or 2`);
  const subtypeFor = { 0: "zero-order", 1: "first-order", 2: "second-order" };
  if (les.subtype !== subtypeFor[order]) fail(rel, `subtype '${les.subtype}' does not match order ${order}`);

  const k = Number(les.rate_law.k_value);
  const c0 = Number(les.integrated.initial_molarity_M);
  if (!(k > 0)) fail(rel, `rate constant k ${les.rate_law.k_value} is not positive`);
  if (!(c0 > 0)) fail(rel, `initial molarity ${les.integrated.initial_molarity_M} is not positive`);
  // the k units must encode the order (concentration exponent) — and set the time base (min → 60 s).
  const unitOrder = { "M/s": 0, "M/min": 0, "1/s": 1, "1/min": 1, "1/(M*s)": 2, "1/(M*min)": 2 };
  if (unitOrder[les.rate_law.k_unit] !== order)
    fail(rel, `k_unit '${les.rate_law.k_unit}' does not match order ${order}`);
  const tb = les.rate_law.k_unit.includes("min") ? 60 : 1;   // seconds per native time unit

  // 1. the reaction conserves every element (re-parsed in pure Node)
  if (!balanceOk(les.reaction.equation_text)) fail(rel, `reaction '${les.reaction.equation_text}' does not balance`);

  // 2. the half-life relation: the FIRST t½ matches the order's formula (native), reported in seconds
  const tHalfNative = halfLife(order, c0, k);
  const tHalfSec = Number(les.half_life.seconds);
  if (!(tHalfSec > 0)) fail(rel, `half_life.seconds ${les.half_life.seconds} is not positive`);
  if (!rc(tHalfSec, tHalfNative * tb, 1e-3)) fail(rel, `t½ ${les.half_life.seconds}s != order-${order} t½ = ${tHalfNative * tb}s`);
  if (les.half_life.depends_on_concentration !== (order !== 1))
    fail(rel, `half_life.depends_on_concentration ${les.half_life.depends_on_concentration} wrong for order ${order}`);
  if (order === 1 && les.half_life.k_times_thalf !== undefined && !rc(Number(les.half_life.k_times_thalf), LN2, 1e-4))
    fail(rel, `half_life.k_times_thalf ${les.half_life.k_times_thalf} != ln2 = ${LN2}`);

  // 3. the integrated rate law: every curve point c(t) matches the order's law, at t = (half_lives)·t½
  if (!(les.curve.points.length >= 3)) fail(rel, "kinetics curve needs ≥ 3 points");
  for (const p of les.curve.points) {
    const tNative = Number(p.half_lives) * tHalfNative;
    if (!rc(Number(p.t_seconds), tNative * tb, 1e-4)) fail(rel, `curve point t ${p.t_seconds} != ${p.half_lives}·t½`);
    const cExp = concAt(order, c0, k, tNative);
    if (!rc(Number(p.concentration_M), cExp, 1e-4))
      fail(rel, `curve t=${p.t_seconds}s: [A] ${p.concentration_M} != order-${order} law = ${cExp}`);
    if (!rc(Number(p.percent_remaining_display), (cExp / c0) * 100, 5e-3))
      fail(rel, `curve t=${p.t_seconds}s: percent_remaining ${p.percent_remaining_display} != ${(cExp / c0) * 100}`);
  }

  // 4. the halving landmarks (c₀/2ⁿ): the TIME of each is order-specific, its DURATION (segment) the fingerprint
  if (!(les.result.landmarks.length >= 3)) fail(rel, "kinetics needs ≥ 3 halving landmarks");
  const segHours = [];
  let prevNative = 0;
  for (const lm of les.result.landmarks) {
    const n = lm.half_lives;
    const cExp = c0 / Math.pow(2, n);                        // c₀/2ⁿ by definition (n successive halvings)
    if (!rc(Number(lm.concentration_M), cExp, 1e-3))
      fail(rel, `landmark ${n}: [A] ${lm.concentration_M} != c₀/2^${n} = ${cExp}`);
    const tNative = timeToReach(order, c0, k, cExp);         // order-specific spacing
    if (!rc(Number(lm.t_hours_display), (tNative * tb) / 3600, 5e-3))
      fail(rel, `landmark ${n}: t ${lm.t_hours_display}h != time-to-reach = ${(tNative * tb) / 3600}h`);
    const segNative = tNative - prevNative;
    if (!rc(Number(lm.segment_half_life_hours_display), (segNative * tb) / 3600, 5e-3))
      fail(rel, `landmark ${n}: segment half-life ${lm.segment_half_life_hours_display}h != ${(segNative * tb) / 3600}h`);
    prevNative = tNative;
    segHours.push(segNative * tb / 3600);
    const pctDecomposed = 100 - (cExp / c0) * 100;
    if (!rc(Number(lm.percent_decomposed_display), pctDecomposed, 5e-3))
      fail(rel, `landmark ${n}: percent_decomposed ${lm.percent_decomposed_display} != ${pctDecomposed}`);
  }

  // 5. the successive-half-life PROGRESSION (the order's fingerprint), machine-checked against the segments above
  const prog = les.half_life.progression;
  const progFor = { 0: "halves", 1: "constant", 2: "doubles" };
  if (prog !== progFor[order]) fail(rel, `half_life.progression '${prog}' wrong for order ${order} (expected ${progFor[order]})`);
  const ratio = (i) => segHours[i + 1] / segHours[i];
  if (prog === "constant" && !(rc(ratio(0), 1, 2e-2) && rc(ratio(1), 1, 2e-2)))
    fail(rel, `progression 'constant' but segments ${segHours} are not equal`);
  if (prog === "doubles" && !(rc(ratio(0), 2, 2e-2) && rc(ratio(1), 2, 2e-2)))
    fail(rel, `progression 'doubles' but segment ratios are ${ratio(0)}, ${ratio(1)} (expected ~2)`);
  if (prog === "halves" && !(rc(ratio(0), 0.5, 2e-2) && rc(ratio(1), 0.5, 2e-2)))
    fail(rel, `progression 'halves' but segment ratios are ${ratio(0)}, ${ratio(1)} (expected ~0.5)`);

  // 6. zero order alone reaches a finite completion: [A] = 0 at t = c₀/k
  if (order === 0) {
    if (les.result.completion_hours_display === undefined) fail(rel, "zero-order lesson missing result.completion_hours_display");
    if (!rc(Number(les.result.completion_hours_display), ((c0 / k) * tb) / 3600, 5e-3))
      fail(rel, `completion ${les.result.completion_hours_display}h != c₀/k = ${((c0 / k) * tb) / 3600}h`);
    if (!rc(concAt(0, c0, k, c0 / k), 0, 1e-9)) fail(rel, "zero order: [A] should be 0 at t = c₀/k");
  } else if (les.result.completion_hours_display !== undefined) {
    fail(rel, `order ${order} is asymptotic — it must not report a finite completion time`);
  }
}
