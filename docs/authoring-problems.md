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

`species` must match a reactant (with phase). Today the producer converts **volume + molarity → moles**
through the units engine and records the dimensional chain, so a given needs `volume_mL` and `molarity_M`.
(The schema also reserves `mass_g`; a mass-based given is not wired in `build.py` yet — add it there when a
lesson needs mass/molar-mass as the entry point.)

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

### Other optional keys

`tags` (array), `reference_links` (array of Atlas ids — they become links as the Atlas is built),
`author` (defaults `"Affinity"`), `created` (date string), and `regimes` (array of facet keys —
`ledger`, `solubility`, `solution_behavior`; defaults to all three, ADR-0003).

## What ChemKernel derives (do not author these)

Everything else in the solution JSON is computed and verified: the **balanced** molecular / complete-ionic /
net-ionic equations with spectators; **moles** and the dimensional chain from each given; the **species
ledger** (n = n₀ + ν·ξ, the limiting reagent, leftovers); the **precipitate** and its mass; the **solubility
basis** (cited to the ruleset); molar masses; display LaTeX; provenance; and — for a supported
single-precipitate double-displacement — the **`interactive` block** of parity-verified closed forms +
engine-computed sample points that drive the sliders (ADR-0022). If the reaction is a different shape, the
lesson renders statically (the block is omitted, by design).

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
