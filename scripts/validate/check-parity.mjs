// check-parity.mjs — the parity oracle (ADR-0008, ADR-0011). For every solution carrying an `interactive`
// block, re-evaluate the exported JS closed forms at the embedded sample points and require them to
// reproduce the values ChemKernel's engine computed (within tolerance). The JS the BROWSER runs to drive the
// sliders is thereby proven to match the Python engine across the whole slider range — including the samples
// that straddle the limiting-reagent switch. Also cross-checks that the default slider setting reproduces the
// committed static answer (extent + precipitate mass), tying the interactive to the verified solution.
// Pure Node — CI re-verifies with no Python. Fails loud (exit 1).

import { readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";

const ROOT = process.cwd();
const ATOL = 1e-9;
const RTOL = 1e-9;

function walk(dir) {
  const out = [];
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) out.push(...walk(p));
    else if (name.endsWith(".solution.json")) out.push(p);
  }
  return out;
}

// Controlled, build-time-only eval of our own generated closed forms (Math.* is available globally).
function compile(expr, params) {
  return new Function(...params, `"use strict"; return (${expr});`);
}

const close = (got, want) => Math.abs(got - want) <= ATOL + RTOL * Math.abs(want);

const derived = join(ROOT, "derived");
let files = [];
try {
  files = walk(derived);
} catch {
  console.error("no derived/ directory — run `npm run produce` first");
  process.exit(1);
}

const fail = (file, msg) => {
  console.error(`PARITY FAILED — ${file}: ${msg}`);
  process.exit(1);
};

let checked = 0;
let withBlock = 0;
for (const file of files) {
  const rel = file.slice(ROOT.length + 1).replaceAll("\\", "/");
  const sol = JSON.parse(readFileSync(file, "utf8"));
  const ix = sol.interactive;
  if (!ix) continue;
  withBlock++;

  const params = ix.closed_form_params;
  const fns = {};
  for (const [name, expr] of Object.entries(ix.closed_form)) {
    try {
      fns[name] = compile(expr, params);
    } catch (e) {
      fail(rel, `closed_form.${name} does not compile: '${expr}' — ${e.message}`);
    }
  }

  for (let si = 0; si < ix.samples.length; si++) {
    const { args, expect } = ix.samples[si];
    const argv = params.map((p) => {
      if (!(p in args)) fail(rel, `sample[${si}] missing arg '${p}'`);
      return Number(args[p]);
    });
    for (const [name, want] of Object.entries(expect)) {
      if (!(name in fns)) fail(rel, `sample[${si}] expects '${name}' with no matching closed form`);
      const got = fns[name](...argv);
      if (!Number.isFinite(got)) fail(rel, `sample[${si}].${name}: JS produced non-finite ${got}`);
      if (!close(got, Number(want)))
        fail(rel, `sample[${si}].${name}: JS ${got} vs engine ${want} (Δ=${Math.abs(got - Number(want)).toExponential(2)})`);
      checked++;
    }
  }

  // cross-check: the DEFAULT slider setting must reproduce the committed static answer.
  const defArgs = params.map((p) => {
    const pd = ix.params.find((q) => q.name === p);
    if (!pd) fail(rel, `closed_form param '${p}' has no slider definition`);
    return Number(pd.default);
  });
  const xiDefault = fns.xi(...defArgs);
  if (!close(xiDefault, Number(sol.ledger.extent_mol)))
    fail(rel, `default xi ${xiDefault} != committed extent_mol ${sol.ledger.extent_mol}`);
  const massDefault = fns.mass(...defArgs);
  if (!close(massDefault, Number(sol.result.precipitate.mass_g)))
    fail(rel, `default mass ${massDefault} != committed precipitate mass_g ${sol.result.precipitate.mass_g}`);
}

console.log(`check-parity: ${withBlock} interactive block(s), ${checked} closed-form point(s) match the engine.`);
