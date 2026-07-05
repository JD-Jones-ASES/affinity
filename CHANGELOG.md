# Changelog

Notable changes, newest first. Architecture rationale lives in [`DECISIONS.md`](./DECISIONS.md); the phase
plan in [`ROADMAP.md`](./ROADMAP.md).

## Phase 0 (in progress) — 2026-07-05 — practice generator, authoring guide, CI/Pages (site live)

- **Generated practice (ADR-0022, brief §6.8):** `chemkernel.practice.generate_practice` builds the
  `precipitation_limiting_reagent_v1` family — deterministic (seeded), solver-verified variants off the same
  reaction, rotating through limiting/mass/leftover asks. Multiplicities reused from the interactive block
  (engine-derived). Every wrong choice is a named misconception; a reject-list drops ambiguous variants
  (near-ties, no leftover, choices colliding at display precision). Spec declares `[practice]`
  family/seed/count. Schema grew an optional `practice` block. `check-parity.mjs` re-derives every answer in
  pure Node from the parity-verified closed forms. Player: `PracticeQuestion.svelte` + a Practice tab (pick a
  choice → right/wrong + the misconception + a worked explanation). **Fixed a Svelte-5 footgun:** a helper
  named `state` collided with Svelte's internal `state` import (compiles `$state`), throwing at render and
  corrupting the island's tab reactivity — renamed. Verified in-browser (feedback, explanations, mobile wrap).
- **Authoring guide:** `docs/authoring-problems.md` — the `*.problem.toml` spec written from the now-stable
  format (required/optional fields, the bare-keys-before-tables gotcha, what ChemKernel derives vs. what you
  author, refuse-to-emit conditions, `[practice]`, build/verify commands, worked example).
- **CI + GitHub Pages (ADR-0001, ADR-0010):** `.github/workflows/deploy.yml` — push to `main` → `npm install`
  → five Node gates + `astro build` → Pages at base `/affinity`. No Python in CI. Pages **enabled on the
  private repo** (owner's Educator plan) and **live** at https://jd-jones-ases.github.io/affinity/ (home +
  lesson return 200). Repo stays private; note the deployed site is world-readable on non-Enterprise plans.
- **Verification:** 57 producer tests (+4: practice shape, closed-forms-reproduce-engine, default+switch,
  full-build inclusion) + 5 Node gates (6 practice answers re-derived) + `astro build` + the live CI run all
  green. Determinism test now forces `PYTHONIOENCODING=utf-8` for the subprocess (matches the utf-8 artifact,
  which now carries ξ in practice explanations).

## Phase 0 (in progress) — 2026-07-05 — the player + honest interactives (verified JSON → rendered site)

