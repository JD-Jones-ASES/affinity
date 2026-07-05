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
- **Phase 0 — the vertical slice — IN PROGRESS** (opened 2026-07-05). ChemKernel foundation landed and
  tested: curated element/ion datasets (ADR-0012), formula parser + molar mass, equation balancer via
  rational null space (ADR-0014), exact Decimal/rational arithmetic (ADR-0013). **23 producer tests
  green.** Remaining: units engine, dissociation + net-ionic transformer, Extent solver + species ledger,
  solution schema, Node gates, player + the two interactives, practice generator, Atlas entry, periodic
  lens, CI.

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

**Landed so far (2026-07-05):** scope item 1 (datasets) complete; item 2's formula parser and equation
balancer complete with tests. Remaining in item 2: units/dimensional-analysis engine, dissociation
transformer, net-ionic reducer, Extent solver → species ledger. Items 3–8 not started.

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

## Phase 1 — the procedural core (map, post-review)

Items and order per brief §17; this roadmap groups them into two tiers — the procedural core here (brief
items 1–6), the model-bearing topics as Phase 2+ (brief items 7–10) — so each phase ends at a reviewable
boundary. Each item opens with its stress scenario and gets its own scope block when its phase opens:

1. **Dimensional analysis gym** — endless generated quantity-algebra with visible unit cancellation.
2. **Formula & nomenclature engine** — ions, charges, compounds, acids, polyatomics, both directions.
3. **Balancing engine** — inspection mode, conservation-matrix view, misconception modes; redox preview.
4. **Stoichiometry suite** — mass/volume/solution/particle stoich, limiting reagent, percent yield.
5. **Valence Table flagship** — lenses, trend mode, formula mode, bonding mode, practice mode (brief §8).
6. **Reaction families** — precipitation, acid-base, gas evolution, combustion, redox (Atlas-backed).

## Phase 2+ — the model-bearing topics (sketch)

Gases + thermochemistry (energy ledger), bonding & structure (Lewis, VSEPR, polarity, IMFs), equilibrium &
acid-base (ICE = ledger with reversible extent), kinetics ($d\xi/dt$), electrochemistry (electron ledger,
$\Delta G = -nFE$). Sequenced after Phase 1 review; not scoped yet.

## Parallel track — the Chemical Atlas breadth-fill

As in the sibling: lessons go deep, the reference goes broad. Species atlas, formula/equation sheet,
reaction atlas, concept graph (typed edges, brief §10.5) fill breadth-first alongside whatever phase is
open. Status: not started; coverage dashboard in [`docs/regime-map.md`](./docs/regime-map.md).

## Out of scope (v1)

Wet-lab procedural instruction and anything on the ADR-0007 safety line; full organic synthesis (organic
appears only as an explanatory electron-movement lens); detailed quantum-chemistry computation; advanced
spectroscopy; biochemistry and materials chemistry except as examples; inquiry-first pedagogy (ADR-0011).
