"""Equation balancer: coefficients hand-checked against known textbook reactions, including a charge-
balanced net ionic equation and deliberately unbalanceable inputs."""

import pytest

from chemkernel import BuildError
from chemkernel.balance import balance
from chemkernel.formula import parse_formula as P


def test_precipitation_molecular_phase0():
    # CaCl2 + Na2CO3 -> CaCO3 + 2 NaCl   (the Phase 0 scenario)
    coeffs = balance([P("CaCl2"), P("Na2CO3")], [P("CaCO3"), P("NaCl")])
    assert coeffs == [1, 1, 1, 2]


def test_combustion_of_methane():
    # CH4 + 2 O2 -> CO2 + 2 H2O
    coeffs = balance([P("CH4"), P("O2")], [P("CO2"), P("H2O")])
    assert coeffs == [1, 2, 1, 2]


def test_net_ionic_uses_charge_row():
    # Ca^2+ + CO3^2- -> CaCO3(s)   balances only because charge is conserved (2 + -2 = 0)
    coeffs = balance([P("Ca^2+"), P("CO3^2-")], [P("CaCO3(s)")])
    assert coeffs == [1, 1, 1]


def test_reduces_to_smallest_integers():
    # H2 + O2 -> H2O  ->  2 H2 + O2 -> 2 H2O, not [4,2,4]
    coeffs = balance([P("H2"), P("O2")], [P("H2O")])
    assert coeffs == [2, 1, 2]


def test_unbalanceable_raises():
    with pytest.raises(BuildError):
        balance([P("H2")], [P("O2")])


def test_charge_mismatch_raises():
    # Na^+ -> Na  cannot conserve charge
    with pytest.raises(BuildError):
        balance([P("Na^+")], [P("Na")])
