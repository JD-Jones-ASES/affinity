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


def test_gas_law_product_lands_in_volume():
    # nRT/P through the units engine (ADR-0040): the dimensions cancel to a volume, and the value is the gas
    # volume in L.
    # n=1 mol, R=0.082057 L·atm/(mol·K), T=273 K, P=1 atm → V ≈ 22.4 L (units certified, not asserted).
    n = Q.of(Decimal("1"), "mol")
    R = Q.of(Decimal("0.0820573660809596"), "L*atm/(mol*K)")
    T = Q.of(Decimal("273"), "K")
    P = Q.of(Decimal("1"), "atm")
    V = (n * R * T / P).to("L")
    assert V.dim == Dim(volume=1)
    assert abs(V.value - Decimal("22.4")) < Decimal("0.05")


def test_pressure_and_temperature_are_distinct_dimensions():
    assert Q.of(1, "atm").dim == Dim(pressure=1)
    assert Q.of(1, "K").dim == Dim(temperature=1)
    with pytest.raises(BuildError):                             # atm and K are not interconvertible
        Q.of(1, "atm").to("K")


def test_calorimetry_product_lands_in_energy():
    # q = m·c·ΔT through the units engine (ADR-0042): g × J·g⁻¹·K⁻¹ × K → J, dimensions certified.
    # 50 g water, c=4.184 J/(g·K), ΔT=20 K → q = 4184 J (units certified, not asserted).
    m = Q.of(Decimal("50"), "g")
    c = Q.of(Decimal("4.184"), "J/(g*K)")
    dT = Q.of(Decimal("20"), "K")
    q = (m * c * dT).to("J")
    assert q.dim == Dim(energy=1)
    assert q.value == Decimal("4184")
    # solving back for the specific heat lands in J/(g·K)
    c_back = (q / (m * dT)).to("J/(g*K)")
    assert c_back.dim == Dim(energy=1, mass=-1, temperature=-1)
    assert c_back.value == Decimal("4.184")


def test_energy_is_independent_of_pressure_volume():
    # the chemistry-bookkeeping basis keeps energy separate from pressure·volume (ADR-0042): a gas-law product
    # (L·atm) and a calorimetry heat (J) never silently equate.
    assert Q.of(1, "J").dim == Dim(energy=1)
    assert Q.of(1, "J").dim != Dim(pressure=1, volume=1)
    with pytest.raises(BuildError):
        Q.of(1, "J").to("L*atm/(mol*K)")


def test_reaction_enthalpy_times_extent_lands_in_energy():
    # the energy ledger (ADR-0043): q = ΔH_rxn·ξ through the units engine — kJ·mol⁻¹ × mol → kJ, dimensions
    # certified. ΔH_rxn = −890.57 kJ/mol, ξ = 0.05 mol → q = −44.5285 kJ (exact; a molar enthalpy is energy/amount).
    dH = Q.of(Decimal("-890.57"), "kJ/mol")
    assert dH.dim == Dim(energy=1, amount=-1)
    xi = Q.of(Decimal("0.05"), "mol")
    q = (dH * xi).to("kJ")
    assert q.dim == Dim(energy=1)
    assert q.value == Decimal("-44.5285")
