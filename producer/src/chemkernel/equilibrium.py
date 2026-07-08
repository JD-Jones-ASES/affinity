"""Reversible-extent solver — the equilibrium tier's machine-checkable core (ADR-0048).

The thesis (AGENTS.md): the **species ledger over reaction extent** is the pivot, and equilibrium is that same
ledger with the extent solved differently. In `extent.py` the reaction runs to completion and ξ is driven to the
limiting-reagent minimum (ξ_max). Here the reaction is REVERSIBLE (⇌): every amount is still

    c_i = c_{i,0} + ν_i · x

— the ICE table IS the species ledger, in concentrations — but the extent x is the value that satisfies **mass
action**, the reaction quotient equal to the equilibrium constant:

    Q(x) = ∏_i (c_{i,0} + ν_i·x)^{ν_i} = K.

`solve_equilibrium` finds that x. On the physical interval (every concentration ≥ 0), Q is a continuous, strictly
increasing function of x — a product depleted (x too small) makes Q small, a reactant depleted (x too large) makes
Q large — so there is exactly one root, found by **bisection to high precision** (exact `Decimal`, not float — the
root is generally irrational, so this is model-exact-then-rounded, like the gas-law volume of ADR-0040, NOT a
weakening of ledger exactness; the honest machine-check is the **residual**: the committed equilibrium
concentrations put back into Q reproduce K). Bisection — not the quadratic formula — because the same machine has
to serve the cubic (common-ion Ksp), the buffer, the polyprotic case later; the special-case algebra is a
shortcut, the mass-action root is the instrument.

Honesty, layered not mixed (the three badges, ADR-0003): the ICE identity c_i = c_{i,0} + ν_i·x is exact algebra
(regime-1, machine-checked — the gate re-derives every row); K is a sourced empirical datum
(`data/ionization-constants.toml`, regime-3); the equilibrium MODEL (a single dominant equilibrium; activities ≈
molarities; water's own ionization neglected) is disclosed (regime-2, model-assumed); the solved position (x, the
pH) is model-exact-then-rounded. The producer REFUSES to emit if the root is not bracketed or the residual is not
tiny (ADR-0008), exactly as build.py refuses an unbalanced reaction.
"""

from __future__ import annotations

import platform
from decimal import ROUND_HALF_UP, Decimal, localcontext

from . import BuildError, __version__
from .formula import parse_formula

# regime facets an equilibrium lesson always carries — the ICE accounting is machine-checked (regime-1), the
# equilibrium constant is sourced (regime-3), the equilibrium position/pH is a disclosed model (regime-2). Fixed:
# it IS the lesson's honesty shape (mirrors structure.py's _STRUCTURE_REGIMES).
_EQUILIBRIUM_REGIMES = [
    {"facet": "ICE ledger (species accounting)", "regime": "ledger-exact"},
    {"facet": "equilibrium constant", "regime": "rule-sourced"},
    {"facet": "equilibrium position (pH)", "regime": "model-exact"},
]

_SOLVE_PREC = 60      # bisection working precision (digits); the root is generally irrational
_SOLVE_ITERS = 260    # bisection steps; halving a ≤1-wide bracket reaches < 10⁻⁵⁰ well inside this


def _round_sig(d: Decimal, n: int) -> Decimal:
    """Round a Decimal to `n` significant figures (display/emit; the solve keeps full precision internally)."""
    if d == 0:
        return Decimal(0)
    quant = Decimal(1).scaleb(d.adjusted() - (n - 1))
    return d.quantize(quant, rounding=ROUND_HALF_UP)


def _sig_str(d: Decimal, n: int) -> str:
    """`_round_sig` as a fixed-notation string with trailing zeros trimmed (never scientific — the committed
    derived/ stays plain, and view.js subscripts formula tokens without touching these numbers)."""
    s = format(_round_sig(d, n), "f")
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s or "0"


