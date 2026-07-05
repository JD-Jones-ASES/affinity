"""Ionic nomenclature: name ↔ formula, Stock system, hand-checked (Phase 1 item 2, ADR-0027)."""

import pytest

from chemkernel import BuildError
from chemkernel.data import ChemData
from chemkernel.nomenclature import (assemble_with, base_cation_name, formula_ionic, greek,
                                     is_variable, name_ionic, other_charge_names, roman)

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _data():
    return ChemData.load(ROOT)


def test_name_ionic_fixed_and_polyatomic():
    d = _data()
    ion = d.ions.__getitem__
    assert name_ionic(ion("Ca^2+"), ion("CO3^2-")) == "calcium carbonate"
    assert name_ionic(ion("Al^3+"), ion("O^2-")) == "aluminum oxide"
    assert name_ionic(ion("Na^+"), ion("Cl^-")) == "sodium chloride"
    assert name_ionic(ion("NH4^+"), ion("PO4^3-")) == "ammonium phosphate"


def test_name_ionic_stock_numeral():
    d = _data()
    ion = d.ions.__getitem__
    assert name_ionic(ion("Fe^3+"), ion("SO4^2-")) == "iron(III) sulfate"
    assert name_ionic(ion("Fe^2+"), ion("Cl^-")) == "iron(II) chloride"
    assert name_ionic(ion("Cu^+"), ion("O^2-")) == "copper(I) oxide"


def test_formula_ionic_crossover():
    d = _data()
    ion = d.ions.__getitem__
    assert formula_ionic(ion("Fe^3+"), ion("SO4^2-"))[0] == "Fe2(SO4)3"
    assert formula_ionic(ion("Al^3+"), ion("O^2-"))[0] == "Al2O3"
    assert formula_ionic(ion("Cu^+"), ion("O^2-"))[0] == "Cu2O"
    assert formula_ionic(ion("Ca^2+"), ion("CO3^2-"))[0] == "CaCO3"          # reduces 2:2 → 1:1


def test_name_ionic_rejects_bad_arguments():
    d = _data()
    ion = d.ions.__getitem__
    with pytest.raises(BuildError):
        name_ionic(ion("Cl^-"), ion("Ca^2+"))                                # cation/anion swapped


def test_variable_charge_detection():
    d = _data()
    ion = d.ions.__getitem__
    assert is_variable(ion("Fe^3+"), d.ions) and is_variable(ion("Cu^+"), d.ions)
    assert not is_variable(ion("Na^+"), d.ions) and not is_variable(ion("Al^3+"), d.ions)
    assert other_charge_names(ion("Fe^3+"), d.ions) == ["iron(II)"]
    assert base_cation_name(ion("Fe^3+"), d) == "iron"                       # no numeral, for prefix distractor


def test_distractor_helpers():
    d = _data()
    ion = d.ions.__getitem__
    # charges-as-own-subscripts misconception for Fe³⁺ + SO₄²⁻: Fe3(SO4)2 (vs correct Fe2(SO4)3)
    assert assemble_with(ion("Fe^3+"), 3, ion("SO4^2-"), 2) == "Fe3(SO4)2"
    assert roman(3) == "III" and greek(2) == "di" and greek(1) == ""
