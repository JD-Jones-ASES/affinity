// validate-gyms.mjs — gate for the Phase-1 procedural gyms (ADR-0024). Ajv-validates every
// derived/gyms/*.gym.json against the schema, then RE-DERIVES every problem's answer in pure Node from its
// raw derivation inputs (the honesty check: the committed answer must reproduce from V/M/mass/molar-mass,
// independent of Python) and checks the response invariants per mode (ADR-0032): a categorical answer is a
// multiple-choice menu (exactly one correct, distinct, equals the answer); a numeric answer is free entry, so
// it carries a diagnostics catalogue (each value distinct from the answer) and NO gameable menu. CI re-proves
// the whole set with no Python. Fails loud (exit 1).

import { readFileSync, existsSync, readdirSync } from "node:fs";
import { join } from "node:path";
import Ajv from "ajv/dist/2020.js";
import addFormats from "ajv-formats";
import { parseFormula } from "./formula.mjs";
import { verifyBalance } from "./balancecheck.mjs";

const ROOT = process.cwd();
const gymDir = join(ROOT, "derived", "gyms");
if (!existsSync(gymDir)) {
  console.log("validate-gyms: no derived/gyms/ — nothing to check.");
  process.exit(0);
}

const ajv = new Ajv({ allErrors: true, strict: true });
addFormats(ajv);
const validate = ajv.compile(JSON.parse(readFileSync(join(ROOT, "schemas", "gym.schema.json"), "utf8")));

const fail = (file, msg) => { console.error(`GYM GATE FAILED — ${file}: ${msg}`); process.exit(1); };

const ATOL = 1e-9, RTOL = 1e-9;
const close = (got, want) => Math.abs(got - want) <= ATOL + RTOL * Math.abs(want);

// numeric-answer kinds are free-entry drills (ADR-0032): they carry a diagnostics catalogue, not a choice menu.
const NUMERIC_KINDS = new Set([
  "volume_molarity_to_moles", "moles_molarity_to_volume", "mass_to_moles", "moles_to_mass",
  "volume_molarity_to_mass", "mass_stoichiometry", "percent_yield", "limiting_mass",
  "gas_ideal", "gas_combined",
]);

// re-derive an answer purely from the raw inputs — the same arithmetic a student does, unit by unit
function rederive(kind, i, rel, id) {
  const num = (k) => {
    if (!(k in i)) fail(rel, `${id}: derivation.inputs missing '${k}' for kind ${kind}`);
    return Number(i[k]);
  };
  switch (kind) {
    case "volume_molarity_to_moles": return (num("v_mL") / 1000) * num("c_M");
    case "moles_molarity_to_volume": return (num("n_mol") / num("c_M")) * 1000;
    case "mass_to_moles": return num("m_g") / num("molar_mass_g_per_mol");
    case "moles_to_mass": return num("n_mol") * num("molar_mass_g_per_mol");
    case "volume_molarity_to_mass": return (num("v_mL") / 1000) * num("c_M") * num("molar_mass_g_per_mol");
    default: fail(rel, `${id}: unknown derivation kind '${kind}'`);
  }
}

// --- ionic nomenclature re-derivation (ADR-0027): re-run the charge crossover + name assembly in pure Node,
// independent of the Python producer, from the emitted ion parts. No formula parser needed — crossover is
// gcd arithmetic + string assembly, and the name is just cation + anion compound_names.
const gcd = (a, b) => { a = Math.abs(a); b = Math.abs(b); while (b) { [a, b] = [b, a % b]; } return a; };
const MONO = /^[A-Z][a-z]?$/;
const groupPart = (part, n) => (n === 1 ? part : (MONO.test(part) ? `${part}${n}` : `(${part})${n}`));
function crossoverFormula(cat, an) {
  const c = cat.charge, a = -an.charge;           // positive magnitudes
  const g = gcd(c, a);
  return groupPart(cat.formula_part, a / g) + groupPart(an.formula_part, c / g);
}