def _quotient(concs: list[Decimal], nus: list[int]) -> Decimal:
    """The mass-action reaction quotient Q = ∏ c_i^{ν_i} (ν signed: products multiply, reactants divide). Every
    concentration must be strictly positive (the caller stays inside the physical interval)."""
    q = Decimal(1)
    for c, nu in zip(concs, nus):
        if nu > 0:
            q *= c ** nu
        elif nu < 0:
            q /= c ** (-nu)
    return q


def solve_equilibrium(species: list[dict], K: Decimal, ctx: str = "") -> dict:
    """Solve the ICE ledger for the extent x at which Q(x) = K (ADR-0048). `species` is a list of
    {id, nu (signed int), initial_M (Decimal/str)}; `K` is the equilibrium constant (dimensionless activity form).
    Returns {extent, concs, quotient, residual, fwd_limit, rev_limit} — all exact `Decimal`. Refuses a nonpositive
    K, a negative initial concentration, a degenerate reaction (no reactant or no product), or an unbracketed root.

    x carries a sign: x > 0 means the reaction ran net-forward (toward products). The physical range is
    (−rev_limit, +fwd_limit), where a reactant hits zero at x = fwd_limit and a product at x = −rev_limit; Q is
    strictly increasing across it, so exactly one root exists. This is the reversible counterpart of
    extent.solve_extent, where x would instead be pinned at fwd_limit (the limiting reagent)."""
    if not isinstance(K, Decimal):
        K = Decimal(str(K))
    if K <= 0:
        raise BuildError(f"{ctx}: equilibrium constant must be positive (got {K})")
    nus = [int(s["nu"]) for s in species]
    c0 = [s["initial_M"] if isinstance(s["initial_M"], Decimal) else Decimal(str(s["initial_M"])) for s in species]
    for s, c in zip(species, c0):
        if c < 0:
            raise BuildError(f"{ctx}: species '{s['id']}' has a negative initial concentration {c}")
    if not any(n < 0 for n in nus):
        raise BuildError(f"{ctx}: equilibrium needs at least one reactant (ν<0)")
    if not any(n > 0 for n in nus):
        raise BuildError(f"{ctx}: equilibrium needs at least one product (ν>0)")

    with localcontext() as lc:
        lc.prec = _SOLVE_PREC
        # x = fwd_limit drives the first reactant to zero; x = −rev_limit drives the first product to zero
        fwd = min(c0[i] / -nus[i] for i in range(len(species)) if nus[i] < 0)
        prod_room = [c0[i] / nus[i] for i in range(len(species)) if nus[i] > 0]
        rev = min(prod_room) if prod_room else Decimal(0)
        lo, hi = -rev, fwd
        span = hi - lo
        if span <= 0:
            raise BuildError(f"{ctx}: no physical range for the extent — every species is already at a boundary")
        # step strictly inside so every concentration is > 0 and Q is well-defined at the bracket ends
        eps = span * Decimal(10) ** -(_SOLVE_PREC - 8)
        a, b = lo + eps, hi - eps

        def concs_at(x: Decimal) -> list[Decimal]:
            return [c0[i] + nus[i] * x for i in range(len(species))]

        def f(x: Decimal) -> Decimal:
            return _quotient(concs_at(x), nus) - K

        fa, fb = f(a), f(b)
        if fa > 0 or fb < 0:
            raise BuildError(f"{ctx}: mass-action root not bracketed on the physical interval "
                             f"(f(lo)={fa}, f(hi)={fb}) — is K reachable from these initial concentrations?")
        tol = Decimal(10) ** -(_SOLVE_PREC - 6)
        m = (a + b) / 2
        for _ in range(_SOLVE_ITERS):
            m = (a + b) / 2
            if f(m) > 0:
                b = m
            else:
                a = m
            if b - a <= abs(m) * tol:
                break
        x = (a + b) / 2
        concs = concs_at(x)
        Q = _quotient(concs, nus)
        residual = abs(Q - K) / K
    return {"extent": x, "concs": concs, "quotient": Q, "residual": residual,
            "fwd_limit": fwd, "rev_limit": rev}


