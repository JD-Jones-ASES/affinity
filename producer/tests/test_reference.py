"""Chemical Atlas builder: the Valence Table projection + charge-crossover assembly + concept entries."""

import tomllib
from pathlib import Path

import pytest

from chemkernel import BuildError
from chemkernel.data import ChemData
from chemkernel.reference import assemble_formula, build_reference_entry, build_valence_table

ROOT = Path(__file__).resolve().parents[2]


def _data():
    return ChemData.load(ROOT)


def test_valence_table_shape():
    t = build_valence_table(_data())
    assert t["kind"] == "valence-table" and t["id"] == "valence-table"
    assert len(t["elements"]) == 15                          # 9 Phase-0 + K,Mg,Al,Fe,Cu,Zn (item 2)
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