- **The player (ADR-0021):** an Astro static site + Svelte 5 islands, build-time KaTeX, base `/affinity`.
  `src/` = `layouts/Base.astro`, `styles/portal.css` (Affinity tokens — chemistry-blue accent; the three
  ADR-0003 badges rendered as blue/violet/amber), `lib/` (`withBase`, `katex` with `inline`/`plain`, `view`
  deep-render + ASCII→Unicode ion formatter), pages (home = the ledger thesis, `lessons/` index by topic,
  `lessons/[slug]` one page per committed `*.solution.json` via `getStaticPaths`, `verification`).
  `SolutionPlayer.svelte` is the dumb stepper — tabs are reconciled views of the one ledger (Equations,
  Dimensional analysis, Species ledger, Beaker, Extent); always-on: the three badges, scenario, verified
  result cards, the SHOWN checks, the data-driven misconception refutation, disclosed assumptions.
  `css:"injected"` set for nested islands (known trap #2); `client:load` so it paints headlessly.
- **Honest interactives (ADR-0022):** the producer emits an optional `interactive` block —
  `chemkernel.interactive.build_interactive` derives every multiplicity from the real chemistry
  (`dissociate`, `net_ionic`), then exports JS closed forms (moles, ξ = min(…), mass, leftovers, spectators)
  plus a deterministic grid of **engine-computed** sample points straddling the limiting switch. Schema grew
  one optional block (ADR-0020 pattern). `ExtentBar.svelte` (two capacity bars, the ξ line, the switch) and
  `BeakerSpecies.svelte` (free ions before mixing → solid + spectators + leftover after) evaluate only those
  forms. **The limiting-reagent switch works** — visually verified: raising [CaCl₂] to 0.15 M flips the
  limiting reagent to CO₃²⁻ (ξ 2.5→3 mmol, 0.250→0.300 g), matching the engine sample exactly.
- **Gate suite rounded out (ADR-0023):** `check-parity.mjs` (re-proves the browser's JS closed forms against
  the engine at every sample; ties the default slider to the committed answer), `check-ledger.mjs`
  (re-derives n = n₀ + ν·ξ per row and matches the reported result, independent of Python), `check-katex.mjs`
  (every LaTeX string renders), `scan-text.mjs` (provider-agnostic; banned list seeded from the sibling,
  ADR-0004). All four proven non-vacuous by tamper tests.
- **Verification:** **53 producer tests** (+4: the interactive block — shape, closed-forms-reproduce-engine,
  default+switch samples, full-build inclusion) + **5 Node gates** (80 closed-form parity points, 4 ledger
  rows, 7 KaTeX strings, schema + honesty, scan) + **`astro build`** (4 pages) all green. Determinism test
  now covers the interactive block (byte-stable across `PYTHONHASHSEED` 0/1/42/12345). Player visually
  confirmed in the browser (both interactives, both themes; no console errors; nested-island CSS renders).

## Phase 0 (in progress) — 2026-07-05 — ChemKernel engine + emit/verify pipeline (spec → verified JSON → gate)

- **Curated `data/` datasets (ADR-0012):** `data/elements.toml` (9 elements: the 6 Phase-0 plus N/S/P for
  ion-composition consistency; CIAAW abridged atomic weights, IUPAC positions) and `data/ions.toml` (13
  common ions; OpenStax charges). Three sources registered in `docs/SOURCES.md`. Every ion's composition
  is machine-verified against the element table at load.
- **`chemkernel` producer package** (uv, Python ≥3.13, sympy 1.14.0): `data` (loader + molar mass +
  load-time self-check), `formula` (parser — elements, subscripts, nested parentheses, caret charge,
  phase; grammar v0, ADR-0014), `balance` (equation balancer via SymPy rational null space → smallest
  positive integers, re-verified element-by-element and for charge, ADR-0014), `units` (Quantity engine
  over an amount/mass/volume basis; units cancel through ×/÷; ADR-0015), `extent` (**Extent solver →
  species ledger**, the ADR-0002 pivot object: n_i = n_{i,0} + ν_i·ξ, ξ = min over reactants, limiting
  reagent, leftovers; refuses negative amounts; ADR-0016). Exact `Decimal`/`Fraction` arithmetic
  throughout, never float (ADR-0013).
- **Verification:** 37 producer tests green (`uv --project producer run pytest`), independent hand-checked
  values. The Phase-0 scenario runs end to end: 25.0 mL 0.100 M CaCl₂ + 20.0 mL 0.150 M Na₂CO₃ →
  CaCl₂ + Na₂CO₃ → CaCO₃ + 2 NaCl (`[1,1,1,2]`); ξ = 0.00250 mol, Ca²⁺ limiting, 0.00050 mol CO₃²⁻
  leftover, **0.250 g CaCO₃** (M = 100.086 g/mol); the net ionic form `[1,1,1]` gives the same result via
  the same ledger machine.
- **Reaction transforms + sourced solubility** (ADR-0018, ADR-0017): `reaction` (dissociation via the ion
  table, complete ionic, net ionic with spectator cancellation + conservation re-check) and `solubility`
  (`data/solubility.toml` from OpenStax Table 4.1; `classify` returns the governing rule for citation;
  `verify_phase` build check). The Phase-0 reaction transforms mechanically to complete ionic
  `Ca²⁺ + 2Cl⁻ + 2Na⁺ + CO₃²⁻ → CaCO₃(s) + 2Na⁺ + 2Cl⁻`, net ionic `Ca²⁺ + CO₃²⁻ → CaCO₃(s)` (spectators
  Na⁺, Cl⁻), with CaCO₃'s precipitation machine-classified and cited to the carbonate rule.
- **Emit + verify pipeline** (ADR-0019, ADR-0020): `chemkernel.build` (`build-problems` entry point) reads
  the authored `problems/precipitation/calcium-carbonate-limiting.problem.toml` and emits the committed,
  verified `derived/precipitation/calcium-carbonate-limiting.solution.json` (exact decimal strings). One
  `schemas/solution.schema.json` (draft 2020-12, `additionalProperties:false`, optional blocks) checked by
  `scripts/validate/validate-solutions.mjs` (Ajv + honesty cross-checks: path/topic match, checks hold,
  rule-sourced regime needs a cited source, ledger integrity, provenance sources) via `package.json`. Gate
  proven non-vacuous against tampered checks/extra keys/bad enums.
- **Determinism fix:** net-ionic term order came from set iteration (varies with `PYTHONHASHSEED` across
  processes), which would have made committed `derived/` non-byte-stable (ADR-0008). Now preserves the
  chemically-conventional left-to-right insertion order; guarded by a cross-hash-seed build test.
- **49 producer tests + the Node gate green** (+2: build regression + determinism guard).
- **Resolved architecture open-questions** Q1 (dataset+format), Q2 (numeric representation), Q3 (parser
  grammar), Q5 (schema granularity), Q6 (solubility encoding) via ADR-0012/0013/0014/0020/0017; units,
  ledger, ionic-transform, and emit shapes fixed by ADR-0015/0016/0018/0019.

## Bootstrap — 2026-07-05 — repo founded, docs-first

- **The full documentation contract for Phase 0, before any code.** AGENTS.md (identity, explicit
  session-routing table, mandatory close-out checklist, factory invariant, planned repo map, honesty
  model), ROADMAP.md (Phase 0 vertical slice scoped from brief §16 with definition of done; Phase 1 map;
  Atlas parallel track), DECISIONS.md (eleven founding ADRs, ADR-0001…0011), docs/architecture.md
  (ChemKernel module map, solution-object plan, gate plan, ported-machinery inventory, open questions),
  docs/house-conventions.md, docs/regime-map.md (all v1 topics, regime-classified), docs/SOURCES.md
  (verification-tier taxonomy + empty register + element-dataset candidates), session log.
- **Repo hygiene mirrored from the sibling portal:** .gitignore (brief + JD.md private; Drive temp dirs;
  note that derived/ will be committed), .gitattributes (LF-pinned), LICENSE (MIT) +
  LICENSE-content.md (CC BY-SA 4.0).
- **Founding brief** renamed to `PROJECT_BRIEF.md`, frozen, gitignored (ADR-0004).
- **Private GitHub repo** created at `JD-Jones-ASES/affinity` (ADR-0010).
