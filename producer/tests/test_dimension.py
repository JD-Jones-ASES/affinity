"""SI dimensional-homogeneity engine (ADR-0039) — the machine-checkable honesty for the formula sheet."""

import pytest

from chemkernel import BuildError
from chemkernel import dimension as dim


def test_bases_order_is_the_committed_contract():
    # the emitted vectors are length-6 in this fixed order; changing it is a schema/gate break
    assert dim.BASES == ("mass", "length", "time", "amount", "temperature", "current")
    assert dim.DIMENSIONLESS == (0, 0, 0, 0, 0, 0)


def test_unit_dimensions_are_the_si_signatures():
    assert dim.unit_dimension("mol") == (0, 0, 0, 1, 0, 0)
    assert dim.unit_dimension("g") == (1, 0, 0, 0, 0, 0)
    assert dim.unit_dimension("L") == (0, 3, 0, 0, 0, 0)            # a volume is length³
    assert dim.unit_dimension("M") == (0, -3, 0, 1, 0, 0)          # mol/L
    assert dim.unit_dimension("atm") == (1, -1, -2, 0, 0, 0)       # pressure
    assert dim.unit_dimension("J") == (1, 2, -2, 0, 0, 0)          # energy
    # R has the SAME dimension whether written in SI or in gas-law teaching units
    assert dim.unit_dimension("J/(mol*K)") == dim.unit_dimension("L*atm/(mol*K)")
    assert dim.unit_dimension("") == dim.DIMENSIONLESS


def test_unknown_unit_refuses():
    with pytest.raises(BuildError, match="unknown unit"):
        dim.unit_dimension("furlong")


def test_pv_and_nrt_both_reduce_to_energy():
    P, V = dim.unit_dimension("atm"), dim.unit_dimension("L")
    n, R, T = dim.unit_dimension("mol"), dim.unit_dimension("L*atm/(mol*K)"), dim.unit_dimension("K")
    pv = dim.term_dimension([(P, 1), (V, 1)])
    nrt = dim.term_dimension([(n, 1), (R, 1), (T, 1)])
    assert pv == nrt == (1, 2, -2, 0, 0, 0)
    assert dim.dimension_name(pv) == "energy"


def test_mole_mass_and_calorimetry_homogeneous():
    # n = m / M  → both amount
    n = dim.term_dimension([(dim.unit_dimension("mol"), 1)])
    m_over_M = dim.term_dimension([(dim.unit_dimension("g"), 1), (dim.unit_dimension("g/mol"), -1)])
    assert n == m_over_M == (0, 0, 0, 1, 0, 0)
    # q = m c ΔT → both energy
    q = dim.term_dimension([(dim.unit_dimension("J"), 1)])
    mcdt = dim.term_dimension([(dim.unit_dimension("g"), 1), (dim.unit_dimension("J/(g*K)"), 1),
                               (dim.unit_dimension("K"), 1)])
    assert q == mcdt == (1, 2, -2, 0, 0, 0)


def test_dimension_name_falls_back_to_exponents():
    assert dim.dimension_name(dim.DIMENSIONLESS) == "dimensionless"
    assert dim.dimension_name((1, 0, 0, 0, 0, 0)) == "mass"
    # an unnamed composite renders as a compact exponent string, never a fabricated unit
    assert "mass^2" in dim.dimension_name((2, 0, 0, 0, 0, 0))
