// validate-reference.mjs — gate for the Chemical Atlas (ADR-0005/0012). Validates every
// derived/reference/*.json against its schema (by `kind`), then cross-checks: reference ids are unique,
// concept `related` edges resolve to a known reference, concept `lessons` resolve to real lesson slugs, and
// the Valence Table is internally consistent (highlighted elements exist; every charge-balance salt's ions
// come from the table). The ADR-0033 additions are RE-DERIVED in pure Node: valence electrons from the
// IUPAC group, every salt's name by compound-name concatenation, every salt's subscripts by gcd charge
// crossover, and every emitted formula-writing `mistake` re-proven wrong (non-neutral or unreduced). Pure
// Node — no Python. Fails loud (exit 1).

import { readFileSync, existsSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";
import Ajv from "ajv/dist/2020.js";
import addFormats from "ajv-formats";
import { verifyBalance, redoxFreeElements } from "./balancecheck.mjs";
import { parseFormula } from "./formula.mjs";
import { unitDimension, eq as dimEq, addScaled, DIMENSIONLESS } from "./dimension.mjs";
import { verifyElectronLedger, ledgerTables, classifyIMF } from "./structurecheck.mjs";

const ROOT = process.cwd();
const refDir = join(ROOT, "derived", "reference");
if (!existsSync(refDir)) {
  console.error("no derived/reference/ — run `npm run produce` first");
  process.exit(1);
}

const ajv = new Ajv({ allErrors: true, strict: true });
addFormats(ajv);
const schemas = {
  "valence-table": ajv.compile(JSON.parse(readFileSync(join(ROOT, "schemas", "valence-table.schema.json"), "utf8"))),
  concept: ajv.compile(JSON.parse(readFileSync(join(ROOT, "schemas", "reference.schema.json"), "utf8"))),
  "reaction-family": ajv.compile(JSON.parse(readFileSync(join(ROOT, "schemas", "reaction-family.schema.json"), "utf8"))),
  species: ajv.compile(JSON.parse(readFileSync(join(ROOT, "schemas", "species.schema.json"), "utf8"))),
  formula: ajv.compile(JSON.parse(readFileSync(join(ROOT, "schemas", "formula.schema.json"), "utf8"))),
  molecule: ajv.compile(JSON.parse(readFileSync(join(ROOT, "schemas", "molecule.schema.json"), "utf8"))),
};

const fail = (file, msg) => { console.error(`REFERENCE GATE FAILED — ${file}: ${msg}`); process.exit(1); };

// The honesty register (docs/SOURCES.md, ADR-0003/0006): collect every registered source id from the
// register table (rows are `| \`source-id\` | … |`). Every `source` an emitted object cites must resolve
// to one of these — SOURCES.md promises exactly this enforcement.
const registeredSources = new Set();
{
  const md = readFileSync(join(ROOT, "docs", "SOURCES.md"), "utf8");
  for (const m of md.matchAll(/^\|\s*`([a-z0-9-]+)`\s*\|/gm)) registeredSources.add(m[1]);
  if (registeredSources.size === 0) fail("docs/SOURCES.md", "no registered source ids found — parser drift?");
}

// every real lesson route slug, for the "used in" links — reaction (*.solution.json), structure
// (*.structure.json, ADR-0045), comparison (*.comparison.json, ADR-0047), equilibrium (*.equilibrium.json,
// ADR-0048), and prediction (*.prediction.json, ADR-0048) lessons all share /lessons/<slug>/.
const slugs = new Set();
(function walk(d) {
  for (const n of readdirSync(d)) {
    const p = join(d, n);
    if (statSync(p).isDirectory()) walk(p);
    else if (n.endsWith(".solution.json") || n.endsWith(".structure.json") || n.endsWith(".comparison.json")
             || n.endsWith(".equilibrium.json") || n.endsWith(".prediction.json"))
      slugs.add(JSON.parse(readFileSync(p, "utf8")).slug);
  }
})(join(ROOT, "derived"));

const files = readdirSync(refDir).filter((n) => n.endsWith(".json"));
const entries = [];
const ids = new Set();
for (const name of files) {
  const rel = `derived/reference/${name}`;
  const obj = JSON.parse(readFileSync(join(refDir, name), "utf8"));
  const validate = schemas[obj.kind];
  if (!validate) fail(rel, `unknown kind '${obj.kind}'`);
  if (!validate(obj)) fail(rel, ajv.errorsText(validate.errors, { separator: "; " }));
  if (ids.has(obj.id)) fail(rel, `duplicate reference id ${obj.id}`);
  ids.add(obj.id);
  entries.push({ rel, obj });
}

// the Valence Table's sourced atomic weights (symbol → exact string), for re-deriving species molar masses —
// a species may only use elements the table already sources (ADR-0038), the same discipline the trends gym uses.
const vt = entries.find((e) => e.obj.kind === "valence-table")?.obj;
const atomicWeight = new Map((vt?.elements ?? []).map((e) => [e.symbol, e.atomic_weight]));
// the Valence Table's derived valence-electron counts + sourced electronegativities, for re-deriving a
// molecule's electron ledger + bond ΔEN in pure Node (ADR-0044) — one source of truth, as species molar
// masses re-sum the table's weights (ADR-0038). Shared with validate-solutions' structure lessons (ADR-0045).
const ledgerT = ledgerTables(vt);

// cross-checks
for (const { rel, obj } of entries) {
  if (obj.kind === "concept") {
    for (const e of obj.related) if (!ids.has(e.to)) fail(rel, `related edge → '${e.to}' resolves to no reference`);
    for (const s of obj.lessons) if (!slugs.has(s)) fail(rel, `lesson '${s}' is not a real lesson slug`);
    // the honesty model (ADR-0003): a rule-sourced concept must cite its source
    if (obj.regime === "rule-sourced" && !obj.source) fail(rel, `rule-sourced concept has no source`);
    if (obj.source && !registeredSources.has(obj.source)) fail(rel, `source '${obj.source}' is not registered in docs/SOURCES.md`);
  } else if (obj.kind === "reaction-family") {
    // ADR-0035: a reaction family cites a registered source, resolves its edges/lessons, and — crucially —
    // every example is RE-PROVEN in pure Node: the coefficient vector is a true reduced balance of the exact
    // shown formulas (verifyBalance), and the emitted redox flag reproduces from the free-element signature
    // (redoxFreeElements). Uniqueness/classification is Python's (the producer refuses an example that does
    // not classify as the declared family); the gate re-derives the two arithmetic-checkable claims and
    // enforces label consistency, so a mis-filed or mis-flagged example fails loud.
    if (!registeredSources.has(obj.source)) fail(rel, `source '${obj.source}' is not registered in docs/SOURCES.md`);
    for (const e of obj.related) if (!ids.has(e.to)) fail(rel, `related edge → '${e.to}' resolves to no reference`);
    for (const s of obj.lessons) if (!slugs.has(s)) fail(rel, `lesson '${s}' is not a real lesson slug`);
    const exRedox = [];
    for (const [i, ex] of obj.examples.entries()) {
      const id = `${obj.id}#${i + 1}`;
      // re-parse + re-balance the exact shown formulas (element + charge conservation, reduced, positive)
      verifyBalance(rel, id, ex.species, ex.coefficients, fail);
      // every example must be filed under this entry's family (the producer asserts it; the gate confirms)
      if (ex.family !== obj.family) fail(rel, `${id}: example family '${ex.family}' != entry family '${obj.family}'`);
      // re-derive the redox flag from the free-element signature and match the emitted value
      const changed = redoxFreeElements(ex.species);
      const wantRedox = changed.length > 0;
      if (ex.redox !== wantRedox)
        fail(rel, `${id}: redox ${ex.redox} != re-derived ${wantRedox} (free-element change: [${changed}])`);
      if (wantRedox && !ex.redox_reason) fail(rel, `${id}: redox example has no redox_reason`);
      // a net-ionic view, when present, must name its spectators (something actually canceled)
      if (ex.net_ionic && !(ex.spectators && ex.spectators.length))
        fail(rel, `${id}: net_ionic emitted without spectators`);
      exRedox.push(wantRedox);
    }
    // the family-level redox flag is present iff the examples agree; re-derive and cross-check
    const uniform = exRedox.every((r) => r) ? true : exRedox.every((r) => !r) ? false : undefined;
    if (obj.redox !== uniform)
      fail(rel, `family redox '${obj.redox}' != re-derived '${uniform}' (examples: [${exRedox}])`);
  } else if (obj.kind === "species") {
    // ADR-0038: a species entry's DERIVED block is re-proven in pure Node. The composition + charge come from
    // re-parsing the exact `formula` string (formula.mjs), and the molar mass re-sums the Valence Table's
    // sourced atomic weights — so "the molar mass of CaCO3 is 100.086 g/mol" is re-derived, never trusted.
    if (!registeredSources.has(obj.source)) fail(rel, `source '${obj.source}' is not registered in docs/SOURCES.md`);
    for (const e of obj.related) if (!ids.has(e.to)) fail(rel, `related edge → '${e.to}' resolves to no reference`);
    for (const s of obj.lessons) if (!slugs.has(s)) fail(rel, `lesson '${s}' is not a real lesson slug`);
    for (const rid of obj.reactions ?? []) if (!ids.has(rid)) fail(rel, `reaction '${rid}' resolves to no reference`);

    // re-parse the formula: charge and composition must reproduce exactly
    let parsed;
    try { parsed = parseFormula(obj.formula); }
    catch (e) { fail(rel, `formula '${obj.formula}' does not parse: ${e.message}`); }
    if (parsed.charge !== obj.charge) fail(rel, `charge ${obj.charge} != re-parsed ${parsed.charge}`);

    const emitted = {};
    for (const c of obj.composition) {
      if (emitted[c.symbol] !== undefined) fail(rel, `duplicate element '${c.symbol}' in composition`);
      emitted[c.symbol] = c.count;
    }
    for (const el of new Set([...Object.keys(parsed.counts), ...Object.keys(emitted)])) {
      if (parsed.counts[el] !== emitted[el])
        fail(rel, `composition count for '${el}' is ${emitted[el] ?? "absent"} but the formula parses to ${parsed.counts[el] ?? "absent"}`);
    }

    // class ↔ charge agreement (element/compound neutral; either ion class charged)
    const isIon = obj.species_class === "monatomic-ion" || obj.species_class === "polyatomic-ion";
    if (isIon && obj.charge === 0) fail(rel, `species_class '${obj.species_class}' but charge is 0`);
    if (!isIon && obj.charge !== 0) fail(rel, `species_class '${obj.species_class}' but charge is ${obj.charge}`);
    if (obj.species_class === "monatomic-ion" && obj.composition.length !== 1)
      fail(rel, `monatomic-ion has ${obj.composition.length} elements`);

    // molar mass re-sums the sourced weights: each weight must match the table (exact string), each subtotal
    // = count × weight, and the total = Σ subtotals (float re-derivation within tolerance, as check-ledger does)
    let total = 0;
    for (const c of obj.composition) {
      const aw = atomicWeight.get(c.symbol);
      if (aw === undefined) fail(rel, `element '${c.symbol}' has no sourced weight in the Valence Table`);
      if (aw !== c.atomic_weight) fail(rel, `${c.symbol}: atomic_weight '${c.atomic_weight}' != table '${aw}'`);
      const sub = c.count * Number(aw);
      if (Math.abs(sub - Number(c.subtotal)) > 1e-6) fail(rel, `${c.symbol}: subtotal '${c.subtotal}' != count × weight = ${sub}`);
      total += Number(c.subtotal);
    }
    if (Math.abs(total - Number(obj.molar_mass_g_per_mol)) > 1e-6)
      fail(rel, `molar_mass '${obj.molar_mass_g_per_mol}' != Σ subtotals = ${total}`);
  } else if (obj.kind === "formula") {
    // ADR-0039: a formula entry's DIMENSIONAL HOMOGENEITY is re-derived in pure Node. Each variable's
    // dimension re-derives from its unit (this gate's own definitional table, independent of Python); each
    // term's dimension re-derives from those variable dimensions + factor powers; and every term must share
    // ONE dimension — that is what makes the equation dimensionally admissible. We do NOT re-check that the
    // relation is *true* (a model-exact relation carries the model-assumed badge); we re-check that it is
    // dimensionally consistent, and that it discloses its model.
    for (const e of obj.related) if (!ids.has(e.to)) fail(rel, `related edge → '${e.to}' resolves to no reference`);
    for (const s of obj.lessons) if (!slugs.has(s)) fail(rel, `lesson '${s}' is not a real lesson slug`);
    for (const s of obj.sources ?? []) if (!registeredSources.has(s)) fail(rel, `source '${s}' is not registered in docs/SOURCES.md`);

    const varDim = new Map();
    for (const v of obj.variables) {
      let want;
      try { want = unitDimension(v.unit); }
      catch (e) { fail(rel, `variable '${v.symbol}': ${e.message}`); }
      if (!dimEq(v.dimension, want))
        fail(rel, `variable '${v.symbol}' (${v.unit}) dimension [${v.dimension}] != re-derived [${want}]`);
      if (varDim.has(v.symbol)) fail(rel, `duplicate variable symbol '${v.symbol}'`);
      varDim.set(v.symbol, v.dimension);
      // a threaded constant must cite a source the entry also lists (register-checked above)
      if (v.constant && !(obj.sources ?? []).includes(v.constant.source))
        fail(rel, `variable '${v.symbol}' constant source '${v.constant.source}' not in the entry's sources`);
    }

    const sides = new Set();
    let common = null;
    for (const t of obj.terms) {
      sides.add(t.side);
      let d = DIMENSIONLESS;
      for (const f of t.factors) {
        if (!varDim.has(f.var)) fail(rel, `term '${t.display}' references unknown variable '${f.var}'`);
        d = addScaled(d, varDim.get(f.var), f.power);
      }
      if (!dimEq(d, t.dimension))
        fail(rel, `term '${t.display}' dimension [${t.dimension}] != re-derived [${d}]`);
      if (common === null) common = d;
      else if (!dimEq(d, common))
        fail(rel, `not homogeneous — term '${t.display}' is [${d}] but another term is [${common}]`);
    }
    if (sides.size < 2) fail(rel, `all terms on one side — an equation needs both sides`);
    if (!dimEq(common, obj.dimension))
      fail(rel, `emitted dimension [${obj.dimension}] != re-derived common [${common}]`);
    // the honesty model (ADR-0003): a model-exact relation must disclose a model assumption
    if (obj.regime === "model-exact" && obj.assumptions.length === 0)
      fail(rel, `model-exact formula discloses no assumption`);
  } else if (obj.kind === "molecule") {
    // ADR-0044/0045: a molecule's ELECTRON LEDGER is re-derived in pure Node by the SHARED engine
    // (structurecheck.mjs) — the same one validate-solutions runs over a structure lesson's embedded molecule.
    // The valence total, per-atom octet/duet, formal charges (+ their sum), the domain count, and every bond's
    // ΔEN + class all re-derive from the exact `formula` + authored atoms/bonds + the sourced table. Here the
    // gate additionally checks the Atlas-specific facets: the cited sources register, and the edges/lessons resolve.
    for (const s of [obj.source, obj.en_source, obj.bonding_source, obj.geometry.source])
      if (!registeredSources.has(s)) fail(rel, `source '${s}' is not registered in docs/SOURCES.md`);
    for (const e of obj.related) if (!ids.has(e.to)) fail(rel, `related edge → '${e.to}' resolves to no reference`);
    for (const s of obj.lessons) if (!slugs.has(s)) fail(rel, `lesson '${s}' is not a real lesson slug`);
    verifyElectronLedger(rel, obj, ledgerT, fail);

    // ADR-0046: the intermolecular block (neutral molecules only) re-derives from the verified structure +
    // polarity. The h_bond_donor + forces + dominant are re-computed in pure Node; the boiling point is
    // data-sourced (its source register-checked, its value not re-derivable — an empirical measurement).
    if (obj.intermolecular) {
      if (obj.charge !== 0) fail(rel, `intermolecular block present on a charged species (charge ${obj.charge})`);
      const want = classifyIMF(obj.atoms, obj.bonds, obj.polarity);
      if (obj.intermolecular.h_bond_donor !== want.hBondDonor)
        fail(rel, `intermolecular h_bond_donor ${obj.intermolecular.h_bond_donor} != re-derived ${want.hBondDonor}`);
      if (obj.intermolecular.dominant !== want.dominant)
        fail(rel, `dominant IMF '${obj.intermolecular.dominant}' != re-derived '${want.dominant}'`);
      if (JSON.stringify(obj.intermolecular.forces) !== JSON.stringify(want.forces))
        fail(rel, `IMF forces ${JSON.stringify(obj.intermolecular.forces)} != re-derived ${JSON.stringify(want.forces)}`);
      // the dominant must be the strongest force actually present
      if (!obj.intermolecular.forces.includes(obj.intermolecular.dominant))
        fail(rel, `dominant IMF '${obj.intermolecular.dominant}' is not among the forces present`);
      // a boiling point + its phase_change + its source travel together, and the source resolves in SOURCES.md
      const hasBp = obj.intermolecular.boiling_point_c !== undefined;
      if (hasBp !== (obj.intermolecular.boiling_source !== undefined) || hasBp !== (obj.intermolecular.phase_change !== undefined))
        fail(rel, `boiling_point_c, phase_change, and boiling_source must all be present or all absent`);
      if (hasBp && !registeredSources.has(obj.intermolecular.boiling_source))
        fail(rel, `boiling_source '${obj.intermolecular.boiling_source}' is not registered in docs/SOURCES.md`);
      if (hasBp && !Number.isFinite(Number(obj.intermolecular.boiling_point_c)))
        fail(rel, `boiling_point_c '${obj.intermolecular.boiling_point_c}' is not numeric`);
    } else if (obj.charge === 0) {
      fail(rel, `neutral molecule '${obj.id}' has no intermolecular block (ADR-0046)`);
    }
  } else if (obj.kind === "valence-table") {
    // every source id the table cites (atomic weight, position, ion charge, and the ADR-0031 properties)
    // must resolve to a SOURCES.md register row
    for (const [facet, sid] of Object.entries(obj.sources)) {
      if (!registeredSources.has(sid)) fail(rel, `source '${sid}' (${facet}) is not registered in docs/SOURCES.md`);
    }
    const syms = new Set(obj.elements.map((e) => e.symbol));
    for (const h of obj.highlight) if (!syms.has(h)) fail(rel, `highlight '${h}' is not an element in the table`);

    // valence electrons re-derive from the emitted IUPAC position (ADR-0033): s/p-block only, He = 2,
    // groups 1–2 = the group, groups 13–18 = group − 10; the d-block must omit the field.
    for (const e of obj.elements) {
      const want = e.block === "s" || e.block === "p"
        ? (e.symbol === "He" ? 2 : e.group <= 2 ? e.group : e.group - 10)
        : undefined;
      if ((e.valence_electrons ?? undefined) !== want)
        fail(rel, `${e.symbol}: valence_electrons ${e.valence_electrons} != re-derived ${want}`);
    }

    // each lens colors a real property and cites a facet of the sources map (already register-checked above)
    for (const lens of obj.lenses ?? []) {
      if (!(lens.source in obj.sources)) fail(rel, `lens '${lens.id}' source key '${lens.source}' not in sources`);
    }

    // every charge-balance salt's ions must come from the table (a common/other monatomic ion or a
    // polyatomic ion); collect their charges so the crossover re-derivation below uses table data.
    const ionCharge = new Map();
    for (const e of obj.elements) {
      for (const ion of [e.common_ion, ...(e.other_ions ?? [])]) if (ion) ionCharge.set(ion.id, ion.charge);
    }
    for (const p of obj.polyatomic) ionCharge.set(p.id, p.charge);
    // an ion id's caret suffix must agree with its emitted charge (Na^+, Ca^2+, S^2-)
    for (const [id, q] of ionCharge) {
      const m = id.match(/\^(\d*)([+-])$/);
      if (!m) fail(rel, `ion id '${id}' has no caret charge suffix`);
      const parsed = (m[1] === "" ? 1 : Number(m[1])) * (m[2] === "+" ? 1 : -1);
      if (parsed !== q) fail(rel, `ion id '${id}' encodes charge ${parsed} but carries ${q}`);
    }

    // charge-balance product (ADR-0033): re-derive the name by concatenation and the subscripts by gcd
    // charge crossover (the ADR-0027 pattern), reconstruct the formula, and re-prove each emitted mistake
    // wrong — non-neutral when the charges differ, unreduced when they match.
    const gcd = (a, b) => { a = Math.abs(a); b = Math.abs(b); while (b) { [a, b] = [b, a % b]; } return a; };
    const MONO = /^[A-Z][a-z]?$/;
    const part = (id) => id.replace(/\^\d*[+-]$/, "");
    const groupPart = (p, n) => (n === 1 ? p : (MONO.test(p) ? `${p}${n}` : `(${p})${n}`));
    for (const cb of obj.charge_balance) {
      if (!ionCharge.has(cb.cation)) fail(rel, `charge_balance cation '${cb.cation}' is not a table ion`);
      if (!ionCharge.has(cb.anion)) fail(rel, `charge_balance anion '${cb.anion}' is not a table ion`);
      const c = ionCharge.get(cb.cation), a = -ionCharge.get(cb.anion);
      if (c <= 0 || a <= 0) fail(rel, `charge_balance ${cb.formula}: cation/anion charges have wrong signs`);
      const g = gcd(c, a);
      if (cb.cation_n !== a / g || cb.anion_n !== c / g)
        fail(rel, `${cb.formula}: subscripts ${cb.cation_n}/${cb.anion_n} != crossover ${a / g}/${c / g}`);
      const formula = groupPart(part(cb.cation), cb.cation_n) + groupPart(part(cb.anion), cb.anion_n);
      if (formula !== cb.formula) fail(rel, `re-derived formula '${formula}' != emitted '${cb.formula}'`);
      const name = `${cb.cation_name} ${cb.anion_name}`;
      if (name !== cb.name) fail(rel, `re-derived name '${name}' != emitted '${cb.name}'`);
      // the own-charge mistake: present iff it differs from the crossover, and provably wrong in the way named
      const naive = groupPart(part(cb.cation), c) + groupPart(part(cb.anion), a);
      if (naive === cb.formula) {
        if (cb.mistake) fail(rel, `${cb.formula}: mistake emitted but the own-charge assembly is correct here`);
      } else {
        if (!cb.mistake) fail(rel, `${cb.formula}: own-charge assembly '${naive}' differs but no mistake emitted`);
        if (cb.mistake.formula !== naive)
          fail(rel, `${cb.formula}: mistake '${cb.mistake.formula}' != re-derived own-charge '${naive}'`);
        const wantKind = c * c - a * a !== 0 ? "own-charge" : "unreduced";
        if (cb.mistake.kind !== wantKind) fail(rel, `${cb.formula}: mistake kind '${cb.mistake.kind}' != '${wantKind}'`);
      }
    }

    // the bonding rule (ADR-0033): its source is the sources-map facet (register-checked above) and the
    // ΔEN classes must tile the scale — each boundary parses and consecutive classes share it.
    if (obj.bonding) {
      if (obj.bonding.source !== obj.sources.bonding)
        fail(rel, `bonding.source '${obj.bonding.source}' != sources.bonding '${obj.sources.bonding}'`);
      const cls = obj.bonding.classes;
      for (let i = 0; i < cls.length; i++) {
        for (const bound of ["min", "max"]) {
          if (cls[i][bound] != null && !Number.isFinite(Number(cls[i][bound])))
            fail(rel, `bonding class '${cls[i].id}' ${bound} '${cls[i][bound]}' is not numeric`);
        }
        if (i > 0 && cls[i].min !== cls[i - 1].max)
          fail(rel, `bonding classes '${cls[i - 1].id}'/'${cls[i].id}' do not share a boundary`);
      }
      if (cls[0].min != null || cls[cls.length - 1].max != null)
        fail(rel, `bonding classes must be open-ended at the extremes (no min on first, no max on last)`);
    }
  }
}

console.log(`validate-reference: ${entries.length} reference object(s) valid; ${ids.size} unique id(s).`);
