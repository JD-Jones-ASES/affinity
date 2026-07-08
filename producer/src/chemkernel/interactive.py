"""Interactive closed-form emission for the player's sliders (ADR-0011, ADR-0008).

ADR-0011 lets a control exist only when co-motion of quantities *is* the lesson — here, the limiting-reagent
switch. ADR-0008 forbids the player from computing chemistry at runtime: the browser may only evaluate
closed forms the producer emits and a Node gate re-proves against this engine (the sibling's emit/parity
pattern, ported chemistry-native).

So for a two-reactant precipitation, this module emits:
  - slider params (volume + concentration of each solution),
  - closed forms (JS-evaluable strings) for every number the player displays — moles of each reacting ion,
    the extent ξ = min(...), the precipitate mass, the leftovers, the spectator-ion amounts,
  - a deterministic grid of sample points whose expected values are computed by the REAL engine
    (`solve_extent`), several straddling the limiting-reagent switch, so `check-parity.mjs` proves the JS
    the browser runs reproduces the engine across the whole slider range.

Every multiplicity (ions per formula unit, net-ionic coefficients) is derived from the actual chemistry
(`dissociate`, `net_ionic`), never hard-coded. If the reaction is not the supported single-precipitate
double-displacement shape, this returns None and the lesson simply ships without an interactive block
(the schema makes it optional) — refuse to guess, don't fabricate a closed form.
"""

from __future__ import annotations

import re
from decimal import Decimal, localcontext
from fractions import Fraction

from . import BuildError
from .extent import solve_extent
from .formula import parse_formula
from .reaction import dissociate

_PHASE_SUFFIX = re.compile(r"\((?:s|l|g|aq)\)$")


def _core(species_id: str) -> str:
    return _PHASE_SUFFIX.sub("", species_id)


def _sdec(x) -> str:
    """Decimal string for a Fraction/Decimal — exact if terminating, else a 30-digit context approximation.
    Used only for parity SAMPLE expectations (compared within tolerance), never for the exact stored answers."""
    f = x if isinstance(x, Fraction) else Fraction(x)
    with localcontext() as c:
        c.prec = 30
        d = Decimal(f.numerator) / Decimal(f.denominator)
    return format(d, "f")


def _lin(coeff: int, v: str, c: str) -> str:
    base = f"{v}/1000*{c}"
    return base if coeff == 1 else f"{coeff}*({base})"


def _over(expr: str, a: int) -> str:
    return expr if a == 1 else f"({expr})/{a}"


def _times(coeff: int, expr: str) -> str:
    return expr if coeff == 1 else f"{coeff}*{expr}"


# deterministic sample grid: (v1, c1, v2, c2) as decimal strings. Chosen to straddle the switch — some keep
# the cation limiting, some flip to the anion, some tie. Byte-stable (no randomness), spans the slider box.
_SAMPLES = [
    ("25.0", "0.100", "20.0", "0.150"),   # defaults — cation (Ca) limits
    ("25.0", "0.150", "20.0", "0.150"),   # richer cation solution — anion limits
    ("25.0", "0.120", "20.0", "0.150"),   # tuned to a tie
    ("50.0", "0.100", "20.0", "0.150"),   # more cation volume — anion limits
    ("10.0", "0.100", "20.0", "0.150"),   # less cation volume — cation limits harder
    ("25.0", "0.100", "40.0", "0.150"),   # more anion volume — cation limits
    ("25.0", "0.100", "10.0", "0.150"),   # less anion volume — anion limits
    ("30.0", "0.200", "30.0", "0.100"),   # anion limits
    ("20.0", "0.050", "20.0", "0.150"),   # cation limits
    ("40.0", "0.075", "15.0", "0.200"),   # tie
]


