# Changelog

Notable changes, newest first. Architecture rationale lives in [`DECISIONS.md`](./DECISIONS.md); the phase
plan in [`ROADMAP.md`](./ROADMAP.md).

## Phase 1 — 2026-07-08 — item 5b: the Valence-Table flagship modes (ADR-0033/0034)

- **Four modes on one committed table** (ADR-0033). **Explore** — five lenses (common ion charge, valence
  electrons, electronegativity, covalent radius, first ionization energy), each coloring the sourced values
  and opening a brief-§8.1 pattern panel (what pattern / why / exceptions / where it shows up). **Trends** —
  an SVG graph of any property across a period or down a group; missing values (noble-gas EN, transition-metal
  radii) render as labeled gaps, never interpolated. **Formula builder** — every cation×anion pair in the ion
  table (156 salts; H⁺ excluded pending acid naming), assembled by verified charge crossover and **named by
  the nomenclature engine** (the item-2 hookup), with the own-charge mistake shown *proven* wrong (non-neutral
  with the charge sum, or unreduced). **Bonding** — pick two elements, ΔEN by exact integer arithmetic over
  build-time ×100 values, classified against the sourced OpenStax Fig 7.8 thresholds (`data/bonding.toml`),
  OpenStax's own "general guide, many exceptions" caution inseparable from the verdict.
- **Architecture Q4 resolved — no fourth badge.** The lens panels' "why" text is the project's first regime-4
  (mechanistic/interpretive) content; it renders under the **model-assumed badge with an explicit
  "interpretive — story, not proof" marker**, per ADR-0003's documented default. The first `mechanistic`
  concept entry (`periodic-trends`) ships the same way; `electronegativity` and `ionization-energy` concepts
  landed rule-sourced (19 concepts total).
- **Practice mode = a seventh gym family** (`periodic_trends_v1`, ADR-0034), generated from the same curated
  data the table renders: which-has-the-larger property (3 same-series elements), predict-the-common-ion
  (fixed-charge main group), order-by-first-ionization-energy. All categorical menus (ADR-0032). **Exceptions
  are answered from data**: when the naive left-to-right rule disagrees with NIST (B < Be, O < N), the naive
  order itself becomes the named trap. `validate-gyms.mjs` re-compares/re-sorts every value in pure Node
  **and cross-checks each embedded value/ion/symbol against the committed `valence-table.json`**.
- **New pure-Node re-derivations in `validate-reference.mjs`**: valence electrons from the IUPAC group
  (He = 2, d-block omitted), every salt's name by concatenation + subscripts by gcd crossover (ADR-0027
  pattern), every emitted mistake re-proven wrong, bonding thresholds tiling. All proven non-vacuous by
  8 tamper tests.
- **167 producer tests** (+11) + **7 gates** (validate-reference = 20 objects; validate-gyms = 7 gyms /
  70 problems; check-katex = 253) + **astro build (16 pages)**, `derived/` byte-stable across rebuilds.
  In-browser: all four modes verified (Period-2 IE graph shows both dips; Fe³⁺+O²⁻ → Fe₂O₃ *iron(III) oxide*
  with the Fe₃O₂ mistake at +5; Na–Cl ΔEN 2.23 → ionic; the trends gym scores, names misconceptions, and
  renders Ca²⁺/Ca⁺/Ca²⁻ menus in Unicode), light + dark themes clean, no console errors.

## Phase 1 — 2026-07-05 — practice must not be gameable: numeric gyms go free-entry (ADR-0032)

- **The problem (owner-caught).** The percent-yield gym offered `55 %`, `0.55 %`, and a third value as multiple
  choice — the correct answer was always the plausible two-digit percent, so a human picked it with no chemistry.
  This is structural to putting a **numeric** answer in a menu: the named-mistake distractors (forgot ×100,
  skipped mL→L, sized from the excess reagent) land a different order of magnitude, hence eliminable on sight.
- **The fix.** The four numeric gym families (conversions, mass-stoichiometry, percent-yield, limiting-reagent)
  are now **free entry** — you type the number. The producer emits the named mistakes as a **`diagnostics`**
  catalogue (value → misconception) instead of a `choices` menu; the player checks your entry (1% tolerance) and,
  if wrong, names the specific mistake you made. `0.55 %` went from a giveaway distractor to precise feedback for
  the learner who actually forgets the ×100.