// --- balancing re-verification (ADR-0028): re-parse each species formula in pure Node (formula.mjs), confirm
// the emitted counts+charge match that independent parse, then verify the emitted coefficient vector zeroes
// every element row AND the charge row of the conservation matrix (the definition of a balanced equation),
// is all-positive and reduced (gcd 1), and reconstructs to the emitted answer. No null-space solve — Python
// owns uniqueness (balance() requires a 1-D null space); the gate proves the emitted answer is a true,
// reduced balance of the exact formulas shown to the student.
const eqSide = (species, coeffs, role) =>
  species.map((s, i) => [s, coeffs[i]]).filter(([s]) => s.role === role)
    .map(([s, c]) => (c === 1 ? "" : `${c} `) + s.formula).join(" + ");
const reconstructEquation = (species, coeffs, arrow) =>
  `${eqSide(species, coeffs, "reactant")} ${arrow} ${eqSide(species, coeffs, "product")}`;

// verifyBalance (the coefficient-vector re-prover) now lives in balancecheck.mjs, shared with the
// reaction-family gate (ADR-0035); imported above. The balancing and stoichiometry branches call it below.

function verifyBalancing(rel, p, fail) {
  const d = p.derivation;
  verifyBalance(rel, p.id, d.species, d.coefficients, fail);
  // the answer reconstructs from species + coefficients: CSV value, "→" display, and the skeletal prompt
  const csv = d.coefficients.join(",");
  if (p.answer.value !== csv) fail(rel, `${p.id}: answer.value '${p.answer.value}' != coefficients '${csv}'`);
  const eq = reconstructEquation(d.species, d.coefficients, "→");
  if (p.answer.display !== eq) fail(rel, `${p.id}: answer.display '${p.answer.display}' != reconstructed '${eq}'`);
  if (!p.prompt.includes(reconstructEquation(d.species, d.species.map(() => 1), "→")))
    fail(rel, `${p.id}: prompt does not contain the skeletal (all-coefficient-1) equation`);
}

// stoichiometry (ADR-0029): re-verify the balanced equation (so the mole ratio is a real one), then re-derive
// the mass (or percent yield) numerically from the given/target molar masses + the coefficient ratio — the
// same arithmetic a student does, independent of Python.
function verifyStoich(rel, p, fail) {
  const d = p.derivation;
  verifyBalance(rel, p.id, d.species, d.coefficients, fail);
  const g = d.given, t = d.target;
  if (!g || !t) fail(rel, `${p.id}: stoichiometry derivation missing given/target`);
  if (g.index === t.index) fail(rel, `${p.id}: given and target are the same species`);
  for (const part of [g, t]) {
    const sp = d.species[part.index];
    if (!sp || sp.formula !== part.formula) fail(rel, `${p.id}: ${part.formula} not at species index ${part.index}`);
    if (d.coefficients[part.index] !== part.coeff)
      fail(rel, `${p.id}: ${part.formula} coeff ${part.coeff} != coefficients[${part.index}]=${d.coefficients[part.index]}`);
  }
  const theoretical = (Number(g.mass_g) / Number(g.molar_mass_g_per_mol))
    * (t.coeff / g.coeff) * Number(t.molar_mass_g_per_mol);

  if (p.kind === "mass_stoichiometry") {
    if (!close(theoretical, Number(p.answer.value)))
      fail(rel, `${p.id}: mass ${p.answer.value} != re-derived ${theoretical}`);
  } else { // percent_yield
    if (d.theoretical_mass_g == null || d.actual_mass_g == null)
      fail(rel, `${p.id}: percent_yield missing theoretical/actual mass`);
    if (!close(theoretical, Number(d.theoretical_mass_g)))
      fail(rel, `${p.id}: theoretical ${d.theoretical_mass_g} != re-derived ${theoretical}`);
    const percent = (Number(d.actual_mass_g) / theoretical) * 100;
    if (!close(percent, Number(p.answer.value)))
      fail(rel, `${p.id}: percent ${p.answer.value} != re-derived ${percent}`);
  }

  // units line up and the chain ends at the answer (as with the conversion gym)
  if (p.answer.unit !== p.target_unit) fail(rel, `${p.id}: answer unit '${p.answer.unit}' != target_unit '${p.target_unit}'`);
  const last = p.chain[p.chain.length - 1];
  if (last.unit !== p.target_unit) fail(rel, `${p.id}: chain ends in '${last.unit}', not target '${p.target_unit}'`);
  if (!close(Number(last.value), Number(p.answer.value))) fail(rel, `${p.id}: chain end ${last.value} != answer ${p.answer.value}`);
}

