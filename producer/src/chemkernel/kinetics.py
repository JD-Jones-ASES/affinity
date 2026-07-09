"""Kinetics — the ledger in time (ADR-0049). Orders 0, 1, 2.

The thesis (AGENTS.md): the **species ledger over reaction extent** is the pivot. Kinetics is that same ledger with
the extent **evolving in time** — dξ/dt is the *rate* of reaction. For a reactant A consumed with rate law
rate = k[A]ⁿ, the **integrated rate law** and **half-life** depend on the order n:

    order 0:  [A] = [A]₀ − kt              t½ = [A]₀ / (2k)      (the half-life SHRINKS as [A] falls)
    order 1:  [A] = [A]₀ · e^(−kt)         t½ = ln 2 / k         (the half-life is CONSTANT — no [A]₀)
    order 2:  1/[A] = 1/[A]₀ + kt          t½ = 1 / (k[A]₀)      (the half-life GROWS as [A] falls)

The contrast is the payoff: a **constant** half-life is not a general fact but the first-order signature. Zero order
alone reaches a real, finite completion ([A] = 0 at t = [A]₀/k); first and second order are asymptotic.

Honesty, layered (the three badges, ADR-0003): the ledger accounting ([A] = [A]₀ − aξ) is exact (regime-1); the rate
law and its **order** are a disclosed **model** (regime-2 — the order is found by experiment, not read off the balanced
equation); k is a sourced empirical datum (regime-3, in its native units — s⁻¹ or min⁻¹); the integrated law + half-life
+ every curve point are exact *given the model* and rounded for display (regime-2, model-exact-then-rounded, the
gas-law-volume pattern of ADR-0040). The machine-check is the algebra, re-derived in Node: c(t) at every point, the
order's t½ relation, and the successive-half-life **progression** (constant / doubling / halving — the order's
fingerprint). The producer REFUSES a nonpositive k / concentration, an unsupported order, a k whose units disagree
with its order, or a non-conserving reaction (ADR-0008)."""

from __future__ import annotations

import platform
from decimal import ROUND_HALF_UP, Decimal, localcontext

from . import BuildError, __version__
from .formula import parse_formula

_PREC = 50   # working precision for exp/ln (the decay is transcendental — model-exact-then-rounded)

# the curve is sampled at these multiples of the FIRST half-life, per order. Each list reaches roughly c₀/8..c₀/16
# without leaving the physical domain: zero order hits [A]=0 at exactly 2·t½ (a straight line to completion), first
# and second order are asymptotic (an exponential / a long hyperbolic tail). Deterministic (no Date/random).
_FRACTIONS = {
    0: ["0", "0.25", "0.5", "0.75", "1", "1.25", "1.5", "1.75", "2"],       # → 0 at 2·t½
    1: ["0", "0.5", "1", "1.5", "2", "2.5", "3", "4", "5"],                 # → c₀/32
    2: ["0", "0.5", "1", "2", "3", "5", "7", "10", "15"],                   # → c₀/16 (the drawn-out tail)
}

# order → the machine-verified behavior of *successive* half-lives (each halving step vs. the one before).
_PROGRESSION = {0: "halves", 1: "constant", 2: "doubles"}
_SUBTYPE = {0: "zero-order", 1: "first-order", 2: "second-order"}

# order → the k-unit family (its concentration exponent). The time part (s or min) is separate — see _time_base.
_ORDER_UNITS = {0: {"M/s", "M/min"}, 1: {"1/s", "1/min"}, 2: {"1/(M*s)", "1/(M*min)"}}

# k is stored + shown in its SOURCED units (honesty); this maps the ASCII unit to a pretty display form.
_K_UNIT_DISPLAY = {
    "1/s": "s⁻¹", "1/min": "min⁻¹",
    "1/(M*s)": "M⁻¹ s⁻¹", "1/(M*min)": "M⁻¹ min⁻¹",
    "M/s": "M s⁻¹", "M/min": "M min⁻¹",
}


def _round_sig(d: Decimal, n: int) -> Decimal:
    if d == 0:
        return Decimal(0)
    return d.quantize(Decimal(1).scaleb(d.adjusted() - (n - 1)), rounding=ROUND_HALF_UP)


def _sig(d: Decimal, n: int) -> str:
    s = format(_round_sig(d, n), "f")
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s or "0"


def _time_base_seconds(k_unit: str) -> int:
    """Seconds per the k's native time unit (min → 60, else 1). k is kept + shown in its sourced units; the engine
    computes in that native time unit, then converts times to seconds/hours for display + the gate."""
    return 60 if "min" in k_unit else 1