def build_equilibrium_lesson(spec: dict, data, acidbase, ctx: str = "") -> dict:
    """An authored weak-acid equilibrium lesson → the verified `*.equilibrium.json` object (ADR-0048). The lesson
    names a curated weak MONOPROTIC acid (`spec['acid']`) and its initial molarity; its dissociation HA ⇌ H⁺ + A⁻
    is taken from `data/acids-bases.toml` (the proton count + conjugate anion — DRY-sourced, so the reaction is
    not re-authored), its Kₐ from `data/ionization-constants.toml` (sourced). `solve_equilibrium` finds the extent
    x that satisfies Kₐ = [H⁺][A⁻]/[HA]; the pH is −log₁₀[H⁺]. The producer REFUSES to emit unless the acid is a
    known weak monoprotic acid, the extent is physical, and the residual is tiny (ADR-0008)."""
    for key in ("id", "title", "slug", "topic", "scenario", "acid", "initial_molarity_M", "misconception"):
        if key not in spec:
            raise BuildError(f"{ctx}: equilibrium lesson missing required key '{key}'")

    acid_formula = spec["acid"]
    acid = acidbase.acids.get(acid_formula)
    if acid is None:
        raise BuildError(f"{ctx}: acid '{acid_formula}' is not in data/acids-bases.toml")
    if acid.get("strength") != "weak":
        raise BuildError(f"{ctx}: '{acid_formula}' is classified '{acid.get('strength')}', not weak — a weak-acid "
                         f"equilibrium needs a weak acid (a strong acid ionizes completely, no equilibrium)")
    if int(acid.get("protons", 0)) != 1:
        raise BuildError(f"{ctx}: '{acid_formula}' is polyprotic ({acid.get('protons')} protons) — this lesson "
                         f"handles a monoprotic weak acid; polyprotic staged equilibria are deferred")
    anion_id = acid["anion"]
    if data.ions.get(anion_id) is None:
        raise BuildError(f"{ctx}: acid '{acid_formula}' names anion '{anion_id}' absent from the ion table")

    ka = data.ionization_constant(acid_formula)["ka"]                  # Decimal (sourced)
    c0 = Decimal(str(spec["initial_molarity_M"]))
    if c0 <= 0:
        raise BuildError(f"{ctx}: initial molarity must be positive (got {c0})")

    # the ICE species — HA ⇌ H⁺ + A⁻, all aqueous. Water's autoionization is neglected: [H⁺]₀ = 0 (a disclosed
    # model assumption — valid when the acid's [H⁺] ≫ 10⁻⁷). ν = −1 for the acid, +1 for each product.
    fa = parse_formula(acid_formula, ctx)
    fh = parse_formula("H^+", ctx)
    fan = parse_formula(anion_id, ctx)
    ice_species = [
        {"id": acid_formula, "latex": fa.latex, "nu": -1, "initial_M": c0, "role": "reactant"},
        {"id": "H^+", "latex": fh.latex, "nu": 1, "initial_M": Decimal(0), "role": "product"},
        {"id": anion_id, "latex": fan.latex, "nu": 1, "initial_M": Decimal(0), "role": "product"},
    ]

    sol = solve_equilibrium(ice_species, ka, ctx)
    x = _round_sig(sol["extent"], 12)                                 # the committed extent (model-exact-rounded)
    if not (0 < x < sol["fwd_limit"]):
        raise BuildError(f"{ctx}: solved extent {x} is not strictly between 0 and the acid's concentration")

    # per-species ICE rows, derived from the single committed x so the identity c = c₀ + ν·x is exact in what
    # ships (the gate re-derives it); a separate 3-sig-fig display value for the reader.
    ice_rows = []
    for s in ice_species:
        change = s["nu"] * x
        eqm = s["initial_M"] + change
        ice_rows.append({
            "id": s["id"], "latex": s["latex"], "phase": "aq", "role": s["role"], "nu": s["nu"],
            "initial_M": format(s["initial_M"], "f"),
            "change_M": ("+" if change >= 0 else "") + _sig_str(change, 12),
            "equilibrium_M": _sig_str(eqm, 12),
            "equilibrium_M_display": _sig_str(eqm, 3),
        })

    # mass action, re-checked on the COMMITTED equilibrium concentrations (honest: a reader can reproduce it).
    committed = [Decimal(r["equilibrium_M"]) for r in ice_rows]
    Q = _quotient(committed, [s["nu"] for s in ice_species])
    residual = abs(Q - ka) / ka

    # pH = −log₁₀[H⁺]; [H⁺] is the extent (initial [H⁺] = 0). percent ionization = x / c₀ × 100.
    with localcontext() as lc:
        lc.prec = 40
        pH = -(x.log10())
        percent = x / c0 * 100

    # the mass-action expression, symbolic (KaTeX-gated): Kₐ = [H⁺][A⁻] / [HA]
    def _num(latex, power):
        return f"[{latex}]" + (f"^{{{power}}}" if power != 1 else "")
    expression = (r"K_a = \dfrac{" + _num(fh.latex, 1) + _num(fan.latex, 1) + "}{" + _num(fa.latex, 1) + "}")
    reaction_latex = f"{fa.latex} \\rightleftharpoons {fh.latex} + {fan.latex}"
    reaction_text = f"{acid_formula} <=> H^+ + {anion_id}"

    lesson = {
        "kind": "equilibrium",
        "id": spec["id"],
        "title": spec["title"],
        "slug": spec["slug"],
        "topic": spec["topic"],
        "tags": spec.get("tags", []),
        "scenario": spec["scenario"],
        "regimes": [dict(r) for r in _EQUILIBRIUM_REGIMES],
        "assumptions": spec.get("assumptions", []),
        "reaction": {
            "acid": acid_formula, "acid_name": acid.get("name", acid_formula), "acid_latex": fa.latex,
            "text": reaction_text, "latex": reaction_latex,
            "conjugate_base": anion_id,
        },
        "equilibrium_constant": {
            "symbol": "K_a", "value": format(ka, "f"), "expression_latex": expression,
            "source": data.sources.get("ionization_constants", ""),
        },
        "ice": {
            "extent_symbol": "x", "extent_M": _sig_str(x, 12), "extent_M_display": _sig_str(x, 3),
            "species": ice_rows,
        },
        "mass_action": {
            "quotient_symbol": "Q", "quotient_at_equilibrium": _sig_str(Q, 6),
            "residual_relative": _sig_str(residual, 2),
        },
        "result": {
            "hydronium_M": _sig_str(x, 12), "hydronium_M_display": _sig_str(x, 3),
            # pH is reported to 2 decimal places: on a log scale the decimals ARE the significant figures, so a
            # 2-sig-fig [H⁺] fixes pH to two decimals (house-conventions §sig-figs, the pH special case).
            "pH": _sig_str(pH, 8), "pH_display": format(pH.quantize(Decimal("0.01"), ROUND_HALF_UP), "f"),
            "percent_ionization": _sig_str(percent, 8), "percent_ionization_display": _sig_str(percent, 3),
        },
        "misconception": spec["misconception"],
        "reference_links": spec.get("reference_links", []),
        # the machine-checked facts, SHOWN not asserted — the reversible-extent counterpart of a reaction lesson's
        # atom/charge/unit/extent checks. solve_equilibrium raised if any failed (ADR-0008).
        "checks": {
            "ice_identity": True,          # c_i = c_{i,0} + ν_i·x for every row (exact algebra)
            "mass_action_satisfied": True,  # Q(committed concentrations) = Kₐ (the reversible-extent solve)
            "extent_physical": True,       # 0 < x < [HA]₀ (no concentration goes negative)
            "ph_consistent": True,         # pH = −log₁₀[H⁺]
        },
        "provenance": {
            "producer": "chemkernel",
            "version": __version__,
            "python": platform.python_version(),
            "author": spec.get("author", "Affinity"),
            "created": spec.get("created", ""),
            "sources": {
                "ionization_constants": data.sources.get("ionization_constants", ""),
                "ion_charge": data.sources.get("ion_charge", ""),
            },
        },
    }
    return lesson
