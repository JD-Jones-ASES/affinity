# DECISIONS — architecture decision log

Newest at the bottom. Each entry: context → decision → consequences. Keep terse; this is a contract, not a
manual.

---

## ADR-0001 — Mirror the sibling stack; port, don't reinvent (2026-07-05)

**Context.** Affinity is the chemistry sibling of the physics portal Quadrature
(`C:\GitHub_Files\Quadrature`, github.com/JD-Jones-ASES/quadrature), itself built on patterns proven in
Mechanic and the other portals. Quadrature's architecture — build-time verified producer, committed derived
JSON, pure-Node CI gates, static Astro/Svelte player — is exactly what the founding brief asks for.

**Decision.** Adopt the Quadrature stack wholesale: Astro static + Svelte 5 islands, build-time KaTeX,
Python producer as a uv package (local only, never CI), JSON Schema draft 2020-12 +
`additionalProperties:false` validated by Ajv in Node gates, committed `derived/`, LF-pinned
`.gitattributes`, GitHub Pages deploy with `npm install` (not `npm ci`) in CI. Port proven producer
machinery where it applies (the tiered equivalence prover and SI dimensional-homogeneity checker are
already on their third project); replace physics-specific machinery with chemistry-native modules.

**Consequences.** Architecture sessions start from a working reference implementation, not a blank page.
Divergences from Quadrature must be chemistry-motivated and get their own ADR.

## ADR-0002 — ChemKernel: one producer; the species ledger over reaction extent is the computational object (2026-07-05)

**Context.** The brief's thesis (§2, §19): balancing, stoichiometry, limiting reagents, ICE tables,
kinetics, thermochemistry, and electrochemistry are all views of $n_i = n_{i,0} + \nu_i \xi$. Quadrature's
analogous move (one solution object, many renderings) worked.

**Decision.** One build-time producer, **ChemKernel** (`producer/`, package `chemkernel`), is the single
source of truth for all derived content. Its central emitted object is the **species ledger**: species,
phase, charge, molar mass, initial moles, stoichiometric coefficient, extent limit, final moles. Every
lesson view (symbol register, particle view, evidence view, dimensional chain, practice items) renders
from ledger-bearing solution JSON. The solver model is named **Extent**; internal representation uses
reaction extent even where the learner-facing view uses coefficient ratios.

**Consequences.** ICE tables, titration states, and electron ledgers are later extensions of one object,
not new machinery. The player never computes chemistry; it steps the ledger.

## ADR-0003 — Honesty model: four regimes classify knowledge, three badges render it (2026-07-05)

**Context.** Quadrature's two-axis model (machine-derived vs. model-assumed) is not enough for chemistry,
where a third kind of claim — empirical rules and tabulated data — dominates whole topics and must never
masquerade as either algebra or mere assumption (brief §3, §7).

**Decision.** Two layers. **Regimes** (per topic/claim-facet, tracked in `docs/regime-map.md`):
(1) ledger-exact, (2) model-exact, (3) empirical/rule-sourced, (4) mechanistic/interpretive. **Badges**
(per rendered claim): **machine-checked**, **data/rule-sourced** (source + version + conditions,
resolving in `docs/SOURCES.md`), **model-assumed** (disclosed, not discharged). Regime-4 content renders
under the model-assumed badge with an explicit interpretive marker — whether it needs a distinct fourth
badge is an open Phase 0 question (`docs/architecture.md` §open-questions). A missing badge on a
rule/model claim breaks the build.

**Consequences.** "Nitrates are soluble" can never look like a theorem. Every solubility call, ion charge,
and idealization is traceable to a source or an assumption; the schema encodes badges as data.

## ADR-0004 — Provider-agnostic public text; founding brief frozen and gitignored (2026-07-05)

**Context.** The founding brief maps scope to a specific exam-board curriculum by name (brief §15).
Quadrature faced the same and kept its brief private, with a scan-text build gate keeping committed text
provider-agnostic (its ADR-0004).

**Decision.** `PROJECT_BRIEF.md` is gitignored, kept frozen and verbatim — corrections and evolution are
recorded here in ADRs, never edited into the brief. Committed text says "beginning chemistry / first-year
college and advanced high-school chemistry." At Phase 0, port the sibling's `scan-text.mjs` gate and seed
its banned-terms list from the sibling's (the list lives in the gate script, which excludes itself from
the scan).

**Consequences.** The public repo carries no exam-board mapping. Agents citing the brief in committed docs
cite section numbers (brief §N), not its text verbatim, when the text would leak the mapping.

## ADR-0005 — Authoring in TOML (2026-07-05)

**Context.** Same separation as the sibling (its ADR-0005): the human layer (scenario, quantities,
assumptions, misconception, interactivity choice) must stay separate from the verified solution object;
ChemKernel needs a spec, not prose.

**Decision.** Author scenarios as `problems/<topic>/<slug>.problem.toml` and Chemical Atlas entries as
TOML under `reference/`, parsed with stdlib `tomllib` (read-only suits an input format; no third-party
parser). ChemKernel reads specs and emits `derived/**.json`.

**Consequences.** Editing a spec re-runs the producer; verified JSON is regenerated and committed. Exact
spec field sets are fixed in Phase 0 and documented in `docs/authoring-*.md` when they stabilize.

## ADR-0006 — Empirical data: versioned, licensed, build-time datasets; every value carries a source id (2026-07-05)

**Context.** Chemistry runs on tabulated fact: atomic weights, ion charges, electronegativities, solubility
behavior, pKa/Ksp/E°. The brief (§6.2) makes the periodic-table database a first-class engine, and the
honesty model (ADR-0003) requires every such value to be badge-traceable. Facts are not copyrightable
(Feist), but datasets carry licenses and versions that must be recorded.

**Decision.** Curated datasets live under `data/`, versioned, with provenance (source, edition/version,
license, access date) registered in `docs/SOURCES.md` before first use. ChemKernel reads only from
`data/`; no empirical constant may be hard-coded in producer logic. **The choice of primary element
dataset (candidates: IUPAC/CIAAW atomic weights; NIST for physical properties; a vetted open compilation
for display metadata) is deferred to the first Phase 0 data session — research licenses and precision,
then record the choice as an ADR.**

**Consequences.** A `data/` change is a content change with an audit trail. Atomic-mass precision and
sig-fig policy (house-conventions) bind to the chosen dataset's stated uncertainty.

## ADR-0007 — Safety scope: calculation and simulated evidence only (2026-07-05)

**Context.** Chemistry has safety implications physics does not (brief §15). The portal teaches reasoning
about reactions, not performing them.

**Decision.** Hard content gate, v1 and until revisited by the owner: no wet-lab procedural instruction,
no synthesis routes, no procurement/handling/disposal guidance, no hazard-exploiting examples. Evidence
views use simulated or cited measurements. Lessons may *discuss* what an experiment would show; they never
instruct how to run one.

**Consequences.** Scope questions near this line are escalation events (AGENTS.md §Escalation), not
judgment calls inside a session.

## ADR-0008 — Verification split: producer refuses to emit; CI re-gates committed output in pure Node (2026-07-05)

**Context.** Sibling-proven (its ADR-0010): the producer runs locally (Python/uv unavailable-by-design in
CI; subagent sandboxes have no network), so CI must be able to verify everything from the committed repo
alone.

**Decision.** Two layers, both fail-loud. (1) **Emit-time**: ChemKernel raises and refuses to write on any
failed check — formula parse, atom balance, charge balance, unit homogeneity, negative extent/amount,
unsupported empirical claim without source tag, missing badge, ambiguous generated practice item.
(2) **CI-time**: Node gates under `scripts/validate/` re-validate committed `derived/` — Ajv schema,
honesty cross-checks, JS-closed-form parity against embedded high-precision sample values, KaTeX
renderability, provider scan — then `astro build`. Gate failure fails the deploy.

**Consequences.** Committed `derived/` is the contract between local Python and CI Node. A green deploy
certifies every shipped claim passed both layers.

## ADR-0009 — Docs-first bootstrap; explicit session routing and close-out in AGENTS.md (2026-07-05)

**Context.** This repo was founded docs-first so that later implementation sessions (typically run by a
different, cheaper agent than the one that did this design pass) inherit contracts instead of re-deriving
them. Quadrature routes sessions implicitly (inline pointers); that costs cold-start time and invites
sessions to read everything or the wrong things. Session-end discipline (doc sweep, git) previously lived
only in the gitignored `JD.md`.

**Decision.** `AGENTS.md` carries (1) an explicit **session-routing table** — read the always-list plus
your session type's row, nothing more — and (2) a **mandatory close-out checklist** (ADRs recorded → doc
sweep → session log with exact verification counts → staged-files check → commit/push), committed to the
repo so it binds any agent, not just ones with the private profile. Directories are created when their
first content lands; until then `AGENTS.md`'s planned repo map is the plan of record — no `.gitkeep`
scaffolding, the repo never pretends.

**Consequences.** Cold-start cost is one file plus a routing row. Doc drift is bounded by the close-out
contract. If routing rows go stale, fixing them is part of the sweep, not an ADR.

## ADR-0010 — Licensing MIT (code) + CC BY-SA 4.0 (content); private until the owner publishes (2026-07-05)

**Context.** House policy across all portals (JD ethos; sibling ADR-0011): code MIT, content CC BY-SA 4.0,
cite-don't-reproduce, no source PDFs on public sites; work-in-progress stays private, finished things
publish.

**Decision.** `LICENSE` (MIT, code) + `LICENSE-content.md` (CC BY-SA 4.0: lesson prose, worked solutions,
Atlas entries, generated practice, rendered figures). Repo created **private**
(`gh repo create affinity --private`); flipping public + wiring Pages happens only at the owner-reviewed
Phase 0 publish. Empirical data licensing is handled per dataset in `docs/SOURCES.md` (ADR-0006).

**Consequences.** Publishing is a deliberate release event with a review gate, mirroring the sibling's
v1.0.0 pattern.

## ADR-0011 — Pedagogy: direct instruction; a slider must earn its place (2026-07-05)

**Context.** The brief rejects inquiry-first pedagogy outright (§1) and inherits the sibling's
interactivity policy (§9): interactive controls are justified only when co-motion of quantities *is* the
lesson; static annotated frames otherwise.

**Decision.** Two standing content policies. (1) **Direct instruction**: explain, demonstrate
procedurally, generate verified practice aggressively; no unguided discover-it-yourself pages.
(2) **Interactivity**: static by default; a control must reveal a moving relationship (limiting-reagent
switch, titration co-motion, equilibrium shift) or it is cut; no sliders for vibes. Simulations always
share state with the symbolic solution — no disconnected animations, no fake microscopic realism.

**Consequences.** Authoring specs declare static/interactive per visualization and the choice is
reviewable. Interactive candidates in the brief (§9, §14) are the whitelist to start from.

## ADR-0012 — Element & ion datasets: CIAAW + OpenStax, authored as TOML under `data/` (2026-07-05)

**Context.** ADR-0006 deferred the element-dataset choice (source, precision, file format, entry shape) to
the first Phase 0 data session; the parser's molar mass and the periodic-table lens both block on it, and
every value must be badge-traceable (ADR-0003) — resolves architecture open-question Q1.

**Decision.** Three sourced datasets, each registered in `docs/SOURCES.md` before use: atomic weights are
the **IUPAC/CIAAW abridged standard atomic weights** (Atomic Weights 2021, table rev. 2024; the numeric
values are scientific facts, CIAAW cited as authority + access date); group/period/block are the
definitional **IUPAC periodic-table** positions; common monatomic and polyatomic ion **charges** are
conventional teaching facts from **OpenStax Chemistry 2e** (CC BY 4.0). Format is **TOML under `data/`**
(consistent with authored specs, `tomllib` read-only): `data/elements.toml` (nine elements — the six
Phase 0 plus N, S, P so every ion is composed of known elements) and `data/ions.toml` (thirteen ions).
Atomic weights are stored as strings, read as `Decimal`. `data.py` machine-checks the dataset on load —
every ion formula must parse and be built from known elements — so ion *composition* is regime-1 verified
even though ion *charge* is regime-3 sourced.

**Consequences.** ChemKernel reads empirical constants only from `data/` (ADR-0006 honored). Extending the
periodic table = adding rows + a SOURCES entry; no code change. Electronegativity, radii, and ionization
energies (a NIST-class source) are deferred until a lesson needs them.

## ADR-0013 — Exact numeric representation inside ChemKernel: never float (2026-07-05)

**Context.** Chemistry arithmetic (molar mass, balancing coefficients, extent, leftovers) must be exact
and reproducible byte-for-byte in committed `derived/` and re-checkable by the Node parity gate — resolves
architecture open-question Q2. Floats would introduce rounding noise and non-determinism.

