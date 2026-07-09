"""Kinetics tier — first-order decay (ADR-0049). The ledger in time: [A](t) = [A]₀·e^(−kt), t½ = ln2/k."""

import math
from decimal import Decimal
from pathlib import Path

import pytest

from chemkernel import BuildError
from chemkernel.build import build_kinetics
from chemkernel.data import ChemData
from chemkernel.kinetics import (_balance_ok, build_kinetics_lesson, concentration_first_order,
                                 half_life_first_order)

ROOT = Path(__file__).resolve().parents[2]
SPEC = ROOT / "problems" / "kinetics" / "hydrogen-peroxide-decomposition.kinetics.toml"


def _spec(**over):
    s = {"id": "t", "title": "t", "slug": "t", "topic": "kinetics", "scenario": "s", "reactant": "H2O2",
         "initial_molarity_M": "1.000", "misconception": {"claim": "c", "refuted_by": "first_order_half_life_constant"}}
    s.update(over)
    return s


# ── the integrated-rate-law math ──

def test_half_life_is_ln2_over_k():
    """t½ = ln2/k, and k·t½ = ln2 — independent of concentration (the first-order signature)."""
    k = Decimal("3.21e-5")
    th = half_life_first_order(k)
    assert abs(float(th) - math.log(2) / float(k)) < 1e-3
    assert abs(float(k * th) - math.log(2)) < 1e-12


def test_concentration_halves_each_half_life():
    """c(n·t½) = c₀/2ⁿ — successive half-lives equal, whatever remains."""
    k, c0 = Decimal("3.21e-5"), Decimal("1.000")
    th = half_life_first_order(k)
    assert abs(float(concentration_first_order(c0, k, th)) - 0.5) < 1e-6
    assert abs(float(concentration_first_order(c0, k, 2 * th)) - 0.25) < 1e-6
    assert abs(float(concentration_first_order(c0, k, 3 * th)) - 0.125) < 1e-6


def test_balance_check_accepts_and_refuses():
    assert _balance_ok("2 H2O2 -> 2 H2O + O2", "t") is True
    with pytest.raises(BuildError, match="does not balance"):
        _balance_ok("2 H2O2 -> H2O + O2", "t")            # H and O do not conserve


# ── the built lesson ──

def test_builds_first_order_lesson():
    d = ChemData.load(ROOT)
    L = build_kinetics_lesson(_spec(), d, "t")
    assert L["kind"] == "kinetics" and L["subtype"] == "first-order"
    assert L["rate_law"]["order"] == 1 and L["rate_law"]["k_unit"] == "1/s"
    assert L["half_life"]["hours_display"] == "6"          # 5.998 h → 6.00 h (3 sig)
    assert abs(float(L["half_life"]["k_times_thalf"]) - math.log(2)) < 1e-6
    assert all(L["checks"].values())


def test_landmarks_and_curve_halve():
    d = ChemData.load(ROOT)
    L = build_kinetics_lesson(_spec(), d, "t")
    lms = L["result"]["landmarks"]
    assert [lm["half_lives"] for lm in lms] == [1, 2, 3]
    assert [lm["concentration_display"] for lm in lms] == ["0.5", "0.25", "0.125"]
    assert [lm["percent_decomposed_display"] for lm in lms] == ["50", "75", "87.5"]


def test_curve_monotonic_decreasing_from_c0():
    d = ChemData.load(ROOT)
    L = build_kinetics_lesson(_spec(), d, "t")
    concs = [Decimal(p["concentration_M"]) for p in L["curve"]["points"]]
    assert concs[0] == Decimal("1")                       # t = 0 → [A]₀
    assert all(concs[i] > concs[i + 1] for i in range(len(concs) - 1))


def test_refuses_unknown_reactant():
    d = ChemData.load(ROOT)
    with pytest.raises(BuildError, match="no rate constant"):
        build_kinetics_lesson(_spec(reactant="N2O5"), d, "t")


def test_refuses_nonpositive_concentration():
    d = ChemData.load(ROOT)
    with pytest.raises(BuildError, match="positive"):
        build_kinetics_lesson(_spec(initial_molarity_M="0"), d, "t")


def test_rate_constant_loaded_and_sourced():
    d = ChemData.load(ROOT)
    rec = d.rate_constant("H2O2")
    assert rec["order"] == 1 and rec["k"] == Decimal("3.21e-5")
    assert d.sources["rate_constants"] == "openstax-chemistry-2e"


def test_round_trip():
    L, out_rel = build_kinetics(SPEC, ROOT)
    assert out_rel == "kinetics/hydrogen-peroxide-decomposition.kinetics.json"
    assert L["kind"] == "kinetics" and L["subtype"] == "first-order"
    assert L["half_life"]["hours_display"] == "6"
