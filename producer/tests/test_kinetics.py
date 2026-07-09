"""Kinetics tier — the ledger in time (ADR-0049), orders 0/1/2. [A](t) and t½ follow the order; the successive
half-life PROGRESSION (constant / doubling / halving) is the order's fingerprint, machine-checked."""

import math
from decimal import Decimal
from pathlib import Path

import pytest

from chemkernel import BuildError
from chemkernel.build import build_kinetics
from chemkernel.data import ChemData
from chemkernel.kinetics import (_balance_ok, build_kinetics_lesson, concentration, concentration_first_order,
                                 half_life, half_life_first_order, time_to_reach)

ROOT = Path(__file__).resolve().parents[2]
SPEC = ROOT / "problems" / "kinetics" / "hydrogen-peroxide-decomposition.kinetics.toml"
SPEC2 = ROOT / "problems" / "kinetics" / "butadiene-dimerization.kinetics.toml"
SPEC0 = ROOT / "problems" / "kinetics" / "ammonia-decomposition.kinetics.toml"


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


# ── orders 0 and 2: the integrated laws, half-lives, and their contrasting progressions ──

def test_integrated_laws_all_orders():
    """Each order's integrated law is distinct: zero linear, first exponential, second reciprocal-linear."""
    k, c0, t = Decimal("0.01"), Decimal("1.0"), Decimal("10")
    assert concentration(0, c0, k, t) == c0 - k * t                          # 1.0 − 0.1 = 0.9
    assert abs(float(concentration(1, c0, k, t)) - float(c0) * math.exp(-0.1)) < 1e-12
    assert abs(float(concentration(2, c0, k, t)) - float(c0) / (1 + 0.01 * 1.0 * 10)) < 1e-12
    # first-order wrappers delegate to the general forms
    assert concentration_first_order(c0, k, t) == concentration(1, c0, k, t)
    assert half_life_first_order(k) == half_life(1, c0, k)


def test_second_order_half_life_grows():
    """t½ = 1/(k[A]₀); successive half-lives DOUBLE (the second half takes ~2× the first)."""
    k, c0 = Decimal("5.76e-2"), Decimal("0.200")
    th = half_life(2, c0, k)                                                 # native = minutes
    assert abs(float(th) - 1 / (float(k) * float(c0))) < 1e-6
    assert abs(float(concentration(2, c0, k, th)) - float(c0) / 2) < 1e-9    # after t½, exactly half
    seg2 = time_to_reach(2, c0, k, c0 / 4) - th                              # 3·t½ − t½ = 2·t½
    assert abs(float(seg2) - 2 * float(th)) < 1e-6


def test_zero_order_half_life_shrinks_and_completes():
    """t½ = [A]₀/(2k); successive half-lives HALVE; and [A] reaches EXACTLY 0 at t = [A]₀/k (finite completion)."""
    k, c0 = Decimal("1.3e-6"), Decimal("0.0100")
    th = half_life(0, c0, k)
    assert abs(float(th) - float(c0) / (2 * float(k))) < 1e-3
    assert concentration(0, c0, k, c0 / k) == 0                             # exhausted at completion
    assert concentration(0, c0, k, c0 / k * 2) == 0                         # stays 0 past completion (no negatives)
    seg2 = time_to_reach(0, c0, k, c0 / 4) - th                             # 1.5·t½ − t½ = 0.5·t½
    assert abs(float(seg2) - 0.5 * float(th)) < 1e-3


def test_builds_second_order_lesson():
    L, rel = build_kinetics(SPEC2, ROOT)
    assert rel == "kinetics/butadiene-dimerization.kinetics.json"
    assert L["subtype"] == "second-order" and L["rate_law"]["order"] == 2
    assert L["rate_law"]["k_unit"] == "1/(M*min)" and L["rate_law"]["k_unit_display"] == "M⁻¹ min⁻¹"
    assert L["half_life"]["progression"] == "doubles" and L["half_life"]["depends_on_concentration"] is True
    assert L["half_life"]["hours_display"] == "1.45"
    assert [lm["segment_half_life_hours_display"] for lm in L["result"]["landmarks"]] == ["1.45", "2.89", "5.79"]
    assert "completion_hours_display" not in L["result"]        # second order is asymptotic — no finite completion
    assert "k_times_thalf" not in L["half_life"]                # the k·t½=ln2 identity is first-order only
    assert all(L["checks"].values())


def test_builds_zero_order_lesson():
    L, rel = build_kinetics(SPEC0, ROOT)
    assert rel == "kinetics/ammonia-decomposition.kinetics.json"
    assert L["subtype"] == "zero-order" and L["rate_law"]["order"] == 0
    assert L["rate_law"]["k_unit"] == "M/s"
    assert L["half_life"]["progression"] == "halves" and L["half_life"]["depends_on_concentration"] is True
    assert L["result"]["completion_hours_display"] == "2.14"    # reaches 0 at a finite time
    assert [lm["segment_half_life_hours_display"] for lm in L["result"]["landmarks"]] == ["1.07", "0.534", "0.267"]
    assert L["curve"]["points"][-1]["concentration_M"] == "0"   # exactly zero at completion, not an asymptote
    assert all(L["checks"].values())


# ── the k-units must encode the order; unsupported orders are refused (ADR-0008) ──

class _StubData:
    def __init__(self, rec):
        self._rec = rec
        self.sources = {"rate_constants": "src", "atomic_weight": "aw"}

    def rate_constant(self, _formula):
        return self._rec


def _rec(**over):
    r = {"name": "x", "reactant": "H2O2", "order": 2, "k": Decimal("1e-2"), "k_unit": "1/(M*s)",
         "equation": "2 H2O2 -> 2 H2O + O2", "conditions": ""}
    r.update(over)
    return r


def test_refuses_unit_order_mismatch():
    """An order-2 reaction with first-order (1/s) k units is refused — the units encode the order."""
    with pytest.raises(BuildError, match="units"):
        build_kinetics_lesson(_spec(), _StubData(_rec(order=2, k_unit="1/s")), "t")


def test_refuses_unsupported_order():
    with pytest.raises(BuildError, match="unsupported"):
        build_kinetics_lesson(_spec(), _StubData(_rec(order=3, k_unit="1/(M*s)")), "t")


def test_round_trip():
    L, out_rel = build_kinetics(SPEC, ROOT)
    assert out_rel == "kinetics/hydrogen-peroxide-decomposition.kinetics.json"
    assert L["kind"] == "kinetics" and L["subtype"] == "first-order"
    assert L["half_life"]["hours_display"] == "6"
