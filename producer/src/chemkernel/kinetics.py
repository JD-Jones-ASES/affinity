"""First-order kinetics — the ledger in time (ADR-0049), the kinetics tier opener.

The thesis (AGENTS.md): the **species ledger over reaction extent** is the pivot. Kinetics is that same ledger with
the extent **evolving in time** — dξ/dt is the *rate* of reaction. For a reactant A consumed first-order, the rate
law rate = k[A] means d[A]/dt = −k[A], whose exact solution is the **integrated rate law**

    [A](t) = [A]₀ · e^(−k t),

and the **half-life** t½ = ln 2 / k is **independent of [A]₀** — the signature of first order. Honesty, layered
(the three badges, ADR-0003): the ledger accounting ([A] = [A]₀ − 2ξ for 2 H₂O₂ → …) is exact (regime-1); the rate
law and its order are a disclosed **model** (regime-2 — the order is found by experiment, not read off the balanced
equation); k is a sourced empirical datum (regime-3); the integrated law + half-life + every curve point are exact
*given the model* and rounded for display (regime-2, model-exact-then-rounded, the gas-law-volume pattern of
ADR-0040). The machine-check is the algebra, re-derived in Node: c(t) = c₀·e^(−kt) at every point, k·t½ = ln 2, and
c(n·t½) = c₀/2ⁿ (successive half-lives equal — the first-order tell). The producer REFUSES a nonpositive k /
concentration / time or a non-first-order reaction sent to this builder (ADR-0008)."""

from __future__ import annotations

import platform
from decimal import ROUND_HALF_UP, Decimal, localcontext

from . import BuildError, __version__
from .formula import parse_formula

_PREC = 50   # working precision for exp/ln (the decay is transcendental — model-exact-then-rounded)

# the curve is sampled at these multiples of the half-life — integer multiples land the halving landmarks
# (1.000 → 0.500 → 0.250 → 0.125 …), the half-integers smooth the exponential. Deterministic (no Date/random).
_HALFLIFE_FRACTIONS = ["0", "0.5", "1", "1.5", "2", "2.5", "3", "4", "5"]


def _round_sig(d: Decimal, n: int) -> Decimal:
    if d == 0:
        return Decimal(0)
    return d.quantize(Decimal(1).scaleb(d.adjusted() - (n - 1)), rounding=ROUND_HALF_UP)


def _sig(d: Decimal, n: int) -> str:
    s = format(_round_sig(d, n), "f")
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s or "0"


def half_life_first_order(k: Decimal) -> Decimal:
    """t½ = ln 2 / k — independent of the starting concentration (the first-order signature)."""
    with localcontext() as lc:
        lc.prec = _PREC
        return Decimal(2).ln() / k


def concentration_first_order(c0: Decimal, k: Decimal, t: Decimal) -> Decimal:
    """[A](t) = [A]₀ · e^(−k t) — the exact integrated first-order rate law."""
    with localcontext() as lc:
        lc.prec = _PREC
        return c0 * (-(k * t)).exp()


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