**Decision.** No `float` anywhere in the pipeline. Molar masses and other decimal quantities use
`decimal.Decimal` (seeded from dataset strings, preserving stated precision); balancing uses exact
rational arithmetic (SymPy `Rational` null space → integers via LCM/GCD). Computation is exact; rounding is
a display concern only, applied at emit time per the sig-fig policy (house-conventions). Emitted JSON will
carry exact values as strings (mirroring the sibling's §12 sketch) so nothing is lost to float.

**Consequences.** Reproducible builds and a checkable parity contract. Display rounding is separated from
computation; the practice generator must avoid items whose answer hinges on ambiguous rounding (Q7).

## ADR-0014 — Formula parser grammar v0 + balancer via rational null space (2026-07-05)

**Context.** ADR-0008 fixed the balancer as "conservation matrix → smallest integer coefficients" but not
the parser's accepted grammar or the exact solving method — resolves architecture open-question Q3.

**Decision.** Parser grammar v0 accepts elements `[A-Z][a-z]?`, integer subscripts, nested `(...)` groups
with subscripts, a trailing caret charge (`^2-`, `^+`, …), and an optional trailing phase `(s|l|g|aq)`.
Hydrates (`·`) and isotopes are **out of scope for v0** (revisit when a lesson needs them). The parser is
pure (no data). The balancer builds the element-plus-charge conservation matrix (reactants +, products −),
takes the SymPy rational null space, and requires it to be exactly **one-dimensional** — a zero- or
multi-dimensional space raises `BuildError` (unbalanceable or ambiguous). The single solution is scaled to
smallest positive integers and then **re-verified element-by-element and for charge** before return.
Subscripts are never mutated; only coefficients are chosen.

**Consequences.** The Phase 0 scenario balances to `[1,1,1,2]` and the net ionic `Ca^2+ + CO3^2- → CaCO3(s)`
to `[1,1,1]` (charge row load-bearing). 23 producer tests cover parser, dataset, and balancer with
independent hand-checked values. The "do not change subscripts" misconception mode (brief §13.3) is a
natural extension since the engine structurally cannot touch subscripts.

## ADR-0015 — Quantity & units engine: exact Decimal over an amount/mass/volume basis (2026-07-05)

**Context.** The dimensional-analysis chain is a first-class Phase 0 deliverable (brief §6.6, §16): moles =
molarity × volume, mass = moles × molar mass, with units tracked and cancelled. It must be exact
(ADR-0013) and reject invalid conversions.

**Decision.** A `Quantity` (`chemkernel.units`) carries an exact `Decimal` magnitude plus a `Dim` vector
over a three-component chemistry basis — **amount [mol], mass [g], volume [L]**. Multiplication and
division add/subtract `Dim`s (units cancel automatically); a dimension mismatch on convert/add raises
`BuildError`. Unit labels resolve through a small registry (mol, mmol, g, kg, mg, L, mL, M ≡ mol/L, g/mol,
dimensionless). Pressure/energy/temperature/charge dimensions are **deferred** to gases/thermo/electrochem
(add basis components then). Symbolic dimensional homogeneity of *reference formulas* (PV=nRT etc.) is a
separate future concern — adapt the sibling's `dims.py` (SymPy SI 7-vector) when the Atlas formula sheet
lands; the two needs are not conflated.

**Consequences.** The numeric dimensional-analysis chain is exact and machine-checked. Adding a unit = one
registry row. Non-terminating ratios are kept out of this engine (it does terminating-decimal
conversions); exact fractional arithmetic lives in the extent solver.

## ADR-0016 — Extent solver & species ledger: the pivot object, in exact Fraction (2026-07-05)

**Context.** ADR-0002 named the species ledger over reaction extent as ChemKernel's central object but
left its concrete shape and solving method open. Every downstream view (limiting reagent, leftovers,
product mass, ICE tables later) renders from it.

**Decision.** `chemkernel.extent.solve_extent` takes (Formula, initial-moles) pairs for reactants and
products plus `balance()`'s coefficients, and returns a `Ledger` of `LedgerRow`s
(species, phase, charge, signed ν, initial_mol, final_mol, role). It computes ξ_max = min over reactants of
n_{i,0}/coeff_i, marks the argmin(s) limiting (ties allowed → list), and sets every amount via
n_i = n_{i,0} + ν_i·ξ. Arithmetic is exact **`Fraction`** (ADR-0013) so fractional extents never round;
display uses a separate `to_decimal(value, places)` helper (Q7 sig-figs still open). The solver **refuses
to emit** a ledger with any negative amount (the nonnegative-extent guard, ADR-0008). It is
species-agnostic: the molecular equation, the net ionic equation, or a complete ionic equation with
spectators at ν=0 all run through the same machine.

**Consequences.** The Phase 0 scenario reproduces the brief end to end — ξ = 0.00250 mol, CaCl₂ limiting,
0.00050 mol CO₃²⁻ leftover, 0.250 g CaCO₃ — from both the molecular and net-ionic forms. ICE tables
(reversible extent) and the electron ledger are later extensions of this row shape, not new machinery.
14 further tests (units + extent); 37 producer tests total.

## ADR-0017 — Solubility ruleset: sourced, precedence-ordered, machine-classified precipitates (2026-07-05)

**Context.** The precipitate in a precipitation lesson (CaCO₃ is a solid) is an empirical claim, not
algebra. ADR-0008 says an unsupported empirical claim breaks the build; the honesty model (ADR-0003)
requires it sourced and cited. Resolves architecture open-question Q6 (solubility-rule encoding).

**Decision.** `data/solubility.toml` encodes the standard solubility rules faithfully from **OpenStax
Chemistry 2e, Table 4.1** (source `openstax-chemistry-2e`, already registered), restricted to rules whose
anions are formable from the ion table. `chemkernel.solubility.classify(cation, anion)` applies them in a
fixed precedence — (1) a universally-soluble cation (group 1 / ammonium) wins; else (2) the anion's
soluble rule, flipped by its cation-exception list; else (3) the anion's insoluble rule, flipped by its
exceptions — and returns a `Verdict` naming the governing rule id + statement, so the lesson cites the
exact rule (data/rule-sourced badge). `group1` is a class token resolved against `data/elements.toml`. An
anion with no matching rule raises `BuildError` (refuse to emit, don't guess). `verify_phase` turns a
mismatch between an authored phase and the ruleset into a build failure.

**Consequences.** CaCO₃ is classified insoluble by `insol-carbonate` (and Na₂CO₃ soluble because Na⁺ is
group 1) — the precipitate is machine-derived and rule-cited, not asserted. CaSO₄ correctly hits the
sulfate exception. Adding an ion that introduces a new anion means adding its rule + keeping the source
current, enforced by the refuse-to-emit default.

## ADR-0018 — Reaction transforms: dissociation + complete/net ionic via the ion table (2026-07-05)

**Context.** The lesson must show the molecular equation become a complete ionic equation and then a net
ionic equation with spectators cancelled (brief §16). This should be machine-derived, not authored prose.

**Decision.** `chemkernel.reaction`: `dissociate(formula)` decomposes a neutral salt into one cation +
one anion from the ion table by charge balance and composition match (no ion identities hard-coded);
`complete_ionic` dissociates every `(aq)` decomposable species and keeps solids/liquids/gases intact;
`net_ionic` cancels spectators (species present unchanged on both sides), reduces coefficients, and
**re-verifies atom and charge conservation** on the reduced equation (refuse to emit if it fails). v0
treats every dissociable `(aq)` species as a strong electrolyte; a strong/weak flag (so a weak acid stays
intact) is deferred until acid-base content needs it.

**Consequences.** The Phase 0 reaction yields, mechanically: complete ionic
`Ca²⁺ + 2Cl⁻ + 2Na⁺ + CO₃²⁻ → CaCO₃(s) + 2Na⁺ + 2Cl⁻`, net ionic `Ca²⁺ + CO₃²⁻ → CaCO₃(s)`, spectators
Na⁺ and Cl⁻ — with conservation re-proven. 10 further tests (reaction + solubility); 47 producer tests
total. The species ledger (ADR-0016) can now be driven at the net-ionic level from these transforms.

## ADR-0019 — The emit pipeline: build.py reads authored TOML, runs the engine, writes derived JSON (2026-07-05)

**Context.** The engine (ADR-0014–0018) computes everything; it needs an orchestrator turning an authored
spec into the committed solution object, mirroring the sibling's `build.py` + `[project.scripts]` pattern.

**Decision.** `chemkernel.build` exposes the `build-problems` entry point:
`problems/<topic>/<slug>.problem.toml → derived/<topic>/<slug>.solution.json`. It parses the spec's human
layer (id/title/slug/topic/scenario, reactants, products, givens, assumptions, misconception,
visualizations, reference links), then derives everything else via the engine — balance, moles +
dimensional chains from the givens, the species ledger, the three equations + spectators, the precipitate
+ leftovers, and the cited solubility basis (`verify_phase` flags any phase that contradicts the ruleset).
Exact amounts are emitted as **terminating decimal strings**; a non-terminating amount raises rather than
shipping a rounded "exact" value (ADR-0013). The producer refuses to emit on any engine failure; the
authored TOML never contains a derived number. Species ids in emitted rows are phase-stripped cores
(`CaCl2`), with phase in its own field.

**Consequences.** The Phase 0 spec builds to a complete solution JSON reproducing the brief. Adding a
lesson = author a TOML + `npm run produce`; the engine never changes. A `test_build` regression pins the
key fields; 48 producer tests total.

## ADR-0020 — One solution schema with optional blocks, gated by Ajv + honesty cross-checks (2026-07-05)

**Context.** Resolves architecture open-question Q5 (schema granularity). The emitted object needs a
contract that CI can re-validate in pure Node.

**Decision.** **One** `schemas/solution.schema.json` (JSON Schema draft 2020-12, `additionalProperties:
false` throughout) with optional blocks for facets a given lesson may omit (`solubility_basis`,
`visualizations`, `tags`, `reference_links`) — the sibling's proven single-schema pattern — rather than a
schema per lesson kind. `scripts/validate/validate-solutions.mjs` compiles it with Ajv (strict) and adds
the honesty cross-checks the shape can't express: derived path matches topic/slug; ids unique; every
`checks.*` holds; a `rule-sourced` regime requires a cited `solubility_basis.source`; ledger integrity
(limiting rows have `final_mol` 0, extent > 0, reactant/product ν signs); the reported precipitate is a
solid ledger row; provenance sources non-empty. Wired via `package.json` (`produce → validate →
prepare:data`), Ajv committed to devDependencies. The gate is proven non-vacuous (rejects tampered checks,
extra keys, bad enums, missing blocks).

**Consequences.** Committed `derived/` is the Python↔Node contract; CI re-verifies it with no Python. New
optional lesson facets extend the one schema; the honesty gate grows with new invariants, not new schemas.

## ADR-0021 — The player: Astro static + Svelte islands stepping the committed solution JSON (2026-07-05)

**Context.** The verified-data spine existed (ADR-0014…0020) but nothing rendered it. ADR-0001 fixed the
stack (Astro static + Svelte 5, build-time KaTeX, GitHub Pages at base `/affinity`); this ADR records the
player's concrete shape, built to the sibling's proven patterns.

**Decision.** `src/` holds: `layouts/Base.astro` (chrome + nav), `styles/portal.css` (Affinity's own tokens —
a chemistry-blue accent, and **three badge colors** mapping the ADR-0003 honesty model: blue machine-checked,
violet data/rule-sourced, amber model-assumed), `lib/` (`withBase` base-path discipline, `katex` build-time
rendering + `inline`/`plain` prose helpers, `view` deep-render of the solution's LaTeX + an ASCII→Unicode ion
formatter). Pages: home (the ledger thesis), `lessons/` index (grouped by topic), `lessons/[slug].astro`
(one page per committed `*.solution.json` via `getStaticPaths` + `import.meta.glob`), `verification`. The
lesson island `SolutionPlayer.svelte` is a **dumb stepper**: tabs are reconciled views of the one ledger —
Equations (molecular → complete ionic → net ionic), Dimensional analysis (the mole chains), Species ledger
(the pivot table with role coloring), plus the two interactive tabs; always-on are the three badges, the
scenario, the verified result cards, the SHOWN checks, the data-driven misconception refutation, and the
disclosed assumptions. `astro.config.mjs` sets `svelte({ compilerOptions: { css: "injected" } })` so nested
child islands ship their scoped CSS (known trap #2). The player hydrates `client:load` (not `client:visible`)
so it paints in headless previews. It computes no chemistry; every value is read from the JSON.

**Consequences.** Adding a lesson = author a TOML + rebuild; its page appears automatically. The presentation
layer is now real: the full verified chain renders and re-validates via `astro build`. Publish (Pages, repo
visibility) remains the owner's Phase-0 call (ADR-0010) — the deploy workflow is deferred to that event.

## ADR-0022 — Honest interactives: emitted closed forms + engine-sampled parity gate (2026-07-05)

**Context.** ADR-0011 admits a control only when co-motion of quantities *is* the lesson — the
limiting-reagent switch qualifies. ADR-0008 forbids the player from computing chemistry at runtime. The
sibling's resolution (its emit/parity pattern) is: the producer exports browser-evaluable closed forms plus
high-precision sample points, and a Node gate re-proves the JS against the engine.

**Decision.** ChemKernel emits an **optional `interactive` block** (extends the one schema per ADR-0020's
settled pattern — additive optional facet, not a contract change) carrying: slider `params` (volume +
concentration of each solution), `closed_form` (JS-evaluable strings for every number the player displays —
moles of each reacting ion, ξ = min(…), precipitate mass, leftovers, spectator amounts), and a deterministic
grid of `samples` whose `expect` values are computed by the **real engine** (`solve_extent`), several
straddling the limiting switch. `chemkernel.interactive.build_interactive` derives every multiplicity from
the actual chemistry (`dissociate`, `net_ionic`) — nothing hard-coded — and returns `None` (block omitted)
for any reaction outside the supported single-precipitate double-displacement shape, refusing to fabricate a
closed form. `scripts/validate/check-parity.mjs` recompiles each closed form, re-evaluates it at every sample,
requires a match to the engine within tolerance, and cross-checks that the default slider setting reproduces
the committed static answer (ξ, mass). The islands (`ExtentBar`, `BeakerSpecies`) evaluate only these forms.

**Consequences.** The sliders drive the real limiting-reagent switch, proven honest without client-side
Python: the JS the browser runs is verified against the engine across the whole slider range. The three
brief-§16 misconception targets are now interactive (smaller-volume-isn't-limiting; spectators don't vanish;
aqueous salts are free ions). Parity gate proven non-vacuous (a wrong molar-mass literal fails it).

## ADR-0023 — Gate suite rounded out: ledger re-derivation, KaTeX, provider scan (2026-07-05)

**Context.** ADR-0008 wants CI to re-prove the committed output in pure Node; architecture.md planned a
fuller gate table than the single `validate-solutions` gate that existed.

**Decision.** Three further Node gates, all fail-loud, wired into `npm run validate`: **`check-ledger.mjs`**
re-derives every ledger row's final amount as n = n₀ + ν·ξ from the committed initial/coefficient/extent
(independent of Python) and cross-checks the reported result (precipitate moles, leftovers) against the
rows; **`check-katex.mjs`** renders every LaTeX string with `throwOnError:true` so a survived string is
known-good; **`scan-text.mjs`** enforces provider-agnosticism (ADR-0004), its banned-terms list **seeded
from the sibling's** generic exam-board terms (the specific board mapping lives only in the private brief —
extend the list when the owner confirms it). Each is proven non-vacuous.

**Consequences.** Five gates now re-verify committed `derived/` with no Python; the honesty story the portal
advertises is enforced end to end. The atom/charge re-check by element counts is future work (needs element
counts in the emitted ledger or a JS formula parser); the extent-equation re-derivation is the achievable,
load-bearing conservation check today.

## ADR-0024 — Procedural gyms: a producer-generated, verified, drillable problem-set content type (2026-07-05)

**Context.** Phase 1 (brief §17) opens with the procedural core — the dimensional-analysis gym, then formula
/nomenclature, balancing, and stoichiometry engines — whose defining trait is *endless generated* practice,
not one authored scenario. The owner opened Phase 1 with the rationale that solving many problems now makes
granular lessons cheap to fill later. The Phase-0 pipeline (`build_problems` → one authored reaction →
`solution.json`) doesn't fit a generated conversion drill, and the `practice` generator is bolted onto a
lesson. A new content shape was needed; the choice was whether to bolt gyms onto the lesson pipeline or give
them their own producer/schema/gate/player track.

**Decision.** A first-class **gym** content type, mirroring the `reference` track's shape so the machinery is
reusable across Phase-1 items. Authored `gyms/**/*.gym.toml` (topic + family + seed + count) →
`chemkernel.gym.generate_gym` → committed `derived/gyms/<slug>.gym.json` via a new **`build-gyms`** entry
point; `npm run produce` runs all three builders. The generator is **deterministic in the seed** (ADR-0008),
computes every value as an exact `Fraction` and **rejects any non-terminating candidate** (ADR-0013), and
**re-checks each conversion's dimensions through the units engine** (`Quantity`) so the emitted cancellation
chain is machine-certified homogeneous — the author never certifies that L × mol/L = mol. Every wrong choice
is a **named cancellation mistake**, not a random number. Each problem carries a raw `derivation` block so the
new Node gate **`validate-gyms.mjs`** re-derives every answer in pure Node (the check-parity pattern:
independent re-computation from raw inputs), plus schema + choice invariants (one correct, distinct displays,
chain ends at the answer, molar-mass consistency). One `schemas/gym.schema.json` (draft 2020-12,
`additionalProperties:false`). The player gets a `/gym/` section + a `DimensionalGym.svelte` drill island that
reveals the cancellation chain on each pick (reusing the proven `PracticeQuestion` interaction pattern);
molar masses stay sourced (provenance carries the atomic-weight source id).

**Consequences.** Seven Node gates now; Phase-1 procedural fill inherits a solved instrument — items 2–4
(nomenclature, balancing, stoichiometry gyms) add a new `family` to `generate_gym` (and, where a new answer
shape appears, a per-kind branch to `validate-gyms`) rather than new plumbing. The first family,
`solution_conversions_v1`, covers volume·molarity·moles·mass in five kinds using only the existing units
engine + sourced molar masses (no new dataset). Particle/Avogadro conversions are deferred until the Avogadro
constant is registered as a sourced datum. The units engine verifies *dimensions*; the exact *values* are
Fraction-exact in the producer and re-derived numerically (float tolerance) by the Node gate — consistent
with how `check-parity` trusts emitted literals and anchors them to engine-computed expectations.

## ADR-0025 — Formula display conventions: upright LaTeX, Unicode prose subscripts, sig-fig policy settled (2026-07-05)

**Context.** Brief §6.1 mandates proper sub/superscripts wherever formulas render. As built, three layers
disagreed: producer LaTeX rendered element symbols in KaTeX's default math italic (𝐶𝑎𝐶𝑙₂ — wrong for
chemistry; IUPAC wants upright), hand-authored concept entries already used upright `\text{…}`, and the
generated practice/gym prose showed raw ASCII (`CaCl2`). Separately, the display sig-fig policy had been
provisional since bootstrap (architecture Q7). The gates constrain the fix: `check-parity`/`validate-gyms`
compare display strings inside committed `derived/`, so typography must not mutate the data layer.

**Decision.** One convention, three layers (house-conventions §Notation):
1. **Data/interchange stays ASCII** — specs, schemas, derived JSON, and gate comparisons keep `CaCl2` /
   caret charges. Typography never enters the contract layer.
2. **Producer LaTeX is upright**: `formula._to_latex` wraps the body in `\mathrm{…}` (phases keep
   `\text{(aq)}`); every equation, ledger row, and Valence-Table symbol inherits.
3. **Prose gets Unicode sub/superscripts at build time, view-side**: `view.js` gained `prettyText(text,
   tokens)` — longest-first `replaceAll` of the exact formula tokens the producer emitted (practice: the
   interactive block's cation/anion/product ids; gym: each problem's `derivation.inputs.substance`; lesson
   scenario/assumptions/misconception: the given/precipitate/leftover species), skipping `$…$` math
   segments. Measurement numbers are untouchable by construction; no regex, no prose parsing.
Also settled: **display sig-figs (closes architecture Q7)** — ledger exact, derived results at 3 significant
figures, givens echoed at their stated precision; the practice reject-list already enforces
no-ambiguous-rounding.

**Consequences.** All `derived/` LaTeX regenerated once (`check-katex` re-proves all strings). The islands
stay plain-text (Unicode needs no `{@html}`); hydration payload unchanged. New generators must emit ASCII
tokens and let the view subscript them — a generator that pre-formats display strings would break the
Node re-derivation gates and is therefore wrong by contract, not just by style.

## ADR-0026 — External chemistry libraries are verification oracles only (2026-07-05)

**Context.** The owner asked whether Python chemistry libraries should be used. Candidates: `chempy`
(SymPy-based `balance_stoichiometry`, formula-parsed molar masses), `periodictable` (element masses),
`mendeleev` (element properties). ADR-0006/0012/0013 already commit the product to curated, cited `data/`
and exact arithmetic — an external library at runtime would smuggle in unsourced values and floats.

**Decision.** External chemistry libraries enter the project **only as dev-dependency test oracles**
(`pyproject` dependency-group `dev`; never `[project]` dependencies; never imported by `chemkernel`
modules). `tests/test_oracle.py` cross-checks: every curated CIAAW atomic weight against `periodictable`;
every corpus substance's molar mass against `chempy`'s independent parser+table; both lesson balances
against `chempy.balance_stoichiometry`. Loose tolerances (different atomic-weight editions), `importorskip`
so a failed optional install degrades to skip rather than break the suite. They are not SOURCES.md register
entries — the register records *shipped* values; oracles verify, they never supply.

**Consequences.** The engine is now double-checked by an independent implementation on every test run —
redundant proof in the spirit of the two-layer Python/Node verification (ADR-0008). When the Valence-Table
flagship needs new element properties (electronegativity, radii, ionization energies), the data still gets
curated into `data/` from a primary source per ADR-0006 — with `mendeleev` available as an oracle to
cross-check the transcription, which is exactly the failure mode oracles catch.

## ADR-0027 — Ionic nomenclature: sourced compound names + pure-Node name/formula re-derivation (2026-07-05)

**Context.** Phase-1 item 2 (formula & nomenclature engine) needs name↔formula in both directions. Naming
is a sourced convention (regime 3); the formula an ion pair assembles into is charge balance (regime 1,
already machine-verified by `reference.assemble_formula`). But the gym honesty model (ADR-0024) has the Node
gate *re-derive every answer in pure Node* — and nomenclature answers are strings (names, formulas), while
the gate has no JS chemistry engine (no formula parser — ADR-0023 left that as future work). The question
was how to keep the CI-re-proves guarantee for string answers.

**Decision.** (1) **Data:** each ion in `data/ions.toml` gains a sourced `compound_name` — the name it takes
inside a compound (element name for a fixed-charge cation, element + Stock Roman numeral for a variable-
charge metal `iron(III)`, -ide/-ate for anions). Six metals were added to `data/elements.toml` (K, Mg, Al,
Fe, Cu, Zn; weights cross-checked against the `periodictable` oracle, ADR-0026), Fe and Cu carrying variable
charges. (2) **Engine:** `chemkernel.nomenclature` is the single source of truth — `name_ionic` = cation +
anion `compound_name`; the formula is `assemble_formula` (verified crossover). (3) **Gate:** the nomenclature
gym emits, per problem, the structured ion parts (`id`, `formula_part`, `charge`, `compound_name`) plus the
`formula` and `name`. `validate-gyms.mjs` re-derives **both independently in pure Node** — the name by
concatenation, the **formula by re-running the gcd charge-crossover + group-string assembly** (integer
arithmetic + string ops, no parser) — and checks them against the emitted values and the answer, plus that
the prompt states the other representation. Every wrong choice is a *named* mistake (wrong Stock numeral,
each ion's own charge used as its subscript, covalent prefixes on an ionic compound).

**Consequences.** The gym schema generalized to two problem shapes: `chain`/`target_unit`/`answer.unit`
optional; `derivation` carries either numeric `inputs` (conversions) or `cation`/`anion`/`formula`/`name`
(nomenclature); a `subscript_tokens` array tells the view which formula tokens to Unicode-subscript
(ADR-0025) — names have no digits so they pass through untouched. Composition stays regime-1 machine-verified
(crossover); names stay regime-3 sourced. The Valence Table shows one ion per element (lowest charge for a
variable metal, deterministically); full oxidation-state display is an item-5 (flagship) enhancement. This
is the template for items 3–6: a new gym family = a Python generator + a `validate-gyms` re-derivation
branch, not new plumbing.

## ADR-0028 — Balancing gym: emit the conservation matrix; re-parse + re-balance in pure Node (2026-07-05)

**Context.** Phase-1 item 3 (the balancing engine) needs a gym family where the learner picks the balanced
equation and *sees every element tally*. The answer shape is new — a coefficient vector over a set of
species, not a number or a string — so it needs its own emission + a new `validate-gyms` re-derivation
branch (ADR-0024's template). Two honesty questions: (1) the player must show a live per-element tally
without computing chemistry at runtime (ADR-0008); (2) the Node gate must re-prove the answer is a true
balance of the *exact formulas shown to the student*, but ADR-0023 had deferred a JS formula parser, so the
gate had no independent way to get element counts from a formula string. The stress scenario is a hard
conservation-matrix balance (combustion with odd coefficients) plus the "never mutate a subscript"
misconception made to fail visibly (brief §13.3).

**Decision.** A `balancing_v1` family in `chemkernel.gym` over a **curated skeletal-reaction corpus**
spanning the archetypes a first course balances (synthesis, combustion, decomposition, single/double
replacement, acid-base, net-ionic). Each reaction is **balanced by the engine** (`balance()`'s rational
null space, ADR-0014) — never authored coefficients — and the problem emits the **conservation matrix as
per-species element counts + charge** (the columns), the coefficient vector (the answer, as a CSV
`answer.value`), and the balanced-equation `answer.display`. Distractors are **named mistakes**: a
coefficient perturbation that throws a specific element off (the misconception states which, and by how
much — data-driven from the tally), and, where genuinely deceptive, the **subscript-mutation trap** — a
*different real substance* (H₂O→H₂O₂, CO→CO₂) that makes the atoms look balanced without coefficients;
the producer refuses to ship a trap unless it proves the trap atom-balances **and** changed a formula.
Two verifiers, independent of the Python producer:
1. A **JS formula parser** `scripts/validate/formula.mjs` (a faithful port of grammar v0) — closing the
   ADR-0023 future-work gap. `validate-gyms.mjs` re-parses every emitted species formula, cross-checks the
   re-derived counts + charge against the emitted matrix (two independent parsers must agree), then verifies
   the coefficient vector **zeroes every element row and the charge row**, is all-positive and reduced
   (gcd 1), and reconstructs to the emitted answer. No null-space solve — Python owns uniqueness (`balance()`
   requires a 1-D null space); the gate proves the emitted answer is a true, reduced balance of the exact
   shown formulas.
2. The **player** (`DimensionalGym`) renders the tally as **integer addition over the emitted matrix** ×
   the correct coefficients — no runtime chemistry, the same "step producer data" discipline as the ledger.
Also fixed here (view-only, no data churn): the gym islands now present choices in a **deterministic
per-problem shuffle** (seeded by the problem id, so server and client agree — no hydration mismatch), because
the producer always emits the correct choice first; picking still uses each choice's original index, and the
Node gate was already position-agnostic (it `filter`s for the correct choice). The corpus's neutral reactions
are cross-checked against `chempy.balance_stoichiometry` as an oracle (ADR-0026).

**Consequences.** Item 3 lands as a new family + a new gate branch + a reusable JS parser — no new plumbing,
per ADR-0024. The JS parser is now available to any future gate needing element counts from a formula string
(e.g. the ADR-0023 ledger atom/charge re-check). The tally view generalises the drill island to a third
problem shape (conversions have a `chain`, nomenclature neither, balancing a `species`/`coefficients` matrix)
without touching the conversion/nomenclature paths. Redox (half-reaction balancing, electron bookkeeping) is
still Phase 2; this family balances by atom + total-charge conservation only. The corpus is data — extending
it is adding a row, and a reaction with a clean subscript-mutation trap adds a `trap` (proven honest at emit
time).

## ADR-0029 — Stoichiometry gyms: forward-generated, balance-verified, molar-mass-consistent (2026-07-05)

**Context.** Phase-1 item 4 (the stoichiometry suite) opens with the stress scenario *percent yield on a
mass→mass path*. Two new gym families are needed — `mass_stoichiometry_v1` (grams → moles → mole ratio →
moles → grams) and `percent_yield_v1` (theoretical yield by mass stoichiometry, then actual ÷ theoretical ×
100). Two honesty questions specific to stoichiometry: (1) the mole ratio is a chemistry claim (it comes from
the balanced equation), so the gate must confirm the ratio is real, not just re-do the arithmetic; (2) the
answers must be exact terminating decimals despite non-round molar masses.

**Decision.** Both families **generate forward from a clean mole amount** (the conversion-gym pattern,
ADR-0024): pick moles of the given species so `mass = moles × M` is exact, carry it across the engine-derived
mole ratio, convert back, and **reject any non-terminating candidate** (ADR-0013). Molar masses come from
`data/` (sourced). Each problem emits the **full balanced equation** (`species` + `coefficients`, the
item-3 shape) *plus* the numeric `given`/`target` facts (formula, coefficient, molar mass, mass). The gate
(`validate-gyms.mjs`) does two independent things per problem: it **re-verifies the equation balances**
(reusing `verifyBalance`, factored out of the balancing branch — so the mole ratio is proven to come from a
real balance, closing the "trust the ratio" hole), and it **re-derives the mass or percent numerically** from
the given/target molar masses + the coefficient ratio — the same arithmetic a student does, in pure Node.
Molar-mass consistency is now enforced **across the whole gym corpus** (conversions ∪ stoichiometry): the
same species must carry the same sourced molar mass everywhere it appears. Distractors are named mistakes
(flipped mole ratio, ratio ignored, grams→moles skipped; for percent yield: inverted, ×100 dropped, reactant
mass as denominator). The neutral corpus's molar masses are cross-checked against `chempy` (ADR-0026).

**Consequences.** Two families reuse the conversion gym's `chain`/`target_unit`/`answer` shape (so the drill
island renders them with no new plumbing) and the item-3 balance verifier (so the equation is re-proven). The
drill island's chain caption became family-aware (units cancel for conversions; "cross the mole ratio" for
mass stoichiometry; "theoretical first" for percent yield). One island bug surfaced and was fixed in
in-browser verification: the conservation-tally block keyed on `derivation.species` (which stoichiometry now
also emits, for the balance check) — it was re-keyed to `kind === "balancing"` so the tally stays
balancing-only. A `percent-yield` Atlas concept covers the regime-map row. **Deferred (item 4 continues):**
`limiting_mass_v1` (limiting reagent from masses), the flagship **percent-yield lesson** (topic
`percent-yield`, which needs the lesson pipeline generalised past precipitation), and particle-count
stoichiometry (needs the Avogadro constant registered as a sourced datum, SOURCES + `data/`).

## ADR-0030 — Finishing item 4: percent-yield lesson (yield block), Avogadro datum, limiting-mass gym (2026-07-05)

**Context.** ADR-0029 landed two stoichiometry gym families and named three deferred item-4 pieces: the
`limiting_mass_v1` gym, the flagship **percent-yield lesson**, and registering the **Avogadro constant**. This
ADR records how each landed. The limiting-mass gym is pure ADR-0029 pattern (a stoich family) and needs no new
decision. The lesson and the datum do: the lesson introduces a new *lesson* facet (actual-vs-theoretical
yield), and the datum is a new sourced dataset.

**Decision.**
1. **The percent-yield lesson reuses the precipitation pipeline rather than generalising it.** The theoretical
   yield of a gravimetric precipitation *is* the precipitate mass the ledger already computes at maximum
   extent — so a percent-yield lesson is a precipitation lesson (`ZnCl2 + Na2CO3 → ZnCO3(s) + 2 NaCl`, fresh
   metal) plus an authored `[yield] actual_mass_g` and a new **optional `result.percent_yield` block**:
   theoretical (= precipitate mass), the authored actual, and `percent = actual ÷ theoretical × 100`. The
   producer **refuses a nonphysical yield** (actual ≤ 0 or > theoretical — you cannot collect more than forms,
   ADR-0008). Percent is a measured ratio, emitted at 0.1% (ADR-0025); `check-ledger` re-derives it (and
   confirms theoretical = precipitate mass, actual physical). The lesson inherits the full machinery — three
   equations, ledger, both interactives, generated practice — **for free**; the yield card is the only new
   render. The formal misconception register stays the reusable precipitation one (data-driven refutation
   untouched); the *yield* misconception (a yield can't exceed 100%) lives inline in the yield card. Chosen
   over generalising `build.py` to arbitrary (non-precipitation, mass-given) reactions — that larger
   generalisation waits until a synthesis/combustion yield lesson genuinely needs it.
2. **The Avogadro constant is a curated, sourced datum** (`data/constants.toml`, source `bipm-si-2019`),
   loaded by `data.py` like every other constant — never hard-coded. It is **exact by the 2019 SI redefinition**
   (N_A = 6.02214076×10²³ mol⁻¹), so it carries no uncertainty. This registers the ADR-0029 prerequisite.

**Consequences.** Item 4's three gym families (`mass_stoichiometry_v1`, `percent_yield_v1`, `limiting_mass_v1`)
and its flagship lesson are complete; the Atlas covers the stoichiometry/percent-yield regime-map rows. Three
lessons total now (2 precipitation + 1 percent-yield). **One item-4 sliver stays deferred:** the *particle-count*
gym drills (moles↔particles) — the Avogadro datum is now in place, but the drills need scientific-notation
display plumbing the gym's decimal-chain rendering doesn't have, and they pair naturally with Phase-2 gas work
(molar volume). The `result.percent_yield` block is the template for any future actual-vs-theoretical lesson;
generalising `build.py` past single-precipitate double-displacement (for a non-precipitation yield lesson)
remains future work.

## ADR-0031 — Element-property curation for the Valence-Table flagship: sourced properties + oracle-checked widening (2026-07-05)

**Context.** Phase-1 item 5 (the Valence-Table flagship) opens with a data-curation session (ROADMAP; ADR-0012
deferred "electronegativity, radii, and ionization energies … until a lesson needs them" to a NIST-class
source; ADR-0026 anticipated cross-checking that curation with the `mendeleev` oracle). The trend lenses
(item 5b) need per-element properties, and the current nine-plus-six element set is too narrow to show the
period/group trends cleanly. The honesty model (ADR-0003/0006) requires every property to carry a resolvable
source id.

**Decision.**
1. **Widen the element set to the first twenty elements (H…Ca) plus the three transition metals the
   nomenclature engine introduced (Fe, Cu, Zn)** — 23 total. This completes periods 1–3 and opens period 4, so
   period 2 (Li→Ne) / period 3 (Na→Ar) left-to-right and groups 1/2/17/18 top-to-bottom all read as clean
   trends. Atomic weights/positions of the eight new elements use the already-registered CIAAW/IUPAC sources
   (no code change — ADR-0012's "extending the table = adding rows"). Added the group-1/2/17 common ions
   Li⁺, Be²⁺, F⁻ (OpenStax charges; composition machine-checked on load).
2. **Curate three periodic properties, each from a primary source, as optional Decimal fields** (`Element`
   grows `electronegativity`, `covalent_radius_pm`, `first_ionization_kj_mol`; never float — ADR-0013):
   - **electronegativity** — Pauling scale, folded into `openstax-chemistry-2e` (Fig 7.2/7.6). *Omitted* for
     the noble gases (Pauling undefined) — never written as 0.
   - **covalent radius (pm)** — Cordero et al., *Dalton Trans.* 2008 (`cordero-2008-covalent-radii`), the
     modern single-source compilation. Main-group Z ≤ 20 only; the transition-metal radii are spin-state-
     dependent and *deferred* to a later pass rather than pick a spin state silently.
   - **first ionization energy (kJ/mol)** — NIST atomic data (`nist-ionization-energies`, public domain).
   The two new sources are registered in `docs/SOURCES.md` before use. OpenStax figures are images (not
   machine-readable), so the exact values were transcribed from the primary compilations and cross-checked
   against the **independent `mendeleev` oracle** (dev-only, ADR-0026) in `tests/test_oracle.py` — the failure
   mode oracles exist to catch. Tolerances are keyed to the definition gap (EN 0.05; radius 5 pm — carbon's
   sp²/sp³ Cordero value differs 3 pm; IE 2 kJ/mol for the eV→kJ/mol conversion).
3. **Emit the widened set + properties into `valence-table.json` and gate them now.** The producer threads
   each curated property (as a string, only where present) and the three property source ids into the emitted
   table; the schema declares them (`additionalProperties:false` preserved); the lens surfaces them in the
   element-detail panel with a data-sourced badge. The interpretive **trend/bonding/practice lenses stay in
   item 5b** — this increment is data + gating + minimal surfacing.
4. **Make SOURCES.md's promised enforcement real.** SOURCES.md claims "the validate-reference gate fails on
   any source id that does not resolve to a row below," but no gate implemented it. `validate-reference.mjs`
   now parses the register and **fails on any emitted `source` (concept or Valence-Table facet) that is not a
   registered id** — closing a doc-vs-code drift and machine-enforcing this session's two new registrations.

**Consequences.** The Valence Table now carries every input the item-5b trend/bonding/practice lenses need,
each machine-tied to a registered primary source and independently oracle-verified; extending it further is
adding rows + (for a genuinely new property) an optional field. Deferred: transition-metal covalent radii
(spin-state pass); ionic radii (a per-ion, coordination-dependent property — belongs on the ion table, not
the element); densities and further NIST properties (until a lesson needs them). `mendeleev` (+ `pandas`) join
`chempy`/`periodictable` as dev-only oracles.

## ADR-0032 — Generated practice must not be answerable by recognition: numeric answers are free entry (2026-07-05)

**Context.** The owner observed that the percent-yield gym was trivially gameable: a problem's choices were
`55 %`, `0.55 %`, and a third value, and *the correct answer was always the plausible two-digit percent* — the
`0.55 %` (forgot ×100) and the >100 % (inverted) options are eliminable on sight, and the third "never needs
checking." A human learns the pattern in seconds and answers with zero chemistry. This is not a percent-yield
bug; it is structural to putting a **numeric** answer in a multiple-choice menu. The named-mistake distractors
that make good *pedagogy* (forgot ×100, skipped mL→L, sized the yield from the excess reagent) produce answers
a different order of magnitude or format from the truth — which is exactly what makes them eliminable as menu
options. Audit: the four numeric gym families (conversions, mass-stoichiometry, percent-yield, limiting-mass)
all had this; the two categorical families (nomenclature, balancing) did not — their distractors are plausible
same-form names/formulas/coefficient-sets that genuinely require checking.

**Decision.** One principle, enforced end to end: **generated practice must not be answerable by recognition.**

1. **Numeric answers are FREE ENTRY, not a menu.** The learner types the number. The producer no longer emits
   `choices` for a numeric problem; it emits a **`diagnostics`** catalogue — each named mistake's *value* +
   its misconception. The player checks the entry against the answer (relative tolerance 1 %, so ordinary
   rounding is accepted) and, if wrong, against the diagnostics — naming the specific mistake the learner
   actually made. The values that were bad *distractors* (0.55 %, a 1000×-too-large mass) become good
   *diagnostics*: precise feedback if and only if the learner produces them. There is nothing to eliminate.
2. **Categorical answers stay multiple choice** (names, formulas, coefficient sets) — a menu is honest because
   every distractor is a plausible, same-form answer a specific misconception produces, with no magnitude or
   format tell. The producer marks each problem's `mode` (`numeric` | `choice`).
3. **The gate enforces the split** (`validate-gyms.mjs`, ADR-0024): a numeric problem must carry `diagnostics`
   and **no** `choices` (a menu would be gameable); a categorical problem must carry a one-correct `choices`
   menu and no diagnostics; and every diagnostic value must sit **≥ 3 %** from the answer, so the 1 % entry
   tolerance can never mis-flag a correct entry as a mistake (the producer drops any mistake within 3.5 %).

**Consequences.** The gym drills computation, not test-taking; the owner's exact complaint is closed and the
whole numeric-gym family is ungameable by construction. Named-mistake feedback is *strengthened* — a mistake is
now caught when the learner commits to it, not merely offered for recognition. Schema grew `mode` +
`diagnostics` (`choices` now optional); the `DimensionalGym` island gained a numeric-entry path (input +
tolerance check + diagnostic lookup + a "Show answer" reveal) beside the existing menu. **The lesson Practice
tab was converted the same way in the same session** (`chemkernel.practice` + `PracticeQuestion.svelte` +
`check-parity.mjs` + the solution schema's practice block): its **mass** and **leftover** questions are now
free entry with a `diagnostics` catalogue (the `0 mmol` leftover throwaway became a diagnostic), while the
categorical **which reagent limits** stays a menu (both reagents are plausible). Free entry suits numeric
answers; a menu remains right for genuinely categorical ones (which limiting reagent, classify the reaction)
where every option is plausible.

## ADR-0033 — Valence-Table flagship modes: lenses, trends, formula builder, bonding; regime-4 renders as an interpretive marker (2026-07-08)

**Context.** Phase-1 item 5b (brief §8): the curated element properties (ADR-0031) exist but the table only
*lists* them — the flagship needs the lenses (each with the brief-§8.1 pattern panel: what pattern / why /
exceptions / where it shows up), trend graphs, a real formula mode (brief §8.3, plus the item-2 deferred
naming hookup), and a bonding mode (ΔEN → polarity). Three open questions: (1) the pattern panels' "why"
text is the project's **first regime-4 (mechanistic/interpretive) content**, which is exactly the trigger
architecture Q4 set for deciding its badge; (2) the bonding classification thresholds are a teaching rule that
must be sourced, not hard-coded (ADR-0006); (3) the player must drive all four modes without computing
chemistry at runtime (ADR-0008).

**Decision.**
1. **Q4 resolved — no fourth badge.** Regime-4 content renders under the **model-assumed (amber) badge with an
   explicit "interpretive" marker** — ADR-0003's documented default made concrete. Each lens panel is emitted
   with `regime: "mechanistic"` and the player renders it as *interpretive — an explanation, not a proof*,
   beside the lens's data-source badge: the colored values are the sourced evidence; the "why" is the useful
   story. The `reference.schema.json` `mechanistic` enum value (reserved since bootstrap) is now live for
   concept entries too, rendered the same way.
2. **Lenses are emitted data.** `build_valence_table` emits a `lenses` catalogue — ion charge, valence
   electrons, electronegativity, covalent radius, first ionization energy — each carrying the element-field it
   colors by, its unit, its source key (must resolve through the table's `sources` map to a SOURCES.md row),
   and the four-part pattern panel. **Valence electrons** are emitted per element, derived from the IUPAC
   group (groups 1–2 → the group number; groups 13–18 → group − 10; He → 2); d-block elements are honestly
   omitted (the count is convention-dependent) exactly as the noble gases omit electronegativity. The Node
   gate re-derives the rule from the emitted group/block.
3. **Formula mode is the full verified crossover product, with names.** `charge_balance` grows from the six
   lesson salts to **every cation×anion pair** in the ion table (H⁺ excluded — acid naming remains the item-2
   deferred follow-up), each still assembled by `assemble_formula` (machine-verified neutral + composition)
   and now carrying the compound **name** from `chemkernel.nomenclature` (the item-2 hookup) plus the ion
   `compound_name` parts so `validate-reference` re-derives the name by concatenation and the formula by gcd
   crossover in pure Node (the ADR-0027 pattern). Where the canonical mistake — each ion's own charge as its
   own subscript — differs from the crossover, the entry emits a named `mistake`, proven at emit time to be
   **non-neutral** (charge sum shown) or **unreduced** (neutral but not the smallest whole-number ratio);
   pairs where it coincides with the answer emit none. Variable-charge metals surface **all** their common
   ions (`other_ions` beside the lens's lowest-charge `common_ion`), closing item 2's deferred
   full-variable-charge display.
4. **Bonding mode is a sourced rule over emitted data.** A new curated ruleset `data/bonding.toml` — the
   OpenStax Chemistry 2e Fig 7.8 (§7.2) ΔEN classification: pure covalent < 0.4, polar covalent 0.4–1.8,
   ionic > 1.8 — with OpenStax's own caveat carried as data: *a general guide with many exceptions* (HF sits
   near the line yet is polar covalent; the better guide is the atoms — two nonmetals bond covalently, metal +
   nonmetal usually ionically). Folded into the already-registered `openstax-chemistry-2e` source (coverage
   extended). The island computes ΔEN by **integer arithmetic over build-time ×100 values** (exact — no float
   noise) and compares against the emitted thresholds: stepping producer data, the ADR-0028 tally discipline.
   The caution renders always, under the interpretive treatment.
5. **Trend mode plots committed values.** No new data: the island renders an SVG of the already-emitted sourced
   values across a chosen period or down a chosen group. Missing values (noble-gas EN, transition-metal radii)
   render as labeled gaps, never interpolated; partial period 4 says so.

**Consequences.** All five brief-§8 modes are live on the curated data, none of it computed at runtime; Q4 is
closed (no honesty-model change — the three badges stand); the interpretive marker is the pattern for all
future regime-4 content. `valence-table.schema.json` grows the lens/bonding/name/mistake/other-ion shapes;
`validate-reference` gains pure-Node re-derivations (valence electrons, salt names, crossover subscripts,
mistake honesty). Deferred: oxidation-state, electron-affinity, metallic-character, density, abundance lenses
(brief §8.1 lists more than the curated properties support — each needs a data-curation pass first); a
metal/nonmetal field for a data-driven bonding caution.

## ADR-0034 — periodic_trends_v1: the practice mode is a gym generated from the table's own data (2026-07-08)

**Context.** Brief §8.5: the table generates targeted drills "from the same data source and explanation
rules." Item 5b's practice mode should be a gym family (ADR-0024 template: a generator + a `validate-gyms`
branch, no new plumbing). Two honesty questions: (1) periodic trends have real exceptions (B < Be and O < N in
first ionization energy — visible in the curated NIST data), and drills must answer from **data**, never from
the naive trend rule; (2) the gym's embedded property values must be *the same values* the Valence Table
renders, or the corpus contradicts itself.

**Decision.** A `periodic_trends_v1` family in `chemkernel.gym`, three kinds, **all categorical menus**
(`mode: "choice"`, ADR-0032 — an element, an ion, or an ordering is a plausible same-form choice):
1. **`trend_compare`** — which of three same-period (or same-group) elements has the largest/smallest covalent
   radius, first ionization energy, or electronegativity. The answer is the curated extreme; every wrong
   choice's misconception states both values and the trend it misread. H and the d-block are excluded from
   trend series (anomalous placement / no curated radius); an extreme tie rejects the candidate.
2. **`predict_ion`** — the common monatomic ion for a fixed-charge main-group element (variable-charge metals
   and H excluded), distractors being the sign flip ("metals lose, nonmetals gain") and the miscounted charge
   (an anion charged by its valence-electron count instead of its vacancy count; a metal losing the wrong
   number).
3. **`order_ionization`** — three same-period elements ordered by increasing first ionization energy.
   Distractors: the reversed order, and — when the data order differs from left-to-right position order — the
   **naive trend order itself**, with the exception named (the B/Be and O/N dips become the teaching moment
   instead of a lie).
Each problem's `derivation` embeds the property, the per-element values, and (for ions) the predicted ion, so
`validate-gyms.mjs` re-compares/re-sorts numerically in pure Node **and cross-checks every embedded value,
ion, and symbol against the committed `derived/reference/valence-table.json`** — one source of truth across
the corpus (the molar-mass-consistency idea extended to reference data). Provenance carries the property
source ids.

**Consequences.** Gym family #7; the drill island renders it with zero new plumbing (choice mode, no chain);
`gym.schema.json` grows the three kinds + a `candidates`/`ion`/`property` derivation shape. Trend exceptions
are answered honestly by construction — if the curated data and the naive rule disagree, the data wins and
the explanation says why. Deferred: radius/EN orderings (IE has the instructive exceptions; one ordering kind
keeps the menu space clean), "which compound is most likely ionic" (needs the metal/nonmetal field),
electron-configuration matching (needs configurations curated).

## ADR-0035 — Reaction classifier + reaction-family Atlas kind; redox by the free-element signature (2026-07-08)

**Context.** Phase-1 item 6 (brief §10.4) opens with the stress scenario *classify + predict products for the
core reaction families* — combustion, synthesis, decomposition, single/double replacement, and the
double-replacement sub-types precipitation / acid-base / gas-evolution — plus a redox tag. The engine had no
classifier and no reaction-family reference kind. Two honesty problems: (1) "this is a precipitation reaction"
is a claim that must be machine-verified, not asserted; (2) full redox bookkeeping needs oxidation numbers,
which are a Phase-2 topic (regime-map) — so how does a first-course Atlas flag redox honestly without them?

**Decision.**
1. **`classify_reaction` in `chemkernel.reaction`** is a pure function of the balanced, phased formulas + the
   injected sourced datasets. Families are recognized most-specific-first: **combustion** (a C/H(/O) fuel +
   O2 → only CO2/H2O), **synthesis** (n→1), **decomposition** (1→n), **single replacement** (one free element
   each side), then the double-replacement sub-types **acid-base** (an acid + a base → salt + water),
   **gas-evolution** (a (g) product justified by an unstable intermediate in the decomposition table), and
   **precipitation** (an insoluble solid product, cited to the solubility rule), else generic **double
   replacement**. No family is hard-coded chemistry — each cites data (solubility ruleset, acid/base table,
   decomposition table). Unclassifiable → BuildError (refuse to emit; the classifier runs on curated corpora).
2. **Redox by the free-element signature.** An element that is FREE (neutral, one element type) on one side and
   COMBINED on the other necessarily changed oxidation state → electrons moved. This flags exactly the
   families a first course calls redox (combustion, single replacement, element-bearing synthesis/
   decomposition) and never over-claims (a double replacement with no free element is correctly non-redox),
   *without assigning oxidation numbers* (deferred to Phase 2, per the regime-map). It is re-derived in pure
   Node in the gate.
3. **Two curated datasets** (ADR-0006), sourced `openstax-chemistry-2e`, machine-checked on load:
   `data/acids-bases.toml` (each acid = `protons` H + its named anion; each base = cation + |charge| OH — the
   composition is regime-1 verified, the acid/base *identity* + names + strong/weak are regime-3 sourced; the
   names partially close the item-2 acid-naming deferral) and `data/decomposition.toml` (unstable
   intermediates — carbonic acid → CO2 + water, aqueous ammonia → NH3 + water — that make a double replacement
   a gas evolution). Loaded by `chemkernel.reactivity` (`AcidBase`/`Decomposition`, mirroring `Solubility`);
   injected into the classifier so `reaction.py` imports neither (it would cycle through `solubility`).
4. **The reaction-family Atlas kind** (`schemas/reaction-family.schema.json`, `kind: "reaction-family"`):
   general form + conditions + misconceptions + **3–5 machine-verified example reactions**. `reference.
   build_reaction_family` balances each example with the engine and classifies it, and **refuses to emit an
   example that does not classify as the entry's declared family** — so the family label is proven, not
   asserted. Each example emits its balanced equation, the classifier's evidence + redox flag, and — where
   spectators actually cancel — the **net-ionic particle view** (reusing `complete_ionic`/`net_ionic`);
   combustion/synthesis/decomposition omit it rather than fake one. A family-level `redox` flag is emitted
   only when every example agrees (omitted for mixed families like decomposition). `prose_tokens` (species ∪
   author-declared intermediates like H2CO3) drive the view's ADR-0025 subscripting.
5. **The gate re-proves the arithmetic-checkable claims in pure Node.** `verifyBalance` was extracted from
   `validate-gyms` into a shared `scripts/validate/balancecheck.mjs` (+ a `redoxFreeElements` re-derivation);
   `validate-reference` dispatches the new kind, re-parses + re-balances every example (element + charge
   conservation, reduced, positive), re-derives the redox flag from the free-element signature and matches the
   emitted value, and enforces family-label consistency. Uniqueness/classification stays Python's (the
   producer refuses a mis-filed example); the gate re-derives balance + redox and cross-checks the labels.
   `check-katex` was extended to render every reaction-family LaTeX (equation, net-ionic, species, general
   form). The player gets `reference/reactions.astro` (all families, jump-nav, net-ionic views, redox badges)
   + a card on the Atlas index.

**Consequences.** The Atlas gains 7 reaction families / 21 machine-verified example reactions — the
regime-map "reaction classes" row goes from atlas-thin (concept stubs) to a full family gallery, and every
"this is family X" / "this is redox" claim is re-proven in CI. `chempy` independently balances the whole
corpus (ADR-0026). The classifier is the shared instrument items 6c (the `reaction_families_v1` gym) and 6d
(the acid-base neutralization lesson) build on. **Deferred:** full oxidation-number assignment (a Phase-2
redox topic — this ships the free-element signature only); a generic double-replacement Atlas entry (a
no-driving-force ion swap is not a real reaction to teach); further gas-forming intermediates (sulfurous acid
needs the sulfite ion curated).

## ADR-0036 — reaction_families_v1: classify-the-family + name-the-spectators, engine-classified (2026-07-08)

**Context.** Item 6's gym (brief §10.4, ROADMAP): *given a reaction → classify its family / predict products
/ name the spectators*. It reuses the ADR-0035 classifier (the gym template, ADR-0024: a generator + a
`validate-gyms` branch, no new plumbing). Reaction-family answers are categorical (a family label, an ion
set), so the ADR-0032 menu is honest. Two honesty questions: (1) the family label must be the *engine's*
classification, not an authored guess; (2) the gym's equations and net-ionic forms must be real (balanced +
conserving).

**Decision.** A `reaction_families_v1` family, two kinds, both `mode: "choice"` (ADR-0032):
1. **`classify_family`** — a balanced equation → its family. The reaction is **balanced by `balance()` and
   classified by `classify_reaction`** at generation (never an authored label); distractors are other
   specific families, each carrying a **definitional** misconception (what that family *would* require) so the
   gym never makes a false claim about the specific reaction, and never the parent "double replacement" of a
   precip/acid-base/gas sub-type (which would be ambiguous). The explanation is the classifier's evidence +
   redox reason.
2. **`name_spectators`** — a reaction with a net-ionic form → its spectator ions. Generated via
   `complete_ionic`/`net_ionic`; distractors are **over-inclusion** (spectators + one reacting ion) and the
   **reacting ions themselves** (the opposite of spectators), each named.
The gate (`validate-gyms`, via the shared `balancecheck.mjs`) re-proves the **molecular** balance and, for
spectators, the **net-ionic** balance (atoms + charge), and checks every claimed spectator is **absent from
the net equation** — a spectator, by definition, cancels. The family label and spectator set rest on the
tested Python classifier/`net_ionic` (as the ADR-0035 Atlas gate does); the gate re-derives the
balance-checkable claims + the spectator invariant. Provenance carries the classification source id
(`reaction_classes` → openstax-chemistry-2e). The gym drill island renders it with **zero new plumbing**
(choice mode, no chain); the gym page's sourced-data badge became reaction-family-aware, and the concept
chips resolve reaction-family ids to the reactions Atlas page.

**Consequences.** Gym family #8; the corpus spans all the families, cross-linked to the reaction-family
Atlas. `gym.schema.json` grows the two kinds + a `family`/`net_species`/`net_coefficients`/`spectators`
derivation shape + the `reaction_classes` provenance key. A subscript-token fix (phase-stripped cores) keeps
the classifier's evidence prose typographically consistent with the phased prompt. **Deferred:**
predict-products drills (honest product-distractor generation needs a careful crossover-mistake generator —
a follow-up), and a redox yes/no kind (thin as a 2-choice menu; the classify explanations already teach it).

## ADR-0037 — Acid-base neutralization lesson: generalize the emitters past a solid precipitate (2026-07-08)

**Context.** Item 6's flagship is the first non-precipitation lesson (brief §10.4): acid-base neutralization
(acid + base → salt + water). The Phase-0 lesson pipeline (`build.py`, `interactive.py`, `practice.py`) was
built for single-precipitate double-displacement — it hard-required a *solid* product to report a mass, drive
the beaker/extent sliders, and generate practice. A neutralization has no solid: the net-ionic product is
**water** (H⁺ + OH⁻ → H₂O), and the salt is entirely spectator ions. The owner chose the full lesson (sliders
+ practice), not a static one.

**Decision.** The reaction shape is structurally the same as precipitation — two solutions, two reacting ions,
one net-ionic product, two spectators — so the generalization is small and surgical, not a rewrite:
1. **The reported product is the net-ionic product** (the single species on the right of the net ionic), of
   *any* phase — a solid precipitate, or water. `build.py` emits `result.precipitate` for a solid (precipitation
   lessons stay **byte-identical**) and the general `result.product` otherwise, plus `result.salt` naming the
   dissolved ionic product. `interactive.py` drops its "must be solid" guard (one line) and emits the product's
   real phase — the ADR-0022 closed forms, engine-sampled parity, and limiting-reagent switch all work
   unchanged because they were always net-ionic-level (the switch here is H⁺ vs OH⁻). `practice.py` takes a
   `family` + `product_noun` so precipitation prose is preserved verbatim.
2. **No solubility claim.** A neutralization is ledger-exact + model-exact (complete dissociation), never
   rule-sourced — so its `regimes` omit solubility, its provenance omits the solubility source, and it carries
   no `solubility_basis`. The schema made `result.precipitate` and `provenance.sources.solubility` optional
   (a `reportedProduct` `$def` shared by precipitate/product/salt). Percent yield stays a gravimetric-
   precipitation concept — refused for a non-solid product.
3. **The player renders the general product.** `SolutionPlayer` shows "Mass of H₂O formed" + a salt card, and
   **gates the Beaker tab on a solid product** (watching a solid settle out is meaningless for water) — the
   ExtentBar (the limiting-reagent switch) carries the interactivity. `ExtentBar`'s label generalized
   ("product mass tracks ξ"). The three gates read `result.precipitate ?? result.product`; `check-ledger`
   additionally re-derives every reported product's mass = moles × M.

**Consequences.** Four lessons now (2 precipitation + 1 percent-yield + 1 neutralization) — the first
non-precipitation shape, with the honest limiting-reagent slider and generated practice, in-browser verified
(the switch flips OH⁻→H⁺ as NaOH concentration rises). The `result.product`/`salt` blocks + the phase-general
interactive are the template for any future two-solution reaction. The regime-map "reaction classes" and the
Phase-1 "acid-base" coverage are now lesson-backed. **Deferred:** a gas-evolution *lesson* (a (g) product
leaves the solution — the ledger closes the same way, but the "product" is a gas whose mass isn't the
headline); the diprotic coefficient-story neutralization (H₂SO₄ + 2 NaOH — the machinery handles it; it is a
second lesson, not new code).

## ADR-0038 — Species atlas entry kind; reaction-family cross-links restored (2026-07-08)

**Context.** Session-map #8, the Atlas breadth audit — the last Phase-1 work before the definition-of-done
gate. The brief's §10 Atlas has four entry kinds; three shipped (periodic lens, concepts, reaction families),
leaving the **species entry**. And the Phase-1 DoD requires every Phase-0/1 regime-map row to show coverage;
one row was still empty — *atoms, isotopes, average atomic mass*. Two honesty questions for a species entry:
(1) what part is machine-checked vs authored, and (2) how a gate re-proves it without trusting Python. The
audit also surfaced a latent defect: the item-6 reaction families shipped with **empty `related`/`lessons`**
— trap #4 (bare keys authored after an array-of-tables header get absorbed into the last table).

**Decision.**
1. **The `species` Atlas kind (`schemas/species.schema.json`, `build_species_entry`).** A species entry's
   **composition (per-element count + sourced atomic weight + subtotal), signed charge, and molar mass are
   DERIVED** by the producer from the authored phase-less `formula` — re-parsed by the grammar-v0 parser, the
   weights summed from `data/` (regime-1 arithmetic over regime-3 CIAAW data). Names, typical phase, and prose
   are **authored + labeled** (the page shows a machine-checked badge on the composition block and a
   data-sourced badge for the weights). The producer refuses an off-dataset element, a class↔charge mismatch
   (element/compound must be neutral; either ion class must be charged), a multi-element "monatomic-ion", or a
   phase baked into the formula. `validate-reference` **re-parses the formula in pure Node** (`formula.mjs` —
   composition + charge must reproduce), re-derives the molar mass by re-summing the **Valence Table's** sourced
   weights (an element with no table weight fails — every species weight is sourced), and re-checks the
   class/charge agreement + edge/lesson/reaction resolution. `check-katex` renders the species symbol +
   inline prose math. 14 curated species land — 10 compounds, 2 elemental molecules (O₂/H₂ — the atoms-vs-
   molecule distinction the periodic lens can't show), 2 polyatomic ions — each cross-linked to the lessons,
   reaction families, and concepts it appears in.
2. **The atoms row filled.** An `atomic-mass` concept (average atomic mass = the abundance-weighted mean of
   isotope masses, $\bar{A} = \sum_i f_i A_i$ — exact arithmetic over sourced CIAAW abundances) fills the last
   empty Phase-0/1 regime-map row with atlas coverage. No new source (the CIAAW standard atomic weight *is*
   that average). A drillable average-atomic-mass gym is deferred — it needs per-isotope data curated.
3. **Trap-#4 fix + guard.** All 7 reaction-family TOMLs had `related`/`lessons` authored after their
   `[[examples]]` headers, so TOML absorbed them and the families shipped with empty cross-links. Fixed by
   moving those bare keys ahead of the first array-of-tables header (and correcting a topic/slug lesson value
   to the bare slug the gate expects). `build_reaction_family` now **rejects an example or misconception that
   carries an unexpected key** — the fingerprint of an absorbed bare key — so this can never ship silently
   again.

**Consequences.** The Atlas now carries **all four brief-§10 entry kinds** and every Phase-0/1 regime-map row
shows coverage — the two structural Phase-1 DoD criteria. `validate-reference` re-proves every species' molar
mass and composition in CI (8-way tamper-tested); the 7 reaction families regained their concept/lesson
cross-links (rendered). Counters: **20 concepts + 14 species** (species is a new derived shape; +15 derived
files). **Deferred:** the formula/equation sheet (the fourth-and-a-half kind — brief-§10; mostly model-bearing,
opens with Phase 2 per the DoD); monatomic-ion species entries (the ion table + Valence Table cover them; the
schema permits the class); the average-atomic-mass gym (needs isotope-abundance data). Phase 1 is now
**complete pending owner review** — the review gate before Phase 2 (the owner's to open).

## ADR-0039 — Open Phase 2; the formula/equation-sheet Atlas kind, verified by dimensional homogeneity (2026-07-08)

**Context.** The owner opened **Phase 2** — the model-bearing tier (brief §17 items 7–10: gases +
thermochemistry, bonding, equilibrium/acid-base, kinetics/electrochemistry). Per the project's phase protocol
(ROADMAP: open with the reusable instrument, then fill depth-first), Phase 2 opens on **gases + thermochemistry**
(brief item 7) by landing the **formula/equation-sheet Atlas kind** — the fourth brief-§10 kind, deferred through
Phase 1 as "mostly model-bearing, opens with Phase 2" (ADR-0038). Three questions had to be answered together:
(1) what is the honesty model for a *reference relation* — most of the sheet (PV=nRT, q=mcΔT) is regime-2
(model-exact), which the machine cannot prove true; (2) architecture Q's ADR-0015 deferred "symbolic dimensional
homogeneity of reference formulas … adapt the sibling's SymPy `dims.py` when the formula sheet lands" — do we; and
(3) the sheet needs new dimensions (pressure, temperature, energy) ADR-0015 deferred "to gases/thermo".

**Decision.**
1. **The honesty model for a formula entry is machine-checked DIMENSIONAL HOMOGENEITY, not a proof of the
   relation.** Each entry is a set of `terms` (monomials over the variables, one per side / addend); a relation is
   admissible iff **every term reduces to one SI dimension vector**. The producer computes each term's dimension
   from the variables' units and **refuses to emit** a non-homogeneous relation (ADR-0008). We do NOT claim the
   relation is true: a **model-exact** entry carries the **model-assumed badge and MUST disclose an assumption**
   (the producer refuses otherwise); a **ledger-exact** entry (n=m/M, definitional) carries the machine-checked
   badge. Dimensional consistency is what we prove; the model is what we disclose — the three-badge honesty model
   (ADR-0003) stands, no new badge.
2. **A native integer-vector dimension engine (`chemkernel.dimension`), NOT SymPy `dims.py`** — a
   chemistry-motivated divergence (ADR-0001). First-course relations are monomials/sums-of-monomials, so
   homogeneity is plain integer-vector arithmetic; the payoff is **pure-Node re-derivation parity** — the producer
   emits each variable's dimension vector + each term's factor powers, and `validate-reference.mjs` (via a shared
   `scripts/validate/dimension.mjs` mirroring the Python table) **re-computes every term's dimension and re-checks
   equality**, the ADR-0028 "emit the matrix, re-tally in Node" pattern. The unit→dimension table is *definitional*
   (the dimension of "atm" is SI structure, not an empirical value), so it lives in code, not `data/` — and the
   Decimal units engine (`units.py`, amount/mass/volume, for numeric conversion) stays **separate** from this SI
   dimension engine, exactly as ADR-0015 required ("the two needs are not conflated"). Base order is the fixed
   6-vector `[mass, length, time, amount, temperature, current]` (luminous dropped; current 0 until electrochem).
3. **The `formula` Atlas kind** (`schemas/formula.schema.json`, `reference.build_formula_entry`): id/name/statement
   (LaTeX) + `variables` (symbol, meaning, unit, derived dimension, optional threaded constant) + `terms` (factors +
   derived dimension) + the common `dimension`/`dimension_name` + `assumptions`/`domain`/`rearrangements`/`summary` +
   `related`/`lessons`. A sourced constant (R, N_A) is **threaded from `data/constants.toml`** — value + unit +
   source — never hard-coded; `data.py` now carries each constant's unit. The **gas constant R** is registered
   (`data/constants.toml`, `bipm-si-2019` — R = N_A·k_B, exact in SI; the L·atm/(mol·K) teaching value is that exact
   value unit-converted). `validate-reference` re-derives homogeneity + resolves edges/lessons/sources; `check-katex`
   renders the statement + rearrangements + inline math. Player: `reference/formulas.astro` (grouped teaching order,
   the dimensional-check line, variable tables, disclosed assumptions) + an Atlas-index card + `view.renderFormula`.
4. **The first sheet: 8 entries** — 5 ledger-exact backfilling Phase-0/1 (mole–mass, molarity, dilution,
   Avogadro's-number, percent yield) + 3 model-exact opening the gas/thermo tier (ideal gas law, combined gas law,
   calorimetry). Two constants threaded (N_A, R).

**Consequences.** The Atlas now carries all four brief-§10 kinds. The formula sheet is the reference backbone the
Phase-2 gym/lesson increments link to, and dimensional homogeneity is the honesty pattern for every future
model-exact relation. `validate-reference` = **50 objects** (was 42); check-katex +42 strings; `dimension.py` +
`dimension.mjs` are the shared engine (7-way tamper-tested: term/variable/total-dimension corruption, forced
non-homogeneity, empty model assumption, dangling edge, unregistered source — each caught). **Deferred:** the
numeric gas-law **computation** (the `units.py` pressure/temperature/energy extension + a `gas_laws_v1` gym) and a
gas-stoichiometry **lesson** are the next Phase-2 increments; specific-heat / thermodynamic-table data curate when a
calorimetry gym/lesson needs values; further sheet entries (Hess's law, pH, K, ΔG, Nernst) land with their topics.

## ADR-0040 — Gas-laws gym: the units engine gains pressure/temperature; the first model-exact-then-rounded numeric answer (2026-07-08)

**Context.** The second Phase-2 increment: the practice instrument for gases — a `gas_laws_v1` gym over PV=nRT and
the combined gas law, the reusable-instrument half of the gas/thermo opener (the formula sheet, ADR-0039, is the
reference half). Three things Phase-1's gym families never had to face: (1) the units engine (`units.py`) had
**no pressure or temperature dimension** — ADR-0015 deferred them "to gases … add basis components then"; (2)
the answer **cannot be an exact terminating decimal** — the gas constant R is non-terminating — so the Phase-1
"reject any non-terminating candidate, emit the exact value" contract (ADR-0013/0024) does not apply; (3) the
ideal-gas law is **regime-2 (model-exact)**, not ledger-exact, so the model must be disclosed (ADR-0003).

**Decision.**
1. **Extend the units engine with `pressure` and `temperature` basis components** (`Dim` grows from 3 fields to
   5; ADR-0015's deferred extension). Registered units: `atm`, `K`, and the molar gas constant's composite unit
   `L*atm/(mol*K)`. The gym computes every answer **through the units engine** — `(n·R·T / P).to("L")` — so the
   dimensions are *certified* (mol·L·atm·mol⁻¹·K⁻¹·K / atm → L) exactly as the conversion gym certifies
   L × mol/L = mol, and the answer value falls out of the same Decimal arithmetic. Temperature is **absolute
   (kelvin) only** — a multiplicative basis; **°C is NOT a units-registry entry** (it is an affine, not a ratio,
   scale). A °C given is converted at the boundary in the generator (K = °C + 273.15), shown as a chain step, and
   **forgetting it is the canonical named diagnostic**. Energy/charge dimensions still wait (thermo/electrochem).
2. **The first model-exact-then-rounded numeric answer.** A gas-law answer is computed at Decimal precision, then
   **reported ROUNDED** — `answer.display` at 3 significant figures (ADR-0025), `answer.value` at 4 (the value the
   player checks a free entry against, 1% tolerance). The Node gate **re-derives PV=nRT (or the combined law)
   numerically** from the emitted state + R and accepts it within **0.5%** — comfortably above the 4-sig-fig
   rounding (~0.05%) and below the ADR-0032 3% diagnostic gap. This is not a weakening of ADR-0013 (which governs
   *ledger* exactness): a gas-law result is a rounded physical quantity by nature, and the honest move is to round
   it and re-prove it consistent with the law, not to fake exactness. Free entry + named diagnostics (ADR-0032)
   carry over unchanged — the two robust diagnostics never collapse onto the answer: the **wrong R** (8.314 SI
   J-units instead of 0.08206 L·atm) and, when applicable, the **unconverted °C**.
3. **The problems are generated CONSISTENT and realistic.** A base state is built (n, P, T chosen; V computed from
   PV=nRT and shown at 3 sig figs), then one variable is hidden and re-solved from the *emitted* givens — so the
   answer both re-derives from what the student sees and is always physical (no 1.5 K or 16 800 K artifacts).
4. **The gym discloses its model.** A `gas_laws_v1` gym carries a top-level `assumptions` block (the ideal-gas
   model) rendered under the **model-assumed (amber) badge** on the gym page — the three-badge honesty model
   applied to a gym for the first time; the sourced R travels in provenance (`constants` → bipm-si-2019). Added
   only for model-bearing families, so the Phase-1 gyms' derived JSON stays byte-identical.

**Consequences.** Gym family #9 (`gas_ideal` + `gas_combined`, 10 drills); the drill island renders it with a
gas-aware chain caption and **zero new interaction plumbing** (the free-entry numeric path from ADR-0032). The
`gas.schema.json` derivation shape + a `verifyGasLaw` Node branch land per the ADR-0024 template. Gate:
**validate-gyms = 9 gyms / 90 problems**; the gas branch is **5-way tamper-tested** (corrupt answer / corrupt a
state value / wrong R / a gameable menu / a too-close diagnostic — each caught). 262 producer tests (+7); 22 pages
(+1: `/gym/gas-laws/`); `derived/` byte-stable (only the new gym added). In-browser: the model-assumed badge +
disclosure render, a correct entry is accepted, the wrong-R entry is named, the concept chips resolve to the
formula-sheet entries. This is the template for every future regime-2 gym (equilibrium, kinetics). **Deferred:**
`kPa`/`torr` and °C *display* niceties; the gas-stoichiometry **lesson** (the ledger drives a gas volume — needs
`build.py` generalised past two-solution double-displacement) is the next increment; particle-count (moles↔particles)
drills now have both prerequisites (Avogadro datum + this numeric-rounding pattern) but still want scientific notation.

## ADR-0041 — Gas-stoichiometry lesson: the ledger drives a gas volume; weighed-mass givens; the gas result block (2026-07-08)

**Context.** The Phase-2 vertical slice (brief §17.7): a lesson where **the extent ledger drives a gas volume** —
a weighed metal + an acid react (single replacement), the ledger fixes the moles of hydrogen, and PV=nRT turns
those moles into the volume you would collect. It is the lesson counterpart to the `gas_laws_v1` gym (ADR-0040)
and the ideal-gas formula-sheet entry (ADR-0039). Three things every prior lesson (precipitation, percent yield,
neutralization — all ADR-0037's two-solution double-displacement) never had to face: (1) a reactant given as a
**weighed mass** (grams), not a solution volume × molarity; (2) the reported product is a **gas whose headline is
its VOLUME**, not a mass — and that volume is **model-exact** (ideal gas), not ledger-exact; (3) a **free-element**
reactant (Zn metal), which the solubility phase-check cannot dissociate.

**Decision.** Generalise `build.py` — one machine, a third reported-product shape — without disturbing the two-
solution lessons (their `derived/` stays byte-identical):
1. **A weighed-mass given.** `_moles_and_chain` gains a `mass_g` branch: grams ÷ molar mass → moles, run through
   the units engine so the dimension is certified (g ÷ g/mol → mol), emitting a two-step g→mol dimensional chain.
   The result must still land on a **terminating decimal** (ADR-0013) — so the authored mass is chosen to give
   clean moles (3.269 g Zn = 0.0500 mol exactly); a mass that made moles non-terminating would fail the build,
   the honest guard against a silently rounded ledger amount.
2. **The gas result block (`result.gas`) — the payoff.** When a spec carries a `[conditions]` block (pressure +
   temperature + the collected `gas_species`), the reported product is that gas, and `result.gas` adds its
   **volume via PV=nRT**, computed **through the units engine** (`(n·R·T/P).to("L")` — the same certified path the
   gas gym uses) from the ledger's exact moles + the **sourced** gas constant R (`data/constants.toml`, never
   hard-coded). Honesty is layered, not mixed: the moles are **ledger-exact** (machine-checked, the reported
   product is a normal product ledger row re-verified by check-ledger); the **volume is model-exact-then-rounded**
   (ADR-0040 — R is non-terminating; `volume_L` at 4 sig figs, `volume_L_display` at 3) and carries the
   **model-assumed badge** with a disclosed ideal-gas assumption. °C→K is the affine boundary conversion (ADR-0040).
   The block also emits `molar_volume_L_per_mol` (RT/P) so the player can name the **22.4-L-at-STP misconception**
   (the canonical gas-volume error) against the actual RT/P at the stated conditions.
3. **Free elements skip the solubility phase-check.** The ruleset classifies ionic *compounds*; a free element
   (single element type, neutral — Zn(s), H₂(g)) has no solubility verdict, so it is skipped. Only a genuine
   *multi-element* neutral (aq)/(s) salt that fails to classify remains a build error.

**Consequences.** The 5th lesson (`gas-stoichiometry/zinc-hydrochloric-hydrogen`, Zn + 2 HCl → ZnCl₂ + H₂): three
equations, the ledger (Zn limits, HCl left over), three dimensional chains (**g→mol**, mL→mol, **mol→L via
PV=nRT**), the gas-volume card + the molar-volume/22.4-L contrast, the dissolved salt, and the misconception
refuted with the verified gas numbers. Schema growth (additive): `result.gas`; a `constants` provenance source;
`given.mass_g` (already permitted). Gates: **check-ledger re-derives V=nRT/P** numerically (0.5% tol) + the °C→K
boundary; **validate-solutions** ties `result.gas` to a model-exact regime + a disclosed model assumption + the
sourced constant. Both branches **6-way tamper-tested** (corrupt volume / break °C→K / corrupt moles / bake in the
22.4 molar-volume / drop the model-exact regime / drop the constants source — each caught). The lesson page's
concept chips now **route by the target entry's kind** (concept / reaction-family / species / formula), so all 16
links resolve — a fix that lights up prior lessons' reaction/formula links too. 264 producer tests (+2); 23 pages
(+1); `derived/` byte-stable (only the new lesson added; no existing solution changed — the regime default is
pinned to its original three facets so adding the `gas_behavior` facet shifts nothing).

**Second increment (same session) — generated practice.** The gas lesson earns a 6-variant practice set (free-entry
**volume** via PV=nRT + **leftover**, categorical **limiting reagent**) without an interactive block: the
single-replacement shape has no cation/anion closed forms, so the reaction constants (metal molar mass +
coefficients, R, T, P) travel in a `practice.gas` block and **check-parity re-derives every answer in pure Node**
from the emitted args (metal mass, acid volume/molarity) — decoupling practice from the interactive for the first
time. The volume distractors are the 22.4-L-at-STP slip + sizing from the excess reactant; the metal-mole/acid grids
are tuned so the limiting reagent genuinely switches. Reuses the generic free-entry `PracticeQuestion` island (no new
frontend); the gas-practice branch is 6-way tamper-tested. Schema: a `practice.gas` block, a `volume` question kind,
and `practice.given` relaxed to allow a `mass_g` given (species-only required). **Deferred (a follow-on increment):**
the gas-stoichiometry **slider interactive** (mass + volume + molarity sliders → the gas volume, parity-verified —
`ExtentBar` is cation/anion-locked, so it needs its own component); collecting the gas **over water** (subtract the
water-vapor pressure — needs a curated vapor-pressure table); `kPa`/`torr` units.

## ADR-0042 — Calorimetry gym: the units engine gains an energy dimension; a gym with both the data-sourced and model-assumed badges (2026-07-08)

**Context.** The thermochemistry opener (brief §17.7) — the energy ledger's first rung, $q = mc\Delta T$. Like the
gas-laws gym (ADR-0040) it is the reusable *instrument* half of a tier (the `formula-calorimetry` sheet entry,
ADR-0039, is the reference half). Two things it needs that no prior gym had: (1) the units engine (`units.py`) has
**no energy dimension** — ADR-0040 deferred energy "when thermochemistry needs them"; (2) the specific heat is an
**empirical, measured** value (regime-3, data-sourced) *as well as* the relation being model-exact (regime-2) — so
the gym must carry **two** honesty badges at once, a first.

**Decision.**
1. **Extend the units engine with an `energy` basis component** (`Dim` grows to 6 fields; ADR-0040's deferred
   extension). Registered units: `J`, `kJ`, and the specific-heat unit `J/(g*K)`. Every answer is computed
   **through** the units engine — $q = (m \cdot c \cdot \Delta T)$, `.to("J")` — so the dimensions are certified
   (g × J·g⁻¹·K⁻¹ × K → J) exactly as the gas gym certifies the ideal-gas product. **Energy is kept INDEPENDENT
   of pressure·volume** in this basis: it is a chemistry-bookkeeping engine, not a physics-equivalence engine, so
   a gas-law product stays in L·atm and a calorimetry heat stays in J — the two never silently equate. $\Delta T$
   rides the **temperature** basis as a *difference* (a change of 1 °C equals a change of 1 K), so the prompt shows
   °C and the machine uses K with no offset — distinct from the gas law's *absolute* kelvin (ADR-0040).
2. **A gym with both the data-sourced and model-assumed badges.** The specific heat is a curated, sourced datum
   (`data/specific-heats.toml`, OpenStax Table 5.1 — water 4.184 down to gold 0.129 J/(g·°C)); the gym's provenance
   carries its source (`specific_heats`), rendered as the **data/rule-sourced** badge ("specific heats sourced …").
   Simultaneously the relation is exact only inside the **calorimetry model** (no heat loss, constant $c$, no phase
   change), disclosed in the `assumptions` block under the **model-assumed** badge (ADR-0040's mechanism). This is
   the first object to wear both badges — the honest picture of a model computation over an empirical constant.
3. **Model-exact-then-rounded, solving for any variable.** $q/m/c/\Delta T$: a consistent state is generated
   (m, ΔT chosen, the sourced c, q computed) and one variable hidden and re-solved from the *emitted* givens; the
   answer is reported to 3 sig figs (a specific heat carries only so many figures) and the Node gate re-derives
   $q = mc\Delta T$ within 0.5%. Solving **for c** is the "identify the substance" experiment — the answer is the
   tabulated value, machine-confirmed. Named diagnostics (ADR-0032): using **another substance's specific heat**
   (treating everything like water — the canonical calorimetry error, robust for q/m/ΔT) and **dropping a factor**.

**Consequences.** Gym family #10 (`calorimetry`, 10 drills). `units.py` `Dim` → 6 fields; `data.py` loads the new
dataset (`ChemData.specific_heats`, a `specific_heats` source key); `gym.py` gains `_calorimetry_problem`/
`_generate_calorimetry` + the family assumptions; `gym.schema.json` a `calorimetry` derivation shape + the
`specific_heats` source key; `validate-gyms.mjs` a `verifyCalorimetry` branch (4-way tamper-tested — corrupt answer /
corrupt a derivation input / a gameable menu / a too-close diagnostic, each caught). The gym page renders the
specific-heats source badge; the drill island a calorimetry chain caption. **validate-gyms = 10 gyms / 100 problems**;
271 producer tests (+7); 24 pages (+1: `/gym/calorimetry/`); `derived/` byte-stable (only the new gym added). This is
the thermochemistry instrument the **energy-ledger lesson** ($\Delta H_\text{rxn}\cdot\xi$, the next increment) builds
on. **Deferred:** initial/final-temperature framing ($\Delta T = T_f - T_i$) + cooling (negative $q$) as distinct
drills; heat of reaction / Hess's law; the energy ledger attaching $\Delta H$ to extent.

## ADR-0043 — Energy-ledger lesson: reaction enthalpy attached to extent (q = ΔH_rxn·ξ) via Hess's law; the first fully molecular lesson (2026-07-08)

**Context.** The thermochemistry vertical slice (brief §17.7) and the flagged next increment after the calorimetry
gym (ADR-0042): a lesson where **the extent ledger drives an energy** — the ledger fixes ξ (moles of reaction,
capped by the limiting reagent), and the heat released is $q = \Delta H_\text{rxn}\cdot\xi$. It is the energy
counterpart to the gas-stoichiometry lesson (ADR-0041, where the ledger drove a *volume*). The canonical teaching
reaction is **methane combustion** ($\mathrm{CH_4(g) + 2\,O_2(g) \to CO_2(g) + 2\,H_2O(l)}$) — but it is the first
lesson that is **fully molecular** (no ions in solution) and the first where the headline is neither a mass nor a
volume but an **energy**, and where $\Delta H_\text{rxn}$ itself must be *derived*, not authored, to stay honest.
Three problems no prior lesson faced: (1) a molecular reaction dissociates nothing, so its complete/net-ionic views
would just echo the molecular equation — dishonest to present as "ionic equations"; (2) combustion has **two
products** (CO₂ + H₂O), breaking the single-reported-product assumption of every prior lesson; (3) $\Delta H_\text{rxn}$
is a claim — asserting it would violate ADR-0008.

**Decision.** Generalise `build.py` — one machine, a fourth reported-product shape (an **energy** headline) — without
disturbing the aqueous lessons (their `derived/` stays byte-identical):
1. **Hess's law over a sourced ΔH_f° table, exact arithmetic.** A new curated dataset
   `data/formation-enthalpies.toml` (standard enthalpies of formation, OpenStax *Chemistry 2e* Appendix G, keyed by
   formula **and phase** because H₂O(l) −285.83 ≠ H₂O(g) −241.82). The producer derives
   $\Delta H_\text{rxn} = \sum_\text{prod}\nu\,\Delta H_f^\circ - \sum_\text{react}\nu\,\Delta H_f^\circ$ — **exact
   Decimal arithmetic over the sourced values** (like average atomic mass, ADR-0038: exact over sourced data), and
   refuses to emit if any species' ΔH_f° is missing (never guesses). An element in its standard state is
   ΔH_f° = 0 **by definition** (the reference level, flagged `is_element` so the page can say so). The emitted
   `result.energy.hess` breakdown carries each species' role/coeff/phase/ΔH_f°/signed contribution so the gate
   re-sums it in pure Node.
2. **The energy result block (`result.energy`) — the payoff.** A spec with an `[energetics]` block (marker;
   `method = "hess-formation"`) reports the **heat** $q = \Delta H_\text{rxn}\cdot\xi$, computed **through the units
   engine** (`kJ·mol⁻¹ × mol → kJ`, dimension certified — `units.py` gains `kJ/mol`/`J/mol`, energy·amount⁻¹) from
   the ledger's exact ξ. **There is no reported product mass** — the energy is the headline; the products are just
   ledger rows (the ledger tab shows their amounts). Honesty is **triple-layered, not mixed**: ξ is **ledger-exact**
   (machine-checked); the ΔH_f° are **data-sourced** (regime-3, the data/rule-sourced badge); the **relations**
   (Hess's law needs enthalpy to be a state function; $q = \Delta H_\text{rxn}\cdot\xi$ needs completion at constant
   P, standard-state ΔH_f°) are **model-assumed** (regime-2, the model-assumed badge). $q$ is **EXACT** here (all
   inputs terminate — a Decimal sum × a terminating ξ), reported at 3 sig figs for display — **distinct** from the
   gas volume's *model-exact-then-rounded* (ADR-0040, where R is non-terminating): each precision treatment reflects
   the real arithmetic, which is more honest than forcing one rule. New regime facet `thermochemistry → model-exact`.
3. **A fully molecular reaction omits the ionic equations.** When `complete_ionic` produces **no charged term**
   (nothing dissociated), the reaction has no ions in solution, so the complete-ionic and net-ionic views are
   **omitted** (schema `equations.required` relaxed to just `molecular`) rather than echoing the molecular equation —
   the honest representation ("no ions → no ionic equation"), and a real generalisation for the many molecular
   reactions Phase 2 will add. Aqueous lessons (all have charged terms) keep all three, byte-identical.

**Consequences.** The 6th lesson (`thermochemistry/methane-combustion-enthalpy`): three dimensional chains (g→mol ×2,
**ξ→q via ΔH_rxn**), the Hess breakdown table (CH₄ −74.6, O₂ 0 (element), CO₂ −393.51, H₂O −571.66 → **−890.57
kJ/mol**), the heat card **q = −890.57 × 0.05 = −44.5 kJ** (exothermic), and the extent-scaling misconception refuted
in the ledger ("−890.57 kJ is *per mole of reaction*; this burn runs only ξ = 0.05 mol, so it releases −44.5 kJ, not
890.57 kJ"). Schema growth (additive): `result.energy` + a `formation_enthalpies` provenance source; `equations`
complete/net-ionic now optional. Gates: **check-ledger re-derives the Hess sum + q = ΔH_rxn·ξ** (independent of
Python, sign→classification checked); **validate-solutions** ties `result.energy` to a model-exact regime + a
disclosed model assumption + the ΔH_f° source, and forbids a product headline beside it; both **7-way tamper-tested**
(corrupt q / a contribution / ΔH_rxn / flip classification / drop the model regime / drop the source / add a spurious
product — each caught). The lesson is the first object to wear **three** honesty badges at once (machine-checked +
data-sourced + model-assumed), and the first fully molecular one. 275 producer tests (+4); 25 pages (+1); `derived/`
byte-stable (only the new lesson + the `reaction-enthalpy` concept added; no existing solution changed — the ionic
equations stay for every aqueous lesson). **Deferred:** a `formula-enthalpy-of-reaction` / Hess formula-sheet entry
(dimensional homogeneity of $\Delta H_\text{rxn}=\sum\nu\Delta H_f^\circ$); directly-sourced $\Delta H_\text{rxn}$
(a single measured heat of reaction, as an alternative to the Hess sum); endothermic and multi-step (Hess-cycle) lessons.

**Second increment (same session) — generated practice.** The energy lesson earns a 6-variant practice set (free-entry
**heat** q = ΔH_rxn·ξ + **leftover**, categorical **limiting reagent**) with **no interactive block** — the molecular
shape has no cation/anion closed forms, so the reaction constants (each reactant's molar mass + coefficient, and
ΔH_rxn) travel in a `practice.energetics` block and **check-parity re-derives every answer in pure Node** from the
emitted args (the two masses), exactly the ADR-0041 gas-practice pattern (`generate_energy_practice`, a `checkEnergyPractice`
gate branch, a `heat` question kind joining `NUMERIC_KINDS`). The variant grids are stated as **capacities** (mol of
reaction) so the limiting reagent switches regardless of the coefficients; the seed is scanned for a set carrying both
CH₄-limiting and O₂-limiting. The heat diagnostics are the **naive ΔH_rxn-as-total** (forgot ξ — the canonical energy-
ledger error) and **sizing ξ from the excess reactant**. Both reactant masses are emitted at **full precision** (not the
gas practice's 3-decimal rounding — energy varies BOTH masses, so a rounding would compound past the leftover
tolerance; the gas practice rounds only the metal, its acid being an exact volume×molarity). Reuses the generic
free-entry `PracticeQuestion` island (no new frontend); the gas/energy practice are the two families decoupled from an
interactive block. Schema: a `practice.energetics` block + the `heat` kind. **6-way tamper-tested** (corrupt a heat / a
leftover / flip a limiting / corrupt ΔH_rxn / a gameable menu / a too-close diagnostic — each caught). 277 producer
tests (+2); check-parity = 320 + **36** practice answers (+6); `derived/` byte-stable (only the energy lesson's JSON
changed, the practice block added).

**Third increment (same session) — the Hess/enthalpy formula-sheet entry.** The reference backbone the energy lesson
links to: `reference/formulas/enthalpy-of-reaction.toml` (the 9th formula entry, ADR-0039 machinery) — ΔH_rxn =
Σν·ΔH_f°(products) − Σν·ΔH_f°(reactants), **model-exact** (enthalpy is a state function — Hess's law, disclosed), its
**dimensional homogeneity machine-checked**: both sides reduce to **molar energy** (kJ/mol). `dimension.py` already
carried `kJ/mol` → energy·amount⁻¹ (ADR-0039); only the display name "molar energy" was added (to `DIM_NAMES`; the Node
gate re-checks the vector, not the name). The entry discloses the state-function + standard-conditions assumptions,
carries the reverse-reaction sign-flip corollary as a rearrangement, and links to the lesson + the `reaction-enthalpy`
concept + `formula-calorimetry`. `validate-reference` = **52 objects** (was 51); check-katex = **487** (+6); 278 producer
tests (+1); the entry is 4-way tamper-tested (corrupt a term dimension / force non-homogeneity / empty the model
assumption / dangling lesson — each caught). **Deferred** (unchanged): endothermic / multi-step (Hess-cycle) lessons;
the gas lesson's slider interactive; further sheet entries (pH, K, ΔG, Nernst) land with their topics.

## ADR-0044 — Open the bonding & structure tier: the Lewis electron-ledger engine + the `molecule` Atlas kind (2026-07-08)

**Context.** The next Phase-2 tier (brief §17.8, the flagged next increment) is **bonding & structure** — Lewis
structures, VSEPR geometry, molecular polarity, IMFs. It needs its own opener, and the house method opens a tier with
its machine-checkable instrument (as the reaction classifier opened item 6, ADR-0035, and the formula sheet opened
Phase 2, ADR-0039). The question was *what in bonding is machine-checkable* — because "the verification system is the
product," a tier that shipped only sourced/interpretive claims would be off-thesis. The answer sits in the project's
own thesis (AGENTS.md): chemistry is "species accounting **plus electron structure**." The species ledger accounts for
atoms over extent; bonding's core is an **electron ledger** — valence-electron accounting into bonds and lone pairs —
and that accounting is **exact integer arithmetic**: regime-1, machine-checked. The regime map already anticipated this
(the *Lewis structures* row is tagged regimes **1, 4**: ledger-exact accounting + the interpretive model).

**Decision.** Open the tier with the **Lewis electron-ledger engine** (`chemkernel.structure`), exposed first as the
`molecule` Atlas kind (the reference surface a later gym + lesson will link to). Honesty is **layered, not mixed** —
the three badges do distinct work over one molecule:
1. **The electron ledger — machine-checked (regime-1).** The author supplies the connectivity (atoms with lone pairs +
   a bond list — the Lewis *model* is a modeling choice); the engine **derives and verifies** the accounting and
   **refuses to emit** any structure that fails (ADR-0008), exactly as `balance()` refuses a non-balancing reaction:
   (a) **valence total** $V = \sum(\text{group valence electrons}) - \text{charge}$ (the group rule is
   `reference.valence_electrons`, ADR-0033; a d-block atom with no defined count is refused — it can't be Lewis-
   accounted); (b) **electron conservation** $2\cdot\Sigma(\text{bond order}) + 2\cdot\Sigma(\text{lone pairs}) = V$;
   (c) **octet/duet** per atom (H → 2, else 8 — strict; electron-deficient/expanded octets deferred); (d) **formal
   charge** per atom $= V_\text{atom} - 2\,\text{lp} - \Sigma\text{order}$, and $\Sigma\text{FC} = \text{charge}$ (this
   last is implied by conservation — a defensive check). The authored atom multiset must reproduce the formula's
   composition, so the structure is provably *this* molecule.
2. **VSEPR geometry — rule-sourced (regime-3).** The **electron-domain count** (bonded neighbours + lone pairs on the
   central atom) is machine-derived; it **keys a sourced table** `data/vsepr.toml` (OpenStax *Chemistry 2e* §7.6:
   2→linear/180°, 3→trigonal planar/120°, 4→tetrahedral/109.5°, with lone-pair shape variants) for the geometry
   *names* + ideal angle. A domain/lone-pair combination outside the table (expanded octets; the trivially-linear
   4-domain/3-lone-pair diatomic) is refused, not guessed.
3. **Bond ΔEN — data-sourced (regime-3).** Each bond's electronegativity difference is computed from the sourced
   Pauling values and classified against the sourced ΔEN thresholds (`data/bonding.toml`) — the same path the Valence
   Table's bonding mode uses (ADR-0033).
4. **Molecular polarity — model-assumed (regime-2), authored + disclosed.** The polar/nonpolar verdict is a
   dipole-cancellation argument over the geometry; it is **authored with a disclosed reason**, never claimed as a
   machine proof, and stated **only for neutral molecules** (a charged ion carries a net charge, not a molecular
   dipole — polarity is forbidden on ions). The machine-checked bond ΔEN + the sourced geometry *support* it.

**Consequences.** A 6-molecule opening corpus that teaches the tier's core contrasts: **H₂O** (bent, polar) vs **CO₂**
(linear — *polar bonds, nonpolar molecule*, the marquee case); **NH₃** (trigonal pyramidal, polar) and **CH₄**
(tetrahedral, nonpolar); **CH₂O** (trigonal planar, polar — geometry alone doesn't settle polarity, the terminal atoms
must match); **NH₄⁺** (tetrahedral cation — the formal charge **+1 sits on N**, and the formal-charge sum equals the
ion charge, the machine-checked claim for a charged species). Two concepts: `lewis-structure` (ledger-exact — the
electron-ledger anchor) and `vsepr` (rule-sourced). New (additive): `chemkernel.structure`, `schemas/molecule.schema.json`,
`data/vsepr.toml` (a `vsepr` source facet). The molecule Atlas ids are **kind-prefixed `molecule-*`** (as formulas are
`formula-*`, reactions `reaction-*`) so a molecule and its same-named species entry coexist and cross-link (molecule-water
↔ the water species). Gates: **`validate-reference` re-derives the entire electron ledger in pure Node** (valence total,
per-atom octet/formal charge, conservation, domain count) + re-derives bond ΔEN from the table's electronegativities and
re-classifies it — 7-way tamper-tested (corrupt a formal charge / valence total / bond ΔEN / geometry domains /
electron_check / bond class / add polarity to an ion — each caught); `check-katex` gains the molecule branch. The player
gains `/reference/molecules/` (the electron-ledger table, VSEPR shape, per-bond ΔEN, polarity — each under its own
badge) + an Atlas-index card. **293 producer tests** (+15 — `test_structure.py` + a vsepr-load test); **validate-reference
= 60 objects** (+8: 6 molecules + 2 concepts); check-katex = **497**; **26 pages** (+1); `derived/` byte-stable; no
existing derived changed. **Deferred within the tier:** octet exceptions (electron-deficient BeH₂/BF₃, expanded PCl₅/SF₆),
resonance (CO₃²⁻/NO₃⁻ — needs equivalent-structure handling), a `lewis_structures_v1` gym (generated counting drills off
the corpus — valence electrons / formal charge / domain count, the balancing-gym pattern), a bonding & structure lesson
(the deep vertical slice), and IMFs (which build on molecular polarity).

**Second increment (same session) — the `lewis_structures_v1` gym.** The electron ledger earns its drill surface. First
a **pure refactor**: the ledger computation is extracted from `build_molecule_entry` into `structure.compute_ledger`
(byte-identical molecule output verified), so the gym answers come from the SAME engine the Atlas uses — never a
hard-coded count. The gym generates off an 8-molecule skeleton corpus (the 6 Atlas molecules + CCl₄ + PCl₃, for valence
variety) with three kinds: **valence_total** + **electron_domains** are free-entry numeric (ADR-0032) with named
diagnostics (the canonical Lewis mistakes: counting *all* electrons not just valence — the atomic-number sum; forgetting a
lone pair is a domain; treating a double bond as two domains); **molecular_geometry** is a categorical menu whose star
distractor is the **electron-domain geometry** (tetrahedral offered for bent H₂O / pyramidal NH₃ — "lone pairs are
invisible in the named shape"), plus the bonds-only shape (ignoring lone pairs). The gate re-derives valence (Σ group
electrons − charge, from `valence-table.json`) + the domain count in pure Node; a molecule with all single bonds and no
lone pairs on the centre yields no named numeric trap, so it's skipped (rotation fills from the rest). Regime-1
(machine-checked counting) — no model badge; the sourced badge names the IUPAC group positions + the VSEPR table. 298
producer tests (+5); **validate-gyms = 11 gyms / 110 problems** (+1/+10); 27 pages (+1); `derived/` byte-stable (only the
new gym; the refactor left the molecule JSONs byte-identical). 6-way tamper-tested (corrupt a valence/domains answer / a
geometry shape / the central lone-pair count / a numeric-question menu / a too-close diagnostic — each caught). A design
note: the electron-domain **count** is bond-order-independent (a multiple bond is one domain), so the gym gate correctly
does not depend on bond order.

## ADR-0045 — The `structure` lesson kind: the electron ledger's presentation shape over a single molecule (2026-07-08)

**Context.** The bonding tier had its engine (`compute_ledger`, ADR-0044), its reference surface (the `molecule` Atlas
kind), and its drill surface (the `lewis_structures_v1` gym). The flagged next increment was the tier's **deep vertical
slice — a bonding & structure lesson**: a molecule stepped from valence electrons → Lewis structure → VSEPR shape →
polarity, with the misconception register. Every prior lesson is a *reaction*: `solution.schema.json` (ADR-0020) requires
`equations.molecular`, a species `ledger` over extent, and a reported `result` (precipitate/product/gas/energy). A
single-molecule lesson has **none** of those — no reactants, no extent, no product. The question was how to represent it
without weakening the reaction schema that guards the six reaction lessons.

**Decision.** A **new, tight `structure` lesson kind** — its own `schemas/structure-lesson.schema.json`, its own builder
`structure.build_structure_lesson`, emitting `derived/<topic>/<slug>.structure.json` — rather than bending
`solution.schema.json` into a discriminated union (which would force `equations`/`ledger`/`result` optional and branch
every reaction-shaped gate + player). This mirrors the house pattern: a genuinely new object shape gets a new tight schema
(as reaction-family/species/formula/molecule each did), and the reaction schema stays pristine ("every `solution.json` is
a verified reaction"). Design specifics:
1. **The pivot is the Lewis ELECTRON ledger, not a species ledger.** The lesson names a `molecule` Atlas entry by id and
   **reuses its authored connectivity** (one source of truth — the lesson can never describe a different structure than
   the Atlas); the ledger is re-derived by the SAME `compute_ledger` engine the Atlas builder and the gym use (no
   hard-coded counts). The producer refuses to emit on any electron-accounting failure, exactly as `build_problem` refuses
   an unbalanced reaction (ADR-0008). The lesson's payoff is molecular **polarity**, so it is authored only for a **neutral**
   molecule (a charged ion carries a net charge, not a dipole — refused).
2. **Four fixed teaching steps, authored prose.** `[steps]` carries exactly `valence`/`lewis`/`shape`/`polarity`; the
   producer fixes each step's title + **regime** (the honesty badge — valence/lewis are machine-checked, shape is
   rule-sourced, polarity is model-assumed), the author supplies only the prose. This is the **three-badge honesty model
   layered over one molecule** — the same "layered, not mixed" discipline as the molecule Atlas kind. The four
   machine-checked facts (electrons conserved, octets/duets complete, formal charges sum to the charge, domain count keys
   the geometry) are SHOWN not asserted — the structure lesson's counterpart of a reaction lesson's atom/charge/unit/extent
   checks.
3. **Node re-verification via a shared engine.** The molecule electron-ledger re-derivation was **factored out** of
   `validate-reference.mjs` into `scripts/validate/structurecheck.mjs` (`verifyElectronLedger` + `ledgerTables` +
   `classifyBond`) — the Node counterpart of `compute_ledger`. Both `validate-reference` (the molecule kind) and
   `validate-solutions` (the structure lesson) call it, so a structure lesson's electron ledger stands on its own
   re-proof, and the gate additionally **cross-checks the embedded ledger byte-for-byte against the Atlas molecule** with
   the same `ref_id` (no drift). `validate-reference`'s lesson-slug walk + the five reference pages' lesson-title maps now
   include `*.structure.json` so the Atlas ↔ lesson backlinks resolve.
4. **The player is fully static.** A structure lesson has no interactivity (the electron ledger is fixed — no sliders), so
   it renders server-side in a plain Astro component `StructureLesson.astro` (the dumbest stepper of all), integrated into
   the existing `/lessons/<slug>/` route (both lesson pages glob `*.solution.json` + `*.structure.json` and branch on kind).

**Consequences.** The first molecule lesson: **`bonding/water-molecular-shape`** — *why water is bent*. Valence (8
electrons, machine-checked) → Lewis (2 O–H bonds + 2 lone pairs on O, octet + formal-charge sum machine-checked) → VSEPR
(4 domains → tetrahedral electron geometry → **bent**, sourced) → polarity (bent + polar O–H bonds → **polar**,
model-assumed). The misconception ("water is linear") is refuted **from the verified geometry** — the two lone pairs are
electron domains, so 4 domains → bent, not a straight line — and CO₂ (genuinely linear, nonpolar despite polar bonds) is
the contrast. Lesson #7; the tier's deep slice. New (additive): `schemas/structure-lesson.schema.json`,
`structure.build_structure_lesson` (+ `build.py`'s extension dispatch + molecule-spec resolver),
`scripts/validate/structurecheck.mjs` (factored from validate-reference — the molecule JSON is byte-identical after the
refactor), `src/components/StructureLesson.astro` + `view.renderStructureLesson`. **306 producer tests** (+8 —
`test_structure.py`); **validate-solutions = 6 + 1 structure lesson**; check-katex = **498** (+1); **28 pages** (+1);
`derived/` byte-stable; **no existing derived changed** except the 3 authored `lessons` backlinks (molecule-water,
lewis-structure, vsepr). 7-way tamper-tested (corrupt the valence total / a formal charge / the step order / the geometry
shape / drop the model assumption / a bad ref_id / a flipped check — each caught by a distinct gate branch). **Deferred:**
generated practice on the lesson (the gym already drills the counting); more structure lessons (CO₂'s linear-nonpolar
contrast as its own slice; NH₃/CH₄) once wanted; IMFs (the tier's next increment, building on molecular polarity).

## ADR-0046 — Open intermolecular forces (IMFs): a structure-derived dominant-IMF classifier on the molecule Atlas (2026-07-08)

**Context.** The bonding tier's remaining topic is **intermolecular forces** — the attractions *between* molecules that
set boiling points, states of matter, and solubility. Unlike everything in the tier so far (electron ledger, VSEPR
geometry — machine-checkable or cleanly sourced), IMFs are the first predominantly **empirical/interpretive** topic
(regime 3–4): "which force is stronger" and "why does that raise the boiling point" are not theorems. Because "the
verification system is the product," shipping IMFs as unanchored prose would be off-thesis. The owner authorized opening
IMFs with the scope proposed here.

**Decision.** Anchor IMFs to the **already-verified molecular structure**. The machine-checkable spine is a **dominant-IMF
classifier** (`structure.classify_imf`) that reads the verified structure + the machine-derived polarity: every molecule
has **London dispersion**; a **polar** molecule adds **dipole–dipole**; a molecule with an **H bonded directly to N/O/F**
adds **hydrogen bonding**; the **dominant** force is the strongest type present (H-bonding > dipole–dipole > dispersion).
The **H-bond-donor detection is exact** — a graph fact over the atoms + bonds — and polarity is already derived, so the
*presence* of each force is machine-derived (the gate re-derives it in pure Node via `structurecheck.classifyIMF`); the
**strength ordering is the sourced rule** (regime-3, OpenStax §10.1), with one disclosed caveat (dispersion grows with
size/polarizability, so for large molecules it can overtake a small dipole). It is delivered as an optional
**`intermolecular` block on the `molecule` Atlas kind** (neutral molecules only — an ion's interactions are ionic, a
different regime), carrying `dominant` + `forces` + `h_bond_donor` (machine-derived) plus a **sourced normal boiling
point** as evidence (`data/boiling-points.toml`, regime-3 — the value is not re-derivable, so the gate register-checks its
source, not its magnitude). A new **`intermolecular-forces` concept** (rule-sourced) carries the teaching: the three
forces, when each dominates, the ordering, and the canonical boiling-point evidence.

**Consequences.** Every neutral molecule Atlas entry now shows its dominant IMF + the forces present + its sourced boiling
point, each under the right badge (machine-derived "from the structure" · data-sourced for the boiling point). The
classifier gets the subtle cases right: **CH₂O** is polar (dipole–dipole) but its H's are on **carbon**, so it is *not* a
hydrogen-bond donor; **CH₄**/**CO₂** are nonpolar (dispersion only); **H₂O**/**NH₃** hydrogen-bond. The evidence is the
canonical hydride comparison — CH₄ (−161.5 °C) ≪ NH₃ (−33.3 °C) ≪ H₂O (100 °C) — plus CO₂ subliming at −78.5 °C (a
nonpolar molecule barely condensing). New (additive): `data/boiling-points.toml` (+ a `boiling_points` source facet + the
`data.py` loader), `structure.classify_imf` + `structurecheck.classifyIMF` (the shared re-derivation), the molecule
schema's optional `intermolecular` block, the `intermolecular-forces` concept, and the molecules-page IMF display. The
molecule schema change is additive (optional block); the 5 neutral molecule JSONs intentionally gain the block (NH₄⁺, an
ion, does not — verified byte-identical). **311 producer tests** (+5); **validate-reference = 61** (+1 concept);
check-katex = 499; 29 pages; `derived/` byte-stable. **6-way tamper-tested** (flip the dominant / the h_bond_donor / the
forces list / add a block to the ammonium ion / an unregistered boiling source / drop a neutral molecule's block — each
caught). **Deferred:** the **IMF comparison lesson** (a new *multi-molecule* lesson shape — the natural next increment,
teaching the boiling-point trend as the payoff); ion–dipole + the strength-vs-size nuance as their own content; drilling
"which IMF dominates?" in the `lewis_structures_v1` gym.

## ADR-0047 — The `comparison` lesson kind: a machine-verified multi-molecule trend (2026-07-08)

**Context.** With IMFs in place (ADR-0046), the bonding tier's teaching payoff is the **boiling-point trend** — line up
similar-sized molecules and show that the boiling point tracks the dominant intermolecular force. That is inherently a
**multi-molecule comparison**, which neither existing lesson shape fits: a reaction lesson (`solution.json`) is a species
ledger over extent; a structure lesson (`structure.json`, ADR-0045) is *one* molecule's electron ledger. The owner
authorized building this lesson (an AskUserQuestion at the increment-16 boundary).

**Decision.** A **third lesson kind, `comparison`** — its own `schemas/comparison-lesson.schema.json` + builder
`structure.build_comparison_lesson`, emitting `derived/<topic>/<slug>.comparison.json` (dispatched by extension in
`build_problems_main` alongside `.problem.toml`/`.structure.toml`). Its rows reference `molecule` Atlas entries by id and
**reuse their verified data** — the builder resolves each via `build_molecule_entry`, so every row's dominant IMF +
boiling point is the same machine-derived/sourced value the Atlas shows (no drift). The load-bearing move: **the lesson's
central claim is itself machine-checked.** The builder sorts the rows ascending by the compared property (boiling point)
and **proves the dominant-IMF rank is non-decreasing** (dispersion 1 < dipole–dipole 2 < hydrogen bonding 3) — i.e. "IMF
strength predicts the ordering" — and **refuses to emit if the authored corpus breaks it** (ADR-0008; it will not teach a
false trend). The gate (`validate-solutions`) re-derives the whole spine in pure Node: rows sorted, rank consistent with
`dominant`, monotonic, and each row's IMF re-derived from the Atlas structure (`classifyIMF`) + boiling point matched. A
fully static `ComparisonLesson.astro` player (nothing to hydrate).

**Consequences.** The bonding tier's capstone: **`bonding/boiling-points-and-imfs`** — CH₄ (−161.5 °C, dispersion) ≪ NH₃
(−33.3 °C, hydrogen bonding) ≪ H₂O (100 °C, hydrogen bonding), three second-row hydrides of nearly equal mass (16/17/18)
so **size is controlled and the intermolecular force is the variable**. The machine verifies the trend; the misconception
is the canonical **intramolecular-vs-intermolecular** confusion ("water boils high because O–H bonds are strong / boiling
breaks them"), refuted from the table (boiling overcomes the forces *between* molecules, not the covalent bonds *within* —
steam is still H₂O). New (additive): `schemas/comparison-lesson.schema.json`, `structure.build_comparison_lesson` (+
`build.py`'s `build_comparison` + the third dispatch), `src/components/ComparisonLesson.astro` +
`view.renderComparisonLesson`; the two lesson pages + five reference pages now glob all three lesson suffixes, and
`validate-reference`/`check-katex` learn `.comparison.json`. **315 producer tests** (+4); **validate-solutions = 6 + 2
structure + 1 comparison**; check-katex = 502 (+3); **30 pages** (+1); `derived/` byte-stable (only the 4 authored
backlinks changed — the concept + the 3 compared molecules). **5-way tamper-tested** (unsort the rows / an inconsistent
imf_rank / a non-monotonic trend / a boiling-point drift / a dominant-IMF drift — each caught by a distinct branch).
There are now **three lesson shapes** (reaction / structure / comparison), each a tight schema; the reaction schema stays
pristine. **Deferred:** more comparison axes (melting point, solubility) once wanted; a "which IMF dominates?" gym drill.

## ADR-0048 — Open equilibrium & acid-base: the reversible-extent solver + the `equilibrium` lesson kind (2026-07-08)

**Context.** With the bonding tier's teaching arc complete, the next flagged tier is **equilibrium & acid-base** — the
largest of the remaining model-bearing topics, and the one the thesis (AGENTS.md, ADR-0002) most directly predicts: *"ICE
table = the species ledger with reversible extent."* In `extent.py` a reaction runs to completion and ξ is driven to the
limiting-reagent minimum. An equilibrium is the SAME ledger — every amount is still $c_i = c_{i,0} + \nu_i\,x$ — but the
extent stops where **mass action** balances ($Q(x)=K$), short of completion. The owner pre-authorized opening this tier
("You can open equilibrium/acid-base if appropriate"). The opening stress scenario is the canonical first equilibrium
problem: **the pH of a weak acid**.

**Decision.** (1) A **reversible-extent solver**, `chemkernel.equilibrium.solve_equilibrium`: it builds the ICE ledger in
concentrations and finds the extent $x$ at which the reaction quotient $Q(x)=\prod_i(c_{i,0}+\nu_i x)^{\nu_i}$ equals $K$.
On the physical interval (every concentration ≥ 0) $Q$ is strictly increasing, so exactly one root exists; it is found by
**bisection to high precision** (exact `Decimal`) — NOT the quadratic formula, because the same machine has to serve the
cubic (common-ion Ksp), the buffer, and the polyprotic case later. The root is generally irrational, so the extent + pH
are **model-exact-then-rounded** (the ADR-0040 gas-law pattern, not a weakening of ADR-0013 ledger exactness); the honest
machine-check is the **residual** — the committed equilibrium concentrations put back into $Q$ reproduce $K$ — plus the
gate's **independent re-solve** of the root in pure Node. (2) A new **`equilibrium` lesson kind** — its own tight
`schemas/equilibrium-lesson.schema.json` + `equilibrium.build_equilibrium_lesson`, emitting
`derived/<topic>/<slug>.equilibrium.json` (dispatched by extension in `build_problems_main`, the **fourth** lesson shape
after reaction/structure/comparison). (3) Honesty **layered, not mixed** (the three badges): the ICE identity
$c_i=c_{i,0}+\nu_i x$ is exact algebra (regime-1, machine-checked — the gate re-derives every row); $K_a$ is a sourced
empirical datum (regime-3); the equilibrium **model** (one dominant equilibrium; activities ≈ molarities; water's own
ionization neglected) is disclosed (regime-2, model-assumed); the solved position (x, pH) is model-exact-then-rounded.
Triple-badged, like the energy lesson. (4) $K_a$ is curated + sourced in **`data/ionization-constants.toml`** (OpenStax
*Chemistry 2e* Appendix H), loaded by `data.py` like the other Phase-2 datasets; the acid's dissociation (HA ⇌ H⁺ + A⁻)
is **DRY-sourced from `data/acids-bases.toml`** (its proton count + conjugate anion), so the reaction is not re-authored.
(5) pH = −log₁₀[H⁺]; the lesson links to two new **concepts** (`chemical-equilibrium`, `ph`) rather than formula-sheet
entries — the honest $K$/pH formula-sheet treatment needs *activities* (dimensionless, so the dimension engine stays
homogeneous), deferred with the rest. (6) The gate re-derives the whole spine in pure Node (`equilibriumcheck.mjs`,
shared like `structurecheck.mjs`, called from `validate-solutions`): the ICE identity, an **independent bisection
re-solve** of the root, the residual $Q(\text{committed})=K$, the pH, and the percent ionization.

**Consequences.** The tier opens on **`equilibrium/acetic-acid-ph`** — 0.100 M acetic acid, $K_a=1.8\times10^{-5}$ →
$x=[\mathrm{H^+}]=1.33\times10^{-3}$ M, **pH 2.88**, 1.33% ionized. The misconception is the canonical one — treating the
weak acid as strong ("$[\mathrm{H^+}]=0.100$, pH = 1.00") — refuted from the ledger: only 1.33% ionizes, 98.67% stays
intact. New (additive): `data/ionization-constants.toml` + the `data.py` loader/accessor/source;
`chemkernel/equilibrium.py`; `schemas/equilibrium-lesson.schema.json`; `build.py`'s `build_equilibrium` + the fourth
dispatch; `problems/equilibrium/acetic-acid-ph.equilibrium.toml`; `reference/concepts/{chemical-equilibrium,ph}.toml`;
`scripts/validate/equilibriumcheck.mjs` + the `validate-solutions` walk; `check-katex`/`validate-reference` learn
`.equilibrium.json`; `src/components/EquilibriumLesson.astro` + `view.renderEquilibriumLesson` + the lesson pages'
dispatch. **333 producer tests** (+18); **validate-solutions = 6 + 2 structure + 1 comparison + 1 equilibrium**;
validate-reference = 63 (+2 concepts); check-katex = 530 (+28); **31 pages** (+1); `derived/` byte-stable (only the 3 new
files). **5-way tamper-tested** (corrupt extent → ICE identity; a *coherent* wrong extent that satisfies the identity →
the independent re-solve; corrupt $K_a$ → re-solve; corrupt pH → log consistency; corrupt the quotient → mass action —
each caught by a distinct branch). There are now **four lesson shapes**. **Deferred (the rest of the tier):** the weak
**base** ($K_b$, pOH, $K_w$); **buffers** (Henderson–Hasselbalch = the ICE ledger with both HA and A⁻ present, the
reverse-direction bracket the solver already supports); **titration curves**; **polyprotic** staged equilibria (H₃PO₄
$K_{a1}/K_{a2}/K_{a3}$); a weak-acid **gym** (solve-for-pH / solve-for-Kₐ, model-exact-then-rounded); the $K$/pH/$K_w$
**formula-sheet** entries (with the activity treatment). Then kinetics ($d\xi/dt$) and electrochemistry.

**Update (2nd increment, same day) — the `solubility` subtype (Ksp) landed, proving the solver generalizes.** The generic
solver was built for exactly this: `solve_equilibrium` gained an **`in_quotient`** flag — a **pure solid** (activity 1) is
excluded from $Q$ and, being in excess, does not bound the forward extent (so when no quotient reactant limits it the
bracket is grown until $Q>K$). The `equilibrium` lesson kind now carries **two subtypes** under one schema (a `subtype`
discriminator; the subtype-specific reaction/result/checks fields are enforced in the gate, since Ajv `strictRequired`
can't follow `required` names across subschemas — kept out of the schema deliberately). `build_solubility_lesson` +
`build_equilibrium` dispatch by `acid` vs `salt`. The opener: **`equilibrium/calcium-fluoride-solubility`** — CaF₂(s) ⇌
Ca²⁺ + 2 F⁻, $K_{sp}=[\mathrm{Ca^{2+}}][\mathrm{F^-}]^2=4s^3$ (a **cubic** — the bisection solver's whole justification),
$s=2.05\times10^{-4}$ M (0.016 g/L); the misconception is the coefficient-forgetting $s=\sqrt{K_{sp}}$, refuted from the
cubic. $K_{sp}$ from `data/solubility-products.toml` (App J); the salt's ion counts are derived by **charge crossover** and
its composition machine-checked on load (regime-1, like acids-bases). It closes the Phase-0 precipitation loop (the
`precipitation` concept backlinks). **340 tests** (+7); validate-solutions = 6 + 2 structure + 1 comparison + **2
equilibrium**; check-katex 555; **32 pages**; the acetic lesson gained `subtype` (byte-change, re-verified). **4-way
tamper-tested** (coherent wrong solubility → the independent re-solve; corrupted fluoride coefficient → ICE identity;
bad g/L → solubility-consistent; the solid forced into Q → ICE identity).

**Update (3rd increment, same day) — the `weak-base` subtype ($K_b$ → pOH → pH via $K_w$) landed, and it reuses the
solver UNCHANGED.** A weak base ionizes against water: $\mathrm{B} + \mathrm{H_2O} \rightleftharpoons \mathrm{BH^+} +
\mathrm{OH^-}$, $K_b = [\mathrm{BH^+}][\mathrm{OH^-}]/[\mathrm{B}]$. Water is the **pure solvent** (activity 1) — so it is
excluded from $Q$ exactly as the Ksp solid is: it rides the *same* `in_quotient=False` mechanism, and `solve_equilibrium`
needed **no change**. The extent is $[\mathrm{OH^-}]$; the pH comes through the **water ion-product** $K_w = [\mathrm{H^+}]
[\mathrm{OH^-}] = 1.0\times10^{-14}$ (the acid/base **bridge**: $[\mathrm{H^+}]=K_w/[\mathrm{OH^-}]$, $\mathrm{pH}+\mathrm{pOH}
=\mathrm{p}K_w=14.00$) — the one genuinely new relation, and the subtype's 4th machine-checked fact (`kw_consistent`).
$K_b$ + $K_w$ are curated in **`data/ionization-constants.toml`** (extended: `[bases.*]` with a `conjugate_acid` +
`[water]`; OpenStax Appendix I + §14.1), and the base's proton accounting (base + H⁺ = the conjugate-acid cation) is
**machine-checked on load** (regime-1) — so the weak base is modeled entirely there, leaving `data/acids-bases.toml` (and
the reaction classifier that reads it) untouched. `build_weak_base_lesson` + a `base` dispatch in `build_equilibrium`; the
`weak-base` subtype added to the schema/gate/player. The opener: **`equilibrium/ammonia-ph`** — 0.100 M NH₃,
$K_b=1.8\times10^{-5}$ → $[\mathrm{OH^-}]=1.33\times10^{-3}$ M, **pOH 2.88, pH 11.12**, 1.33% ionized — the exact **mirror**
of the acetic-acid lesson (same $K$, same extent, reflected about neutral: $2.88+11.12=14.00$), which the misconception
(treating the weak base as strong, "pH 13.00") turns into the teaching moment. A new **`water-autoionization` concept** (the
$K_w$ bridge). **350 tests** (+10); validate-solutions = 6 + 2 structure + 1 comparison + **3 equilibrium**;
validate-reference = 65 (+1 concept); check-katex 588; **33 pages**; `derived/` byte-stable (2 new files + the ph/
chemical-equilibrium cross-links). **7-way tamper-tested** (ICE identity; a coherent wrong extent → the independent
re-solve; pOH; the $K_w$-bridge hydronium; pH / pH+pOH=p$K_w$; a corrupted $K_w$; water forced into $Q$ — each a distinct
branch). The `equilibrium` lesson kind now has **three subtypes** (weak-acid / weak-base / solubility).

**Update (4th increment, same day) — the `buffer` subtype landed, exercising the solver's nonzero-initial-product case +
the common-ion effect + Henderson–Hasselbalch.** A buffer is the *same* weak-acid reaction (HA ⇌ H⁺ + A⁻) and the *same*
solver, but the conjugate base A⁻ is **already present** ([A⁻]₀ > 0, from a dissolved salt). The pre-loaded product is a
**common ion**: by Le Chatelier it drives the ionization left, so far less acid ionizes and the pH sits near p$K_a$ instead
of the pure acid's low value. The signature is **Henderson–Hasselbalch**, pH = p$K_a$ + log₁₀([A⁻]/[HA]) — nothing but the
mass-action law $K_a=[\mathrm{H^+}][\mathrm{A^-}]/[\mathrm{HA}]$ in logarithmic form, so it is **machine-checked on the
equilibrium concentrations** (it must reproduce −log₁₀[H⁺]) rather than asserted. The lesson also **re-solves the acid alone**
([A⁻]₀ = 0) to quantify the suppression the common ion causes — both extents are real solver outputs, the gate re-derives
the acid-alone one too. `build_buffer_lesson` + a `build_equilibrium` dispatch (`acid` **with** `conjugate_base_molarity_M`
→ buffer; `acid` alone → weak-acid). The opener: **`equilibrium/acetate-buffer`** — 0.100 M acetic acid + 0.100 M acetate,
$K_a=1.8\times10^{-5}$ → **pH 4.74 = p$K_a$** (equal amounts, so the ratio is 1), 0.018% ionized; the acetate suppresses
ionization **74×** vs the acid alone (pH 4.74 not 2.88). The misconception is treating the added salt as an inert spectator
(the common-ion oversight), refuted from that contrast. A new **`buffer` concept** (common-ion + Henderson–Hasselbalch). No
new reaction fields (the buffer reuses the weak-acid `acid`/`conjugate_base`); new result fields (p$K_a$, buffer ratio, the
H–H pH, the no-buffer contrast) + the `hh_consistent` check. **356 tests** (+6); validate-solutions = 6 + 2 structure + 1
comparison + **4 equilibrium**; validate-reference = 66 (+1 concept); check-katex 619; **34 pages**; `derived/` byte-stable
(2 new files + the ph/chemical-equilibrium cross-links). **8-way tamper-tested** (ICE identity; coherent wrong extent → the
independent re-solve; pH; p$K_a$; buffer ratio; the H–H identity; the no-buffer pH → the acid-alone re-solve; the suppression
factor — each a distinct branch). The `equilibrium` lesson kind now has **four subtypes** (weak-acid / buffer / weak-base /
solubility).

**Update (5th increment, same day) — the `weak_acid_ph_v1` gym: the tier's drill instrument.** Every model-bearing tier
gets a gym (gases, calorimetry); equilibrium's is the pH of a weak acid, drilled endlessly over the curated weak acids +
concentrations. It is **model-exact-then-rounded AND data-sourced** (like calorimetry, ADR-0042 — both badges): the pH rides
the ideal-dilute-solution model (regime-2, disclosed) and rests on the sourced $K_a$ (regime-3). It is found the **honest**
way — the generator and the gate both use `solve_equilibrium`'s mass-action root (Q=$K_a$ by bisection), **no small-x
approximation** — exactly the flagship acetic-acid lesson's machine, so the gym and the lesson can't disagree. Free-entry
numeric (ADR-0032), pH reported to 3 sig figs; the diagnostics are the canonical weak-acid errors, each a wrong pH VALUE:
treating the acid as strong (pH = −log[HA]₀), confusing $K_a$ with [H⁺] (pH = p$K_a$), and dropping the square root
([H⁺] = $K_a$·[HA]₀). The gate's re-derivation **reuses `solveEquilibrium` from `equilibriumcheck.mjs`** (the same shared
Node solver the equilibrium lessons' gate uses) — one instrument, three call sites (the Python builder, the lesson gate, the
gym gate). New (additive): `gym._generate_weak_acid_ph` + `_sci` (Unicode scientific notation for the prompt's $K_a$) + the
`weak_acid_ph_v1` family registration + provenance source + model-assumed disclosure; the `weak_acid_ph` derivation kind +
`equilibrium` block + the `ionization_constants` provenance source in `schemas/gym.schema.json`; `verifyWeakAcidPh` in
`validate-gyms.mjs`; `gyms/equilibrium/weak-acid-ph.gym.toml`. A subtle bug caught in review: a scientific-notation Decimal
($K_a$) must be emitted with `format(d, "f")`, not `_trim(str(d))` — the latter strips the exponent's trailing zero
(4.9E-10 → 4.9E-1). **362 tests** (+6); validate-gyms = **12 gyms / 120 problems**; check-katex unchanged (gym prompts are
Unicode prose, not KaTeX); **35 pages** (+1: `/gym/weak-acid-ph/`); `derived/` byte-stable (1 new file). In-browser: the free
entry accepts the correct pH and the wrong "treated as strong" entry fires the named diagnostic.

**Update (6th increment, same day) — the common-ion effect: solubility with a shared ion pre-loaded.** The natural Ksp
follow-on, and the second face of the common-ion effect the buffer already showed for a weak acid — now on the **cubic**. A
Ksp salt dissolves not into pure water but into a solution that **already contains one of its own ions** (from a
fully-dissociated soluble salt — the counter-ion a spectator, omitted). That is a **nonzero initial product concentration** —
exactly the buffer's case — so `solve_equilibrium` is **reused unchanged**; Le Chatelier drives the dissolution left and far
less dissolves. Delivered as a **variant of the existing `solubility` subtype** (NOT a new subtype — the reaction, the Ksp
expression, the molar-solubility result are all identical; only one product column starts above zero): `build_solubility_lesson`
gained an optional `common_ion` + `common_ion_molarity_M`, sets that ion's initial concentration, and **re-solves the salt in
pure water** for the suppression contrast (mirroring the buffer's acid-alone re-solve). The opener:
**`equilibrium/calcium-fluoride-common-ion`** — CaF₂ into 0.10 M F⁻ (from NaF) → molar solubility **3.45×10⁻⁹ M**, about
**59 400× less** than the 2.05×10⁻⁴ M in pure water; the misconception is that solubility is a fixed property of the salt,
refuted from the contrast. A new **`common-ion-effect` concept** (the one principle behind both buffers and suppressed
solubility), cross-linked from `buffer` and `solubility-product`. Additive schema (reaction `common_ion`/`common_ion_latex`/
`common_ion_molarity_M`; result `molar_solubility_pure_water_M`(`_display`); `suppression_factor_display` **reused** from the
buffer) — the subtype enum stays four, `checks` unchanged. **369 tests** (+7); validate-solutions = 6 + 2 structure + 1
comparison + **5 equilibrium** (14 ids); validate-reference = **67** (+1 concept); check-katex **643** (+24); **36 pages**
(+1: `/lessons/calcium-fluoride-common-ion/`); `derived/` byte-stable (2 new files + the buffer/solubility-product
cross-links). **3-way tamper-tested** on the new branch (the suppression factor; the pure-water contrast solubility; the
common ion's initial concentration vs the reaction block). In-browser: the ICE table shows F⁻ pre-loaded at 0.10, the
"59 400× less" card, the common-ion note, and the refuted misconception; 0 KaTeX errors.

**Update (7th increment, same day) — the `polyprotic` subtype: staged ionization, the same solver run per stage.** A
polyprotic acid loses its protons in STAGES (H₃PO₄ ⇌ H⁺ + H₂PO₄⁻, then H₂PO₄⁻ ⇌ H⁺ + HPO₄²⁻, then HPO₄²⁻ ⇌ H⁺ + PO₄³⁻),
each with its own Kₐ (Kₐ1 ≫ Kₐ2 ≫ Kₐ3, ~10⁵ apart). `solve_equilibrium` runs **once per stage**, each seeded with the
previous stage's equilibrium concentrations (the standard **successive treatment** — a disclosed model assumption, exact in
the well-separated-Kₐ limit). The FIFTH subtype (`build_polyprotic_lesson`, dispatched when the named acid has ≥ 2 protons).
Schema: the top-level `ice`/`mass_action`/`reaction`/`equilibrium_constant` are the FIRST (dominant) ionization — so the
existing required fields stay meaningful and the existing ICE renderer shows stage 1 — and `result.later_stages` carries
stages 2..n as compact, independently re-solvable objects (+ `result.species_ladder` for every species' equilibrium
concentration, + `proton_count`). No `required`-field relaxation; the 4th check reuses `ph_consistent`. Data (regime-3): a
`[polyprotic]` table in `data/ionization-constants.toml` (each stage's composition — acid = anion + H⁺, charge one more
positive — machine-checked on load, the Kₐ required strictly decreasing) + two new ion-table anions (H₂PO₄⁻/HPO₄²⁻), all
OpenStax App H. The opener: **`equilibrium/phosphoric-acid-ph`** — 0.100 M H₃PO₄ → **pH 1.62** ([H⁺] = 0.0239 M, 23.9% of
the first proton), and the checkable payoffs FALL OUT of the solve: [H⁺] tracks stage 1, the amphiprotic **[HPO₄²⁻] ≈ Kₐ2 =
6.2×10⁻⁸** (because [H⁺] ≈ [H₂PO₄⁻] collapses stage 2's mass-action law), and [PO₄³⁻] ≈ 10⁻¹⁸ (essentially absent). The
misconception is that all three protons ionize comparably. A new **`polyprotic-acid` concept**. Gate `equilibriumcheck.mjs`
re-solves each later stage on the chained initials + re-checks Q=Kₐ per stage + the accumulated [H⁺]/pH + the species-ladder
reconstruction. **376 tests** (+7); validate-solutions = 6 + 2 structure + 1 comparison + **6 equilibrium** (15 ids);
validate-reference = **68** (+1 concept); check-katex **702** (+59); **37 pages** (+1); `derived/` byte-stable. **5-way
tamper-tested** (a stage extent; the chain link; the pH; a ladder concentration; the accumulated hydronium). In-browser:
stage-1 ICE + the later-ionizations table + the species ladder (10⁻² → 10⁻¹⁸) + the ≈Kₐ2 payoff render; 0 KaTeX errors. The
`equilibrium` kind now has **five subtypes**.

**Update (8th increment, same day) — the `titration` subtype: the ledger marched, and the tier's first plot.** A weak acid
titrated by a strong base — the equilibrium tier's remaining marquee. The insight the whole tier builds to: a titration curve
is nothing but the **species ledger solved over and over** as titrant is added, the region deciding which equilibrium
dominates. `build_titration_lesson` samples the added-base volume at fractions of the equivalence volume and computes the pH
at each by region — a **weak-acid/buffer solve** before equivalence (HA ⇌ H⁺ + A⁻ with [A⁻] from the neutralized acid), the
**conjugate base's weak-base solve** at equivalence (A⁻ + H₂O ⇌ HA + OH⁻, Kᵦ = K_w/Kₐ → the K_w bridge to pH), and **excess
strong base** past it — each reusing `solve_equilibrium`. The SIXTH subtype. Reuses only existing curated data (acetic acid's
Kₐ + NaOH as a curated strong base — **no new data**). Schema: the top-level ice = the **initial** point (the pure weak acid,
so the required fields + the existing ICE renderer stay meaningful), plus a top-level **`titration` block** (the (volume, pH)
curve + the three landmarks + the equivalence/half-equivalence volumes + pKₐ). The player draws a **build-time SVG** of the
verified points (no client chemistry — the "dumb stepper" plots, it does not compute) — the tier's first chart. The opener:
**`equilibrium/acetic-acid-titration`** — 25.0 mL 0.100 M acetic acid + 0.100 M NaOH → the classic curve: initial **pH 2.88**,
a buffer region flattest at half-equivalence (12.5 mL) where **pH = pKₐ = 4.74**, a steep jump through the **equivalence point**
(25.0 mL, **pH 8.72 — basic**, the conjugate base hydrolysing), then excess base. The misconception is expecting pH 7 at
equivalence (true only for strong+strong); it fails against the machine's basic result. A new **`titration` concept**. Gate
`equilibriumcheck.mjs` **recomputes the entire curve** independently (region + pH per point, from the titrant/acid inputs +
Kₐ + K_w) and re-checks the landmarks (half-eq pH ≈ pKₐ, equivalence > 7). **383 tests** (+7); validate-solutions = 6 + 2
structure + 1 comparison + **7 equilibrium** (16 ids); validate-reference = **69** (+1 concept); check-katex **716** (+14);
**38 pages** (+1); `derived/` byte-stable. **5-way tamper-tested** (a curve pH; a curve region label; the equivalence pH
forced acidic; the equivalence volume; the half-equivalence pH). In-browser: the SVG curve renders the textbook shape
(buffer plateau → equivalence jump → excess-base tail) with the three landmark markers + a pH-7 reference line; 0 KaTeX
errors. The `equilibrium` kind now has **six subtypes**.

**Update (9th increment, same day) — the `prediction` lesson KIND: Q vs Kₛₚ, the precipitation face (a snapshot, not a
solve).** The flagged remaining equilibrium item, and the first face that is **not** an equilibrium *solve*. "Will a
precipitate form when two solutions are mixed?" is answered by the **reaction quotient**, not the solver: mix, dilute each ion
into the combined volume, evaluate $Q = [\text{cation}]^a[\text{anion}]^b$ at that instant, and compare to $K_{sp}$ —
$Q > K_{sp}$ ⇒ supersaturated ⇒ a precipitate forms; $Q < K_{sp}$ ⇒ stays clear; $Q = K_{sp}$ ⇒ exactly saturated. Because there
is no extent to solve (no ICE table, and $Q \neq K$ by design), it does **not** fit the equilibrium-lesson schema (whose `ice`
requires a solved extent and whose `mass_action_satisfied` check would be a lie for a snapshot). Following the house pattern
(structure/comparison/equilibrium each got their own tight schema, not a bent union — the same reasoning as Q5/ADR-0020), it is
a **new `prediction` lesson kind**: `schemas/prediction-lesson.schema.json`, `build_prediction_lesson` (in `equilibrium.py`,
reusing `_quotient` + the sourced Ksp data), dispatched by the `*.prediction.toml` extension → `*.prediction.json`, its own
static `PredictionLesson.astro`. The honesty shape is unchanged (the three badges/regimes): the ion accounting (mixing dilution
+ Q) is machine-checked (regime-1), $K_{sp}$ sourced (regime-3), the verdict the disclosed model prediction (regime-2 — the
thermodynamic prediction, no metastable supersaturation). Machine-checked facts: `mixing_dilution` ($[\text{ion}]$ after mixing
$= [\text{ion}]_{\text{source}} \times V_{\text{source}}/V_{\text{total}}$), `quotient_computed` (Q at the mixed
concentrations), `verdict_consistent` (`forms_precipitate` ⇔ $Q > K_{sp}$, an **exact Decimal comparison**). The source→ion
multiplicity is machine-checked for a **monatomic ion** (its element appears `per_formula` times in the neutral source
formula — Ca(NO₃)₂ really has one Ca; NaF one F), with the strong-electrolyte full dissociation the disclosed model
assumption. The opener: **`equilibrium/calcium-fluoride-precipitation`** — 40.0 mL 0.010 M Ca(NO₃)₂ + 60.0 mL 0.010 M NaF →
[Ca²⁺] = 0.0040 M, [F⁻] = 0.0060 M, **Q = 1.44×10⁻⁷ ≫ Kₛₚ = 3.45×10⁻¹¹ (≈ 4170×)** → **a precipitate forms**. The **third view
of CaF₂** (dissolve it / suppress it / **predict** it — reuses the same curated Ksp, no new data). The misconception is judging
by the clarity/dilution of the *parts* ("both clear and only 0.010 M → nothing happens"), refuted because it is the ion product
of the *mixture* vs. the tiny Ksp that decides. A new **`reaction-quotient` concept** (Q has K's form, evaluated anywhere; Q vs
K predicts the direction of change). Gate `equilibriumcheck.mjs` gains `verifyPrediction` (re-derives the dilution + Q + verdict
+ source composition in pure Node, reusing `parseFormula` + `reactionQuotient`); the check-katex / validate-reference
lesson-slug / lesson-route walks gained the `.prediction.json` suffix. **392 tests** (+9); validate-solutions = 6 + 2 structure
+ 1 comparison + 7 equilibrium + **1 prediction** (17 ids); validate-reference = **70** (+1 concept); check-katex **752**
(+36); **39 pages** (+1); `derived/` byte-stable (2 new files). **5-way tamper-tested** (the verdict flipped against Q; a mixed
concentration; Q; the margin; the source `per_formula`). In-browser: the mixing table + Q substitution + the verdict banner
("✓ A precipitate forms", Q > Kₛₚ ≈ 4170×) render, 0 KaTeX errors, all 5 concept chips resolve. Lessons now come in **five
shapes** (reaction · structure · comparison · equilibrium · prediction); the equilibrium tier spans **six `equilibrium`
subtypes + the `prediction` kind** — the ledger solved to equilibrium, and now the ledger's quotient tested against it.

**Follow-on (same increment) — the other verdict + a verdict-general player.** A second prediction lesson
`equilibrium/magnesium-hydroxide-no-precipitate` shows the $Q < K_{sp}$ case: dilute Mg(NO₃)₂ + NaOH → $Q = 1.25\times10^{-13}$,
about **45× below** $K_{sp} = 5.61\times10^{-12}$ → **stays clear**. It makes "insoluble" read as *quantitative* (a precipitate
forms only when Q exceeds Kₛₚ, not because a compound is "insoluble"), refuting the reverse misconception; and it exercises the
**second** curated Kₛₚ salt (Mg(OH)₂) plus a **polyatomic-ion** (OH⁻) source — whose multiplicity rides the disclosed
full-dissociation model (the monatomic composition check applies only to a monatomic ion). Authoring it surfaced a latent gap:
`PredictionLesson.astro`'s misconception refutation had been hardcoded for the "precipitate forms / Q above Kₛₚ" case — now
**branched on the verdict**, so the `prediction` kind handles both outcomes cleanly. **393 tests** (+1); validate-solutions =
2 prediction (18 ids); check-katex 773; **40 pages**; the "no" verdict tamper-tested (flipping it to "precipitate" is caught).

**Update (10th increment, same day) — the equilibrium constants on the formula sheet, as dimensionless *activity* relations
(owner-decided).** The last flagged equilibrium-tier item: put Kₐ, K_b, K_w, K_sp (and the conjugate identity Kₐ·K_b = K_w) on
the ADR-0039 formula/equation sheet. The design question — how a *monomial* dimension checker handles equilibrium quantities and
the **log** relation pH = −log₁₀(a) — was put to the owner (they chose **"K-relations only"**). The resolution, now the house
treatment: an equilibrium constant is built from **activities**, and an activity $a_X = [X]/c^\circ$ is a concentration measured
against the $c^\circ = 1\ \mathrm{M}$ **standard state** — hence **dimensionless**. So each K is a monomial of dimensionless
quantities, and "both sides reduce to the zero SI vector" is exactly what the existing engine checks — **no engine change**
(the dimensionless unit `"1"` was already registered, ADR-0039). The pH/pOH **log-definitions are NOT forced onto the sheet**
(a monomial checker can't verify a transcendental); they remain in the `ph` concept, which is their honest home. Consequences:
**5 new formula entries** (sheet 9 → 14), all model-exact + disclosing the activity/standard-state idealization; the dimension
re-derivation in `validate-reference.mjs` verifies them unchanged. Two display fixes fell out: the formulas page grouped by a
hardcoded id list, so a new **"Equilibrium & acid–base"** section was added — which revealed that `formula-enthalpy-of-reaction`
(ADR-0043) had never been listed in any group and so had **silently not rendered** (now in "Gases & energy"); and since a
variable's `meaning` renders as plain text (not KaTeX), the activity notation moved out of `$…$` math into prose. **394 tests**
(+1); validate-reference = **75** (+5); check-katex 830; 40 pages; `derived/` byte-stable. **The equilibrium & acid-base tier is
now feature-complete** — six subtypes + the gym + the prediction kind (both verdicts) + the K reference surface — leaving only
optional enhancements (a titration slider, a weak-base/buffer gym). The model-bearing tiers still open: kinetics, electrochemistry.

## ADR-0049 — Open kinetics: the ledger in time (dξ/dt), first-order decay (2026-07-08)

**Context.** Phase 2 extends the species-ledger-over-extent machine to the model-bearing tiers. The equilibrium & acid-base tier
is feature-complete, and the owner directed opening **kinetics** next. Kinetics is the thesis's most literal time extension: the
reaction extent ξ — static in a completed ledger, solved-from-mass-action in equilibrium — now **evolves in time**, and dξ/dt is
the *rate*. Opening a tier needs a stress scenario (its hardest single case, per the ROADMAP method), a decay engine, the honesty
treatment for an empirical rate law, and a new lesson kind.

**Decision.** (1) Open kinetics on **first-order decay** — the simplest, most iconic case, the one that isolates the tier's ideas:
a rate law rate = k[A], its integrated form [A](t) = [A]₀e^(−kt), and the concentration-independent half-life t½ = ln2/k.
(2) A new `chemkernel.kinetics` module: `concentration_first_order` (Decimal `.exp()`), `half_life_first_order` (Decimal
`.ln()`), `build_kinetics_lesson`. The transcendental decay is computed at high Decimal precision and rounded for display —
**model-exact-then-rounded**, the same honesty as the gas-law volume (ADR-0040), not a weakening of ledger exactness. (3) A new
**`kinetics` lesson kind** (the **6th lesson shape** — own tight `kinetics-lesson.schema.json`, `*.kinetics.json`), a curve
lesson like titration: the rate law + k + the integrated law + the half-life + a decay **curve** (a build-time SVG of verified
points) + the halving landmarks. (4) Honesty, layered (the three badges, **no new badge**): the species accounting (the ledger,
[A] = [A]₀ − aξ) is machine-checked (regime-1); the **rate law and its order are a disclosed model** (regime-2 — the order is
found by experiment, *not* read off the balanced-equation coefficients, a named misconception); k is a **sourced empirical
datum** (regime-3, `data/rate-constants.toml`, OpenStax §12.4); the integrated law + half-life + every curve point are exact
given the model (regime-2). (5) The machine-check is the algebra, re-derived in pure Node (`kineticscheck.mjs`): the reaction
balances, every curve point c(t) = c₀·e^(−kt), k·t½ = ln2, and c(n·t½) = c₀/2ⁿ (successive half-lives equal — the first-order
tell). The producer refuses a non-first-order reaction sent to this builder, an unknown reactant, or a nonpositive input
(ADR-0008).

**Consequences.** The tier opens on **`kinetics/hydrogen-peroxide-decomposition`** — 2 H₂O₂ → 2 H₂O + O₂, first order, k =
3.21×10⁻⁵ s⁻¹ → **t½ = 6.00 h**, decaying 1.000 → 0.500 → 0.250 → 0.125 M each 6.00 h. The misconception is the shrinking-half-life
error (true for order < 1 — zero order — not first; higher orders make t½ *grow*): refuted because t½ = ln2/k carries **no concentration**, so every half-life is the same
clock — machine-checked. Three concepts: `reaction-rate` (the ledger's time derivative dξ/dt — the tier's gateway), `rate-law`
(rate = k[A]ⁿ, the order empirical, not the coefficient — an explicit `contrast` edge to `balancing-equations`), `half-life` (the
first-order signature). `data/rate-constants.toml` is the new curated dataset (k + order + the balanced equation, machine-checked
on load). The player reuses the titration-plot SVG pattern for the decay curve (the constant half-life visualized as evenly-spaced
halvings). **404 producer tests** (+10); validate-solutions = +1 kinetics (19 ids); validate-reference = 78 (+3 concepts);
check-katex 857; 41 pages; the gate 5-way tamper-tested; browser-verified. Lessons now come in **six shapes** (reaction ·
structure · comparison · equilibrium · prediction · kinetics). **Next in-tier:** second- and zero-order decay (a half-life that
grows / shrinks — the contrast that makes "constant t½" meaningful), a kinetics **gym** (compute [A](t) / t½ / determine the order
from data), and the **Arrhenius** temperature dependence of k. Then **electrochemistry** remains the last Phase-2 tier.

**Update (2nd increment, same session) — second- and zero-order decay: the contrast that makes "constant t½" mean something.**
First order alone can't teach *why* a constant half-life is special — you need the orders that behave differently. **Decision:**
generalize `chemkernel.kinetics` to **orders 0, 1, 2** on one engine — `concentration` / `half_life` / `time_to_reach` dispatch on
order (zero: $[A]_0-kt$, $t_{1/2}=[A]_0/2k$; first: $[A]_0e^{-kt}$, $\ln2/k$; second: $1/[A]_0+kt$, $1/k[A]_0$); the first-order
functions become thin wrappers so existing call sites/tests are unchanged. The k **units encode the order** ($M\,s^{-1}$ /
$s^{-1}$ / $M^{-1}\,s^{-1}$) and the **time base** (min → 60 s): k is kept + shown in its **sourced native units** — butadiene's is
per *minute*, stored verbatim from OpenStax rather than silently converted (the honest choice; the engine reads the time base off
the unit string). The `kinetics` schema stays **one shape** (no new lesson kind): the `subtype` enum widens to
zero/first/second-order, `rate_law.order` to {0,1,2}; `half_life` gains `progression` (constant/doubles/halves — the order's
fingerprint) + `depends_on_concentration`; each landmark gains its **segment half-life** (the duration of *that* halving step);
zero order alone reports a **finite completion** ($[A]=0$ at $t=[A]_0/k$); the check `half_life_constant` → `half_life_progression`.
The gate (`kineticscheck.mjs`) re-derives every point per order and checks the **progression ratios** (~1 / ~2 / ~½) + the finite
completion; the player narrates order-aware (grows / shrinks / constant, and "runs out completely" for zero order). **Two lessons,
both OpenStax §12.4 (web-sourced):** `kinetics/butadiene-dimerization` (2 C₄H₆ → C₈H₁₂, 2nd order, $k=5.76\times10^{-2}\
M^{-1}min^{-1}$, 0.200 M → $t_{1/2}$ **grows** 1.45 → 2.89 → 5.79 h; misconception "a half-life is a half-life"), and
`kinetics/ammonia-decomposition` (2 NH₃ → N₂ + 3 H₂ on hot tungsten, **zero** order, $k=1.3\times10^{-6}\ M\,s^{-1}$, 0.0100 M →
$t_{1/2}$ **shrinks** 1.07 → 0.534 → 0.267 h, reaching **exactly 0 at 2.14 h**; misconception "it must slow as it runs low"). A new
`integrated-rate-law` concept ties the three orders together. Honesty unchanged (three badges); the zero-order transcendental
residual at completion is floored to an exact 0 (the model-exact boundary). **Consequences:** **411 producer tests** (+7);
validate-solutions = **3 kinetics** (21 ids); validate-reference = **79** (+1 concept); check-katex 895; **43 pages** (+2); the
kinetics gate **10-way tamper-tested** across both new orders; browser-verified all three orders side by side (6→6→6 constant vs.
doubling vs. halving). **Next in-tier:** a kinetics **gym** (compute [A](t) / t½ / determine the order from data), then
**Arrhenius**.

**Update (3rd increment, same session) — the `kinetics_v1` gym: the tier's drill instrument.** Every model-bearing tier gets its
gym; kinetics's drills the three orders on the **same order-general `chemkernel.kinetics` engine** the lessons use. **Decision:**
a `kinetics_v1` family (`_generate_kinetics`) with three kinds — **`kinetics_concentration`** (numeric: apply the order's
integrated law for [A](t)), **`kinetics_half_life`** (numeric: apply the order's t½ formula — [A]₀ is a deliberate distractor for
order 1), and **`kinetics_order`** (categorical: read the order off three successive half-lives — constant/doubling/halving, the
tier's payoff). The gym works entirely in k's **native time unit** (no conversion — the drill is the integrated law itself), the
answers **model-exact-then-rounded** to 3 sig figs; it carries **both badges** (data-sourced k + the model-assumed rate law/order,
`_FAMILY_ASSUMPTIONS["kinetics_v1"]`). The star mistake — **using the wrong order's formula** — is exactly what the numeric
diagnostics (the other two orders' results) and the order-kind distractors (the other two orders + their pattern) encode. The
`kinetics_order` half-lives are the **real** successive half-lives of a sourced reaction (engine-computed), presented anonymized so
the learner reads the pattern, not the reactant. The gate (`validate-gyms.mjs`) re-derives every answer per order in pure Node with
the **same** `concAt`/`halfLife`/`timeToReach` now **exported from `kineticscheck.mjs`** (one engine, shared — as `equilibriumcheck`
is shared with the weak-acid gym). **Consequences:** **417 producer tests** (+6); validate-gyms = **13 gyms / 130 problems** (+1/+10);
**44 pages** (+1, `/gym/kinetics/`); check-katex 895 (gym prompts are Unicode prose, not KaTeX); the gym gate **6-way tamper-tested**;
browser-verified (a numeric drill checks "✓ Correct — 0.0075 M", 0 KaTeX errors). Gym family #13. **Next in-tier:** **Arrhenius**
(k = A·e^(−Eₐ/RT) — a formula-sheet entry with a sourced activation energy + a lesson), then **electrochemistry**.

## ADR-0050 — Open electrochemistry: the electron ledger (oxidation numbers → cell potential → ΔG = −nFE) (2026-07-09)

**Context.** The last Phase-2 tier. The brief (§) frames electrochemistry as *electron bookkeeping plus free energy per charge* —
the species ledger with **electrons** as the tracked quantity. ADR-0035 deferred oxidation numbers to Phase 2, flagging redox only
by the free-element signature; a real electrochemistry tier needs them, plus half-reactions, cell potentials, and the ΔG bridge.
Opening a tier needs its hardest single stress scenario (the ROADMAP method), a new engine, sourced data, and a lesson kind. The
owner authorized opening electrochemistry (via an AskUserQuestion at the kinetics-core-complete boundary).

**Decision.** (1) Open on the canonical **galvanic (Daniell) cell** — Zn(s) + Cu²⁺ → Zn²⁺ + Cu — the stress scenario that
exercises every piece: oxidation numbers, two half-reactions, the electron ledger, E°cell, and ΔG°. (2) A new **`chemkernel.redox`**
module with two engines: **`oxidation_states`** assigns each atom its oxidation number by the first-course rule hierarchy (free
element 0; monatomic ion = charge; F −1, group-1 +1, group-2 +2, H +1, O −2) and **solves the one remaining element by the
sum-to-charge constraint** — the rules are a sourced convention (regime-3), the accounting exact (regime-1), machine-checked; it
**refuses** a formula with more than one rule-unknown element (honest over guessing — this *completes* the ADR-0035 free-element
flag). And **`build_electrochemistry_lesson`** takes two sourced metal-ion/metal couples, assigns the cathode (higher E°) and anode
(lower E°), writes the half-reactions, balances the **electron ledger** (n = lcm of the electron counts, the halves scaled so
electrons cancel and the overall reaction balances atoms + charge), reads E°cell = E°(cathode) − E°(anode), and computes
**ΔG° = −nFE°** (model-exact-then-rounded; F exact, E° sourced). (3) A new **`electrochemistry` lesson kind** (the **7th lesson
shape** — own tight `electrochemistry-lesson.schema.json`, `*.electrochemistry.json`), like every model-bearing tier before it
(equilibrium/kinetics got their own kinds rather than bending the reaction lesson). (4) Two sourced data: **standard reduction
potentials** E° (`data/reduction-potentials.toml`, OpenStax Appendix L — 7 couples; the composition machine-checked on load: the
oxidized form is a cation, the reduced form the neutral same element, `electrons` = the ion charge) and the **Faraday constant**
F = 96485.33212 C/mol (`data/constants.toml`, exact since 2019 SI — F = N_A·e). (5) Honesty, layered (the three badges, **no new
badge**): the electron ledger + oxidation numbers are machine-checked (regime-1); E° is sourced (regime-3); the cell potential +
free energy ride the disclosed standard-state model (regime-2). (6) The gate `electrochemistrycheck.mjs` re-derives the whole spine
in pure Node — each species' oxidation numbers (re-run the rule solver, check the sum), each half-reaction's atom+charge+electron
balance, the electron ledger (n lost = n gained), the overall balance, E°cell = E°cathode − E°anode > 0, and ΔG° = −nFE°. The
producer refuses equal potentials (no cell), an unknown couple, or a non-balancing overall reaction (ADR-0008).

**Why on-thesis.** The reaction extent ξ, static in a finished ledger and solved-from-mass-action in equilibrium, is now measured in
**moles of electrons, n**: "for redox, the ledger adds an electron ledger" (brief §). E°cell is **intensive** (energy per charge —
it does not scale with the coefficients, a machine-tested property), and ΔG° = −nFE° is the bridge from voltage to the same free
energy the thermochemistry tier computes.

**Consequences.** The tier opens on **`electrochemistry/daniell-cell`** — E°cell = 1.10 V, n = 2, ΔG° = −212 kJ/mol, spontaneous;
the misconception (the cell direction is a matter of how you write it) is refuted because the reduction potentials fix it (Cu²⁺/Cu at
+0.337 V sits above Zn²⁺/Zn at −0.7618 V → Cu²⁺ reduced, Zn oxidized; E°cell > 0). Six concepts — `redox` (the gateway, filling a
real Atlas gap — redox had only the ADR-0035 flag), `oxidation-number`, `half-reaction`, `electron-ledger`, `cell-potential`,
`standard-reduction-potential`. **427 producer tests** (+10); validate-solutions = **+1 electrochemistry** (22 ids); validate-reference
= **85** (+6 concepts); check-katex = **937**; **45 pages** (+1); the gate **9-way tamper-tested**; browser-verified (the cell renders
with oxidation numbers, both half-reactions, E°cell 1.099 V, ΔG° −212 kJ/mol, 0 KaTeX errors). Lessons now come in **seven shapes**
(reaction · structure · comparison · equilibrium · prediction · kinetics · **electrochemistry**). **Next in-tier:** the Nernst
equation (E away from standard conditions — the `galvanic` subtype extends to nonstandard), a `ΔG = −nFE` / Nernst formula-sheet
entry, and possibly a redox-balancing gym or more cells (concentration cell, electrolytic). This is the last Phase-2 tier to open —
a **Phase-2 definition of done** can now be firmed up.

## ADR-0051 — v1.0.0 QC pass, work package A: chemistry & source-provenance corrections (2026-07-09)

**Context.** A pre-v1.0.0 quality-control sweep (15-dimension multi-agent review, logged in `docs/sessions/2026-07-09.md`)
surfaced three high-severity learner-facing chemistry/honesty defects and a cluster of provenance mismatches — for a project
whose *product is the verification system*, a data-sourced badge whose named source contradicts the shipped value is a headline
defect. The owner resolved four decisions (O1–O4) before implementation; this ADR records the honesty-model-touching calls in
work package A (the rest of A is prose/label fixes needing no ADR). None changed a schema, the badge set, or house conventions.

**Decision.** (1) **Ksp source (O1):** adopt the OpenStax Appendix J values the file *claimed* to cite — CaF₂ 3.45×10⁻¹¹ → **4.0×10⁻¹¹**,
Mg(OH)₂ 5.61×10⁻¹² → **8.9×10⁻¹²** (the shipped CRC values were correct chemistry but not in the cited source). Single-source
coherence over a second authority; both prediction verdicts stay robust (CaF₂ 3600× above, Mg(OH)₂ 71× below). (2) **Electronegativity
source (O2):** the shipped values are the **revised-Pauling (Allred 1961)** scale, which OpenStax Fig 7.6 (classic single-decimal
Pauling, F 4.0) does not carry; keep the values, register **`allred-1961-electronegativity`** and repoint `data/elements.toml`. (3)
**Boiling points:** §10.1 teaches the CH₄≪NH₃≪H₂O trend (Fig 10.12) but prints no precise values, so the VALUES move to a new
**`nist-webbook-boiling-points`** source while §10.1 remains the trend's teaching source (the concept). (4) **Specific heats:** silver
(0.233, *absent* from the cited Table 5.1) is replaced by **silicon 0.712** (present in the table), keeping the dataset genuinely
single-sourced; Table 5.1 re-located §5.2 → §5.1. (5) **Oxidation-number concept regime:** its definitional core is the assignment
**rule hierarchy** (regime-3), so it is rebadged `ledger-exact` → **`rule-sourced`** + a registered source (OpenStax §4.1), matching
the `vsepr` precedent (ADR-0044) and `docs/regime-map.md`; the sum-to-charge accounting stays exact (regime-1) at the lesson level
(ADR-0050 unchanged), disclosed in the definition. (6) **Prediction regimes facet:** the shared `_regimes()` helper hardcoded "ICE
ledger" as the regime-1 facet, but a prediction runs no ICE solve — its accounting facet is overridden to **"dilution + reaction
quotient Q"**. (7) Two rendered chemistry-error fixes needing no source change: the first-order **half-life misconception** refutation
was inverted (a shrinking t½ signals order **< 1**, not higher order); and the **reaction-rate** concept vs the kinetics lessons used
two rate conventions differing by the coefficient a — now both disclose the per-species rate −d[A]/dt = k[A]ⁿ (k is A's disappearance
constant), matching OpenStax §12.4's own integration convention. (8) Temperatures recorded where the source states them (H₂O₂ k at
40 °C; the reduction-potential table's definitional 25 °C) and honestly disclosed absent where the source gives none.

**Why on-thesis.** The honesty model's core promise is "no claim ships unsourced or mislabeled, and every source resolves." A source
citation the named reference contradicts, or a rule-convention wearing a ledger-exact badge, breaks that promise as surely as a wrong
number would. These are honesty-layer corrections, not chemistry-content changes — every value stays chemically correct; what changes
is *what it is attributed to and how it is labeled*.

**Consequences.** Two new sources registered (`allred-1961-electronegativity`, `nist-webbook-boiling-points`); the `openstax-chemistry-2e`
register row shed electronegativity + boiling-point values and gained the §4.1 oxidation-number rules. 23 derived files regenerated
(deterministic); all **7 gates green**, **45 pages**, **427 producer tests** (8 value/source assertions updated to match). CaF₂ molar
solubility 2.05×10⁻⁴ → **2.15×10⁻⁴ M**, common-ion suppression 59 400× → **53 900×**, prediction margin 4170× → **3600×** — all still
comfortably one-directional. A new completeness-refutation branch in `SolutionPlayer` (`neutralization_leaves_excess`) makes the
"both reactants fully consumed" misconception fail in the ledger (limiting → 0, excess keeps 0.5 mmol) instead of rendering the
unrelated volume rebuttal. No schema, badge, or house-convention change. **Next:** work packages B (verification/gate hardening),
C (navigability), D (doc compression), then the Phase-2 depth (Arrhenius, Nernst) before the v1.0.0 tag.
