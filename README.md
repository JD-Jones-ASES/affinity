# Affinity

**A beginning-chemistry portal where the verification system is the product.**

**Status:** **Phase 2 open** (Phase 1 complete + owner-reviewed) — six machine-verified lessons (precipitation,
percent yield, acid-base neutralization, **gas stoichiometry** — a weighed metal + acid whose hydrogen volume falls
out of the ledger via PV=nRT — and now the **energy ledger** — burning methane, whose heat q = ΔH_rxn·ξ falls out of
the ledger via Hess's law over sourced formation enthalpies), ten procedural gyms (dimensional analysis, nomenclature,
balancing, the full stoichiometry suite, periodic trends, reaction families, **gas laws** — PV=nRT and the
combined gas law — and now **calorimetry** — q=mcΔT), the Chemical Atlas — five reference surfaces: a typed concept graph + **7 reaction
families** with engine-classified example reactions + **14 species entries** with engine-derived molar masses +
the **Valence Table flagship** (five lenses, trend graphs, a 156-salt formula builder, a ΔEN bonding mode over 23
sourced elements) + the **formula & equation sheet** (the ideal gas law, calorimetry, mole–mass and more, each
with its **dimensional homogeneity machine-checked**) + now **molecule structure entries** (Lewis **electron ledgers** —
valence total, octet, and formal charge machine-checked — with VSEPR shape and polarity: why CO₂ is nonpolar but H₂O is
not) — and generated practice. Phase 2 has landed its gas + thermochemistry tiers and opened **bonding & structure**; see
[`ROADMAP.md`](./ROADMAP.md). See [`AGENTS.md`](./AGENTS.md) to work the repo.

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
