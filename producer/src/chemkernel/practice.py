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
from decimal import Decimal
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


def generate_practice(interactive: dict, seed: int, count: int, ctx: str = "") -> dict | None:
    """Build the practice block from an emitted `interactive` block (its multiplicities are engine-derived)."""
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
                "prompt": f"{stem} What mass of {prod['id']} precipitate forms?",
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
    return {"family": "precipitation_limiting_reagent_v1", "seed": seed, "questions": questions}


def _vol_misconception(this_vol: Decimal, other_vol: Decimal, this_src: str) -> str:
    if this_vol < other_vol:
        return f"{this_src} has the smaller volume, but volume alone doesn't decide it — convert to moles first."
    return f"Picking {this_src} by inspection — compare the moles of the reacting ion, not the volumes or concentrations alone."
