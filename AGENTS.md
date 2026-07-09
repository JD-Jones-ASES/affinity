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
3. The newest [`docs/sessions/`](./docs/sessions/) log — **read its closing "State at session end" block
   first** (every increment ends with a state + next-pointer block; older logs vary the label slightly);
   read the rest of the log only if that block leaves questions. Logs can run long on multi-increment
   days; the tail is the contract.

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
2. **Doc sweep — update AND compress.** Append to `CHANGELOG.md` if something shipped (the canonical
   what-shipped record); update `ROADMAP.md ## Status` if the phase state moved and this file's
   `## Current state` if counters or standing facts changed (counters live *only* here — never restate
   them in ROADMAP). Then enforce the **anti-bloat budgets** — history accumulates in CHANGELOG and the
   session logs, never in the orientation docs:
   - `AGENTS.md ## Current state` = the counters block + a short standing-facts note (25-line ceiling,
     counted from the heading). It states *what is*, never *how it got there*.
   - `AGENTS.md ## Where this might go next` = one paragraph pointing at the open item + the standing
     options; next-up detail lives in the newest session log's closing block.
   - `ROADMAP.md ## Status` = one "Now" line naming the open item, then **one compressed line per landed
     roadmap item** (plus one for a cross-cutting increment worth a line) — ADR ids, no narrative;
     CHANGELOG has the detail. Only the open phase's current work may carry a full paragraph.
   - ROADMAP scope blocks for **landed** items keep their deferred/open lists (a future session needs
     those) but shed step-by-step narrative.
   - Deep sweep additionally re-reads every touched doc for bloat, drift, and stale instructions, and fixes
     them. **Smell test:** if the orientation docs (this file, ROADMAP `## Status`) grew beyond the budgets
     above during a session that didn't open a phase, the sweep isn't done.