def build_kinetics_lesson(spec: dict, data, ctx: str = "") -> dict:
    """An authored first-order kinetics lesson → the verified `*.kinetics.json` object (ADR-0049). The lesson names a
    reactant whose rate constant + order live in `data/rate-constants.toml` (sourced); the producer requires **first
    order**, computes the integrated rate law [A](t) = [A]₀·e^(−kt), the half-life t½ = ln2/k, and a decay curve
    (sampled at multiples of t½). The rate law is disclosed (model-assumed); the constant is sourced; the decay is
    model-exact-then-rounded. REFUSES a non-first-order reaction, an unknown reactant, or a nonpositive input."""
    for key in ("id", "title", "slug", "topic", "scenario", "reactant", "initial_molarity_M", "misconception"):
        if key not in spec:
            raise BuildError(f"{ctx}: kinetics lesson missing required key '{key}'")

    reactant = spec["reactant"]
    rec = data.rate_constant(reactant)                       # raises if absent (sourced k + order)
    if rec["order"] != 1:
        raise BuildError(f"{ctx}: '{reactant}' is order {rec['order']} — this lesson handles a FIRST-order reaction "
                         f"(the integrated law [A]=[A]₀e^(−kt) and t½=ln2/k are the first-order forms)")
    if rec["k_unit"] != "1/s":
        raise BuildError(f"{ctx}: first-order k must carry '1/s' units (got '{rec['k_unit']}')")
    k = rec["k"]
    c0 = Decimal(str(spec["initial_molarity_M"]))
    if c0 <= 0:
        raise BuildError(f"{ctx}: initial molarity must be positive (got {c0})")

    equation = rec["equation"]
    _balance_ok(equation, ctx)                               # the reaction conserves every element (engine-checked)
    fr = parse_formula(reactant, ctx)

    t_half = half_life_first_order(k)                        # ln2/k (seconds), independent of c0

    # the decay curve: [A] at each sampled time (a multiple of t½). Deterministic + machine-checkable.
    curve = []
    for frac in _HALFLIFE_FRACTIONS:
        n = Decimal(frac)
        t = n * t_half
        c = concentration_first_order(c0, k, t)
        with localcontext() as lc:
            lc.prec = _PREC
            pct_remaining = c / c0 * 100
        curve.append({
            "half_lives": frac,
            "t_seconds": _sig(t, 8), "t_seconds_display": _sig(t, 3),
            "t_hours_display": _sig(t / 3600, 3),
            "concentration_M": _sig(c, 12), "concentration_display": _sig(c, 3),
            "percent_remaining_display": _sig(pct_remaining, 3),
            "percent_decomposed_display": _sig(100 - pct_remaining, 3),
        })

    # the halving landmarks (1, 2, 3 half-lives → c₀/2, c₀/4, c₀/8): each half-life is the SAME t½, whatever remains
    landmarks = []
    for n in (1, 2, 3):
        c = concentration_first_order(c0, k, Decimal(n) * t_half)   # = c0 / 2**n exactly
        landmarks.append({
            "half_lives": n, "t_hours_display": _sig(Decimal(n) * t_half / 3600, 3),
            "concentration_M": _sig(c, 12), "concentration_display": _sig(c, 3),
            "percent_decomposed_display": _sig(100 - c / c0 * 100, 3),
        })

    with localcontext() as lc:
        lc.prec = _PREC
        k_thalf = k * t_half                                # = ln 2 (the machine-checkable half-life relation)

    rate_law_latex = f"\\text{{rate}} = k\\,[{fr.latex}]"
    integrated_latex = f"[{fr.latex}] = [{fr.latex}]_0\\,e^{{-kt}}"
    half_life_latex = "t_{1/2} = \\dfrac{\\ln 2}{k}"

    return {
        "kind": "kinetics",
        "subtype": "first-order",
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
            "order": 1, "statement_latex": rate_law_latex, "k_symbol": "k",
            "k_value": format(k, "f"), "k_display": _sig(k, 3), "k_unit": rec["k_unit"], "k_unit_display": "s⁻¹",
            "source": data.sources.get("rate_constants", ""),
        },
        "integrated": {
            "law_latex": integrated_latex,
            "initial_molarity_M": format(c0, "f"), "initial_molarity_display": _sig(c0, 3),
        },
        "half_life": {
            "symbol": "t_{1/2}", "relation_latex": half_life_latex,
            "seconds": _sig(t_half, 8), "seconds_display": _sig(t_half, 3),
            "hours_display": _sig(t_half / 3600, 3),
            "k_times_thalf": _sig(k_thalf, 8),              # = ln 2 (the machine-checked relation)
        },
        "curve": {"points": curve},
        "result": {
            "half_life_hours_display": _sig(t_half / 3600, 3),
            "half_life_seconds_display": _sig(t_half, 3),
            "landmarks": landmarks,
        },
        "misconception": spec["misconception"],
        "reference_links": spec.get("reference_links", []),
        # the machine-checked facts, SHOWN not asserted (the gate re-derives all four, ADR-0008).
        "checks": {
            "reaction_balanced": True,      # the equation conserves every element (regime-1)
            "integrated_law": True,         # every curve point c(t) = c₀·e^(−kt)
            "half_life_relation": True,     # k·t½ = ln 2, so t½ = ln2/k (independent of c₀)
            "half_life_constant": True,     # c(n·t½) = c₀/2ⁿ — successive half-lives are equal (first-order tell)
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
