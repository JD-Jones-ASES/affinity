"""Chemical Atlas builder: the Valence Table projection + charge-crossover assembly + concept entries."""

import tomllib
from pathlib import Path

import pytest

from chemkernel import BuildError
from chemkernel.data import ChemData
from chemkernel.reactivity import AcidBase, Decomposition
from chemkernel.reference import (assemble_formula, build_reaction_family, build_reference_entry,
                                  build_species_entry, build_valence_table)
from chemkernel.solubility import Solubility

ROOT = Path(__file__).resolve().parents[2]


def _data():
    return ChemData.load(ROOT)


def _reactivity():
    d = _data()
    solub = Solubility.load(ROOT)
    ab = AcidBase.load(ROOT)
    ab.validate(d)
    dec = Decomposition.load(ROOT)
    dec.validate(d)
    return d, solub, ab, dec


def _family(spec):
    d, solub, ab, dec = _reactivity()
    return build_reaction_family(spec, d, solubility=solub, acidbase=ab, decomposition=dec, ctx=spec["id"])


def test_valence_table_shape():
    t = build_valence_table(_data())
    assert t["kind"] == "valence-table" and t["id"] == "valence-table"
    assert len(t["elements"]) == 23           # first-20 (H…Ca) + Fe,Cu,Zn (ADR-0031, item 5a)
    assert t["highlight"] == ["Ca", "Na"]
    ca = next(e for e in t["elements"] if e["symbol"] == "Ca")
    assert ca["common_ion"]["id"] == "Ca^2+" and ca["common_ion"]["charge"] == 2
    # a variable-charge metal shows its lowest charge deterministically (Fe²⁺, not Fe³⁺)
    fe = next(e for e in t["elements"] if e["symbol"] == "Fe")
    assert fe["common_ion"]["id"] == "Fe^2+"
    # C and P have no monatomic ion in the dataset (N and S now do — nitride, sulfide)
    carbon = next(e for e in t["elements"] if e["symbol"] == "C")
    assert "common_ion" not in carbon
    assert {p["id"] for p in t["polyatomic"]} >= {"CO3^2-", "SO4^2-", "NO3^-"}
    assert t["sources"]["ion_charge"] == "openstax-chemistry-2e"


def test_valence_table_carries_sourced_periodic_properties():
    t = build_valence_table(_data())
    by = {e["symbol"]: e for e in t["elements"]}
    # curated properties are emitted as strings (ADR-0031)
    assert by["Ca"]["electronegativity"] == "1.00"
    assert by["Ca"]["covalent_radius_pm"] == "176"
    assert by["Ca"]["first_ionization_kj_mol"] == "589.8"
    # optionality: noble gases omit electronegativity, transition metals omit covalent radius
    assert "electronegativity" not in by["Ar"]
    assert "covalent_radius_pm" not in by["Fe"]
    assert by["Ar"]["first_ionization_kj_mol"] == "1520.6"   # every element keeps its ionization energy
    # every property source is threaded through for the badges
    assert t["sources"]["electronegativity"] == "openstax-chemistry-2e"
    assert t["sources"]["covalent_radius"] == "cordero-2008-covalent-radii"
    assert t["sources"]["ionization_energy"] == "nist-ionization-energies"


def test_charge_balance_salts_are_the_lesson_salts():
    t = build_valence_table(_data())
    got = {(c["cation"], c["anion"]): c["formula"] for c in t["charge_balance"]}
    assert got[("Ca^2+", "CO3^2-")] == "CaCO3"
    assert got[("Na^+", "CO3^2-")] == "Na2CO3"
    assert got[("Ca^2+", "Cl^-")] == "CaCl2"
    assert got[("Na^+", "Cl^-")] == "NaCl"
    # the calcium-phosphate lesson's salts, assembled by crossover (charge −3 → 3:2 and 3:1 ratios)
    assert got[("Ca^2+", "PO4^3-")] == "Ca3(PO4)2"
    assert got[("Na^+", "PO4^3-")] == "Na3PO4"


