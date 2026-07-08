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

// every real lesson route slug, for the "used in" links
const slugs = new Set();
(function walk(d) {
  for (const n of readdirSync(d)) {
    const p = join(d, n);
    if (statSync(p).isDirectory()) walk(p);
    else if (n.endsWith(".solution.json")) slugs.add(JSON.parse(readFileSync(p, "utf8")).slug);
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

// cross-checks
for (const { rel, obj } of entries) {
  if (obj.kind === "concept") {
    for (const e of obj.related) if (!ids.has(e.to)) fail(rel, `related edge → '${e.to}' resolves to no reference`);
    for (const s of obj.lessons) if (!slugs.has(s)) fail(rel, `lesson '${s}' is not a real lesson slug`);
    // the honesty model (ADR-0003): a rule-sourced concept must cite its source
    if (obj.regime === "rule-sourced" && !obj.source) fail(rel, `rule-sourced concept has no source`);
    if (obj.source && !registeredSources.has(obj.source)) fail(rel, `source '${obj.source}' is not registered in docs/SOURCES.md`);
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
