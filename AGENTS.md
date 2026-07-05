# AGENTS.md — what this is & how to work it

Entry point for anyone (human or coding agent) opening this repo cold. Read this file top to bottom once,
then follow **Session routing** below — it tells you which documents your kind of session needs. Do not
read everything; read what your row says, then start. Sibling reference implementation:
`C:\GitHub_Files\Quadrature` (the physics portal this project mirrors).

## What this is

**Affinity** is a beginning-chemistry portal where *the verification system is the product*: a build-time
Python producer (**ChemKernel**) turns authored problem specs into machine-verified solution JSON, and a
static Astro/Svelte player renders it. No claim ships unverified, unsourced, or unlabeled.

**The thesis.** Chemistry is species accounting plus electron structure under energy constraints. The
**species ledger over reaction extent** ($n_i = n_{i,0} + \nu_i \xi$) is the pivot: balancing, stoichiometry,
limiting reagents, ICE tables, kinetics, thermochemistry, and electrochemistry are all views of the same
conserved, changing system. The learner can start with recipes and coefficients; the ledger is always
underneath. (Physics sibling analogue: "the algebra formulas are calculus already evaluated.")

Named parts: **ChemKernel** (the producer), **Extent** (the solver model), **Valence Table** (the
periodic-table flagship), **Chemical Atlas** (the reference corpus: elements, species, formulas, reactions,
concept graph).

The founding brief (`PROJECT_BRIEF.md`, gitignored — private) maps scope to a specific exam-board
curriculum; that mapping stays out of committed text. Public language is "beginning chemistry / first-year
college and advanced high-school chemistry." A scan-text build gate enforces this once code exists
(ADR-0004).

## Session routing

Always, in order (every session, ~5 minutes):

1. This file, if you haven't this session.
2. [`ROADMAP.md`](./ROADMAP.md) `## Status` — where the build is.
3. The newest [`docs/sessions/`](./docs/sessions/) log — what just happened and what was flagged next.

Then, by session type:

| Session type | Read before working |
|---|---|
| ChemKernel design / implementation | [`docs/architecture.md`](./docs/architecture.md) in full; [`DECISIONS.md`](./DECISIONS.md) in full; [`docs/house-conventions.md`](./docs/house-conventions.md); brief §2–§7, §11 (local file `PROJECT_BRIEF.md`); the sibling's `producer/` for ported patterns |
| Schemas / validation gates | [`docs/architecture.md`](./docs/architecture.md) (solution-object + verification-gates sections); [`docs/house-conventions.md`](./docs/house-conventions.md) (naming); [`DECISIONS.md`](./DECISIONS.md) ADR-0002, ADR-0003, ADR-0008; sibling's `schemas/` + `scripts/validate/` |
| Content authoring (lessons, Atlas entries) | `docs/authoring-*.md` (exist from Phase 0); [`docs/house-conventions.md`](./docs/house-conventions.md); [`docs/regime-map.md`](./docs/regime-map.md) |
| Data curation (elements, ions, solubility, pKa…) | [`docs/SOURCES.md`](./docs/SOURCES.md); [`docs/house-conventions.md`](./docs/house-conventions.md); [`docs/regime-map.md`](./docs/regime-map.md); ADR-0006 |
| Frontend / player / Valence Table | [`docs/architecture.md`](./docs/architecture.md) (rendering section); sibling's `src/` (islands, build-time KaTeX, base-path handling) |
| Planning / review / docs-only | [`ROADMAP.md`](./ROADMAP.md); [`DECISIONS.md`](./DECISIONS.md); [`CHANGELOG.md`](./CHANGELOG.md); recent session logs |
| Release / deploy | `## Deploy` below; the phase's **Definition of done** in [`ROADMAP.md`](./ROADMAP.md) |

If `PROJECT_BRIEF.md` is absent (it is gitignored and never distributed), the committed docs carry the
binding contracts for the current phase — the brief adds private rationale and detail for scoping *later*
phases; without it, execute the open phase but don't re-scope phases.

