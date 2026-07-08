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