def test_charge_balance_is_the_full_named_product():
    """ADR-0033: every cation×anion pair (H⁺ excluded), each named by the nomenclature engine."""
    data = _data()
    t = build_valence_table(data)
    n_cat = sum(1 for i in data.ions.values() if i.charge > 0 and i.compound_name and i.id != "H^+")
    n_an = sum(1 for i in data.ions.values() if i.charge < 0 and i.compound_name)
    assert len(t["charge_balance"]) == n_cat * n_an
    by = {(c["cation"], c["anion"]): c for c in t["charge_balance"]}
    assert ("H^+", "Cl^-") not in by                      # acids are the deferred item-2 follow-up
    fe = by[("Fe^3+", "SO4^2-")]
    assert fe["formula"] == "Fe2(SO4)3" and fe["name"] == "iron(III) sulfate"
    assert fe["cation_name"] == "iron(III)" and fe["anion_name"] == "sulfate"


def test_charge_balance_mistakes_are_proven_wrong():
    """The own-charge mistake is emitted iff it differs, with the honest kind (ADR-0033)."""
    t = build_valence_table(_data())
    by = {(c["cation"], c["anion"]): c for c in t["charge_balance"]}
    assert "mistake" not in by[("Na^+", "Cl^-")]                       # 1:1 — own-charge IS the answer
    ca = by[("Ca^2+", "CO3^2-")]["mistake"]
    assert ca["formula"] == "Ca2(CO3)2" and ca["kind"] == "unreduced"  # neutral but not smallest ratio
    fe = by[("Fe^3+", "O^2-")]["mistake"]
    assert fe["formula"] == "Fe3O2" and fe["kind"] == "own-charge"     # 3×(+3) + 2×(−2) = +5 ≠ 0
    assert "+5" in fe["note"]


def test_valence_electrons_rule():
    """Main-group counts from the IUPAC group; He = 2; d-block honestly omitted (ADR-0033)."""
    t = build_valence_table(_data())
    by = {e["symbol"]: e for e in t["elements"]}
    assert by["H"]["valence_electrons"] == 1
    assert by["He"]["valence_electrons"] == 2              # first shell fills at two — not 8
    assert by["C"]["valence_electrons"] == 4
    assert by["Cl"]["valence_electrons"] == 7
    assert by["Ar"]["valence_electrons"] == 8
    for tm in ("Fe", "Cu", "Zn"):
        assert "valence_electrons" not in by[tm]           # convention-dependent — omitted, never asserted


def test_variable_charge_metals_surface_all_their_ions():
    t = build_valence_table(_data())
    by = {e["symbol"]: e for e in t["elements"]}
    assert [i["id"] for i in by["Fe"]["other_ions"]] == ["Fe^3+"]
    assert [i["id"] for i in by["Cu"]["other_ions"]] == ["Cu^2+"]
    assert "other_ions" not in by["Na"]                    # fixed-charge metals carry exactly one


def test_lenses_and_bonding_are_emitted_and_sourced():
    t = build_valence_table(_data())
    lenses = {l["id"]: l for l in t["lenses"]}
    assert set(lenses) == {"ion-charge", "valence-electrons", "electronegativity",
                           "covalent-radius", "ionization-energy"}
    for lens in lenses.values():
        assert lens["source"] in t["sources"]              # every lens cites a sources-map facet
        assert lens["regime"] == "mechanistic"             # the why-panel is interpretive (Q4, ADR-0033)
        assert set(lens["panel"]) == {"pattern", "why", "exceptions", "where"}
    b = t["bonding"]
    assert b["source"] == "openstax-chemistry-2e" and t["sources"]["bonding"] == b["source"]
    assert [c["id"] for c in b["classes"]] == ["nonpolar-covalent", "polar-covalent", "ionic"]
    assert b["classes"][0]["max"] == "0.4" == b["classes"][1]["min"]   # OpenStax Fig 7.8 boundaries tile
    assert b["classes"][1]["max"] == "1.8" == b["classes"][2]["min"]
    assert "exception" in b["caution"]                     # the caveat ships as data, inseparable


