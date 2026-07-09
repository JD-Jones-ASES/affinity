# ROADMAP — Affinity, phase by phase

The multi-session backbone. Each phase: **goal · scope · definition of done**. We open every phase with its
single most-complex "stress" scenario (so the granular fill inherits a solved instrument), then fill
depth-first, and close with a doc sweep. Status lives here; history in [`CHANGELOG.md`](./CHANGELOG.md);
rationale in [`DECISIONS.md`](./DECISIONS.md).

## Status

- **Now (2026-07-09): v1.0.0 RELEASED** — scope frozen (ADR-0053); Phase 2 complete. Counters live in
  `AGENTS.md ## Current state`; per-increment detail in [`CHANGELOG.md`](./CHANGELOG.md) +
  [`docs/sessions/`](./docs/sessions/); the deferred depth is the **v1.1 backlog** below. The scope blocks under
  Phase 0/1/2 are the plan of record (they keep their deferred/open lists).

**Landed — one line per roadmap item (rationale in the cited ADRs, per-increment detail in CHANGELOG):**

- **v1.0.0 release** — scope freeze + the release contract (ADR-0053); the complete 118-element Valence Table
  (ADR-0052); the pre-release QC sweep — chemistry/provenance + verification/navigability hardening (ADR-0051 +
  packages A–D, session 2026-07-09).
- **Electrochemistry tier** — the electron ledger on the Daniell cell (oxidation numbers → half-reactions → E°cell
  → ΔG=−nFE°), the 7th lesson shape (ADR-0050).
- **Kinetics tier** — the ledger in time, orders 0/1/2 (t½ constant/grows/shrinks) + the `kinetics_v1` gym, the 6th
  lesson shape (ADR-0049).
- **Equilibrium & acid–base tier** — the reversible-extent solver + the `equilibrium` lesson kind (6 subtypes:
  weak-acid · buffer · weak-base · Ksp incl. common-ion · polyprotic · titration) + the `weak_acid_ph_v1` gym + the
  `prediction` kind (Q vs Kₛₚ, both verdicts) + the K/K_w/K_sp formula entries (ADR-0048).
- **Bonding & structure tier** — the Lewis electron-ledger engine + the `molecule` Atlas kind + the
  `lewis_structures_v1` gym + the `structure` and `comparison` lesson shapes + intermolecular forces
  (ADR-0044/0045/0046/0047).
- **Gases + thermochemistry tier** — the formula/equation sheet (ADR-0039), the `gas_laws_v1` (ADR-0040) +
  `calorimetry_v1` (ADR-0042) gyms, the gas-stoichiometry (ADR-0041) + energy-ledger/Hess (ADR-0043) lessons.
- **Phase 1 — the procedural core** — dimensional-analysis gym (ADR-0024), the nomenclature engine (ADR-0027), the
  balancing gym + JS parser (ADR-0028), the stoichiometry suite + percent-yield lesson + Avogadro datum
  (ADR-0029/0030), the Valence Table flagship modes (ADR-0031/0033/0034), reaction families + the neutralization
  lesson (ADR-0035/0036/0037), the species Atlas kind (ADR-0038); free-entry practice (ADR-0032).
- **Phase 0 — the vertical slice** — the whole emit → verify → present pipeline on the calcium-carbonate
  precipitation lesson: ChemKernel engine (ADR-0012–0019), the solution schema + Node gates (ADR-0020/0023), the
  parity-verified player (ADR-0021/0022), the Atlas + Valence Table, CI → live Pages (ADR-0010); + a 2nd
  limiting-reagent lesson.
- **Bootstrap** — docs-first founding: routing + close-out protocol, ADR-0001…0011, the architecture contract, the
  regime map, SOURCES, licenses, the private repo.

## v1.1 backlog

The v1.0.0 scope freeze (ADR-0053) deferred the following; none is a basic-chemistry gap.

- **Kinetics depth:** the **Arrhenius** temperature dependence of k (k = A·e^(−Eₐ/RT)) — a formula-sheet entry + a lesson.
- **Electrochemistry depth:** the **Nernst** equation (E away from standard conditions — the `galvanic` subtype
  extends), a ΔG=−nFE/Nernst formula-sheet entry, more cells (concentration / electrolytic), and a **redox-balancing gym**.
- **B7 / O3 — build-time KaTeX:** move the practice island's runtime KaTeX to build-time rendering (restoring
  ADR-0001 site-wide), then add a **bundle-scan gate** so it can't regress.