- **Categorical stays multiple choice.** Nomenclature and balancing keep a menu — a name / formula / coefficient
  set has no magnitude to give it away, and every distractor is a plausible, same-form answer.
- **Enforced.** Each problem carries a `mode` (`numeric` | `choice`); `validate-gyms.mjs` fails a numeric problem
  that ships a (gameable) menu, a categorical one that ships diagnostics, or any diagnostic within 3% of the
  answer (which the 1% entry tolerance could misread as correct). Schema grew `mode` + `diagnostics`.
- **155 producer tests** (+7: numeric-is-free-entry + categorical-is-a-menu + the percent-yield regression) +
  **7 gates** + **astro build (15 pages)** green. In-browser: the percent-yield gym takes a typed answer — `55`
  → ✓ Correct; `0.55` → "✗ … the answer is 55 %" + "That's the fraction, not the percent — multiply by 100."; the
  balancing gym still shows a 3-option menu.
- **The lesson Practice tab too** (same session). Its **mass** and **leftover** questions are now free entry —
  the producer emits a `diagnostics` catalogue (the `0 mmol` leftover throwaway became a diagnostic that names
  the mistake), the schema's practice block grew `mode` + `diagnostics`, `check-parity.mjs` enforces the split,
  and `PracticeQuestion.svelte` gained the numeric-entry path. The categorical **which reagent limits** stays a
  menu. In-browser: entering `0` mmol on a leftover question → "the answer is 8.5 mmol · Only the limiting
  reagent reaches 0…". **156 producer tests** total; 7 gates + astro build green.

## Phase 1 — 2026-07-05 — item 5a: element-property data curation (Valence-Table flagship)

- **Element set widened to 23** (ADR-0031): the first twenty elements (H…Ca — periods 1–3 complete, period 4
  open) plus the transition metals Fe/Cu/Zn, so the clean periodic trends read across periods 2–3 and down
  groups 1/2/17/18. Added the group-1/2/17 common ions Li⁺, Be²⁺, F⁻ (OpenStax charges, composition
  machine-checked). New atomic weights use the already-registered CIAAW/IUPAC sources.
- **Three primary-sourced periodic properties**, optional Decimal fields on every element where defined (never
  float): **electronegativity** (Pauling scale — folded into `openstax-chemistry-2e`; omitted for the noble
  gases, where Pauling is undefined), **covalent radius** in pm (**Cordero et al., *Dalton Trans.* 2008** —
  new source `cordero-2008-covalent-radii`; main-group Z ≤ 20 only, transition-metal radii deferred as
  spin-state-dependent), and **first ionization energy** in kJ/mol (**NIST** — new source
  `nist-ionization-energies`, public domain).
- **Independent oracle cross-check** (ADR-0026): `mendeleev` (+ `pandas`) added as dev-only oracles;
  `tests/test_oracle.py` re-checks every curated electronegativity, covalent radius, and ionization energy
  against mendeleev's separate data pipeline — the transcription guard oracles exist for. OpenStax's property
  figures are images (not machine-readable), so values were transcribed from the primary compilations and the
  oracle is the transcription check.
