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
