// Gate: schema-validate every derived solution JSON with Ajv, then run the honesty cross-checks that the
// schema shape alone can't express (ADR-0019). Pure Node — CI re-verifies the committed output with no
// Python. Fails loud (exit 1) on the first problem.

import { readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";
import Ajv from "ajv/dist/2020.js";
import addFormats from "ajv-formats";

const ROOT = process.cwd();
const schema = JSON.parse(readFileSync(join(ROOT, "schemas", "solution.schema.json"), "utf8"));
const ajv = new Ajv({ allErrors: true, strict: true });
addFormats(ajv);
const validate = ajv.compile(schema);

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

console.log(`validate-solutions: ${files.length} solution(s) valid; ${ids.size} unique id(s).`);
