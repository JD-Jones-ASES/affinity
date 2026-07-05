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

  // the reported result must agree with the ledger rows it summarizes
  const precip = sol.result.precipitate;
  const prow = byId[precip.species];
  if (!prow) fail(rel, `result precipitate ${precip.species} has no ledger row`);
  if (!near(Number(precip.moles), Number(prow.final_mol)))
    fail(rel, `precipitate moles ${precip.moles} != ledger final ${prow.final_mol}`);
  for (const lo of sol.result.leftover ?? []) {
    const lrow = byId[lo.species];
    if (!lrow) fail(rel, `leftover ${lo.species} has no ledger row`);
    if (!near(Number(lo.moles), Number(lrow.final_mol)))
      fail(rel, `leftover ${lo.species} moles ${lo.moles} != ledger final ${lrow.final_mol}`);
  }
}

console.log(`check-ledger: ${files.length} ledger(s), ${rows} row(s) satisfy n = n0 + ν·ξ and match the result.`);