// limiting reagent from masses (ADR-0029): re-verify the balance, re-compute each reactant's reaction extent
// (moles ÷ coefficient), confirm the emitted limiting reagent is the smaller one, and re-derive the maximum
// product mass from that extent — independent of Python.
function verifyLimiting(rel, p, fail) {
  const d = p.derivation;
  verifyBalance(rel, p.id, d.species, d.coefficients, fail);
  if (!Array.isArray(d.reactants) || d.reactants.length < 2 || !d.target)
    fail(rel, `${p.id}: limiting_mass derivation missing reactants/target`);
  for (const part of [...d.reactants, d.target]) {
    const sp = d.species[part.index];
    if (!sp || sp.formula !== part.formula) fail(rel, `${p.id}: ${part.formula} not at species index ${part.index}`);
    if (d.coefficients[part.index] !== part.coeff)
      fail(rel, `${p.id}: ${part.formula} coeff ${part.coeff} != coefficients[${part.index}]=${d.coefficients[part.index]}`);
  }
  const extents = d.reactants.map((r) => (Number(r.mass_g) / Number(r.molar_mass_g_per_mol)) / r.coeff);
  let minI = 0;
  for (let i = 1; i < extents.length; i++) if (extents[i] < extents[minI]) minI = i;
  if (d.reactants[minI].index !== d.limiting_index)
    fail(rel, `${p.id}: limiting reagent is ${d.reactants[minI].formula} (index ${d.reactants[minI].index}), not emitted index ${d.limiting_index}`);
  const theoretical = extents[minI] * d.target.coeff * Number(d.target.molar_mass_g_per_mol);
  if (!close(theoretical, Number(p.answer.value)))
    fail(rel, `${p.id}: product mass ${p.answer.value} != re-derived ${theoretical}`);
  if (p.answer.unit !== p.target_unit) fail(rel, `${p.id}: answer unit '${p.answer.unit}' != target_unit '${p.target_unit}'`);
  const last = p.chain[p.chain.length - 1];
  if (last.unit !== p.target_unit) fail(rel, `${p.id}: chain ends in '${last.unit}', not target '${p.target_unit}'`);
  if (!close(Number(last.value), Number(p.answer.value))) fail(rel, `${p.id}: chain end ${last.value} != answer ${p.answer.value}`);
}

// --- periodic trends (ADR-0034): the drills embed sourced property values and predicted ions; the gate
// re-compares/re-sorts them numerically AND cross-checks every embedded symbol, value, and ion against the
// committed valence-table.json — the gym and the Valence Table must tell one story (the molar-mass-
// consistency idea extended to reference data).
let _vt = null;
function valenceTable(rel) {
  if (_vt) return _vt;
  const p = join(ROOT, "derived", "reference", "valence-table.json");
  if (!existsSync(p)) fail(rel, "periodic-trends gym needs derived/reference/valence-table.json — run produce");
  const t = JSON.parse(readFileSync(p, "utf8"));
  _vt = { bySym: new Map(t.elements.map((e) => [e.symbol, e])) };
  return _vt;
}

function checkCandidates(rel, p, fail) {
  const { bySym } = valenceTable(rel);
  const d = p.derivation;
  for (const c of d.candidates) {
    const el = bySym.get(c.symbol);
    if (!el) fail(rel, `${p.id}: '${c.symbol}' is not a Valence-Table element`);
    if (el[d.property] !== c.value)
      fail(rel, `${p.id}: ${c.symbol} ${d.property} '${c.value}' != table '${el[d.property]}'`);
    if (el.block !== "s" && el.block !== "p") fail(rel, `${p.id}: '${c.symbol}' is d-block — not a trend series member`);
    if (c.symbol === "H") fail(rel, `${p.id}: H is excluded from trend series (conventional placement)`);
    const pos = d.series.kind === "period" ? el.period : el.group;
    if (pos !== d.series.n) fail(rel, `${p.id}: ${c.symbol} is not in ${d.series.kind} ${d.series.n}`);
  }
  const values = d.candidates.map((c) => Number(c.value));
  if (values.some((v) => !Number.isFinite(v))) fail(rel, `${p.id}: non-numeric candidate value`);
  return values;
}

