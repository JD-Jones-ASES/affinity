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
| `ciaaw-2021-atomic-weights` | `data/elements.toml` atomic weights | `cited` | IUPAC/CIAAW abridged standard atomic weights, Atomic Weights 2021 report (table rev. 2024). Values are scientific facts (not copyrightable, Feist); © CIAAW 2007–2024 covers presentation only | accessed 2026-07-05 · https://www.ciaaw.org/abridged-atomic-weights.htm |
| `iupac-periodic-table` | `data/elements.toml` group/period/block | `cited` | IUPAC periodic table (definitional element positions) | structural facts; used to place elements on the Valence Table |
| `openstax-chemistry-2e` | `data/ions.toml` ion charges; `data/solubility.toml` rules; `data/elements.toml` electronegativity; `data/bonding.toml` ΔEN bond classes; `data/acids-bases.toml` acid/base identities; `data/decomposition.toml` gas-forming intermediates | `cited` | OpenStax *Chemistry 2e*, CC BY 4.0 (ion charges; solubility rules from Table 4.1, §4.2; Pauling electronegativities from Fig 7.6, §7.2; ΔEN bond classification from Fig 7.8, §7.2 — pure covalent < 0.4, polar covalent 0.4–1.8, ionic > 1.8, "a general guide with many exceptions"; reaction classification incl. acid-base neutralization and gas-forming reactions from §4.2) | common ion charges + solubility rules + Pauling electronegativities + the bond-class guideline + the acid/base + gas-evolution reaction conventions (universal teaching facts; the Allred-revised Pauling scale); ion + acid/base *composition* is separately machine-checked in `data.py`/`reactivity.py`; the ΔEN caveat ships as data with the rule; accessed 2026-07-05, Fig 7.8 verified 2026-07-08, §4.2 reaction classes 2026-07-08 |
| `bipm-si-2019` | `data/constants.toml` Avogadro constant | `cited` | BIPM *SI Brochure* 9th ed. (2019); 26th CGPM (2018) redefinition, in force 20 May 2019 | N_A = 6.02214076×10²³ mol⁻¹, **exact by definition** (a defined SI value, no uncertainty); accessed 2026-07-05 · https://www.bipm.org/en/publications/si-brochure |
| `nist-ionization-energies` | `data/elements.toml` first ionization energy | `cited` | NIST Atomic Spectra Database / *Ground Levels and Ionization Energies for the Neutral Atoms* — US-government data, **public domain**. Values (kJ/mol) are scientific facts (Feist) | first ionization energies for Z 1–20 + Fe/Cu/Zn; NIST reports in eV, converted to kJ/mol (1 eV = 96.485 kJ/mol); cross-checked against the `mendeleev` oracle; accessed 2026-07-05 · https://physics.nist.gov/PhysRefData/ASD/ionEnergy.html |
| `cordero-2008-covalent-radii` | `data/elements.toml` covalent radius | `cited` | Cordero, Gómez, Platero-Prats, Revés, Echeverría, Cremades, Barragán, Alvarez, "Covalent radii revisited," *Dalton Trans.* 2008, 2832–2838 (doi:10.1039/b801115j). Radii (pm) are scientific facts (Feist) | single-bond covalent radii, main-group Z ≤ 20 (the modern standard compilation); transition-metal radii are spin-state-dependent and deferred; cross-checked against the `mendeleev` oracle; accessed 2026-07-05 |

## Element-dataset decision (RESOLVED — ADR-0012)

Atomic weights come from **IUPAC/CIAAW** (abridged standard values, using the abridged single value rather
than the published interval), positions from the **IUPAC periodic table**, ion charges from **OpenStax
Chemistry 2e** (CC BY 4.0). All three registered above. Physical properties landed with the Valence-Table
flagship data session (ADR-0031, Phase 1 item 5a):

- ~~**NIST** — physical properties (ionization energies, radii, densities, electronegativity)~~ — landing:
  first **ionization energies** from NIST (`nist-ionization-energies`, public domain); **covalent radii** from
  Cordero et al. 2008 (`cordero-2008-covalent-radii`) — a cleaner single-source compilation than NIST for
  radii; **electronegativity** from OpenStax's Pauling table (folded into `openstax-chemistry-2e`). Densities
  and further NIST properties remain deferred until a lesson needs them.
- ~~The **solubility ruleset**~~ — done (ADR-0017): `data/solubility.toml` from OpenStax Table 4.1,
  registered above.

## Conventions for adding an entry

0. Test **oracles** (ADR-0026: `chempy`, `periodictable` as dev-dependencies cross-checking the engine) are
   *not* register entries — the register records shipped values; oracles verify and never supply one.
1. Register the source here (id, version, license, conditions) in the same session that lands the data.
2. Put the data under `data/` with the source id embedded in the file (provenance travels with the data).
3. Values used in lessons/Atlas entries reference the source id; the gate enforces resolution.
4. Exceptions and validity conditions (temperature, concentration regime) are recorded with the rule, not
   in prose only.