3. **Session log.** Write or append `docs/sessions/YYYY-MM-DD.md` (one file per date): what was resumed,
   decisions (ADR ids), what shipped, verification evidence (exact counts, never "tests pass"), deferred
   items — and **always end with a "State at session end" block whose last line is a "Next up" pointer**
   (the cold-start contract; routing step 3 reads that block first).
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
gyms/**/*.gym.toml   (drill specs) ─┤    parse + balance + PROVE +       derived/reference/*.json
data/elements + curated datasets   ─┘    ledger + units + badges +       derived/gyms/*.gym.json
                                         practice + generated gyms        derived/assets/**            (COMMITTED)
                                                                              │
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
gyms/<topic>/        AUTHORED gym specs (topic + family + seed + count) → generated drill sets (ADR-0024)
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
(not `npm ci` — known trap #1) → the seven Node gates + `astro build` → GitHub Pages at base path `/affinity`
(https://jd-jones-ases.github.io/affinity/). Producer never runs in CI; CI validates the committed `derived/`.
The **repo stays private** (ADR-0010); the owner's GitHub Educator plan allows Pages from a private repo, so
Pages was enabled without going public. Caveat: on non-Enterprise plans the deployed *site* is world-readable
at its URL even though the repo is private (private/access-controlled Pages needs Enterprise Cloud).

## Current state

**Phase 0 + Phase 1 COMPLETE (owner-reviewed). Phase 2 OPEN (2026-07-08, ADR-0039–0048)** — the model-bearing tier.
Its **gases + thermochemistry** and **bonding & structure** tiers are complete across all surfaces (formula sheet + gyms +
lessons + the Lewis-ledger engine/`molecule` Atlas kind + IMFs, ADR-0039–0047), and **equilibrium & acid-base is open** with
four subtypes + a gym (ADR-0048 — the **reversible-extent solver** + the `equilibrium` lesson kind, a fourth lesson shape:
weak-acid pH · buffer (common-ion + Henderson–Hasselbalch) · weak-base pH via Kw · Ksp solubility, incl. a **common-ion**
solubility variant). **Next:** the rest of equilibrium (titration, polyprotic, common-ion Q-vs-Ksp prediction), then kinetics,
electrochemistry. History
in [`CHANGELOG.md`](./CHANGELOG.md) + [`docs/sessions/`](./docs/sessions/); plan in [`ROADMAP.md`](./ROADMAP.md); modules in
[`docs/architecture.md`](./docs/architecture.md) (§as-built). States only *what is*.

**Counters:** 15 lessons (2 precipitation + 1 percent-yield + 1 neutralization + 1 gas-stoichiometry + 1 energy-ledger +
3 bonding (2 structure + 1 IMF comparison) + **6 equilibrium** (weak-acid pH + buffer + weak-base pH + Ksp solubility +
common-ion Ksp + polyprotic, ADR-0048)) · 12 gyms / 120 verified problems (dimensional analysis · ionic nomenclature ·
balancing · mass stoichiometry · percent yield · limiting reagent · periodic trends · reaction families · gas laws ·
calorimetry · Lewis structures · weak-acid pH) · 1 Valence Table (23 elements; four modes; 182 named + machine-verified
salts) · 31 concept entries (8 rule-sourced, 1 interpretive) + 7 reaction families (21 example reactions) + 14 species
entries + 6 molecule structure entries (Lewis ledger + VSEPR + dominant IMF, ADR-0044/0046) + 9 formula-sheet entries
(ADR-0039/0043) · 68 Atlas reference objects · 7 Node gates + CI + live Pages · 376 producer tests · astro build = 37 pages.

**Standing facts a session should know:** the seven architecture open questions are all resolved; honesty = three badges
(regime-4 → model-assumed badge + an "interpretive" marker, ADR-0033); numeric practice free-entry (diagnostics), categorical
a menu (ADR-0032). Lessons come in **four shapes** (each a tight schema; dispatched by extension in `build_problems_main`):
a **reaction lesson** (`*.solution.json`, `build_problem`) with **four reported-product shapes** — precipitate /
neutralization water (ADR-0037) / gas via PV=nRT (ADR-0041) / energy via Hess (`result.energy`, no product mass, ADR-0043);
a **`structure` lesson** (`*.structure.json`, ADR-0045): a single molecule, no reaction, pivoting on the **Lewis electron
ledger**, stepped valence→Lewis→VSEPR→polarity; a **`comparison` lesson** (`*.comparison.json`, ADR-0047): several
molecules vs. a property, the trend machine-checked (rows reuse verified Atlas molecules; sorted by boiling point, the
dominant-IMF rank must be **non-decreasing** — refuses a non-monotonic corpus); and an **`equilibrium` lesson**
(`*.equilibrium.json`, ADR-0048): the **ICE table = the species ledger with the extent solved from mass action** ($Q=K$,
not the limiting reagent) — `chemkernel.equilibrium.solve_equilibrium` finds the root by **bisection to high precision**
(exact Decimal, general beyond the quadratic), the extent model-exact-then-rounded, the machine-check the **residual**
$Q(\text{committed})=K$ + the gate's **independent re-solve** (shared `equilibriumcheck.mjs`); triple-badged (ICE
machine-checked / $K$ sourced / position model-assumed). **Five subtypes** on one `solve_equilibrium` (one schema +
`subtype`; dispatched `salt`/`base`/`acid`, + `conjugate_base_molarity_M` → buffer, ≥2 protons → polyprotic; $K$ +
composition sourced + machine-checked on load — detail in ADR-0048): **weak-acid** pH · **buffer** (common-ion +
Henderson–Hasselbalch, A⁻ pre-loaded) · **weak-base** (water excluded from $Q$ via `in_quotient`, pH via the $K_w$ bridge) ·
**solubility** (Ksp cubic, solid excluded; optional **common-ion** suppression) · **polyprotic** (staged Kₐ1≫Kₐ2≫Kₐ3, the
solver run once per stage — top-level ice = stage 1, `result.later_stages` the rest; [H⁺] tracks stage 1, mid-anion ≈ Kₐ2).
`mass_g`→moles supported; a fully molecular reaction omits the ionic equations; redox = the free-element signature (Phase 2).
The Atlas carries all four brief-§10 kinds (lens, concepts, reactions, species ADR-0038, formula sheet ADR-0039 — machine-checked
**dimensional homogeneity** via `chemkernel.dimension`, separate from Decimal `units.py` per ADR-0015) **plus a fifth structural
surface**, the **`molecule` kind** (ADR-0044/0046): the Lewis electron ledger (valence total → octet → formal charge, exact
integer accounting **machine-checked**) + sourced VSEPR geometry (`data/vsepr.toml`) + sourced bond ΔEN + disclosed polarity
+ a **dominant IMF** (ADR-0046 — London-dispersion/dipole-dipole/hydrogen-bonding from the polarity + an *exact* H-on-N/O/F
test; the ranking is the sourced rule, a sourced boiling point the evidence — neutral molecules only).
**`compute_ledger` is one engine shared by the molecule Atlas builder, the `lewis_structures_v1` gym, AND the structure lesson**;
a shared `scripts/validate/structurecheck.mjs` re-derives the ledger in pure Node for both the reference + solutions gates. Atlas
ids are **kind-prefixed** where they'd collide (`formula-*`/`reaction-*`/`molecule-*`); species/concepts stay bare. `units.py`
carries amount/mass/volume/pressure/temperature/energy dims. Regime-2 wears the model-assumed badge (gas/calorimetry
model-exact-then-rounded, energy ledger EXACT); ledger values incl. mass-given moles stay Fraction-exact (ADR-0013). The producer
never runs in CI — the seven Node gates re-verify committed `derived/` from scratch.

## Where this might go next (paths for a future session)

**Phase 2 is open** (ADR-0039–0048). The **gas + thermochemistry** and **bonding & structure** tiers are complete, and
**equilibrium & acid-base is open** (ADR-0048 — the reversible-extent solver + the `equilibrium` lesson kind, a fourth
shape, with **five subtypes**: weak-acid pH + buffer (common-ion + Henderson–Hasselbalch) + weak-base pH (via the $K_w$
bridge, water excluded from Q) + Ksp solubility (the `in_quotient` pure-solid-excluded generalization on the **cubic**, incl.
a **common-ion** suppression variant) + **polyprotic** (staged Kₐ1≫Kₐ2≫Kₐ3, the solver run once per stage, ADR-0048 7th
increment)). The flagged next increment (newest session log's closing block) is **more of the equilibrium tier**, all reusing
the same `solve_equilibrium` instrument: **titration curves** (a march of extent as titrant is added — the tier's remaining
marquee; the producer computes every point + emits a static SVG pH curve); $Q$-vs-$K_{sp}$ precipitation prediction (the
common-ion Ksp machinery is now in place — a *prediction* face on top of it); the $K$/pH/$K_w$ **formula-sheet** entries (they
need the *activity* — dimensionless — treatment). The tier's **`weak_acid_ph_v1` gym** landed (ADR-0048 5th increment); a
weak-**base**/buffer/polyprotic gym extension could follow.
Then **kinetics** (dξ/dt, rate laws, half-life) and **electrochemistry** (oxidation numbers → electron ledger, ΔG=−nFE,
Nernst). Bonding corpus-depth deferrals: octet exceptions (BeH₂/BF₃/PCl₅/SF₆), resonance (CO₃²⁻/NO₃⁻), more structure
lessons (NH₃/CH₄), more comparison axes, a "which IMF dominates?" gym drill. Smaller/optional: endothermic / multi-step
Hess-cycle lessons; the gas lesson's **slider interactive**. Always in season inside settled contracts: Atlas breadth-fill,
further lessons, docs-only sessions. **Opening the later Phase-2 tiers** proceeds inside the open phase.

**Known traps (1 and 2 bit the sibling; 3–5 are local):** (1) In CI use `npm install`, not `npm ci` —
the lockfile is Windows-generated and may omit Linux-only optional native deps. (2) Svelte islands nested
inside islands need `svelte({ compilerOptions: { css: "injected" } })` in `astro.config.mjs` or child
scoped CSS is silently dropped. (3) Google Drive syncs this folder — see close-out step 4. (4) TOML: bare
keys must precede any `[table]` header or they get absorbed into it. (5) `actions/deploy-pages` can fail
transiently ("Deployment failed, try again later") even when every gate passed — `gh run rerun <id>
--failed` fixes it; and never pipe `gh run watch --exit-status` through `| tail` (the pipeline exit status
is tail's, masking the failure) — check the run **conclusion**, then curl the live pages for the new
content, not just a 200.