function verifyTrendCompare(rel, p, fail) {
  const { bySym } = valenceTable(rel);
  const d = p.derivation;
  const values = checkCandidates(rel, p, fail);
  const extreme = d.direction === "max" ? Math.max(...values) : Math.min(...values);
  if (values.filter((v) => v === extreme).length !== 1) fail(rel, `${p.id}: tied extreme — ambiguous answer`);
  const winner = d.candidates[values.indexOf(extreme)].symbol;
  if (p.answer.value !== winner) fail(rel, `${p.id}: answer '${p.answer.value}' != re-derived extreme '${winner}'`);
  if (p.answer.display !== `${winner} (${bySym.get(winner).name})`)
    fail(rel, `${p.id}: answer display '${p.answer.display}' != '${winner} (${bySym.get(winner).name})'`);
}

function verifyOrderIonization(rel, p, fail) {
  const d = p.derivation;
  if (d.property !== "first_ionization_kj_mol") fail(rel, `${p.id}: order_ionization on '${d.property}'`);
  const values = checkCandidates(rel, p, fail);
  const ascending = d.candidates.map((c, i) => [c.symbol, values[i]]).sort((a, b) => a[1] - b[1]).map(([s]) => s);
  if (p.answer.value !== ascending.join(",")) fail(rel, `${p.id}: answer '${p.answer.value}' != re-sorted '${ascending.join(",")}'`);
  if (p.answer.display !== ascending.join(" < ")) fail(rel, `${p.id}: answer display mismatches the re-sorted order`);
}

function verifyPredictIon(rel, p, fail) {
  const { bySym } = valenceTable(rel);
  const d = p.derivation;
  const el = bySym.get(d.element);
  if (!el) fail(rel, `${p.id}: '${d.element}' is not a Valence-Table element`);
  if (!el.common_ion) fail(rel, `${p.id}: '${d.element}' has no common ion in the table`);
  if (el.other_ions?.length) fail(rel, `${p.id}: '${d.element}' is variable-charge — 'the' common ion is ambiguous`);
  if (el.common_ion.id !== d.ion.id || el.common_ion.charge !== d.ion.charge)
    fail(rel, `${p.id}: ion ${d.ion.id} (${d.ion.charge}) != table common ion ${el.common_ion.id} (${el.common_ion.charge})`);
  if (p.answer.value !== d.ion.id) fail(rel, `${p.id}: answer '${p.answer.value}' != ion '${d.ion.id}'`);
}

// --- reaction families (ADR-0035/0036): re-prove the molecular equation balances (so the shown reaction is
// real); for name_spectators additionally re-prove the NET equation balances (atoms + charge) and that every
// claimed spectator is ABSENT from the net equation — a spectator, by definition, cancels. The family LABEL
// and the spectator SET are the tested Python classifier's/net_ionic's (as with the reaction-family Atlas,
// ADR-0035); the gate re-derives the balance-checkable claims and the spectator/net-equation invariants.
function verifyReactionFamily(rel, p, fail) {
  const d = p.derivation;
  verifyBalance(rel, p.id, d.species, d.coefficients, fail);
  if (p.kind === "classify_family") {
    if (p.answer.value !== d.family) fail(rel, `${p.id}: answer '${p.answer.value}' != derivation family '${d.family}'`);
  } else { // name_spectators
    if (!Array.isArray(d.net_species) || !Array.isArray(d.spectators) || !d.spectators.length)
      fail(rel, `${p.id}: name_spectators derivation missing net_species/spectators`);
    verifyBalance(rel, `${p.id}(net)`, d.net_species, d.net_coefficients, fail);   // the net eq conserves atoms + charge
    const netFormulas = new Set(d.net_species.map((s) => s.formula));
    for (const sp of d.spectators)
      if (netFormulas.has(sp)) fail(rel, `${p.id}: '${sp}' is claimed a spectator but appears in the net ionic equation`);
    if (p.answer.value !== d.spectators.join(","))
      fail(rel, `${p.id}: answer '${p.answer.value}' != spectators '${d.spectators.join(",")}'`);
  }
}