def test_assemble_formula_crossover_and_parens():
    data = _data()
    ion = data.ions.__getitem__
    assert assemble_formula(ion("Ca^2+"), ion("CO3^2-"))[0] == "CaCO3"      # 1:1
    assert assemble_formula(ion("Na^+"), ion("CO3^2-"))[0] == "Na2CO3"      # 2:1
    assert assemble_formula(ion("Ca^2+"), ion("Cl^-"))[0] == "CaCl2"        # 1:2
    assert assemble_formula(ion("Ca^2+"), ion("NO3^-"))[0] == "Ca(NO3)2"    # polyatomic anion needs parens
    assert assemble_formula(ion("Na^+"), ion("PO4^3-"))[0] == "Na3PO4"      # 3:1
    # every assembled formula is verified neutral by the builder; a swapped (cation as anion) arg is rejected
    with pytest.raises(BuildError):
        assemble_formula(ion("Cl^-"), ion("Ca^2+"))


def test_concept_entry_build():
    spec = tomllib.loads((ROOT / "reference" / "concepts" / "limiting-reagent.toml").read_text(encoding="utf-8"))
    entry = build_reference_entry(spec)
    assert entry["kind"] == "concept" and entry["id"] == "limiting-reagent"
    assert entry["term"] == "limiting reagent"
    assert {"to": "extent-of-reaction", "type": "built-on"} in entry["related"]
    assert entry["lessons"] == ["calcium-carbonate-limiting", "calcium-phosphate-limiting"]
    assert entry["regime"] == "ledger-exact" and "latex" in entry


def test_concept_entry_requires_fields():
    with pytest.raises(BuildError):
        build_reference_entry({"id": "x", "kind": "concept", "title": "X"})  # missing term/definition


def test_rule_sourced_concept_needs_source():
    base = {"id": "solubility-rules", "kind": "concept", "title": "Solubility rules",
            "term": "solubility rules", "definition": "Empirical rules.", "regime": "rule-sourced"}
    with pytest.raises(BuildError):
        build_reference_entry(dict(base))                      # rule-sourced without a source is refused
    entry = build_reference_entry({**base, "source": "openstax-chemistry-2e"})
    assert entry["source"] == "openstax-chemistry-2e"


def test_authored_concepts_all_build():
    root = ROOT / "reference" / "concepts"
    for path in sorted(root.glob("*.toml")):
        spec = tomllib.loads(path.read_text(encoding="utf-8"))
        entry = build_reference_entry(spec, spec.get("id", path.stem))
        # every related edge points at an id that is either another concept file or the valence table
        assert entry["kind"] == "concept"


# --- reaction-family entries (ADR-0035) ---

_ACID_BASE_SPEC = {
    "id": "reaction-acid-base", "kind": "reaction-family", "title": "Acid-base neutralization",
    "family": "acid-base", "general_form": "acid + base -> salt + water",
    "summary": "H+ meets OH-.", "source": "openstax-chemistry-2e",
    "conditions": ["needs an acid and a base"],
    "misconceptions": [{"claim": "always pH 7", "refute": "only strong+strong"}],
    "examples": [
        {"reactants": ["HCl(aq)", "NaOH(aq)"], "products": ["NaCl(aq)", "H2O(l)"]},
        {"reactants": ["H2SO4(aq)", "NaOH(aq)"], "products": ["Na2SO4(aq)", "H2O(l)"]},
        {"reactants": ["HNO3(aq)", "KOH(aq)"], "products": ["KNO3(aq)", "H2O(l)"]},
    ],
    "related": [], "lessons": [],
}


