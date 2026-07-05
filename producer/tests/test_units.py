"""Quantity & units engine: conversions and dimension tracking, values hand-checked."""

from decimal import Decimal

import pytest

from chemkernel import BuildError
from chemkernel.units import Dim, Quantity as Q


def test_construct_and_convert():
    v = Q.of(Decimal("25.0"), "mL")
    assert v.value == Decimal("25.0")
    assert v.to("L").value == Decimal("0.025")


def test_moles_from_volume_times_molarity():
    # 25.0 mL * 0.100 mol/L = 0.00250 mol  (units cancel to amount)
    n = Q.of(Decimal("25.0"), "mL") * Q.of(Decimal("0.100"), "M")
    assert n.dim == Dim(amount=1)
    assert n.label == "mol"
    assert n.value == Decimal("0.00250")


def test_mass_from_moles_times_molar_mass():
    # 0.00250 mol * 100.086 g/mol = 0.250215 g
    m = Q.of(Decimal("0.00250"), "mol") * Q.of(Decimal("100.086"), "g/mol")
    assert m.dim == Dim(mass=1) and m.label == "g"
    assert m.value == Decimal("0.250215")


def test_unit_prefix_conversion():
    assert Q.of(Decimal("0.00250"), "mol").to("mmol").value == Decimal("2.50")


def test_dimension_mismatch_conversion_raises():
    with pytest.raises(BuildError):
        Q.of(1, "mol").to("L")


def test_add_incompatible_raises():
    with pytest.raises(BuildError):
        Q.of(1, "mol") + Q.of(1, "g")


def test_unknown_unit_raises():
    with pytest.raises(BuildError):
        Q.of(1, "furlong")
