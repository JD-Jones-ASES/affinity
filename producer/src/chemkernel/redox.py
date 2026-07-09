r"""Electrochemistry — the electron ledger (ADR-0050), the last Phase-2 tier.

The thesis (AGENTS.md, brief §): chemistry is species accounting plus electron structure under energy constraints.
Electrochemistry is that ledger with **electrons** as the tracked quantity: *electron bookkeeping plus free energy
per charge*. A redox reaction moves electrons from the species **oxidized** (its oxidation number rises — it loses
electrons, at the anode) to the species **reduced** (its oxidation number falls — it gains electrons, at the
cathode). The reaction extent ξ is now measured in **moles of electrons transferred**, n.

Two engines here:
  1. `oxidation_states` — assigns each atom its oxidation number by the standard first-course rule hierarchy (a
     free element is 0; a monatomic ion is its charge; F −1, group-1 +1, group-2 +2, H +1, O −2, then the one
     remaining element is solved so the numbers **sum to the species charge**). This *completes* the free-element
     redox flag of ADR-0035 (which detected redox without assigning numbers). The rules are the sourced convention
     (regime-3); the sum-to-charge accounting is exact (regime-1) and machine-checked. It REFUSES a formula it
     cannot resolve to one unknown (honest, over guessing).
  2. `build_electrochemistry_lesson` — a **galvanic cell** from two sourced metal-ion/metal couples: it assigns
     the roles (the higher standard reduction potential is the cathode), writes the two half-reactions, balances
     the **electron ledger** (n = lcm of the two electron counts, the half-reactions scaled so electrons cancel),
     reads the cell potential $E^\circ_\text{cell} = E^\circ_\text{cathode} - E^\circ_\text{anode}$ off the sourced
     table, and computes the free energy $\Delta G^\circ = -nFE^\circ$ (F sourced, exact). Honesty is layered: the
     electron ledger + the overall balance are machine-checked (regime-1); $E^\circ$ is sourced (regime-3); the
     cell model (standard conditions, activities = 1) is disclosed (regime-2), and $\Delta G^\circ$ is
     model-exact-then-rounded."""

from __future__ import annotations

import platform
from decimal import ROUND_HALF_UP, Decimal, localcontext
from fractions import Fraction
from math import gcd

from . import BuildError, __version__
from .formula import parse_formula

_PREC = 40


def _round_sig(d: Decimal, n: int) -> Decimal:
    if d == 0:
        return Decimal(0)
    return d.quantize(Decimal(1).scaleb(d.adjusted() - (n - 1)), rounding=ROUND_HALF_UP)


def _sig(d: Decimal, n: int) -> str:
    s = format(_round_sig(d, n), "f")
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s or "0"


def _ox_display(v) -> str:
    """A signed oxidation-number label: 0 → '0', +2 → '+2', −2 → '−2' (Unicode minus)."""
    if v == 0:
        return "0"
    n = v if isinstance(v, int) else (int(v) if v.denominator == 1 else v)
    body = f"{abs(n)}" if isinstance(n, int) else f"{abs(n.numerator)}/{n.denominator}"
    return ("+" if n > 0 else "−") + body


def _rule_ox(sym: str, data) -> int | None:
    """The fixed oxidation-number rule for an element in a compound (None → solve by the sum constraint)."""
    if sym == "F":
        return -1
    if sym == "H":
        return 1
    if sym == "O":
        return -2
    el = data.elements.get(sym)
    if el is not None and getattr(el, "group", None) == 1 and sym != "H":
        return 1                                            # alkali metals
    if el is not None and getattr(el, "group", None) == 2:
        return 2                                            # alkaline-earth metals
    if sym in ("Cl", "Br", "I"):
        return -1                                           # halogens (first-course default: not bonded to O/F)
    return None


