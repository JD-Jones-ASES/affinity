// validate-reference.mjs — gate for the Chemical Atlas (ADR-0005/0012). Validates every
// derived/reference/*.json against its schema (by `kind`), then cross-checks: reference ids are unique,
// concept `related` edges resolve to a known reference, concept `lessons` resolve to real lesson slugs, and
// the Valence Table is internally consistent (highlighted elements exist; every charge-balance salt's ions
// come from the table). Pure Node — no Python. Fails loud (exit 1).

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
    // every charge-balance salt's ions must come from the table (a monatomic common_ion or a polyatomic ion)
    const ionIds = new Set([
      ...obj.elements.flatMap((e) => (e.common_ion ? [e.common_ion.id] : [])),
      ...obj.polyatomic.map((p) => p.id),
    ]);
    for (const cb of obj.charge_balance) {
      if (!ionIds.has(cb.cation)) fail(rel, `charge_balance cation '${cb.cation}' is not a table ion`);
      if (!ionIds.has(cb.anion)) fail(rel, `charge_balance anion '${cb.anion}' is not a table ion`);
    }
  }
}

console.log(`validate-reference: ${entries.length} reference object(s) valid; ${ids.size} unique id(s).`);
