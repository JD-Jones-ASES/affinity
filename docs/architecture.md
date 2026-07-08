# Architecture — the factory, in detail

See [`AGENTS.md`](../AGENTS.md) for orientation and [`DECISIONS.md`](../DECISIONS.md) for rationale. This is
the **design contract written before implementation** (bootstrap, 2026-07-05): Phase 0 sessions build to
it, flip its sections from *planned* to *as-built* as they land, and record divergences as ADRs. Once
`schemas/` exists it is the single source of truth for data shapes; this doc narrates them.

## Pipeline

```
problems/<topic>/<slug>.problem.toml ─┐
reference/**/*.toml                  ─┼─►  ChemKernel (uv, LOCAL)   ─►  derived/<topic>/<slug>.solution.json
gyms/<topic>/<slug>.gym.toml         ─┤                                 derived/reference/*.json
data/** (curated datasets)           ─┘                                 derived/gyms/<slug>.gym.json
                                                                        derived/assets/**        (COMMITTED)
                                                                             │
                                            scripts/validate/*.mjs ─────────┤  (Ajv + cross-checks + parity
                                                                             │   + KaTeX + scan; fail loud)
                                                                             ▼
                                            Astro + Svelte player (steps the JSON; no runtime chemistry)
```

Entry points (mirroring the sibling's `[project.scripts]` pattern): `build-problems`, `build-reference`,
and `build-gyms` (ADR-0024), invoked as `uv --project producer run <entry>`; chained by npm scripts exactly
as in the sibling: `prepare:data` = `produce` + `validate`; `build` = `validate` + `astro build`.

The load-bearing invariant: **ChemKernel refuses to emit** an object that fails any check below
(ADR-0008). CI re-gates the committed output with Node-only checks. A green build certifies both layers.

**As-built (2026-07-08 — Phase 0 complete; Phase 1 open, items 1–5 landed).** The pipeline runs end to end — compute → emit →
verify → **present**. The engine: `data/` (element, ion, solubility datasets, ADR-0012/0017);
`chemkernel.data`/`formula`/`balance`/`units`/`extent`/`reaction`/`solubility`/`build` (ADR-0012–0019);
`chemkernel.interactive` (ADR-0022) — parity-verified closed forms for the sliders; `chemkernel.practice`
(deterministic solver-verified variants); `chemkernel.reference` (the Atlas builder); and `chemkernel.gym`
(ADR-0024) — the Phase-1 generated-drill producer. Emit + verify: `problems/**/*.problem.toml` →
`derived/**/*.solution.json`, `reference/**/*.toml` → `derived/reference/*.json`, `gyms/**/*.gym.toml` →
`derived/gyms/*.gym.json` (all committed), pinned by `schemas/solution.schema.json` (ADR-0020, with optional
`interactive`/`practice` blocks), `schemas/{reference,valence-table}.schema.json`, and
`schemas/gym.schema.json` — checked by **seven Node gates** (table below) via `package.json`. Present: the
**player** (ADR-0021) — an Astro static site + Svelte islands (`src/`): `lessons/[slug].astro` +
`SolutionPlayer.svelte` step scenario → three equations → dimensional chains → species ledger → result, with
the three honesty badges, the (coefficient-aware) misconception register, **both interactives** (`ExtentBar`,
`BeakerSpecies`) whose limiting-reagent switch runs on the parity-verified closed forms, and a **Practice**
tab (`PracticeQuestion.svelte`); `gym/[slug].astro` + `DimensionalGym.svelte` run the drill sets;
`reference/` hosts the Atlas + Valence Table. Spec formats are documented (`docs/authoring-problems.md`,
`docs/authoring-gyms.md`) and **CI deploys to GitHub Pages** (`.github/workflows/deploy.yml`, live at
`/affinity`). Independent **test oracles** (ADR-0026: `chempy`, `periodictable` as dev-deps) cross-check the
molar masses and balancer in pytest. **Current counters: 3 lessons (2 precipitation + 1 percent-yield) + 7
gyms (conversions + ionic nomenclature + balancing + mass stoichiometry + percent yield + limiting reagent +
periodic trends; 70 drills — numeric families free-entry, ADR-0032), 1 Valence Table (23 elements; four modes
— Explore lenses / Trends / Formula builder / Bonding — over sourced properties + the 156-pair named
crossover product + the `data/bonding.toml` ΔEN rule, ADR-0031/0033) + 19 concept entries, 167 producer tests
+ 7 Node gates + `astro build` (16 pages) + live CI/Pages green. Lesson practice mass/leftover questions are
free-entry too (ADR-0032).**

## ChemKernel module map (brief §6)

| Module | Responsibility | Status |
|---|---|---|
| `formula.py` parser | formula string → element-count vector, charge, phase, display LaTeX (pure; no data) | **built** (ADR-0014) |
| `data.py` data layer | loads `data/` datasets (elements + **periodic properties**, ions, solubility, **constants**); molar mass; the Avogadro constant; the only path to empirical values (ADR-0006); self-validates on load | **built** (ADR-0012, +constants ADR-0030, +properties ADR-0031) |
| `balance.py` balancer | element+charge conservation matrix over ℚ → SymPy null space → smallest positive integer coefficients; re-verified; fails on ambiguity | **built** (ADR-0014) |
| `units.py` engine | `Quantity` over an amount/mass/volume `Dim` basis; exact Decimal; units cancel through ×/÷; rejects invalid conversions (numeric dimensional-analysis chain) | **built** (ADR-0015) |
| `extent.py` solver | initial moles → per-reactant extent limits → limiting reagent(s) → species ledger with leftovers; exact Fraction; refuses negative amounts | **built** (ADR-0016) |
| `reaction.py` transforms | dissociation (formula → ions via the ion table), complete ionic, net ionic with spectator cancellation + conservation re-check | **built** (ADR-0018) |
| `solubility.py` classifier | sourced ruleset → soluble/insoluble verdict + governing rule id; `verify_phase` build check | **built** (ADR-0017) |
| proofs | atom/charge conservation (in `balance.py` + `reaction.py`) and nonnegative extent (in `extent.py`) done; unit homogeneity of reference formulas (SymPy `dims.py`) with the Atlas | partly built |
| `build.py` orchestration | authored `problems/**/*.problem.toml` → engine → verified `derived/<topic>/<slug>.solution.json`; entry point `build-problems`; exact decimal strings | **built** (ADR-0019) |
| `interactive.py` | derives the optional interactive block: slider params + JS closed forms + engine-computed sample points; multiplicities from `dissociate`/`net_ionic`; single-precipitate double-displacement only, else omitted | **built** (ADR-0022) |
| `practice.py` generator | deterministic seeded variants off the reaction → solver-verified answers + misconception distractors; reject-list (near-ties, no leftover, colliding displays); reuses `interactive` multiplicities | **built** (ADR-0022, one family) |
| `reference.py` Atlas builder | Valence Table projection of `data/` (elements + sourced charges + periodic properties + valence electrons, ADR-0031/0033) + the full named charge-crossover product (verified neutral; own-charge mistakes proven wrong) + the five lens pattern panels + the sourced bonding rule; authored concept entries; `build-reference` entry point | **built** (brief §8/§10/§16) |
| `gym.py` drill generator | authored `gyms/**/*.gym.toml` → deterministic generated problem sets; exact Fractions (non-terminating rejected); dimensions re-proven through `units.py`; equations balanced by `balance.py`; named-mistake distractors; `build-gyms` entry point | **built** (ADR-0024/0027/0028/0029/0034, seven families: conversions · ionic nomenclature · balancing · mass stoichiometry · percent yield · limiting reagent · periodic trends) |
| reaction classifier | precipitation/acid-base/gas-evolution/combustion/redox/… + required conditions | Phase 1 |
| equilibrium / kinetics / thermo / electrochem | ICE-as-ledger, rate laws, energy ledger, electron ledger | Phase 2+ |

## The solution object (pinned by `schemas/solution.schema.json`, ADR-0020)

**Built.** One schema, draft 2020-12, `additionalProperties:false`, with optional blocks (Q5 → single
schema). The emitted object (see `derived/precipitation/calcium-carbonate-limiting.solution.json`) carries,
per the brief's §12 sketch: `id/title/slug/topic/scenario`; a
`regimes` block (per-facet regime classification, ADR-0003); `assumptions[]` (each `{claim, kind}` —
model/rule assumptions only, **never referenced inside derivations**); `given[]` (species + quantities);
`equations` (molecular, complete ionic, net ionic); `checks` (atom balance, charge balance, unit check,
extent nonnegative — all must be true to emit); `ledger` (the species ledger: per-species phase, charge,
initial mol, stoich coefficient, final mol; limiting species; ξ_max); a dimensional-analysis `chain`;
`result`; `visualizations[]` (kind, static/interactive mode, params, annotations — ADR-0011 governs mode);
an optional `interactive` block (ADR-0022: slider params + JS closed forms + engine-computed sample points
the player evaluates and `check-parity` re-proves); an optional `practice` block (ADR-0022: deterministic
solver-verified variants, each with `args` so `check-parity` re-derives the answer in Node; per ADR-0032
each question carries a `mode` — numeric ones are free-entry with a `diagnostics` catalogue, only the
categorical limiting question keeps a `choices` menu);
`misconception` (claim + what refutes it); `reference_links[]` (must resolve into the Atlas); badge
annotations on every data/rule/model-dependent value; `provenance` (producer version, dataset versions,
author, created).

## Ported machinery (third-generation code — ADR-0001)

From `C:\GitHub_Files\Quadrature\producer/src/quadrature_producer/`:

- **`prove.py` (tiered_zero)** — tiered symbolic-equivalence prover (structural → simplify → equals →
  rewrite → 50-dps numeric sampling, tolerance 1e-40); reuse for closed-form equivalences (e.g. dilution
  algebra, gas-law rearrangements).
- **`dims.py`** — SI 7-vector dimensional homogeneity via `sympy.physics.units` (mol is a base unit, so
  chemistry quantities fit; extend the unit namespace with M ≡ mol/L etc.). Note: pins `sympy==1.14.0`
  for a semi-private API — keep the pin or re-verify.
- **`emit.py` parity pattern** — export browser-evaluable JS closed forms *plus* high-precision sample
  points; a Node gate recompiles and re-evaluates (`ATOL 1e-6`, `RTOL 1e-9`). This is how interactive
  sliders stay honest without client-side Python.
- **Gate suite skeleton** — `validate-solutions.mjs` (Ajv + honesty cross-checks), `check-parity.mjs`,
  `check-katex.mjs`, `scan-text.mjs` (ADR-0004) port nearly unchanged; chemistry adds balance/ledger
  cross-checks (see below).
- **Deterministic concept-graph layout** frozen into JSON at build time (no client layout jitter).

New, chemistry-native (no sibling equivalent): the formula parser, the balancer (integer nullspace), the
dissociation/net-ionic transformer, the Extent solver/ledger, the curated data layer, and the practice
reject-list.

## Verification gates (all built — seven)

| Gate | Checks |
|---|---|
| validate-solutions | **built** (ADR-0020): Ajv schema; every `checks.*` true; path matches topic/slug; unique ids; rule-sourced regime needs a cited `solubility_basis.source`; ledger integrity (limiting rows final_mol 0, extent > 0, ν signs); precipitate is a solid ledger row; provenance sources non-empty |
| validate-reference | **built** (+ADR-0031/0033): each `derived/reference/*.json` schema-valid by `kind` (`valence-table`/`concept`); unique ids; concept `related` edges + `lessons` slugs resolve; every charge-balance salt's ions come from the table; **every emitted `source` id (concept or Valence-Table facet) resolves to a `docs/SOURCES.md` register row**; and the ADR-0033 re-derivations — valence electrons from the IUPAC group (He = 2, d-block omitted), every salt's `name` by compound-name concatenation + subscripts by gcd crossover + formula reconstruction, every `mistake` re-proven wrong (non-neutral vs unreduced), and the bonding ΔEN classes tiling their boundaries |
| validate-gyms | **built** (ADR-0024/0027/0028/0029/0034): each `derived/gyms/*.gym.json` Ajv-valid; every answer **re-derived in pure Node** per kind — conversions from raw `derivation.inputs`; nomenclature by name-concatenation + gcd charge-crossover; balancing by re-parsing each formula (`formula.mjs`) and re-proving the coefficients zero every element + charge row; **stoichiometry** (mass→mass, percent yield, limiting reagent) by re-verifying the equation balances (`verifyBalance`) **and** re-deriving the mass/percent/limiting reagent from the given/target molar masses + the coefficient ratio; **periodic trends** by re-comparing/re-sorting the embedded property values and **cross-checking every value, ion, and symbol against the committed `valence-table.json`**; plus the **response-mode split** (ADR-0032: numeric → a `diagnostics` catalogue each ≥ 3 % from the answer, no gameable menu; categorical → a one-correct `choices` menu) and molar-mass consistency across the **whole** corpus (conversions ∪ stoichiometry) |
| check-ledger | **built** (ADR-0023): re-derives every row's final amount as n = n₀ + ν·ξ from the committed initial/coefficient/extent (independent of Python), checks role/sign consistency, matches the reported result (precipitate moles, leftovers), and **re-derives percent yield** (ADR-0030: theoretical = precipitate mass, percent = actual ÷ theoretical × 100, actual physical). A JS formula parser now exists (`formula.mjs`, ADR-0028) for a future atom/charge re-check by element counts |
| check-parity | **built** (ADR-0023, ADR-0022, ADR-0032): recompiles the exported JS closed forms and re-evaluates them at the embedded engine-computed sample points within tolerance; cross-checks the default slider setting against the committed static answer; **re-derives every practice answer** in Node from those closed forms (mass/leftover numerically, limiting by capacity) and enforces the mode split — numeric questions carry a `diagnostics` catalogue (each ≥ 3 % from the answer) and no menu; the categorical limiting question keeps a one-correct `choices` menu |
| check-katex | **built** (ADR-0023): every LaTeX string renders through KaTeX with `throwOnError:true` |
| scan-text | **built** (ADR-0023): committed text is provider-agnostic; banned-terms list in the gate, seeded from the sibling's (ADR-0004) |

## Rendering

**Built (ADR-0021).** All LaTeX is rendered to HTML at build time in Astro frontmatter (`src/lib/katex.js`,
`view.js`) — KaTeX never ships to the browser. The lesson island hydrates **`client:load`** (not
`client:visible`): the player is the lesson and sits above the fold, and `client:visible` never fires in a
headless preview that loads at a 0×0 viewport (the IntersectionObserver never triggers), which would block
paint-verification. Interactive islands evaluate only the producer's exported, parity-checked closed forms
(ADR-0022) — no runtime chemistry. Nested Svelte islands (the interactives inside `SolutionPlayer`) require
`svelte({ compilerOptions: { css: "injected" } })` in `astro.config.mjs` or their scoped CSS is silently
dropped (known trap #2) — set, and confirmed rendering in the browser.

**Choice presentation (ADR-0028).** The gym drill islands show multiple-choice options in a deterministic
per-problem shuffle **seeded by the problem id** — the producer always emits the correct choice first, and a
problem-id seed makes server and client agree (no hydration mismatch). Never reorder choices with
`Math.random()` or client-only state; picking uses each choice's original index, and the gate is
position-agnostic.

**Formula typography (ADR-0025).** Producer LaTeX is upright (`\mathrm{CaCl_{2}}`, IUPAC). Generated and
authored prose (practice prompts/choices/explanations, gym drills, scenarios, assumption claims) gets
Unicode sub/superscripts at build time via `view.js` `prettyText` — a longest-first `replaceAll` of exactly
the formula tokens the producer emitted, skipping `$…$` math — so measurement numbers are never touched and
the committed `derived/` stays ASCII (the parity/gym gates compare those strings). Gym pages go through
`renderGym` the same way lessons go through `renderSolution`.

## Practice generation policy

Variants are generated at build time, verified by the solver, and **committed** like all derived content —
the browser never generates problems. Generation must be deterministic (explicit seed recorded in the
spec) so rebuilds are byte-stable and diffs reviewable. The reject-list (brief §6.8) is enforced at
generation: ugly arithmetic, multiple limiting reagents, negative leftovers, impossible species, unsourced
solubility claims, ambiguous sig figs, unbalanced templates.

## Open questions (resolve in Phase 0, each answer → ADR)

1. ~~**Element dataset**~~ — **RESOLVED (ADR-0012):** CIAAW atomic weights + IUPAC positions + OpenStax
   ion charges; TOML under `data/`; strings→Decimal; load-time self-check.
2. ~~**Numeric representation**~~ — **RESOLVED (ADR-0013):** Decimal for masses, rational for balancing,
   never float; exact values as strings in emitted JSON.
3. ~~**Parser scope v0**~~ — **RESOLVED (ADR-0014):** elements/subscripts/parentheses/charge/phase in;
   hydrates and isotopes deferred.
4. ~~**Regime-4 badge**~~ — **RESOLVED (ADR-0033):** no fourth badge. Mechanistic/interpretive content
   renders under the **model-assumed badge with an explicit "interpretive — story, not proof" marker** —
   ADR-0003's documented default, made concrete when the first regime-4 content shipped (the Valence-Table
   lens pattern panels + the `periodic-trends` concept, item 5b).
5. ~~**Schema granularity**~~ — **RESOLVED (ADR-0020):** one `solution.schema.json` with optional blocks.
6. ~~**Solubility-rule encoding**~~ — **RESOLVED (ADR-0017):** `data/solubility.toml`, precedence-ordered
   rules from OpenStax Table 4.1; `classify()` returns the governing rule id for citation.
7. ~~**Sig-fig policy**~~ — **RESOLVED (ADR-0025):** ledger exact; derived results at 3 significant
   figures; givens echoed at stated precision; policy lives in house-conventions §Numeric representation;
   the practice reject-list already drops ambiguous-rounding items.
