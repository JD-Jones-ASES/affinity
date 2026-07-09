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

**As-built (2026-07-08 — Phase 0 + Phase 1 complete + owner-reviewed; Phase 2 OPEN — the formula-sheet Atlas kind (ADR-0039), the gas-laws gym (ADR-0040), the gas-stoichiometry lesson (ADR-0041), the calorimetry gym (ADR-0042), the energy-ledger lesson (ADR-0043), the bonding tier — the Lewis electron-ledger engine + `molecule` Atlas kind + the `lewis_structures_v1` gym (ADR-0044), the bonding & structure lesson — the `structure` lesson kind (ADR-0045), intermolecular forces — a structure-derived dominant-IMF classifier (ADR-0046), the IMF comparison lesson — the `comparison` lesson kind (ADR-0047), and **equilibrium & acid-base opened** — the reversible-extent solver + the `equilibrium` lesson kind (ADR-0048) — landed).** The pipeline runs end to end — compute → emit →
verify → **present**. The engine: `data/` (element, ion, solubility, acid-base, decomposition, constants, bonding, specific-heats, formation-enthalpies, **VSEPR**, boiling-points, **ionization-constants** datasets, ADR-0012/0017/0035/0039/0042/0043/0044/0046/0048);
`chemkernel.data`/`formula`/`balance`/`units`/`dimension`/`extent`/`equilibrium`/`reaction`/`reactivity`/`solubility`/`structure`/`build` (ADR-0012–0019/0035/0039/0044/0048);
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
molar masses and balancer in pytest. **Current counters: 16 lessons (2 precipitation + 1 percent-yield + 1
acid-base neutralization, ADR-0037; + 1 gas-stoichiometry — the ledger drives a gas volume via PV=nRT, ADR-0041;
+ 1 thermochemistry/energy-ledger — the ledger drives a heat q=ΔH_rxn·ξ via Hess's law, ADR-0043; + 2 bonding/structure —
a single molecule's Lewis electron ledger stepped to VSEPR + polarity, the `structure` lesson kind, ADR-0045: water
bent-polar + CO₂ linear-nonpolar; + 1 bonding/comparison — several molecules vs. boiling point with the IMF-strength
trend machine-verified, the `comparison` lesson kind, ADR-0047; + 7 equilibrium — the ICE table = the species ledger with
the extent solved from mass action Q=K, the `equilibrium` lesson kind with six subtypes, ADR-0048: the weak-acid pH of acetic
acid + a buffer (acetic acid + acetate — the common-ion effect + Henderson–Hasselbalch, the solver's nonzero-initial-product
case) + the weak-base pH of ammonia (water excluded from Q, pH via the Kw bridge) + the Ksp molar solubility of CaF₂ — a pure
solid excluded from Q, a cubic — plus a common-ion variant (CaF₂ into 0.10 M F⁻, dissolution suppressed 59 400×) + the
polyprotic staged pH of H₃PO₄ (Kₐ1≫Kₐ2≫Kₐ3, the solver run once per stage on the previous stage's output) + a titration curve
(acetic acid vs NaOH — the ledger marched by region, a build-time SVG of verified points))
+ 12 gyms (conversions + ionic nomenclature + balancing + mass
stoichiometry + percent yield + limiting reagent + periodic trends + reaction families + gas laws + calorimetry +
Lewis structures + weak-acid pH; 120 drills — numeric families free-entry, ADR-0032), 1 Valence Table (23 elements; four modes — Explore lenses /
Trends / Formula builder / Bonding — over sourced properties + the 182-pair named crossover product + the
`data/bonding.toml` ΔEN rule, ADR-0031/0033) + 32 concept entries (incl. `chemical-equilibrium` + `ph` + `solubility-product` + `water-autoionization` + `buffer` + `common-ion-effect` + `polyprotic-acid` + `titration`, ADR-0048) + 7 reaction families (21 engine-classified
example reactions, ADR-0035) + 14 species entries (composition/charge/molar mass derived from the formula +
re-summed in Node, ADR-0038) + 6 molecule structure entries (Lewis electron ledger — valence total/octet/formal charge —
machine-checked, re-derived in Node, + VSEPR geometry from `data/vsepr.toml`, + a structure-derived **dominant IMF**
ADR-0046, ADR-0044) + 9 formula-sheet entries
(dimensional homogeneity machine-checked, ADR-0039 — incl. Hess's law ΔH_rxn=Σν·ΔH_f°, ADR-0043) = **69 Atlas reference
objects**, 383 producer tests + 7 Node gates + `astro build` (38 pages) + live CI/Pages green. Lesson practice mass/leftover/volume/heat questions are
free-entry too (ADR-0032); gas-stoichiometry (ADR-0041) + energy-ledger (ADR-0043) practice re-derive from reaction constants with no interactive block.**

## ChemKernel module map (brief §6)

| Module | Responsibility | Status |
|---|---|---|
| `formula.py` parser | formula string → element-count vector, charge, phase, display LaTeX (pure; no data) | **built** (ADR-0014) |
| `data.py` data layer | loads `data/` datasets (elements + **periodic properties**, ions, solubility, **constants**, **specific heats**, **formation enthalpies**, **VSEPR geometry**, **boiling points**); molar mass; the Avogadro + gas constants; ΔH_f° by (formula, phase); the VSEPR table keyed (domains, lone pairs); boiling points by formula (IMF evidence, ADR-0046); acid ionization constants K_a by acid formula + base ionization constants K_b (+ conjugate acid, proton accounting machine-checked) + the water ion-product K_w + solubility products K_sp by salt formula (with ion counts derived by charge crossover + the salt composition machine-checked, ADR-0048); the only path to empirical values (ADR-0006); self-validates on load | **built** (ADR-0012, +constants ADR-0030, +properties ADR-0031, +specific heats ADR-0042, +ΔH_f° ADR-0043, +VSEPR ADR-0044, +boiling points ADR-0046, +K_a/K_b/K_w/K_sp ADR-0048) |
| `balance.py` balancer | element+charge conservation matrix over ℚ → SymPy null space → smallest positive integer coefficients; re-verified; fails on ambiguity | **built** (ADR-0014) |
| `units.py` engine | `Quantity` over an amount/mass/volume/**pressure/temperature/energy** `Dim` basis (pressure + temperature for gases, ADR-0040; **energy** for thermochemistry, ADR-0042 — kept independent of pressure·volume); exact Decimal; units cancel through ×/÷; rejects invalid conversions; certifies + computes the gas-law product (`(n·R·T/P).to("L")`), the calorimetry heat (`(m·c·ΔT).to("J")`), and the reaction heat (`(ΔH_rxn·ξ).to("kJ")` — `kJ/mol` registered, ADR-0043). °C→K is an affine boundary conversion (absolute T); ΔT rides the temperature basis as a difference (1 °C = 1 K) | **built** (ADR-0015, +gas dims ADR-0040, +energy ADR-0042, +kJ/mol ADR-0043) |
| `dimension.py` SI engine | definitional unit → SI dimension 6-vector `[mass, length, time, amount, temperature, current]`; term (monomial) dimension by integer-vector arithmetic; homogeneity check for the formula-sheet reference relations. Separate from `units.py` (ADR-0015 — not conflated); mirrored by `scripts/validate/dimension.mjs` for pure-Node re-derivation | **built** (ADR-0039) |
| `extent.py` solver | initial moles → per-reactant extent limits → limiting reagent(s) → species ledger with leftovers; exact Fraction; refuses negative amounts | **built** (ADR-0016) |
| `equilibrium.py` reversible-extent solver | the ICE table = the species ledger with the extent solved from **mass action** (Q(x)=K) not the limiting reagent — `solve_equilibrium` finds the root by **bisection to high precision** (exact Decimal, general beyond the quadratic), the extent model-exact-then-rounded (ADR-0040 pattern), the machine-check the residual Q(committed)=K; an `in_quotient` flag excludes a **pure condensed phase** from Q (grows the bracket when no quotient reactant limits — the Ksp case). Six builders: `build_equilibrium_lesson` (weak-acid pH — dissociation DRY-sourced from acids-bases, K_a from ionization-constants, pH=−log₁₀[H⁺]) + `build_buffer_lesson` (buffer — the same reaction with A⁻ **already present** [A⁻]₀>0, the nonzero-initial-product case; the common-ion effect + **Henderson–Hasselbalch** pH=pK_a+log([A⁻]/[HA]) machine-checked as mass-action-logged; re-solves the acid alone for the common-ion contrast) + `build_weak_base_lesson` (weak base — B + H₂O ⇌ BH⁺ + OH⁻, water the **pure solvent excluded from Q** by the same flag → the solver is reused unchanged; K_b + conjugate acid from ionization-constants, → [OH⁻] → pOH → **pH via the K_w bridge**) + `build_solubility_lesson` (Ksp — the solid excluded, K_sp=4s³ a **cubic**, → molar solubility s + g/L; optionally a **common ion** pre-loaded — a nonzero initial product, the buffer's case on the cubic — re-solving pure water for the suppression contrast) + `build_polyprotic_lesson` (polyprotic — HₙA ionizes in **stages** Kₐ1≫Kₐ2≫Kₐ3 from the `[polyprotic]` data table, the solver run **once per stage** on the previous stage's equilibrium; top-level ice = stage 1, `result.later_stages` the rest; [H⁺] tracks stage 1, the mid-anion ≈ Kₐ2) + `build_titration_lesson` (titration — a weak acid vs a strong base, the ledger **marched by region** as titrant is added: a weak-acid/buffer solve, the conjugate base's weak-base solve at equivalence, excess base after; the top-level ice = the initial point, a `titration` block carries the (volume, pH) curve + landmarks; the player draws a build-time SVG). Dispatched by a `titrant` key → titration, else the acid's proton count (≥2 → polyprotic). Refuses an unbracketed root / a strong acid / a monoprotic acid sent to the polyprotic builder (or vice-versa) / an unknown base or salt / a common ion not shared with the salt / a non-strong titrant | **built** (ADR-0048) |
| `reaction.py` transforms | dissociation (formula → ions via the ion table), complete ionic, net ionic with spectator cancellation + conservation re-check; **reaction classification** (families + free-element redox, ADR-0035) | **built** (ADR-0018/0035) |
| `reactivity.py` datasets | acid/base + gas-forming-intermediate tables (`data/acids-bases.toml`, `data/decomposition.toml`); composition machine-checked on load; injected into the classifier | **built** (ADR-0035) |
| `solubility.py` classifier | sourced ruleset → soluble/insoluble verdict + governing rule id; `verify_phase` build check | **built** (ADR-0017) |
| proofs | atom/charge conservation (in `balance.py` + `reaction.py`) and nonnegative extent (in `extent.py`) done; unit homogeneity of reference formulas (SymPy `dims.py`) with the Atlas | partly built |
| `build.py` orchestration | `build-problems` builds every lesson under `problems/`, dispatched by extension: `*.problem.toml` → `build_problem` (a **reaction** lesson — engine → `derived/<topic>/<slug>.solution.json`; **four reported-product shapes** — precipitate / water / **gas** (`[conditions]` → `result.gas` via PV=nRT, ADR-0041) / **energy** (`[energetics]` → `result.energy` q=ΔH_rxn·ξ via Hess's law, ADR-0043 — no product mass); weighed-`mass_g` → moles; a fully molecular reaction omits the ionic equations), `*.structure.toml` → `build_structure` (a **structure** lesson — a single molecule, ADR-0045, `…structure.json`), `*.comparison.toml` → `build_comparison` (a **comparison** lesson — several molecules vs. a property with the trend machine-verified, ADR-0047, `…comparison.json`), and `*.equilibrium.toml` → `build_equilibrium` (an **equilibrium** lesson — the ICE table = the species ledger with the extent solved from mass action, ADR-0048, `…equilibrium.json`; two subtypes dispatched by `acid` vs `salt`: weak-acid pH / Ksp solubility) | **built** (ADR-0019, +gas ADR-0041, +energy ADR-0043, +structure ADR-0045, +comparison ADR-0047, +equilibrium ADR-0048) |
| `interactive.py` | derives the optional interactive block: slider params + JS closed forms + engine-computed sample points; multiplicities from `dissociate`/`net_ionic`; single-precipitate double-displacement only, else omitted | **built** (ADR-0022) |
| `practice.py` generator | deterministic seeded variants off the reaction → solver-verified answers + misconception distractors; reject-list (near-ties, no leftover, colliding displays); reuses `interactive` multiplicities — or, with no interactive, re-derives from reaction constants: **gas stoichiometry** (`generate_gas_practice`, ADR-0041 — volume via PV=nRT + leftover + limiting; 22.4-L + excess distractors) and **energy ledger** (`generate_energy_practice`, ADR-0043 — heat q=ΔH_rxn·ξ + leftover + limiting; naive-ΔH_rxn + excess distractors; both masses at full precision) | **built** (ADR-0022/0041/0043, three families) |
| `reference.py` Atlas builder | Valence Table projection of `data/` (elements + sourced charges + periodic properties + valence electrons, ADR-0031/0033) + the full named charge-crossover product (verified neutral; own-charge mistakes proven wrong) + the five lens pattern panels + the sourced bonding rule; authored concept entries; `build-reference` entry point | **built** (brief §8/§10/§16) |
| `gym.py` drill generator | authored `gyms/**/*.gym.toml` → deterministic generated problem sets; exact Fractions (non-terminating rejected) for ledger-exact families, model-exact-then-rounded for gas laws + calorimetry (ADR-0040/0042); dimensions re-proven through `units.py`; equations balanced by `balance.py`; **Lewis-structure counting** answered by `structure.compute_ledger` (ADR-0044); named-mistake distractors; **weak-acid pH** answered by `equilibrium.solve_equilibrium`'s mass-action root (model-exact + data-sourced, ADR-0048); regime-2 families disclose a model assumption (calorimetry + weak-acid pH add a data-sourced badge too, ADR-0042/0048); `build-gyms` entry point | **built** (ADR-0024/0027/0028/0029/0034/0036/0040/0042/0044/0048, **twelve** families: conversions · ionic nomenclature · balancing · mass stoichiometry · percent yield · limiting reagent · periodic trends · reaction families · gas laws · calorimetry · Lewis structures · weak-acid pH) |
| `reference.py` reaction families | authored `reference/reactions/*.toml` → engine-balanced + engine-classified example reactions with net-ionic views; the reaction-atlas entry kind (ADR-0035) | **built** (ADR-0035) |
| `reference.py` species entries | authored `reference/species/*.toml` → the species-atlas entry kind (ADR-0038): composition (per-element count + sourced weight + subtotal), signed charge, and molar mass all **derived from the formula** by the parser + `data/` weights (never asserted); names/phase/prose authored + labeled; refuses off-dataset elements or class↔charge mismatches | **built** (ADR-0038) |
| `reference.py` formula entries | authored `reference/formulas/*.toml` → the formula/equation-sheet Atlas kind (ADR-0039): each term's SI dimension computed from the variables' units, **refuses to emit a non-homogeneous relation**; model-exact relations must disclose an assumption; sourced constants (R, N_A) threaded from `data/constants.toml`, never hard-coded. 9 entries incl. **Hess's law** ΔH_rxn=Σν·ΔH_f° (both sides molar energy — kJ/mol; ADR-0043) | **built** (ADR-0039/0043) |
| `structure.py` molecule entries | authored `reference/molecules/*.toml` → the `molecule` Atlas kind (ADR-0044): the **Lewis electron ledger** (valence total = Σ group electrons − charge; electron conservation 2·bonds + 2·lone pairs = V; per-atom octet/duet; formal charge Σ = charge) all **derived + machine-checked**, refuses any structure that fails; **VSEPR geometry** keys `data/vsepr.toml` on the machine-derived domain count; bond ΔEN from sourced electronegativities + `data/bonding.toml`; molecular polarity authored + disclosed (model-assumed, neutral only). The ledger computation is `compute_ledger`, **shared with the `lewis_structures_v1` gym AND the `structure` lesson** (one engine, no hard-coded counts). The electron-structure counterpart of the species ledger. Also `build_structure_lesson` (ADR-0045): a single molecule stepped valence→Lewis→VSEPR→polarity, reusing a `molecule` Atlas entry's authored connectivity. And `classify_imf` (ADR-0046): the dominant **intermolecular force** from the verified structure + polarity (London-dispersion/dipole-dipole/hydrogen-bonding; the H-on-N/O/F test exact, the ranking sourced) → the molecule Atlas `intermolecular` block. And `build_comparison_lesson` (ADR-0047): several molecules vs. a property (boiling point), rows reusing verified Atlas entries, sorted, the dominant-IMF-rank-non-decreasing **trend machine-verified** (refuses a non-monotonic corpus) | **built** (ADR-0044, +structure lesson ADR-0045, +IMFs ADR-0046, +comparison lesson ADR-0047) |
| equilibrium / kinetics / thermo / electrochem / bonding | ICE-as-ledger, rate laws, energy ledger, electron ledger, Lewis/VSEPR; gases + thermo done (gyms + lessons, ADR-0040–0043); **bonding tier complete** (Lewis electron ledger + `molecule` kind + gym + 3 lessons + IMFs, ADR-0044–0047); **equilibrium & acid-base opened** (the reversible-extent solver `equilibrium.py` + the `equilibrium` lesson kind, six subtypes — weak-acid pH + buffer (common-ion + Henderson–Hasselbalch) + weak-base pH (water excluded from Q, pH via the K_w bridge) + Ksp solubility (a pure solid excluded from Q, a cubic; + a common-ion variant) + polyprotic (staged Kₐ, the solver run once per stage) + titration (a weak-acid/strong-base curve, a build-time SVG), ADR-0048; kinetics + electrochem follow) | Phase 2 (open) |

## The solution object (pinned by `schemas/solution.schema.json`, ADR-0020)

**Built.** One schema, draft 2020-12, `additionalProperties:false`, with optional blocks (Q5 → single
schema). It pins a **reaction** lesson; the **structure** (ADR-0045), **comparison** (ADR-0047), and **equilibrium** (ADR-0048)
lessons are each a different object with its own tight schema (`schemas/{structure,comparison,equilibrium}-lesson.schema.json`),
not a bent union — the equilibrium lesson carries an ICE table (initial/change/equilibrium concentrations) + the mass-action
residual + the pH, no completion ledger / reported product. The emitted object (see `derived/precipitation/calcium-carbonate-limiting.solution.json`) carries,
per the brief's §12 sketch: `id/title/slug/topic/scenario`; a
`regimes` block (per-facet regime classification, ADR-0003); `assumptions[]` (each `{claim, kind}` —
model/rule assumptions only, **never referenced inside derivations**); `given[]` (species + quantities);
`equations` (molecular always; complete ionic + net ionic + spectators only when the reaction has ions in
solution — a fully molecular reaction omits them, ADR-0043); `checks` (atom balance, charge balance, unit check,
extent nonnegative — all must be true to emit); `ledger` (the species ledger: per-species phase, charge,
initial mol, stoich coefficient, final mol; limiting species; ξ_max); a dimensional-analysis `chain`;
`result` (the reported net-ionic product — `precipitate` for a solid, or the general `product` + a named
`salt` for a non-precipitating reaction like neutralization, ADR-0037; a **`gas`** block adds the collected
gas's volume via PV=nRT for gas stoichiometry, ADR-0041; or an **`energy`** block carries the heat q=ΔH_rxn·ξ via
Hess's law for the energy ledger, ADR-0043 — no product mass then; plus `limiting_species`, `leftover`,
optional `percent_yield`); `visualizations[]` (kind, static/interactive mode, params, annotations — ADR-0011 governs mode);
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
| validate-solutions | **built** (ADR-0020/0037/0041/0045): **reaction lessons** (`*.solution.json`) — Ajv schema; every `checks.*` true; path matches topic/slug; unique ids; rule-sourced regime needs a cited `solubility_basis.source`; ledger integrity (limiting rows final_mol 0, extent > 0, ν signs); the reported product (`precipitate` ?? `product`) is a product ledger row of the right phase (a `precipitate` must be solid); a `result.gas` (ADR-0041) is the gas-phase reported product + carries a model-exact regime + a disclosed model assumption + the sourced `constants`; a `result.energy` (ADR-0043) carries no product headline + a model-exact regime + a disclosed model assumption + the `formation_enthalpies` source, its Hess rows agreeing with the ledger; provenance sources non-empty. Also **structure lessons** (`*.structure.json`, ADR-0045) against the structure-lesson schema: the Lewis electron ledger re-derived in pure Node (shared `structurecheck.mjs`) + cross-checked byte-for-byte against the Atlas `molecule` with the same `ref_id` (no drift); the four steps in canonical order; a ledger-exact regime + a disclosed model assumption. And **comparison lessons** (`*.comparison.json`, ADR-0047): the rows re-verified sorted ascending by the property, each `imf_rank` consistent with its `dominant`, the rank **non-decreasing** (the trend), and each row's IMF re-derived from the Atlas structure (`classifyIMF`) + boiling point matched (no drift). And **equilibrium lessons** (`*.equilibrium.json`, ADR-0048, six subtypes): the whole reversible-extent spine re-derived in pure Node (shared `equilibriumcheck.mjs`) — the ICE identity c=c₀+ν·x (a pure condensed-phase row — a Ksp solid or the weak-base solvent water — excluded), an **independent bisection re-solve** of the mass-action root (weak-acid quadratic + buffer + weak-base + Ksp cubic + each polyprotic stage, the excluded species out of Q), the residual Q(committed)=K, and the subtype result (weak-acid: pH=−log₁₀[H⁺] + percent ionization; buffer: pK_a + the buffer ratio + **Henderson–Hasselbalch** pH=pK_a+log([A⁻]/[HA]) reproducing −log₁₀[H⁺] + the common-ion contrast from re-solving the acid alone; weak-base: pOH=−log₁₀[OH⁻] + the **K_w bridge** [H⁺]=K_w/[OH⁻], pH+pOH=pK_w; solubility: molar solubility s + s×molar mass = g/L, and for a **common-ion** lesson the pure-water re-solve reproducing the suppression contrast; **polyprotic**: each `later_stages` stage re-solved on the previous stage's outputs, Q=Kₐ per stage, the accumulated [H⁺]/pH, and the species-ladder reconstruction; **titration**: the whole `titration.curve` recomputed independently — every point's region + pH from the titrant/acid inputs + Kₐ + K_w — plus the landmark re-checks (half-equivalence pH = pKₐ, equivalence basic)); all three regimes present + a disclosed model assumption + the K source + the subtype-specific fields |
| validate-reference | **built** (+ADR-0031/0033/0035/0038/0039/0044): each `derived/reference/*.json` schema-valid by `kind` (`valence-table`/`concept`/`reaction-family`/`species`/`formula`/`molecule`); unique ids; `related` edges + `lessons` slugs (+ species `reactions`) resolve; every charge-balance salt's ions come from the table; **every emitted `source` id resolves to a `docs/SOURCES.md` register row**; the ADR-0033 re-derivations (valence electrons from the IUPAC group, salt names by concatenation + subscripts by gcd crossover, mistakes re-proven wrong, bonding boundaries tiling); the ADR-0035 **reaction-family** re-derivations — every example's coefficient vector re-proven a true reduced balance (`balancecheck.mjs`) and its redox flag re-derived, with family-label consistency; the ADR-0038 **species** re-derivations — the formula re-parsed (`formula.mjs`) for composition + charge, the molar mass re-summed from the Valence Table's sourced weights, and the class↔charge agreement enforced; the ADR-0039 **formula** re-derivations — each variable's dimension re-derived from its unit and each term's dimension re-computed from those + the factor powers (`dimension.mjs`), every term required to share one dimension, and a model-exact relation required to disclose an assumption; and the ADR-0044 **molecule** re-derivations — the entire **Lewis electron ledger** re-computed in pure Node (valence total from the table's valence electrons, per-atom octet/duet + formal charge + their conservation, the electron-domain count), plus each bond's ΔEN re-derived from the table's electronegativities and re-classified against the sourced thresholds, and polarity present iff the species is neutral. This molecule re-derivation is factored into the shared `structurecheck.mjs` (`verifyElectronLedger`, ADR-0045), reused by validate-solutions for structure lessons; the ADR-0046 **intermolecular** block is likewise re-derived (`classifyIMF` — the h_bond_donor + forces + dominant re-computed from the structure + polarity, the boiling source register-checked) |
| validate-gyms | **built** (ADR-0024/0027/0028/0029/0034/0036): each `derived/gyms/*.gym.json` Ajv-valid; every answer **re-derived in pure Node** per kind — conversions from raw `derivation.inputs`; nomenclature by name-concatenation + gcd charge-crossover; balancing by re-parsing each formula (`formula.mjs`) and re-proving the coefficients zero every element + charge row; **stoichiometry** by re-verifying the equation balances (`verifyBalance`, now in shared `balancecheck.mjs`) **and** re-deriving the mass/percent/limiting reagent; **periodic trends** by re-comparing the embedded values and cross-checking them against `valence-table.json`; **reaction families** by re-proving the molecular (and, for spectators, the net-ionic) balance and that every spectator is absent from the net equation; **gas laws** (ADR-0040) by re-deriving PV=nRT (or the combined law) numerically from the emitted state + sourced R, within a tolerance above the rounding and below the 3% diagnostic gap; **calorimetry** (ADR-0042) by re-deriving q=mcΔT numerically from the emitted values + the sourced specific heat; **Lewis structures** (ADR-0044) by re-deriving the valence total (Σ group valence electrons − charge, from `valence-table.json`) + the electron-domain count (bonded neighbours + lone pairs on the central atom) from the emitted structure, and re-checking the geometry's correct choice is the sourced shape; **weak-acid pH** (ADR-0048) by re-solving the mass-action root (Q=Kₐ) in pure Node from the emitted Kₐ + concentration (reusing `solveEquilibrium` from the shared `equilibriumcheck.mjs`) and re-checking pH=−log₁₀[H⁺]; plus the **response-mode split** (ADR-0032) and molar-mass consistency across the whole corpus |
| check-ledger | **built** (ADR-0023/0037/0041): re-derives every row's final amount as n = n₀ + ν·ξ from the committed initial/coefficient/extent (independent of Python), checks role/sign consistency, matches the reported result (the product — precipitate, water, or gas — + salt moles, each with mass = moles × M, and the leftovers), **re-derives percent yield** (ADR-0030), **re-derives a gas volume V=nRT/P** numerically from the emitted state + sourced R (0.5% tol) + the °C→K boundary (ADR-0041), and **re-derives the reaction enthalpy + heat** — the Hess sum ΔH_rxn=Σν·ΔH_f° from the emitted breakdown, then q=ΔH_rxn·ξ, and the exo/endo classification from the sign (ADR-0043). A JS formula parser exists (`formula.mjs`, ADR-0028) for a future atom/charge re-check by element counts |
| check-parity | **built** (ADR-0023, ADR-0022, ADR-0032, ADR-0037, ADR-0041): recompiles the exported JS closed forms and re-evaluates them at the embedded engine-computed sample points within tolerance; cross-checks the default slider setting against the committed reported-product mass (`precipitate` ?? `product`); **re-derives every practice answer** in Node and enforces the mode split (numeric → `diagnostics`, no menu; categorical → one-correct `choices`) — for **gas-stoichiometry practice** (ADR-0041) from the `practice.gas` reaction constants (metal molar mass + coefficients, R, T, P) + the per-question args, no interactive block needed (V=nRT/P at 0.5%, leftover exact, limiting categorical), and for **energy-ledger practice** (ADR-0043) from the `practice.energetics` constants (each reactant's molar mass + coefficient + ΔH_rxn) + the two masses (q=ΔH_rxn·ξ at 0.5%, leftover exact, limiting categorical) |
| check-katex | **built** (ADR-0023/0035/0038/0039/0044/0045): every LaTeX string renders through KaTeX with `throwOnError:true` — solution equations/ledger, concept/Valence-Table LaTeX, every reaction-family equation/net-ionic/species/general-form, each species-atlas symbol + inline prose math, each formula-sheet statement + rearrangement + inline math, each molecule's formula symbol + inline summary/polarity/notes math, each **structure lesson**'s molecule symbol + inline scenario/step/misconception/polarity/assumption math (ADR-0045), and each **equilibrium lesson**'s reaction (⇌) + mass-action expression + ICE species symbols + inline scenario/assumption/misconception math (ADR-0048) |
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
