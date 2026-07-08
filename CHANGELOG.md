# Changelog

Notable changes, newest first. Architecture rationale lives in [`DECISIONS.md`](./DECISIONS.md); the phase
plan in [`ROADMAP.md`](./ROADMAP.md).

## Phase 2 — 2026-07-08 — equilibrium: Ksp solubility — the reversible-extent solver proven on the cubic (ADR-0048, 2nd increment)

The reversible-extent solver **generalizes** — same machine, a structurally different equilibrium. A **Ksp
(solubility)** lesson dissolves a sparingly soluble salt; the dissolving species is a **pure solid** (activity 1),
so it is excluded from the mass-action quotient — and for a 1:2 salt that makes $K_{sp} = 4s^3$, a **cubic**, which
bisection solves but the quadratic formula can't (the reason the solver was built general, ADR-0048).

- **Lesson `equilibrium/calcium-fluoride-solubility`** — CaF₂(s) ⇌ Ca²⁺ + 2 F⁻, $K_{sp} = 3.45\times10^{-11}$ →
  molar solubility $s = 2.05\times10^{-4}$ M (0.016 g/L). The misconception is forgetting the coefficient
  ($s=\sqrt{K_{sp}}$), refuted from the cubic: [F⁻] = 2s enters $K_{sp}$ **twice** (a factor and an exponent), so
  $s = (K_{sp}/4)^{1/3}$, ~35× larger than $\sqrt{K_{sp}}$. Closes the Phase-0 loop — the quantitative version of the
  qualitative precipitation rules (the `precipitation` concept backlinks).
- **Engine:** `solve_equilibrium` gains an `in_quotient` flag — a pure solid is excluded from Q and, being in
  excess, does not bound the forward extent (the bracket is grown until Q > K). A new `build_solubility_lesson`; the
  `equilibrium` lesson kind now has two **subtypes** (`weak-acid` / `solubility`), one schema (a `subtype`
  discriminator), dispatched in `build_equilibrium` by `acid` vs `salt`.
- **Data:** `data/solubility-products.toml` (Ksp, OpenStax App J: CaF₂, Mg(OH)₂) — the ion counts derived by charge
  crossover + the salt composition machine-checked on load; the `solubility-product` concept.
- **Gate:** `equilibriumcheck.mjs` handles the solid row (no concentration, excluded from Q) + re-derives the molar
  solubility + g/L; `validate-solutions` enforces the subtype-specific fields. The static `EquilibriumLesson.astro`
  renders both subtypes (the solid row shows "— pure solid · excluded from Ksp"; the change column "+2s").
- **Verification:** **340 producer tests** (+7); 7 gates green (validate-solutions = 6 + 2 structure + 1 comparison +
  **2 equilibrium**; validate-reference 64; check-katex 555); **32 pages** (+1); `derived/` byte-stable (the acetic
  lesson gained `subtype`, + 2 new files). **4-way tamper-tested** — a coherent wrong solubility → the independent
  re-solve; a corrupted fluoride coefficient → ICE identity; a bad g/L → solubility-consistent; the solid forced
  into Q → ICE identity.

## Phase 2 — 2026-07-08 — open equilibrium & acid-base: the reversible-extent solver + weak-acid pH (ADR-0048)

Opened the **equilibrium & acid-base** tier on its stress scenario, **the pH of a weak acid** — the thesis made literal:
*the ICE table is the species ledger with the extent solved from mass action, not driven to a limiting reagent.*

- **Engine `chemkernel.equilibrium.solve_equilibrium`** — the **reversible-extent solver**. Builds the ICE ledger
  ($c_i = c_{i,0} + \nu_i\,x$) in concentrations and finds the extent $x$ where the reaction quotient $Q(x)=K$, by
  **bisection to high precision** (exact `Decimal`; general beyond the quadratic — ready for Ksp, buffers, polyprotic).
  The root is model-exact-then-rounded (ADR-0040 pattern); the machine-check is the **residual** ($Q$ at the committed
  concentrations reproduces $K$) plus the gate's independent re-solve.
- **New `equilibrium` lesson kind** — the fourth lesson shape (`schemas/equilibrium-lesson.schema.json`,
  `build_equilibrium_lesson`, `*.equilibrium.json`, dispatched by extension). Lesson **`equilibrium/acetic-acid-ph`**:
  0.100 M acetic acid, $K_a=1.8\times10^{-5}$ → $x=[\mathrm{H^+}]=1.33\times10^{-3}$ M, **pH 2.88**, 1.33% ionized. The
  misconception is treating the weak acid as strong ($[\mathrm{H^+}]=0.100$, pH 1.00), refuted from the ledger (98.67%
  stays intact). Triple-badged: ICE identity machine-checked (regime-1), $K_a$ data-sourced (regime-3), the equilibrium
  position/pH model-assumed (regime-2).
- **Data:** `data/ionization-constants.toml` ($K_a$ for weak acids, OpenStax *Chemistry 2e* Appendix H) + the `data.py`
  loader/accessor. The acid's dissociation (HA ⇌ H⁺ + A⁻) is **DRY-sourced from `data/acids-bases.toml`**. Two new
  concepts (`chemical-equilibrium`, `ph`); formula-sheet $K$/pH entries deferred (they need the activity treatment).
