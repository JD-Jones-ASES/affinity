// Gate: schema-validate every derived solution JSON with Ajv, then run the honesty cross-checks that the
// schema shape alone can't express (ADR-0019). Pure Node — CI re-verifies the committed output with no
// Python. Fails loud (exit 1) on the first problem.

import { readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";
import Ajv from "ajv/dist/2020.js";
import addFormats from "ajv-formats";
import { verifyElectronLedger, ledgerTables, classifyIMF } from "./structurecheck.mjs";
import { verifyEquilibrium } from "./equilibriumcheck.mjs";

const ROOT = process.cwd();
const schema = JSON.parse(readFileSync(join(ROOT, "schemas", "solution.schema.json"), "utf8"));
const structureSchema = JSON.parse(readFileSync(join(ROOT, "schemas", "structure-lesson.schema.json"), "utf8"));
const comparisonSchema = JSON.parse(readFileSync(join(ROOT, "schemas", "comparison-lesson.schema.json"), "utf8"));
const equilibriumSchema = JSON.parse(readFileSync(join(ROOT, "schemas", "equilibrium-lesson.schema.json"), "utf8"));
const ajv = new Ajv({ allErrors: true, strict: true });
addFormats(ajv);
const validate = ajv.compile(schema);
const validateStructure = ajv.compile(structureSchema);
const validateComparison = ajv.compile(comparisonSchema);
const validateEquilibrium = ajv.compile(equilibriumSchema);
const IMF_RANK = { "london-dispersion": 1, "dipole-dipole": 2, "hydrogen-bonding": 3 };

// walk derived/ for lesson files matching a suffix (*.solution.json reactions, *.structure.json structures)
function walkSuffix(dir, suffix) {
  const out = [];
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) out.push(...walkSuffix(p, suffix));
    else if (name.endsWith(suffix)) out.push(p);
  }
  return out;
}
const walk = (dir) => walkSuffix(dir, ".solution.json");

const derived = join(ROOT, "derived");
let files = [];
try {
  files = walk(derived);
} catch {
  console.error("no derived/ directory — run `npm run produce` first");
  process.exit(1);
}
if (files.length === 0) {
  console.error("no *.solution.json under derived/");
  process.exit(1);
}

const fail = (file, msg) => {
  console.error(`GATE FAILED — ${file}: ${msg}`);
  process.exit(1);
};