- **Emitted + gated + surfaced.** The producer threads the properties + their source ids into
  `valence-table.json` (schema declares them, `additionalProperties:false` preserved); the Valence-Table lens
  shows a **Periodic properties** panel per element with a per-source badge (and the honest "electronegativity
  undefined for the noble gases" note). `validate-reference.mjs` **now enforces that every emitted `source` id
  resolves to a `docs/SOURCES.md` register row** — a check SOURCES.md promised but no gate implemented.
- **The interpretive trend/bonding/practice lenses are item 5b** — this increment is data + gating + minimal
  surfacing.
- **148 producer tests** (+9: 3 mendeleev oracle checks + 5 data/widening + 1 valence-table-properties) +
  **7 gates** (validate-reference = **17 objects**, now source-resolving) + **astro build (15 pages)** green.
  In-browser: the Valence Table renders all 23 elements; Ca shows EN 1.00 / covalent radius 176 pm / first
  ionization energy 589.8 kJ/mol with source badges; Ar shows no EN (+ the note) but keeps its ionization
  energy; Fe shows EN + ionization energy but no covalent radius. No console errors. Gates proven non-vacuous
  (tampered EN fails the oracle; an unregistered source id fails the reference gate).

## Phase 1 — 2026-07-05 — item 4 FINISHED: limiting-reagent gym, percent-yield lesson, Avogadro datum

- **Limiting-reagent gym, `limiting_mass_v1`** (ADR-0029). Two reactant masses in → which runs out first (the
  smaller reaction extent = moles ÷ coefficient) and the maximum product mass it allows. Generated forward
  (exact); the gate re-verifies the balance, re-computes each reactant's extent, confirms the limiting reagent,
  and re-derives the product mass. The star wrong option sizes the yield from the reagent that is actually in
  **excess** — the classic mistake.
- **Flagship percent-yield lesson** (`percent-yield/zinc-carbonate-percent-yield`, ADR-0030). A gravimetric
  precipitation (`ZnCl2 + Na2CO3 → ZnCO3(s) + 2 NaCl`) where the **theoretical yield is the precipitate mass**
  the ledger already computes, plus an authored actual (measured) mass → an optional **`result.percent_yield`**
  block: theoretical, actual, and `percent = actual ÷ theoretical × 100`. The producer refuses a nonphysical
  yield (>100%); `check-ledger` re-derives the percent and confirms theoretical = precipitate mass. The lesson
  reuses the full pipeline — three equations, species ledger, both interactives, generated practice — and adds
  a **yield card** (with the "a yield can't exceed 100%" teaching inline). **3 lessons total.**
- **Avogadro constant registered** (`data/constants.toml`, source `bipm-si-2019`) — a curated, sourced,
  **exact** datum (2019 SI redefinition, N_A = 6.02214076×10²³ mol⁻¹), loaded by `data.py` like every other
  constant. This lands the ADR-0029 prerequisite for particle-count stoichiometry.
- **139 producer tests** (+6: limiting-mass shape + yield-lesson + nonphysical-yield-refused + Avogadro datum)
  + **7 gates** (validate-gyms = **6 gyms / 60 problems**; validate-solutions = 3; check-ledger re-derives the
  yield; check-parity = 240 + 18; check-katex = 97) + **astro build (15 pages)** green. In-browser: the
  percent-yield lesson renders the yield card + the full precipitation lesson; the limiting-reagent gym works.
  **Deferred to Phase 2:** the particle-count *drills* (moles↔particles — sci-notation display; pairs with gas
  work).

## Phase 1 — 2026-07-05 — item 4 (part): the stoichiometry gyms

- **Mass stoichiometry, `mass_stoichiometry_v1`** (ADR-0029). Grams of one species → grams of another across a
  balanced equation: grams → moles (÷ molar mass) → **cross the mole ratio** → moles → grams (× molar mass).
  Each problem is generated forward from a clean mole amount so every value is an exact terminating decimal,
  and the equation is balanced by ChemKernel. Wrong options are named mistakes — the mole ratio flipped or
  ignored, or the grams→moles conversion skipped.
- **Percent yield, `percent_yield_v1`** (ADR-0029). Given a reactant mass and the actual product mass
  collected, find percent yield: theoretical yield by mass stoichiometry, then actual ÷ theoretical × 100.
  Wrong options: inverted ratio, the ×100 dropped, or the reactant mass used as the denominator.
- **Two independent gate checks per problem.** `validate-gyms.mjs` **re-verifies the equation balances**
  (reusing item 3's `verifyBalance` — so the mole ratio is proven to come from a real balance, not trusted)
  **and re-derives the mass/percent numerically** from the given/target molar masses + the coefficient ratio,
  in pure Node. Molar-mass consistency is now enforced across the **whole** gym corpus (a species carries one
  sourced molar mass everywhere it appears). `chempy` cross-checks the corpus molar masses (ADR-0026).
- **Player + Atlas.** The drill island's chain caption is now family-aware ("cross the mole ratio" /
  "theoretical yield first"); chain step notes get Unicode subscripts too. A new `percent-yield` Atlas concept
  covers the regime-map row. Fixed an island bug caught in in-browser testing: the balancing conservation-tally
  block keyed on `derivation.species` (which stoichiometry now also emits, for the balance check) — re-keyed
  to balancing-only so the stoich reveal renders its chain, not a broken tally.
- **133 producer tests** (+33: stoichiometry shape/re-derivation/balance/determinism + a `chempy` molar-mass
  cross-check over every corpus species) + **7 gates** (validate-gyms = **5 gyms / 50 problems**,
  validate-reference = 17, check-katex = 90) + **astro build (13 pages)** green. In-browser: both stoich drills
  render their chains + family labels; the reveal, scoring, and shuffled choices work; balancing's tally
  regresses clean. **Deferred (item 4 continues):** the `limiting_mass_v1` gym, the flagship percent-yield
  lesson, and the Avogadro datum for particle-count stoichiometry.

## Phase 1 — 2026-07-05 — item 3: the balancing engine

- **Balancing gym, `balancing_v1`** (ADR-0028). Pick the balanced equation, then watch **every element (and
  charge) tally to equal counts on both sides**. A curated skeletal-reaction corpus — synthesis, combustion
  (incl. odd-coefficient propane/ethane), decomposition, single/double replacement, acid-base, and charged
  net-ionic — each **balanced by the engine** (`balance()`'s conservation-matrix null space, ADR-0014), never
  authored coefficients. The producer emits the conservation matrix (per-species element counts + charge), so
  the drill island shows the tally by **integer addition over producer data** — no runtime chemistry.
- **Named-mistake distractors.** A coefficient perturbation that throws a *stated* element off ("that leaves
  O unbalanced — 2 on the left, 4 on the right"), and the classic **subscript-mutation trap**: a different
  real substance (H₂O→H₂O₂ peroxide, CO→CO₂ dioxide) that only *looks* balanced without coefficients — the
  producer refuses to ship a trap unless it proves the trap atom-balances **and** changed a formula.
- **A pure-JS formula parser** (`scripts/validate/formula.mjs`) — a faithful grammar-v0 port, closing the
  ADR-0023 future-work gap. `validate-gyms.mjs` re-parses every emitted formula, cross-checks its counts +
  charge against the emitted matrix, then verifies the coefficient vector **zeroes every element row and the
  charge row**, is all-positive and reduced (gcd 1), and reconstructs to the emitted answer — the answer is
  re-proved a true, reduced balance of the exact formulas shown, in pure Node. Proven non-vacuous (breaking a
  coefficient, an emitted count, a formula, or the answer CSV each fails the gate loud).
- **Choice ordering fixed (all gyms).** The drill islands now present choices in a deterministic per-problem
  shuffle (seeded by the problem id — server/client agree, no hydration mismatch); the producer still emits
  the correct choice first and the gate stays position-agnostic.
- **100 producer tests** (+17: 5 balancing gym + 12 `chempy` corpus balance cross-checks, ADR-0026) +
  **7 gates** (validate-gyms = **3 gyms / 30 problems** re-derived) + **astro build (11 pages)** green.
  In-browser: the balancing drill renders the tally (elements + a charge row for net-ionic), the H₂O₂/CO₂
  subscript traps with their misconceptions, and the shuffled choices; conversions/nomenclature regress clean.

## Phase 1 — 2026-07-05 — item 2: the formula & nomenclature engine

- **Ionic nomenclature, both directions** (ADR-0027). A new gym family `ionic_nomenclature_v1`: name a
  compound from its formula and write the formula from its name, including the **Stock system** for
  variable-charge metals (iron(III), copper(I)). Each wrong option is a named mistake — wrong oxidation
  state, each ion's own charge used as its subscript, or covalent prefixes on an ionic compound.
- **Data curation.** `data/elements.toml` += K, Mg, Al, Fe, Cu, Zn (CIAAW weights, each cross-checked
  against the `periodictable` oracle); `data/ions.toml` += the transition-metal ions (Fe²⁺/Fe³⁺, Cu⁺/Cu²⁺),
  Zn²⁺, K⁺, Mg²⁺, Al³⁺, and the monatomic anions sulfide/nitride — plus a sourced **`compound_name`** on
  every ion (the name it takes in a compound). **15 elements, 23 ions.**
- **Engine.** `chemkernel.nomenclature` — `name_ionic` (cation + anion compound_name) + `formula_ionic`
  (verified charge crossover, reusing `reference.assemble_formula`); the Stock-numeral and covalent-prefix
  helpers drive the distractors.
- **Verification.** The gym schema generalized to two problem shapes (optional chain/unit; a `subscript_tokens`
  array; a `derivation` that carries ion parts for nomenclature). `validate-gyms.mjs` re-derives every
  nomenclature answer **in pure Node** — the name by concatenation, the **formula by re-running the gcd
  crossover** — independent of the Python producer. The Valence Table now shows 15 elements (variable metals
  pick their lowest charge deterministically); a new `nomenclature` Atlas concept links the gym.
- **83 producer tests** (+9: nomenclature module + gym family) + **7 gates** (validate-gyms = **2 gyms / 20
  problems** re-derived, validate-reference = 16, check-katex = 88) + **astro build (10 pages)** green.
  In-browser: the nomenclature drill renders both directions with subscripted formulas (NaNO₃, Ca₃(PO₄)₂,
  FeCl₃) while names stay plain; conversion gym + Valence Table (now with Fe/Cu/Zn) regress clean.

## Phase 1 — 2026-07-05 — formula typography, test oracles, doc sweep, roadmap overhaul

- **Formula rendering (ADR-0025, brief §6.1).** Producer LaTeX is now **upright** (`\mathrm{CaCl_{2}}`,
  IUPAC style — was math italic); every equation, ledger row, and Valence-Table symbol regenerated. All
  generated/authored prose — practice prompts/choices/explanations, gym drills, lesson scenarios,
  assumption claims, misconception claims, slider labels, beaker captions — now renders **Unicode
  sub/superscripts** (CaCl₂, Ca²⁺) via the new view-side `prettyText` (longest-first replaceAll of exactly
  the producer's formula tokens, `$…$`-math-safe) + `renderGym`; measurement numbers untouched by
  construction; committed `derived/` stays ASCII so the parity/gym gates are untouched. Display sig-fig
  policy settled (closes architecture Q7): ledger exact, derived results 3 sig figs, givens echoed.
- **Independent test oracles (ADR-0026).** `chempy` + `periodictable` as dev-dependencies;
  `tests/test_oracle.py` cross-checks every curated atomic weight (periodictable), every corpus molar mass
  (chempy), and both lesson balances (`balance_stoichiometry` reproduces 1:1:1:2 and 3:2:1:6). Oracles
  verify, never supply — runtime values still come only from cited `data/`.
- **Doc sweep.** architecture.md brought to as-built (gyms in the pipeline/module-map/gates table; **seven**
  gates; current counters; Q4 given an explicit decision trigger; Q7 resolved); README status updated
  (Phase 0 complete / Phase 1 in progress; Gym listed); house-conventions gained the typography rule;
  SOURCES notes that oracles are not register entries.
- **ROADMAP overhaul.** Phase-1 items 2–6 got full scope blocks (nomenclature data+engine+families;
  balancing gym with conservation-matrix view; stoichiometry suite + percent-yield lesson; Valence-Table
  data curation then lenses/modes; reaction families + atlas kind + classifier), a proposed 8-session map,
  and an explicit **Phase-1 definition of done** ("relatively complete procedural course": every Phase-0/1
  regime-map row covered, 4+ lessons, all instruments landed, review gate before Phase 2).
- **74 producer tests (+4 oracle) + 7 gates + astro build (9 pages) green**; both lessons + gym verified
  in-browser (subscripts everywhere, 31 upright `\mathrm` KaTeX nodes / 0 italic on the lesson page,
  0.250 g / 0.310 g regressions intact).

## Phase 1 — 2026-07-05 — OPEN: the dimensional-analysis gym (a generated-problem instrument)

- **Phase 1 opened** by the owner ("the more problems we solve, the easier filling in granular lessons
  later"). **Item 1 — the dimensional-analysis gym — landed** as the reusable generated-problem instrument
  the rest of Phase 1 inherits (ADR-0024).
- **New content type: the gym.** Authored `gyms/**/*.gym.toml` → `chemkernel.gym.generate_gym` → committed
  `derived/gyms/<slug>.gym.json` via a new **`build-gyms`** entry point (`npm run produce` now runs all three
  builders). Deterministic in the seed; every value exact `Fraction` (non-terminating candidates rejected);
  every conversion's dimensions **re-checked through the units engine** so the emitted cancellation chain is
  machine-certified homogeneous; every wrong choice a **named cancellation mistake**.
- **First family `solution_conversions_v1`:** 10 problems across five kinds — volume·molarity→moles,
  moles·molarity→volume, mass↔moles, and the two-step volume·molarity·molar-mass→grams — over recognizable
  salts whose molar mass comes from `data/` (sourced).
- **Schema + gate:** one `schemas/gym.schema.json` (draft 2020-12, `additionalProperties:false`) and
  **`validate-gyms.mjs`** — the 7th Node gate — which re-derives every answer in pure Node from raw inputs,
  and checks the choice invariants (one correct, distinct displays, chain ends at the answer, molar-mass
  consistency).
- **Player:** a `/gym/` section (index + per-gym page) and the `DimensionalGym.svelte` drill island — pick an
  answer and it reveals the **cancellation chain** step by step, the worked explanation, and (for a wrong
  pick) exactly which cancellation mistake it was. **Gym** added to the nav; concept chips link into the
  Atlas (incl. a new `dimensional-analysis` concept).
- **70 producer tests** (+5 gym: shape/kind-coverage, exact re-derivation, terminating answers, determinism,
  unknown-family refusal) + **7 gates** (validate-gyms = 10 problems) + **`astro build` (9 pages)** all green.
  In-browser: the gym page renders the drill, badges, and Atlas chips; the drill's click interaction is the
  proven `PracticeQuestion` pattern (this preview session couldn't dispatch Svelte-5 delegated clicks — the
  lesson tabs were equally unresponsive — so live-click was confirmed by pattern parity + the data gates, not
  a fresh click).

## Post-Phase-0 — 2026-07-05 — a second lesson (non-unit stoichiometry) + Atlas breadth

- **Second full lesson** `precipitation/calcium-phosphate-limiting` — 30.0 mL 0.100 M CaCl₂ + 25.0 mL
  0.100 M Na₃PO₄ → **Ca₃(PO₄)₂(s)** (0.310 g), the first **non-1:1** reaction: net ionic
  `3 Ca²⁺ + 2 PO₄³⁻ → Ca₃(PO₄)₂`. It stresses what the 1:1 carbonate lesson can't — the limiting reagent is
  set by **moles ÷ coefficient**, not raw moles: CaCl₂ starts with *more* Ca²⁺ (3.00 mmol) than there is
  PO₄³⁻ (2.50 mmol) yet still limits, because 3.00/3 < 2.50/2. Full interactives + 6 practice variants, all
  engine-derived and parity-verified — the `interactive`/`practice` emitters generalised to coefficient > 1
  with **no code changes** (every multiplicity was already derived from the real chemistry).
- **Coefficient-aware misconception refutation (player).** `SolutionPlayer` reads the verified ledger and,
  when the reactant coefficients differ, refutes "fewer moles = limiting" by showing each reactant's capacity
  (initial ÷ |ν|) and naming the smaller — surfacing that the limiting reagent can start with *more* moles.
  The equal-coefficient (carbonate) lesson still shows the volume story. Fixed a latent bug in passing: the
  smaller-volume-vs-limiting check compared phased given ids against phase-stripped ledger ids (so it was
  always false, only coincidentally right) — now phase-stripped and correct.
- **Practice explanation fixed to teach the method.** The `limiting`-question explanation now reasons by
  capacity (moles ÷ net-ionic coefficient) instead of "supplies fewer" — which was the exact misconception
  the lesson breaks and is false in general for non-1:1 stoichiometry (only coincidentally true for the
  sampled variants). Molar-mass in the mass explanation is no longer padded with trailing zeros.
- **Six new concept entries** — `stoichiometry`, `dissociation`, `spectator-ion`, `polyatomic-ion`,
  `conservation-of-mass`, `balancing-equations` — now **13 concepts**, cross-linked into a denser typed graph;
  both lessons list all the shared concepts (15 resolving chips each). `polyatomic-ion` is rule-sourced
  (`openstax-chemistry-2e`); the rest are ledger-/model-exact.
- **Valence Table** gained the phosphate salts: clicking phosphate now shows **Ca₃(PO₄)₂** and **Na₃PO₄**
  assembled by charge crossover and verified neutral (`3×(+2)+2×(−3)=0`, `3×(+1)+1×(−3)=0`), tying the lens to
  the new lesson.
- **65 producer tests** (+1: a non-unit-stoichiometry practice test asserting capacity, not raw moles) + **6
  gates** (validate-solutions = 2, validate-reference = **14 objects**, check-ledger = 8 rows, check-parity =
  **160 closed-form points + 12 practice answers**, check-katex = **71 strings**, scan) + **`astro build`
  (7 pages)** all green. Both lessons verified in-browser (the switch, practice, both misconception
  refutations, the Valence Table phosphate click); no console errors.

## Post-Phase-0 — 2026-07-05 — Atlas breadth-fill + polish

- **Five more concept entries** (`molarity`, `molar-mass`, `net-ionic-equation`, `precipitation`,
  `solubility-rules`) — now **7 concepts**, richly cross-linked (molarity↔molar-mass;
  net-ionic↔precipitation↔solubility-rules). Every concept the Phase-0 lesson references resolves, so all its
  chips link into the Atlas (7 → concept entries, calcium/carbonate → the Valence Table).
- **Honesty model in the Atlas:** concept entries gained an optional `source`; a `rule-sourced` concept
  **must** cite it (`build_reference_entry` raises, `validate-reference` re-checks, the index shows the violet
  badge). `precipitation` and `solubility-rules` are rule-sourced, citing `openstax-chemistry-2e`.
- **Fix:** the Verification page rendered "in action in thelessons" — an Astro whitespace collapse where a
  line-ending word met a link on the next line; fixed with `{" "}`. A full scan of the built HTML confirms no
  other collapse artifacts across the site.
- 64 producer tests (+2) + 6 gates (validate-reference = 8 objects, check-katex = 40 strings) + astro build
  (6 pages) green.

## Phase 0 — 2026-07-05 — the Chemical Atlas + Valence Table (Phase 0 COMPLETE)

- **The reference layer.** `chemkernel.reference`: `build_valence_table` projects `data/` — elements in
  their IUPAC positions + the sourced monatomic ion charges + the polyatomic ions — and emits
  **machine-verified charge-balance salts**: a cation+anion pair's neutral formula is assembled by charge
  crossover and re-checked (neutral + composition), so CaCO₃/Na₂CO₃/CaCl₂/NaCl (the lesson's four salts) are
  *derived* from the table, not asserted. `build_reference_entry` emits authored concept entries. New
  `build-reference` entry point → `derived/reference/*.json`; `npm run produce` runs both builders.
- **Content:** two authored concepts (`limiting-reagent`, `extent-of-reaction`), cross-linked (a minimal
  typed concept graph) and tied to the lesson. `schemas/valence-table.schema.json` +
  `schemas/reference.schema.json`. New **`validate-reference.mjs`** gate (Ajv by `kind`; `related` edges and
  `lessons` slugs resolve; charge-balance ions come from the table); `check-katex` extended to reference
  LaTeX + inline definition math (now **32 strings**).
- **Player:** `ValenceTable.svelte` — the periodic lens: a group×period grid; click an element for its
  common ion + the sourced charge + why; click a polyatomic to watch neutral formulas fall out of charge
  balance; Ca/Na highlighted. `reference/` index + `reference/valence-table/` pages; **Reference** added to
  the nav; the lesson's concept chips now link into the Atlas. Delivers both brief-§16 reference targets
  (verified in-browser: "click Ca → why Ca²⁺", "click carbonate → how CaCO₃ follows from charge balance").
- **Verification:** 62 producer tests (+5 reference: table shape, the four salts, crossover incl. parenthesised
  `Ca(NO3)2`, concept build) + **6 Node gates** + `astro build` (6 pages) + the live CI run all green.
- **Phase 0 is COMPLETE** — every brief-§16 definition-of-done item is met, end to end, and deployed. Stops
  here for owner review before Phase 1.

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
