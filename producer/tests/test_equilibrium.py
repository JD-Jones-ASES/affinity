"""The reversible-extent solver + weak-acid equilibrium lesson (ADR-0048).

The ICE table is the species ledger with the extent solved from mass action (Q = K), not driven to a limiting
reagent. These tests pin the solver's numerics (the root satisfies Q = K to a tiny residual), the ICE identity,
the pH, and the producer's refusals — the honesty guards that make it safe to emit.
"""

from decimal import Decimal
from pathlib import Path

import pytest

from chemkernel import BuildError
from chemkernel.build import build_equilibrium
from chemkernel.data import ChemData
from chemkernel.equilibrium import build_equilibrium_lesson, solve_equilibrium, _quotient
from chemkernel.reactivity import AcidBase

ROOT = Path(__file__).resolve().parents[2]
SPEC = ROOT / "problems" / "equilibrium" / "acetic-acid-ph.equilibrium.toml"


def _acid_system(c0, hplus=Decimal(0)):
    return [
        {"id": "HA", "nu": -1, "initial_M": Decimal(c0)},
        {"id": "H^+", "nu": 1, "initial_M": hplus},
        {"id": "A^-", "nu": 1, "initial_M": Decimal(0)},
    ]


# ── the solver ──

def test_weak_acid_quadratic_root():
    """Acetic acid, 0.100 M, Ka = 1.8e-5 — the canonical quadratic. x = [H+] ≈ 1.333e-3; the residual is tiny."""
    r = solve_equilibrium(_acid_system("0.100"), Decimal("1.8e-5"), "acetic")
    assert abs(r["extent"] - Decimal("0.00133267")) < Decimal("1e-7")
    # the machine-check: Q at the root reproduces K essentially exactly
    assert r["residual"] < Decimal("1e-40")
    assert float(r["quotient"]) == pytest.approx(1.8e-5, rel=1e-9)


def test_root_satisfies_mass_action_generally():
    """A much stronger weak acid (Ka = 0.10, C0 = 0.10) where the small-x approximation would fail badly: the
    solver still lands the root (≈61.8% ionized), Q = K. Bisection, not the quadratic formula — the instrument."""
    r = solve_equilibrium(_acid_system("0.10"), Decimal("0.10"), "strong-weak")
    assert Decimal("0.06") < r["extent"] < Decimal("0.064")
    assert r["residual"] < Decimal("1e-40")
    # the naive √(Ka·C0) would give 0.10 (100% ionized) — the honest root is far from it
    assert r["extent"] < Decimal("0.07")


def test_root_is_bracketed_between_zero_and_reactant():
    r = solve_equilibrium(_acid_system("0.250"), Decimal("4.9e-10"), "very-weak")
    assert 0 < r["extent"] < Decimal("0.250")
    assert r["fwd_limit"] == Decimal("0.250")


def test_quotient_products_over_reactants():
    q = _quotient([Decimal("0.0987"), Decimal("0.00133"), Decimal("0.00133")], [-1, 1, 1])
    assert float(q) == pytest.approx(0.00133 * 0.00133 / 0.0987, rel=1e-9)


def test_solver_refuses_nonpositive_K():
    with pytest.raises(BuildError, match="must be positive"):
        solve_equilibrium(_acid_system("0.1"), Decimal(0), "bad")


def test_solver_refuses_negative_initial():
    with pytest.raises(BuildError, match="negative initial"):
        solve_equilibrium(_acid_system("-0.1"), Decimal("1e-5"), "bad")


def test_solver_refuses_missing_side():
    only_reactants = [{"id": "A", "nu": -1, "initial_M": Decimal("0.1")}]
    with pytest.raises(BuildError, match="at least one product"):
        solve_equilibrium(only_reactants, Decimal("1e-5"), "bad")


# ── the lesson builder ──

def _data_ab():
    data = ChemData.load(ROOT)
    ab = AcidBase.load(ROOT)
    ab.validate(data)
    return data, ab


def _spec(**over):
    base = {"id": "t", "title": "t", "slug": "t", "topic": "equilibrium", "scenario": "s",
            "acid": "HC2H3O2", "initial_molarity_M": "0.100",
            "misconception": {"claim": "c", "refuted_by": "weak_acid_partial_ionization"}}
    base.update(over)
    return base