- **B8 — producer fail-loud guards:** the `extent.py` product-row nonnegative guard; `reaction.py` `dissociate()`
  ambiguity refusal; `build.py` misnamed-lesson-file error; `structure.py` duplicate-bond guard; float rejection at
  the spec boundary (ADR-0013). All latent (CI backstops committed output); each wants a refusal test.
- **C7 / C8 — producer-side display polish:** `mass_g_display` 3-decimal → 3-sig-fig (ADR-0025); ionic-equation phase
  labels; diagnostic spacing; the seeded answer-shuffle so the correct choice isn't always emitted first; gym anion naming.
- **Bonding corpus-depth:** octet exceptions (BeH₂/BF₃/PCl₅/SF₆); resonance (CO₃²⁻/NO₃⁻); more structure lessons
  (NH₃/CH₄); more comparison axes (melting point, solubility); a "which IMF dominates?" gym drill; a formal-charge gym drill.
- **Smaller / optional:** endothermic / multi-step Hess-cycle lessons; the gas and titration lessons' **slider
  interactives**; transition-metal + heavy covalent radii; ionic radii (per-ion, coordination-dependent); further
  Valence-Table lenses (oxidation state / electron affinity / metallic character / density / abundance);
  particle-count gym drills. Always in season inside settled contracts: Atlas breadth-fill, further lessons,
  docs-only sessions.

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
6. **Reaction families** — precipitation, acid-base, gas evolution, combustion, redox (Atlas-backed). **← LANDED (classifier + Atlas kind + gym + neutralization lesson; ADR-0035/0036/0037)**

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

**Item 6 — reaction families (brief §10.4) — LANDED (2026-07-08, ADR-0035/0036/0037).** Stress scenario met:
*classify + predict products for the core families* — combustion, synthesis, decomposition, single/double
replacement, precipitation, acid-base neutralization, gas evolution, plus a machine-checkable redox flag.
Shipped: the **reaction classifier** (`chemkernel.reaction.classify_reaction`, most-specific-first over the
sourced solubility/acid-base/decomposition datasets; redox by the free-element signature) + the two curated
datasets (`data/acids-bases.toml`, `data/decomposition.toml`, `chemkernel.reactivity`); the **reaction-family
Atlas kind** (`schemas/reaction-family.schema.json` — 7 families / 21 engine-classified example reactions with
net-ionic views; a shared `balancecheck.mjs` re-proves balance + redox in Node); the **`reaction_families_v1`
gym** (classify-the-family + name-the-spectators, both categorical); and the **acid-base neutralization
lesson** (first non-precipitation lesson — the `result.product`/`salt` generalisation + the phase-general
interactive gives it the limiting-reagent slider + generated practice, precipitation lessons byte-identical).
**Deferred within item 6:** full oxidation-number assignment (Phase-2 redox); predict-products gym drills
(needs a careful product-distractor generator); a generic double-replacement Atlas entry (no driving force =
not a real reaction); a gas-evolution *lesson* (a gas product leaves solution — the ledger closes the same,
but the product mass isn't the headline); the diprotic coefficient-story neutralization (machinery handles it
— a second lesson, not new code); further gas-forming intermediates (sulfurous acid needs the sulfite ion).

### Proposed session map (one reviewable increment each)

1. ~~Rendering polish + oracle tests + doc sweep + this roadmap~~ (this session).
2. ~~Item 2 — nomenclature data + engine + gym families (+ Atlas nomenclature concept)~~ (landed).
3. ~~Item 3 — balancing gym + conservation-matrix view~~ (landed; ADR-0028 — + a reusable JS formula parser).
4. ~~Item 4 — stoichiometry families + the percent-yield lesson (+ Avogadro datum)~~ (landed; ADR-0029/0030 — 3 gym families + the lesson + the datum; particle drills → Phase 2).
5. ~~Item 5a — element-property data curation (SOURCES + data/ + oracle cross-check)~~ (landed; ADR-0031 — 23 elements + electronegativity/covalent-radius/first-ionization-energy, primary-sourced + mendeleev-checked; completed to all **118 elements** at v1.0.0, ADR-0052).
6. ~~Item 5b — Valence Table lenses + trend/bonding/practice modes~~ (landed; ADR-0033/0034 — four modes +
   the `periodic_trends_v1` gym + Q4 resolved).
