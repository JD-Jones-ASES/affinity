"""Practice generator: solver-verified variants with misconception distractors (brief §6.8, ADR-0011).

The `precipitation_limiting_reagent_v1` family generates limiting-reagent questions off the same reaction the
lesson teaches. Generation is **deterministic** (seeded, ADR-0008 / architecture practice-generation policy):
the same spec seed always yields byte-identical questions, so committed `derived/` stays reviewable. Every
answer is computed from the reaction model (the same multiplicities the interactive block derives from the
real chemistry) — never hand-authored. Response mode follows ADR-0032: the **numeric** questions (mass,
leftover) are **free entry** — the learner types the number, and the named mistakes become a `diagnostics`
catalogue that names what they entered, never a menu whose wrong values (a `0 mmol` leftover, a plausible-but-
excess mass) could be eliminated or guessed; the **categorical** question (which reagent limits) stays a
multiple-choice menu, since both reagents are plausible. A **reject-list** still drops ambiguous variants:
near-ties (no clear limiting reagent) and no-leftover cases.

The emitted questions carry `args` (v1,c1,v2,c2) so `check-parity.mjs` re-derives every answer in pure Node
from the parity-verified closed forms — the practice answers are verified twice, like everything else.
"""

from __future__ import annotations

import random
from decimal import ROUND_HALF_UP, Decimal, localcontext
from fractions import Fraction

from .extent import to_decimal

# nice discrete grids — volumes are multiples of 5 mL, concentrations multiples of 0.05 M, so moles are clean
_VOLS = [Decimal(v) for v in ("10.0", "15.0", "20.0", "25.0", "30.0", "35.0", "40.0", "45.0", "50.0")]
_CONCS = [Decimal(c) for c in ("0.050", "0.100", "0.150", "0.200", "0.250")]
_KINDS = ["limiting", "mass", "leftover"]
_MIN_RATIO = Fraction(23, 20)   # capacities must differ by ≥ 15% — a clear (unambiguous) limiting reagent


def _mmol(frac: Fraction) -> str:
    """Amount in mmol as a trimmed decimal string."""
    d = to_decimal(frac * 1000, 4).normalize()
    s = format(d, "f")
    return s


def _grams(frac: Fraction) -> str:
    return format(to_decimal(frac, 3), "f")


def _exact_grams(frac: Fraction) -> str:
    """A weighed mass at FULL (terminating) precision, trailing zeros trimmed — so a gate re-deriving moles from
    the displayed mass gets the exact amount back (ADR-0043 energy practice varies BOTH reactant masses, so a
    3-decimal rounding would compound past the leftover tolerance; the gas practice rounds only the metal since
    its acid is an exact volume×molarity)."""
    s = format(to_decimal(frac, 8), "f")
    return s.rstrip("0").rstrip(".") if "." in s else s


def _rel_close(a: float, b: float, tol: float) -> bool:
    return abs(a - b) <= tol * max(abs(b), 1e-9) + 1e-12


def _practice_diagnostics(answer_disp: str, unit: str, wrongs: list[tuple[str, str]]) -> list[dict]:
    """Free-entry diagnostics for a numeric practice answer (ADR-0032). A numeric answer is not a menu — a
    plausible wrong mass or a `0 mmol` leftover is still eliminable/guessable — so the learner types the number
    and these named-mistake VALUES diagnose what they entered. Drops any candidate within 3.5% of the answer
    (so a correct entry is never mis-flagged) and any duplicate display."""
    ans = float(answer_disp)
    diags, seen = [], set()
    for disp, why in wrongs:
        try:
            fval = float(disp)
        except ValueError:
            continue
        if fval != fval or _rel_close(fval, ans, 0.035):
            continue
        if disp in seen:
            continue
        seen.add(disp)
        diags.append({"value": disp, "unit": unit, "misconception": why})
    return diags


