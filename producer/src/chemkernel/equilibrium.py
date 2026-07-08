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
    `solubility` (ADR-0048, 2nd increment). The SAME reversible-extent solver as the weak acid, but the dissolving
    species is a **pure solid** — excluded from the mass-action quotient (activity 1), so Kₛₚ = [cation]^a[anion]^b
    and the extent x is the **molar solubility** s. For a 1:2 salt like CaF₂ that makes Kₛₚ = [Ca²⁺][F⁻]² = 4s³, a
    **cubic** — solved by bisection, the reason the solver is general (ADR-0048). The salt + its ions + Kₛₚ come
    from `data/solubility-products.toml` (the composition machine-checked on load, the Kₛₚ sourced); the producer
    REFUSES an unknown salt or one with no curated Kₛₚ (ADR-0008)."""
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

    # the ICE species: the pure SOLID (excluded from Q — the load-bearing idea) + the two dissolved ions
    ice_species = [
        {"id": salt_formula, "latex": fs.latex, "phase": "s", "role": "reactant", "nu": -1, "in_quotient": False,
         "initial_M": Decimal(0)},
        {"id": cation_id, "latex": fc.latex, "phase": "aq", "role": "product", "nu": n_cat, "initial_M": Decimal(0)},
        {"id": anion_id, "latex": fan.latex, "phase": "aq", "role": "product", "nu": n_an, "initial_M": Decimal(0)},
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

    # Ksp expression: [cation]^a [anion]^b (concentrations — no phase labels, the solid absent)
    def _br(latex, power):
        return f"[{latex}]" + (f"^{{{power}}}" if power != 1 else "")
    expression = "K_{sp} = " + _br(fc.latex, n_cat) + _br(fan.latex, n_an)
    reaction_latex = (f"{fs.latex}\\,\\text{{(s)}} \\rightleftharpoons "
                      f"{_coeff_latex(n_cat)}{fc.latex}\\,\\text{{(aq)}} + "
                      f"{_coeff_latex(n_an)}{fan.latex}\\,\\text{{(aq)}}")
    coeff = lambda n: "" if n == 1 else f"{n} "
    reaction_text = f"{salt_formula}(s) <=> {coeff(n_cat)}{cation_id}(aq) + {coeff(n_an)}{anion_id}(aq)"

    return {
        "kind": "equilibrium",
        "subtype": "solubility",
        "id": spec["id"],
        "title": spec["title"],
        "slug": spec["slug"],
        "topic": spec["topic"],
        "tags": spec.get("tags", []),
        "scenario": spec["scenario"],
        "regimes": _regimes("equilibrium position (solubility)"),
        "assumptions": spec.get("assumptions", []),
        "reaction": {
            "salt": salt_formula, "salt_name": rec["name"], "salt_latex": fs.latex,
            "text": reaction_text, "latex": reaction_latex, "cation": cation_id, "anion": anion_id,
        },
        "equilibrium_constant": {
            "symbol": "K_sp", "value": format(ksp, "f"), "expression_latex": expression,
            "source": data.sources.get("solubility_products", ""),
        },
        "ice": {"extent_symbol": "s", "extent_M": _sig_str(s, 12), "extent_M_display": _sig_str(s, 3),
                "species": ice_rows},
        "mass_action": {"quotient_symbol": "Q", "quotient_at_equilibrium": _sig_str(Q, 6),
                        "residual_relative": _sig_str(residual, 2)},
        "result": {
            "molar_solubility_M": _sig_str(s, 12), "molar_solubility_M_display": _sig_str(s, 3),
            "solubility_g_per_L": _sig_str(solubility_g_per_L, 6),
            "solubility_g_per_L_display": _sig_str(solubility_g_per_L, 3),
            "molar_mass_g_per_mol": format(molar_mass, "f"),
        },
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
