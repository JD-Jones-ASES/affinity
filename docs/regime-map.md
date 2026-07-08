# Regime map — the breadth scope tracker

Every v1 topic (brief §15), classified by the regimes it spans (ADR-0003): **1** ledger-exact ·
**2** model-exact · **3** empirical/rule-sourced · **4** mechanistic/interpretive. A topic listing
regime 3 or 4 can never ship its rule/interpretive claims without badges. Status is hand-updated as
content lands (`lesson`, `atlas`, `practice`, combinations, or `—`). This table doubles as the coverage
dashboard; phases are defined in [`ROADMAP.md`](../ROADMAP.md).

| Topic | Regimes | Phase | Status |
|---|---|---|---|
| measurement, units, dimensional analysis | 1 | **1** | **gym** (solution conversions) + atlas (dimensional-analysis concept) |
| atoms, isotopes, average atomic mass | 1, 3 | **1** | **atlas** (average-atomic-mass concept — the abundance-weighted mean of isotope masses, exact arithmetic over sourced CIAAW data; the species atlas shows those atomic weights summed into every molar mass — ADR-0038) |
| mole concept & molar mass | 1, 3 | 1 | **atlas** (molar-mass concept + the **species atlas** — every entry's molar mass derived by re-summing the sourced atomic weights, ADR-0038; **formula sheet** — mole–mass $n=m/M$ and Avogadro $N=n\,N_A$, dimensionally verified, ADR-0039) |
| ions & formula writing | 1, 3 | 1 | **gym** (nomenclature, both directions) + **atlas** (Valence Table; polyatomic-ion concept; species entries for the carbonate/hydroxide ions with derived composition + molar mass) |
| nomenclature (ionic, covalent, acids) | 1, 3 | **1** | **gym** (ionic, both directions — Stock system) + atlas (nomenclature concept) |
| periodic table & periodic trends | 3, 4 | **1** | **gym + atlas** (Valence Table flagship: five lenses with interpretive pattern panels, trend graphs, the 156-salt formula builder, ΔEN bonding mode — ADR-0031/0033; `periodic-trends` gym drilled from the same data, exceptions named — ADR-0034; periodic-trends/electronegativity/ionization-energy concepts) |
| balancing equations | 1 | **1** | **gym** (balancing, conservation-matrix + charge tally) + atlas (balancing-equations concept) |
| reaction classes | 3, 4 | **1** | **lesson + gym + atlas** (acid-base neutralization lesson — ADR-0037; `reaction_families_v1` gym: classify-the-family + name-the-spectators — ADR-0036; **7 reaction-family Atlas entries** / 21 engine-classified example reactions with net-ionic views + free-element redox — ADR-0035; precipitation/net-ionic/solubility-rules/dissociation/spectator-ion concepts) |
| stoichiometry (mass/volume/solution/particle) | 1 | **1** | **2 gyms** (mass → mass; limiting reagent from masses) + atlas (stoichiometry, conservation-of-mass concepts) — particle stoich (Avogadro) → Phase 2 |
| limiting reagents | 1, 2 | **0** | **2 lessons, practice, gym, atlas** (Phase 0 slice + non-1:1 phosphate; limiting-from-mass gym) |
| percent yield | 1, 2 | **1** | **lesson + gym + atlas** (zinc-carbonate gravimetric lesson; percent-yield gym; percent-yield concept + formula-sheet entry, ADR-0039) |
| solutions & molarity | 1, 2 | **0** | **2 lessons** + atlas (molarity concept + formula sheet: molarity $c=n/V$, dilution $M_1V_1=M_2V_2$ — ADR-0039) |
| precipitation & net ionic equations | 1, 2, 3 | **0** | **2 lessons + atlas** (carbonate + calcium phosphate) |
| gases (ideal-gas model) | 1, 2 | **2** | **lesson + gym + atlas** (`gas-stoichiometry/zinc-hydrochloric-hydrogen` lesson: the extent ledger drives a gas volume via PV=nRT — a weighed-mass given + a `result.gas` block, moles ledger-exact / volume model-exact-then-rounded under the model-assumed badge, check-ledger re-derives V=nRT/P — ADR-0041; `gas_laws_v1` gym: PV=nRT + combined gas law, solve for any variable — ADR-0040; formula sheet: ideal gas law + combined gas law, dimensional homogeneity machine-checked — ADR-0039) |
| thermochemistry & calorimetry | 2, 3 | **2** | **lesson + gym + atlas** (`thermochemistry/methane-combustion-enthalpy` lesson: the extent ledger drives an **energy** — $q = \Delta H_\text{rxn}\cdot\xi$, with $\Delta H_\text{rxn}$ from **Hess's law** over sourced $\Delta H_f^\circ$ (`data/formation-enthalpies.toml`, OpenStax Appendix G); `build.py`'s fourth reported-product shape (`result.energy`), the first fully molecular lesson, triple-badged (machine-checked ξ + data-sourced ΔH_f° + model-assumed Hess), $q$ exact — ADR-0043; `calorimetry_v1` gym: $q=mc\Delta T$, sourced specific heats, both honesty badges — ADR-0042; formula sheet: calorimetry $q=mc\Delta T$ + **Hess's law** $\Delta H_\text{rxn}=\sum\nu\Delta H_f^\circ$ (both sides molar energy, machine-checked — ADR-0043); `reaction-enthalpy` concept). Endothermic + multi-step Hess-cycle lessons follow |
| electronic structure & configurations | 3, 4 | 2+ | — |
| bonding (ionic/covalent, electronegativity) | 3, 4 | 2+ | **atlas + gym**: the Valence Table's bonding mode (sourced ΔEN classification + caution, ADR-0033) + per-bond ΔEN on every molecule Atlas entry (ADR-0044); IMFs stay Phase 2+ |
| Lewis structures | 1, 4 | 2 | **atlas** (molecule kind, ADR-0044): the **Lewis electron ledger** — valence total, octet/duet, formal charge, and their conservation — **machine-checked** (exact integer accounting, re-derived in pure Node); octet exceptions + resonance deferred |
| VSEPR & polarity | 3, 4 | 2 | **atlas** (molecule kind, ADR-0044): VSEPR geometry from the sourced `data/vsepr.toml` table keyed on the machine-derived electron-domain count; molecular polarity authored + disclosed (model-assumed, neutral molecules) |
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
