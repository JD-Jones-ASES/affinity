# ROADMAP — Affinity, phase by phase

The multi-session backbone. Each phase: **goal · scope · definition of done**. We open every phase with its
single most-complex "stress" scenario (so the granular fill inherits a solved instrument), then fill
depth-first, and close with a doc sweep. Status lives here; history in [`CHANGELOG.md`](./CHANGELOG.md);
rationale in [`DECISIONS.md`](./DECISIONS.md).

## Status

- **Now (2026-07-08): Phase 1 OPEN — items 1–5 landed and deployed; item 6 (reaction families) is next**,
  then the Atlas breadth audit (session-map #8) and the Phase-1 definition-of-done check → owner review
  before Phase 2. Counters live in `AGENTS.md ## Current state`; per-increment detail in
  [`CHANGELOG.md`](./CHANGELOG.md) + [`docs/sessions/`](./docs/sessions/); scope blocks below are the plan
  of record.
- **Bootstrap — COMPLETE** (2026-07-05): docs-first founding — routing + close-out protocol, ADR-0001…0011,
  architecture contract, regime map, SOURCES, licenses, private repo.
- **Phase 0 — the vertical slice — COMPLETE** (2026-07-05, owner-reviewed): the whole emit → verify →
  present pipeline on the calcium-carbonate precipitation lesson — ChemKernel engine (ADR-0012…0019), one
  solution schema + the five-gate Node suite (ADR-0020/0023), the player with both parity-verified
  interactives (ADR-0021/0022), practice tab, authoring guide, CI → live Pages (ADR-0010), and the Chemical
  Atlas (Valence Table + concepts). All eight brief-§16 items met.
- **Post-Phase-0 breadth** (2026-07-05): second lesson `calcium-phosphate-limiting` — first non-1:1
  stoichiometry, limiting-by-capacity teaching; Atlas to 13 concepts.
- **Phase 1 — the procedural core — OPEN (2026-07-05), filling depth-first:**
  - **Item 1** — dimensional-analysis gym, the reusable generated-problem instrument (ADR-0024).
  - **Item 2** — formula & nomenclature engine, ionic both directions + Stock system (ADR-0027).
  - **Item 3** — balancing gym + conservation-matrix tally + the pure-JS formula parser (ADR-0028).
  - **Item 4** — stoichiometry suite: 3 gym families + the percent-yield lesson + the Avogadro datum
    (ADR-0029/0030).
  - **Practice hardening** — numeric answers are free-entry with diagnostics, never gameable menus; gyms
    and the lesson Practice tab both (ADR-0032, owner-caught).
  - **Item 5** — the Valence-Table flagship: 5a sourced property data (ADR-0031); 5b the four modes
    (lenses/trends/formula-builder/bonding) + the `periodic_trends_v1` gym + architecture Q4 resolved
    (ADR-0033/0034).

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
5. **Valence Table flagship** — lenses, trend mode, formula mode, bonding mode, practice mode (brief §8). **← LANDED (5a data + 5b modes)**
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

**Item 5 — Valence Table flagship (brief §8) — COMPLETE.** **Sub-item 5a — data curation — LANDED
(2026-07-05, ADR-0031):** the element set widened to **23** (first-20 H…Ca + Fe/Cu/Zn) and
**electronegativity** (Pauling/OpenStax), **covalent radius** (Cordero 2008, main-group Z ≤ 20), and **first
ionization energy** (NIST) curated as optional Decimal fields — primary-sourced, registered in SOURCES,
cross-checked against the `mendeleev` oracle (ADR-0026), emitted into the Valence Table and gated
(SOURCES-resolution now enforced in `validate-reference`). **Sub-item 5b — the modes — LANDED (2026-07-08,
ADR-0033/0034):** the five **lenses** (ion charge, valence electrons, electronegativity, covalent radius,
first ionization energy), each a color overlay + the brief-§8.1 pattern panel rendered with the interpretive
marker (Q4 resolved — no fourth badge); **trend mode** (SVG property graphs by period/group, honest gaps);
**formula mode** (the full verified crossover product with engine names + per-pair proven mistakes — the
item-2 naming hookup closed, variable-charge metals surfacing all their ions); **bonding mode** (exact
integer ΔEN vs the sourced OpenStax thresholds, `data/bonding.toml`, caution attached); **practice mode**
(the `periodic_trends_v1` gym family — compare / predict-the-ion / order-by-IE, generated from the same
data, exceptions answered from data and named, gate-cross-checked against the emitted table).
*Deferred within item 5:* transition-metal covalent radii (spin-state pass); **ionic radii** (per-ion,
coordination-dependent — belongs on the ion table); oxidation-state / electron-affinity / metallic-character
/ density / abundance lenses (brief §8.1 lists more than the curated data yet supports — each needs its own
data-curation pass); a metal/nonmetal field (would make the bonding caution data-driven and enable "which
compound is most likely ionic" drills); acid naming in the formula builder (with the item-2 follow-up).

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
5. ~~Item 5a — element-property data curation (SOURCES + data/ + oracle cross-check)~~ (landed; ADR-0031 — 23 elements + electronegativity/covalent-radius/first-ionization-energy, primary-sourced + mendeleev-checked).
6. ~~Item 5b — Valence Table lenses + trend/bonding/practice modes~~ (landed; ADR-0033/0034 — four modes +
   the `periodic_trends_v1` gym + Q4 resolved).
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
open. Status: **19 concept entries + the Valence Table**; reaction-family and species entry kinds arrive
with Phase-1 items 6 and 8; coverage dashboard in [`docs/regime-map.md`](./docs/regime-map.md).

## Out of scope (v1)

Wet-lab procedural instruction and anything on the ADR-0007 safety line; full organic synthesis (organic
appears only as an explanatory electron-movement lens); detailed quantum-chemistry computation; advanced
spectroscopy; biochemistry and materials chemistry except as examples; inquiry-first pedagogy (ADR-0011).