def test_builds_acetic_acid_lesson():
    data, ab = _data_ab()
    L = build_equilibrium_lesson(_spec(), data, ab, "t")
    assert L["kind"] == "equilibrium"
    # the reaction is DRY-sourced from acids-bases.toml (proton count + conjugate base)
    assert L["reaction"]["text"] == "HC2H3O2 <=> H^+ + C2H3O2^-"
    assert L["reaction"]["conjugate_base"] == "C2H3O2^-"
    # Ka from the sourced dataset
    assert L["equilibrium_constant"]["value"] == "0.000018"
    assert L["equilibrium_constant"]["source"] == "openstax-chemistry-2e"
    # the solved position
    assert L["ice"]["extent_M_display"] == "0.00133"
    assert L["result"]["pH_display"] == "2.88"
    assert L["result"]["percent_ionization_display"] == "1.33"
    # all machine-checked facts true
    assert all(L["checks"].values())


def test_ice_identity_holds():
    """Every equilibrium concentration = initial + ν·x (the ledger identity, exact in what ships)."""
    data, ab = _data_ab()
    L = build_equilibrium_lesson(_spec(), data, ab, "t")
    x = Decimal(L["ice"]["extent_M"])
    for row in L["ice"]["species"]:
        expected = Decimal(row["initial_M"]) + row["nu"] * x
        assert abs(Decimal(row["equilibrium_M"]) - expected) < Decimal("1e-10")


def test_mass_action_residual_tiny():
    """Q at the committed equilibrium concentrations reproduces Ka — the machine-check."""
    data, ab = _data_ab()
    L = build_equilibrium_lesson(_spec(), data, ab, "t")
    concs = [Decimal(r["equilibrium_M"]) for r in L["ice"]["species"]]
    nus = [r["nu"] for r in L["ice"]["species"]]
    Q = _quotient(concs, nus)
    ka = Decimal(L["equilibrium_constant"]["value"])
    assert abs(Q - ka) / ka < Decimal("1e-6")


def test_regimes_layered():
    data, ab = _data_ab()
    L = build_equilibrium_lesson(_spec(), data, ab, "t")
    regimes = {r["regime"] for r in L["regimes"]}
    assert {"ledger-exact", "rule-sourced", "model-exact"} <= regimes


def test_refuses_strong_acid():
    data, ab = _data_ab()
    with pytest.raises(BuildError, match="not weak"):
        build_equilibrium_lesson(_spec(acid="HCl"), data, ab, "t")


def test_refuses_polyprotic_acid():
    data, ab = _data_ab()
    with pytest.raises(BuildError, match="polyprotic"):
        build_equilibrium_lesson(_spec(acid="H3PO4"), data, ab, "t")


def test_refuses_unknown_acid():
    data, ab = _data_ab()
    with pytest.raises(BuildError, match="not in data/acids-bases"):
        build_equilibrium_lesson(_spec(acid="HBr"), data, ab, "t")


def test_refuses_nonpositive_concentration():
    data, ab = _data_ab()
    with pytest.raises(BuildError, match="molarity must be positive"):
        build_equilibrium_lesson(_spec(initial_molarity_M="0"), data, ab, "t")


# ── the data layer ──

def test_ionization_constants_loaded():
    data = ChemData.load(ROOT)
    assert data.ionization_constant("HC2H3O2")["ka"] == Decimal("1.8e-5")
    assert data.sources["ionization_constants"] == "openstax-chemistry-2e"


def test_missing_ka_refused():
    data = ChemData.load(ROOT)
    with pytest.raises(BuildError, match="no ionization constant"):
        data.ionization_constant("HNO3")   # a strong acid — no Ka curated


# ── the build round-trip ──

def test_build_equilibrium_round_trip():
    lesson, out_rel = build_equilibrium(SPEC, ROOT)
    assert out_rel == "equilibrium/acetic-acid-ph.equilibrium.json"
    assert lesson["id"] == "acetic-acid-ph"
    assert lesson["kind"] == "equilibrium"