# ── the integrated rate laws, half-lives, and their inverses (all in the k's native time unit) ──

def concentration(order: int, c0: Decimal, k: Decimal, t: Decimal) -> Decimal:
    """[A](t) for a zero-/first-/second-order decay. Zero order floors at 0 (the reactant is fully consumed at
    t = c₀/k — a real, finite completion, unlike the asymptotic 1st/2nd orders)."""
    with localcontext() as lc:
        lc.prec = _PREC
        if order == 0:
            c = c0 - k * t
            # at/after completion (t ≥ c₀/k) the reactant is exhausted — floor the transcendental-division residual
            # (the c₀/k round-trip leaves ~1e-31 of c₀) to an exact 0, the model-exact completion boundary.
            return c if c > c0 * Decimal("1e-20") else Decimal(0)
        if order == 1:
            return c0 * (-(k * t)).exp()
        if order == 2:
            return c0 / (1 + k * c0 * t)
    raise BuildError(f"unsupported reaction order {order} (kinetics handles 0, 1, 2)")


def half_life(order: int, c0: Decimal, k: Decimal) -> Decimal:
    """The FIRST half-life t½. Order 0: c₀/(2k) — shrinks as c₀ falls. Order 1: ln2/k — independent of c₀
    (the signature). Order 2: 1/(k·c₀) — grows as c₀ falls."""
    with localcontext() as lc:
        lc.prec = _PREC
        if order == 0:
            return c0 / (2 * k)
        if order == 1:
            return Decimal(2).ln() / k
        if order == 2:
            return 1 / (k * c0)
    raise BuildError(f"unsupported reaction order {order} (kinetics handles 0, 1, 2)")


def time_to_reach(order: int, c0: Decimal, k: Decimal, c: Decimal) -> Decimal:
    """Time for [A] to fall from c₀ to c (c < c₀) — the inverse of the integrated law. Used for the halving
    landmarks (c = c₀/2ⁿ), whose *spacing* is the order's fingerprint (equal / doubling / halving)."""
    with localcontext() as lc:
        lc.prec = _PREC
        if order == 0:
            return (c0 - c) / k
        if order == 1:
            return (c0 / c).ln() / k
        if order == 2:
            return (1 / c - 1 / c0) / k
    raise BuildError(f"unsupported reaction order {order} (kinetics handles 0, 1, 2)")


# thin first-order wrappers (kept so existing call sites + tests read cleanly; delegate to the general forms).
def half_life_first_order(k: Decimal) -> Decimal:
    """t½ = ln 2 / k (first order) — independent of [A]₀."""
    return half_life(1, Decimal(1), k)


def concentration_first_order(c0: Decimal, k: Decimal, t: Decimal) -> Decimal:
    """[A](t) = [A]₀·e^(−kt) — the first-order integrated law."""
    return concentration(1, c0, k, t)


def _balance_ok(equation: str, ctx: str) -> bool:
    """Machine-check that an authored 'aA + bB -> cC + dD' equation conserves every element (regime-1). Parses each
    'coeff Formula' token with the formula parser and sums element counts on each side. Refuses an unbalanced one."""
    if "->" not in equation:
        raise BuildError(f"{ctx}: reaction equation '{equation}' has no '->'")
    lhs, rhs = equation.split("->", 1)

    def _side_counts(side: str) -> dict[str, int]:
        totals: dict[str, int] = {}
        for term in side.split("+"):
            term = term.strip()
            if not term:
                raise BuildError(f"{ctx}: empty term in equation '{equation}'")
            head, _, rest = term.partition(" ")
            if head.isdigit():           # a leading integer coefficient
                coeff, formula = int(head), rest.strip()
            else:
                coeff, formula = 1, term
            for el, cnt in parse_formula(formula, ctx).counts.items():
                totals[el] = totals.get(el, 0) + coeff * cnt
        return totals

    if _side_counts(lhs) != _side_counts(rhs):
        raise BuildError(f"{ctx}: reaction '{equation}' does not balance ({_side_counts(lhs)} vs {_side_counts(rhs)})")
    return True


def _regimes() -> list[dict]:
    """The kinetics lesson's fixed honesty shape: the species accounting is machine-checked (regime-1), the rate
    constant is sourced (regime-3), the rate law + decay position is a disclosed model (regime-2)."""
    return [
        {"facet": "species accounting over time (the ledger)", "regime": "ledger-exact"},
        {"facet": "rate constant", "regime": "rule-sourced"},
        {"facet": "rate law + integrated decay", "regime": "model-exact"},
    ]