def oxidation_states(formula: str, data, ctx: str = "") -> dict:
    """Assign each element in `formula` its oxidation number (int or Fraction), machine-checked to sum to the
    species charge. Refuses a formula with more than one rule-unknown element (ambiguous for a first course)."""
    f = parse_formula(formula, ctx)
    counts, charge = f.counts, f.charge
    els = list(counts)
    if len(els) == 1 and charge == 0:
        return {els[0]: 0}                                  # a free element is 0 by definition
    if len(els) == 1 and counts[els[0]] == 1:
        return {els[0]: charge}                             # a monatomic ion is its charge

    known: dict = {}
    known_sum = 0
    unknowns: list[str] = []
    for sym, n in counts.items():
        ox = _rule_ox(sym, data)
        if ox is None:
            unknowns.append(sym)
        else:
            known[sym] = ox
            known_sum += ox * n
    if len(unknowns) == 1:
        u = unknowns[0]
        val = Fraction(charge - known_sum, counts[u])
        known[u] = int(val) if val.denominator == 1 else val
    elif len(unknowns) == 0:
        if known_sum != charge:
            raise BuildError(f"{ctx}: oxidation-number rules for {formula} sum to {known_sum}, not the "
                             f"species charge {charge} — the fixed rules conflict here")
    else:
        raise BuildError(f"{ctx}: cannot assign oxidation numbers for {formula} — {len(unknowns)} elements "
                         f"{unknowns} have no first-course rule (needs more than the standard hierarchy)")
    # machine-check (regime-1): the assigned numbers, weighted by count, sum to the charge
    total = sum((v if isinstance(v, int) else v) * counts[s] for s, v in known.items())
    if total != charge:
        raise BuildError(f"{ctx}: oxidation numbers for {formula} sum to {total}, not the charge {charge}")
    return known


def _species_ox(formula: str, data, ctx: str) -> dict:
    """The oxidation-number record for one species: its formula, latex, and per-element numbers (for display)."""
    f = parse_formula(formula, ctx)
    ox = oxidation_states(formula, data, ctx)
    return {"formula": formula, "latex": f.latex,
            "atoms": [{"element": el, "ox_number": str(ox[el]), "ox_display": _ox_display(ox[el])}
                      for el in f.counts]}


def _half_reaction_latex(ion_latex: str, metal_latex: str, electrons: int, reduction: bool) -> str:
    """Render a metal-ion/metal half-reaction. reduction: Mⁿ⁺ + n e⁻ → M; oxidation: M → Mⁿ⁺ + n e⁻."""
    e = f"{electrons}\\,\\mathrm{{e^-}}" if electrons != 1 else "\\mathrm{e^-}"
    if reduction:
        return f"{ion_latex} + {e} \\rightarrow {metal_latex}"
    return f"{metal_latex} \\rightarrow {ion_latex} + {e}"


def _regimes() -> list[dict]:
    return [
        {"facet": "electron ledger + oxidation-number accounting", "regime": "ledger-exact"},
        {"facet": "standard reduction potentials E°", "regime": "rule-sourced"},
        {"facet": "cell potential + free energy (standard-state model)", "regime": "model-exact"},
    ]