const ids = new Set();
for (const file of files) {
  const rel = file.slice(ROOT.length + 1).replaceAll("\\", "/");
  const sol = JSON.parse(readFileSync(file, "utf8"));

  if (!validate(sol)) fail(rel, ajv.errorsText(validate.errors, { separator: "; " }));

  // 1. derived path must match declared topic/slug
  const expected = `derived/${sol.topic}/${sol.slug}.solution.json`;
  if (rel !== expected) fail(rel, `path does not match topic/slug (expected ${expected})`);

  // 2. unique ids across the corpus
  if (ids.has(sol.id)) fail(rel, `duplicate id ${sol.id}`);
  ids.add(sol.id);

  // 3. every check must hold (schema pins them const:true; assert here too as the honesty gate)
  for (const [k, v] of Object.entries(sol.checks)) if (v !== true) fail(rel, `check ${k} is not true`);

  // 4. a rule-sourced regime requires a cited solubility_basis with a source
  if (sol.regimes.some((r) => r.regime === "rule-sourced")) {
    if (!sol.solubility_basis || !sol.solubility_basis.source)
      fail(rel, "regime rule-sourced present but no solubility_basis.source");
  }

  // 5. ledger integrity: exactly the limiting rows have role "limiting" and final_mol 0; extent > 0
  const limiting = sol.ledger.species.filter((s) => s.role === "limiting");
  if (limiting.length !== sol.ledger.limiting.length)
    fail(rel, "ledger.limiting count disagrees with rows tagged limiting");
  for (const s of limiting) if (Number(s.final_mol) !== 0) fail(rel, `${s.id} limiting but final_mol != 0`);
  if (!(Number(sol.ledger.extent_mol) > 0)) fail(rel, "extent_mol is not positive");

  // 6. every reactant row consumes (nu<0), every product forms (nu>0); charges are integers
  for (const s of sol.ledger.species) {
    if (s.role === "product" && s.nu <= 0) fail(rel, `${s.id} is a product but nu <= 0`);
    if (s.role !== "product" && s.nu >= 0) fail(rel, `${s.id} is a reactant but nu >= 0`);
  }

  // 7. the reported product (ADR-0037): a precipitation/neutralization/gas lesson carries exactly one of
  // `precipitate` (a solid) or the general `product`, a product row in the ledger of the right phase. An
  // energy-ledger lesson (ADR-0043) carries NEITHER — its headline is `result.energy` (the heat q = ΔH_rxn·ξ),
  // and the products are just ledger rows.
  const rep = sol.result.precipitate ?? sol.result.product;
  if (sol.result.energy) {
    if (rep) fail(rel, `an energy-ledger result must not also carry a precipitate/product headline`);
  } else {
    if (!rep || (sol.result.precipitate && sol.result.product))
      fail(rel, `result must carry exactly one of precipitate/product`);
    const row = sol.ledger.species.find((s) => s.id === rep.species && s.role === "product");
    if (!row) fail(rel, `result product ${rep.species} is not a product ledger row`);
    if (sol.result.precipitate && row.phase !== "s") fail(rel, `result precipitate ${rep.species} is not a solid ledger row`);
    if (row.phase !== rep.phase) fail(rel, `result product ${rep.species} phase ${rep.phase} != ledger ${row.phase}`);
  }

  // 8. provenance sources must be non-empty (every empirical value is traceable)
  for (const [k, v] of Object.entries(sol.provenance.sources))
    if (!v) fail(rel, `provenance.sources.${k} is empty`);

  // 9. gas stoichiometry (ADR-0041): the reported product IS the collected gas (phase g); the ideal-gas volume
  // is regime-2, so it must carry a model-exact regime + a disclosed model assumption (the model-assumed badge
  // does the honesty work) and cite the gas constant's source. Ties the volume to its disclosure.
  if (sol.result.gas) {
    const g = sol.result.gas;
    if (rep.species !== g.species || rep.phase !== "g")
      fail(rel, `result.gas ${g.species} must be the reported product and gas-phase (product is ${rep.species}/${rep.phase})`);
    if (!sol.regimes.some((r) => r.regime === "model-exact"))
      fail(rel, "result.gas present but no model-exact regime — the ideal-gas volume is regime-2");
    if (!sol.assumptions.some((a) => a.kind === "model"))
      fail(rel, "result.gas present but no disclosed model assumption");
    if (!sol.provenance.sources.constants)
      fail(rel, "result.gas present but provenance.sources.constants (the gas constant's source) is missing");
  }

  // 10. the energy ledger (ADR-0043): q = ΔH_rxn·ξ is model-exact (Hess's law + complete reaction at constant
  // pressure), so it must carry a model-exact regime + a disclosed model assumption (the model-assumed badge
  // does the honesty work) and cite the ΔH_f° source (the data-sourced badge). Every Hess row must be a real
  // ledger species whose role/phase agree. (check-ledger re-derives the Hess sum + q arithmetically.)
  if (sol.result.energy) {
    const e = sol.result.energy;
    if (!sol.regimes.some((r) => r.regime === "model-exact"))
      fail(rel, "result.energy present but no model-exact regime — the reaction enthalpy is regime-2");
    if (!sol.assumptions.some((a) => a.kind === "model"))
      fail(rel, "result.energy present but no disclosed model assumption");
    if (!sol.provenance.sources.formation_enthalpies)
      fail(rel, "result.energy present but provenance.sources.formation_enthalpies (the ΔH_f° source) is missing");
    for (const h of e.hess) {
      const hrow = sol.ledger.species.find((s) => s.id === h.species);
      if (!hrow) fail(rel, `energy Hess species ${h.species} is not a ledger species`);
      if ((h.role === "product") !== (hrow.role === "product"))
        fail(rel, `energy Hess species ${h.species} role ${h.role} disagrees with the ledger (${hrow.role})`);
      if (hrow.phase !== h.phase)
        fail(rel, `energy Hess species ${h.species} phase ${h.phase} != ledger ${hrow.phase}`);
    }
  }
}

