// balancecheck.mjs — shared pure re-verification helpers for the Node gates (ADR-0028/0035). Given emitted
// species (formula, role, counts, charge) + a coefficient vector, `verifyBalance` re-parses each formula
// (formula.mjs), confirms the emitted counts/charge match that independent parse, then proves the coefficients
// zero every element row AND the charge row of the conservation matrix — the definition of a balanced
// equation — all-positive and reduced (gcd 1). No null-space solve: Python owns uniqueness (balance() needs a
// 1-D null space); the gate proves the emitted answer is a true, reduced balance of the exact shown formulas.
// Shared by validate-gyms (balancing + stoichiometry) and validate-reference (reaction-family examples).

import { parseFormula } from "./formula.mjs";

export const gcd = (a, b) => { a = Math.abs(a); b = Math.abs(b); while (b) { [a, b] = [b, a % b]; } return a; };

export function verifyBalance(rel, id, species, coefficients, fail) {
  if (!Array.isArray(species) || !Array.isArray(coefficients))
    fail(rel, `${id}: derivation missing species/coefficients`);
  const n = species.length;
  if (coefficients.length !== n) fail(rel, `${id}: ${coefficients.length} coefficients for ${n} species`);
  const els = new Set();
  for (const s of species) {
    let parsed;
    try { parsed = parseFormula(s.formula); }
    catch (e) { fail(rel, `${id}: cannot parse species '${s.formula}': ${e.message}`); }
    if (parsed.charge !== s.charge) fail(rel, `${id}: '${s.formula}' charge ${parsed.charge} != emitted ${s.charge}`);
    const a = parsed.counts, b = s.counts;
    for (const k of new Set([...Object.keys(a), ...Object.keys(b)])) {
      if ((a[k] || 0) !== (b[k] || 0)) fail(rel, `${id}: '${s.formula}' count ${k}=${a[k] || 0} != emitted ${b[k] || 0}`);
      els.add(k);
    }
  }
  for (const key of [...els].sort().concat("charge")) {
    let left = 0, right = 0;
    species.forEach((s, i) => {
      const amt = (key === "charge" ? s.charge : (s.counts[key] || 0)) * coefficients[i];
      if (s.role === "reactant") left += amt; else right += amt;
    });
    if (left !== right) fail(rel, `${id}: ${key} not conserved (${left} vs ${right}) — not balanced`);
  }
  if (coefficients.some((c) => !Number.isInteger(c) || c < 1))
    fail(rel, `${id}: coefficients must be positive integers, got [${coefficients}]`);
  if (coefficients.reduce((a, b) => gcd(a, b)) !== 1)
    fail(rel, `${id}: coefficients [${coefficients}] are not reduced (common factor)`);
  return [...els].sort();
}

// The item-6 redox signature (ADR-0035): an element FREE (neutral, one element type) on one side and combined
// on the other changed oxidation state. Re-derives, in pure Node, the `redox` flag the classifier emitted —
// no oxidation-number assignment (a Phase-2 topic), just the free-element criterion a first course uses.
export function redoxFreeElements(species) {
  const isFree = (s) => s.charge === 0 && Object.keys(s.counts).length === 1;
  const setOf = (role, free) => {
    const out = new Set();
    for (const s of species) if (s.role === role && isFree(s) === free)
      for (const el of Object.keys(s.counts)) out.add(el);
    return out;
  };
  const freeL = setOf("reactant", true), freeR = setOf("product", true);
  const combL = setOf("reactant", false), combR = setOf("product", false);
  const changed = new Set();
  for (const el of freeL) if (combR.has(el)) changed.add(el);
  for (const el of freeR) if (combL.has(el)) changed.add(el);
  return [...changed].sort();
}