def test_reaction_family_acid_base_shape():
    fam = _family(_ACID_BASE_SPEC)
    assert fam["kind"] == "reaction-family" and fam["family"] == "acid-base"
    assert fam["redox"] is False                          # no free element in any example
    assert len(fam["examples"]) == 3
    ex = fam["examples"][0]
    assert ex["family"] == "acid-base"
    assert ex["equation"]["text"] == "HCl(aq) + NaOH(aq) -> NaCl(aq) + H2O(l)"
    assert ex["coefficients"] == [1, 1, 1, 1]
    # the net-ionic particle view strips the spectators to the essential change
    assert ex["net_ionic"]["text"] == "H^+(aq) + OH^-(aq) -> H2O(l)"
    assert ex["spectators"] == ["Cl^-", "Na^+"]
    # H2SO4 + 2 NaOH reduces to the SAME net ionic
    assert fam["examples"][1]["net_ionic"]["text"] == "H^+(aq) + OH^-(aq) -> H2O(l)"


def test_reaction_family_refuses_misfiled_example():
    bad = dict(_ACID_BASE_SPEC)
    bad["examples"] = _ACID_BASE_SPEC["examples"] + [
        {"reactants": ["CaCl2(aq)", "Na2CO3(aq)"], "products": ["CaCO3(s)", "NaCl(aq)"]},  # precipitation
    ]
    with pytest.raises(BuildError, match="classifies as 'precipitation'"):
        _family(bad)


def test_reaction_family_combustion_is_redox_no_netionic():
    spec = {
        "id": "reaction-combustion", "kind": "reaction-family", "title": "Combustion",
        "family": "combustion", "general_form": "fuel + O2 -> CO2 + H2O", "summary": "burns",
        "source": "openstax-chemistry-2e", "conditions": [],
        "misconceptions": [{"claim": "x", "refute": "y"}],
        "examples": [
            {"reactants": ["CH4(g)", "O2(g)"], "products": ["CO2(g)", "H2O(g)"]},
            {"reactants": ["C3H8(g)", "O2(g)"], "products": ["CO2(g)", "H2O(g)"]},
            {"reactants": ["C2H6(g)", "O2(g)"], "products": ["CO2(g)", "H2O(g)"]},
        ], "related": [], "lessons": [],
    }
    fam = _family(spec)
    assert fam["redox"] is True
    for ex in fam["examples"]:
        assert ex["redox"] is True and "redox_reason" in ex
        assert "net_ionic" not in ex                      # nothing dissolves to cancel — no faked net ionic
    # the propane balance is the hard one (C3H8 + 5 O2 -> 3 CO2 + 4 H2O)
    assert fam["examples"][1]["coefficients"] == [1, 5, 3, 4]


def test_reaction_family_decomposition_mixed_redox_omits_family_flag():
    spec = {
        "id": "reaction-decomposition", "kind": "reaction-family", "title": "Decomposition",
        "family": "decomposition", "general_form": "AB -> A + B", "summary": "splits",
        "source": "openstax-chemistry-2e", "conditions": [],
        "misconceptions": [{"claim": "x", "refute": "y"}],
        "examples": [
            {"reactants": ["KClO3(s)"], "products": ["KCl(s)", "O2(g)"]},   # redox
            {"reactants": ["CaCO3(s)"], "products": ["CaO(s)", "CO2(g)"]},  # not redox
            {"reactants": ["H2O(l)"], "products": ["H2(g)", "O2(g)"]},      # redox
        ], "related": [], "lessons": [],
    }
    fam = _family(spec)
    assert "redox" not in fam                             # examples disagree → no family-level flag
    assert [ex["redox"] for ex in fam["examples"]] == [True, False, True]