// ── structure lessons (ADR-0045): a single-molecule lesson, its own tight schema. The Lewis ELECTRON ledger is
// re-derived in pure Node by the SHARED engine (structurecheck.mjs) — the same one the molecule Atlas kind uses,
// so the lesson's claim stands on its own re-proof — and cross-checked against the Atlas molecule with the same
// ref_id (no drift). No equations/species-ledger/reported-product here; the electron ledger IS the object.
const structureFiles = walkSuffix(derived, ".structure.json");
const comparisonFiles = walkSuffix(derived, ".comparison.json");
const STEP_KEYS = ["valence", "lewis", "shape", "polarity"];
let ledgerT = null;      // built lazily from the emitted valence-table.json
const moleculeById = new Map();
if (structureFiles.length || comparisonFiles.length) {
  const vtPath = join(derived, "reference", "valence-table.json");
  let vt;
  try { vt = JSON.parse(readFileSync(vtPath, "utf8")); }
  catch { fail("derived/reference/valence-table.json", "missing — a structure/comparison lesson needs the Valence Table to re-derive its ledger"); }
  ledgerT = ledgerTables(vt);
  // the molecule Atlas entries, for the no-drift cross-check (structure + comparison lessons)
  const refDir = join(derived, "reference");
  for (const name of readdirSync(refDir).filter((n) => n.endsWith(".json"))) {
    const obj = JSON.parse(readFileSync(join(refDir, name), "utf8"));
    if (obj.kind === "molecule") moleculeById.set(obj.id, obj);
  }
}
for (const file of structureFiles) {
  const rel = file.slice(ROOT.length + 1).replaceAll("\\", "/");
  const les = JSON.parse(readFileSync(file, "utf8"));

  if (!validateStructure(les)) fail(rel, ajv.errorsText(validateStructure.errors, { separator: "; " }));

  // 1. derived path matches declared topic/slug; 2. id unique across ALL lessons (shared set)
  const expected = `derived/${les.topic}/${les.slug}.structure.json`;
  if (rel !== expected) fail(rel, `path does not match topic/slug (expected ${expected})`);
  if (ids.has(les.id)) fail(rel, `duplicate id ${les.id}`);
  ids.add(les.id);

  // 3. every machine-checked fact must hold (schema pins const:true; assert here as the honesty gate)
  for (const [k, v] of Object.entries(les.checks)) if (v !== true) fail(rel, `check ${k} is not true`);

  // 4. the four teaching steps are exactly valence → lewis → shape → polarity, in order
  const keys = les.steps.map((s) => s.key);
  if (keys.length !== 4 || keys.some((k, i) => k !== STEP_KEYS[i]))
    fail(rel, `steps must be ${STEP_KEYS.join(" → ")} in order, got ${keys.join(" → ")}`);

  // 5. the electron ledger re-derives in pure Node (the machine-checked core) — the SAME engine as the Atlas
  verifyElectronLedger(rel, les.molecule, ledgerT, fail);

  // 6. the electron ledger is claimed machine-checked (regime-1); polarity is model-assumed, so a model
  // assumption must be disclosed (the model-assumed badge does honest work) — mirrors the gas/energy gates
  if (!les.regimes.some((r) => r.regime === "ledger-exact"))
    fail(rel, "structure lesson has no ledger-exact regime — the electron ledger is the machine-checked core");
  if (!les.assumptions.some((a) => a.kind === "model"))
    fail(rel, "structure lesson discloses no model assumption (polarity + VSEPR are model-assumed)");

  // 7. the named molecule Atlas entry exists AND the embedded ledger matches it byte-for-byte (no drift): the
  // lesson and the Atlas describe the SAME machine-checked structure (one authored source, ADR-0045).
  const atlas = moleculeById.get(les.molecule.ref_id);
  if (!atlas) fail(rel, `molecule.ref_id '${les.molecule.ref_id}' resolves to no molecule Atlas entry`);
  for (const k of ["formula", "latex", "charge", "valence_electrons", "valence_breakdown", "electron_check",
                   "atoms", "bonds", "geometry", "polarity", "polarity_reason", "names"]) {
    if (JSON.stringify(les.molecule[k]) !== JSON.stringify(atlas[k]))
      fail(rel, `molecule.${k} drifts from the Atlas entry ${les.molecule.ref_id} — the lesson must embed the same structure`);
  }

  // 8. provenance sources non-empty (each is a source id the Atlas molecule already register-checks)
  for (const [k, v] of Object.entries(les.provenance.sources))
    if (!v) fail(rel, `provenance.sources.${k} is empty`);
}

