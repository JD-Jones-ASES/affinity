// check-ledger.mjs — re-prove the species ledger in pure Node (ADR-0008, ADR-0016). The ledger is the pivot
// object: every amount is n_i = n_{i,0} + ν_i·ξ. This gate re-derives every row's final amount from its
// initial amount, signed coefficient, and the reported extent — independent of the Python engine — and
// cross-checks the reported result (precipitate moles, leftovers) against the ledger. So CI re-proves the
// conservation arithmetic with no Python. Fails loud (exit 1).

import { readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";

const ROOT = process.cwd();
const TOL = 1e-12;

function walk(dir) {
  const out = [];
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) out.push(...walk(p));
    else if (name.endsWith(".solution.json")) out.push(p);
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

const fail = (file, msg) => {
  console.error(`LEDGER FAILED — ${file}: ${msg}`);
  process.exit(1);
};
const near = (a, b) => Math.abs(a - b) <= TOL + TOL * Math.abs(b);

let rows = 0;
let gases = 0;
for (const file of files) {
  const rel = file.slice(ROOT.length + 1).replaceAll("\\", "/");
  const sol = JSON.parse(readFileSync(file, "utf8"));
  const L = sol.ledger;
  const xi = Number(L.extent_mol);
  if (!(xi > 0)) fail(rel, `extent_mol ${L.extent_mol} is not positive`);

  const byId = {};
  for (const r of L.species) {
    // the ledger equation, re-derived: final = initial + ν·ξ
    const expected = Number(r.initial_mol) + r.nu * xi;
    if (!near(expected, Number(r.final_mol)))
      fail(rel, `${r.id}: final_mol ${r.final_mol} != initial + ν·ξ = ${expected}`);
    // roles are consistent with the signs and the extent
    if (r.role === "product" && !(r.nu > 0 && Number(r.initial_mol) === 0))
      fail(rel, `${r.id}: product must have ν>0 and initial 0`);
    if (r.role !== "product" && !(r.nu < 0)) fail(rel, `${r.id}: reactant must have ν<0`);
    if (r.role === "limiting" && !near(Number(r.final_mol), 0))
      fail(rel, `${r.id}: limiting but final_mol ${r.final_mol} != 0`);
    if (r.role === "excess" && !(Number(r.final_mol) > 0))
      fail(rel, `${r.id}: excess but nothing left over`);
    byId[r.id] = r;
    rows++;
  }

  // the reported limiting set is exactly the rows tagged limiting
  const tagged = L.species.filter((r) => r.role === "limiting").map((r) => r.id).sort();
  if (JSON.stringify(tagged) !== JSON.stringify([...L.limiting].sort()))
    fail(rel, `ledger.limiting ${JSON.stringify(L.limiting)} disagrees with rows tagged limiting ${JSON.stringify(tagged)}`);

  // the reported result must agree with the ledger rows it summarizes. The reported product is the
  // precipitate (a solid) or the general `product` (water, for neutralization — ADR-0037); a neutralization
  // also names the dissolved `salt`. Each must match its ledger final mole count, and its mass = moles × M.
  const precip = sol.result.precipitate ?? sol.result.product;
  for (const rep of [precip, sol.result.salt].filter(Boolean)) {
    const prow = byId[rep.species];
    if (!prow) fail(rel, `result product ${rep.species} has no ledger row`);
    if (!near(Number(rep.moles), Number(prow.final_mol)))
      fail(rel, `product ${rep.species} moles ${rep.moles} != ledger final ${prow.final_mol}`);
    if (!near(Number(rep.mass_g), Number(rep.moles) * Number(rep.molar_mass_g_per_mol)))
      fail(rel, `product ${rep.species} mass ${rep.mass_g} != moles × molar mass`);
  }
  for (const lo of sol.result.leftover ?? []) {
    const lrow = byId[lo.species];
    if (!lrow) fail(rel, `leftover ${lo.species} has no ledger row`);
    if (!near(Number(lo.moles), Number(lrow.final_mol)))
      fail(rel, `leftover ${lo.species} moles ${lo.moles} != ledger final ${lrow.final_mol}`);
  }

  // gas stoichiometry (ADR-0041): the collected gas's VOLUME rides on PV=nRT. Its moles are ledger-exact
  // (already checked above as the reported product); here re-derive V = nRT/P numerically from the emitted
  // state + the sourced gas constant R, independent of Python. Model-exact-then-rounded (R is non-terminating):
  // volume_L is a 4-sig-fig value, so the 0.5% tolerance sits above the rounding (~0.05%) and well below the
  // ~8% STP-22.4-L misconception gap. Temperature is absolute (K); a stated °C converts at the boundary
  // (K = °C + 273.15 — an affine offset, ADR-0040).
  const gas = sol.result.gas;
  if (gas) {
    const relClose = (got, want) => Math.abs(got - want) <= 0.005 * Math.abs(want) + 1e-9;
    if (gas.phase !== "g") fail(rel, `gas ${gas.species} phase ${gas.phase} != g`);
    if (!near(Number(gas.moles), Number(precip.moles)))
      fail(rel, `gas moles ${gas.moles} != reported product moles ${precip.moles}`);
    if (gas.temperature_C !== undefined &&
        Math.abs(Number(gas.temperature_C) + 273.15 - Number(gas.temperature_K)) > 1e-9)
      fail(rel, `gas ${gas.temperature_C} °C + 273.15 != ${gas.temperature_K} K`);
    const n = Number(gas.moles), R = Number(gas.gas_constant);
    const T = Number(gas.temperature_K), P = Number(gas.pressure_atm);
    if (!(R > 0 && T > 0 && P > 0)) fail(rel, `gas state must be positive (R=${R}, T=${T}, P=${P})`);
    const V = (n * R * T) / P, molar = (R * T) / P;
    if (!relClose(V, Number(gas.volume_L)))
      fail(rel, `gas volume_L ${gas.volume_L} != re-derived nRT/P = ${V.toFixed(6)}`);
    if (!relClose(V, Number(gas.volume_L_display)))
      fail(rel, `gas volume_L_display ${gas.volume_L_display} != re-derived nRT/P = ${V.toFixed(6)}`);
    if (!relClose(molar, Number(gas.molar_volume_L_per_mol_display)))
      fail(rel, `gas molar volume ${gas.molar_volume_L_per_mol_display} != re-derived RT/P = ${molar.toFixed(6)}`);
    gases++;
  }

  // percent yield (ADR-0029): the theoretical yield IS the precipitate mass; the reported percent must be
  // actual ÷ theoretical × 100 (re-derived here, then rounded to the emitted 3-sig-fig display), and the
  // actual yield must be physical (0 < actual ≤ theoretical — you cannot collect more than forms).
  const py = sol.result.percent_yield;
  if (py) {
    if (!near(Number(py.theoretical_mass_g), Number(precip.mass_g)))
      fail(rel, `theoretical yield ${py.theoretical_mass_g} != precipitate mass ${precip.mass_g}`);
    const actual = Number(py.actual_mass_g), theo = Number(py.theoretical_mass_g);
    if (!(actual > 0 && actual <= theo + TOL))
      fail(rel, `actual yield ${py.actual_mass_g} must be > 0 and ≤ theoretical ${py.theoretical_mass_g}`);
    const rePercent = (actual / theo) * 100;    // must round to the emitted display (reported to 0.1%)
    if (Math.abs(rePercent - Number(py.percent_display)) > 0.05 + 1e-9)
      fail(rel, `percent_display ${py.percent_display} != actual/theoretical*100 = ${rePercent.toFixed(4)}`);
  }
}

console.log(`check-ledger: ${files.length} ledger(s), ${rows} row(s) satisfy n = n0 + ν·ξ and match the result` +
  (gases ? `; ${gases} gas volume(s) re-derived from PV=nRT.` : "."));