// --- gas laws (Phase 2, ADR-0040): re-derive the answer numerically from the emitted state values + the
// sourced gas constant R (ideal) or from the two states (combined). The answer is model-exact-then-rounded to
// 4 sig figs, so the tolerance sits above the rounding (~0.05%) but well below the 3% diagnostic gap. The
// dimensions were certified at emit time by the units engine (ADR-0040); here we re-prove the arithmetic.
function verifyGasLaw(rel, p, fail) {
  const d = p.derivation.gas;
  if (!d || !d.solve_for) fail(rel, `${p.id}: gas derivation missing solve_for`);
  const num = (k) => { if (!(k in d)) fail(rel, `${p.id}: gas derivation missing '${k}' for ${p.kind}/${d.solve_for}`); return Number(d[k]); };
  let got;
  if (p.kind === "gas_ideal") {
    const R = num("R");
    if (d.solve_for === "P") got = (num("n_mol") * R * num("T_K")) / num("V_L");
    else if (d.solve_for === "V") got = (num("n_mol") * R * num("T_K")) / num("P_atm");
    else if (d.solve_for === "n") got = (num("P_atm") * num("V_L")) / (R * num("T_K"));
    else if (d.solve_for === "T") got = (num("P_atm") * num("V_L")) / (num("n_mol") * R);
    else fail(rel, `${p.id}: unknown ideal solve_for '${d.solve_for}'`);
  } else { // gas_combined — P1V1/T1 = P2V2/T2 (R cancels)
    const K = (num("P1_atm") * num("V1_L")) / num("T1_K");
    if (d.solve_for === "P2") got = (K * num("T2_K")) / num("V2_L");
    else if (d.solve_for === "V2") got = (K * num("T2_K")) / num("P2_atm");
    else if (d.solve_for === "T2") got = (num("P2_atm") * num("V2_L")) / K;
    else fail(rel, `${p.id}: unknown combined solve_for '${d.solve_for}'`);
  }
  const want = Number(p.answer.value);
  if (!Number.isFinite(got)) fail(rel, `${p.id}: gas re-derivation is not finite`);
  if (Math.abs(got - want) > 0.005 * Math.abs(want) + 1e-9)
    fail(rel, `${p.id}: answer ${p.answer.value} != re-derived ${got} (Δrel=${(Math.abs(got - want) / Math.abs(want)).toExponential(2)})`);
  if (p.answer.unit !== p.target_unit) fail(rel, `${p.id}: answer unit '${p.answer.unit}' != target_unit '${p.target_unit}'`);
  const last = p.chain[p.chain.length - 1];
  if (last.unit !== p.target_unit) fail(rel, `${p.id}: chain ends in '${last.unit}', not target '${p.target_unit}'`);
  if (Math.abs(Number(last.value) - want) > 0.01 * Math.abs(want) + 1e-9)
    fail(rel, `${p.id}: chain end ${last.value} != answer ${p.answer.value}`);
}

const files = readdirSync(gymDir).filter((n) => n.endsWith(".gym.json"));
if (files.length === 0) { console.log("validate-gyms: no *.gym.json — nothing to check."); process.exit(0); }

const ids = new Set();
const molarMass = new Map(); // substance -> molar mass string (must be consistent across every problem)
let problemCount = 0;