// ── comparison lessons (ADR-0047): several molecules vs. a property, the IMF-strength trend machine-verified.
// The gate re-derives the whole spine: the rows are sorted ascending by boiling point; the dominant-IMF rank is
// non-decreasing (the trend); and each row's dominant IMF + boiling point match the Atlas molecule (no drift —
// the IMF re-derived by classifyIMF from the Atlas structure, the boiling point read off the Atlas entry).
for (const file of comparisonFiles) {
  const rel = file.slice(ROOT.length + 1).replaceAll("\\", "/");
  const les = JSON.parse(readFileSync(file, "utf8"));

  if (!validateComparison(les)) fail(rel, ajv.errorsText(validateComparison.errors, { separator: "; " }));

  const expected = `derived/${les.topic}/${les.slug}.comparison.json`;
  if (rel !== expected) fail(rel, `path does not match topic/slug (expected ${expected})`);
  if (ids.has(les.id)) fail(rel, `duplicate id ${les.id}`);
  ids.add(les.id);
  for (const [k, v] of Object.entries(les.checks)) if (v !== true) fail(rel, `check ${k} is not true`);

  // rows sorted ascending by boiling point; the dominant-IMF rank non-decreasing (the machine-verified trend)
  let prevBp = -Infinity, prevRank = 0;
  for (const r of les.rows) {
    const bp = Number(r.boiling_point_c);
    if (bp < prevBp) fail(rel, `rows not sorted ascending by boiling point (${r.formula} ${r.boiling_point_c} °C after ${prevBp})`);
    if (IMF_RANK[r.dominant] !== r.imf_rank) fail(rel, `${r.formula}: imf_rank ${r.imf_rank} != rank of '${r.dominant}' (${IMF_RANK[r.dominant]})`);
    if (r.imf_rank < prevRank) fail(rel, `IMF trend not monotonic — ${r.formula} (${r.dominant}) at ${r.boiling_point_c} °C ranks below a lower-boiling molecule`);
    if (!r.forces.includes(r.dominant)) fail(rel, `${r.formula}: dominant '${r.dominant}' not among its forces`);
    prevBp = bp; prevRank = r.imf_rank;

    // no drift: the row is re-derived from the Atlas molecule with the same ref_id
    const atlas = moleculeById.get(r.ref_id);
    if (!atlas) fail(rel, `row ref_id '${r.ref_id}' resolves to no molecule Atlas entry`);
    if (!atlas.intermolecular) fail(rel, `row '${r.ref_id}' Atlas entry has no intermolecular block`);
    const want = classifyIMF(atlas.atoms, atlas.bonds, atlas.polarity);
    if (want.dominant !== r.dominant) fail(rel, `${r.formula}: dominant '${r.dominant}' != re-derived '${want.dominant}' from the Atlas structure`);
    if (JSON.stringify(want.forces) !== JSON.stringify(r.forces)) fail(rel, `${r.formula}: forces drift from the Atlas re-derivation`);
    if (atlas.intermolecular.boiling_point_c !== r.boiling_point_c) fail(rel, `${r.formula}: boiling_point_c '${r.boiling_point_c}' != Atlas '${atlas.intermolecular.boiling_point_c}'`);
    if (atlas.formula !== r.formula) fail(rel, `row formula '${r.formula}' != Atlas '${atlas.formula}'`);
  }
  for (const [k, v] of Object.entries(les.provenance.sources)) if (!v) fail(rel, `provenance.sources.${k} is empty`);
}

