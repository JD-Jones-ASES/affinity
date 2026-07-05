"""Dataset loading + self-consistency. Values hand-checked against CIAAW abridged atomic weights;
molar masses computed independently here, not by re-reading the producer's own output."""

from decimal import Decimal
from pathlib import Path

import pytest

from chemkernel import BuildError
from chemkernel.data import ChemData

ROOT = Path(__file__).resolve().parents[2]


def data():
    return ChemData.load(ROOT)


def test_loads_and_self_validates():
    d = data()  # ChemData.load() runs validate(); a bad dataset would raise here
    assert d.elements["Ca"].Z == 20
    assert d.elements["Ca"].atomic_weight == Decimal("40.078")
    assert d.elements["Cl"].atomic_weight == Decimal("35.45")
    assert d.elements["Na"].group == 1 and d.elements["Na"].period == 3


def test_atomic_weights_are_decimal_not_float():
    d = data()
    for el in d.elements.values():
        assert isinstance(el.atomic_weight, Decimal)


def test_avogadro_constant_loaded_exact():
    d = data()  # the 2019 SI redefinition fixed N_A exactly (ADR-0006); read as Decimal, never float
    assert isinstance(d.avogadro, Decimal)
    assert d.avogadro == Decimal("6.02214076e23")
    assert d.sources["constants"] == "bipm-si-2019"


def test_molar_mass_caco3_matches_hand_value():
    # 40.078 + 12.011 + 3*15.999 = 100.086  (brief quotes 100.09 to 2 dp)
    d = data()
    assert d.molar_mass("CaCO3") == Decimal("100.086")
    assert d.molar_mass("CaCO3").quantize(Decimal("0.01")) == Decimal("100.09")


def test_molar_mass_cacl2_and_na2co3():
    d = data()
    assert d.molar_mass("CaCl2") == Decimal("40.078") + 2 * Decimal("35.45")   # 110.978
    assert d.molar_mass("Na2CO3") == 2 * Decimal("22.990") + Decimal("12.011") + 3 * Decimal("15.999")


def test_unknown_element_raises():
    d = data()
    with pytest.raises(BuildError):
        d.molar_mass("Xe")  # xenon not in the minimal dataset


def test_every_ion_composition_is_known():
    d = data()
    assert d.ions["CO3^2-"].charge == -2
    assert d.ions["Ca^2+"].kind == "monatomic" and d.ions["Ca^2+"].element == "Ca"
    # every ion formula must be composed of elements present in elements.toml (validate() guarantees this)
    from chemkernel.formula import parse_formula
    for ion in d.ions.values():
        for el in parse_formula(ion.formula).counts:
            assert el in d.elements
