"""Extent solver & species ledger. Amounts hand-checked against the Phase-0 scenario (brief §16):
25.0 mL 0.100 M CaCl2 + 20.0 mL 0.150 M Na2CO3 -> 0.250 g CaCO3, Ca limiting, CO3 left over."""

from decimal import Decimal
from fractions import Fraction
from pathlib import Path

import pytest

from chemkernel import BuildError
from chemkernel.data import ChemData
from chemkernel.extent import solve_extent, species_mass_g, to_decimal
from chemkernel.formula import parse_formula as P
from chemkernel.units import Quantity as Q

ROOT = Path(__file__).resolve().parents[2]

# initial moles: 0.0250 L * 0.100 M = 0.00250 ; 0.0200 L * 0.150 M = 0.00300
N_CACL2 = Fraction(1, 400)     # 0.00250
N_NA2CO3 = Fraction(3, 1000)   # 0.00300


def rows_by_species(ledger):
    return {r.species: r for r in ledger.rows}


def test_molecular_ledger_matches_brief():
    led = solve_extent(
        [(P("CaCl2"), N_CACL2), (P("Na2CO3"), N_NA2CO3)],
        [(P("CaCO3"), 0), (P("NaCl"), 0)],
        [1, 1, 1, 2],
    )
    assert led.extent_mol == Fraction(1, 400)
    assert led.limiting == ["CaCl2"]
    r = rows_by_species(led)
    assert r["CaCl2"].final_mol == 0 and r["CaCl2"].nu == -1
    assert r["Na2CO3"].final_mol == Fraction(1, 2000)      # 0.00050 leftover
    assert r["CaCO3"].final_mol == Fraction(1, 400) and r["CaCO3"].nu == 1
    assert r["NaCl"].final_mol == Fraction(1, 200) and r["NaCl"].nu == 2  # 0.00500


def test_product_mass_is_quarter_gram():
    led = solve_extent(
        [(P("CaCl2"), N_CACL2), (P("Na2CO3"), N_NA2CO3)],
        [(P("CaCO3"), 0), (P("NaCl"), 0)],
        [1, 1, 1, 2],
    )
    caco3 = rows_by_species(led)["CaCO3"]
    mass = species_mass_g(caco3, ChemData.load(ROOT))
    assert to_decimal(mass, 3) == Decimal("0.250")


def test_net_ionic_ledger_same_result():
    # Ca^2+ + CO3^2- -> CaCO3(s) — the same machine, at the ion level
    led = solve_extent(
        [(P("Ca^2+"), N_CACL2), (P("CO3^2-"), N_NA2CO3)],
        [(P("CaCO3(s)"), 0)],
        [1, 1, 1],
    )
    assert led.limiting == ["Ca^2+"]
    r = rows_by_species(led)
    assert r["Ca^2+"].final_mol == 0 and r["Ca^2+"].charge == 2
    assert r["CO3^2-"].final_mol == Fraction(1, 2000) and r["CO3^2-"].charge == -2
    assert r["CaCO3(s)"].final_mol == Fraction(1, 400) and r["CaCO3(s)"].phase == "s"


def test_integration_moles_from_units_engine():
    # derive the initial moles through the units engine, feed the ledger
    n1 = Q.of(Decimal("25.0"), "mL") * Q.of(Decimal("0.100"), "M")
    n2 = Q.of(Decimal("20.0"), "mL") * Q.of(Decimal("0.150"), "M")
    led = solve_extent(
        [(P("CaCl2"), n1.value), (P("Na2CO3"), n2.value)],
        [(P("CaCO3"), 0), (P("NaCl"), 0)],
        [1, 1, 1, 2],
    )
    assert led.extent_mol == Fraction(1, 400) and led.limiting == ["CaCl2"]


def test_limiting_reagent_switches_with_amounts():
    # more CaCl2, less Na2CO3 -> Na2CO3 now limits (the interactive's core; kills the volume misconception)
    led = solve_extent(
        [(P("CaCl2"), Fraction(3, 1000)), (P("Na2CO3"), Fraction(1, 1000))],
        [(P("CaCO3"), 0), (P("NaCl"), 0)],
        [1, 1, 1, 2],
    )
    assert led.limiting == ["Na2CO3"]
    r = rows_by_species(led)
    assert r["CaCl2"].final_mol == Fraction(2, 1000)   # 0.00200 excess
    assert r["CaCO3"].final_mol == Fraction(1, 1000)


def test_stoichiometric_tie_marks_both_limiting():
    led = solve_extent(
        [(P("CaCl2"), N_CACL2), (P("Na2CO3"), N_CACL2)],
        [(P("CaCO3"), 0), (P("NaCl"), 0)],
        [1, 1, 1, 2],
    )
    assert set(led.limiting) == {"CaCl2", "Na2CO3"}


def test_negative_initial_amount_raises():
    with pytest.raises(BuildError):
        solve_extent([(P("CaCl2"), Fraction(-1, 400))], [(P("CaCO3"), 0)], [1, 1])