7. ~~Item 6 — reaction families (atlas kind + classifier + gym + the neutralization lesson)~~ (landed; ADR-0035/0036/0037 — classifier + 7-family Atlas + `reaction_families_v1` gym + the neutralization lesson).
8. ~~Atlas breadth audit: species-atlas entry kind; fill every Phase-0/1 regime-map row; Phase-1
   definition-of-done check~~ (landed; ADR-0038 — 14 species + the `atomic-mass` concept + the reaction-family
   cross-link fix; formula/equation sheet deferred to Phase 2). **DoD met → stop for owner review** (Phase 2 is
   the owner's to open).

Sequencing rationale: 2→3→4 build the procedural chain in teaching order on the existing instrument;
5 needs its own data session first; 6 is the largest (new reaction shapes) and benefits from everything
before it. The Atlas breadth-fill runs inside every session (each item ships its concepts), with session 8
as the sweep that catches what slipped.

### Phase-1 definition of done ("relatively complete procedural course") — MET (2026-07-08, pending owner review)

- ✓ All six items landed with their gym families, flagship instruments, and lessons as scoped above.
- ✓ **Every Phase-0/1 topic row in [`docs/regime-map.md`](./docs/regime-map.md) shows coverage** (no "—" in
  the phase-0/1 tier): measurement/dimensional analysis, atoms & atomic mass (← filled this session),
  mole & molar mass, ions & formula writing, nomenclature, periodic table & trends, balancing,
  reaction classes, stoichiometry, limiting reagents, percent yield, solutions & molarity, precipitation.
- ✓ The Atlas carries all four brief-§10 entry kinds: periodic lens, concepts, reaction families, **species
  entries** (landed this session, ADR-0038). The formula/equation sheet opens with Phase 2 (mostly
  model-bearing) — the DoD explicitly relaxes it here.
- ✓ 4 lessons total, each keeping the misconception register + ledger view; 7 gates green; deployed to Pages.
- **→ Now stopped for owner review before Phase 2** (opening Phase 2 is the owner's call).

## Phase 2 — the model-bearing topics (OPEN 2026-07-08)

**Goal.** Extend the one machine (species ledger over extent, ADR-0002) to the topics where the answer is
*model-exact* rather than ledger-exact: gases, thermochemistry (the energy ledger), bonding & structure,
equilibrium & acid-base (ICE = ledger with reversible extent), kinetics ($d\xi/dt$), electrochemistry (electron
ledger, $\Delta G = -nFE$). The honesty pivot: regime-2 content is exact *inside a disclosed model* — so the
**model-assumed badge does real work**, and where the machine can still check something (dimensional homogeneity,
conservation, the algebra given the model) it does. Opened on **gases + thermochemistry** (brief §17 item 7); the
rest sequences after, each with its own scope block when its increment opens.

**Opening tier — gases + thermochemistry + the formula sheet:**
- **Formula/equation-sheet Atlas kind — LANDED** (ADR-0039): the fourth brief-§10 Atlas kind. 8 relations with
  variables/units, **dimensional homogeneity machine-checked** (native `chemkernel.dimension` SI-vector engine,
  re-derived in pure Node); model-exact relations disclose their assumptions; the gas constant R registered. This
  is the reference instrument the gas/thermo gym + lesson link to.
- **Gas-law computation — LANDED** (ADR-0040): `units.py` gained the deferred pressure/temperature dimensions
  (ADR-0015; °C→K is an affine boundary conversion, not a scaling unit); the `gas_laws_v1` gym (PV=nRT +
  combined-gas-law, numeric free-entry per ADR-0032, model-assumed badge — regime-2 answers are model-exact then
  3-sig-fig-rounded, gate re-derives PV=nRT numerically within tolerance). **Deferred within:** kPa/torr units and
  °C display niceties; energy/charge dimensions (thermo/electrochem).
- **Gas-stoichiometry lesson — LANDED** (ADR-0041): the vertical slice — the extent ledger drives a gas volume via
  PV=nRT (Zn + 2 HCl → ZnCl₂ + H₂). `build.py` generalised past two-solution double-displacement to a third
  reported-product shape: a **weighed-mass given** (grams ÷ molar mass → moles, dimension-certified, still
  terminating) + a **`result.gas` block** (the collected gas's volume through the units engine from the sourced R,
  model-exact-then-rounded under the model-assumed badge; check-ledger re-derives V=nRT/P, 6-way tamper-tested). The
  moles/limiting are ledger-exact; the volume is model-exact. **Generated practice** landed too (6 variants —
  free-entry volume/leftover + categorical limiting; the reaction constants travel in a `practice.gas` block so
  check-parity re-derives without an interactive; reuses the generic practice island; 6-way tamper-tested).
  **Deferred within (a follow-on increment):** the lesson's **slider interactive** (mass/volume/molarity sliders →
  the gas volume — `ExtentBar` is cation/anion-locked, needs its own component); collecting the gas **over water** (a
  vapor-pressure table); `kPa`/`torr` units.
- **Calorimetry gym — LANDED** (ADR-0042): $q=mc\Delta T$, solve for any variable, over sourced specific heats
  (`data/specific-heats.toml`, OpenStax Table 5.1). The `units.py` engine gained the deferred **energy** dimension
  (J, kJ, J/(g·K), kept independent of pressure·volume); the first gym wearing **both** the data-sourced (specific
  heats) and model-assumed (calorimetry model) badges; model-exact-then-rounded, the gate re-derives $q=mc\Delta T$.
- **Thermochemistry (energy ledger) — LANDED** (ADR-0043): reaction enthalpy attached to extent
  ($\Delta H_\text{rxn}\cdot\xi$) via **Hess's law** over sourced $\Delta H_f^\circ$ (`data/formation-enthalpies.toml`,
  OpenStax Appendix G) — the `methane-combustion-enthalpy` lesson. `build.py`'s fourth reported-product shape (a
  `result.energy` headline); the first fully **molecular** lesson (no ionic equation); `units.py` gains `kJ/mol`;
  triple-badged; the `reaction-enthalpy` concept; **generated practice** (heat/leftover/limiting, a `practice.energetics`
  constants block re-derived by check-parity — ADR-0043 2nd increment); and the **`formula-enthalpy-of-reaction`** Hess
  sheet entry (ΔH_rxn=Σν·ΔH_f°, both sides molar energy — machine-checked; ADR-0043 3rd increment). **Deferred within:**
  endothermic / multi-step Hess-cycle lessons; and within calorimetry, initial/final-temperature framing
  ($\Delta T = T_f - T_i$) + cooling (negative $q$) drills.

