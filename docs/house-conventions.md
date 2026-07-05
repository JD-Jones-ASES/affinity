# House conventions

Will be baked into ChemKernel and the player. **Changing any of these is an ADR-level decision.** Items
marked *(open)* are settled in Phase 0 alongside the architecture open-questions list.

## Units & quantities

- SI base + chemistry-standard derived units: mol, g, L, mL, M (≡ mol/L), atm/kPa, J/kJ, °C/K.
- Every numeric value in specs and derived JSON carries a unit; unitless numbers are only for counts,
  ratios, and dimensionless quantities (pH, K). The units engine rejects everything else.
- Dimensional-analysis chains are first-class content: every computed quantity must be reconstructible
  from its rendered chain (brief §6.6).
- Temperature defaults to 25 °C unless stated; the default is a **model-assumed** badge, not a fact.

## Notation

- Phases always explicit in equations and data: `(s)`, `(l)`, `(g)`, `(aq)`.
- Charge notation in data/specs: caret form `Ca^2+`, `SO4^2-`; rendering converts to superscripts. Never
  encode charge as a bare suffix.
- Reaction arrows: `->` in specs (→ rendered); `<=>` for equilibria (⇌ rendered).
- The extent of reaction is ξ (`xi` in data). Learner-facing pages may defer ξ notation, but ledger data
  always carries it (ADR-0002).
- Subscripts are formula structure, coefficients are amounts — the distinction is load-bearing everywhere
  (misconception register); nothing in the toolchain may ever "balance" by mutating a subscript.

## Chemistry defaults

- Strong electrolytes fully dissociate in the dissociation transformer; the assumption is disclosed on
  every lesson using it (**model-assumed** badge).
- Solubility calls always cite the specific rule applied, from the curated ruleset in `data/` *(open:
  encoding — architecture Q6)*.
- Spectator ions are shown canceling, never vanishing (particle view + complete ionic equation).
- Atomic masses come only from the `data/` element dataset at its stated precision *(open: dataset —
  ADR-0006)*; no hand-typed molar masses anywhere, including prose.

## Significant figures *(open — architecture Q7)*

Computation exact; display rounded. Working default until the ADR: carry exact values in the ledger,
render 3 significant figures for derived results, and echo given-value precision. The practice generator
must never produce items whose correctness hinges on ambiguous rounding.

## Naming

- Lesson/topic ids and slugs: `kebab-case`, pattern `^[a-z0-9-]+$`. **Species ids are exempt** — they use
  the caret charge form (`Ca^2+`, `CO3^2-`); their exact pattern is pinned by the Phase 0 schema.
- Files: `problems/<topic>/<slug>.problem.toml` → `derived/<topic>/<slug>.solution.json`.
- Each `<topic>` path segment is a kebab-case slug mapping to exactly one `docs/regime-map.md` row; record
  the slug in that row's Status cell when its first content lands. Phase 0's is `precipitation`.

## Prose register

Direct instruction (ADR-0011); terse, concrete, no "explore and discover" framing; misconceptions are
demonstrated failing, not scolded. Public text stays provider-agnostic (ADR-0004).
