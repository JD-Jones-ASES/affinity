"""Independent-oracle cross-checks (ADR-0026): third-party chemistry libraries re-verify the engine.

The verification thesis wants redundant, independent proof. These tests check our curated data and our
balancer against libraries with entirely separate data pipelines and algorithms:
  - `periodictable` — element masses (independent of our CIAAW-curated data/elements.toml),
  - `chempy` — formula-parsed molar masses and SymPy-based equation balancing.

Oracles are DEV-ONLY (pyproject dependency-group `dev`, ADR-0026): they never run at build time and never
supply a shipped value; runtime constants still come exclusively from cited `data/` (ADR-0006/0012).
Tolerances are loose (different atomic-weight editions round differently) — these catch transcription and
logic errors, not last-digit revisions. `importorskip` degrades gracefully if an oracle can't install.
"""

import tomllib
from decimal import Decimal
from pathlib import Path

import pytest

from chemkernel.balance import balance
from chemkernel.data import ChemData
from chemkernel.formula import parse_formula

chempy = pytest.importorskip("chempy")
periodictable = pytest.importorskip("periodictable")

ROOT = Path(__file__).resolve().parents[2]

# every substance the corpus uses (gym salts ∪ lesson species)
_SUBSTANCES = ["NaCl", "CaCl2", "Na2CO3", "CaCO3", "Na3PO4", "Ca3(PO4)2"]


def _data():
    return ChemData.load(ROOT)


def test_element_weights_match_periodictable():
    """Every curated CIAAW atomic weight agrees with periodictable's independent element table."""
    data = _data()
    for sym, el in data.elements.items():
        oracle = getattr(periodictable, sym).mass
        tol = max(float(getattr(el, "uncertainty", 0) or 0), 0.01)
        assert abs(float(el.atomic_weight) - oracle) <= tol, (
            f"{sym}: ours {el.atomic_weight} vs periodictable {oracle}")


def test_molar_masses_match_chempy():
    """Our molar-mass sums agree with chempy's independent parser + mass table."""
    data = _data()
    for f in _SUBSTANCES:
        ours = float(data.molar_mass(f))
        oracle = chempy.Substance.from_formula(f).mass
        assert abs(ours - oracle) <= 0.02, f"{f}: ours {ours} vs chempy {oracle}"


@pytest.mark.parametrize("reactants,products", [
    (["CaCl2", "Na2CO3"], ["CaCO3", "NaCl"]),        # the carbonate lesson
    (["CaCl2", "Na3PO4"], ["Ca3(PO4)2", "NaCl"]),    # the phosphate lesson (3:2:1:6)
])
def test_balancer_matches_chempy(reactants, products):
    """Our conservation-matrix balancer and chempy's SymPy balancer agree exactly."""
    ours = balance([parse_formula(s) for s in reactants], [parse_formula(s) for s in products])
    r_or, p_or = chempy.balance_stoichiometry(set(reactants), set(products))
    oracle = [int(r_or[s]) for s in reactants] + [int(p_or[s]) for s in products]
    assert ours == oracle
