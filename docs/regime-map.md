# Regime map — the breadth scope tracker

Every v1 topic (brief §15), classified by the regimes it spans (ADR-0003): **1** ledger-exact ·
**2** model-exact · **3** empirical/rule-sourced · **4** mechanistic/interpretive. A topic listing
regime 3 or 4 can never ship its rule/interpretive claims without badges. Status is hand-updated as
content lands (`lesson`, `atlas`, `practice`, combinations, or `—`). This table doubles as the coverage
dashboard; phases are defined in [`ROADMAP.md`](../ROADMAP.md).

| Topic | Regimes | Phase | Status |
|---|---|---|---|
| measurement, units, dimensional analysis | 1 | **1** | **gym** (solution conversions) + atlas (dimensional-analysis concept) |
| atoms, isotopes, average atomic mass | 1, 3 | 1 | — |
| mole concept & molar mass | 1, 3 | 1 | atlas (molar-mass concept) |
| ions & formula writing | 1, 3 | 1 | **gym** (nomenclature, both directions) + atlas (Valence Table; polyatomic-ion) |
| nomenclature (ionic, covalent, acids) | 1, 3 | **1** | **gym** (ionic, both directions — Stock system) + atlas (nomenclature concept) |
| periodic table & periodic trends | 3, 4 | 1 | atlas (Valence Table lens — positions + ion charges) |
| balancing equations | 1 | **1** | **gym** (balancing, conservation-matrix + charge tally) + atlas (balancing-equations concept) |
| reaction classes | 3, 4 | 1 | atlas (precipitation, net-ionic, solubility-rules, dissociation, spectator-ion concepts) |
| stoichiometry (mass/volume/solution/particle) | 1 | **1** | **2 gyms** (mass → mass; limiting reagent from masses) + atlas (stoichiometry, conservation-of-mass concepts) — particle stoich (Avogadro) → Phase 2 |
| limiting reagents | 1, 2 | **0** | **2 lessons, practice, gym, atlas** (Phase 0 slice + non-1:1 phosphate; limiting-from-mass gym) |
| percent yield | 1, 2 | **1** | **lesson + gym + atlas** (zinc-carbonate gravimetric lesson; percent-yield gym; percent-yield concept) |
| solutions & molarity | 1, 2 | **0** | **2 lessons** + atlas (molarity concept) |
| precipitation & net ionic equations | 1, 2, 3 | **0** | **2 lessons + atlas** (carbonate + calcium phosphate) |
| gases (ideal-gas model) | 1, 2 | 2+ | — |
| thermochemistry & calorimetry | 2, 3 | 2+ | — |
| electronic structure & configurations | 3, 4 | 2+ | — |
| bonding (ionic/covalent, electronegativity) | 3, 4 | 2+ | — |
| Lewis structures | 1, 4 | 2+ | — |
| VSEPR & polarity | 3, 4 | 2+ | — |
| intermolecular forces | 4 | 2+ | — |
| kinetics (rate laws, half-life) | 2, 3 | 2+ | — |
| equilibrium (ICE, K, Q) | 2, 3 | 2+ | — |
| acids & bases (pH, strength) | 2, 3 | 2+ | — |
| buffers & titrations | 2, 3 | 2+ | — |
| solubility equilibria (Ksp) | 2, 3 | 2+ | — |
| redox & oxidation states | 1, 3 | 2+ | — |
| electrochemistry (cells, E°, Nernst) | 1, 2, 3 | 2+ | — |
| organic lens (electron movement, functional-group preview) | 4 | 2+ | — |

Notes:

- Regime assignments are the *span* a topic touches; individual claims within a lesson get per-facet
  regime tags and per-claim badges in the solution object (architecture §solution-object).
- The organic lens is explanatory only — no synthesis content (ADR-0007, ROADMAP out-of-scope).
- Physical-chemistry seeds (extent, free energy, entropy-as-dispersal) appear inside host topics, not as
  standalone rows, until the owner opens a dedicated track.
