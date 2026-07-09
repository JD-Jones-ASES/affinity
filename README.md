# Affinity

**A beginning-chemistry portal where the verification system is the product.**

Affinity is a first-year college and advanced high-school chemistry course in which *nothing ships unless a
machine checked it, a registered source backs it, or a disclosed model assumption labels it.* A build-time
Python producer (**ChemKernel**) turns authored problem specs into machine-verified solution data; a static
Astro/Svelte player renders it and computes no chemistry of its own. The claim on the tin — no claim ships
unverified, unsourced, or unlabeled — is enforced by seven gates that break the build, not by good intentions.

**Live:** <https://jd-jones-ases.github.io/affinity/>

## v1.0.0 snapshot

> **22 lessons** (7 shapes) · **13 gyms / 130 drills** · a **118-element Valence Table** with **182 machine-verified
> salts** · **85 Chemical Atlas objects** · **7 Node verification gates** — all green at **47 pages** · **432 producer
> tests**.

Numbers drift, so they live in one place (`AGENTS.md ## Current state`) and are re-counted from the committed
tree, never hand-narrated here.

## The idea in three lines

Chemistry is species accounting plus electron structure under energy constraints. One object — the **species
ledger over reaction extent** — underlies balancing, stoichiometry, limiting reagents, ICE tables, kinetics,
thermochemistry, and electrochemistry; every lesson is a different view of it. A learner can start with
recipes and coefficients; the ledger is always underneath.

## What's inside

- **Lessons** that reconcile several views of one scenario — setup, macroscopic observation, symbol register,
  species (or electron) ledger, particle view, and evidence — each with a **misconception register** that makes
  the canonical wrong move visibly fail in the ledger rather than merely scolding it. Seven lesson shapes:
  reaction, structure (Lewis), comparison (a trend), equilibrium (ICE), prediction (Q vs Kₛₚ), kinetics (the
  ledger in time), and electrochemistry (the electron ledger).
- **The Gym** — procedural drills generated and machine-verified at build time (dimensional analysis,
  nomenclature, balancing, the full stoichiometry suite, periodic trends, reaction families, gas laws,
  calorimetry, Lewis structures, weak-acid pH, kinetics), every wrong option a *named* mistake, every numeric
  answer free-entry so a menu can't be gamed.
- **The Valence Table** — a real 18-column periodic table (f-block detached) over all 118 elements: a database
  visualization, pattern explainer, and problem generator with lens / trend / formula-builder / bonding modes
  and 182 verified salt names.
- **The Chemical Atlas** — species, formulas, reactions, molecule structures, and a typed concept graph;
  breadth to the lessons' depth.

## How it's verified

ChemKernel **refuses to emit** any object that fails formula parsing, atom balance, charge balance, unit
homogeneity, or a nonnegativity check on reaction extent. CI then re-validates the committed output in **pure
Node** — schema gates, honesty cross-checks, an independent re-derivation of every model-bearing lesson shape,
numeric parity between the browser's closed forms and the producer's high-precision values, a KaTeX render
gate, and a provider-agnostic scan gate. A failure breaks the deploy. Three honesty badges — **machine-checked**
/ **data-rule-sourced** / **model-assumed** — mark every claim; every source resolves in
[`docs/SOURCES.md`](./docs/SOURCES.md) and is credited publicly on the [Sources & credits](https://jd-jones-ases.github.io/affinity/credits/)
page. The whole verified surface is laid out on the [Verification](https://jd-jones-ases.github.io/affinity/verification/)
page.

## v1.0.0 contract — what is proven, and what is not

The product is the verification system, so its boundary is stated plainly (ADR-0053).

**Machine-checked on every commit, in pure Node over the committed output:** atom and charge conservation
(balance re-derived, not asserted) · nonnegative reaction extent · unit / dimensional homogeneity of the
reference relations · strict schema validity · every source id resolves · numeric parity of the browser's
closed forms with the producer · the per-shape re-derivations (the ICE re-solve + residual, the decay curve +
half-life progression, the electron ledger + E°cell + ΔG, the Lewis ledger, the IMF trend) · and the
118-element periodic dataset cross-checked against an independent oracle.

**Not proven — and not claimed to be:** the **empirical table values themselves** beyond their sourcing (a Kₐ, a
boiling point, an E° is *sourced and labeled*, not derived) · **pedagogical choices** (which misconception to
target, what order to teach) · and **model assumptions** (ideal gas, complete dissociation, activities ≈
molarities, standard conditions) — these are **disclosed under the model-assumed badge, not discharged**.

**One disclosed implementation exception:** KaTeX is rendered at build time for lesson and Atlas prose, but the
interactive practice island currently ships the runtime KaTeX bundle (v1.1 moves it to build time and adds a
bundle-scan gate).

## How it was made

**AI-authored under an owner-designed verification system.** There is no human-review gate on the calculations
by design — the verification *system* is the safeguard: a failed conservation proof, a non-homogeneous unit, a
schema mismatch, or a closed form that doesn't reproduce the producer's numbers all **break the build** rather
than ship.

## Stack

Astro (static) + Svelte islands · KaTeX rendered at build time for lesson/Atlas prose (the practice island
currently ships runtime KaTeX — v1.1) · Python + SymPy producer via **uv** (build time only — no server, no
client-side Python) · JSON Schema + Ajv gates · GitHub Pages.

## Explore the repo

- [`ROADMAP.md`](./ROADMAP.md) — phase plan + the v1.1 backlog.
- [`CHANGELOG.md`](./CHANGELOG.md) — what shipped, when.
- [`DECISIONS.md`](./DECISIONS.md) — the architecture decision records (cited as ADR-NNNN throughout).
- [`AGENTS.md`](./AGENTS.md) — orientation + working protocol for anyone (human or agent) opening the repo.
- [`docs/architecture.md`](./docs/architecture.md) — the emit → verify → present pipeline in detail.

## License

Code [MIT](./LICENSE) · content [CC BY-SA 4.0](./LICENSE-content.md). Empirical data is sourced per
[`docs/SOURCES.md`](./docs/SOURCES.md); facts are not copyrightable, and each dataset's own terms are recorded
there.