- **Gate:** `scripts/validate/equilibriumcheck.mjs` (shared) re-derives the whole spine in pure Node — the ICE identity,
  an **independent bisection re-solve** of the root, the residual, the pH, the percent ionization — wired into
  `validate-solutions`; `check-katex`/`validate-reference` learn `.equilibrium.json`. A fully static
  `EquilibriumLesson.astro` player (the ICE table, the mass-action check, the pH headline).
- **Verification:** **333 producer tests** (+18); 7 gates green (validate-solutions = 6 + 2 structure + 1 comparison +
  **1 equilibrium**; validate-reference = 63; check-katex = 530); **31 pages** (+1); `derived/` byte-stable (only the 3
  new files). **5-way tamper-tested** — corrupt extent → ICE identity; a *coherent* wrong extent → the independent
  re-solve; corrupt $K_a$ → re-solve; corrupt pH → log; corrupt the quotient → mass action. **Four lesson shapes** now.

## Phase 2 — 2026-07-08 — IMF comparison lesson: a machine-verified boiling-point trend (ADR-0047)

The bonding tier's capstone — and a third lesson shape. Where a reaction lesson is a species ledger and a structure
lesson is one molecule's electron ledger, a **comparison lesson** lines up several molecules against a property and
teaches the trend — with the trend itself machine-checked.

- **Lesson `bonding/boiling-points-and-imfs`** — *same size, different boiling points*: CH₄ (−161.5 °C, dispersion) ≪
  NH₃ (−33.3 °C, hydrogen bonding) ≪ H₂O (100 °C, hydrogen bonding), three hydrides of nearly equal mass (16/17/18) so
  **size is controlled and the intermolecular force is the variable**. The misconception is the intramolecular-vs-
  intermolecular confusion ("water boils high because its O–H bonds are strong / boiling breaks them"), refuted from the
  table (boiling overcomes the forces *between* molecules, not the covalent bonds *within* — steam is still H₂O).
- **New kind** (`schemas/comparison-lesson.schema.json`, `structure.build_comparison_lesson`, `*.comparison.json`): rows
  reference `molecule` Atlas entries and **reuse their verified IMF + boiling point** (no drift). The builder sorts by
  boiling point and **proves the dominant-IMF rank is non-decreasing** — "IMF strength predicts the ordering" — refusing
  to emit if the corpus breaks it. A fully static `ComparisonLesson.astro` player; all lesson/reference pages now glob
  the three lesson suffixes.
- **Gate:** the trend re-derives in pure Node — rows sorted, rank consistent, monotonic, and each row's IMF re-derived
  from the Atlas structure (`classifyIMF`) + boiling point matched. **5-way tamper-tested** (unsort / bad imf_rank /
  non-monotonic / boiling drift / dominant drift — each caught).
- **Verification:** **315 producer tests** (+4); 7 gates green (validate-solutions = 6 + 2 structure + **1 comparison**;
  check-katex = 502); **30 pages** (+1); `derived/` byte-stable (only 4 authored backlinks). Three lesson shapes now.

## Phase 2 — 2026-07-08 — intermolecular forces: a structure-derived dominant-IMF classifier (ADR-0046)

The bonding tier's last core topic — anchored to the machine-verified structure so it stays on-thesis despite being the
tier's first predominantly empirical subject.

- **Engine** (`structure.classify_imf`): the dominant intermolecular force of a neutral molecule, from its verified
  structure + polarity — every molecule has **London dispersion**, a **polar** one adds **dipole–dipole**, an **H bonded
  to N/O/F** adds **hydrogen bonding**; dominant = the strongest present. The H-bond-donor test is an exact graph fact;
  the ordering is the sourced rule (regime-3, with the dispersion-grows-with-size caveat disclosed).
- **Atlas:** an optional **`intermolecular` block** on the `molecule` kind (neutral molecules only — ions' interactions
  are ionic) with `dominant`/`forces`/`h_bond_donor` (machine-derived) + a **sourced normal boiling point** as evidence
  (`data/boiling-points.toml`). A new **`intermolecular-forces` concept** (rule-sourced) carries the teaching + the
  boiling-point trend. Every neutral molecule page now shows its dominant IMF + boiling point under the right badges.
- **Subtlety, right:** CH₂O is polar (dipole–dipole) but its H's are on **carbon** → *not* an H-bond donor; CH₄/CO₂ are
  dispersion-only; H₂O/NH₃ hydrogen-bond. Evidence: CH₄ (−161.5 °C) ≪ NH₃ (−33.3 °C) ≪ H₂O (100 °C); CO₂ sublimes (−78.5 °C).
- **Gate:** the IMF classification re-derives in pure Node (shared `structurecheck.classifyIMF`); the boiling **source** is
  register-checked (its value is empirical, not re-derivable). **6-way tamper-tested** (dominant / h_bond_donor / forces /
  a block on the ammonium ion / an unregistered source / a missing block on a neutral molecule — each caught).
- **Verification:** **311 producer tests** (+5); 7 gates green (**validate-reference = 61**, +1 concept; check-katex = 499);
  29 pages; `derived/` byte-stable — the 5 neutral molecule JSONs gain the block, NH₄⁺ (an ion) byte-identical.

## Phase 2 — 2026-07-08 — CO₂ structure lesson: polar bonds, nonpolar molecule (ADR-0045, 2nd increment)

The second `structure` lesson — the marquee VSEPR contrast, proving the new machinery generalises to a different shape.

