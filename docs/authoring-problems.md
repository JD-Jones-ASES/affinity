# Authoring problems — the `*.problem.toml` spec

How to author a lesson for Affinity. You write a **spec** (the human layer); ChemKernel derives and
**verifies** everything else and emits the committed solution JSON (ADR-0005, ADR-0019). You never write a
derived number — if you find yourself computing a molar mass, a coefficient, or a mole amount by hand to put
in the spec, stop: that is the producer's job, and hand-entered values would not be checked.

See [`house-conventions.md`](./house-conventions.md) for units/notation, [`regime-map.md`](./regime-map.md)
for how topics are regime-classified, and [`SOURCES.md`](./SOURCES.md) for the datasets every empirical value
resolves to. The binding shape of the *output* is [`../schemas/solution.schema.json`](../schemas/solution.schema.json);
this guide covers the *input*.

## Where it lives

```
problems/<topic>/<slug>.problem.toml
```

`<topic>` is the topic slug (e.g. `precipitation`) and `<slug>` the lesson slug (kebab-case). The producer
writes `derived/<topic>/<slug>.solution.json`, and the gate refuses a file whose emitted `topic`/`slug`
don't match its path. One lesson per file.

## The one TOML gotcha

**Bare keys must precede any `[table]` or `[[array]]` header**, or TOML absorbs them into the preceding
table (known trap #4, AGENTS.md). Put all the root scalars (`id`, `title`, `reactants`, …) at the top of the
file, then the `[[given]]` / `[[assumptions]]` / `[misconception]` / `[[visualizations]]` sections.

Numbers that must stay exact are written as **strings** (`"25.0"`, `"0.100"`) so no float ever enters the
pipeline (ADR-0013). The producer reads them as `Decimal`.

## Fields

### Required root keys

| Key | Type | Notes |
|---|---|---|
| `id` | string | globally unique, `^[a-z0-9-]+$` (e.g. `precipitation-calcium-carbonate-limiting`) |
| `title` | string | the learner-facing question/title |
| `slug` | string | kebab-case; the URL and filename stem |
| `topic` | string | topic slug; the directory name and grouping key |
| `scenario` | string | the prose setup; may contain inline math `$…$` and `**bold**` |
| `reactants` | array of formula strings | phased, e.g. `["CaCl2(aq)", "Na2CO3(aq)"]` |
| `products` | array of formula strings | phased, e.g. `["CaCO3(s)", "NaCl(aq)"]` |

Formula grammar (v0, ADR-0014): elements `[A-Z][a-z]?`, integer subscripts, nested `(...)` groups with
subscripts, a trailing caret charge (`^2-`, `^+`), and an optional trailing phase `(s|l|g|aq)`. Hydrates and
isotopes are out of scope for v0. The balancer chooses coefficients; **never** pre-balance by writing
coefficients into the spec — list one formula unit of each species.

### `[[given]]` — the measured inputs (at least one)

Each entry is a species you were handed and how much of it:

```toml
[[given]]
species = "CaCl2(aq)"
volume_mL = "25.0"
molarity_M = "0.100"
```

`species` must match a reactant (with phase). Two given shapes (ADR-0041), both converted **to moles** through
the units engine with the dimensional chain recorded: a **solution**, `volume_mL` + `molarity_M` (volume ×
molarity → moles); or a weighed **mass**, `mass_g` (grams ÷ molar mass → moles) — used for a solid reactant like
a metal:

```toml
[[given]]
species = "Zn(s)"
mass_g = "3.269"     # ÷ 65.38 g/mol → 0.0500 mol (must land on a terminating decimal, ADR-0013)
```

Either way the moles must be a terminating decimal or the build refuses (the ledger-exactness guard) — choose a
mass that divides cleanly by the molar mass.

### `[[assumptions]]` — disclosed idealizations (optional)

Author-asserted modeling or rule assumptions — **disclosed, not discharged** (ADR-0003). They render under
the model-assumed badge and are **never** referenced inside a derivation.

```toml
[[assumptions]]
claim = "CaCl2 and Na2CO3 are strong electrolytes and dissociate completely in water."
kind = "model"   # "model" (an idealization) or "rule" (an empirical rule you're leaning on)
```

### `[misconception]` — the canonical wrong move (required)

The register (brief §13): the wrong move, made to visibly fail in the ledger — never merely scolded.

```toml
[misconception]
claim = "The limiting reagent is whichever reactant has the smaller volume."
refuted_by = "moles_and_extent_limits"
```

`refuted_by` is a short token naming the mechanism; the player builds a data-driven refutation from the
ledger — it points out when the smaller-volume reactant is actually in excess, and when the reactant
coefficients differ it shows each reactant's capacity (moles ÷ coefficient) so "fewer moles must be limiting"
visibly fails (the calcium-phosphate lesson: the limiting reagent starts with *more* moles).

### `[[visualizations]]` — declare interactivity (optional)

A control must earn its place (ADR-0011): declare `mode = "interactive"` only when co-motion of quantities
*is* the lesson (the limiting-reagent switch), else `"static"`.

```toml
[[visualizations]]
kind = "extent_bar"          # or "beaker_species_view"
mode = "interactive"
annotate = ["xi_limited_by_Ca", "CO3_left_over", "CaCO3_mass_tracks_xi"]
```

Whether the sliders actually appear depends on the producer emitting a verified `interactive` block (below) —
a declaration alone does not fabricate an instrument.

### `[practice]` — generated practice (optional)

Deterministic, solver-verified variants (brief §6.8). Requires the reaction to also emit an interactive block
(the practice generator reuses its engine-derived multiplicities).

```toml
[practice]
family = "precipitation_limiting_reagent_v1"
seed = 20260705    # fixed seed → byte-identical variants every build (ADR-0008)
count = 6          # the producer refuses to emit if it can't generate this many non-rejected variants
```

Each generated question rotates through limiting-reagent / mass / leftover asks; every wrong choice is a
named misconception, and a reject-list drops ambiguous variants (near-ties, no leftover, choices that
collide at display precision). Changing `seed` regenerates the whole set; commit the new `derived/` with it.

### `[yield]` — percent yield (optional, ADR-0029/0030)

Turn a precipitation lesson into a percent-yield lesson. The **theoretical** yield is the precipitate mass
ChemKernel already computes (the ledger at maximum extent); you author only the **actual** (measured) mass.

```toml
[yield]
actual_mass_g = "0.276"   # the recovered mass; must be > 0 and ≤ the theoretical yield (else the build refuses)
```

ChemKernel emits a `result.percent_yield` block (theoretical, actual, and `percent = actual ÷ theoretical ×
100`, reported to 0.1%) and the player renders a yield card. `check-ledger` re-derives the percent and
confirms the yield is physical. The full precipitation machinery — equations, ledger, interactives, practice —
comes for free; the yield card is the only addition.

### Non-precipitation lessons (acid-base neutralization, ADR-0037)

You author these **exactly like a precipitation lesson** — same reactants/products/given/practice — but with
no solid product. ChemKernel reports the **net-ionic product** (water, for a neutralization) as `result.product`
instead of `result.precipitate`, names the dissolved `result.salt`, and still emits the limiting-reagent
interactive + generated practice (the switch is H⁺ vs OH⁻). Two authoring notes: set `regimes = ["ledger",
"solution_behavior"]` (a neutralization has **no** solubility claim, so omit `solubility` or the build will
demand a `solubility_basis` it can't produce), and give both solutions as `[[given]]` volumetric inputs. See
[`problems/neutralization/hydrochloric-sodium-hydroxide.problem.toml`](../problems/neutralization/hydrochloric-sodium-hydroxide.problem.toml).
Percent yield stays precipitation-only (it needs a solid).

### Gas-stoichiometry lessons (the ledger drives a gas volume, ADR-0041)

For a reaction that releases a gas (a metal + acid → H₂, single replacement), add a **`[conditions]`** table and
ChemKernel reports the collected gas as `result.product` **plus a `result.gas` block** carrying its **volume via
PV=nRT** at those conditions:

```toml
[conditions]              # must follow every root key (TOML trap #4 — a bare key below it is absorbed)
gas_species = "H2"        # which product is the collected gas
pressure_atm = "1.00"
temperature_C = "25.00"   # or temperature_K = "298.15" (°C converts at the boundary, K = °C + 273.15)
```

Author notes: set `regimes = ["ledger", "gas_behavior"]` (the moles are ledger-exact, the volume is
**model-exact** — an ideal gas — so it carries the model-assumed badge and needs a disclosed `[[assumptions]]` of
`kind = "model"`); give the metal as a weighed `mass_g` given and the acid as a volumetric one; there is **no**
solubility claim (omit `solubility`). The gas volume is model-exact-then-rounded (3 sig figs) — the gas constant
R travels from `data/constants.toml` (its source lands in `provenance.sources.constants`). A great misconception:
`22.4 L/mol` is the molar volume only at STP; the player refutes it with the actual RT/P. A `[practice]` block
yields gas-specific drills (free-entry volume via PV=nRT + leftover, categorical limiting reagent) even though the
single-replacement shape has no slider interactive. See
[`problems/gas-stoichiometry/zinc-hydrochloric-hydrogen.problem.toml`](../problems/gas-stoichiometry/zinc-hydrochloric-hydrogen.problem.toml).

### Other optional keys

`tags` (array), `reference_links` (array of Atlas ids — they become links as the Atlas is built),
`author` (defaults `"Affinity"`), `created` (date string), and `regimes` (array of facet keys —
`ledger`, `solubility`, `solution_behavior`, `gas_behavior`; defaults to the first three, ADR-0003 — omit
`solubility` for a non-precipitation lesson, use `gas_behavior` for the ideal-gas volume).

## What ChemKernel derives (do not author these)

Everything else in the solution JSON is computed and verified: the **balanced** molecular / complete-ionic /
net-ionic equations with spectators; **moles** and the dimensional chain from each given; the **species
ledger** (n = n₀ + ν·ξ, the limiting reagent, leftovers); the reported **product** and its mass (precipitate,
water, or a gas — and a gas's **volume via PV=nRT**, ADR-0041); the **solubility basis** (cited to the ruleset,
precipitation only); molar masses; display LaTeX; provenance; and — for a supported single-precipitate
double-displacement — the **`interactive` block** of parity-verified closed forms + engine-computed sample points
that drive the sliders (ADR-0022). If the reaction is a different shape, the interactive block is omitted (by
design) — but a gas-stoichiometry lesson with a `[practice]` block still earns **generated practice** (free-entry
volume via PV=nRT + leftover, categorical limiting reagent), re-derived by check-parity from the reaction
constants with no interactive (ADR-0041).

## What makes the build refuse to emit

The producer raises and writes nothing (ADR-0008) on: an unparseable formula; an unbalanceable or ambiguous
equation; non-conserved atoms or charge in the net ionic; a **negative** amount/extent; a phase that
contradicts the sourced solubility ruleset; a non-terminating "exact" amount; or a missing required field.
Fix the spec, not the output.

## Build & verify

```bash
npm run produce        # problems/**/*.problem.toml -> derived/**/*.solution.json  (local; needs uv)
npm run validate       # 5 pure-Node gates over committed derived/ (no Python)
npm run build          # validate -> astro build (the static site)
npm run dev            # local preview
```

Commit the regenerated `derived/` alongside the spec — it is the Python↔Node contract CI re-verifies
(ADR-0008). The gates: `validate-solutions` (schema + honesty), `check-ledger` (re-derives n = n₀ + ν·ξ),
`check-parity` (re-proves the sliders' JS against the engine), `check-katex`, `scan-text`
(provider-agnostic — no course/exam/board names in committed text, ADR-0004).

## Worked example

The Phase-0 slice — [`problems/precipitation/calcium-carbonate-limiting.problem.toml`](../problems/precipitation/calcium-carbonate-limiting.problem.toml)
— is the reference authored spec. Read it beside its emitted
[`derived/precipitation/calcium-carbonate-limiting.solution.json`](../derived/precipitation/calcium-carbonate-limiting.solution.json)
to see exactly which fields are authored and which the engine derives.
