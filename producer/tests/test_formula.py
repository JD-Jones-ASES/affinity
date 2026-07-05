"""Formula parser: counts, charge, phase, LaTeX. Expected values written out by hand."""

import pytest

from chemkernel import BuildError
from chemkernel.formula import parse_formula


def test_simple_binary():
    f = parse_formula("CaCl2")
    assert f.counts == {"Ca": 1, "Cl": 2}
    assert f.charge == 0 and f.phase is None
    assert f.latex == r"\mathrm{CaCl_{2}}"        # upright per ADR-0025


def test_polyatomic_counts():
    f = parse_formula("Na2CO3")
    assert f.counts == {"Na": 2, "C": 1, "O": 3}
    assert f.charge == 0


def test_parentheses_group_multiplies():
    f = parse_formula("Ca(OH)2")
    assert f.counts == {"Ca": 1, "O": 2, "H": 2}
    assert f.latex == r"\mathrm{Ca(OH)_{2}}"


def test_nested_and_polyatomic_multiplier():
    # (NH4)2SO4 -> N2 H8 S1 O4
    f = parse_formula("(NH4)2SO4")
    assert f.counts == {"N": 2, "H": 8, "S": 1, "O": 4}


def test_cation_charge():
    f = parse_formula("Na^+")
    assert f.counts == {"Na": 1} and f.charge == 1


def test_polyatomic_anion_charge_and_latex():
    f = parse_formula("CO3^2-")
    assert f.counts == {"C": 1, "O": 3} and f.charge == -2
    assert f.latex == r"\mathrm{CO_{3}}^{2-}"     # charge superscripts the upright group


def test_phase_stripped():
    f = parse_formula("CaCO3(s)")
    assert f.counts == {"Ca": 1, "C": 1, "O": 3}
    assert f.phase == "s"


def test_phase_and_charge_together():
    f = parse_formula("SO4^2-(aq)")
    assert f.counts == {"S": 1, "O": 4}
    assert f.charge == -2 and f.phase == "aq"


def test_empty_raises():
    with pytest.raises(BuildError):
        parse_formula("   ")


def test_unbalanced_parens_raises():
    with pytest.raises(BuildError):
        parse_formula("Ca(OH2")


def test_leading_junk_raises():
    with pytest.raises(BuildError):
        parse_formula("2CaCl2")  # a coefficient is not part of a formula
