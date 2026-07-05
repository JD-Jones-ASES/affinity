# Architecture — the factory, in detail

See [`AGENTS.md`](../AGENTS.md) for orientation and [`DECISIONS.md`](../DECISIONS.md) for rationale. This is
the **design contract written before implementation** (bootstrap, 2026-07-05): Phase 0 sessions build to
it, flip its sections from *planned* to *as-built* as they land, and record divergences as ADRs. Once
`schemas/` exists it is the single source of truth for data shapes; this doc narrates them.

## Pipeline (planned)

```
problems/<topic>/<slug>.problem.toml ─┐
reference/**/*.toml                  ─┼─►  ChemKernel (uv, LOCAL)   ─►  derived/<topic>/<slug>.solution.json
data/** (curated datasets)           ─┘                                 derived/reference/*.json
                                                                        derived/assets/**        (COMMITTED)
                                                                             │
                                            scripts/validate/*.mjs ─────────┤  (Ajv + cross-checks + parity
                                                                             │   + KaTeX + scan; fail loud)
                                                                             ▼
                                            Astro + Svelte player (steps the JSON; no runtime chemistry)
```

Entry points (mirroring the sibling's `[project.scripts]` pattern): `build-problems` and
`build-reference`, invoked as `uv --project producer run <entry>`; chained by npm scripts exactly as in
the sibling: `prepare:data` = `produce` + `validate`; `build` = `validate` + `astro build`.

The load-bearing invariant: **ChemKernel refuses to emit** an object that fails any check below
(ADR-0008). CI re-gates the committed output with Node-only checks. A green build certifies both layers.

**As-built so far (2026-07-05).** The full compute + chemistry engine exists and is tested: `data/`
(element, ion, and solubility datasets, ADR-0012/0017); `chemkernel.data` (loader + molar mass +
self-check); `chemkernel.formula` (parser, ADR-0014); `chemkernel.balance` (balancer, ADR-0014);
`chemkernel.units` (Quantity engine, ADR-0015); `chemkernel.extent` (Extent solver → species ledger,
ADR-0016); `chemkernel.reaction` (dissociation + complete/net ionic, ADR-0018); `chemkernel.solubility`
(sourced classifier, ADR-0017). **47 producer tests green** (`uv --project producer run pytest`). The
entire Phase 0 chemistry runs end to end in the library — molecular → complete ionic → net ionic
(spectators Na⁺, Cl⁻), the carbonate solubility rule cited as the precipitate's basis, moles from
volume×molarity, the species ledger, limiting reagent, 0.250 g CaCO₃ — all matching the brief. What
remains is the *emit + verify + present* layer: no `build.py`, solution schema, Node gates, or entry
points yet. Next: the solution schema → `build.py` (authored TOML spec → verified JSON) → Node gates + CI
→ the player.

## ChemKernel module map (brief §6)

| Module | Responsibility | Status |
|---|---|---|
| `formula.py` parser | formula string → element-count vector, charge, phase, display LaTeX (pure; no data) | **built** (ADR-0014) |
| `data.py` data layer | loads `data/` datasets; molar mass; the only path to empirical values (ADR-0006); self-validates on load | **built** (ADR-0012) |
| `balance.py` balancer | element+charge conservation matrix over ℚ → SymPy null space → smallest positive integer coefficients; re-verified; fails on ambiguity | **built** (ADR-0014) |
| `units.py` engine | `Quantity` over an amount/mass/volume `Dim` basis; exact Decimal; units cancel through ×/÷; rejects invalid conversions (numeric dimensional-analysis chain) | **built** (ADR-0015) |
| `extent.py` solver | initial moles → per-reactant extent limits → limiting reagent(s) → species ledger with leftovers; exact Fraction; refuses negative amounts | **built** (ADR-0016) |
| `reaction.py` transforms | dissociation (formula → ions via the ion table), complete ionic, net ionic with spectator cancellation + conservation re-check | **built** (ADR-0018) |
| `solubility.py` classifier | sourced ruleset → soluble/insoluble verdict + governing rule id; `verify_phase` build check | **built** (ADR-0017) |
| proofs | atom/charge conservation (in `balance.py` + `reaction.py`) and nonnegative extent (in `extent.py`) done; unit homogeneity of reference formulas (SymPy `dims.py`) with the Atlas | partly built |
| practice generator | template + constraints + misconception target → solver-verified variants with derivation trees; reject-list enforced | Phase 0 (one family) |
| reaction classifier | precipitation/acid-base/gas-evolution/combustion/redox/… + required conditions | Phase 1 |
| equilibrium / kinetics / thermo / electrochem | ICE-as-ledger, rate laws, energy ledger, electron ledger | Phase 2+ |

## The solution object (planned shape; schema pins it in Phase 0)

Per the brief's §12 sketch, one JSON object per lesson carrying: `id/title/slug/topic/scenario`; a
`regimes` block (per-facet regime classification, ADR-0003); `assumptions[]` (each `{claim, kind}` —
model/rule assumptions only, **never referenced inside derivations**); `given[]` (species + quantities);
`equations` (molecular, complete ionic, net ionic); `checks` (atom balance, charge balance, unit check,
extent nonnegative — all must be true to emit); `ledger` (the species ledger: per-species phase, charge,
initial mol, stoich coefficient, final mol; limiting species; ξ_max); a dimensional-analysis `chain`;
`result`; `visualizations[]` (kind, static/interactive mode, params, annotations — ADR-0011 governs mode);
`misconception` (claim + what refutes it); `practice_family`; `reference_links[]` (must resolve into the
Atlas); badge annotations on every data/rule/model-dependent value; `provenance` (producer version,
dataset versions, author, created).

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

## Verification gates (planned)

| Gate | Checks |
|---|---|
| validate-solutions | Ajv schema; every `checks.*` true; assumptions all kind-tagged; badges present on every rule/model claim; path matches topic/slug; unique ids; reference_links resolve |
| validate-reference | Atlas JSON schema-valid; concept-graph edges resolve; every empirical value carries a source id resolving in `docs/SOURCES.md` |
| check-ledger | recompute atom/charge totals from the committed ledger (initial vs. final, per element and charge) — conservation re-proven in Node, independent of Python |
| check-parity | recompile exported JS closed forms; re-evaluate at embedded sample points within tolerance; practice answers finite and unique |
| check-katex | every LaTeX string renders through KaTeX |
| scan-text | committed text is provider-agnostic (banned-terms list lives in the gate, seeded from the sibling's) |

## Rendering

As in the sibling: all LaTeX rendered to HTML at build time (KaTeX never ships to the browser); islands
hydrate `client:visible`; interactive graphs evaluate exported closed forms/tables only. Nested Svelte
islands require `css: "injected"` (sibling ADR-0019 — known trap).

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
4. **Regime-4 badge** — does mechanistic/interpretive content need a fourth badge, or model-assumed + an
   interpretive marker (ADR-0003 leaves this open)?
5. **Schema granularity** — one `solution.schema.json` with optional blocks (sibling pattern) vs. schema
   per lesson kind.
6. ~~**Solubility-rule encoding**~~ — **RESOLVED (ADR-0017):** `data/solubility.toml`, precedence-ordered
   rules from OpenStax Table 4.1; `classify()` returns the governing rule id for citation.
7. **Sig-fig policy** — computation exact, display rounded; where the policy lives (house-conventions) and
   how the practice generator avoids ambiguous-rounding items.