def build_interactive(reactants, products, coeffs, given, data, net_left, net_right, ctx=""):
    """Return the interactive block for a two-reactant single-precipitate reaction, or None if unsupported."""
    if len(reactants) != 2:
        return None

    # the two reacting ions from the net ionic (one cation, one anion)
    react_ions = list(net_left.keys())
    if len(react_ions) != 2:
        return None
    charge_of = {key: parse_formula(key[0]).charge for key in react_ions}
    cats = [k for k in react_ions if charge_of[k] > 0]
    ans = [k for k in react_ions if charge_of[k] < 0]
    if len(cats) != 1 or len(ans) != 1:
        return None
    cation_key, anion_key = cats[0], ans[0]
    a_cat, a_an = net_left[cation_key], net_left[anion_key]
    cation_id, anion_id = cation_key[0], anion_key[0]

    # the single net-ionic product and its coefficient — a solid precipitate (precipitation) or water for an
    # acid-base neutralization (ADR-0037). The limiting-reagent switch is the same instrument either way; the
    # only difference is the product's phase and identity, both derived from the net ionic, not assumed.
    net_products = list(net_right.items())
    if len(net_products) != 1:
        return None
    precip_key, p = net_products[0]
    precip_id = precip_key[0]
    product_phase = precip_key[1] or "s"

    # dissociate each reactant; find which supplies the cation, which the anion, plus each one's spectator.
    # (Formula is unhashable — it carries a counts dict — so keep a list of (Formula, ions), not a dict.)
    diss = []
    for f in reactants:
        try:
            diss.append((f, dict(dissociate(f, data, ctx))))
        except BuildError:
            return None
    react_cat = next((f for f, ions in diss if cation_id in ions), None)
    react_an = next((f for f, ions in diss if anion_id in ions), None)
    if react_cat is None or react_an is None or react_cat is react_an:
        return None
    ions_cat = next(ions for f, ions in diss if f is react_cat)
    ions_an = next(ions for f, ions in diss if f is react_an)
    k_cat = ions_cat[cation_id]
    k_an = ions_an[anion_id]
    spec_cat = [(i, n) for i, n in ions_cat.items() if i != cation_id]
    spec_an = [(i, n) for i, n in ions_an.items() if i != anion_id]
    if len(spec_cat) != 1 or len(spec_an) != 1:
        return None
    spec_cat_id, s_cat = spec_cat[0]
    spec_an_id, s_an = spec_an[0]

    # map each reactant to its given (volume, molarity); both must be volumetric
    by_species = {g["species"]: g for g in given if "volume_mL" in g and "molarity_M" in g}
    g_cat = by_species.get(react_cat.raw)
    g_an = by_species.get(react_an.raw)
    if g_cat is None or g_an is None:
        return None

    molar_mass = str(data.molar_mass(precip_id))

    # closed forms — v1/c1 drive the cation solution, v2/c2 the anion solution
    n_cation = _lin(k_cat, "v1", "c1")
    n_anion = _lin(k_an, "v2", "c2")
    xi = f"Math.min({_over(n_cation, a_cat)}, {_over(n_anion, a_an)})"
    moles_precip = _times(p, f"({xi})")
    closed_form = {
        "n_cation": n_cation,
        "n_anion": n_anion,
        "xi": xi,
        "mass": f"{moles_precip}*{molar_mass}",
        "leftover_cation": f"({n_cation}) - {_times(a_cat, f'({xi})')}",
        "leftover_anion": f"({n_anion}) - {_times(a_an, f'({xi})')}",
        "n_spec_cation": _lin(s_cat, "v1", "c1"),
        "n_spec_anion": _lin(s_an, "v2", "c2"),
    }

    # sample points, expectations computed by the REAL engine (solve_extent), straddling the switch
    cation_f = parse_formula(cation_id)
    anion_f = parse_formula(anion_id)
    precip_f = parse_formula(precip_id)
    samples = []
    for v1, c1, v2, c2 in _SAMPLES:
        n_r_cat = Fraction(Decimal(v1)) / 1000 * Fraction(Decimal(c1))
        n_r_an = Fraction(Decimal(v2)) / 1000 * Fraction(Decimal(c2))
        n_cat = k_cat * n_r_cat
        n_an = k_an * n_r_an
        ledger = solve_extent([(cation_f, n_cat), (anion_f, n_an)], [(precip_f, 0)],
                              [a_cat, a_an, p], ctx)
        finals = {r.species: r.final_mol for r in ledger.rows}
        mass = finals[precip_f.raw] * Fraction(Decimal(molar_mass))
        samples.append({
            "args": {"v1": v1, "c1": c1, "v2": v2, "c2": c2},
            "expect": {
                "n_cation": _sdec(n_cat),
                "n_anion": _sdec(n_an),
                "xi": _sdec(ledger.extent_mol),
                "mass": _sdec(mass),
                "leftover_cation": _sdec(finals[cation_f.raw]),
                "leftover_anion": _sdec(finals[anion_f.raw]),
                "n_spec_cation": _sdec(s_cat * n_r_cat),
                "n_spec_anion": _sdec(s_an * n_r_an),
            },
        })

    params = [
        {"name": "v1", "label": f"V({_core(react_cat.raw)})", "species": _core(react_cat.raw),
         "kind": "volume", "unit": "mL", "min": "5", "max": "50", "default": g_cat["volume_mL"], "step": "0.5"},
        {"name": "c1", "label": f"[{_core(react_cat.raw)}]", "species": _core(react_cat.raw),
         "kind": "concentration", "unit": "M", "min": "0.02", "max": "0.30", "default": g_cat["molarity_M"], "step": "0.005"},
        {"name": "v2", "label": f"V({_core(react_an.raw)})", "species": _core(react_an.raw),
         "kind": "volume", "unit": "mL", "min": "5", "max": "50", "default": g_an["volume_mL"], "step": "0.5"},
        {"name": "c2", "label": f"[{_core(react_an.raw)}]", "species": _core(react_an.raw),
         "kind": "concentration", "unit": "M", "min": "0.02", "max": "0.30", "default": g_an["molarity_M"], "step": "0.005"},
    ]

    return {
        "params": params,
        "closed_form_params": ["v1", "c1", "v2", "c2"],
        "closed_form": closed_form,
        "cation": {"id": cation_id, "source": _core(react_cat.raw), "per": k_cat, "net_coeff": a_cat},
        "anion": {"id": anion_id, "source": _core(react_an.raw), "per": k_an, "net_coeff": a_an},
        "product": {"id": precip_id, "molar_mass": molar_mass, "phase": product_phase, "net_coeff": p},
        "spectators": [
            {"id": spec_cat_id, "source": _core(react_cat.raw), "per": s_cat, "key": "n_spec_cation"},
            {"id": spec_an_id, "source": _core(react_an.raw), "per": s_an, "key": "n_spec_anion"},
        ],
        "leftover_keys": {"cation": "leftover_cation", "anion": "leftover_anion"},
        "samples": samples,
    }