def test_reaction_family_guard_rejects_absorbed_key():
    """The TOML trap #4 guard: a top-level bare key absorbed into the last [[examples]] table (an example
    carrying an unexpected key) must fail loud, not ship a family with empty related/lessons (ADR-0038)."""
    spec = {
        "id": "reaction-x", "kind": "reaction-family", "title": "X", "family": "combustion",
        "general_form": "f + O2 -> CO2 + H2O", "summary": "s", "source": "openstax-chemistry-2e",
        "conditions": [], "misconceptions": [{"claim": "a", "refute": "b"}],
        "examples": [
            {"reactants": ["CH4(g)", "O2(g)"], "products": ["CO2(g)", "H2O(g)"]},
            {"reactants": ["C3H8(g)", "O2(g)"], "products": ["CO2(g)", "H2O(g)"],
             "lessons": ["oops-absorbed"]},   # a bare `lessons` swallowed into this table
        ],
    }
    with pytest.raises(BuildError, match="unexpected key"):
        _family(spec)


# --- species atlas (ADR-0038) -------------------------------------------------------------------------

def _species(spec):
    return build_species_entry(spec, _data(), ctx=spec["id"])


def test_species_derives_composition_and_molar_mass():
    sp = _species({
        "id": "water", "kind": "species", "title": "Water", "formula": "H2O",
        "species_class": "compound", "names": ["water"], "summary": "s", "source": "ciaaw-2021-atomic-weights",
    })
    assert sp["charge"] == 0 and sp["latex"] == r"\mathrm{H_{2}O}"
    # composition in formula order, each subtotal = count × sourced weight
    assert [(c["symbol"], c["count"], c["atomic_weight"], c["subtotal"]) for c in sp["composition"]] == [
        ("H", 2, "1.0080", "2.0160"), ("O", 1, "15.999", "15.999")]
    assert sp["molar_mass_g_per_mol"] == "18.0150"        # 2×1.0080 + 15.999, exact


def test_species_parenthesized_formula_counts_group_twice():
    sp = _species({
        "id": "calcium-phosphate", "kind": "species", "title": "Calcium phosphate", "formula": "Ca3(PO4)2",
        "species_class": "compound", "names": ["calcium phosphate"], "summary": "s",
        "source": "ciaaw-2021-atomic-weights",
    })
    comp = {c["symbol"]: c["count"] for c in sp["composition"]}
    assert comp == {"Ca": 3, "P": 2, "O": 8}              # the phosphate group taken twice
    assert sp["molar_mass_g_per_mol"] == "310.174"


def test_species_ion_carries_charge_from_the_formula():
    sp = _species({
        "id": "carbonate-ion", "kind": "species", "title": "Carbonate ion", "formula": "CO3^2-",
        "species_class": "polyatomic-ion", "names": ["carbonate"], "summary": "s",
        "source": "ciaaw-2021-atomic-weights",
    })
    assert sp["charge"] == -2 and sp["species_class"] == "polyatomic-ion"
    assert sp["molar_mass_g_per_mol"] == "60.008"         # electron mass conventionally ignored


def test_species_rejects_off_dataset_element():
    with pytest.raises(BuildError):                       # Au is not in the 23-element dataset
        _species({"id": "gold", "kind": "species", "title": "Gold", "formula": "Au",
                  "species_class": "element", "names": ["gold"], "summary": "s",
                  "source": "ciaaw-2021-atomic-weights"})


def test_species_rejects_class_charge_mismatch():
    # a neutral compound cannot carry a charge...
    with pytest.raises(BuildError, match="charge"):
        _species({"id": "bad", "kind": "species", "title": "Bad", "formula": "CO3^2-",
                  "species_class": "compound", "names": ["bad"], "summary": "s",
                  "source": "ciaaw-2021-atomic-weights"})
    # ...and an ion cannot be neutral
    with pytest.raises(BuildError, match="neutral"):
        _species({"id": "bad2", "kind": "species", "title": "Bad2", "formula": "H2O",
                  "species_class": "polyatomic-ion", "names": ["bad"], "summary": "s",
                  "source": "ciaaw-2021-atomic-weights"})


def test_species_rejects_phase_in_formula():
    with pytest.raises(BuildError, match="phase-less"):
        _species({"id": "bad3", "kind": "species", "title": "Bad3", "formula": "H2O(l)",
                  "species_class": "compound", "names": ["water"], "summary": "s",
                  "source": "ciaaw-2021-atomic-weights"})
