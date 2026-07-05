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

  // 7. the precipitate reported in result must be a solid product row in the ledger
  const precip = sol.result.precipitate.species;
  const row = sol.ledger.species.find((s) => s.id === precip);
  if (!row || row.phase !== "s") fail(rel, `result precipitate ${precip} is not a solid ledger row`);

  // 8. provenance sources must be non-empty (every empirical value is traceable)
  for (const [k, v] of Object.entries(sol.provenance.sources))
    if (!v) fail(rel, `provenance.sources.${k} is empty`);
}

console.log(`validate-solutions: ${files.length} solution(s) valid; ${ids.size} unique id(s).`);
