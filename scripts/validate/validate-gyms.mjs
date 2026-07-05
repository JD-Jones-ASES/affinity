// validate-gyms.mjs — gate for the Phase-1 procedural gyms (ADR-0024). Ajv-validates every
// derived/gyms/*.gym.json against the schema, then RE-DERIVES every problem's answer in pure Node from its
// raw derivation inputs (the honesty check: the committed answer must reproduce from V/M/mass/molar-mass,
// independent of Python) and checks the choice invariants (exactly one correct, distinct displays, the correct
// choice equals the answer, the chain ends at the answer). CI re-proves the whole set with no Python. Fails
// loud (exit 1).

import { readFileSync, existsSync, readdirSync } from "node:fs";
import { join } from "node:path";
import Ajv from "ajv/dist/2020.js";
import addFormats from "ajv-formats";

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

    // 2. choices: exactly one correct, distinct displays, the correct one is the answer, wrong ones name a mistake
    const correct = p.choices.filter((c) => c.correct);
    if (correct.length !== 1) fail(rel, `${p.id}: ${correct.length} correct choices (want exactly 1)`);
    if (correct[0].display !== p.answer.display) fail(rel, `${p.id}: correct choice '${correct[0].display}' != answer.display '${p.answer.display}'`);
    const displays = p.choices.map((c) => c.display);
    if (new Set(displays).size !== displays.length) fail(rel, `${p.id}: choice displays are not distinct`);
    for (const c of p.choices) if (!c.correct && !c.misconception) fail(rel, `${p.id}: a wrong choice has no named misconception`);

    // 3. molar mass is consistent per substance across the whole corpus (conversion problems only)
    const mm = p.derivation.inputs?.molar_mass_g_per_mol;
    if (mm != null) {
      const sub = p.derivation.inputs.substance;
      if (molarMass.has(sub) && molarMass.get(sub) !== mm)
        fail(rel, `${p.id}: molar mass ${mm} for ${sub} disagrees with ${molarMass.get(sub)} elsewhere`);
      molarMass.set(sub, mm);
    }
    problemCount++;
  }
}

console.log(`validate-gyms: ${files.length} gym(s), ${problemCount} problem(s) re-derived and consistent; ${ids.size} unique id(s).`);