// ── equilibrium lessons (ADR-0048): the ICE table = the species ledger with the extent solved from mass action.
// The gate re-derives the whole spine in pure Node (equilibriumcheck.mjs): the ICE identity c_i = c_{i,0} + ν_i·x,
// an INDEPENDENT bisection re-solve of the root, the residual Q(committed)=K, the pH, and the percent ionization.
// Honesty is layered: the ICE accounting is machine-checked (regime-1), the equilibrium constant is sourced
// (regime-3), the equilibrium position/pH is a disclosed model (regime-2) — so all three regimes must be present
// and a model assumption disclosed, mirroring the gas/energy gates.
const equilibriumFiles = walkSuffix(derived, ".equilibrium.json");
for (const file of equilibriumFiles) {
  const rel = file.slice(ROOT.length + 1).replaceAll("\\", "/");
  const les = JSON.parse(readFileSync(file, "utf8"));

  if (!validateEquilibrium(les)) fail(rel, ajv.errorsText(validateEquilibrium.errors, { separator: "; " }));

  const expected = `derived/${les.topic}/${les.slug}.equilibrium.json`;
  if (rel !== expected) fail(rel, `path does not match topic/slug (expected ${expected})`);
  if (ids.has(les.id)) fail(rel, `duplicate id ${les.id}`);
  ids.add(les.id);
  for (const [k, v] of Object.entries(les.checks)) if (v !== true) fail(rel, `check ${k} is not true`);

  // honesty shape: all three regimes present; a model assumption disclosed (the equilibrium position is regime-2);
  // the equilibrium constant carries its data source (the data-sourced badge).
  for (const r of ["ledger-exact", "rule-sourced", "model-exact"])
    if (!les.regimes.some((x) => x.regime === r)) fail(rel, `equilibrium lesson missing a ${r} regime`);
  if (!les.assumptions.some((a) => a.kind === "model"))
    fail(rel, "equilibrium lesson discloses no model assumption (the equilibrium position is model-assumed)");
  if (!les.equilibrium_constant.source) fail(rel, "equilibrium_constant.source (the K data source) is missing");
  for (const [k, v] of Object.entries(les.provenance.sources)) if (!v) fail(rel, `provenance.sources.${k} is empty`);

  // subtype-specific field presence (the schema keeps the union optional — strictRequired can't cross subschemas)
  const need = (obj, keys, where) => { for (const k of keys) if (obj[k] === undefined) fail(rel, `${where}.${k} missing for subtype ${les.subtype}`); };
  if (les.subtype === "weak-acid") {
    need(les.reaction, ["acid", "acid_name", "acid_latex", "conjugate_base"], "reaction");
    need(les.result, ["hydronium_M", "hydronium_M_display", "pH", "pH_display", "percent_ionization", "percent_ionization_display"], "result");
    need(les.checks, ["ph_consistent"], "checks");
    need(les.provenance.sources, ["ionization_constants", "ion_charge"], "provenance.sources");
  } else if (les.subtype === "buffer") {
    need(les.reaction, ["acid", "acid_name", "acid_latex", "conjugate_base"], "reaction");
    need(les.result, ["hydronium_M", "hydronium_M_display", "pH", "pH_display", "pKa", "pKa_display", "buffer_ratio", "buffer_ratio_display", "hh_pH", "hh_pH_display", "hydronium_no_buffer_M", "hydronium_no_buffer_M_display", "pH_no_buffer", "pH_no_buffer_display", "suppression_factor_display", "percent_ionization", "percent_ionization_display"], "result");
    need(les.checks, ["hh_consistent"], "checks");
    need(les.provenance.sources, ["ionization_constants", "ion_charge"], "provenance.sources");
  } else if (les.subtype === "weak-base") {
    need(les.reaction, ["base", "base_name", "base_latex", "conjugate_acid"], "reaction");
    need(les.result, ["hydroxide_M", "hydroxide_M_display", "pOH", "pOH_display", "hydronium_M", "hydronium_M_display", "pH", "pH_display", "kw", "percent_ionization", "percent_ionization_display"], "result");
    need(les.checks, ["kw_consistent"], "checks");
    need(les.provenance.sources, ["ionization_constants", "ion_charge"], "provenance.sources");
  } else if (les.subtype === "solubility") {
    need(les.reaction, ["salt", "salt_name", "salt_latex", "cation", "anion"], "reaction");
    need(les.result, ["molar_solubility_M", "molar_solubility_M_display", "solubility_g_per_L", "solubility_g_per_L_display", "molar_mass_g_per_mol"], "result");
    need(les.checks, ["solubility_consistent"], "checks");
    need(les.provenance.sources, ["solubility_products", "ion_charge", "atomic_weight"], "provenance.sources");
    // the common-ion variant carries the ion already present + the pure-water contrast (checked by the gate)
    if (les.reaction.common_ion !== undefined) {
      need(les.reaction, ["common_ion_latex", "common_ion_molarity_M"], "reaction");
      need(les.result, ["molar_solubility_pure_water_M", "molar_solubility_pure_water_M_display", "suppression_factor_display"], "result");
    }
  } else if (les.subtype === "polyprotic") {
    // stage 1 lives in the top-level reaction/ice (weak-acid shape); the later stages + ladder live in result
    need(les.reaction, ["acid", "acid_name", "acid_latex", "conjugate_base"], "reaction");
    need(les.result, ["hydronium_M", "hydronium_M_display", "pH", "pH_display", "percent_ionization",
      "percent_ionization_display", "proton_count", "species_ladder", "later_stages"], "result");
    if (!Array.isArray(les.result.later_stages) || les.result.later_stages.length < 1)
      fail(rel, "polyprotic result.later_stages must list stages 2..n (≥ 1 entry)");
    need(les.checks, ["ph_consistent"], "checks");
    need(les.provenance.sources, ["ionization_constants", "ion_charge"], "provenance.sources");
  } else fail(rel, `unknown equilibrium subtype '${les.subtype}'`);

  // the machine-checked core: re-derive the reversible-extent solve independently of Python
  verifyEquilibrium(rel, les, fail);
}

console.log(`validate-solutions: ${files.length} solution(s) + ${structureFiles.length} structure + ${comparisonFiles.length} comparison + ${equilibriumFiles.length} equilibrium lesson(s) valid; ${ids.size} unique id(s).`);
