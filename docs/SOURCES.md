# SOURCES — the honesty register

Quote/data validation is a hard rule: every value or rule in this repo is machine-verified, sourced here,
or labeled as a model assumption (ADR-0003, ADR-0006). Empirical datasets are registered **before first
use**; ChemKernel reads them only from `data/`, and the validate-reference gate fails on any source id
that does not resolve to a row below.

## Verification methods (register method tags, and the badge each renders under)

These tags classify *register entries*; they map onto the three reader-facing badges (ADR-0003) as noted.
Model assumptions are **not** register entries — they live in each lesson's `assumptions[]` and render as
the **model-assumed** badge.

- **`chemkernel-derived`** — the value/relationship is machine-proven by the producer (conservation
  proofs, balanced coefficients, stoichiometric results, unit chains). Renders as **machine-checked**.
  No external source needed for the *math* — though its empirical inputs (atomic masses etc.) each carry
  their own source.
- **`standard-result`** — a textbook-universal relationship (e.g. $PV = nRT$, Henderson–Hasselbalch)
  whose form is source-invariant; verified structurally by the producer and linked to a derivation or a
  more primitive node where one exists. Renders as **machine-checked** when the producer proves it,
  otherwise **data/rule-sourced**.
- **`cited`** — a value, rule, or convention taken from a named source, with edition/version (or URL +
  access date), license/terms, and conditions of validity. Solubility rules, atomic weights, pKa/Ksp/E°
  tables, electronegativities, trend exceptions all live here. Renders as **data/rule-sourced**.

## Register

| Source id | Points to | Method/covers | Version & license | Notes |
|---|---|---|---|---|
| _(none yet — Phase 0 ships the element dataset and solubility ruleset)_ | | | | |

## Element-dataset candidates (decide in first Phase 0 data session → ADR; see ADR-0006)

- **IUPAC/CIAAW** — the authority for standard atomic weights (some published as intervals; the ADR must
  pick a convention for interval → display value). Verify current recommended values + terms at decision
  time.
- **NIST** — physical properties (ionization energies, radii, densities); US-government data, public
  domain.
- A vetted open compilation (e.g. community periodic-table JSON datasets) may be acceptable for display
  metadata (names, categories, blocks) **only** with license verified and values spot-checked against the
  authorities above; load-bearing numbers come from the authorities.

## Conventions for adding an entry

1. Register the source here (id, version, license, conditions) in the same session that lands the data.
2. Put the data under `data/` with the source id embedded in the file (provenance travels with the data).
3. Values used in lessons/Atlas entries reference the source id; the gate enforces resolution.
4. Exceptions and validity conditions (temperature, concentration regime) are recorded with the rule, not
   in prose only.
