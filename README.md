# Affinity

**A beginning-chemistry portal where the verification system is the product.**

**Status:** **Phase 2 open** (Phase 1 complete + owner-reviewed) — twenty-one machine-verified lessons (precipitation,
percent yield, acid-base neutralization, **gas stoichiometry** — a weighed metal + acid whose hydrogen volume falls
out of the ledger via PV=nRT — the **energy ledger** — burning methane, whose heat q = ΔH_rxn·ξ falls out of
the ledger via Hess's law over sourced formation enthalpies — two **single-molecule structure lessons** (why water is
bent → polar, why CO₂ is linear → polar bonds, nonpolar molecule; each stepped valence electrons → Lewis structure →
VSEPR shape → polarity, the electron ledger machine-checked), and a **multi-molecule comparison** whose IMF-strength
boiling-point trend is itself machine-checked (CH₄ ≪ NH₃ ≪ H₂O)), and seven **equilibrium** lessons (the pH of
acetic acid; the pH of ammonia — a weak base, the exact mirror of the acetic-acid lesson across neutral, water excluded from
Q and pH reached through the Kw bridge; a **buffer** — acetic acid + acetate, where the common-ion effect holds the pH at pKₐ
and Henderson–Hasselbalch falls out as the mass-action law in log form; and the Ksp molar solubility of calcium fluoride —
the ICE table is the species ledger with the extent solved from **mass action** Q=K, not driven to a limiting reagent; for
Ksp the pure solid is excluded from Q, so it is a cubic, and the machine-check is the residual — with a **common-ion variant**
where dissolving calcium fluoride into a fluoride solution suppresses its solubility 59 400-fold; and **polyprotic** phosphoric
acid, whose three protons come off in stages Kₐ1 ≫ Kₐ2 ≫ Kₐ3 — the same solver run once per stage, so the first ionization
sets the pH and the amphiprotic middle anion sits at ≈ Kₐ2; and a **titration curve** — acetic acid titrated by NaOH, the
ledger marched drop by drop into a build-time SVG that reads pKₐ off the half-equivalence plateau and lands basic at
equivalence), **two precipitation-prediction lessons** (a different kind — the **reaction quotient** Q, compared to Ksp,
decides whether a solid forms: calcium fluoride crashes out of a millimolar mix, while dilute magnesium hydroxide stays clear
despite being “insoluble” — a snapshot, not a solve), and **three kinetics lessons** (the **ledger in time**, one lesson kind over
the three reaction **orders** — the order sets the clock: hydrogen peroxide decays first-order with a **constant** half-life
($[\mathrm{A}]=[\mathrm{A}]_0 e^{-kt}$, $t_{1/2}=\ln 2/k=6$ h), butadiene dimerizes second-order with a half-life that **grows** as
it thins out ($1/[\mathrm{A}]=1/[\mathrm{A}]_0+kt$, 1.45→2.89→5.79 h), and ammonia on hot tungsten decomposes zero-order with a
half-life that **shrinks**, running out **completely** at a finite time ($[\mathrm{A}]=[\mathrm{A}]_0-kt$, 1.07→0.534→0.267 h) —
each a decay curve, the contrast machine-checked), twelve procedural gyms (dimensional analysis, nomenclature,
balancing, the full stoichiometry suite, periodic trends, reaction families, gas laws, calorimetry, **Lewis
structures** — valence electrons, electron domains, molecular shape, counted exactly — and **weak-acid pH** — the ICE table's
mass-action root, solved not approximated), the Chemical Atlas — five reference surfaces: a typed concept graph + **7 reaction
families** with engine-classified example reactions + **14 species entries** with engine-derived molar masses +
the **Valence Table flagship** (five lenses, trend graphs, a 156-salt formula builder, a ΔEN bonding mode over 23
sourced elements) + the **formula & equation sheet** (the ideal gas law, calorimetry, mole–mass, and the
**equilibrium constants** Kₐ/K_b/K_w/K_sp written as dimensionless activity relations, each with its
**dimensional homogeneity machine-checked**) + now **molecule structure entries** (Lewis **electron ledgers** —
valence total, octet, and formal charge machine-checked — with VSEPR shape, polarity, and the **dominant intermolecular
force** derived from the structure: why CO₂ is nonpolar but H₂O is not, and why water boils at 100 °C while methane boils
at −161 °C) — and generated practice. Phase 2 has landed its gas + thermochemistry tiers, its **bonding & structure**
tier (engine, gym, three lessons, and intermolecular forces), and has **opened equilibrium & acid-base** (the
reversible-extent solver + the `equilibrium` lesson kind with six subtypes — weak-acid pH, buffer, weak-base pH, Ksp
solubility incl. a common-ion variant, polyprotic staged ionization, and titration curves — plus a `prediction` lesson kind
(Q vs Ksp: does a precipitate form?) and the K/Kw/Ksp formula sheet), and has now **opened kinetics** (the ledger in time —
decay of orders 0/1/2 on one order-general engine, the `kinetics` lesson kind); see [`ROADMAP.md`](./ROADMAP.md). See [`AGENTS.md`](./AGENTS.md) to work the repo.

## The idea in three lines

Chemistry is species accounting plus electron structure under energy constraints. One object — the
**species ledger over reaction extent** — underlies balancing, stoichiometry, limiting reagents, ICE
tables, kinetics, thermochemistry, and electrochemistry; every lesson is a view of it. Nothing ships
unless a machine checked it, a registered source backs it, or a disclosed model assumption labels it.

## What's inside

- **Lessons** that reconcile six views of one scenario: setup, macroscopic observation, symbol register,
  species ledger, particle/electronic view, and evidence view — with a misconception register that makes
  the canonical wrong move visibly fail.
- **The Gym** — procedural drills generated and machine-verified at build time (dimensional analysis, ionic
  nomenclature, equation balancing, the full stoichiometry suite — mass→mass, percent yield, limiting
  reagent — and periodic trends drilled from the table's own sourced data), every wrong option a named
  mistake.
- **The Chemical Atlas** — species, formulas, reactions, and a typed concept graph; breadth to the
  lessons' depth.
- **The Valence Table** — a periodic table that is a database visualization, pattern explainer, and
  problem generator, not decoration.
- **Verified generative practice** — every item solver-checked with a full derivation tree before it can
  ship.

## How it's verified

A build-time Python producer (**ChemKernel**) refuses to emit any object that fails formula parsing, atom
balance, charge balance, unit homogeneity, or a nonnegativity check on reaction extent. CI re-validates
the committed output in pure Node — schema gates, honesty cross-checks, numeric parity between the
browser's closed forms and the producer's high-precision values — and a failure breaks the deploy. Three
honesty badges (**machine-checked** / **data-rule-sourced** / **model-assumed**) mark every claim; sources
are registered in [`docs/SOURCES.md`](./docs/SOURCES.md).

## How it was made

AI-authored under an owner-designed verification system. There is no human-review gate on the calculations
by design — the verification *system* is the safeguard: a failed conservation proof, a non-homogeneous
unit, a schema mismatch, or a closed form that doesn't reproduce the producer's numbers all **break the
build** rather than ship.

## Stack

Astro (static) + Svelte islands · KaTeX rendered at build time · Python + SymPy producer via uv (build
time only — no server, no client-side Python) · JSON Schema + Ajv gates · GitHub Pages.

## License

Code [MIT](./LICENSE) · content [CC BY-SA 4.0](./LICENSE-content.md).