**Bonding & structure tier — OPEN (2026-07-08, ADR-0044):** the **Lewis electron-ledger engine**
(`chemkernel.structure`, `compute_ledger`) + the **`molecule` Atlas kind** + the **`lewis_structures_v1` gym** — the
electron-structure counterpart of the species ledger. The valence total, octets, formal charges, and their conservation
are **machine-checked** (exact integer accounting, re-derived in pure Node); the **VSEPR geometry** keys a sourced table
(`data/vsepr.toml`, OpenStax §7.6) on the machine-derived electron-domain count; **bond ΔEN** reuses the sourced Pauling
values + `data/bonding.toml`; **molecular polarity** is authored + disclosed (model-assumed, neutral molecules only). 6
molecules (H₂O/CO₂/NH₃/CH₄/CH₂O/NH₄⁺) + the `lewis-structure`/`vsepr` concepts; `/reference/molecules/`. The gym drills
valence total / electron domains (free-entry) + molecular geometry (categorical, the electron-domain-geometry distractor)
off the shared engine — the counting practice for the ledger. The **deep vertical slice — the `structure` lesson kind**
(`bonding/water-molecular-shape`, ADR-0045) — landed: a single molecule stepped valence → Lewis → VSEPR → polarity on the
shared `compute_ledger`, a new tight `structure-lesson.schema.json` (no reaction), the electron-ledger re-derivation
factored into a shared `structurecheck.mjs`. **IMFs landed** (ADR-0046): `structure.classify_imf` derives the dominant
intermolecular force from the verified structure + polarity (the H-on-N/O/F test is exact; the ranking sourced), delivered
as the molecule Atlas `intermolecular` block + sourced boiling points + the `intermolecular-forces` concept. **Deferred
within:** the IMF **comparison lesson** (a new multi-molecule lesson shape — teaching the boiling-point trend as the
payoff); octet exceptions (electron-deficient BeH₂/BF₃, expanded PCl₅/SF₆); resonance (CO₃²⁻/NO₃⁻ — equivalent-structure
handling); more structure lessons (NH₃/CH₄); a formal-charge gym drill (wants nonzero-FC molecules, i.e. resonance).

