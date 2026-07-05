# Authoring gyms — the `*.gym.toml` spec

How to add a **procedural gym** — a generated, machine-verified problem set for drilling a Phase-1 skill
(brief §17, ADR-0024). You author a tiny spec; ChemKernel *generates* the problems, computes every answer
exactly, re-checks each conversion's dimensions through the units engine, and emits the committed gym JSON.
You never write a problem or an answer — the seed makes the set deterministic and reviewable.

See [`authoring-problems.md`](./authoring-problems.md) for the sibling lesson pipeline, and
[`house-conventions.md`](./house-conventions.md) for units/notation. The binding *output* shape is
[`../schemas/gym.schema.json`](../schemas/gym.schema.json); this guide covers the *input*.

## Where it lives

```
gyms/<topic>/<slug>.gym.toml   ->   derived/gyms/<slug>.gym.json
```

`<topic>` is the topic slug (e.g. `dimensional-analysis`); `<slug>` is the gym slug (kebab-case) and the
output filename stem. The gate refuses a file whose emitted `slug` doesn't match its path. One gym per file.

## The spec

All keys are root scalars (no `[table]` sections), so the TOML trap #4 doesn't bite here.

```toml
id = "dimensional-analysis-solution-conversions"   # globally unique, ^[a-z0-9-]+$
title = "Solution conversions: volume, molarity, moles, and mass"
slug = "solution-conversions"                        # kebab-case; URL + filename stem
topic = "dimensional-analysis"                        # topic slug (directory + grouping)
family = "solution_conversions_v1"                    # which generator to run (see below)
seed = 4242043                                        # fixed seed → byte-identical problems every build
count = 10                                             # the producer refuses to emit fewer than this
blurb = "…"                                           # one-paragraph description (shown on the card + page)
skills = ["mL → L (÷ 1000)", "volume × molarity → moles", …]   # what this gym drills (chips)
reference_links = ["dimensional-analysis", "molarity", "molar-mass"]   # Atlas concept ids -> chips
```

## Families

A `family` selects the generator in `chemkernel.gym.generate_gym`. Today:

- **`solution_conversions_v1`** — volume · molarity · moles · mass conversions in five kinds
  (`volume_molarity_to_moles`, `moles_molarity_to_volume`, `mass_to_moles`, `moles_to_mass`,
  `volume_molarity_to_mass`), drawn over a small set of recognizable salts whose molar mass comes from
  `data/` (sourced). Numeric answers; the gate re-derives each from the raw inputs.
- **`ionic_nomenclature_v1`** (ADR-0027) — name ↔ formula for ionic compounds, both directions
  (`ionic_formula_to_name`, `ionic_name_to_formula`), including the Stock system for variable-charge metals.
  Names come from each ion's sourced `compound_name`; the formula from verified charge crossover. These
  problems carry no numeric `chain`; their `derivation` holds the ion parts, and `subscript_tokens` lists the
  formula tokens the view should Unicode-subscript. `validate-gyms.mjs` re-derives the name (concatenation)
  and the formula (gcd crossover) in pure Node.

Adding a new procedural skill (balancing, stoichiometry, …) means adding a new `family` to `generate_gym`
and, if it introduces a new answer shape, a per-kind branch to `validate-gyms.mjs` so the gate can re-derive
it. It does **not** mean new plumbing.

## What ChemKernel guarantees (so you don't author it)

- **Exact values.** Every amount is an exact `Fraction`; a candidate whose answer would not terminate as a
  decimal is rejected (ADR-0013). Distractors are rounded for display only.
- **Machine-checked dimensions.** Each generated conversion is re-run through the units engine (`Quantity`),
  so the emitted cancellation chain is certified dimensionally homogeneous — `L × mol/L = mol` is proven, not
  asserted.
- **Named mistakes.** Every wrong choice is a specific cancellation error (skipped mL→L, inverted a factor,
  stopped at moles), never a random number.
- **Re-derivable answers.** Each problem carries a raw `derivation` block; `validate-gyms.mjs` re-computes
  every answer in pure Node from those inputs, so CI re-proves the whole set without Python.

## What makes the build refuse to emit

An unknown `family`; a generator that can't produce `count` non-rejected problems at the given seed (a build
failure beats silently shipping fewer); a molar mass that doesn't resolve from `data/`. Fix the spec, not the
output.

## Build & verify

```bash
npm run produce        # …also runs build-gyms: gyms/**/*.gym.toml -> derived/gyms/**  (local; needs uv)
npm run validate       # 7 pure-Node gates over committed derived/ (includes validate-gyms)
npm run build          # validate -> astro build
```

Commit the regenerated `derived/gyms/` alongside the spec — it is the Python↔Node contract CI re-verifies.
Changing `seed` regenerates the whole set; commit the new `derived/` with it.
