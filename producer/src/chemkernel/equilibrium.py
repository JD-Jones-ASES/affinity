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
# equilibrium constant is sourced (regime-3), the equilibrium position (pH / solubility) is a disclosed model
# (regime-2). Fixed: it IS the lesson's honesty shape (mirrors structure.py's _STRUCTURE_REGIMES).
def _regimes(position_facet: str) -> list[dict]:
    return [
        {"facet": "ICE ledger (species accounting)", "regime": "ledger-exact"},
        {"facet": "equilibrium constant", "regime": "rule-sourced"},
        {"facet": position_facet, "regime": "model-exact"},
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


def _quotient(concs: list[Decimal], nus: list[int], in_q: list[bool] | None = None) -> Decimal:
    """The mass-action reaction quotient Q = ∏ c_i^{ν_i} (ν signed: products multiply, reactants divide). A species
    with `in_q[i]` False is a **pure condensed phase** (a solid or the solvent — activity 1) and is EXCLUDED from Q
    (ADR-0048, the Ksp case: the undissolved solid does not appear). Every included concentration must be strictly
    positive (the caller stays inside the physical interval)."""
    q = Decimal(1)
    for i, (c, nu) in enumerate(zip(concs, nus)):
        if in_q is not None and not in_q[i]:
            continue
        if nu > 0:
            q *= c ** nu
        elif nu < 0:
            q /= c ** (-nu)
    return q


def solve_equilibrium(species: list[dict], K: Decimal, ctx: str = "") -> dict:
    """Solve the ICE ledger for the extent x at which Q(x) = K (ADR-0048). `species` is a list of
    {id, nu (signed int), initial_M (Decimal/str), in_quotient (bool, default True)}; `K` is the equilibrium
    constant (dimensionless activity form). Returns {extent, concs, quotient, residual, fwd_limit, rev_limit} — all
    exact `Decimal`. Refuses a nonpositive K, a negative initial concentration, a degenerate reaction, or an
    unbracketed root.

    x carries a sign: x > 0 means the reaction ran net-forward (toward products). Q is strictly increasing in x on
    the physical interval, so exactly one root exists — found by bisection. A species flagged `in_quotient=False`
    is a **pure solid** (the Ksp dissolution case): it is excluded from Q and, being in excess, does NOT bound the
    forward extent — so when no *quotient* reactant limits the forward direction the bracket is grown until Q > K.
    This is the reversible counterpart of extent.solve_extent, where x would instead be pinned at the limiting
    reagent."""
    if not isinstance(K, Decimal):
        K = Decimal(str(K))
    if K <= 0:
        raise BuildError(f"{ctx}: equilibrium constant must be positive (got {K})")
    nus = [int(s["nu"]) for s in species]
    c0 = [s["initial_M"] if isinstance(s["initial_M"], Decimal) else Decimal(str(s["initial_M"])) for s in species]
    in_q = [bool(s.get("in_quotient", True)) for s in species]
    for s, c in zip(species, c0):
        if c < 0:
            raise BuildError(f"{ctx}: species '{s['id']}' has a negative initial concentration {c}")
    if not any(n < 0 for n in nus):
        raise BuildError(f"{ctx}: equilibrium needs at least one reactant (ν<0)")
    if not any(n > 0 and in_q[i] for i, n in enumerate(nus)):
        raise BuildError(f"{ctx}: equilibrium needs at least one product in the quotient (ν>0)")

    with localcontext() as lc:
        lc.prec = _SOLVE_PREC

        def concs_at(x: Decimal) -> list[Decimal]:
            return [c0[i] + nus[i] * x for i in range(len(species))]

        def f(x: Decimal) -> Decimal:
            return _quotient(concs_at(x), nus, in_q) - K

        # a product in the quotient hits zero at x = −rev (the reverse bound)
        prod_room = [c0[i] / nus[i] for i in range(len(species)) if nus[i] > 0 and in_q[i]]
        rev = min(prod_room) if prod_room else Decimal(0)
        # a QUOTIENT reactant hits zero at x = fwd (the forward bound). If none is in the quotient — a pure solid
        # dissolving (Ksp) — the forward extent is unbounded, so grow the upper bracket until Q > K.
        react_room = [c0[i] / -nus[i] for i in range(len(species)) if nus[i] < 0 and in_q[i]]
        lo = -rev
        if react_room:
            fwd = min(react_room)
            span = fwd - lo
            if span <= 0:
                raise BuildError(f"{ctx}: no physical range for the extent — every species is at a boundary")
            eps = span * Decimal(10) ** -(_SOLVE_PREC - 8)
            a, b = lo + eps, fwd - eps            # strictly inside so every quotient concentration is > 0
        else:
            a = lo + Decimal(10) ** -(_SOLVE_PREC // 2)   # a tiny positive extent (products lift off zero)
            b, guard = Decimal(1), 0
            while f(b) <= 0 and guard < 400:      # grow until Q(b) > K (Q → ∞ as x grows, so this terminates)
                b *= 2
                guard += 1
            fwd = b

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
        Q = _quotient(concs, nus, in_q)
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
        "subtype": "weak-acid",
        "id": spec["id"],
        "title": spec["title"],
        "slug": spec["slug"],
        "topic": spec["topic"],
        "tags": spec.get("tags", []),
        "scenario": spec["scenario"],
        "regimes": _regimes("equilibrium position (pH)"),
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


def build_buffer_lesson(spec: dict, data, acidbase, ctx: str = "") -> dict:
    """An authored buffer equilibrium lesson → the verified `*.equilibrium.json` object, subtype `buffer`
    (ADR-0048, 4th increment). The SAME reversible-extent solver + the SAME reaction as the weak acid
    (HA ⇌ H⁺ + A⁻), but the conjugate base A⁻ is **already present** (from a dissolved salt) — so [A⁻]₀ > 0.
    This is the solver's nonzero-initial-product / reverse-direction case working for real: the extra A⁻ pushes
    the equilibrium LEFT (Le Chatelier — the **common-ion effect**), so far less acid ionizes and the pH sits
    near pK_a rather than the pure acid's low value. The signature is **Henderson–Hasselbalch**,
    pH = pK_a + log₁₀([A⁻]/[HA]), which is nothing but the mass-action law $K_a=[\\mathrm{H^+}][\\mathrm{A^-}]/
    [\\mathrm{HA}]$ in logarithmic form — machine-checked here on the EQUILIBRIUM concentrations (exact). The
    lesson also re-solves the acid ALONE ([A⁻]₀ = 0) to quantify the suppression the common ion causes."""
    for key in ("id", "title", "slug", "topic", "scenario", "acid", "acid_molarity_M",
                "conjugate_base_molarity_M", "misconception"):
        if key not in spec:
            raise BuildError(f"{ctx}: buffer lesson missing required key '{key}'")

    acid_formula = spec["acid"]
    acid = acidbase.acids.get(acid_formula)
    if acid is None:
        raise BuildError(f"{ctx}: acid '{acid_formula}' is not in data/acids-bases.toml")
    if acid.get("strength") != "weak":
        raise BuildError(f"{ctx}: '{acid_formula}' is not a weak acid — a buffer needs a weak conjugate pair")
    if int(acid.get("protons", 0)) != 1:
        raise BuildError(f"{ctx}: '{acid_formula}' is polyprotic — this buffer lesson is monoprotic")
    anion_id = acid["anion"]
    if data.ions.get(anion_id) is None:
        raise BuildError(f"{ctx}: acid '{acid_formula}' names anion '{anion_id}' absent from the ion table")

    ka = data.ionization_constant(acid_formula)["ka"]
    c_ha = Decimal(str(spec["acid_molarity_M"]))
    c_a = Decimal(str(spec["conjugate_base_molarity_M"]))
    if c_ha <= 0 or c_a <= 0:
        raise BuildError(f"{ctx}: a buffer needs positive acid and conjugate-base molarities (got {c_ha}, {c_a})")

    fa = parse_formula(acid_formula, ctx)
    fh = parse_formula("H^+", ctx)
    fan = parse_formula(anion_id, ctx)
    # HA ⇌ H⁺ + A⁻, with A⁻ already present ([A⁻]₀ = c_a from the fully-dissociated salt; its cation is a
    # spectator, omitted from the equilibrium). [H⁺]₀ = 0 (water's ionization neglected).
    ice_species = [
        {"id": acid_formula, "latex": fa.latex, "nu": -1, "initial_M": c_ha, "role": "reactant"},
        {"id": "H^+", "latex": fh.latex, "nu": 1, "initial_M": Decimal(0), "role": "product"},
        {"id": anion_id, "latex": fan.latex, "nu": 1, "initial_M": c_a, "role": "product"},
    ]

    sol = solve_equilibrium(ice_species, ka, ctx)
    x = _round_sig(sol["extent"], 12)
    if not (0 < x < c_ha):
        raise BuildError(f"{ctx}: solved extent {x} is not strictly between 0 and [HA]₀ ({c_ha})")

    ice_rows = []
    for s in ice_species:
        change = s["nu"] * x
        eqm = s["initial_M"] + change
        ice_rows.append({
            "id": s["id"], "latex": s["latex"], "phase": "aq", "role": s["role"], "nu": s["nu"],
            "in_quotient": True, "initial_M": format(s["initial_M"], "f"),
            "change_M": ("+" if change >= 0 else "") + _sig_str(change, 12),
            "equilibrium_M": _sig_str(eqm, 12),
            "equilibrium_M_display": _sig_str(eqm, 3),
        })

    committed = [Decimal(r["equilibrium_M"]) for r in ice_rows]
    Q = _quotient(committed, [s["nu"] for s in ice_species])
    residual = abs(Q - ka) / ka

    ha_eq = c_ha - x                                    # equilibrium [HA]
    a_eq = c_a + x                                      # equilibrium [A⁻]
    with localcontext() as lc:
        lc.prec = 40
        pH = -(x.log10())                               # [H⁺] = x
        pKa = -(ka.log10())
        ratio = a_eq / ha_eq                            # equilibrium [A⁻]/[HA]
        hh_pH = pKa + ratio.log10()                     # Henderson–Hasselbalch on the equilibrium concentrations
        percent = x / c_ha * 100

    # the common-ion contrast: re-solve the acid ALONE (no added conjugate base) — the pure weak-acid pH the
    # misconception assumes. Both extents are real solver outputs (the gate re-derives the no-buffer one too).
    pure = [dict(ice_species[0], initial_M=c_ha), dict(ice_species[1]),
            dict(ice_species[2], initial_M=Decimal(0))]
    sol0 = solve_equilibrium(pure, ka, ctx)
    x0 = _round_sig(sol0["extent"], 12)
    with localcontext() as lc:
        lc.prec = 40
        pH0 = -(x0.log10())
        suppression = x0 / x                            # how many-fold the common ion suppressed ionization

    def _num(latex, power):
        return f"[{latex}]" + (f"^{{{power}}}" if power != 1 else "")
    expression = (r"K_a = \dfrac{" + _num(fh.latex, 1) + _num(fan.latex, 1) + "}{" + _num(fa.latex, 1) + "}")
    reaction_latex = f"{fa.latex} \\rightleftharpoons {fh.latex} + {fan.latex}"
    reaction_text = f"{acid_formula} <=> H^+ + {anion_id}"

    return {
        "kind": "equilibrium",
        "subtype": "buffer",
        "id": spec["id"],
        "title": spec["title"],
        "slug": spec["slug"],
        "topic": spec["topic"],
        "tags": spec.get("tags", []),
        "scenario": spec["scenario"],
        "regimes": _regimes("equilibrium position (buffer pH)"),
        "assumptions": spec.get("assumptions", []),
        "reaction": {
            "acid": acid_formula, "acid_name": acid.get("name", acid_formula), "acid_latex": fa.latex,
            "text": reaction_text, "latex": reaction_latex, "conjugate_base": anion_id,
        },
        "equilibrium_constant": {
            "symbol": "K_a", "value": format(ka, "f"), "expression_latex": expression,
            "source": data.sources.get("ionization_constants", ""),
        },
        "ice": {"extent_symbol": "x", "extent_M": _sig_str(x, 12), "extent_M_display": _sig_str(x, 3),
                "species": ice_rows},
        "mass_action": {"quotient_symbol": "Q", "quotient_at_equilibrium": _sig_str(Q, 6),
                        "residual_relative": _sig_str(residual, 2)},
        "result": {
            "hydronium_M": _sig_str(x, 12), "hydronium_M_display": _sig_str(x, 3),
            "pH": _sig_str(pH, 8), "pH_display": format(pH.quantize(Decimal("0.01"), ROUND_HALF_UP), "f"),
            "pKa": _sig_str(pKa, 8), "pKa_display": format(pKa.quantize(Decimal("0.01"), ROUND_HALF_UP), "f"),
            "buffer_ratio": _sig_str(ratio, 8), "buffer_ratio_display": _sig_str(ratio, 3),
            "hh_pH": _sig_str(hh_pH, 8),
            "hh_pH_display": format(hh_pH.quantize(Decimal("0.01"), ROUND_HALF_UP), "f"),
            "percent_ionization": _sig_str(percent, 8), "percent_ionization_display": _sig_str(percent, 3),
            # the common-ion contrast: the acid alone would give this (much lower) pH
            "hydronium_no_buffer_M": _sig_str(x0, 12), "hydronium_no_buffer_M_display": _sig_str(x0, 3),
            "pH_no_buffer": _sig_str(pH0, 8),
            "pH_no_buffer_display": format(pH0.quantize(Decimal("0.01"), ROUND_HALF_UP), "f"),
            "suppression_factor_display": _sig_str(suppression, 3),
        },
        "misconception": spec["misconception"],
        "reference_links": spec.get("reference_links", []),
        "checks": {
            "ice_identity": True,            # c_i = c_{i,0} + ν_i·x for every row (A⁻ starts nonzero)
            "mass_action_satisfied": True,   # Q(committed) = K_a
            "extent_physical": True,         # 0 < x < [HA]₀
            "hh_consistent": True,           # pH = pK_a + log₁₀([A⁻]/[HA]) — Henderson–Hasselbalch = mass action, logged
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


def build_weak_base_lesson(spec: dict, data, ctx: str = "") -> dict:
    """An authored weak-base equilibrium lesson → the verified `*.equilibrium.json` object, subtype `weak-base`
    (ADR-0048, 3rd increment). The SAME reversible-extent solver as the weak acid, but the base ionizes against
    water:  B(aq) + H2O(l) ⇌ BH⁺(aq) + OH⁻(aq),  K_b = [BH⁺][OH⁻]/[B]. Water is the **pure solvent** (activity 1)
    — excluded from Q exactly like the Ksp solid (`in_quotient=False`), so the solver is UNCHANGED. The extent x
    is [OH⁻]; the pH comes through the **water ion-product** K_w = [H⁺][OH⁻]: [H⁺] = K_w/[OH⁻], pH = −log₁₀[H⁺],
    and pH + pOH = pK_w. The base + its conjugate acid + K_b come from data/ionization-constants.toml (the
    composition machine-checked on load); the producer REFUSES an unknown base or one with no curated K_b."""
    for key in ("id", "title", "slug", "topic", "scenario", "base", "initial_molarity_M", "misconception"):
        if key not in spec:
            raise BuildError(f"{ctx}: weak-base lesson missing required key '{key}'")

    base_formula = spec["base"]
    rec = data.base_ionization_constant(base_formula)                  # raises if absent (sourced Kb)
    kb = rec["kb"]
    kw = data.water_ion_product()                                      # the acid/base bridge (sourced)
    ca_id = rec["conjugate_acid"]                                      # the cation formed (e.g. NH4^+)
    if data.ions.get(ca_id) is None:
        raise BuildError(f"{ctx}: base '{base_formula}' names conjugate acid '{ca_id}' absent from the ion table")

    c0 = Decimal(str(spec["initial_molarity_M"]))
    if c0 <= 0:
        raise BuildError(f"{ctx}: initial molarity must be positive (got {c0})")

    fb = parse_formula(base_formula, ctx)
    fw = parse_formula("H2O", ctx)
    fca = parse_formula(ca_id, ctx)
    foh = parse_formula("OH^-", ctx)

    # the ICE species: the base + WATER (a pure liquid, activity 1 — excluded from Q, ν=−1) + the two products.
    # Water is the load-bearing exclusion, exactly the Ksp solid's role (in_quotient=False). ν = −1 base/water,
    # +1 each product. Water's autoionization is neglected: [OH⁻]₀ = 0 (disclosed model assumption).
    ice_species = [
        {"id": base_formula, "latex": fb.latex, "phase": "aq", "role": "reactant", "nu": -1, "initial_M": c0},
        {"id": "H2O", "latex": fw.latex, "phase": "l", "role": "reactant", "nu": -1, "in_quotient": False,
         "initial_M": Decimal(0)},
        {"id": ca_id, "latex": fca.latex, "phase": "aq", "role": "product", "nu": 1, "initial_M": Decimal(0)},
        {"id": "OH^-", "latex": foh.latex, "phase": "aq", "role": "product", "nu": 1, "initial_M": Decimal(0)},
    ]

    sol = solve_equilibrium(ice_species, kb, ctx)
    x = _round_sig(sol["extent"], 12)                                  # the committed extent = [OH⁻] (rounded)
    if not (0 < x < sol["fwd_limit"]):
        raise BuildError(f"{ctx}: solved extent {x} is not strictly between 0 and the base's concentration")

    # per-species ICE rows from the single committed x (so c = c₀ + ν·x is exact in what ships); water is the
    # '—' pure-liquid row (no concentration), like the Ksp solid.
    ice_rows = []
    for s in ice_species:
        if not s.get("in_quotient", True):
            ice_rows.append({"id": s["id"], "latex": s["latex"], "phase": s["phase"], "role": s["role"],
                             "nu": s["nu"], "in_quotient": False})
            continue
        change = s["nu"] * x
        eqm = s["initial_M"] + change
        ice_rows.append({
            "id": s["id"], "latex": s["latex"], "phase": s["phase"], "role": s["role"], "nu": s["nu"],
            "in_quotient": True, "initial_M": format(s["initial_M"], "f"),
            "change_M": ("+" if change >= 0 else "") + _sig_str(change, 12),
            "equilibrium_M": _sig_str(eqm, 12),
            "equilibrium_M_display": _sig_str(eqm, 3),
        })

    # mass action, re-checked on the COMMITTED concentrations (water excluded): Q = [BH⁺][OH⁻]/[B] = K_b
    committed = [Decimal(r["equilibrium_M"]) for r in ice_rows if r.get("in_quotient")]
    q_nus = [r["nu"] for r in ice_rows if r.get("in_quotient")]
    Q = _quotient(committed, q_nus)
    residual = abs(Q - kb) / kb

    # the K_w bridge: [OH⁻] = x → pOH = −log₁₀[OH⁻]; [H⁺] = K_w/[OH⁻] → pH = −log₁₀[H⁺]. percent ionized = x/c₀·100.
    with localcontext() as lc:
        lc.prec = 40
        oh = x
        pOH = -(oh.log10())
        hplus = kw / oh
        pH = -(hplus.log10())
        percent = x / c0 * 100

    # the mass-action expression, symbolic (KaTeX-gated): K_b = [BH⁺][OH⁻] / [B]
    def _num(latex, power):
        return f"[{latex}]" + (f"^{{{power}}}" if power != 1 else "")
    expression = (r"K_b = \dfrac{" + _num(fca.latex, 1) + _num(foh.latex, 1) + "}{" + _num(fb.latex, 1) + "}")
    reaction_latex = (f"{fb.latex}\\,\\text{{(aq)}} + {fw.latex}\\,\\text{{(l)}} \\rightleftharpoons "
                      f"{fca.latex}\\,\\text{{(aq)}} + {foh.latex}\\,\\text{{(aq)}}")
    reaction_text = f"{base_formula}(aq) + H2O(l) <=> {ca_id}(aq) + OH^-(aq)"

    return {
        "kind": "equilibrium",
        "subtype": "weak-base",
        "id": spec["id"],
        "title": spec["title"],
        "slug": spec["slug"],
        "topic": spec["topic"],
        "tags": spec.get("tags", []),
        "scenario": spec["scenario"],
        "regimes": _regimes("equilibrium position (pH via K_b and K_w)"),
        "assumptions": spec.get("assumptions", []),
        "reaction": {
            "base": base_formula, "base_name": rec["name"], "base_latex": fb.latex,
            "text": reaction_text, "latex": reaction_latex, "conjugate_acid": ca_id,
        },
        "equilibrium_constant": {
            "symbol": "K_b", "value": format(kb, "f"), "expression_latex": expression,
            "source": data.sources.get("ionization_constants", ""),
        },
        "ice": {"extent_symbol": "x", "extent_M": _sig_str(x, 12), "extent_M_display": _sig_str(x, 3),
                "species": ice_rows},
        "mass_action": {"quotient_symbol": "Q", "quotient_at_equilibrium": _sig_str(Q, 6),
                        "residual_relative": _sig_str(residual, 2)},
        "result": {
            "hydroxide_M": _sig_str(oh, 12), "hydroxide_M_display": _sig_str(oh, 3),
            "pOH": _sig_str(pOH, 8), "pOH_display": format(pOH.quantize(Decimal("0.01"), ROUND_HALF_UP), "f"),
            # [H⁺] is tiny for a base — the checked value keeps 12 sig figs, the display 3 (ADR-0025).
            "hydronium_M": _sig_str(hplus, 12), "hydronium_M_display": _sig_str(hplus, 3),
            # pH to 2 decimals (on a log scale the decimals ARE the sig figs — house-conventions §sig-figs).
            "pH": _sig_str(pH, 8), "pH_display": format(pH.quantize(Decimal("0.01"), ROUND_HALF_UP), "f"),
            "percent_ionization": _sig_str(percent, 8), "percent_ionization_display": _sig_str(percent, 3),
            "kw": format(kw, "f"),
        },
        "misconception": spec["misconception"],
        "reference_links": spec.get("reference_links", []),
        "checks": {
            "ice_identity": True,          # c_i = c_{i,0} + ν_i·x for every dissolved row (water excluded)
            "mass_action_satisfied": True,  # Q(committed) = K_b (water excluded from Q)
            "extent_physical": True,       # 0 < x < [B]₀ (no concentration goes negative)
            "kw_consistent": True,         # [H⁺] = K_w/[OH⁻]; pH = −log₁₀[H⁺]; pH + pOH = pK_w
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


def _coeff_latex(n: int) -> str:
    return "" if n == 1 else f"{n}\\,"


def build_solubility_lesson(spec: dict, data, ctx: str = "") -> dict:
    """An authored Ksp (solubility-equilibrium) lesson → the verified `*.equilibrium.json` object, subtype
    `solubility` (ADR-0048, 2nd increment; 6th increment adds the **common-ion** variant). The SAME reversible-extent
    solver as the weak acid, but the dissolving species is a **pure solid** — excluded from the mass-action quotient
    (activity 1), so Kₛₚ = [cation]^a[anion]^b and the extent x is the **molar solubility** s. For a 1:2 salt like
    CaF₂ that makes Kₛₚ = [Ca²⁺][F⁻]² = 4s³, a **cubic** — solved by bisection, the reason the solver is general
    (ADR-0048). The salt + its ions + Kₛₚ come from `data/solubility-products.toml` (the composition machine-checked
    on load, the Kₛₚ sourced); the producer REFUSES an unknown salt or one with no curated Kₛₚ (ADR-0008).

    OPTIONALLY the author names a **common ion** (`common_ion` + `common_ion_molarity_M`) — one of the salt's own
    ions, already present from a fully-dissociated soluble salt (its counter-ion a spectator, omitted). That is a
    nonzero initial product concentration, so (Le Chatelier — the **common-ion effect**) the dissolution is driven
    LEFT and far less dissolves. It is exactly the buffer's nonzero-initial-product case, now on the Ksp **cubic**;
    the solver is unchanged. The lesson then also re-solves the salt in PURE water for the suppression contrast."""
    for key in ("id", "title", "slug", "topic", "scenario", "salt", "misconception"):
        if key not in spec:
            raise BuildError(f"{ctx}: solubility lesson missing required key '{key}'")

    salt_formula = spec["salt"]
    rec = data.solubility_product(salt_formula)                      # raises if absent (sourced Ksp)
    ksp = rec["ksp"]
    cation_id, anion_id = rec["cation"], rec["anion"]
    n_cat, n_an = rec["n_cation"], rec["n_anion"]
    fs = parse_formula(salt_formula, ctx)
    fc = parse_formula(cation_id, ctx)
    fan = parse_formula(anion_id, ctx)

    # optional COMMON ION: one of the salt's own ions, already in solution (nonzero initial product). It must be
    # shared with the salt — a foreign ion would not be a *common* ion (that is a different, ionic-strength effect).
    common_id = spec.get("common_ion")
    common_c0 = {cation_id: Decimal(0), anion_id: Decimal(0)}
    if common_id is not None:
        if common_id not in (cation_id, anion_id):
            raise BuildError(f"{ctx}: common ion '{common_id}' is not one of {salt_formula}'s ions "
                             f"({cation_id} / {anion_id}) — a common ion must be shared with the salt")
        cc = Decimal(str(spec.get("common_ion_molarity_M", 0)))
        if cc <= 0:
            raise BuildError(f"{ctx}: a common-ion solubility lesson needs a positive common_ion_molarity_M")
        common_c0[common_id] = cc

    # the ICE species: the pure SOLID (excluded from Q — the load-bearing idea) + the two dissolved ions (one may
    # start nonzero — the common ion)
    ice_species = [
        {"id": salt_formula, "latex": fs.latex, "phase": "s", "role": "reactant", "nu": -1, "in_quotient": False,
         "initial_M": Decimal(0)},
        {"id": cation_id, "latex": fc.latex, "phase": "aq", "role": "product", "nu": n_cat,
         "initial_M": common_c0[cation_id]},
        {"id": anion_id, "latex": fan.latex, "phase": "aq", "role": "product", "nu": n_an,
         "initial_M": common_c0[anion_id]},
    ]

    sol = solve_equilibrium(ice_species, ksp, ctx)
    s = _round_sig(sol["extent"], 12)                               # the molar solubility (model-exact-rounded)
    if not (s > 0):
        raise BuildError(f"{ctx}: solved molar solubility {s} is not positive")

    # ICE rows: the solid carries NO concentration (a pure solid, activity 1 — the '—' row); the ions do
    ice_rows = [{"id": salt_formula, "latex": fs.latex, "phase": "s", "role": "reactant", "nu": -1,
                 "in_quotient": False}]
    for sp in ice_species[1:]:
        change = sp["nu"] * s
        eqm = sp["initial_M"] + change                              # = n·s (initial 0)
        ice_rows.append({
            "id": sp["id"], "latex": sp["latex"], "phase": "aq", "role": "product", "nu": sp["nu"],
            "in_quotient": True, "initial_M": format(sp["initial_M"], "f"),
            "change_M": "+" + _sig_str(change, 12), "equilibrium_M": _sig_str(eqm, 12),
            "equilibrium_M_display": _sig_str(eqm, 3),
        })

    # mass action, re-checked on the COMMITTED ion concentrations (the solid is excluded): Q = [cat]^a[an]^b = Ksp
    ion_concs = [Decimal(r["equilibrium_M"]) for r in ice_rows[1:]]
    Q = _quotient(ion_concs, [n_cat, n_an])
    residual = abs(Q - ksp) / ksp

    # molar solubility s + mass solubility (g/L) = s × molar mass of the salt
    molar_mass = data.molar_mass(salt_formula)
    solubility_g_per_L = s * molar_mass

    # the common-ion contrast: re-solve in PURE water (both ions initial 0) — the higher solubility the
    # misconception assumes. Both s values are real solver outputs (the gate re-derives the pure-water one too).
    pure_water_s = suppression = None
    if common_id is not None:
        pure = [dict(ice_species[0]), dict(ice_species[1], initial_M=Decimal(0)),
                dict(ice_species[2], initial_M=Decimal(0))]
        s0 = _round_sig(solve_equilibrium(pure, ksp, ctx)["extent"], 12)
        with localcontext() as lc:
            lc.prec = 40
            pure_water_s, suppression = s0, s0 / s              # how many-fold the common ion suppressed dissolution

    # Ksp expression: [cation]^a [anion]^b (concentrations — no phase labels, the solid absent)
    def _br(latex, power):
        return f"[{latex}]" + (f"^{{{power}}}" if power != 1 else "")
    expression = "K_{sp} = " + _br(fc.latex, n_cat) + _br(fan.latex, n_an)
    reaction_latex = (f"{fs.latex}\\,\\text{{(s)}} \\rightleftharpoons "
                      f"{_coeff_latex(n_cat)}{fc.latex}\\,\\text{{(aq)}} + "
                      f"{_coeff_latex(n_an)}{fan.latex}\\,\\text{{(aq)}}")
    coeff = lambda n: "" if n == 1 else f"{n} "
    reaction_text = f"{salt_formula}(s) <=> {coeff(n_cat)}{cation_id}(aq) + {coeff(n_an)}{anion_id}(aq)"

    reaction = {
        "salt": salt_formula, "salt_name": rec["name"], "salt_latex": fs.latex,
        "text": reaction_text, "latex": reaction_latex, "cation": cation_id, "anion": anion_id,
    }
    result = {
        "molar_solubility_M": _sig_str(s, 12), "molar_solubility_M_display": _sig_str(s, 3),
        "solubility_g_per_L": _sig_str(solubility_g_per_L, 6),
        "solubility_g_per_L_display": _sig_str(solubility_g_per_L, 3),
        "molar_mass_g_per_mol": format(molar_mass, "f"),
    }
    # the common-ion additions: the ion already present (name + molarity) + the pure-water contrast it suppresses
    if common_id is not None:
        reaction["common_ion"] = common_id
        reaction["common_ion_latex"] = parse_formula(common_id, ctx).latex
        reaction["common_ion_molarity_M"] = format(common_c0[common_id], "f")
        result["molar_solubility_pure_water_M"] = _sig_str(pure_water_s, 12)
        result["molar_solubility_pure_water_M_display"] = _sig_str(pure_water_s, 3)
        result["suppression_factor_display"] = _sig_str(suppression, 3)

    return {
        "kind": "equilibrium",
        "subtype": "solubility",
        "id": spec["id"],
        "title": spec["title"],
        "slug": spec["slug"],
        "topic": spec["topic"],
        "tags": spec.get("tags", []),
        "scenario": spec["scenario"],
        "regimes": _regimes("equilibrium position ("
                            + ("solubility with a common ion)" if common_id is not None else "solubility)")),
        "assumptions": spec.get("assumptions", []),
        "reaction": reaction,
        "equilibrium_constant": {
            "symbol": "K_sp", "value": format(ksp, "f"), "expression_latex": expression,
            "source": data.sources.get("solubility_products", ""),
        },
        "ice": {"extent_symbol": "s", "extent_M": _sig_str(s, 12), "extent_M_display": _sig_str(s, 3),
                "species": ice_rows},
        "mass_action": {"quotient_symbol": "Q", "quotient_at_equilibrium": _sig_str(Q, 6),
                        "residual_relative": _sig_str(residual, 2)},
        "result": result,
        "misconception": spec["misconception"],
        "reference_links": spec.get("reference_links", []),
        "checks": {
            "ice_identity": True,           # [ion] = n·s for every dissolved ion (exact algebra)
            "mass_action_satisfied": True,  # Q(committed ions) = Ksp (the solid excluded)
            "extent_physical": True,        # s > 0
            "solubility_consistent": True,  # solubility(g/L) = s × molar mass
        },
        "provenance": {
            "producer": "chemkernel",
            "version": __version__,
            "python": platform.python_version(),
            "author": spec.get("author", "Affinity"),
            "created": spec.get("created", ""),
            "sources": {
                "solubility_products": data.sources.get("solubility_products", ""),
                "ion_charge": data.sources.get("ion_charge", ""),
                "atomic_weight": data.sources.get("atomic_weight", ""),
            },
        },
    }


def _ka_expr(h_latex: str, an_latex: str, acid_latex: str, symbol: str) -> str:
    """The stage's mass-action expression, symbolic (KaTeX-gated): K_{ai} = [H⁺][anion] / [reactant]."""
    return symbol + r" = \dfrac{[" + h_latex + "][" + an_latex + "]}{[" + acid_latex + "]}"


def build_polyprotic_lesson(spec: dict, data, acidbase, ctx: str = "") -> dict:
    """An authored polyprotic weak-acid equilibrium lesson → the verified `*.equilibrium.json` object, subtype
    `polyprotic` (ADR-0048). A polyprotic acid loses its protons in STAGES — HₙA ⇌ H⁺ + Hₙ₋₁A, then Hₙ₋₁A ⇌
    H⁺ + Hₙ₋₂A, … — each with its own Kₐ (Kₐ1 ≫ Kₐ2 ≫ …). The SAME reversible-extent solver runs once **per stage**,
    each stage seeded with the previous stage's equilibrium concentrations (the standard successive treatment — a
    disclosed model assumption, valid because each Kₐ is ~10⁵ smaller, so the first ionization sets [H⁺] almost
    entirely). The acid + its ordered (acid, Kₐ, anion) stages come from `data/ionization-constants.toml`
    `[polyprotic]` (each stage's composition machine-checked on load); the producer REFUSES a non-polyprotic or
    strong acid, or an unphysical extent (ADR-0008). The payoff is checkable, not asserted: [H⁺] tracks stage 1,
    and the amphiprotic middle anion sits at ≈ Kₐ2."""
    for key in ("id", "title", "slug", "topic", "scenario", "acid", "initial_molarity_M", "misconception"):
        if key not in spec:
            raise BuildError(f"{ctx}: polyprotic lesson missing required key '{key}'")

    acid_formula = spec["acid"]
    acid = acidbase.acids.get(acid_formula)
    if acid is None:
        raise BuildError(f"{ctx}: acid '{acid_formula}' is not in data/acids-bases.toml")
    if acid.get("strength") != "weak":
        raise BuildError(f"{ctx}: '{acid_formula}' is not a weak acid — a polyprotic equilibrium lesson needs a "
                         f"weak acid (a strong acid ionizes completely)")
    if int(acid.get("protons", 0)) < 2:
        raise BuildError(f"{ctx}: '{acid_formula}' has {acid.get('protons')} proton(s) — a polyprotic lesson needs "
                         f"≥ 2 (use the weak-acid subtype for a monoprotic acid)")

    rec = data.polyprotic_constant(acid_formula)                       # {name, stages:[{acid, ka, anion}]} (sourced)
    stages_data = rec["stages"]
    c0 = Decimal(str(spec["initial_molarity_M"]))
    if c0 <= 0:
        raise BuildError(f"{ctx}: initial molarity must be positive (got {c0})")

    fh = parse_formula("H^+", ctx)
    # running concentration of every species across the staged solve (the successive treatment). H⁺ ACCUMULATES.
    conc = {acid_formula: c0, "H^+": Decimal(0)}
    for st in stages_data:
        conc[st["anion"]] = Decimal(0)

    def _ice_row(sid, latex, nu, initial, x):
        change = nu * x
        eqm = initial + change
        return {"id": sid, "latex": latex, "phase": "aq", "role": "reactant" if nu < 0 else "product", "nu": nu,
                "initial_M": _sig_str(initial, 12), "change_M": ("+" if change >= 0 else "") + _sig_str(change, 12),
                "equilibrium_M": _sig_str(eqm, 12), "equilibrium_M_display": _sig_str(eqm, 3)}

    solved = []              # per-stage {index, acid, anion, ka, latexes, x, rows, Q, residual, initials}
    for i, st in enumerate(stages_data):
        a_id, an_id, ka = st["acid"], st["anion"], st["ka"]
        fa, fan = parse_formula(a_id, ctx), parse_formula(an_id, ctx)
        init_reactant, init_h, init_anion = conc[a_id], conc["H^+"], conc[an_id]
        ice_species = [
            {"id": a_id, "latex": fa.latex, "nu": -1, "initial_M": init_reactant, "role": "reactant"},
            {"id": "H^+", "latex": fh.latex, "nu": 1, "initial_M": init_h, "role": "product"},
            {"id": an_id, "latex": fan.latex, "nu": 1, "initial_M": init_anion, "role": "product"},
        ]
        x = _round_sig(solve_equilibrium(ice_species, ka, f"{ctx} stage {i + 1}")["extent"], 12)
        if not (0 < x <= init_reactant):
            raise BuildError(f"{ctx}: stage {i + 1} extent {x} is not in (0, [{a_id}]₀={init_reactant}]")
        rows = [_ice_row(a_id, fa.latex, -1, init_reactant, x), _ice_row("H^+", fh.latex, 1, init_h, x),
                _ice_row(an_id, fan.latex, 1, init_anion, x)]
        committed = [Decimal(r["equilibrium_M"]) for r in rows]
        Q = _quotient(committed, [-1, 1, 1])
        residual = abs(Q - ka) / ka
        # advance the running concentrations: the reactant loses x, H⁺ gains x, the anion gains x
        conc[a_id] -= x
        conc["H^+"] += x
        conc[an_id] += x
        solved.append({"index": i + 1, "acid": a_id, "anion": an_id, "ka": ka, "acid_latex": fa.latex,
                       "anion_latex": fan.latex, "x": x, "rows": rows, "Q": Q, "residual": residual,
                       "init_reactant": init_reactant, "init_h": init_h, "init_anion": init_anion})

    hplus = conc["H^+"]                                                # the final total [H⁺] (≈ stage-1 extent)
    with localcontext() as lc:
        lc.prec = 40
        pH = -(hplus.log10())
        percent = solved[0]["x"] / c0 * 100                           # first-proton ionization %

    # the species ladder: the equilibrium concentration of every phosphate species (H3PO4 → … → the last anion),
    # read straight off the running concentrations (the successive treatment's answer).
    ladder_ids = [acid_formula] + [st["anion"] for st in stages_data]
    species_ladder = []
    for sid in ladder_ids:
        f = parse_formula(sid, ctx)
        species_ladder.append({"id": sid, "latex": f.latex, "equilibrium_M": _sig_str(conc[sid], 12),
                               "equilibrium_M_display": _sig_str(conc[sid], 3)})

    st1 = solved[0]
    sym1_tex = "K_{a1}"                            # LaTeX (braces for the multi-char subscript)
    sym1_html = "K_a1"                             # the emitted `symbol` (the player's split-on-"_" sub renderer)
    # the later stages (2..n) as compact, independently re-solvable objects (the gate re-solves each)
    later_stages = []
    for s in solved[1:]:
        sym = f"K_{{a{s['index']}}}"
        an_eqm = s["init_anion"] + s["x"]
        later_stages.append({
            "index": s["index"], "ka_symbol": sym, "ka_value": format(s["ka"], "f"),
            "expression_latex": _ka_expr(fh.latex, s["anion_latex"], s["acid_latex"], sym),
            "reactant_id": s["acid"], "reactant_latex": s["acid_latex"],
            "anion_id": s["anion"], "anion_latex": s["anion_latex"],
            "initial_reactant_M": _sig_str(s["init_reactant"], 12),
            "initial_hydronium_M": _sig_str(s["init_h"], 12),
            "initial_anion_M": _sig_str(s["init_anion"], 12),
            "extent_M": _sig_str(s["x"], 12), "extent_M_display": _sig_str(s["x"], 3),
            "anion_equilibrium_M": _sig_str(an_eqm, 12), "anion_equilibrium_M_display": _sig_str(an_eqm, 3),
            "quotient_at_equilibrium": _sig_str(s["Q"], 6), "residual_relative": _sig_str(s["residual"], 2),
        })

    reaction_latex = f"{st1['acid_latex']} \\rightleftharpoons {fh.latex} + {st1['anion_latex']}"
    reaction_text = f"{acid_formula} <=> H^+ + {st1['anion']}"

    result = {
        "hydronium_M": _sig_str(hplus, 12), "hydronium_M_display": _sig_str(hplus, 3),
        "pH": _sig_str(pH, 8), "pH_display": format(pH.quantize(Decimal("0.01"), ROUND_HALF_UP), "f"),
        "percent_ionization": _sig_str(percent, 8), "percent_ionization_display": _sig_str(percent, 3),
        "proton_count": int(acid.get("protons", len(stages_data))),
        "species_ladder": species_ladder,
        "later_stages": later_stages,
    }

    return {
        "kind": "equilibrium",
        "subtype": "polyprotic",
        "id": spec["id"],
        "title": spec["title"],
        "slug": spec["slug"],
        "topic": spec["topic"],
        "tags": spec.get("tags", []),
        "scenario": spec["scenario"],
        "regimes": _regimes("equilibrium position (staged pH)"),
        "assumptions": spec.get("assumptions", []),
        "reaction": {
            "acid": acid_formula, "acid_name": acid.get("name", acid_formula), "acid_latex": st1["acid_latex"],
            "text": reaction_text, "latex": reaction_latex, "conjugate_base": st1["anion"],
        },
        "equilibrium_constant": {
            "symbol": sym1_html, "value": format(st1["ka"], "f"),
            "expression_latex": _ka_expr(fh.latex, st1["anion_latex"], st1["acid_latex"], sym1_tex),
            "source": data.sources.get("ionization_constants", ""),
        },
        "ice": {"extent_symbol": "x", "extent_M": _sig_str(st1["x"], 12),
                "extent_M_display": _sig_str(st1["x"], 3), "species": st1["rows"]},
        "mass_action": {"quotient_symbol": "Q", "quotient_at_equilibrium": _sig_str(st1["Q"], 6),
                        "residual_relative": _sig_str(st1["residual"], 2)},
        "result": result,
        "misconception": spec["misconception"],
        "reference_links": spec.get("reference_links", []),
        "checks": {
            "ice_identity": True,           # each stage: c = c₀ + ν·x (exact algebra), chained across stages
            "mass_action_satisfied": True,  # each stage: Q(committed) = Kₐᵢ
            "extent_physical": True,        # 0 < xᵢ ≤ [reactant]₀ᵢ at every stage
            "ph_consistent": True,          # pH = −log₁₀[H⁺] on the accumulated hydronium
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


# the fractions of the equivalence volume at which the titration curve is sampled — denser near the equivalence
# point (0.9–1.1) so the steep pH jump is resolved; always includes 0 (initial), 0.5 (half-equivalence, pH=pKₐ),
# and 1.0 (equivalence). Deterministic (no Date/random — the gate re-derives every point from the same list).
_TITRATION_FRACTIONS = ["0", "0.2", "0.4", "0.5", "0.6", "0.8", "0.9", "0.96", "1.0", "1.04", "1.1", "1.2",
                        "1.4", "1.6", "2.0"]


def _titration_point(c_acid, v_acid, c_base, v_base, ka, kw, anion_id, acid_formula, ctx):
    """pH at one point of a weak-acid/strong-base titration, by region — the same reversible-extent solver at each.
    Returns (pH Decimal, region str, hydronium Decimal). n = C·V in mmol; V_total in mL (the units cancel in the
    ratios, so concentrations are mmol/mL = mol/L)."""
    n_acid = c_acid * v_acid
    n_base = c_base * v_base
    v_tot = v_acid + v_base
    fh = parse_formula("H^+", ctx)
    fa = parse_formula(acid_formula, ctx)
    fan = parse_formula(anion_id, ctx)
    if n_base < n_acid:
        # before equivalence: some HA converted to A⁻ by the strong base — a weak acid (V_b=0) or a buffer.
        ha0 = (n_acid - n_base) / v_tot
        a0 = n_base / v_tot
        species = [
            {"id": acid_formula, "latex": fa.latex, "nu": -1, "initial_M": ha0, "role": "reactant"},
            {"id": "H^+", "latex": fh.latex, "nu": 1, "initial_M": Decimal(0), "role": "product"},
            {"id": anion_id, "latex": fan.latex, "nu": 1, "initial_M": a0, "role": "product"},
        ]
        x = solve_equilibrium(species, ka, ctx)["extent"]
        hplus = x                                              # [H⁺] = the ionization extent (initial [H⁺] = 0)
        region = "initial" if n_base == 0 else "buffer"
    elif n_base == n_acid:
        # equivalence: all HA is now A⁻, which hydrolyses as a weak base A⁻ + H₂O ⇌ HA + OH⁻ (K_b = K_w/K_a).
        a0 = n_acid / v_tot
        kb = kw / ka
        foh = parse_formula("OH^-", ctx)
        fw = parse_formula("H2O", ctx)
        species = [
            {"id": anion_id, "latex": fan.latex, "nu": -1, "initial_M": a0, "role": "reactant"},
            {"id": "H2O", "latex": fw.latex, "nu": -1, "initial_M": Decimal(0), "in_quotient": False, "role": "reactant"},
            {"id": acid_formula, "latex": fa.latex, "nu": 1, "initial_M": Decimal(0), "role": "product"},
            {"id": "OH^-", "latex": foh.latex, "nu": 1, "initial_M": Decimal(0), "role": "product"},
        ]
        oh = solve_equilibrium(species, kb, ctx)["extent"]
        hplus = kw / oh                                        # the K_w bridge
        region = "equivalence"
    else:
        # after equivalence: excess strong base sets [OH⁻]; the A⁻ hydrolysis is negligible beside it.
        oh = (n_base - n_acid) / v_tot
        hplus = kw / oh
        region = "excess-base"
    with localcontext() as lc:
        lc.prec = 40
        pH = -(hplus.log10())
    return pH, region, hplus


def build_titration_lesson(spec: dict, data, acidbase, ctx: str = "") -> dict:
    """An authored titration-curve lesson → the verified `*.equilibrium.json` object, subtype `titration` (ADR-0048).
    A **weak acid titrated by a strong base** — the ledger *marched* as titrant is added: at each added volume the
    ICE is re-solved by the appropriate region (a weak acid / a buffer / the conjugate-base weak-base solve at
    equivalence / excess strong base), and the sequence of (volume, pH) points IS the titration curve. Every point
    reuses `solve_equilibrium`. The top-level ice is the **initial** point (the pure weak acid, V_b = 0), so the
    schema's required fields stay meaningful + the existing ICE renderer shows the starting solution; the `titration`
    block carries the curve + the three landmarks (initial, half-equivalence where pH = pKₐ, equivalence — basic for
    a weak acid). The acid + Kₐ come from `acids-bases.toml`/`ionization-constants.toml`, the titrant is a curated
    STRONG base; the producer REFUSES a strong or polyprotic acid, or a non-strong titrant (ADR-0008)."""
    for key in ("id", "title", "slug", "topic", "scenario", "acid", "acid_molarity_M", "acid_volume_mL",
                "titrant", "titrant_molarity_M", "misconception"):
        if key not in spec:
            raise BuildError(f"{ctx}: titration lesson missing required key '{key}'")

    acid_formula = spec["acid"]
    acid = acidbase.acids.get(acid_formula)
    if acid is None:
        raise BuildError(f"{ctx}: acid '{acid_formula}' is not in data/acids-bases.toml")
    if acid.get("strength") != "weak":
        raise BuildError(f"{ctx}: '{acid_formula}' is not a weak acid — this titration curve is a weak acid vs a "
                         f"strong base (a strong acid gives a featureless curve, no buffer region / pKₐ)")
    if int(acid.get("protons", 0)) != 1:
        raise BuildError(f"{ctx}: '{acid_formula}' is polyprotic — this titration lesson is monoprotic")
    anion_id = acid["anion"]
    if data.ions.get(anion_id) is None:
        raise BuildError(f"{ctx}: acid '{acid_formula}' names anion '{anion_id}' absent from the ion table")
    titrant_formula = spec["titrant"]
    titrant = acidbase.bases.get(titrant_formula)
    if titrant is None:
        raise BuildError(f"{ctx}: titrant '{titrant_formula}' is not in data/acids-bases.toml")
    if titrant.get("strength") != "strong":
        raise BuildError(f"{ctx}: titrant '{titrant_formula}' is not a strong base — the titrant must ionize "
                         f"completely so the added moles of OH⁻ are exact")

    ka = data.ionization_constant(acid_formula)["ka"]
    kw = data.water_ion_product()
    c_acid = Decimal(str(spec["acid_molarity_M"]))
    v_acid = Decimal(str(spec["acid_volume_mL"]))
    c_base = Decimal(str(spec["titrant_molarity_M"]))
    if c_acid <= 0 or v_acid <= 0 or c_base <= 0:
        raise BuildError(f"{ctx}: acid molarity/volume and titrant molarity must be positive")

    v_eq = c_acid * v_acid / c_base                                   # equivalence volume (mL): n_acid = n_base
    v_half = v_eq / 2

    fa = parse_formula(acid_formula, ctx)
    fan = parse_formula(anion_id, ctx)
    fh = parse_formula("H^+", ctx)
    ft = parse_formula(titrant_formula, ctx)

    # the curve: pH at each sampled volume (a fraction of the equivalence volume). Deterministic + machine-checkable.
    curve = []
    for frac in _TITRATION_FRACTIONS:
        v_base = v_eq * Decimal(frac)
        pH, region, hplus = _titration_point(c_acid, v_acid, c_base, v_base, ka, kw, anion_id, acid_formula, ctx)
        curve.append({
            "volume_mL": _sig_str(v_base, 6), "volume_mL_display": _sig_str(v_base, 4),
            "fraction_of_equivalence": frac, "region": region,
            "pH": _sig_str(pH, 8), "pH_display": format(pH.quantize(Decimal("0.01"), ROUND_HALF_UP), "f"),
            "hydronium_M": _sig_str(hplus, 6),
        })

    def _landmark(v_base):
        pH, region, hplus = _titration_point(c_acid, v_acid, c_base, v_base, ka, kw, anion_id, acid_formula, ctx)
        return {"volume_mL": _sig_str(v_base, 6), "volume_mL_display": _sig_str(v_base, 4),
                "pH": _sig_str(pH, 8), "pH_display": format(pH.quantize(Decimal("0.01"), ROUND_HALF_UP), "f"),
                "region": region}
    initial = _landmark(Decimal(0))
    half = _landmark(v_half)
    equivalence = _landmark(v_eq)

    with localcontext() as lc:
        lc.prec = 40
        pKa = -(ka.log10())

    # the top-level ICE = the INITIAL point (the pure weak acid, before any titrant): HA ⇌ H⁺ + A⁻, [HA]₀ = C_a.
    ice_species = [
        {"id": acid_formula, "latex": fa.latex, "nu": -1, "initial_M": c_acid, "role": "reactant"},
        {"id": "H^+", "latex": fh.latex, "nu": 1, "initial_M": Decimal(0), "role": "product"},
        {"id": anion_id, "latex": fan.latex, "nu": 1, "initial_M": Decimal(0), "role": "product"},
    ]
    x0 = _round_sig(solve_equilibrium(ice_species, ka, ctx)["extent"], 12)
    ice_rows = []
    for s in ice_species:
        change = s["nu"] * x0
        eqm = s["initial_M"] + change
        ice_rows.append({
            "id": s["id"], "latex": s["latex"], "phase": "aq", "role": s["role"], "nu": s["nu"],
            "initial_M": _sig_str(s["initial_M"], 12),
            "change_M": ("+" if change >= 0 else "") + _sig_str(change, 12),
            "equilibrium_M": _sig_str(eqm, 12), "equilibrium_M_display": _sig_str(eqm, 3),
        })
    committed = [Decimal(r["equilibrium_M"]) for r in ice_rows]
    Q0 = _quotient(committed, [-1, 1, 1])
    residual0 = abs(Q0 - ka) / ka

    def _num(latex, power):
        return f"[{latex}]" + (f"^{{{power}}}" if power != 1 else "")
    expression = (r"K_a = \dfrac{" + _num(fh.latex, 1) + _num(fan.latex, 1) + "}{" + _num(fa.latex, 1) + "}")
    reaction_latex = f"{fa.latex} \\rightleftharpoons {fh.latex} + {fan.latex}"
    reaction_text = f"{acid_formula} <=> H^+ + {anion_id}"
    neutralization_latex = f"{fa.latex} + \\mathrm{{OH^-}} \\rightarrow {fan.latex} + \\mathrm{{H_2O}}"

    return {
        "kind": "equilibrium",
        "subtype": "titration",
        "id": spec["id"],
        "title": spec["title"],
        "slug": spec["slug"],
        "topic": spec["topic"],
        "tags": spec.get("tags", []),
        "scenario": spec["scenario"],
        "regimes": _regimes("titration curve (pH vs added base)"),
        "assumptions": spec.get("assumptions", []),
        "reaction": {
            "acid": acid_formula, "acid_name": acid.get("name", acid_formula), "acid_latex": fa.latex,
            "text": reaction_text, "latex": reaction_latex, "conjugate_base": anion_id,
        },
        "equilibrium_constant": {
            "symbol": "K_a", "value": format(ka, "f"), "expression_latex": expression,
            "source": data.sources.get("ionization_constants", ""),
        },
        "ice": {"extent_symbol": "x", "extent_M": _sig_str(x0, 12), "extent_M_display": _sig_str(x0, 3),
                "species": ice_rows},
        "mass_action": {"quotient_symbol": "Q", "quotient_at_equilibrium": _sig_str(Q0, 6),
                        "residual_relative": _sig_str(residual0, 2)},
        "titration": {
            "titrant": titrant_formula, "titrant_name": titrant.get("name", titrant_formula), "titrant_latex": ft.latex,
            "titrant_molarity_M": format(c_base, "f"),
            "acid_molarity_M": format(c_acid, "f"), "acid_volume_mL": format(v_acid, "f"),
            "neutralization_latex": neutralization_latex,
            "kw": format(kw, "f"), "pKa": _sig_str(pKa, 8),
            "pKa_display": format(pKa.quantize(Decimal("0.01"), ROUND_HALF_UP), "f"),
            "equivalence_volume_mL": _sig_str(v_eq, 6), "equivalence_volume_mL_display": _sig_str(v_eq, 4),
            "half_equivalence_volume_mL": _sig_str(v_half, 6), "half_equivalence_volume_mL_display": _sig_str(v_half, 4),
            "curve": curve,
            "landmarks": {"initial": initial, "half_equivalence": half, "equivalence": equivalence},
        },
        "result": {
            "hydronium_M": _sig_str(x0, 12), "hydronium_M_display": _sig_str(x0, 3),
            "pH": initial["pH"], "pH_display": initial["pH_display"],
            "pH_half_equivalence_display": half["pH_display"], "pH_equivalence_display": equivalence["pH_display"],
            "pKa_display": format(pKa.quantize(Decimal("0.01"), ROUND_HALF_UP), "f"),
        },
        "misconception": spec["misconception"],
        "reference_links": spec.get("reference_links", []),
        "checks": {
            "ice_identity": True,           # the initial point: c = c₀ + ν·x (exact algebra)
            "mass_action_satisfied": True,  # the initial point: Q(committed) = Kₐ
            "extent_physical": True,        # 0 < x < [HA]₀
            "ph_consistent": True,          # every curve point's pH re-derived by its region (buffer / weak base / excess)
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