def generate_practice(interactive: dict, seed: int, count: int, ctx: str = "",
                      family: str = "precipitation_limiting_reagent_v1",
                      product_noun: str = "precipitate") -> dict | None:
    """Build the practice block from an emitted `interactive` block (its multiplicities are engine-derived).
    `family` labels the set — precipitation, or acid-base neutralization (ADR-0037); the machinery is identical
    (the limiting-reagent switch off the reaction's own multiplicities). `product_noun` names the product in the
    mass prompt ("precipitate" for a solid, "" for water)."""
    cat, an, prod = interactive["cation"], interactive["anion"], interactive["product"]
    k_cat, a_cat, src_cat = cat["per"], cat["net_coeff"], cat["source"]
    k_an, a_an, src_an = an["per"], an["net_coeff"], an["source"]
    p, molar_mass = prod["net_coeff"], Fraction(Decimal(prod["molar_mass"]))

    rng = random.Random(seed)
    questions: list[dict] = []
    seen: set[tuple] = set()
    attempts = 0
    while len(questions) < count and attempts < 4000:
        attempts += 1
        v1, c1, v2, c2 = rng.choice(_VOLS), rng.choice(_CONCS), rng.choice(_VOLS), rng.choice(_CONCS)
        key = (v1, c1, v2, c2)
        if key in seen:
            continue

        n_cat = k_cat * (Fraction(v1) / 1000 * Fraction(c1))
        n_an = k_an * (Fraction(v2) / 1000 * Fraction(c2))
        cap_cat, cap_an = n_cat / a_cat, n_an / a_an

        # reject ambiguous variants: near-tie (no clear limiting reagent) → skip
        hi, lo = max(cap_cat, cap_an), min(cap_cat, cap_an)
        if lo == 0 or hi / lo < _MIN_RATIO:
            continue

        cat_limits = cap_cat < cap_an
        xi = lo
        mass = p * xi * molar_mass
        left_cat = n_cat - a_cat * xi
        left_an = n_an - a_an * xi
        excess_src = src_an if cat_limits else src_cat
        excess_left = left_an if cat_limits else left_cat

        kind = _KINDS[len(questions) % len(_KINDS)]
        given = [
            {"species": src_cat, "volume_mL": format(v1, "f"), "molarity_M": format(c1, "f")},
            {"species": src_an, "volume_mL": format(v2, "f"), "molarity_M": format(c2, "f")},
        ]
        args = {"v1": format(v1, "f"), "c1": format(c1, "f"), "v2": format(v2, "f"), "c2": format(c2, "f")}
        stem = (f"{format(v1, 'f')} mL of {format(c1, 'f')} M {src_cat} is mixed with "
                f"{format(v2, 'f')} mL of {format(c2, 'f')} M {src_an}.")
        limiting_src = src_cat if cat_limits else src_an

        if kind == "limiting":
            q = {
                "id": f"q{len(questions) + 1}", "kind": "limiting", "mode": "choice",  # categorical (ADR-0032)
                "prompt": f"{stem} Which reactant is the limiting reagent?",
                "given": given, "args": args,
                "answer": {"display": limiting_src, "value": limiting_src},
                "choices": [
                    {"display": src_cat, "correct": cat_limits,
                     "misconception": None if cat_limits else _vol_misconception(v1, v2, src_cat)},
                    {"display": src_an, "correct": not cat_limits,
                     "misconception": None if not cat_limits else _vol_misconception(v2, v1, src_an)},
                    {"display": "Neither — both are fully consumed", "correct": False,
                     "misconception": "A limiting reagent runs out first; here one reactant is left over, so they are not both fully consumed."},
                ],
                "explain": (f"Each reactant's capacity is its reacting-ion moles ÷ its net-ionic coefficient: "
                            f"{src_cat} = {_mmol(n_cat)} ÷ {a_cat} = {_mmol(cap_cat)} mmol, "
                            f"{src_an} = {_mmol(n_an)} ÷ {a_an} = {_mmol(cap_an)} mmol. "
                            f"{limiting_src} is smaller, so it limits."
                            + ("" if a_cat == a_an else " Fewer moles doesn't always mean limiting — the coefficient decides.")),
            }
        elif kind == "mass":
            m_correct = mass
            m_excess = p * hi * molar_mass                    # used the reactant in excess as if it were limiting
            m_sum = p * (cap_cat + cap_an) * molar_mass        # ignored the limiting reagent — added both
            q = {
                "id": f"q{len(questions) + 1}", "kind": "mass", "mode": "numeric",  # free entry (ADR-0032)
                "prompt": f"{stem} What mass of {prod['id']}{' ' + product_noun if product_noun else ''} forms?",
                "given": given, "args": args,
                "answer": {"display": f"{_grams(m_correct)} g", "value": format(to_decimal(m_correct, 3), 'f'), "unit": "g"},
                "diagnostics": _practice_diagnostics(_grams(m_correct), "g", [
                    (_grams(m_excess), f"Used {excess_src}, the reactant in excess, as if it were limiting — the product is capped by the limiting reagent."),
                    (_grams(m_sum), "Added the product each reactant could make separately — but they make the same product, capped by whichever runs out first."),
                ]),
                "explain": (f"ξ = {_mmol(xi)} mmol (set by {limiting_src}); "
                            f"mass = {p} × {_mmol(xi)} mmol × {prod['molar_mass']} g/mol = {_grams(m_correct)} g."),
            }
        else:  # leftover
            full_excess = n_an if cat_limits else n_cat
            q = {
                "id": f"q{len(questions) + 1}", "kind": "leftover", "mode": "numeric",  # free entry (ADR-0032)
                "prompt": f"{stem} After the reaction, how many mmol of the excess reactant remain?",
                "given": given, "args": args,
                "answer": {"display": f"{_mmol(excess_left)} mmol", "value": _mmol(excess_left), "unit": "mmol"},
                "diagnostics": _practice_diagnostics(_mmol(excess_left), "mmol", [
                    (_mmol(full_excess), f"That is all the {excess_src} you started with — some of it reacts; only the surplus over the limiting reagent remains."),
                    ("0", "Only the limiting reagent reaches 0; the reactant in excess leaves a leftover."),
                ]),
                "explain": (f"{excess_src} started at {_mmol(full_excess)} mmol and "
                            f"{_mmol(full_excess - excess_left)} mmol reacted, leaving {_mmol(excess_left)} mmol."),
            }

        seen.add(key)
        questions.append(q)

    if len(questions) < count:
        return None
    return {"family": family, "seed": seed, "questions": questions}


