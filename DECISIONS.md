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