def _eq_latex(equation: str, ctx: str) -> str:
    """Render 'aA + bB -> cC + dD' to KaTeX using the formula parser's upright LaTeX (→ for the arrow)."""
    def _side(side: str) -> str:
        parts = []
        for term in side.split("+"):
            term = term.strip()
            head, _, rest = term.partition(" ")
            if head.isdigit():
                parts.append(f"{head}\\,{parse_formula(rest.strip(), ctx).latex}")
            else:
                parts.append(parse_formula(term, ctx).latex)
        return " + ".join(parts)
    lhs, rhs = equation.split("->", 1)
    return f"{_side(lhs)} \\rightarrow {_side(rhs)}"


def _rate_law_latex(order: int, sym: str) -> str:
    if order == 0:
        return "\\text{rate} = k"
    if order == 1:
        return f"\\text{{rate}} = k\\,[{sym}]"
    return f"\\text{{rate}} = k\\,[{sym}]^2"


def _integrated_latex(order: int, sym: str) -> str:
    if order == 0:
        return f"[{sym}] = [{sym}]_0 - kt"
    if order == 1:
        return f"[{sym}] = [{sym}]_0\\,e^{{-kt}}"
    return f"\\dfrac{{1}}{{[{sym}]}} = \\dfrac{{1}}{{[{sym}]_0}} + kt"


def _half_life_latex(order: int, sym: str) -> str:
    if order == 0:
        return f"t_{{1/2}} = \\dfrac{{[{sym}]_0}}{{2k}}"
    if order == 1:
        return "t_{1/2} = \\dfrac{\\ln 2}{k}"
    return f"t_{{1/2}} = \\dfrac{{1}}{{k\\,[{sym}]_0}}"