for (const name of files) {
  const rel = `derived/gyms/${name}`;
  const gym = JSON.parse(readFileSync(join(gymDir, name), "utf8"));
  if (!validate(gym)) fail(rel, ajv.errorsText(validate.errors, { separator: "; " }));

  if (name !== `${gym.slug}.gym.json`) fail(rel, `filename does not match slug '${gym.slug}'`);
  if (ids.has(gym.id)) fail(rel, `duplicate gym id ${gym.id}`);
  ids.add(gym.id);

  for (const p of gym.problems) {
    if (p.derivation.kind !== p.kind) fail(rel, `${p.id}: derivation.kind '${p.derivation.kind}' != problem kind '${p.kind}'`);

    if (p.kind.startsWith("ionic_")) {
      // 1n. nomenclature: re-derive name + formula independently and check the answer + prompt
      const d = p.derivation;
      if (!d.cation || !d.anion || d.formula == null || d.name == null)
        fail(rel, `${p.id}: nomenclature derivation missing cation/anion/formula/name`);
      const reName = `${d.cation.compound_name} ${d.anion.compound_name}`;
      const reFormula = crossoverFormula(d.cation, d.anion);
      if (reName !== d.name) fail(rel, `${p.id}: re-derived name '${reName}' != emitted '${d.name}'`);
      if (reFormula !== d.formula) fail(rel, `${p.id}: re-derived formula '${reFormula}' != emitted '${d.formula}'`);
      const want = p.kind === "ionic_formula_to_name" ? d.name : d.formula;
      const other = p.kind === "ionic_formula_to_name" ? d.formula : d.name;
      if (p.answer.value !== want) fail(rel, `${p.id}: answer '${p.answer.value}' != re-derived '${want}'`);
      if (!p.prompt.includes(other)) fail(rel, `${p.id}: prompt does not contain the ${p.kind === "ionic_formula_to_name" ? "formula" : "name"} '${other}'`);
    } else if (p.kind === "balancing") {
      // 1b. balancing: re-parse the formulas, verify the coefficients zero every element + charge row (ADR-0028)
      verifyBalancing(rel, p, fail);
    } else if (p.kind === "mass_stoichiometry" || p.kind === "percent_yield") {
      // 1s. stoichiometry: re-verify the balanced equation + re-derive the mass/percent numerically (ADR-0029)
      verifyStoich(rel, p, fail);
    } else if (p.kind === "limiting_mass") {
      // 1L. limiting reagent from masses: re-derive extents, confirm the limiter + the product mass (ADR-0029)
      verifyLimiting(rel, p, fail);
    } else if (p.kind === "trend_compare") {
      // 1t. periodic trends: re-compare the sourced values + cross-check them against the table (ADR-0034)
      verifyTrendCompare(rel, p, fail);
    } else if (p.kind === "order_ionization") {
      verifyOrderIonization(rel, p, fail);
    } else if (p.kind === "predict_ion") {
      verifyPredictIon(rel, p, fail);
    } else if (p.kind === "classify_family" || p.kind === "name_spectators") {
      // 1r. reaction families (ADR-0035/0036): re-prove the molecular (and, for spectators, the net) balance
      verifyReactionFamily(rel, p, fail);
    } else if (p.kind === "gas_ideal" || p.kind === "gas_combined") {
      // 1g. gas laws (ADR-0040): re-derive PV=nRT / the combined law numerically from the emitted state + R
      verifyGasLaw(rel, p, fail);
    } else {
      // 1c. conversion: the answer re-derives from the raw inputs; units line up; the chain ends at the answer
      const got = rederive(p.kind, p.derivation.inputs, rel, p.id);
      if (!Number.isFinite(got)) fail(rel, `${p.id}: re-derivation is not finite`);
      if (!close(got, Number(p.answer.value)))
        fail(rel, `${p.id}: answer ${p.answer.value} != re-derived ${got} (Δ=${Math.abs(got - Number(p.answer.value)).toExponential(2)})`);
      if (p.answer.unit !== p.target_unit) fail(rel, `${p.id}: answer unit '${p.answer.unit}' != target_unit '${p.target_unit}'`);
      const last = p.chain[p.chain.length - 1];
      if (last.unit !== p.target_unit) fail(rel, `${p.id}: chain ends in '${last.unit}', not target '${p.target_unit}'`);
      if (!close(Number(last.value), Number(p.answer.value))) fail(rel, `${p.id}: chain end ${last.value} != answer ${p.answer.value}`);
    }

    // 2. response, mode-aware (ADR-0032). A categorical answer is a multiple-choice menu (exactly one correct,
    //    distinct displays, the correct one equals the answer, every wrong choice names a mistake). A numeric
    //    answer is FREE-ENTRY — there is deliberately no menu to game — so it carries a diagnostic catalogue
    //    instead, whose values must each be genuinely distinct from the answer (else a correct entry would be
    //    mislabelled a mistake) and name a misconception.
    const expectedMode = NUMERIC_KINDS.has(p.kind) ? "numeric" : "choice";
    if (p.mode !== expectedMode) fail(rel, `${p.id}: mode '${p.mode}' but kind '${p.kind}' expects '${expectedMode}'`);

    if (p.mode === "choice") {
      if (p.diagnostics) fail(rel, `${p.id}: a choice problem must not carry diagnostics`);
      if (!Array.isArray(p.choices)) fail(rel, `${p.id}: choice problem missing choices`);
      const correct = p.choices.filter((c) => c.correct);
      if (correct.length !== 1) fail(rel, `${p.id}: ${correct.length} correct choices (want exactly 1)`);
      if (correct[0].display !== p.answer.display) fail(rel, `${p.id}: correct choice '${correct[0].display}' != answer.display '${p.answer.display}'`);
      const displays = p.choices.map((c) => c.display);
      if (new Set(displays).size !== displays.length) fail(rel, `${p.id}: choice displays are not distinct`);
      for (const c of p.choices) if (!c.correct && !c.misconception) fail(rel, `${p.id}: a wrong choice has no named misconception`);
    } else {
      if (p.choices) fail(rel, `${p.id}: a numeric answer must not be a multiple-choice menu — it is gameable by magnitude (ADR-0032)`);
      if (!Array.isArray(p.diagnostics)) fail(rel, `${p.id}: numeric problem missing diagnostics`);
      const ans = Number(p.answer.value);
      if (!Number.isFinite(ans)) fail(rel, `${p.id}: numeric answer.value '${p.answer.value}' is not a number`);
      const seen = new Set();
      for (const d of p.diagnostics) {
        if (!d.misconception) fail(rel, `${p.id}: a diagnostic has no named misconception`);
        const dv = Number(d.value);
        if (!Number.isFinite(dv)) fail(rel, `${p.id}: diagnostic value '${d.value}' is not a number`);
        if (Math.abs(dv - ans) <= 0.03 * Math.max(Math.abs(ans), 1e-9))
          fail(rel, `${p.id}: diagnostic ${d.value} is within 3% of the answer ${p.answer.value} — the 1% entry tolerance could mis-flag a correct entry`);
        if (d.unit !== p.answer.unit) fail(rel, `${p.id}: diagnostic unit '${d.unit}' != answer unit '${p.answer.unit}'`);
        if (seen.has(d.value)) fail(rel, `${p.id}: duplicate diagnostic value ${d.value}`);
        seen.add(d.value);
      }
    }

    // 3. molar mass is consistent per substance across the WHOLE corpus (conversions ∪ stoichiometry): the
    // same species must carry the same sourced molar mass everywhere it appears.
    const mmPairs = [];
    if (p.derivation.inputs?.molar_mass_g_per_mol != null)
      mmPairs.push([p.derivation.inputs.substance, p.derivation.inputs.molar_mass_g_per_mol]);
    for (const part of [p.derivation.given, p.derivation.target, ...(p.derivation.reactants || [])])
      if (part?.molar_mass_g_per_mol != null) mmPairs.push([part.formula, part.molar_mass_g_per_mol]);
    for (const [sub, mm] of mmPairs) {
      if (molarMass.has(sub) && molarMass.get(sub) !== mm)
        fail(rel, `${p.id}: molar mass ${mm} for ${sub} disagrees with ${molarMass.get(sub)} elsewhere`);
      molarMass.set(sub, mm);
    }
    problemCount++;
  }
}

console.log(`validate-gyms: ${files.length} gym(s), ${problemCount} problem(s) re-derived and consistent; ${ids.size} unique id(s).`);