Division of labor between documents (do not duplicate content across them):
**ROADMAP.md** = status + phase plan · **DECISIONS.md** = rationale (ADRs; cite as ADR-NNNN, never restate)
· **CHANGELOG.md** = what shipped when · **docs/architecture.md** = the pipeline in detail ·
**docs/sessions/** = per-session logs · **AGENTS.md** (this file) = orientation + protocol.

## Session close-out (non-negotiable, every session)

No session ends without this checklist. Small session → short sweep; long session → deep sweep.

1. **Decisions.** Every ADR-level call made this session is recorded in [`DECISIONS.md`](./DECISIONS.md)
   (format: context → decision → consequences, newest at bottom).
2. **Doc sweep.** Update `ROADMAP.md ## Status` if the phase state moved; append to `CHANGELOG.md` if
   something shipped; update this file's `## Current state` if counters or architecture changed. Deep
   sweep additionally re-reads the touched docs for bloat, drift, and stale instructions, and fixes them.
3. **Session log.** Write or append `docs/sessions/YYYY-MM-DD.md`: what was resumed, decisions (ADR ids),
   what shipped, verification evidence (exact counts, never "tests pass"), deferred items, state at
   session end, next-up candidates.
4. **Git.** Stage; **verify staging with `git ls-files --cached`** (Google Drive spawns
   `.tmp.driveupload/` junk mid-session — it must never be committed); commit with a message naming what
   shipped; push. Branches only when they make sense; this is a simple, single-owner repo.

## Tech stack (mirrors the sibling — ADR-0001)

- **Astro** static output + **Svelte 5** islands; **KaTeX rendered at build time** (no client KaTeX).
- **Python 3.13+ ChemKernel producer** as a **uv** package under `producer/` — runs **locally, never in
  CI**. SymPy for symbolic checks; exact rational arithmetic for balancing and stoichiometry.
- **JSON Schema draft 2020-12** contracts in `schemas/`, `additionalProperties: false`, validated by
  **Ajv** in Node gates under `scripts/validate/`.
- Generated data in `derived/` is **committed**; CI is pure Node (gates + `astro build`) → GitHub Pages.
- No database, no server, no client-side Python. The player does not improvise chemistry.

## How it will work (the factory invariant)

```
problems/<topic>/*.problem.toml    ─┐
reference/**/*.toml  (Atlas specs) ─┼─►  ChemKernel (uv, LOCAL)      ─►  derived/<topic>/*.solution.json
data/elements + curated datasets   ─┘    parse + balance + PROVE +       derived/reference/*.json
                                         ledger + units + badges +       derived/assets/**            (COMMITTED)
                                         practice variants                    │
                                             Ajv + parity + KaTeX + scan ─────┤  (fail loud)
                                                                              ▼
                                             Astro + Svelte player (steps the JSON; runs no Python)
```

- **The producer** is a pure function of the spec. It **refuses to emit** any object that fails atom
  balance, charge balance, unit check, nonnegative-extent check, or schema shape. Verification breaks the
  build — locally at emit time, again in CI over the committed output.
- **The content layer** is authored TOML: scenario, quantities, assumptions, misconception target, graph
  and practice choices. Humans (and agents) author specs, never solution JSON.
- **The player** is a dumb stepper: renders prose, steps the ledger, evaluates exported closed forms and
  tables. It never balances an equation or computes chemistry at runtime.

## Planned repo map

Directories are created when their first real content lands (no `.gitkeep` scaffolding). Until then this
map is the plan of record (ADR-0009):

```
problems/<topic>/    AUTHORED scenario TOML (quantities, assumptions, unknowns, misconception, regime)
reference/           AUTHORED Chemical Atlas specs (species, formulas, reactions, graph edges)
data/                CURATED datasets (periodic table, ions, solubility, …) — versioned + sourced (ADR-0006)
producer/            ChemKernel: uv package; src/chemkernel/*.py + tests/
derived/             GENERATED, COMMITTED, schema-valid ChemKernel output
schemas/             JSON-Schema contracts (draft 2020-12, additionalProperties:false)
scripts/validate/    Node gates (Ajv schema, honesty cross-checks, JS/Python parity, KaTeX, scan-text)
src/                 Astro app: pages/, layouts/, islands/ (Svelte), lib/, styles/
docs/                architecture, house-conventions, regime-map, SOURCES, authoring-* (Phase 0+), sessions/
.github/workflows/   deploy.yml (Phase 0): push to main -> Node gates + astro build -> GitHub Pages
```

## Honesty model (four regimes, three badges — non-negotiable)

Chemistry needs a finer honesty model than the physics sibling's two axes, because so much of it is
empirical. Two layers, never mixed in the data:

**Regimes** classify what *kind* of knowledge a topic or claim facet is (tracked per topic in
[`docs/regime-map.md`](./docs/regime-map.md)):

1. **Ledger-exact** — the machine fully checks it (parsing, molar mass, balancing, stoichiometry, units).
2. **Model-exact** — exact inside a disclosed idealization (ideal gas, complete dissociation, additive volumes).
3. **Empirical/rule-sourced** — tables and rules (solubility rules, electronegativities, pKa); sourced,
   exception-aware, never dressed up as theorems.
4. **Mechanistic/interpretive** — chemically useful explanation without machine proof (why this acid is
   stronger); present, carefully labeled.

**Badges** are what the reader sees on each claim (ADR-0003):

1. **Machine-checked** — ChemKernel derived and verified it; the proof detail is shown, not asserted.
2. **Data/rule-sourced** — from a registered dataset or rule; badge reveals source, version, conditions.
   Every source resolves in [`docs/SOURCES.md`](./docs/SOURCES.md).
3. **Model-assumed** — author-asserted idealization; **disclosed, not discharged**.

Every lesson carries a misconception register: the canonical wrong move, made to visibly fail in the
ledger/particle view — never merely scolded.

## House conventions

See [`docs/house-conventions.md`](./docs/house-conventions.md) — units and quantity notation, phase labels,
charge notation, significant-figures policy, naming. Baked into producer and player once they exist;
changing any of these is an ADR-level decision.

## Escalation (what stops a session)

Stop and put the choice to the owner — with a recommendation — before implementing, whenever a session
would: change a schema contract, the honesty model, house conventions, the stack, licensing, or scope;
publish anything (repo visibility, Pages, external services); or add content in safety-restricted
territory. **Hard scope rule (ADR-0007): no wet-lab procedural instruction, no synthesis routes, no
procurement/disposal guidance — simulated evidence and calculation only.** Routine work inside settled
contracts needs no permission; record it and go.

## Deploy

**Live (2026-07-05).** `.github/workflows/deploy.yml`: push to `main` → GitHub Actions runs `npm install`
(not `npm ci` — known trap #1) → the five Node gates + `astro build` → GitHub Pages at base path `/affinity`
(https://jd-jones-ases.github.io/affinity/). Producer never runs in CI; CI validates the committed `derived/`.
The **repo stays private** (ADR-0010); the owner's GitHub Educator plan allows Pages from a private repo, so
Pages was enabled without going public. Caveat: on non-Enterprise plans the deployed *site* is world-readable
at its URL even though the repo is private (private/access-controlled Pages needs Enterprise Cloud).

## Current state

**Phase 0 COMPLETE (2026-07-05), pending owner review.** All eight scope items landed, verified, and
deployed. Bootstrap docs shipped, then the full ChemKernel compute + chemistry engine: `data/` (element/ion/
solubility datasets, ADR-0012/0017) and the `chemkernel` package —
`data`, `formula` (ADR-0014), `balance` (ADR-0014), `units` (ADR-0015), `extent` (species ledger, the
ADR-0002 pivot, ADR-0016), `reaction` (dissociation + complete/net ionic, ADR-0018), `solubility` (sourced
classifier, ADR-0017), `build` (orchestrator + `build-problems` entry point, ADR-0019), `interactive`
(parity-verified closed forms for the sliders, ADR-0022), `practice` (deterministic solver-verified
variants, brief §6.8), `reference` (the Valence Table projection + charge-crossover salt assembly + concept
entries) — all exact Decimal/Fraction, never float (ADR-0013). The **emit → verify → present pipeline is live end to end**: the authored spec
`problems/precipitation/calcium-carbonate-limiting.problem.toml` builds to a committed, schema-valid
`derived/…solution.json` (`schemas/solution.schema.json`, ADR-0020), passes **five Node gates**
(`validate-solutions`, `check-ledger`, `check-parity`, `check-katex`, `scan-text`), and **renders as an
Astro/Svelte site** (ADR-0021): the lesson page steps scenario → three equations → dimensional chains →
species ledger → result, shows the three honesty badges + the misconception register, and hosts **both
interactives** — the extent bar and the beaker/species view — whose **limiting-reagent switch** runs on the
parity-verified closed forms (ADR-0022). The lesson also renders a **Practice** tab (6 solver-verified
variants with misconception distractors, brief §6.8), the spec format is documented
(`docs/authoring-problems.md`), **CI deploys to GitHub Pages** (live), and the **Chemical Atlas** exists —
the **Valence Table** periodic lens (click an element for its common ion; click a polyatomic to see neutral
formulas fall out of charge balance; the two lessons' salts — incl. Ca₃(PO₄)₂/Na₃PO₄ — assembled by crossover
+ machine-verified) plus **13 cross-linked concept entries**, gated by `validate-reference`. Molecular →
complete ionic → net ionic (spectators Na⁺/Cl⁻), carbonate rule cited, ledger, Ca²⁺ limiting, 0.250 g CaCO₃.
A **second lesson** (`calcium-phosphate-limiting`, post-Phase-0 within settled contracts) adds the first
**non-1:1** reaction (`3 Ca²⁺ + 2 PO₄³⁻ → Ca₃(PO₄)₂`, 0.310 g): the `interactive`/`practice` emitters
generalised to coefficient > 1 with no code changes, the player refutes the "fewer moles = limiting"
misconception by **capacity** (moles ÷ coefficient), and the practice explanation teaches the same. **Counters:
2 built + rendered lessons (with practice), 1 Valence Table + 13 cross-linked concept entries (2 rule-sourced,
cited), 6 Node gates + CI + live Pages, 65 producer tests green.** **Phase 0 is complete end to end** — every brief-§16 definition-of-done item is met;
**stop for owner review** before Phase 1. See [`ROADMAP.md`](./ROADMAP.md) and
[`docs/architecture.md`](./docs/architecture.md) (§as-built) for module status.

## Where this might go next (paths for a future session)

Phase 0 is the only sanctioned build track until it lands and is reviewed (brief §16, ROADMAP). Done and
tested: (a) element/ion/solubility datasets + SOURCES; (b) parser + balancer; (c) units/quantity engine;
(d) dissociation + net-ionic transforms + solubility classifier; (e) Extent solver → species ledger; (f)
the solution schema + `build.py` + the **five-gate** Node suite (validate-solutions, check-ledger,
check-parity, check-katex, scan-text); (g) the **player** with **both interactives**; (h) the gate suite;
(i) the **practice generator** + Practice tab; (j) the **Chemical Atlas** (Valence Table lens +
`build-reference` + `reference.schema.json`/`valence-table.schema.json` + `validate-reference` + concept
entries, now **13**); (k) `docs/authoring-problems.md`; and **CI/Pages** (live at `/affinity`) — **all eight
items landed and verified. Phase 0 is complete.**

**Next is owner review** (ADR-0010 publish already done — Pages is live). After review, per ROADMAP: **Phase 1
— the procedural core** (dimensional-analysis gym, formula/nomenclature engine, balancing engine,
stoichiometry suite, the Valence Table flagship, reaction families) and/or the **Atlas breadth-fill**
(more species/reactions/concept-graph edges, `docs/regime-map.md` is the coverage dashboard). Do not open
Phase 1 scope autonomously — that is a phase boundary the owner opens. Docs-only sessions are always in
season. **Extending Phase 0** (a second lesson, more Atlas entries) is fair game and inherits the settled
contracts — a second lesson (`calcium-phosphate-limiting`) and six more concepts landed this way (2026-07-05).
Note the `interactive`/`practice` emitters (`chemkernel.interactive`/`practice`) support single-precipitate
double-displacement at **any** integer stoichiometry (proven on the 3:2 phosphate reaction) — other reaction
shapes (acid-base, gas-evolution, redox) still render statically (the blocks are omitted, by design) until
the emitters generalise to them.

**Known traps (1 and 2 bit the sibling; 3 and 4 are local):** (1) In CI use `npm install`, not `npm ci` —
the lockfile is Windows-generated and may omit Linux-only optional native deps. (2) Svelte islands nested
inside islands need `svelte({ compilerOptions: { css: "injected" } })` in `astro.config.mjs` or child
scoped CSS is silently dropped. (3) Google Drive syncs this folder — see close-out step 4. (4) TOML: bare
keys must precede any `[table]` header or they get absorbed into it.