def build_kinetics_lesson(spec: dict, data, ctx: str = "") -> dict:
    """An authored kinetics lesson → the verified `*.kinetics.json` object (ADR-0049). The lesson names a reactant
    whose rate constant + order live in `data/rate-constants.toml` (sourced, in native units). The producer picks the
    order-appropriate integrated rate law, half-life, decay curve, and halving landmarks (with each halving step's
    duration — the order's fingerprint). The rate law + order are disclosed (model-assumed); k is sourced; the decay is
    model-exact-then-rounded. REFUSES an unsupported order, a k whose units disagree with its order, an unknown
    reactant, a non-conserving reaction, or a nonpositive input."""
    for key in ("id", "title", "slug", "topic", "scenario", "reactant", "initial_molarity_M", "misconception"):
        if key not in spec:
            raise BuildError(f"{ctx}: kinetics lesson missing required key '{key}'")

    reactant = spec["reactant"]
    rec = data.rate_constant(reactant)                       # raises if absent (sourced k + order)
    order = rec["order"]
    if order not in (0, 1, 2):
        raise BuildError(f"{ctx}: order {order} unsupported — this lesson kind handles orders 0, 1, 2")
    if rec["k_unit"] not in _ORDER_UNITS[order]:
        raise BuildError(f"{ctx}: an order-{order} k must carry units in {sorted(_ORDER_UNITS[order])} "
                         f"(got '{rec['k_unit']}') — the k units encode the order")
    k = rec["k"]
    c0 = Decimal(str(spec["initial_molarity_M"]))
    if c0 <= 0:
        raise BuildError(f"{ctx}: initial molarity must be positive (got {c0})")

    equation = rec["equation"]
    _balance_ok(equation, ctx)                               # the reaction conserves every element (engine-checked)
    fr = parse_formula(reactant, ctx)
    tb = _time_base_seconds(rec["k_unit"])                   # native time unit → seconds

    def _hours(t_native: Decimal) -> Decimal:
        return t_native * tb / 3600

    t_half = half_life(order, c0, k)                         # the FIRST half-life (native units)

    # the decay curve: [A] at each sampled time (a multiple of the first t½). Deterministic + machine-checkable.
    curve = []
    for frac in _FRACTIONS[order]:
        n = Decimal(frac)
        t = n * t_half
        c = concentration(order, c0, k, t)
        with localcontext() as lc:
            lc.prec = _PREC
            pct_remaining = c / c0 * 100
        t_sec = t * tb
        curve.append({
            "half_lives": frac,
            "t_seconds": _sig(t_sec, 8), "t_seconds_display": _sig(t_sec, 3),
            "t_hours_display": _sig(_hours(t), 3),
            "concentration_M": _sig(c, 12), "concentration_display": _sig(c, 3),
            "percent_remaining_display": _sig(pct_remaining, 3),
            "percent_decomposed_display": _sig(100 - pct_remaining, 3),
        })

    # the halving landmarks (c₀/2, c₀/4, c₀/8): the TIME of each is order-specific, and each step's duration
    # (segment) is the order's fingerprint — equal (1st), doubling (2nd), halving (0th).
    landmarks = []
    prev_t = Decimal(0)
    for n in (1, 2, 3):
        c = c0 / (2 ** n)                                    # c₀/2ⁿ exactly (n successive halvings, by definition)
        t = time_to_reach(order, c0, k, c)                  # order-specific spacing (native)
        seg = t - prev_t                                    # this halving step's duration
        prev_t = t
        landmarks.append({
            "half_lives": n, "t_hours_display": _sig(_hours(t), 3),
            "segment_half_life_hours_display": _sig(_hours(seg), 3),
            "concentration_M": _sig(c, 12), "concentration_display": _sig(c, 3),
            "percent_decomposed_display": _sig(100 - c / c0 * 100, 3),
        })

    half_life_block = {
        "symbol": "t_{1/2}", "relation_latex": _half_life_latex(order, fr.latex),
        "seconds": _sig(t_half * tb, 8), "seconds_display": _sig(t_half * tb, 3),
        "hours_display": _sig(_hours(t_half), 3),
        "progression": _PROGRESSION[order],                 # constant / doubles / halves (machine-checked)
        "depends_on_concentration": order != 1,             # false only for first order (the signature)
    }
    if order == 1:                                          # the classic first-order identity k·t½ = ln 2
        with localcontext() as lc:
            lc.prec = _PREC
            half_life_block["k_times_thalf"] = _sig(k * t_half, 8)

    result = {
        "half_life_hours_display": _sig(_hours(t_half), 3),
        "half_life_seconds_display": _sig(t_half * tb, 3),
        "landmarks": landmarks,
    }
    if order == 0:                                          # zero order alone reaches a real, finite completion
        result["completion_hours_display"] = _sig(_hours(c0 / k), 3)

    return {
        "kind": "kinetics",
        "subtype": _SUBTYPE[order],
        "id": spec["id"],
        "title": spec["title"],
        "slug": spec["slug"],
        "topic": spec["topic"],
        "tags": spec.get("tags", []),
        "scenario": spec["scenario"],
        "regimes": _regimes(),
        "assumptions": spec.get("assumptions", []),
        "reaction": {
            "reactant": reactant, "reactant_name": rec["name"], "reactant_latex": fr.latex,
            "equation_text": equation, "equation_latex": _eq_latex(equation, ctx),
            "conditions": rec.get("conditions", ""),
        },
        "rate_law": {
            "order": order, "statement_latex": _rate_law_latex(order, fr.latex), "k_symbol": "k",
            "k_value": format(k, "f"), "k_display": _sig(k, 3), "k_unit": rec["k_unit"],
            "k_unit_display": _K_UNIT_DISPLAY[rec["k_unit"]],
            "source": data.sources.get("rate_constants", ""),
        },
        "integrated": {
            "law_latex": _integrated_latex(order, fr.latex),
            "initial_molarity_M": format(c0, "f"), "initial_molarity_display": _sig(c0, 3),
        },
        "half_life": half_life_block,
        "curve": {"points": curve},
        "result": result,
        "misconception": spec["misconception"],
        "reference_links": spec.get("reference_links", []),
        # the machine-checked facts, SHOWN not asserted (the gate re-derives all four, ADR-0008).
        "checks": {
            "reaction_balanced": True,      # the equation conserves every element (regime-1)
            "integrated_law": True,         # every curve point c(t) matches the order's integrated law
            "half_life_relation": True,     # the first t½ matches the order's formula (ln2/k, c₀/2k, or 1/k·c₀)
            "half_life_progression": True,  # successive half-lives follow the order (constant / doubling / halving)
        },
        "provenance": {
            "producer": "chemkernel",
            "version": __version__,
            "python": platform.python_version(),
            "author": spec.get("author", "Affinity"),
            "created": spec.get("created", ""),
            "sources": {
                "rate_constants": data.sources.get("rate_constants", ""),
                "atomic_weight": data.sources.get("atomic_weight", ""),
            },
        },
    }