def build_electrochemistry_lesson(spec: dict, data, ctx: str = "") -> dict:
    """An authored galvanic-cell lesson → the verified `*.electrochemistry.json` object (ADR-0050). The spec names
    two metal-ion/metal `couples` (by ion formula, sourced in data/reduction-potentials.toml); the producer assigns
    the cathode (higher E°) and anode (lower E°), writes the half-reactions, balances the electron ledger, and
    computes E°cell + ΔG° = −nFE°. REFUSES equal potentials (no cell), an unknown couple, or a non-balancing
    overall reaction."""
    for key in ("id", "title", "slug", "topic", "scenario", "couples", "misconception"):
        if key not in spec:
            raise BuildError(f"{ctx}: electrochemistry lesson missing required key '{key}'")
    couples = spec["couples"]
    if not isinstance(couples, list) or len(couples) != 2:
        raise BuildError(f"{ctx}: `couples` must be a 2-list of ion formulas (got {couples})")

    recs = [data.reduction_potential(ion) for ion in couples]     # raises if a couple is absent (sourced)
    e0 = [r["e_standard"] for r in recs]
    if e0[0] == e0[1]:
        raise BuildError(f"{ctx}: the two couples have equal E° — no galvanic cell (no driving force)")
    # the cathode is the couple with the HIGHER standard reduction potential (it is reduced); the other is the anode
    ci, ai = (0, 1) if e0[0] > e0[1] else (1, 0)
    cat, an = recs[ci], recs[ai]                                  # cathode / anode couple records

    e_cathode, e_anode = cat["e_standard"], an["e_standard"]
    n = cat["electrons"] * an["electrons"] // gcd(cat["electrons"], an["electrons"])   # electrons transferred
    ka, kc = n // an["electrons"], n // cat["electrons"]          # half-reaction multipliers (anode / cathode)

    an_ion, an_metal = parse_formula(an["oxidized"], ctx), parse_formula(an["reduced"], ctx)
    cat_ion, cat_metal = parse_formula(cat["oxidized"], ctx), parse_formula(cat["reduced"], ctx)

    # the overall cell reaction: (ka)·anode metal + (kc)·cathode ion → (ka)·anode ion + (kc)·cathode metal
    lhs_terms = [(ka, an_metal), (kc, cat_ion)]                   # (coefficient, parsed Formula)
    rhs_terms = [(ka, an_ion), (kc, cat_metal)]

    def _side_text(terms):
        return " + ".join((f"{c} " if c != 1 else "") + f.raw for c, f in terms)

    def _side_latex(terms):
        return " + ".join((f"{c}\\," if c != 1 else "") + f.latex for c, f in terms)

    equation_text = f"{_side_text(lhs_terms)} -> {_side_text(rhs_terms)}"
    equation_latex = f"{_side_latex(lhs_terms)} \\rightarrow {_side_latex(rhs_terms)}"

    # machine-check the overall reaction balances (atoms + charge) — the electron ledger closed
    def _tally(terms):
        atoms: dict = {}
        charge = 0
        for coeff, f in terms:
            for el, c in f.counts.items():
                atoms[el] = atoms.get(el, 0) + coeff * c
            charge += coeff * f.charge
        return atoms, charge
    latoms, lcharge = _tally(lhs_terms)
    ratoms, rcharge = _tally(rhs_terms)
    if latoms != ratoms or lcharge != rcharge:
        raise BuildError(f"{ctx}: overall cell reaction does not balance ({latoms} q{lcharge} vs {ratoms} q{rcharge})")

    with localcontext() as lc:
        lc.prec = _PREC
        e_cell = e_cathode - e_anode                             # E°cell = E°cathode − E°anode
        # ΔG° = −nFE°  (J/mol → kJ/mol); F exact, E° sourced → model-exact-then-rounded
        delta_g_J = -Decimal(n) * data.faraday * e_cell
        delta_g_kJ = delta_g_J / 1000
    if e_cell <= 0:
        raise BuildError(f"{ctx}: computed E°cell = {e_cell} V ≤ 0 — not a spontaneous galvanic cell")

    # oxidation numbers for every species in the overall reaction (the anode metal 0 → +q, the cathode ion +q → 0)
    ox_species = [_species_ox(an_metal.raw, data, ctx), _species_ox(cat_ion.raw, data, ctx),
                  _species_ox(an_ion.raw, data, ctx), _species_ox(cat_metal.raw, data, ctx)]

    anode_el = next(iter(an_metal.counts))
    cathode_el = next(iter(cat_ion.counts))
    notation = (f"{an_metal.raw}(s) | {an_ion.raw}(aq) || {cat_ion.raw}(aq) | {cat_metal.raw}(s)")
    notation_latex = (f"{an_metal.latex}(s)\\;\\vert\\;{an_ion.latex}(aq)\\;\\Vert\\;"
                      f"{cat_ion.latex}(aq)\\;\\vert\\;{cat_metal.latex}(s)")

    return {
        "kind": "electrochemistry",
        "subtype": "galvanic",
        "id": spec["id"], "title": spec["title"], "slug": spec["slug"], "topic": spec["topic"],
        "tags": spec.get("tags", []),
        "scenario": spec["scenario"],
        "regimes": _regimes(),
        "assumptions": spec.get("assumptions", []),
        "reaction": {"equation_text": equation_text, "equation_latex": equation_latex,
                     "electrons_transferred": n},
        "oxidation_states": {"species": ox_species,
                             "oxidized": {"element": anode_el, "from": _ox_display(0),
                                          "to": _ox_display(an_ion.charge)},
                             "reduced": {"element": cathode_el, "from": _ox_display(cat_ion.charge),
                                         "to": _ox_display(0)}},
        "half_reactions": {
            "oxidation": {
                "role": "anode", "couple_name": an["name"],
                "equation_latex": _half_reaction_latex(an_ion.latex, an_metal.latex, an["electrons"], reduction=False),
                "electrons": an["electrons"], "multiplier": ka,
                "e_standard_V": format(e_anode, "f"), "e_standard_display": _sig(e_anode, 4),
                "element": anode_el, "ox_from": _ox_display(0), "ox_to": _ox_display(an_ion.charge)},
            "reduction": {
                "role": "cathode", "couple_name": cat["name"],
                "equation_latex": _half_reaction_latex(cat_ion.latex, cat_metal.latex, cat["electrons"], reduction=True),
                "electrons": cat["electrons"], "multiplier": kc,
                "e_standard_V": format(e_cathode, "f"), "e_standard_display": _sig(e_cathode, 4),
                "element": cathode_el, "ox_from": _ox_display(cat_ion.charge), "ox_to": _ox_display(0)},
        },
        "electron_ledger": {"n": n, "balanced": True,
                            "note": (f"{ka}×({an['electrons']} e⁻) lost = {kc}×({cat['electrons']} e⁻) gained "
                                     f"= {n} e⁻ transferred")},
        "cell": {
            "anode_ion": an_ion.raw, "anode_metal": an_metal.raw, "anode_name": an["name"],
            "cathode_ion": cat_ion.raw, "cathode_metal": cat_metal.raw, "cathode_name": cat["name"],
            "notation_text": notation, "notation_latex": notation_latex,
            "e_cell_V": format(e_cell, "f"), "e_cell_display": _sig(e_cell, 4),
            "spontaneous": True},
        "result": {
            "e_cell_display": _sig(e_cell, 4), "e_cell_V": format(e_cell, "f"),
            "n_electrons": n,
            "delta_g_kJ_per_mol": format(delta_g_kJ, "f"), "delta_g_display": _sig(delta_g_kJ, 3),
            "faraday": format(data.faraday, "f"),
            "spontaneous": True},
        "misconception": spec["misconception"],
        "reference_links": spec.get("reference_links", []),
        # the machine-checked facts, SHOWN not asserted (the gate re-derives all five, ADR-0008).
        "checks": {
            "oxidation_states_sum": True,      # each species' oxidation numbers sum to its charge
            "half_reactions_balanced": True,   # each half-reaction conserves atoms + charge (incl. electrons)
            "electrons_cancel": True,          # n electrons lost at the anode = n gained at the cathode
            "cell_potential": True,            # E°cell = E°cathode − E°anode, and > 0 (spontaneous)
            "delta_g_relation": True,          # ΔG° = −nFE°
        },
        "provenance": {
            "producer": "chemkernel", "version": __version__, "python": platform.python_version(),
            "author": spec.get("author", "Affinity"), "created": spec.get("created", ""),
            "sources": {
                "reduction_potentials": data.sources.get("reduction_potentials", ""),
                "constants": data.sources.get("constants", ""),
                "atomic_weight": data.sources.get("atomic_weight", ""),
            },
        },
    }
