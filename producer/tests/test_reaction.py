"""Dissociation, complete ionic, net ionic, and reaction classification (ADR-0035).

Classification is checked against the item-6 corpus — one reaction per first-course family — with the redox
flag verified from the free-element signature."""

from pathlib import Path

import pytest

from chemkernel import BuildError
from chemkernel.data import ChemData
from chemkernel.formula import parse_formula as P
from chemkernel.reaction import (classify_reaction, complete_ionic, dissociate, net_ionic,
                                  redox_free_elements)
from chemkernel.reactivity import AcidBase, Decomposition
from chemkernel.solubility import Solubility

ROOT = Path(__file__).resolve().parents[2]


def data():
    return ChemData.load(ROOT)


def _classify(reactants, products):
    d = data()
    solub = Solubility.load(ROOT)
    ab = AcidBase.load(ROOT)
    ab.validate(d)
    dec = Decomposition.load(ROOT)
    dec.validate(d)
    return classify_reaction([P(s) for s in reactants], [P(s) for s in products], d,
                             solubility=solub, acidbase=ab, decomposition=dec)


# one reaction per family: (reactants, products, family, is_redox)
_CORPUS = [
    (["CH4(g)", "O2(g)"], ["CO2(g)", "H2O(g)"], "combustion", True),
    (["C3H8(g)", "O2(g)"], ["CO2(g)", "H2O(g)"], "combustion", True),
    (["N2(g)", "H2(g)"], ["NH3(g)"], "synthesis", True),
    (["Na(s)", "Cl2(g)"], ["NaCl(s)"], "synthesis", True),
    (["Mg(s)", "O2(g)"], ["MgO(s)"], "synthesis", True),
    (["KClO3(s)"], ["KCl(s)", "O2(g)"], "decomposition", True),
    (["CaCO3(s)"], ["CaO(s)", "CO2(g)"], "decomposition", False),          # no free element → not redox
    (["Zn(s)", "HCl(aq)"], ["ZnCl2(aq)", "H2(g)"], "single-replacement", True),
    (["Fe(s)", "CuSO4(aq)"], ["FeSO4(aq)", "Cu(s)"], "single-replacement", True),
    (["HCl(aq)", "NaOH(aq)"], ["NaCl(aq)", "H2O(l)"], "acid-base", False),
    (["H2SO4(aq)", "NaOH(aq)"], ["Na2SO4(aq)", "H2O(l)"], "acid-base", False),
    (["HCl(aq)", "Na2CO3(aq)"], ["NaCl(aq)", "H2O(l)", "CO2(g)"], "gas-evolution", False),
    (["HCl(aq)", "CaCO3(s)"], ["CaCl2(aq)", "H2O(l)", "CO2(g)"], "gas-evolution", False),
    (["NH4Cl(aq)", "NaOH(aq)"], ["NaCl(aq)", "NH3(g)", "H2O(l)"], "gas-evolution", False),
    (["CaCl2(aq)", "Na2CO3(aq)"], ["CaCO3(s)", "NaCl(aq)"], "precipitation", False),
    (["MgCl2(aq)", "NaOH(aq)"], ["Mg(OH)2(s)", "NaCl(aq)"], "precipitation", False),
    (["CuSO4(aq)", "Na2CO3(aq)"], ["CuCO3(s)", "Na2SO4(aq)"], "precipitation", False),
]


@pytest.mark.parametrize("reactants,products,family,is_redox", _CORPUS)
def test_classify_corpus(reactants, products, family, is_redox):
    c = _classify(reactants, products)
    assert c["family"] == family, f"{reactants}->{products}: got {c['family']}, want {family}"
    assert c["redox"] is is_redox
    assert c["evidence"]
    if is_redox:
        assert "redox_reason" in c


def test_redox_free_element_signature():
    # Zn free→combined, H combined→free: both flagged
    assert redox_free_elements([P("Zn(s)"), P("HCl(aq)")], [P("ZnCl2(aq)"), P("H2(g)")]) == ["H", "Zn"]
    # double replacement, nothing free: empty
    assert redox_free_elements([P("CaCl2(aq)"), P("Na2CO3(aq)")], [P("CaCO3(s)"), P("NaCl(aq)")]) == []


def test_classify_unclassifiable_raises():
    with pytest.raises(BuildError):
        _classify(["NaCl(aq)"], ["NaCl(aq)"])   # nothing happens — not a real reaction shape


@pytest.mark.parametrize("reactants,products,family,is_redox", _CORPUS)
def test_corpus_reactions_balance(reactants, products, family, is_redox):
    """Every classifier-corpus reaction is real chemistry — the engine finds a unique integer balance."""
    from chemkernel.balance import balance
    coeffs = balance([P(s) for s in reactants], [P(s) for s in products], "corpus")
    assert all(c >= 1 for c in coeffs) and len(coeffs) == len(reactants) + len(products)


def test_dissociate_simple_salts():
    d = data()
    assert dissociate(P("CaCl2"), d) == [("Ca^2+", 1), ("Cl^-", 2)]
    assert dissociate(P("Na2CO3"), d) == [("Na^+", 2), ("CO3^2-", 1)]
    assert dissociate(P("NaCl"), d) == [("Na^+", 1), ("Cl^-", 1)]


def test_dissociate_rejects_ion_and_nonsalt():
    d = data()
    with pytest.raises(BuildError):
        dissociate(P("Ca^2+"), d)     # already an ion
    with pytest.raises(BuildError):
        dissociate(P("CH4"), d)       # not an ionic salt of known ions


def test_complete_and_net_ionic_phase0():
    d = data()
    reactants = [P("CaCl2(aq)"), P("Na2CO3(aq)")]
    products = [P("CaCO3(s)"), P("NaCl(aq)")]
    left, right = complete_ionic(reactants, products, [1, 1, 1, 2], d)

    # complete ionic: free ions on the left, CaCO3(s) intact on the right
    assert ("Ca^2+", 1, 2, "aq") in left
    assert ("Cl^-", 2, -1, "aq") in left
    assert ("Na^+", 2, 1, "aq") in left
    assert ("CO3^2-", 1, -2, "aq") in left
    assert ("CaCO3", 1, 0, "s") in right
    assert ("Na^+", 2, 1, "aq") in right and ("Cl^-", 2, -1, "aq") in right

    net_left, net_right, spectators = net_ionic(left, right)
    assert net_left == {("Ca^2+", "aq"): 1, ("CO3^2-", "aq"): 1}
    assert net_right == {("CaCO3", "s"): 1}
    assert spectators == ["Cl^-", "Na^+"]


def test_net_ionic_conservation_holds():
    # net_ionic raises if atoms/charge don't balance; reaching here means the Phase-0 net eq is conserved
    d = data()
    left, right = complete_ionic([P("CaCl2(aq)"), P("Na2CO3(aq)")],
                                 [P("CaCO3(s)"), P("NaCl(aq)")], [1, 1, 1, 2], d)
    net_left, net_right, _ = net_ionic(left, right)
    # Ca + CO3 on each side, charge 0 on each side
    assert sum(v for v in net_left.values()) == 2
