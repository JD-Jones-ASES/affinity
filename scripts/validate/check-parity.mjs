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

const close = (got, want, atol = ATOL, rtol = RTOL) => Math.abs(got - want) <= atol + rtol * Math.abs(want);

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
let practiceChecked = 0;
let withBlock = 0;
for (const file of files) {
  const rel = file.slice(ROOT.length + 1).replaceAll("\\", "/");
  const sol = JSON.parse(readFileSync(file, "utf8"));
  const ix = sol.interactive;
  if (!ix) {
    if (sol.practice) fail(rel, "practice block present but no interactive block to re-derive its answers");
    continue;
  }
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
  // the interactive's default-setting mass must reproduce the committed reported-product mass — the
  // precipitate, or the general product (water for neutralization, ADR-0037).
  const reported = sol.result.precipitate ?? sol.result.product;
  const massDefault = fns.mass(...defArgs);
  if (!close(massDefault, Number(reported.mass_g)))
    fail(rel, `default mass ${massDefault} != committed product mass_g ${reported.mass_g}`);

  // practice: re-derive every generated answer in Node from the parity-verified closed forms (ADR-0011).
  // The stated display values are rounded, so numeric answers are checked at display tolerance.
  if (sol.practice) {
    const DTOL = 1e-3; // grams to 3 decimals / mmol trimmed — half-ULP slack
    for (const q of sol.practice.questions) {
      const qa = params.map((p) => {
        if (!(p in q.args)) fail(rel, `practice ${q.id}: missing arg '${p}'`);
        return Number(q.args[p]);
      });
      // response mode (ADR-0032): a categorical question (which reagent limits) is a menu; the numeric ones
      // (mass, leftover) are free entry, so they carry a diagnostics catalogue instead of a gameable menu.
      const expectedMode = (q.kind === "mass" || q.kind === "leftover") ? "numeric" : "choice";
      if (q.mode !== expectedMode) fail(rel, `practice ${q.id}: mode '${q.mode}' but kind '${q.kind}' expects '${expectedMode}'`);
      if (q.mode === "choice") {
        if (q.diagnostics) fail(rel, `practice ${q.id}: a choice question must not carry diagnostics`);
        const correct = q.choices.filter((c) => c.correct);
        if (correct.length !== 1) fail(rel, `practice ${q.id}: ${correct.length} correct choices (want exactly 1)`);
        if (correct[0].display !== q.answer.display)
          fail(rel, `practice ${q.id}: correct choice '${correct[0].display}' != answer '${q.answer.display}'`);
        const displays = q.choices.map((c) => c.display);
        if (new Set(displays).size !== displays.length)
          fail(rel, `practice ${q.id}: choice displays are not distinct`);
      } else {
        if (q.choices) fail(rel, `practice ${q.id}: a numeric answer must not be a multiple-choice menu (gameable — ADR-0032)`);
        if (!Array.isArray(q.diagnostics)) fail(rel, `practice ${q.id}: numeric question missing diagnostics`);
        const ans = Number(q.answer.value);
        for (const d of q.diagnostics) {
          if (!d.misconception) fail(rel, `practice ${q.id}: a diagnostic has no misconception`);
          const dv = Number(d.value);
          if (!Number.isFinite(dv)) fail(rel, `practice ${q.id}: diagnostic value '${d.value}' is not a number`);
          if (Math.abs(dv - ans) <= 0.03 * Math.max(Math.abs(ans), 1e-9))
            fail(rel, `practice ${q.id}: diagnostic ${d.value} within 3% of the answer ${q.answer.value} — could mis-flag a correct entry`);
        }
      }

      if (q.kind === "mass") {
        if (!close(Number(q.answer.value), fns.mass(...qa), DTOL, DTOL))
          fail(rel, `practice ${q.id}: mass answer ${q.answer.value} != closed-form ${fns.mass(...qa)}`);
      } else if (q.kind === "leftover") {
        const leftMol = Math.max(fns.leftover_cation(...qa), fns.leftover_anion(...qa));
        if (!close(Number(q.answer.value), leftMol * 1000, DTOL, DTOL))
          fail(rel, `practice ${q.id}: leftover answer ${q.answer.value} mmol != closed-form ${leftMol * 1000}`);
      } else if (q.kind === "limiting") {
        const capCat = fns.n_cation(...qa) / ix.cation.net_coeff;
        const capAn = fns.n_anion(...qa) / ix.anion.net_coeff;
        const limits = capCat < capAn ? ix.cation.source : ix.anion.source;
        if (q.answer.value !== limits)
          fail(rel, `practice ${q.id}: limiting answer '${q.answer.value}' != closed-form '${limits}'`);
      }
      practiceChecked++;
    }
  }
}

console.log(`check-parity: ${withBlock} interactive block(s), ${checked} closed-form point(s) + ${practiceChecked} practice answer(s) match the engine.`);