def _vol_misconception(this_vol: Decimal, other_vol: Decimal, this_src: str) -> str:
    if this_vol < other_vol:
        return f"{this_src} has the smaller volume, but volume alone doesn't decide it — convert to moles first."
    return f"Picking {this_src} by inspection — compare the moles of the reacting ion, not the volumes or concentrations alone."


# ------------------------------ gas-stoichiometry practice (ADR-0041) ------------------------------
#
# Variants of a weighed metal + an acid solution: which reactant limits, how much gas forms (PV=nRT), how much
# excess is left. Free-entry numeric (volume, leftover) + categorical (limiting), ADR-0032. The gas volume is
# model-exact-then-rounded (ADR-0040) — the moles are exact (clean grids), the volume rides on R (non-terminating)
# and is reported to 3 sig figs. NO interactive block: the reaction constants travel in the practice `gas` block so
# check-parity re-derives every answer in pure Node from the emitted `args` (metal mass, acid volume/molarity).

# the metal (weighed) and the acid (a stronger solution than the dilute lesson grids, so its capacity is
# COMPARABLE to the metal's — the limiting reagent then genuinely switches across variants, metal or acid).
_GAS_METAL_MOL = [Decimal(n) for n in ("0.0200", "0.0300", "0.0400", "0.0500", "0.0600", "0.0800")]
_GAS_ACID_VOL = [Decimal(v) for v in ("20.0", "30.0", "40.0", "50.0", "60.0", "80.0")]
_GAS_ACID_CONC = [Decimal(c) for c in ("0.500", "1.00", "1.50", "2.00", "2.50")]
_STP_MOLAR_VOL = Decimal("22.4")   # the STP-only molar volume — the canonical wrong constant off STP


