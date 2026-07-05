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
  balance — the four lesson salts assembled by crossover and machine-verified) + two cross-linked concept
  entries, gated by `validate-reference`. **62 producer tests + 6 Node gates + astro build (6 pages) + live
  Pages.** Every item of the brief-§16 definition of done is met. **Phase 0 is complete — stop for owner
  review** before opening Phase 1.

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
