"""Acid/base + decomposition datasets: load, composition self-check, and lookups (ADR-0035)."""

from pathlib import Path

import pytest

from chemkernel import BuildError
from chemkernel.data import ChemData
from chemkernel.reactivity import AcidBase, Decomposition

ROOT = Path(__file__).resolve().parents[2]


def data():
    return ChemData.load(ROOT)


def test_acidbase_loads_and_self_checks():
    ab = AcidBase.load(ROOT)
    ab.validate(data())   # every acid = protons·H + anion; every base = cation + n·OH (raises on mismatch)
    assert ab.is_acid("HCl") and ab.is_acid("H2SO4") and ab.is_acid("H3PO4")
    assert ab.is_base("NaOH") and ab.is_base("Ca(OH)2")
    assert not ab.is_acid("NaCl") and not ab.is_base("HCl")
    assert ab.acid_name("HCl") == "hydrochloric acid"
    assert ab.base_name("NaOH") == "sodium hydroxide"
    assert ab.acids["H2SO4"]["protons"] == 2
    assert ab.acids["HC2H3O2"]["strength"] == "weak"


def test_acidbase_composition_mismatch_raises():
    d = data()
    bad = AcidBase({"HCl": {"name": "x", "strength": "strong", "protons": 2, "anion": "Cl^-"}}, {}, "src")
    with pytest.raises(BuildError):        # HCl is 1 H + Cl-, not 2
        bad.validate(d)
    bad2 = AcidBase({}, {"NaOH": {"name": "x", "strength": "strong", "cation": "Ca^2+"}}, "src")
    with pytest.raises(BuildError):        # NaOH is not Ca2+ + 2 OH
        bad2.validate(d)
    bad3 = AcidBase({"HX": {"name": "x", "strength": "strong", "protons": 1, "anion": "Xx^-"}}, {}, "src")
    with pytest.raises(BuildError):        # unknown anion
        bad3.validate(d)


def test_decomposition_loads_and_self_checks():
    dec = Decomposition.load(ROOT)
    dec.validate(data())
    assert "H2CO3" in dec.decompositions and "NH4OH" in dec.decompositions
    # carbonic acid decomposes to CO2 + water; its products present + gas emitted → justified
    just = dec.justifies(["NaCl", "H2O", "CO2"], ["CO2"])
    assert just is not None and just["gas"] == "CO2" and just["name"] == "carbonic acid"
    # a stray gas with no matching intermediate is NOT justified (can't fake gas evolution)
    assert dec.justifies(["NaCl", "O2"], ["O2"]) is None
    # water present but no gas emitted → not justified
    assert dec.justifies(["NaCl", "H2O", "CO2"], []) is None


def test_decomposition_gas_must_be_a_product():
    with pytest.raises(BuildError):
        Decomposition({"H2CO3": {"name": "x", "products": ["H2O"], "gas": "CO2", "note": "n"}}, "s").validate(data())