def _sig(d: Decimal, digits: int) -> str:
    if d == 0:
        return "0"
    with localcontext() as c:
        c.prec = digits
        c.rounding = ROUND_HALF_UP
        s = format(+d, "f")
    return (s.rstrip("0").rstrip(".") if "." in s else s) or "0"


def generate_gas_practice(seed: int, count: int, ctx: str = "", *, metal: dict, acid: dict, gas: dict,
                          R: Decimal, temperature_K: Decimal, pressure_atm: Decimal,
                          family: str = "gas_stoichiometry_v1") -> dict | None:
    """Build the gas-stoichiometry practice block. `metal` = {id, molar_mass (Decimal), coeff}; `acid` = {id,
    coeff}; `gas` = {id, coeff, molar_mass}. The volume answers use the sourced gas constant R at the stated
    conditions. Deterministic (seeded) and solver-verified; returns None if it cannot fill `count`."""
    m_id, M_metal, k_metal = metal["id"], Fraction(metal["molar_mass"]), metal["coeff"]
    a_id, k_acid = acid["id"], acid["coeff"]
    g_id, k_gas = gas["id"], gas["coeff"]
    molar_vol = R * temperature_K / pressure_atm   # L/mol at the conditions (Decimal)

    def _vol_L(xi: Fraction) -> Decimal:
        return k_gas * Decimal(xi.numerator) / Decimal(xi.denominator) * molar_vol

    rng = random.Random(seed)
    questions: list[dict] = []
    seen: set[tuple] = set()
    attempts = 0
    while len(questions) < count and attempts < 4000:
        attempts += 1
        n_metal = rng.choice(_GAS_METAL_MOL)
        v_acid, c_acid = rng.choice(_GAS_ACID_VOL), rng.choice(_GAS_ACID_CONC)
        key = (n_metal, v_acid, c_acid)
        if key in seen:
            continue
        n_metal_f = Fraction(n_metal)
        n_acid_f = Fraction(v_acid) / 1000 * Fraction(c_acid)
        cap_metal, cap_acid = n_metal_f / k_metal, n_acid_f / k_acid

        hi, lo = max(cap_metal, cap_acid), min(cap_metal, cap_acid)
        if lo == 0 or hi / lo < _MIN_RATIO:      # reject near-ties (no clear limiting reagent)
            continue
        metal_limits = cap_metal < cap_acid
        xi = lo
        mass_metal = n_metal_f * M_metal          # the weighed mass shown to the student (exact)
        left_metal = n_metal_f - k_metal * xi
        left_acid = n_acid_f - k_acid * xi
        excess_src = a_id if metal_limits else m_id
        excess_left = left_acid if metal_limits else left_metal
        excess_start = n_acid_f if metal_limits else n_metal_f
        limiting_src = m_id if metal_limits else a_id

        given = [{"species": m_id, "mass_g": _grams(mass_metal)},
                 {"species": a_id, "volume_mL": format(v_acid, "f"), "molarity_M": format(c_acid, "f")}]
        args = {"metal_mass_g": _grams(mass_metal), "acid_volume_mL": format(v_acid, "f"),
                "acid_molarity_M": format(c_acid, "f")}
        stem = (f"{_grams(mass_metal)} g of {m_id} is dropped into {format(v_acid, 'f')} mL of "
                f"{format(c_acid, 'f')} M {a_id}, and the {g_id} gas is collected at "
                f"{_sig(pressure_atm, 3)} atm and {_sig(temperature_K, 4)} K.")

        kind = ("volume", "limiting", "leftover")[len(questions) % 3]
        if kind == "volume":
            vol = _vol_L(xi)
            vol_stp = k_gas * Decimal(xi.numerator) / Decimal(xi.denominator) * _STP_MOLAR_VOL   # the 22.4 slip
            vol_excess = _vol_L(hi)                                                              # from the excess
            q = {
                "id": f"q{len(questions) + 1}", "kind": "volume", "mode": "numeric",
                "prompt": f"{stem} What volume of {g_id} forms?",
                "given": given, "args": args,
                "answer": {"display": f"{_sig(vol, 3)} L", "value": _sig(vol, 4), "unit": "L"},
                "diagnostics": _practice_diagnostics(_sig(vol, 4), "L", [
                    (_sig(vol_stp, 4), "Used 22.4 L/mol — that is the molar volume only at STP (0 °C, 1 atm). "
                                       "At these conditions use PV=nRT (RT/P L/mol)."),
                    (_sig(vol_excess, 4), f"Sized the gas from {excess_src}, the reactant in excess — the gas is "
                                          f"capped by the limiting reagent {limiting_src}."),
                ]),
                "explain": (f"{limiting_src} limits, so ξ = {_mmol(xi)} mmol of {g_id}; "
                            f"V = {_mmol(xi)} mmol × {_sig(molar_vol, 4)} L/mol (= RT/P) = {_sig(vol, 3)} L."),
            }
        elif kind == "limiting":
            q = {
                "id": f"q{len(questions) + 1}", "kind": "limiting", "mode": "choice",
                "prompt": f"{stem} Which reactant is the limiting reagent?",
                "given": given, "args": args,
                "answer": {"display": limiting_src, "value": limiting_src},
                "choices": [
                    {"display": m_id, "correct": metal_limits,
                     "misconception": None if metal_limits else
                     f"{m_id} is in excess here — divide each reactant's moles by its coefficient and compare."},
                    {"display": a_id, "correct": not metal_limits,
                     "misconception": None if not metal_limits else
                     f"{a_id} is in excess here — the acid's moles ÷ {k_acid} still beats the metal's capacity."},
                    {"display": "Neither — both are fully consumed", "correct": False,
                     "misconception": "One reactant is left over, so they are not both fully consumed."},
                ],
                "explain": (f"Capacities: {m_id} = {_mmol(n_metal_f)} ÷ {k_metal} = {_mmol(cap_metal)} mmol, "
                            f"{a_id} = {_mmol(n_acid_f)} ÷ {k_acid} = {_mmol(cap_acid)} mmol. "
                            f"{limiting_src} is smaller, so it limits."),
            }
        else:  # leftover
            q = {
                "id": f"q{len(questions) + 1}", "kind": "leftover", "mode": "numeric",
                "prompt": f"{stem} After the reaction, how many mmol of the excess reactant remain?",
                "given": given, "args": args,
                "answer": {"display": f"{_mmol(excess_left)} mmol", "value": _mmol(excess_left), "unit": "mmol"},
                "diagnostics": _practice_diagnostics(_mmol(excess_left), "mmol", [
                    (_mmol(excess_start), f"That is all the {excess_src} you started with — some reacts; only the "
                                          f"surplus over the limiting reagent remains."),
                    ("0", "Only the limiting reagent reaches 0; the excess reactant leaves a leftover."),
                ]),
                "explain": (f"{excess_src} started at {_mmol(excess_start)} mmol and "
                            f"{_mmol(excess_start - excess_left)} mmol reacted, leaving {_mmol(excess_left)} mmol."),
            }

        seen.add(key)
        questions.append(q)

    if len(questions) < count:
        return None
    # the reaction constants travel with the set so check-parity re-derives every answer in pure Node
    return {
        "family": family, "seed": seed,
        "gas": {
            "metal_id": m_id, "metal_molar_mass": format(metal["molar_mass"], "f"), "metal_coeff": k_metal,
            "acid_id": a_id, "acid_coeff": k_acid, "gas_id": g_id, "gas_coeff": k_gas,
            "gas_constant": format(R, "f"), "temperature_K": format(temperature_K, "f"),
            "pressure_atm": format(pressure_atm, "f"),
        },
        "questions": questions,
    }


