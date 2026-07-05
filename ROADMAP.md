# ROADMAP — Affinity, phase by phase

The multi-session backbone. Each phase: **goal · scope · definition of done**. We open every phase with its
single most-complex "stress" scenario (so the granular fill inherits a solved instrument), then fill
depth-first, and close with a doc sweep. Status lives here; history in [`CHANGELOG.md`](./CHANGELOG.md);
rationale in [`DECISIONS.md`](./DECISIONS.md).

## Status

- **Bootstrap — COMPLETE** (2026-07-05). Repo founded docs-first: AGENTS.md session routing + close-out
  protocol, eleven founding ADRs (ADR-0001…0011), architecture design contract with open questions,
  house conventions, regime map seeded across all v1 topics, SOURCES register, licenses, private GitHub
  repo. No code, no content.
- **Phase 0 — the vertical slice — COMPLETE** (2026-07-05), pending owner review. All eight scope items
  landed and verified end to end; the site is built and deployed. ChemKernel compute + chemistry engine:
  element/ion/solubility datasets (ADR-0012/0017), formula parser + molar mass,
  balancer (ADR-0014), units/quantity engine (ADR-0015), Extent solver → species ledger (ADR-0016),
  dissociation + complete/net ionic transforms (ADR-0018), sourced solubility classifier (ADR-0017) —
  exact arithmetic throughout (ADR-0013). The **whole Phase 0 chemistry** runs end to end: molecular →
  complete ionic → net ionic (spectators Na⁺/Cl⁻), carbonate rule cited for the precipitate, ledger, Ca²⁺
  limiting, 0.250 g CaCO₃. The **emit + verify pipeline is live** (`build.py`/ADR-0019 →
  `schemas/solution.schema.json`/ADR-0020 → Ajv + honesty gate). The **player now exists** (ADR-0021): an
  Astro static site + Svelte islands renders the committed `derived/…solution.json` — scenario, the three
  honesty badges, the three equations, dimensional chains, the species-ledger table, the result, the SHOWN
  checks, and the misconception register. Both **interactives** work (ADR-0022): the extent bar and the
  beaker/species view drive the **limiting-reagent switch** from parity-verified closed forms (the producer
  emits an `interactive` block of JS closed forms + engine-computed sample points; `check-parity.mjs`
  re-proves the browser's JS against the engine). The **gate suite is rounded out** (ADR-0023): five Node
  gates — validate-solutions, check-ledger, check-parity, check-katex, scan-text — plus `astro build`. The
  lesson also renders a **Practice** tab — 6 deterministic solver-verified variants with misconception
  distractors, re-derived in Node from the parity-verified closed forms (ADR-0022, brief §6.8). The spec
  format is documented (`docs/authoring-problems.md`) and **CI deploys to GitHub Pages** (`deploy.yml`, live
  at `/affinity`; repo stays private on the owner's Educator plan, ADR-0010). **57 producer tests + 5 Node
  gates + CI + live Pages green.** The **Chemical Atlas** now exists too (item 7): the Valence Table periodic
  lens (click an element for its common ion; click a polyatomic to see neutral formulas fall out of charge
  balance — the four lesson salts assembled by crossover and machine-verified) + **7 cross-linked concept
  entries** (2 rule-sourced, cited), gated by `validate-reference`. **64 producer tests + 6 Node gates + astro
  build (6 pages) + live Pages.** Every item of the brief-§16 definition of done is met. **Phase 0 is complete — stop for owner
  review** before opening Phase 1.
- **Post-Phase-0 breadth — 2026-07-05** (within settled contracts; Phase 0 stays complete). A **second
  lesson** `precipitation/calcium-phosphate-limiting` — the first **non-1:1** reaction
  (`3 Ca²⁺ + 2 PO₄³⁻ → Ca₃(PO₄)₂`, 0.310 g), where the limiting reagent is set by moles ÷ coefficient, not raw
  moles — with full interactives + 6 practice variants (the emitters generalised to coefficient > 1 with no
  code changes). The player gained a **coefficient-aware misconception refutation** (fires when coefficients
  differ; the volume story still serves the 1:1 lesson) and the practice `limiting` explanation now teaches
  capacity (moles ÷ coefficient) rather than the raw-moles fallacy. The **Atlas grew to 13 concepts**
  (+`stoichiometry`, `dissociation`, `spectator-ion`, `polyatomic-ion`, `conservation-of-mass`,
  `balancing-equations`) and the **Valence Table** gained the phosphate salts (Ca₃(PO₄)₂, Na₃PO₄ by crossover).
  **2 lessons, 1 Valence Table + 13 concepts, 6 gates + CI + live Pages, 65 producer tests + astro build
  (7 pages).** Phase 1 is still the owner's to open.
- **Phase 1 — the procedural core — OPEN (2026-07-05).** Owner opened Phase 1 to build problem-generation
  infrastructure ("the more problems we solve, the easier filling in granular lessons later"). **Item 1 —
  the dimensional-analysis gym — landed** end to end as the reusable generated-problem instrument (ADR-0024):
  authored `gyms/*.gym.toml` → `chemkernel.gym`/`build-gyms` → `derived/gyms/*.gym.json`, `gym.schema.json`,
  the **`validate-gyms`** gate (now **7 gates**), and a `/gym/` drill player. First family
  `solution_conversions_v1`: 10 deterministic, units-engine-verified conversions (volume·molarity·moles·mass),
  each answer re-derived in pure Node, each wrong choice a named cancellation mistake. **70 producer tests +
  7 gates + astro build (9 pages) + live Pages.** Items 2–6 (nomenclature, balancing, stoichiometry, the
  Valence Table flagship, reaction families) inherit the instrument.
- **Session 2026-07-05 (cont.) — rendering + oracles + planning overhaul.** Formula typography settled
  (ADR-0025): producer LaTeX now upright (`\mathrm`), generated practice/gym/scenario prose gets Unicode
  sub/superscripts view-side (brief §6.1), display sig-figs finalized (closes architecture Q7). Independent
  **test oracles** added (ADR-0026: `chempy` + `periodictable` dev-deps cross-check molar masses + both
  lesson balances — **74 producer tests**). Doc sweep (architecture as-built to 7 gates/gym, README status)
  and this roadmap's **Phase-1 scope blocks, session map, and definition of done** landed; scope decision:
  Phase 1 + Atlas breadth first, **Phase 2 opens only on owner review**.
- **Session 2026-07-05 (cont.) — Phase-1 item 2: formula & nomenclature engine (ionic).** Landed the second
  gym family `ionic_nomenclature_v1` (name↔formula both directions, Stock system), a sourced `compound_name`
  on every ion + 6 new metals (oracle-checked), the `chemkernel.nomenclature` engine, a pure-Node
  name/formula re-derivation branch in `validate-gyms`, a `nomenclature` Atlas concept, and the Valence Table
  to 15 elements (ADR-0027). **83 producer tests + 7 gates (2 gyms / 20 problems) + astro build (10 pages).**
  Covalent/acid naming and the flagship formula-mode hookup are deferred within item 2.
- **Session 2026-07-05 (cont.) — Phase-1 item 4 FINISHED.** Landed the remaining item-4 pieces (ADR-0030):
  the **`limiting_mass_v1`** gym (limiting reagent from two masses → max product mass; the star distractor
  sizes the yield from the excess reagent), the **flagship percent-yield lesson**
  (`percent-yield/zinc-carbonate-percent-yield`) reusing the precipitation pipeline (theoretical = precipitate
  mass) + an authored `[yield]` block → a new optional `result.percent_yield` block (re-derived by
  `check-ledger`; >100% refused; a yield card + the full equations/ledger/interactives/practice for free), and
  the **Avogadro constant** as a curated, sourced, exact datum (`data/constants.toml`, `bipm-si-2019`).
  **139 producer tests + 7 gates (6 gyms / 60 problems; 3 solutions) + astro build (15 pages).** Item 4 is
  complete bar the *particle-count* drills (moles↔particles), deferred to Phase 2 (the datum is in place; the
  drills need sci-notation display and pair with gas/molar-volume work). **3 lessons total** now.
- **Session 2026-07-05 (cont.) — Phase-1 item 4 (part): the stoichiometry gyms.** Landed two gym families
  (ADR-0029): **`mass_stoichiometry_v1`** (grams → moles → mole ratio → moles → grams) and
  **`percent_yield_v1`** (theoretical yield, then actual ÷ theoretical × 100), both forward-generated from
  clean mole amounts (exact values) over the balancing corpus's neutral reactions. The gate **re-verifies each
  equation balances** (reusing item 3's `verifyBalance` — the mole ratio is proven, not trusted) **and**
  re-derives the mass/percent numerically; molar-mass consistency now spans the whole gym corpus; `chempy`
  cross-checks the corpus molar masses. Named-mistake distractors throughout; a `percent-yield` Atlas concept;
  the drill island's chain caption went family-aware. Fixed an island bug caught in-browser: the
  conservation-tally block keyed on `derivation.species` (which stoichiometry also emits) — re-keyed to
  balancing-only. **133 producer tests + 7 gates (5 gyms / 50 problems) + astro build (13 pages).** Deferred:
  the `limiting_mass_v1` gym, the flagship percent-yield lesson, and the Avogadro datum.
- **Session 2026-07-05 (cont.) — Phase-1 item 3: the balancing engine.** Landed the third gym family
  `balancing_v1` (ADR-0028): a curated skeletal-reaction corpus (synthesis · combustion · decomposition ·
  single/double replacement · acid-base · net-ionic) each **balanced by the engine**, emitting the
  **conservation matrix** so the `DimensionalGym` island shows a **live per-element + charge tally** (integer
  addition over producer data). Distractors are named mistakes — a coefficient that throws a stated element
  off, and the **subscript-mutation trap** (H₂O→H₂O₂, CO→CO₂, proven honest at emit time). New verifiers: a
  **pure-JS formula parser** (`scripts/validate/formula.mjs`, closing the ADR-0023 gap) re-parses every
  formula and re-proves the coefficients zero every element + charge row; `chempy` cross-checks the neutral
  corpus. Also fixed the gym islands' choice ordering (deterministic per-problem shuffle — the producer emits
  the correct choice first). **100 producer tests + 7 gates (3 gyms / 30 problems) + astro build (11 pages).**
  Deferred: redox half-reactions (Phase 2); a free coefficient-entry mode.

---

## Phase 0 — the vertical slice (then STOP for review)

**Goal.** One lesson end to end, stressing every hard architectural piece: **"A precipitate forms: calcium
chloride + sodium carbonate"** (brief §16). 25.0 mL of 0.100 M CaCl₂ + 20.0 mL of 0.150 M Na₂CO₃ → what
mass of CaCO₃, which reactant limits, which ions remain. One scenario exercises formulas, polyatomic ions,
balancing, dissociation, net ionic equations, molarity, dimensional analysis, limiting reagent via extent,
leftover species, two earned interactives, the misconception register, generated practice, the Atlas, and
a periodic-table lens.

The lesson lives at `problems/precipitation/` (the topic slug for path purposes — house-conventions
§naming).

**Landed so far (2026-07-05):** scope items 1 (datasets), 2 (parser, balancer, units engine, dissociation
transformer, net-ionic reducer, Extent solver → species ledger), 3 (conservation + nonnegative-extent
proofs), **4 (solution schema + `build.py` + the five-gate Node suite: validate-solutions, check-ledger,
check-parity, check-katex, scan-text)**, **5 (the player + both interactives — the extent bar and the
beaker/species view, with the limiting-reagent switch driven by parity-verified closed forms)**, **6 (the
practice generator + Practice tab)**, and **8 (the authoring guide `docs/authoring-problems.md` + the CI
`deploy.yml`, live on GitHub Pages)** are complete and tested; the authored Phase-0 spec, its verified
`derived/` JSON, and the Astro/Svelte site are committed and deployed. **Item 7 (the Chemical Atlas entry +
the Valence Table periodic lens)** is now done too — **all eight scope items complete.** Phase 0 stops here
for owner review.

**Scope.**
1. `data/`: minimal element dataset (Ca, Cl, Na, C, O, H) + common-ion and polyatomic-ion entries, source
   decision recorded as an ADR (ADR-0006), entries registered in `docs/SOURCES.md`.
2. ChemKernel core: formula parser (elements, subscripts, parentheses, charges, phases) → element-count
   vector, charge, molar mass, display LaTeX; unit/dimensional-analysis engine; equation balancer
   (conservation matrix → smallest integer coefficients); dissociation transformer + net-ionic reducer
   with spectator identification; extent solver → species ledger with limiting reagent and leftovers.
3. Proofs at emit time: atom balance, charge balance, unit homogeneity, nonnegative extent (ADR-0008).
4. `schemas/solution.schema.json` + Node gates: Ajv validation, honesty cross-checks, parity check on
   exported JS closed forms, KaTeX gate, scan-text gate (ADR-0004).
5. Player: lesson page stepping scenario → equations → dimensional chain → ledger → result; the
   **beaker/species view** and **extent bar** interactives (sliders for volume/concentration; watch the
   limiting reagent switch); misconception register rendering — all three brief-§16 targets: smaller
   volume/mass is not necessarily limiting; spectator ions do not vanish; aqueous ionic compounds are not
   intact floating molecules.
6. Practice generator: `precipitation_limiting_reagent_v1` family, solver-verified variants with full
   derivation trees; reject-list enforced (ugly arithmetic, ambiguous sig figs, nonphysical leftovers).
7. Chemical Atlas: one fully linked reference entry (*limiting reagent via extent*) + one Valence Table
   lens (common ion charges, Ca and Na highlighted).
8. `docs/authoring-problems.md` written from the stabilized spec format; CI deploy workflow wired.

**Definition of done (brief §16).** A learner can open the page and follow the full chain: mixed solutions
→ ions before reaction → balanced molecular / complete ionic / net ionic equations → stepped mole
conversions → ledger computing maximum extent → why Ca²⁺ limits at the defaults → mass of CaCO₃ → leftover
carbonate and spectators → drag sliders and watch the limiting reagent switch → answer generated variants
with immediate diagnosis → click Ca in the table and see why Ca²⁺ is the common ion → click carbonate and
see how `CaCO3` follows from charge balance → watch the misconceptions fail. All gates green; deployed
static build. **Then stop for owner review; publish (ADR-0010) is the owner's call.**

## Phase 1 — the procedural core (OPEN 2026-07-05)

Items and order per brief §17; this roadmap groups them into two tiers — the procedural core here (brief
items 1–6), the model-bearing topics as Phase 2+ (brief items 7–10) — so each phase ends at a reviewable
boundary. Each item opens with its stress scenario and gets its own scope block when its phase opens:

1. **Dimensional analysis gym** — endless generated quantity-algebra with visible unit cancellation. **← LANDED**
2. **Formula & nomenclature engine** — ions, charges, compounds, acids, polyatomics, both directions. **← LANDED (ionic; covalent/acid deferred)**
3. **Balancing engine** — inspection mode, conservation-matrix view, misconception modes; redox preview. **← LANDED**
4. **Stoichiometry suite** — mass/volume/solution/particle stoich, limiting reagent, percent yield. **← LANDED (3 gym families + the percent-yield lesson + Avogadro datum; particle-count *drills* deferred to Phase 2)**
5. **Valence Table flagship** — lenses, trend mode, formula mode, bonding mode, practice mode (brief §8).
6. **Reaction families** — precipitation, acid-base, gas evolution, combustion, redox (Atlas-backed).

**Item 1 — Dimensional analysis gym — LANDED (2026-07-05).** Opened Phase 1 by building the reusable
**gym instrument** (ADR-0024), stress-scenario = solution/mass conversions (volume·molarity·moles·mass):
`chemkernel.gym.generate_gym` + the `build-gyms` entry point → committed `derived/gyms/<slug>.gym.json`, one
`schemas/gym.schema.json`, the `validate-gyms.mjs` Node gate (re-derives every answer in pure Node), and a
`/gym/` player with the `DimensionalGym` drill island (reveals the cancellation chain on each pick). The first
family `solution_conversions_v1` generates 10 deterministic problems across five kinds; each value is exact
(non-terminating candidates rejected), each conversion's dimensions are re-checked through the units engine,
and each wrong choice is a named cancellation mistake. **Items 2–6 inherit this instrument** — a new item adds
a `family` to `generate_gym` (and a per-kind branch to `validate-gyms` when a new answer shape appears), not a
new pipeline. Deferred inside item 1 (revisit with item 4 and Phase 2 gases): particle/Avogadro conversions
(needs the Avogadro constant registered as a sourced datum), gas-volume conversions, density/percent-
composition chains, and multi-path "diagnose the invalid conversion" drills (brief §13.1).

**Item 2 — formula & nomenclature engine — LANDED (2026-07-05, ionic; ADR-0027).** Stress scenario met:
name↔formula both directions across ionic mono- and polyatomic species incl. the Stock system (iron(III)
sulfate ↔ Fe₂(SO₄)₃). Shipped: a sourced `compound_name` on every ion + 6 new metals (K/Mg/Al/Fe/Cu/Zn,
oracle-checked; Fe/Cu variable-charge); `chemkernel.nomenclature` (name = cation+anion compound_name; formula
= verified crossover); the `ionic_nomenclature_v1` gym family (both directions, named-mistake distractors —
wrong Stock numeral / own-charge subscripts / covalent prefixes); a pure-Node re-derivation branch in
`validate-gyms` (name by concatenation, formula by gcd crossover); a `nomenclature` Atlas concept; the
Valence Table grew to 15 elements. **Deferred to a follow-up:** covalent-prefix naming
(`covalent_nomenclature_v1` — needs a binary-molecular dataset) and acid naming (`acid_nomenclature_v1`);
attaching naming to the Valence-Table formula mode (with item 5); full variable-charge display on the lens
(item 5).

**Item 3 — balancing engine — LANDED (2026-07-05, ADR-0028).** Stress scenario met: a hard
conservation-matrix balance (propane/ethane combustion with odd coefficients) plus the "never mutate a
subscript" misconception made to fail visibly. Shipped: a `balancing_v1` gym family over a curated
skeletal-reaction corpus (synthesis, combustion, decomposition, single/double replacement, acid-base,
net-ionic), each **balanced by the engine** (`balance()`'s null space, not authored coefficients); the
producer emits the **conservation matrix** (per-species element counts + charge) + the coefficient answer,
so the `DimensionalGym` island shows a **live per-element (and charge) tally** by integer addition over
producer data — no runtime chemistry. Distractors are named mistakes: a coefficient perturbation that throws
a stated element off, and the **subscript-mutation trap** (H₂O→H₂O₂, CO→CO₂ — a different real substance,
proven deceptive-and-formula-changing at emit time). New verifiers: a **JS formula parser**
(`scripts/validate/formula.mjs`, closing the ADR-0023 gap) lets `validate-gyms.mjs` re-parse every formula
and re-prove the coefficients zero every element + charge row (positive, gcd 1, reconstructs to the answer);
`chempy` cross-checks the neutral corpus (ADR-0026). Also fixed: the gym islands now present choices in a
deterministic per-problem shuffle (the producer emits the correct choice first). **Deferred:** redox
half-reaction balancing + electron bookkeeping (Phase 2); a free coefficient-*entry* mode (this ships
multiple-choice + the live tally on reveal); the polyatomic-preservation and combustion-quick-pattern
misconception *modes* as distinct UI (the corpus exercises both — SO₄/PO₄ as units, odd-coefficient
combustion — the named distractors cover the traps).

**Item 4 — stoichiometry suite — LANDED (2026-07-05, ADR-0029 + ADR-0030).** Three gym families +
the flagship lesson + the Avogadro datum. Gyms: **`mass_stoichiometry_v1`** (grams → moles → mole ratio →
moles → grams), **`percent_yield_v1`** (theoretical yield, then actual ÷ theoretical × 100), and
**`limiting_mass_v1`** (limiting reagent from two masses → max product mass; the star distractor sizes the
yield from the *excess* reagent) — all forward-generated from clean mole amounts (exact), over the balancing
corpus's neutral reactions; the gate **re-verifies each equation balances** (reusing the item-3 verifier — the
mole ratio/limiting comparison is proven, not trusted) **and** re-derives the mass/percent/limiting-reagent
numerically, with molar-mass consistency enforced across the whole gym corpus. The **flagship percent-yield
lesson** (`percent-yield/zinc-carbonate-percent-yield`, ADR-0030) reuses the precipitation pipeline — the
theoretical yield *is* the precipitate mass — plus an authored `[yield] actual_mass_g` → an optional
`result.percent_yield` block (re-derived by `check-ledger`; nonphysical >100% refused); it inherits the three
equations, ledger, both interactives, and generated practice for free, with a yield card as the only new
render. The **Avogadro constant** is now a curated, sourced, exact datum (`data/constants.toml`,
`bipm-si-2019`). Atlas: a `percent-yield` concept; the drill island's chain caption is family-aware.
**Deferred to Phase 2:** the *particle-count* gym drills (moles↔particles — the datum is in place, but the
drills need scientific-notation display and pair naturally with gas/molar-volume work); the brief-§13.2
*extent-ledger* leg on the gym drills (they carry the recipe + dimensional chain); generalising `build.py`
past single-precipitate double-displacement for a non-precipitation yield lesson. Particle-count stoichiometry
lands once its display plumbing exists — the Avogadro constant is now registered (SOURCES +
`data/`). Sequential reactions and mixture analysis deferred to Phase 2 unless trivial.

**Item 5 — Valence Table flagship (brief §8).** Opens with a **data-curation session** (ADR-0006):
electronegativity (Pauling), atomic/ionic radii, first ionization energy — primary-sourced (NIST/CIAAW),
registered in SOURCES, cross-checked against the `mendeleev` oracle (ADR-0026); likely widen the element
set beyond the current 9 (target: main-group Z ≤ 20 + the transition metals item 2 introduced). Then the
lenses (valence electrons, ion charges, electronegativity, radius, ionization energy — each with the
brief-§8.1 pattern panel: what pattern / why / exceptions / where it shows up) and the modes: **trend mode**
(click a group/period → build-time-computed trend graph), **formula mode** (built — gets naming from item
2), **bonding mode** (electronegativity difference → polarity spectrum + ionic/covalent warning),
**practice mode** (a `periodic_trends_v1` gym family generated *from the same data*: which is larger,
predict the ion, order by IE).

**Item 6 — reaction families (brief §10.4).** Stress scenario: *classify + predict products for the six
core families* — precipitation, acid-base neutralization, gas evolution, combustion, redox
(oxidation-state level), single/double replacement. Scope: the **reaction-atlas entry kind**
(`schemas/reference.schema.json` grows `kind: "reaction-family"`: general form, required conditions,
misconceptions, 3–5 machine-verified example reactions, particle+ledger views); a `reaction-classifier`
module (`chemkernel.reaction` grows family detection: acid-base needs H⁺ transfer bookkeeping, gas
evolution needs the decomposition table — both curated datasets, cited); a `reaction_families_v1` gym
family (given reactants → predict products / classify family / name the spectators). The
`interactive`/`practice` emitters generalize past single-precipitate double-displacement here (acid-base
neutralization is the first new shape). A second flagship lesson (acid-base titration-free neutralization)
anchors the family.

### Proposed session map (one reviewable increment each)

1. ~~Rendering polish + oracle tests + doc sweep + this roadmap~~ (this session).
2. ~~Item 2 — nomenclature data + engine + gym families (+ Atlas nomenclature concept)~~ (landed).
3. ~~Item 3 — balancing gym + conservation-matrix view~~ (landed; ADR-0028 — + a reusable JS formula parser).
4. ~~Item 4 — stoichiometry families + the percent-yield lesson (+ Avogadro datum)~~ (landed; ADR-0029/0030 — 3 gym families + the lesson + the datum; particle drills → Phase 2).
5. Item 5a — element-property data curation (SOURCES + data/ + oracle cross-check).
6. Item 5b — Valence Table lenses + trend/bonding/practice modes.
7. Item 6 — reaction families (atlas kind + classifier + gym + the neutralization lesson).
8. Atlas breadth audit: species-atlas + formula-sheet entry kinds; fill every Phase-0/1 regime-map row;
   **Phase-1 definition-of-done check → stop for owner review** (Phase 2 is the owner's to open).

Sequencing rationale: 2→3→4 build the procedural chain in teaching order on the existing instrument;
5 needs its own data session first; 6 is the largest (new reaction shapes) and benefits from everything
before it. The Atlas breadth-fill runs inside every session (each item ships its concepts), with session 8
as the sweep that catches what slipped.

### Phase-1 definition of done ("relatively complete procedural course")

- All six items landed with their gym families, flagship instruments, and lessons as scoped above.
- **Every Phase-0/1 topic row in [`docs/regime-map.md`](./docs/regime-map.md) shows coverage** (lesson,
  gym, and/or atlas — no "—" in the phase-0/1 tier): measurement/dimensional analysis, atoms & atomic
  mass, mole & molar mass, ions & formula writing, nomenclature, periodic table & trends, balancing,
  reaction classes, stoichiometry, limiting reagents, percent yield, solutions & molarity, precipitation.
- The Atlas carries all four brief-§10 entry kinds (periodic lens ✓, concepts ✓, reaction families,
  species entries) — the formula/equation sheet may open with Phase 2 (its formulas are mostly
  model-bearing).
- 4+ lessons total; every lesson keeps the misconception register + ledger view; all gates green; deployed.
- **Then stop for owner review before Phase 2.**

## Phase 2+ — the model-bearing topics (sketch)

Gases + thermochemistry (energy ledger), bonding & structure (Lewis, VSEPR, polarity, IMFs), equilibrium &
acid-base (ICE = ledger with reversible extent), kinetics ($d\xi/dt$), electrochemistry (electron ledger,
$\Delta G = -nFE$). Sequenced after Phase 1 review; not scoped yet — opening Phase 2 is the owner's call
(scope decision 2026-07-05).

## Parallel track — the Chemical Atlas breadth-fill

As in the sibling: lessons go deep, the reference goes broad. Species atlas, formula/equation sheet,
reaction atlas, concept graph (typed edges, brief §10.5) fill breadth-first alongside whatever phase is
open. Status: **16 concept entries + the Valence Table**; reaction-family and species entry kinds arrive
with Phase-1 items 6 and 8; coverage dashboard in [`docs/regime-map.md`](./docs/regime-map.md).

## Out of scope (v1)

Wet-lab procedural instruction and anything on the ADR-0007 safety line; full organic synthesis (organic
appears only as an explanatory electron-movement lens); detailed quantum-chemistry computation; advanced
spectroscopy; biochemistry and materials chemistry except as examples; inquiry-first pedagogy (ADR-0011).
