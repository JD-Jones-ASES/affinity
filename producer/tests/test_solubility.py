"""Solubility classifier against OpenStax Table 4.1 rules (data/solubility.toml)."""

from pathlib import Path

import pytest

from chemkernel import BuildError
from chemkernel.data import ChemData
from chemkernel.formula import parse_formula as P
from chemkernel.solubility import Solubility

ROOT = Path(__file__).resolve().parents[2]


def setup():
    return Solubility.load(ROOT), ChemData.load(ROOT)


def test_carbonate_of_calcium_is_insoluble():
    s, d = setup()
    v = s.classify("Ca^2+", "CO3^2-", d)
    assert v.soluble is False and v.rule_id == "insol-carbonate"


def test_group1_cation_overrides_insoluble_anion():
    s, d = setup()
    v = s.classify("Na^+", "CO3^2-", d)   # Na2CO3 is soluble because Na is group 1
    assert v.soluble is True and v.rule_id == "sol-cation"


def test_chloride_of_calcium_is_soluble():
    s, d = setup()
    assert s.classify("Ca^2+", "Cl^-", d).soluble is True


def test_calcium_sulfate_hits_the_exception():
    s, d = setup()
    v = s.classify("Ca^2+", "SO4^2-", d)   # Ca is in the sulfate exception list -> insoluble
    assert v.soluble is False and v.rule_id == "sol-sulfate-exception"


def test_classify_compound_phase0_species():
    s, d = setup()
    assert s.classify_compound(P("CaCO3"), d).soluble is False
    assert s.classify_compound(P("NaCl"), d).soluble is True
    assert s.classify_compound(P("CaCl2"), d).soluble is True
    assert s.classify_compound(P("Na2CO3"), d).soluble is True


def test_verify_phase_matches_and_catches_mismatch():
    s, d = setup()
    s.verify_phase(P("CaCO3(s)"), d)      # consistent -> no raise
    s.verify_phase(P("CaCl2(aq)"), d)     # consistent -> no raise
    with pytest.raises(BuildError):
        s.verify_phase(P("CaCO3(aq)"), d)  # ruleset says insoluble -> mislabeled aqueous
