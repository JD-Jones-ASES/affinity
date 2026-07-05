# Changelog

Notable changes, newest first. Architecture rationale lives in [`DECISIONS.md`](./DECISIONS.md); the phase
plan in [`ROADMAP.md`](./ROADMAP.md).

## Phase 0 (in progress) — 2026-07-05 — ChemKernel engine: datasets, parser, balancer, units, ledger, ionic transforms, solubility

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
- **47 producer tests green** total (+10 for reaction + solubility).
- **Resolved architecture open-questions** Q1 (dataset+format), Q2 (numeric representation), Q3 (parser
  grammar), Q6 (solubility encoding) via ADR-0012/0013/0014/0017; units engine, ledger, and ionic-transform
  shapes fixed by ADR-0015/0016/0018.

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