- **Lesson `bonding/carbon-dioxide-molecular-shape`** — *why CO₂ is linear*: 16 e⁻ → two C=O **double bonds** (the octet
  fix, machine-checked) → 2 electron domains, **no lone pairs on carbon** → **linear** (sourced) → each C=O polar (ΔEN
  0.89) but the two dipoles cancel → **nonpolar** (model-assumed). The same "central atom + two outer atoms" skeleton as
  water, opposite result — the lone pairs (present in water, absent here) decide. The misconception ("two polar bonds → a
  polar molecule") gets a new data-driven refutation branch (`symmetric_geometry_cancels_dipoles`).
- **Reuse:** authored entirely inside the ADR-0045 contract — no new schema/builder/gate; the CO₂ molecule Atlas entry's
  connectivity + the shared `compute_ledger`. `test_structure.py` generalised to build **every** shipped structure lesson.
- **Verification:** 306 producer tests green; 7 gates green (validate-solutions = 6 + **2** structure lessons;
  check-katex = **499**); **29 pages** (+1); `derived/` byte-stable, no existing derived changed (bar the CO₂ + 2 concept
  backlinks). In-browser: the linear/nonpolar payoff + the "polar bonds cancel" refutation render; both structure lessons
  list under Bonding (8 lessons), and CO₂ ↔ water cross-link as the contrast pair.

## Phase 2 — 2026-07-08 — bonding & structure lesson: the electron ledger over a single molecule (ADR-0045)

The bonding tier's deep vertical slice — the electron ledger's presentation shape generalised past a reaction to one
molecule. A new **`structure` lesson kind** (its own tight schema + builder), NOT a bent reaction schema.

- **Lesson `bonding/water-molecular-shape`** — *why water is bent*: stepped **valence** (8 e⁻, machine-checked) →
  **Lewis** (2 O–H bonds + 2 lone pairs, octet + formal-charge sum machine-checked) → **VSEPR** (4 domains → tetrahedral
  → **bent**, sourced) → **polarity** (bent + polar bonds → **polar**, model-assumed). The misconception ("water is
  linear") is refuted from the verified geometry (the 2 lone pairs are electron domains → bent), with CO₂ as the contrast.
- **New kind** (`schemas/structure-lesson.schema.json`, `structure.build_structure_lesson`): the lesson names a `molecule`
  Atlas entry and **reuses its authored connectivity**, re-deriving the electron ledger with the SAME `compute_ledger`
  engine the Atlas + gym use (no hard-coded counts). `build.py` dispatches `*.structure.toml` by extension. Payoff is
  polarity, so a neutral molecule only.
- **Gates:** the molecule electron-ledger re-derivation factored out of `validate-reference` into a shared
  `scripts/validate/structurecheck.mjs` (`verifyElectronLedger`) — the molecule JSON is byte-identical after the refactor.
  `validate-solutions` walks `*.structure.json`, re-derives the ledger in pure Node, and cross-checks it byte-for-byte
  against the Atlas molecule (no drift). check-katex + the reference-page backlinks + the lesson-slug walk learn the new
  suffix. **7-way tamper-tested** (valence total / formal charge / step order / geometry drift / missing model assumption /
  bad ref_id / flipped check — each caught by a distinct branch).
- **Player:** fully static `src/components/StructureLesson.astro` (no island — nothing to hydrate); the `/lessons/<slug>/`
  route + index glob both lesson kinds. The three honesty badges, the four stepped panels, the SHOWN checks, the
  data-driven misconception refutation, the disclosed assumptions.
- **Verification:** **306 producer tests** (+8); **validate-solutions = 6 + 1 structure lesson**; check-katex = **498**
  (+1); 7 gates green; **28 pages** (+1); `derived/` byte-stable, no existing derived changed (bar 3 authored `lessons`
  backlinks). In-browser: the four steps, the bent/polar payoff cards, and the lone-pair refutation all render; the
  molecule Atlas + both concepts backlink to the lesson.

## Phase 2 — 2026-07-08 — Lewis-structures gym: generated electron-counting drills (ADR-0044, 2nd increment)

The electron ledger earns its drill surface — the practice half of the bonding tier opener.

- **Refactor:** `structure.compute_ledger` extracted from `build_molecule_entry` (molecule derived JSON byte-identical),
  so the gym's answers come from the SAME verified engine the Atlas uses.
- **`lewis_structures_v1` gym** over an 8-molecule skeleton corpus (the 6 Atlas molecules + CCl₄ + PCl₃). Three kinds:
  **valence total** + **electron domains** are free-entry numeric with named diagnostics (counting *all* electrons not
  just valence; forgetting a lone pair is a domain; a double bond as two domains); **molecular geometry** is categorical,
  with the **electron-domain geometry** (tetrahedral for bent/pyramidal) as the star distractor. Regime-1 machine-checked
  counting — no model badge; the sourced badge names the IUPAC group positions + the VSEPR table.
- **Gate:** `validate-gyms` re-derives valence (Σ group electrons − charge, from `valence-table.json`) + the domain count
  in pure Node. **6-way tamper-tested** (corrupt a valence/domains answer / a geometry shape / a central lone-pair count /
  a numeric-question menu / a too-close diagnostic — each caught).
- **Player:** `/gym/lewis-structures/` (the generic free-entry island + a lewis chain caption + the source badge);
  concept chips resolve to `lewis-structure` + `vsepr`.
- **Verification:** **298 producer tests** (+5); **validate-gyms = 11 gyms / 110 problems** (+1/+10); 7 gates green;
  **27 pages** (+1); `derived/` byte-stable, no existing derived changed. In-browser: entering the "all electrons"
  wrong answer (66 for PCl₃) → "the answer is 26 electrons" + the named diagnostic + the "Cl 3×7 + P 1×5 = 26" chain.

## Phase 2 — 2026-07-08 — bonding & structure tier opened: the Lewis electron-ledger engine + molecule Atlas kind (ADR-0044)

The next Phase-2 tier opens with its machine-checkable instrument. The Lewis structure is an **electron ledger** — the
electron-structure counterpart of the species ledger — and its accounting is exact integer arithmetic, so it wears the
machine-checked badge.

- **Engine** (`chemkernel/structure.py`): `build_molecule_entry` verifies an authored structure (atoms + lone pairs +
  bonds) and refuses to emit unless the **valence total** (Σ group electrons − charge), **electron conservation**
  (2·bonds + 2·lone pairs = V), every **octet/duet**, and every **formal charge** (Σ = molecular charge) check out.
  The **VSEPR geometry** keys a new sourced table (`data/vsepr.toml`, OpenStax §7.6) on the machine-derived domain
  count; **bond ΔEN** re-uses the sourced electronegativities + `data/bonding.toml`; **molecular polarity** is authored
  + disclosed (model-assumed), stated only for neutral molecules.
- **Atlas kind `molecule`** (`schemas/molecule.schema.json`; ids kind-prefixed `molecule-*` so a molecule and its
  same-named species coexist + cross-link). Six molecules: **H₂O** (bent, polar) vs **CO₂** (linear — polar bonds,
  nonpolar molecule), **NH₃**/**CH₄**, **CH₂O** (trigonal planar, polar), **NH₄⁺** (the +1 formal charge on N). Two
  concepts: `lewis-structure` (ledger-exact anchor), `vsepr` (rule-sourced). The Atlas now has a 5th reference surface.
- **Gate:** `validate-reference` re-derives the **whole electron ledger in pure Node** (valence total, per-atom
  octet/formal charge, conservation, domain count) + re-derives every bond's ΔEN from the table's electronegativities
  and re-classifies it; `check-katex` gains the molecule branch. **7-way tamper-tested** (corrupt a formal charge /
  valence total / bond ΔEN / geometry domains / electron_check / bond class / polarity on an ion — each caught).
- **Player:** `/reference/molecules/` — the electron-ledger table, VSEPR shape, per-bond ΔEN, polarity, each under its
  own badge — plus an Atlas-index card ("why CO₂ is nonpolar but H₂O is not").
- **Verification:** **293 producer tests** (+15: `test_structure.py` + a vsepr-load test); **validate-reference = 60**
  (+8); check-katex = **497**; 7 gates green; **26 pages** (+1); `derived/` byte-stable across two rebuilds, no existing
  derived changed. In-browser: CO₂ shows all four facet badges + "polar bonds, nonpolar molecule"; NH₄⁺ shows the charge
  subtraction and the +1 formal charge on N with no polarity (it's an ion); no console errors.
- **Deferred within the tier:** octet exceptions (BeH₂/BF₃/PCl₅/SF₆); resonance (CO₃²⁻/NO₃⁻); a `lewis_structures_v1`
  gym (generated counting drills); a bonding & structure lesson; IMFs.

## Phase 2 — 2026-07-08 — Hess's-law formula-sheet entry (ADR-0043, 3rd increment)

The reference backbone the energy-ledger lesson links to — the 9th formula/equation-sheet entry.

- **`formula-enthalpy-of-reaction`** (Hess's law): ΔH_rxn = Σν·ΔH_f°(products) − Σν·ΔH_f°(reactants), **model-exact**
  (enthalpy is a state function — disclosed), with **dimensional homogeneity machine-checked**: both sides reduce to
  **molar energy** (kJ/mol). `dimension.py` already carried `kJ/mol`; only the "molar energy" display name was added.
  The reverse-reaction sign flip ships as a rearrangement; links to the lesson + the `reaction-enthalpy` concept.
- **Verification:** 278 producer tests (+1); **validate-reference = 52** (+1); **check-katex = 487** (+6); 7 gates green;
  25 pages; `derived/` byte-stable (only the new formula file + the lesson's new reference link). 4-way tamper-tested
  (corrupt a term dimension / force non-homogeneity / empty the model assumption / dangling lesson — each caught). The
  static build renders the entry (title, the "both reduce to molar energy" check line, the state-function assumption).

## Phase 2 — 2026-07-08 — energy-ledger lesson: reaction enthalpy attached to extent (ADR-0043)

The thermochemistry vertical slice — **the extent ledger drives an energy**: q = ΔH_rxn·ξ, with ΔH_rxn assembled by
**Hess's law** from sourced formation enthalpies. The energy counterpart of the gas-stoichiometry lesson (ADR-0041).

- **The 6th lesson** (`thermochemistry/methane-combustion-enthalpy`): CH₄ + 2 O₂ → CO₂ + 2 H₂O. The ledger fixes ξ
  (CH₄ limits at 0.05 mol, O₂ left over); the heat is **q = ΔH_rxn·ξ = −890.57 × 0.05 = −44.5 kJ** (exothermic).
- **Hess's law over a sourced ΔH_f° table** (`data/formation-enthalpies.toml`, OpenStax Appendix G, keyed by formula
  **and** phase — H₂O(l) −285.83 ≠ H₂O(g) −241.82): ΔH_rxn = Σν·ΔH_f°(products) − Σν·ΔH_f°(reactants), **exact Decimal
  arithmetic** over the sourced values; an element in its standard state contributes 0 (the reference level). The
  producer refuses to emit if any ΔH_f° is missing.
- **The `result.energy` block — a fourth reported-product shape** (`build.py`): the headline is the **heat**, not a
  product mass. q = ΔH_rxn·ξ is computed **through the units engine** (`units.py` gains `kJ/mol` — kJ·mol⁻¹ × mol → kJ,
  dimension certified). Honesty is **triple-layered**: ξ ledger-exact (machine-checked) · ΔH_f° data-sourced · the
  relations (Hess's law, q = ΔH_rxn·ξ to completion) model-assumed. The **first lesson wearing three badges at once**.
  q is **exact** here (all inputs terminate), 3-sig-fig display — distinct from the gas volume's model-exact-then-
  rounded (ADR-0040), each treatment reflecting the real arithmetic.
- **The first fully MOLECULAR lesson:** a gas-phase combustion dissociates nothing, so the complete/net-ionic views
  are **omitted** (there is no ionic equation) rather than echoing the molecular one (`equations` complete/net-ionic
  now optional). Aqueous lessons keep all three, byte-identical.
- **The `reaction-enthalpy` concept** (Hess's law + ΔH_f° + q = ΔH_rxn·ξ) → **20 → 21 concepts**; the lesson's 14
  reference chips all resolve.
- **Generated practice** (same session, ADR-0043 second increment): a 6-variant set — free-entry **heat** (q = ΔH_rxn·ξ)
  + **leftover**, categorical **limiting reagent** — with **no interactive block**. The reaction constants (each
  reactant's molar mass + coefficient + ΔH_rxn) travel in a `practice.energetics` block so **check-parity re-derives
  every answer in Node** from the two masses (the ADR-0041 gas-practice template; `heat` joins the numeric kinds). The
  heat diagnostics: the **naive ΔH_rxn-as-total** (forgot ξ) + **sizing ξ from the excess reactant**. Both masses emitted
  at full precision so the re-derivation stays exact. 6-way tamper-tested.
- **Verification:** **277 producer tests** (+6); **validate-solutions = 6**, **validate-reference = 51**, **check-ledger =
  6 ledgers / 24 rows + 1 gas volume + 1 reaction enthalpy re-derived from Hess's law**, **check-parity = 320 + 36
  practice answers**, check-katex = 481; 7 gates green; `astro build` = **25 pages** (+1). `derived/` byte-stable (only the
  new lesson + concept added; no existing solution changed). The energy result gates are **7-way tamper-tested** (corrupt
  q / a Hess contribution / ΔH_rxn / flip classification / drop the model regime / drop the source / add a spurious
  product) and the practice gate **6-way** — each caught. In-browser: the heat card (−44.5 kJ, exothermic), the Hess table
  (→ −890.57 kJ/mol), the ξ×ΔH flow, the extent-scaling misconception refuted, the "no ions in solution" note, and the
  Practice tab (the naive-ΔH_rxn entry named) render; the aqueous lessons keep their 3 equations. No console errors.
- **Deferred:** a Hess formula-sheet entry; endothermic / multi-step Hess-cycle lessons; the gas lesson's slider interactive.

## Phase 2 — 2026-07-08 — calorimetry gym; the units engine gains an energy dimension (ADR-0042)

The thermochemistry opener — the energy ledger's first rung, **q = m·c·ΔT**, generated endlessly.

- **The `calorimetry_v1` gym** (ADR-0042): solve q = m·c·ΔT for any of the four variables, over a sourced
  specific-heat table (water 4.184 down to gold 0.129 J/(g·°C)). Gym family #10.
- **The units engine gains an `energy` dimension** (`units.py` `Dim` → 6 fields — ADR-0040's deferred extension):
  `J`, `kJ`, `J/(g*K)` registered, and every answer is computed **through** the engine (g × J·g⁻¹·K⁻¹ × K → J,
  dimensions certified). Energy stays **independent of pressure·volume** — a chemistry-bookkeeping basis, so a
  gas-law product (L·atm) and a calorimetry heat (J) never silently equate. ΔT rides the temperature basis as a
  **difference** (1 °C = 1 K), distinct from the gas law's absolute kelvin.
- **The first object with BOTH honesty badges:** the specific heat is a measured, **data-sourced** datum
  (`data/specific-heats.toml`, OpenStax Table 5.1 — the data/rule-sourced badge), *and* the relation is exact only
  inside the **calorimetry model** (no heat loss, constant c, no phase change — the model-assumed badge). Both render
  on the gym.
- **Model-exact-then-rounded** (a specific heat carries only so many figures): 3-sig-fig answers, the gate
  re-derives q = m·c·ΔT within 0.5%. Solving **for c** is the identify-the-substance experiment (the answer is the
  tabulated value, machine-confirmed). Named diagnostics: **using another substance's c** (treating everything like
  water) + dropping a factor.
- **Verification:** 271 producer tests (+7); **validate-gyms = 10 gyms / 100 problems**; 7 gates green; `astro build`
  = **24 pages** (+1: `/gym/calorimetry/`); `derived/` byte-stable (only the new gym added). The `verifyCalorimetry`
  gate branch is **4-way tamper-tested**. In-browser: the three badges + the model disclosure render; a "used water's
  c" entry is named; the chips resolve to the calorimetry formula-sheet entry. No console errors.
- **Deferred:** initial/final-temperature framing (ΔT = T_f − T_i) + cooling (negative q) as distinct drills; the
  **energy-ledger lesson** (ΔH_rxn·ξ, Hess) — the next thermochemistry increment.

## Phase 2 — 2026-07-08 — gas-stoichiometry lesson: the ledger drives a gas volume (ADR-0041)

The Phase-2 vertical slice — the extent ledger drives a **gas volume**. A weighed metal + an acid react; the
ledger fixes the moles of hydrogen, and PV=nRT turns them into the volume you would collect.

- **The 5th lesson** (`gas-stoichiometry/zinc-hydrochloric-hydrogen`, Zn + 2 HCl → ZnCl₂ + H₂, ADR-0041): three
  equations, the species ledger (Zn limits, HCl left over), three dimensional chains (**g→mol**, mL→mol, and the
  new **mol→L via PV=nRT**), a gas-volume card, the dissolved salt, and the misconception refuted with the
  verified numbers. First lesson with a **weighed-mass given** and first with a **gas product**.
- **`build.py` generalised** past the two-solution double-displacement shape (ADR-0041), a third reported-product
  shape alongside precipitate/water: (1) `_moles_and_chain` gains a **`mass_g` branch** (grams ÷ molar mass →
  moles, dimension certified through the units engine; still must terminate — 3.269 g Zn = 0.0500 mol exactly);
  (2) a **`result.gas` block** — the collected gas's volume via `(n·R·T/P).to("L")` through the units engine from
  the ledger's exact moles + the **sourced** R, model-exact-then-rounded (3 sig figs) under the model-assumed
  badge, with `molar_volume` (RT/P) emitted to name the **22.4-L-at-STP misconception**; (3) **free elements skip
  the solubility phase-check** (a metal has no solubility verdict).
- **Honesty layered, not mixed:** the moles/limiting are **ledger-exact** (machine-checked); the **volume is
  model-exact** (ideal gas, disclosed). **check-ledger re-derives V=nRT/P** numerically (0.5% tol) + the °C→K
  boundary; **validate-solutions** ties `result.gas` to a model-exact regime + a disclosed model assumption + the
  sourced constant. Both branches **6-way tamper-tested** (incl. baking in the wrong 22.4 molar volume — caught).
- **Concept chips now route by entry kind** (concept / reaction-family / species / formula), so the lesson's 16
  Atlas links all resolve — and prior lessons' reaction/formula links light up too.
- **Generated practice** (ADR-0041): the gas lesson earns a **6-variant practice set** — free-entry **volume**
  (PV=nRT) + **leftover** (mmol), categorical **limiting reagent** — even though the single-replacement shape has
  no cation/anion interactive. The reaction constants (metal molar mass + coefficients, R, T, P) travel in a
  `practice.gas` block, and **check-parity re-derives every answer in pure Node** from the emitted args (metal
  mass, acid volume/molarity) — no interactive block needed. The volume distractors are the **22.4-L-at-STP** slip
  and sizing from the excess reactant; the limiting reagent genuinely switches (Zn or HCl). Reuses the generic
  free-entry `PracticeQuestion` island (no new frontend). The gas-practice branch is **6-way tamper-tested**.
- **Verification:** 264 producer tests (+2); 7 Node gates green — validate-solutions = 5, check-ledger = 5 ledgers
  / 20 rows + **1 gas volume re-derived from PV=nRT**, **check-parity = 30 practice answers** (+6 gas), check-katex
  = 468; `astro build` = **23 pages** (+1); `derived/` byte-stable (only the new lesson added — no existing
  solution changed). In-browser: the volume card (1.22 L, model-assumed), the mol×RT/P=volume flow, the g→mol +
  mol→L chains, the STP-trap refutation, and the **Practice tab** (a wrong 22.4-L entry is named) render; no
  console errors, dark + light clean.
- **Deferred (a follow-on increment):** the gas-stoichiometry **slider interactive** (mass/volume/molarity sliders
  → the gas volume — ExtentBar is cation/anion-locked, so it needs its own component); collecting the gas **over
  water** (vapor-pressure correction); `kPa`/`torr` units.

## Phase 2 — 2026-07-08 — gas-laws gym; the units engine gains pressure/temperature (ADR-0040)

The practice instrument for gases — the second Phase-2 increment, on top of the formula sheet.

- **The `gas_laws_v1` gym** (ADR-0040): PV=nRT and the combined gas law, solve for any variable — the first
  **model-exact** gym. Two Phase-1 firsts. (1) The **units engine gains pressure + temperature dimensions**
  (`units.py` `Dim` grows to 5 fields — ADR-0015's deferred extension), and every answer is computed **through**
  it (`(n·R·T/P).to("L")`) so the dimensions are certified exactly as the conversion gym certifies L × mol/L = mol.
  (2) The first **model-exact-then-rounded** numeric answer — R is non-terminating, so the answer is reported at
  3 significant figures (display) / 4 (checked), and the Node gate re-derives PV=nRT numerically within 0.5%
  (above the rounding, below the 3% diagnostic gap). Not a weakening of ledger exactness (ADR-0013) — a gas-law
  result is a rounded physical quantity by nature.
- **Realistic, honest problems.** Each state is generated **consistent** (n, P, T chosen; V computed) so no absurd
  temperatures/volumes ship; temperature is absolute (K), and a °C given is converted (K = °C + 273.15) as a shown
  step — **forgetting it is the canonical named diagnostic**, alongside the wrong-R slip (8.314 SI instead of
  0.08206 L·atm). Free entry, never a gameable menu (ADR-0032).
- **The model is disclosed.** The gym carries an `assumptions` block (the ideal-gas model) under the
  **model-assumed (amber) badge** — the three-badge honesty model applied to a gym for the first time; the sourced
  R travels in provenance. Added only for model-bearing families, so the Phase-1 gyms stay byte-identical.
- **Gate + player + tests.** A `verifyGasLaw` branch re-derives every answer in pure Node (**validate-gyms = 9
  gyms / 90 problems**), **5-way tamper-tested** (corrupt answer / state value / R / a gameable menu / a too-close
  diagnostic — each caught). The drill island renders it with a gas-aware chain caption and zero new interaction
  plumbing; the gym page shows the model badge + disclosure and resolves the formula-sheet concept chips. **262
  producer tests** (+7); `astro build` = **22 pages** (+1: `/gym/gas-laws/`); `derived/` byte-stable. In-browser:
  correct entry accepted, the wrong-R entry named, no console errors.

## Phase 2 — 2026-07-08 — OPENED: formula/equation-sheet Atlas kind (ADR-0039)

The owner opened **Phase 2** (the model-bearing tier). Following the phase protocol (open with the reusable
instrument, then fill depth-first), it opens on **gases + thermochemistry** by landing the fourth brief-§10
Atlas kind — the **formula/equation sheet** — with a machine-checkable honesty model for regime-2 relations.

- **The `formula` Atlas kind** (`schemas/formula.schema.json`, `reference.build_formula_entry`, ADR-0039): a
  reference relation whose **dimensional homogeneity is machine-checked** — each side (each term) is a monomial
  over the variables, and the producer refuses to emit unless every term reduces to one SI dimension vector. We
  do not claim the relation is *true*: a **model-exact** entry (PV=nRT) carries the model-assumed badge and
  **must disclose an assumption**; a **ledger-exact** entry (n=m/M) carries the machine-checked badge.
  Dimensional consistency is what we prove; the model is what we disclose.
- **A native SI-vector dimension engine** (`chemkernel.dimension`) — not SymPy `dims.py` (a chemistry-motivated
  divergence, ADR-0001): first-course relations are monomials, so homogeneity is integer-vector arithmetic, and
  the payoff is **pure-Node re-derivation** — the producer emits each variable's dimension vector + each term's
  factor powers, and `validate-reference.mjs` (via a shared `scripts/validate/dimension.mjs`) re-computes every
  term's dimension and re-checks equality (the ADR-0028 emit-and-re-tally pattern). Kept separate from the
  Decimal `units.py` engine, exactly as ADR-0015 required.
- **8 relations** — 5 ledger-exact backfilling Phase-0/1 (mole–mass, molarity, dilution, Avogadro's-number,
  percent yield) + 3 model-exact opening the gas/thermo tier (ideal gas law, combined gas law, calorimetry).
  Two sourced constants **threaded from `data/constants.toml`** (N_A; the **gas constant R**, newly registered
  under `bipm-si-2019`) — never hard-coded. Player: `reference/formulas.astro` (teaching-order groups, the
  dimensional-check line, variable/unit tables, disclosed assumptions, rearrangements) + an Atlas-index card.
- **Gates + tests.** `validate-reference` = **50 objects** (+8 formulas), re-deriving homogeneity; `check-katex`
  = **461** (+42 formula LaTeX). **255 producer tests** (+12: `test_dimension.py` + formula-builder tests). The
  formula gate is **7-way tamper-tested** — term/variable/total-dimension corruption, forced non-homogeneity,
  empty model assumption, dangling edge, unregistered source — each caught then restored. `derived/` byte-stable
  (+8 files); `astro build` = **21 pages** (+1: `/reference/formulas/`). In-browser verified (light + dark, no
  console errors). The Atlas now carries **all four brief-§10 kinds**.

## Phase 1 — 2026-07-08 — session-map #8: Atlas breadth audit (ADR-0038) — Phase-1 DoD met

The last Phase-1 work — the species Atlas kind, the final empty regime-map row filled, and a cross-link
integrity fix — clearing the Phase-1 definition-of-done. Then **stop for owner review** (the gate before
Phase 2).

- **The species Atlas kind** (`schemas/species.schema.json`, `build_species_entry`, ADR-0038): **14 curated
  species** — 10 compounds, 2 elemental molecules (O₂/H₂), 2 polyatomic ions — each with its **composition,
  charge, and molar mass DERIVED by the engine** from the authored phase-less formula (re-parsed, weights
  summed from `data/`), never asserted; names, phase, and prose authored + labeled. The producer refuses an
  off-dataset element, a class↔charge mismatch, or a phase in the formula. Every entry cross-links to the
  lessons, reaction families, and concepts it appears in.
- **The gate re-derives it in pure Node.** `validate-reference` re-parses each species formula (`formula.mjs`
  — composition + charge must reproduce), re-sums the molar mass from the **Valence Table's** sourced atomic
  weights (an unsourced element fails), and re-checks the class/charge agreement + edge resolution;
  `check-katex` renders the species symbol + inline prose math. 8-way tamper-tested (corrupt molar mass /
  count / weight, flipped ion charge, class↔charge mismatch, dangling edges — each caught).
- **The last regime-map row filled.** An `atomic-mass` concept (average atomic mass = the abundance-weighted
  mean of isotope masses, $\bar{A} = \sum_i f_i A_i$) covers *atoms, isotopes, average atomic mass* — the only
  Phase-0/1 row still at "—". No new source (the CIAAW standard weight *is* that average).
- **Cross-link integrity fix (TOML trap #4).** All 7 reaction families had shipped with **empty
  `related`/`lessons`** — the bare keys were authored after the `[[examples]]` headers and TOML absorbed them
  into the last example table. Moved ahead of the first array-of-tables header (and a topic/slug lesson value
  corrected to the bare slug); `build_reaction_family` now **rejects an example/misconception carrying an
  unexpected key**, so an absorbed key fails loud.
- **Player.** A `/reference/species/` page (species grouped by class, each with its composition table, molar
  mass, machine-checked + data-sourced badges, and cross-links) + a Species card on the Atlas index;
  `renderSpecies` in `view.js`; `.claude/launch.json` gained `autoPort` so a session can preview without
  colliding with another chat's dev server.
- **Phase-1 definition of done met:** all four brief-§10 Atlas kinds present (bar the Phase-2 formula sheet),
  every Phase-0/1 regime-map row covered, 4 lessons, 7 gates green, deployed. **Verification:** 243 producer
  tests (+7); validate-reference = 42 objects (1 table + 20 concepts + 7 reactions + 14 species); check-katex
  = 419; all 7 gates green; `derived/` byte-stable (54 files); astro build = 20 pages.

## Phase 1 — 2026-07-08 — item 6: reaction families (ADR-0035/0036/0037) — Phase 1 items 1–6 complete

The last Phase-1 item, in four increments — a reaction classifier and its three surfaces (Atlas, gym, lesson).

- **The reaction classifier** (`chemkernel.reaction.classify_reaction`, ADR-0035). A pure function of the
  balanced, phased formulas + the injected sourced datasets: combustion, synthesis, decomposition, single/
  double replacement, and the double-replacement sub-types precipitation / acid-base / gas-evolution —
  most-specific-first, each citing data (the solubility ruleset, the acid/base table, the decomposition
  table), never hard-coded. **Redox by the free-element signature**: an element free on one side and combined
  on the other changed oxidation state — the exact first-course redox families, with no oxidation-number
  assignment (a Phase-2 topic). Two new sourced datasets (`data/acids-bases.toml`, `data/decomposition.toml`,
  openstax-chemistry-2e), composition machine-checked on load by `chemkernel.reactivity`.
- **The reaction-family Atlas kind** (`schemas/reaction-family.schema.json`, ADR-0035): **7 families / 21
  example reactions**, each **balanced and classified by the engine** — the producer refuses to file an
  example under a family it does not classify as. Each example emits the balanced equation, the classifier's
  evidence + redox flag, and the **net-ionic particle view** where spectators cancel (combustion/synthesis/
  decomposition omit it rather than fake one). Player: `reference/reactions.astro` (jump-nav, net-ionic views,
  redox badges) + an Atlas-index card. `verifyBalance` extracted to a shared `balancecheck.mjs`;
  `validate-reference` re-proves every example's balance + redox in pure Node and enforces family-label
  consistency (tamper-tested); `check-katex` extended to reaction-family LaTeX.
- **The `reaction_families_v1` gym** (gym family #8, ADR-0036): classify-the-family (a balanced equation → its
  family) and name-the-spectators (a reaction with a net-ionic form → its spectator ions), both categorical
  (ADR-0032). Reactions engine-balanced + engine-classified at generation; family distractors are definitional
  (what the wrong family requires, never a false claim about this reaction), spectator distractors are
  over-inclusion + the reacting ions themselves. `validate-gyms` re-proves the molecular (and, for spectators,
  the net) balance and that every spectator is absent from the net equation — tamper-tested.
- **The acid-base neutralization lesson** (`neutralization/hydrochloric-sodium-hydroxide`, ADR-0037) — the
  **first non-precipitation lesson**. HCl + NaOH → NaCl + water: the net-ionic product is water, the salt is
  all spectators. The emitters generalized past single-precipitate double-displacement — the reported product
  is the net-ionic product of *any* phase (`result.product`/`result.salt` beside the precipitation-only
  `result.precipitate`; precipitation lessons stay **byte-identical**); `interactive.py` dropped its
  must-be-solid guard so the limiting-reagent slider (H⁺ vs OH⁻) works unchanged; `practice.py` parametrized.
  No solubility claim (ledger-exact + model-exact). Player: a water/salt result card, the Beaker tab gated to
  solid products, the ExtentBar generalized; the three solution gates read `precipitate ?? product`.
- **236 producer tests** (+69) + **7 gates green** (validate-solutions = 4, validate-reference = 27 objects /
  1 table + 19 concepts + 7 families, validate-gyms = 8 gyms / 80 problems, check-katex = 381, check-parity =
  320 closed-form points + 24 practice answers) + **astro build (19 pages)**, `derived/` byte-stable (39
  files). `chempy` independently balances the whole reaction corpus (ADR-0026). In-browser: all 7 families
  render with correct redox badges + net-ionic views; the gym scores a classify (Zn + 2 HCl → single
  replacement) with the redox reason; the neutralization slider flips OH⁻ → H⁺ as NaOH rises (0.027 → 0.036 g
  water), no Beaker tab, only machine-checked + model-assumed badges. No console errors.

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