# ------------------------------ energy-ledger practice (ADR-0043) ------------------------------
#
# Variants of the same reaction with the two reactant amounts varied: which reactant limits, how much HEAT the
# burn releases (q = ΔH_rxn·ξ), how much excess is left. Free-entry numeric (heat, leftover) + categorical
# (limiting), ADR-0032. Like the gas practice (ADR-0041) there is NO interactive block — the reaction constants
# (each reactant's molar mass + coefficient, and ΔH_rxn) travel in the practice `energetics` block so check-parity
# re-derives every answer in pure Node from the emitted `args` (the two masses). The extent ξ is set by the
# limiting reagent; q rides on the sourced-then-summed ΔH_rxn. Grids are stated as CAPACITIES (mol of reaction) so
# the limiting reagent switches regardless of the coefficients.
_ENERGY_CAP_A = [Decimal(c) for c in ("0.0200", "0.0300", "0.0400", "0.0500", "0.0600")]
_ENERGY_CAP_B = [Decimal(c) for c in ("0.0200", "0.0300", "0.0400", "0.0500", "0.0600", "0.0800")]


def generate_energy_practice(seed: int, count: int, ctx: str = "", *, reactant_a: dict, reactant_b: dict,
                             delta_h_rxn: Decimal, family: str = "energy_ledger_v1") -> dict | None:
    """Build the energy-ledger practice block. `reactant_a`/`reactant_b` = {id, molar_mass (Decimal), coeff};
    `delta_h_rxn` the reaction enthalpy (kJ/mol, signed). Deterministic (seeded) and solver-verified; returns
    None if it cannot fill `count`. The heat q = ΔH_rxn·ξ is model-exact — reported to 3 sig figs (its precision
    is the sourced ΔH_f°'s), the gate re-derives within tolerance."""
    a_id, M_a, k_a = reactant_a["id"], Fraction(reactant_a["molar_mass"]), reactant_a["coeff"]
    b_id, M_b, k_b = reactant_b["id"], Fraction(reactant_b["molar_mass"]), reactant_b["coeff"]
    dH = Fraction(delta_h_rxn)

    rng = random.Random(seed)
    questions: list[dict] = []
    seen: set[tuple] = set()
    attempts = 0
    while len(questions) < count and attempts < 4000:
        attempts += 1
        cap_a, cap_b = rng.choice(_ENERGY_CAP_A), rng.choice(_ENERGY_CAP_B)
        key = (cap_a, cap_b)
        if key in seen:
            continue
        cap_a_f, cap_b_f = Fraction(cap_a), Fraction(cap_b)
        hi, lo = max(cap_a_f, cap_b_f), min(cap_a_f, cap_b_f)
        if lo == 0 or hi / lo < _MIN_RATIO:        # reject near-ties (no clear limiting reagent)
            continue
        a_limits = cap_a_f < cap_b_f
        xi = lo
        n_a, n_b = cap_a_f * k_a, cap_b_f * k_b     # initial moles (exact)
        mass_a, mass_b = n_a * M_a, n_b * M_b        # weighed masses shown to the student
        limiting_src = a_id if a_limits else b_id
        excess_src = b_id if a_limits else a_id
        excess_cap, excess_coeff = (cap_b_f, k_b) if a_limits else (cap_a_f, k_a)
        excess_start = n_b if a_limits else n_a
        excess_left = excess_coeff * (excess_cap - xi)   # excess reactant left after ξ

        # q = ΔH_rxn·ξ — exact (terminating), carried as a Decimal so _sig rounds to sig figs (a raw Fraction
        # would format at full precision, bypassing the rounding). Two named mistakes: the naive ΔH_rxn-as-total
        # (forgot ξ) and sizing ξ from the reactant in excess.
        q_correct = to_decimal(dH * xi, 12)          # the heat (exact within 12 places)
        q_excess = to_decimal(dH * hi, 12)           # sized the extent from the reactant in excess

        ma_s, mb_s = _exact_grams(mass_a), _exact_grams(mass_b)   # full precision → the gate re-derives moles exactly
        given = [{"species": a_id, "mass_g": ma_s}, {"species": b_id, "mass_g": mb_s}]
        args = {"mass_a_g": ma_s, "mass_b_g": mb_s}
        stem = (f"For this reaction ΔH_rxn = {_sig(delta_h_rxn, 5)} kJ/mol. {ma_s} g of {a_id} reacts "
                f"with {mb_s} g of {b_id} and the reaction goes to completion.")

        kind = ("heat", "limiting", "leftover")[len(questions) % 3]
        if kind == "heat":
            q = {
                "id": f"q{len(questions) + 1}", "kind": "heat", "mode": "numeric",   # free entry (ADR-0032)
                "prompt": f"{stem} What is q, the heat of reaction (kJ)? A negative value means heat is released.",
                "given": given, "args": args,
                "answer": {"display": f"{_sig(q_correct, 3)} kJ", "value": _sig(q_correct, 4), "unit": "kJ"},
                "diagnostics": _practice_diagnostics(_sig(q_correct, 4), "kJ", [
                    (_sig(delta_h_rxn, 5), "Used ΔH_rxn as the total heat — that is per mole of reaction. Multiply "
                                           "by the extent ξ (the moles of reaction the limiting reagent allows)."),
                    (_sig(q_excess, 4), f"Sized the extent from {excess_src}, the reactant in excess — ξ is capped "
                                        f"by the limiting reagent {limiting_src}."),
                ]),
                "explain": (f"{limiting_src} limits, so ξ = {_mmol(xi)} mmol of reaction; "
                            f"q = ΔH_rxn × ξ = {_sig(delta_h_rxn, 5)} kJ/mol × {_mmol(xi)} mmol = "
                            f"{_sig(q_correct, 3)} kJ."),
            }
        elif kind == "limiting":
            q = {
                "id": f"q{len(questions) + 1}", "kind": "limiting", "mode": "choice",
                "prompt": f"{stem} Which reactant is the limiting reagent?",
                "given": given, "args": args,
                "answer": {"display": limiting_src, "value": limiting_src},
                "choices": [
                    {"display": a_id, "correct": a_limits,
                     "misconception": None if a_limits else
                     f"{a_id} is in excess here — divide each reactant's moles by its coefficient and compare."},
                    {"display": b_id, "correct": not a_limits,
                     "misconception": None if not a_limits else
                     f"{b_id} is in excess here — divide each reactant's moles by its coefficient and compare."},
                    {"display": "Neither — both are fully consumed", "correct": False,
                     "misconception": "One reactant is left over, so they are not both fully consumed."},
                ],
                "explain": (f"Capacities (moles ÷ coefficient): {a_id} = {_mmol(n_a)} ÷ {k_a} = {_mmol(cap_a_f)} mmol, "
                            f"{b_id} = {_mmol(n_b)} ÷ {k_b} = {_mmol(cap_b_f)} mmol. "
                            f"{limiting_src} is smaller, so it limits."),
            }
        else:  # leftover
            q = {
                "id": f"q{len(questions) + 1}", "kind": "leftover", "mode": "numeric",
                "prompt": f"{stem} After the reaction, how many mmol of the excess reactant remain?",
                "given": given, "args": args,
                "answer": {"display": f"{_mmol(excess_left)} mmol", "value": _mmol(excess_left), "unit": "mmol"},
                "diagnostics": _practice_diagnostics(_mmol(excess_left), "mmol", [
                    (_mmol(excess_start), f"That is all the {excess_src} you started with — some reacts; only the "
                                          f"surplus over the limiting reagent remains."),
                    ("0", "Only the limiting reagent reaches 0; the excess reactant leaves a leftover."),
                ]),
                "explain": (f"{excess_src} started at {_mmol(excess_start)} mmol and "
                            f"{_mmol(excess_start - excess_left)} mmol reacted, leaving {_mmol(excess_left)} mmol."),
            }

        seen.add(key)
        questions.append(q)

    if len(questions) < count:
        return None
    return {
        "family": family, "seed": seed,
        "energetics": {
            "reactant_a_id": a_id, "reactant_a_molar_mass": format(reactant_a["molar_mass"], "f"),
            "reactant_a_coeff": k_a,
            "reactant_b_id": b_id, "reactant_b_molar_mass": format(reactant_b["molar_mass"], "f"),
            "reactant_b_coeff": k_b,
            "delta_h_rxn_kj_per_mol": format(delta_h_rxn, "f"),
        },
        "questions": questions,
    }