**Equilibrium & acid-base tier — OPEN (2026-07-08, ADR-0048):** the thesis made literal — the **ICE table is the species
ledger** ($c_i = c_{i,0} + \nu_i\,x$) with the extent solved from **mass action** ($Q(x)=K$), not driven to a limiting
reagent. The **reversible-extent solver** (`chemkernel.equilibrium.solve_equilibrium`) finds the root by **bisection to high
precision** (exact Decimal — general beyond the quadratic, ready for Ksp/buffers/polyprotic); the root is
model-exact-then-rounded (ADR-0040 pattern), and the machine-check is the **residual** ($Q$ at the committed concentrations
reproduces $K$) plus the gate's **independent re-solve** (`equilibriumcheck.mjs`, shared, in Node). A new **`equilibrium`
lesson kind** (the fourth shape — own tight `equilibrium-lesson.schema.json`, `build_equilibrium_lesson`,
`*.equilibrium.json`) → **`equilibrium/acetic-acid-ph`**: 0.100 M acetic acid, $K_a=1.8\times10^{-5}$ → $[\mathrm{H^+}]=
1.33\times10^{-3}$ M, **pH 2.88**, 1.33% ionized; the misconception is treating the weak acid as strong. Triple-badged (ICE
identity machine-checked / $K_a$ data-sourced / equilibrium position + pH model-assumed); $K_a$ from
`data/ionization-constants.toml` (OpenStax App H), the HA ⇌ H⁺ + A⁻ dissociation DRY-sourced from `data/acids-bases.toml`;
concepts `chemical-equilibrium` + `ph`; a static `EquilibriumLesson.astro`. The **`solubility` subtype landed too** (2nd
increment): `equilibrium/calcium-fluoride-solubility` — `solve_equilibrium` gained an `in_quotient` flag so a **pure solid
is excluded from Q** (and, in excess, does not bound the forward extent — the bracket grows until Q > K), making
$K_{sp}=[\mathrm{Ca^{2+}}][\mathrm{F^-}]^2=4s^3$ a **cubic** the bisection solver handles; one schema, two subtypes
(`subtype` discriminator, dispatched by `acid` vs `salt`); $K_{sp}$ from `data/solubility-products.toml` (App J), the salt
composition machine-checked by charge crossover; the `solubility-product` concept; it closes the Phase-0 precipitation loop.
The **`weak-base` subtype landed too** (3rd increment): `equilibrium/ammonia-ph` — a weak base ionizes against water
(NH₃ + H₂O ⇌ NH₄⁺ + OH⁻), and **water is the pure solvent excluded from Q** by the *same* `in_quotient=False` flag the Ksp
solid uses, so `solve_equilibrium` is **reused unchanged**; the extent is [OH⁻] and the **$K_w$ bridge** ($[\mathrm{H^+}]
[\mathrm{OH^-}]=10^{-14}$, pH + pOH = 14.00) gives the pH — 0.100 M NH₃, $K_b=1.8\times10^{-5}$ → **pOH 2.88, pH 11.12**,
the exact mirror of the acetic-acid lesson. $K_b$/$K_w$ from `data/ionization-constants.toml` (App I/§14.1; `acids-bases.toml`
untouched), the base's proton accounting machine-checked on load; the `water-autoionization` concept. The **`buffer` subtype
landed too** (4th increment): `equilibrium/acetate-buffer` — the same weak-acid reaction with the conjugate base A⁻ **already
present** ([A⁻]₀ > 0, the solver's nonzero-initial-product case), so the **common ion** suppresses ionization (Le Chatelier)
— 0.100 M acetic acid + 0.100 M acetate → **pH 4.74 = p$K_a$**, 74× less ionized than the acid alone; **Henderson–Hasselbalch**
(pH = p$K_a$ + log([A⁻]/[HA])) is machine-checked as the mass-action law logged, and the lesson re-solves the acid alone for
the common-ion contrast; the `buffer` concept. The tier's **`weak_acid_ph_v1` gym** landed too (5th increment) —
pH-of-a-weak-acid free-entry drills, model-exact-then-rounded + data-sourced, the gate re-solving the mass-action root in pure
Node (the same `solveEquilibrium` the lessons' gate uses — one solver, four call sites). The **common-ion solubility variant**
landed too (6th increment): `equilibrium/calcium-fluoride-common-ion` — CaF₂ into 0.10 M F⁻ (a shared ion pre-loaded, the
buffer's nonzero-initial-product case now on the **cubic** — the solver reused unchanged), dissolution suppressed **53 900×**
to $4.0\times10^{-9}$ M; a variant of the `solubility` subtype (optional `common_ion`), the pure-water solubility re-solved
for the contrast; the `common-ion-effect` concept. The **polyprotic** subtype landed too (7th increment):
`equilibrium/phosphoric-acid-ph` — 0.100 M H₃PO₄ ionizing in stages Kₐ1≫Kₐ2≫Kₐ3, the solver run **once per stage** on the
previous stage's equilibrium (the successive treatment; top-level ice = stage 1, `result.later_stages` the rest) → **pH 1.62**;
the [H⁺]-tracks-stage-1 and amphiprotic-[HPO₄²⁻]≈Kₐ2 payoffs fall out of the solve; a `[polyprotic]` data table + two new
ion-table anions (composition machine-checked on load) + a `polyprotic-acid` concept. A **titration** subtype landed too (8th
increment): `equilibrium/acetic-acid-titration` — a weak acid (acetic) titrated by a strong base (NaOH), the ledger *marched*
by region (weak acid/buffer → the conjugate base's weak-base solve at equivalence → excess base), each point reusing
`solve_equilibrium`; the top-level ice = the initial point, a `titration` block carries the (volume, pH) curve + landmarks;
the player draws a **build-time SVG** (the tier's first plot) — initial pH 2.88, pH = pKₐ = 4.74 at half-equivalence, basic at
equivalence (pH 8.72); reuses acetic acid's Kₐ + NaOH (no new data); a `titration` concept; the gate recomputes the whole
curve. **Six subtypes now** (+ `titrant` → titration), **plus the `prediction` lesson kind** (Q vs $K_{sp}$ — a snapshot, not a
solve; 9th increment: `equilibrium/calcium-fluoride-precipitation`, a `reaction-quotient` concept, `verifyPrediction` in the
gate) — with **both verdicts** (CaF₂ forms; dilute Mg(OH)₂ stays clear). The **K/K_w/K_sp formula-sheet entries** landed too
(10th increment — Kₐ/K_b/K_w/K_sp + Kₐ·K_b=K_w as **dimensionless activity** relations, $a_X=[X]/c^\circ$, fitting the monomial
dimension engine unchanged; pH/pOH stay in the `ph` concept, owner-decided). **The equilibrium & acid-base tier is now
feature-complete.** Optional leftovers: a titration slider interactive; a weak-base/buffer gym extension. **Next tier: kinetics
is now OPEN** (ADR-0049 — first-, second-, and zero-order decay; see the Status scope block), then electrochemistry.

**Then (each its own increment, sketch):** the rest of bonding (above) + the rest of equilibrium & acid-base (above);
**kinetics is open** (ADR-0049 — first-, second-, and zero-order decay + the `kinetics_v1` gym landed on one order-general engine;
next: Arrhenius); **electrochemistry is open** (ADR-0050 — oxidation numbers *completed* the free-element redox flag from ADR-0035;
the electron ledger + E°cell + $\Delta G=-nFE$ landed on the Daniell cell; next: the Nernst equation). **All Phase-2 tiers are now
open.** Further formula-sheet entries ($\Delta G=\Delta H-T\Delta S$, Arrhenius, Nernst) land with their topics.

**Definition of done (a reviewable Phase-2 boundary):** deferred to the opening tier's close — at minimum the
gas/thermo tier lands its gym(s) + at least one gas or calorimetry lesson (misconception register + ledger view
kept), the formula sheet grows to cover the tier, every new regime-2 claim carries the model-assumed badge with its
disclosure, and all gates stay green + deployed. The full Phase-2 DoD firms up as the later tiers scope.

## Parallel track — the Chemical Atlas breadth-fill

As in the sibling: lessons go deep, the reference goes broad. Species atlas, formula/equation sheet,
reaction atlas, concept graph (typed edges, brief §10.5) fill breadth-first alongside whatever phase is
open. Status: **all four brief-§10 Atlas kinds ship, plus a fifth structural surface** — periodic lens (Valence
Table), concepts, reaction families (ADR-0035), species (ADR-0038), the **formula/equation sheet** (ADR-0039), and
now the **`molecule` structure kind** (ADR-0044 — Lewis electron ledgers + VSEPR) — plus the typed-edge concept graph
woven through every entry's `related` links. Counts live in `AGENTS.md ## Current state`; coverage dashboard in
[`docs/regime-map.md`](./docs/regime-map.md).

## Out of scope (v1)

Wet-lab procedural instruction and anything on the ADR-0007 safety line; full organic synthesis (organic
appears only as an explanatory electron-movement lens); detailed quantum-chemistry computation; advanced
spectroscopy; biochemistry and materials chemistry except as examples; inquiry-first pedagogy (ADR-0011).
