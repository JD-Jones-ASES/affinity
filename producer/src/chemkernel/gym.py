"""Dimensional-analysis gym generator (Phase 1 / brief §17.1, ADR-0024).

Generates verified quantity-algebra whose whole point is **visible unit cancellation**: convert among volume,
molarity, moles, and mass, each conversion factor shown as a fraction whose units cancel into the next step.
The honesty model, applied to a *generated* problem set:

  - every value is exact (`Fraction`); a candidate whose answer does not terminate as a decimal is rejected
    (like the practice reject-list), so nothing is silently rounded (ADR-0013);
  - every conversion's dimensions are re-checked by the **units engine** (`Quantity`), so the emitted chain is
    guaranteed dimensionally homogeneous — the machine, not the author, certifies that L × mol/L = mol;
  - every wrong choice is a **named cancellation mistake** (skipped mL→L, inverted a factor, stopped early),
    never a random number;
  - each problem carries a raw `derivation` block so `validate-gyms.mjs` re-derives the answer in pure Node.

Deterministic: a spec's seed always yields byte-identical problems (ADR-0008), so committed `derived/` is
reviewable. Molar masses come from `data/` (sourced, and separately tested in `test_data.py`).
"""

from __future__ import annotations

import random
from decimal import Context, Decimal, ROUND_HALF_UP, localcontext
from fractions import Fraction

from . import BuildError, __version__
from .nomenclature import (assemble_with, base_cation_name, formula_ionic, greek, is_variable,
                          name_ionic, other_charge_names, roman)
from .units import Quantity

# recognizable salts whose molar mass resolves from data/ (each parses + is built from known elements)
_SUBSTANCES = ["NaCl", "CaCl2", "Na2CO3", "CaCO3", "Na3PO4"]

_VOLS = [Decimal(v) for v in ("10.0", "15.0", "20.0", "25.0", "30.0", "40.0", "50.0", "100.0", "250.0")]
_CONCS = [Decimal(c) for c in ("0.0500", "0.100", "0.150", "0.200", "0.250", "0.500")]
_MOLS = [Decimal(n) for n in ("0.0100", "0.0250", "0.0500", "0.100", "0.150", "0.200")]

# rotation order — one of each before repeating, so a gym samples the whole skill set
_KINDS = ["volume_molarity_to_moles", "moles_molarity_to_volume", "mass_to_moles",
          "moles_to_mass", "volume_molarity_to_mass"]


def _terminates(f: Fraction) -> bool:
    den = f.denominator
    while den % 2 == 0:
        den //= 2
    while den % 5 == 0:
        den //= 5
    return den == 1


def _exact(f: Fraction) -> str:
    """Exact decimal string for a terminating Fraction (high-precision local context)."""
    with localcontext() as ctx:
        ctx.prec = 60
        return format(Decimal(f.numerator) / Decimal(f.denominator), "f")


def _trim(s: str) -> str:
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s or "0"


def _sig(f: Fraction, digits: int = 4) -> str:
    """A trimmed significant-figure display string (for choices — the wrong ones needn't terminate)."""
    if f == 0:
        return "0"
    with localcontext() as ctx:
        ctx.prec = digits
        ctx.rounding = ROUND_HALF_UP
        return _trim(format(+(Decimal(f.numerator) / Decimal(f.denominator)), "f"))


def _disp(f: Fraction, unit: str) -> str:
    # exact when it terminates and is short; else significant-figure rounded
    body = _trim(_exact(f)) if _terminates(f) else _sig(f)
    return f"{body} {unit}"


def _verify_dims(expr: Quantity, target_unit: str, ctx: str) -> None:
    """The units engine certifies the conversion lands in the target dimension (raises on mismatch)."""
    want = Quantity.of(1, target_unit).dim
    if expr.dim != want:
        raise BuildError(f"{ctx}: dimensional check failed — got dim {expr.dim}, expected {target_unit} ({want})")


def _fr(d: Decimal) -> Fraction:
    return Fraction(d)


def _problem(kind, sub, molar_mass, rng, ctx):
    """Build one verified problem of `kind`, or return None to reject (non-terminating / colliding choices)."""
    M = _fr(molar_mass)

    if kind == "volume_molarity_to_moles":
        v, c = Decimal(rng.choice(_VOLS)), Decimal(rng.choice(_CONCS))
        vL = _fr(v) / 1000
        n = vL * _fr(c)
        if not _terminates(n):
            return None
        _verify_dims(Quantity.of(v, "mL").to("L") * Quantity.of(c, "M"), "mol", ctx)
        chain = [
            {"value": _trim(_exact(_fr(v))), "unit": "mL", "note": "given volume"},
            {"value": _trim(_exact(vL)), "unit": "L", "note": "× (1 L / 1000 mL)"},
            {"value": _trim(_exact(n)), "unit": "mol", "note": f"× {_trim(str(c))} mol/L"},
        ]
        answer, target = n, "mol"
        prompt = f"How many moles of {sub} are in {_trim(str(v))} mL of {_trim(str(c))} M {sub}(aq)?"
        wrongs = [
            (n * 1000, "Skipped mL → L — the volume must be in litres before multiplying by mol/L (a factor of 1000)."),
            (vL / _fr(c), "Divided the volume by the molarity; the factor is × mol/L, and L × mol/L = mol."),
        ]
        explain = (f"{_trim(str(v))} mL = {_trim(_exact(vL))} L; × {_trim(str(c))} mol/L = {_trim(_exact(n))} mol. "
                   f"The litres cancel against mol/L, leaving mol.")
        deriv = {"substance": sub, "v_mL": _trim(str(v)), "c_M": _trim(str(c))}

    elif kind == "moles_molarity_to_volume":
        v, c = Decimal(rng.choice(_VOLS)), Decimal(rng.choice(_CONCS))
        n = _fr(v) / 1000 * _fr(c)                       # generate forward so the volume comes back clean
        vL = n / _fr(c)
        if not _terminates(n) or not _terminates(_fr(v)):
            return None
        _verify_dims(Quantity.of(_exact(n), "mol") / Quantity.of(c, "M"), "L", ctx)
        chain = [
            {"value": _trim(_exact(n)), "unit": "mol", "note": "given amount"},
            {"value": _trim(_exact(vL)), "unit": "L", "note": f"÷ {_trim(str(c))} mol/L"},
            {"value": _trim(str(v)), "unit": "mL", "note": "× (1000 mL / 1 L)"},
        ]
        answer, target = _fr(v), "mL"
        prompt = (f"What volume (in mL) of {_trim(str(c))} M {sub}(aq) contains "
                  f"{_trim(_exact(n))} mol of {sub}?")
        wrongs = [
            (vL, "Left the answer in litres — the L → mL step (× 1000) was skipped."),
            (n * _fr(c) * 1000, "Multiplied by the molarity instead of dividing; to undo mol/L you divide."),
        ]
        explain = (f"{_trim(_exact(n))} mol ÷ {_trim(str(c))} mol/L = {_trim(_exact(vL))} L; × 1000 = "
                   f"{_trim(str(v))} mL. Dividing by mol/L cancels the moles and leaves litres.")
        deriv = {"substance": sub, "n_mol": _trim(_exact(n)), "c_M": _trim(str(c))}

    elif kind == "mass_to_moles":
        n0 = _fr(rng.choice(_MOLS))
        m = n0 * M                                       # generate forward: mass of a clean mole amount
        if not _terminates(m):
            return None
        _verify_dims(Quantity.of(_exact(m), "g") / Quantity.of(str(molar_mass), "g/mol"), "mol", ctx)
        chain = [
            {"value": _trim(_exact(m)), "unit": "g", "note": "given mass"},
            {"value": _trim(_exact(n0)), "unit": "mol", "note": f"÷ {_trim(str(molar_mass))} g/mol"},
        ]
        answer, target = n0, "mol"
        prompt = f"How many moles are in {_trim(_exact(m))} g of {sub}?  (M = {_trim(str(molar_mass))} g/mol)"
        wrongs = [
            (m * M, "Multiplied by the molar mass instead of dividing; g ÷ (g/mol) = mol."),
            (M / m, "Inverted the factor — divided the molar mass by the mass."),
        ]
        explain = (f"{_trim(_exact(m))} g ÷ {_trim(str(molar_mass))} g/mol = {_trim(_exact(n0))} mol. "
                   f"Grams over grams-per-mole leaves moles.")
        deriv = {"substance": sub, "m_g": _trim(_exact(m)), "molar_mass_g_per_mol": _trim(str(molar_mass))}

    elif kind == "moles_to_mass":
        n0 = _fr(rng.choice(_MOLS))
        m = n0 * M
        if not _terminates(m):
            return None
        _verify_dims(Quantity.of(_exact(n0), "mol") * Quantity.of(str(molar_mass), "g/mol"), "g", ctx)
        chain = [
            {"value": _trim(_exact(n0)), "unit": "mol", "note": "given amount"},
            {"value": _trim(_exact(m)), "unit": "g", "note": f"× {_trim(str(molar_mass))} g/mol"},
        ]
        answer, target = m, "g"
        prompt = f"What is the mass of {_trim(_exact(n0))} mol of {sub}?  (M = {_trim(str(molar_mass))} g/mol)"
        wrongs = [
            (n0 / M, "Divided by the molar mass instead of multiplying; mol × (g/mol) = g."),
            (M, f"Reported the molar mass — that is the mass of exactly 1 mol, not {_trim(_exact(n0))} mol."),
        ]
        explain = (f"{_trim(_exact(n0))} mol × {_trim(str(molar_mass))} g/mol = {_trim(_exact(m))} g. "
                   f"Moles times grams-per-mole leaves grams.")
        deriv = {"substance": sub, "n_mol": _trim(_exact(n0)), "molar_mass_g_per_mol": _trim(str(molar_mass))}

    else:  # volume_molarity_to_mass — the two-step chain
        v, c = Decimal(rng.choice(_VOLS)), Decimal(rng.choice(_CONCS))
        vL = _fr(v) / 1000
        n = vL * _fr(c)
        m = n * M
        if not _terminates(m):
            return None
        _verify_dims(Quantity.of(v, "mL").to("L") * Quantity.of(c, "M") * Quantity.of(str(molar_mass), "g/mol"),
                     "g", ctx)
        chain = [
            {"value": _trim(str(v)), "unit": "mL", "note": "given volume"},
            {"value": _trim(_exact(vL)), "unit": "L", "note": "× (1 L / 1000 mL)"},
            {"value": _trim(_exact(n)), "unit": "mol", "note": f"× {_trim(str(c))} mol/L"},
            {"value": _trim(_exact(m)), "unit": "g", "note": f"× {_trim(str(molar_mass))} g/mol"},
        ]
        answer, target = m, "g"
        prompt = (f"What mass of {sub} is in {_trim(str(v))} mL of {_trim(str(c))} M {sub}(aq)?  "
                  f"(M = {_trim(str(molar_mass))} g/mol)")
        wrongs = [
            (n * 1000 * M, "Skipped mL → L, so the moles (and the mass) came out 1000× too large."),
            (n, "Stopped at moles — the amount was never multiplied by the molar mass to reach grams."),
        ]
        explain = (f"{_trim(str(v))} mL = {_trim(_exact(vL))} L; × {_trim(str(c))} mol/L = {_trim(_exact(n))} mol; "
                   f"× {_trim(str(molar_mass))} g/mol = {_trim(_exact(m))} g.")
        deriv = {"substance": sub, "v_mL": _trim(str(v)), "c_M": _trim(str(c)),
                 "molar_mass_g_per_mol": _trim(str(molar_mass))}

    # assemble choices: the EXACT answer + the two named-mistake distractors (rounded — they're wrong anyway)
    correct_disp = _disp(answer, target)
    choices = [{"display": correct_disp, "correct": True, "misconception": None}]
    for val, why in wrongs:
        choices.append({"display": f"{_sig(val)} {target}", "correct": False, "misconception": why})
    displays = [ch["display"] for ch in choices]
    if len(set(displays)) != len(displays):        # a distractor collided with the answer at display precision
        return None

    return {
        "kind": kind,
        "prompt": prompt,
        "chain": chain,
        "target_unit": target,
        "answer": {"value": _exact(answer), "unit": target, "display": correct_disp},
        "derivation": {"kind": kind, "inputs": deriv},
        "choices": choices,
        "explain": explain,
    }


def _generate_conversions(seed, count, data, ctx):
    molar_mass = {s: data.molar_mass(s) for s in _SUBSTANCES}   # sourced, and separately tested
    rng = random.Random(seed)
    problems: list[dict] = []
    seen: set = set()
    attempts = 0
    while len(problems) < count and attempts < 6000:
        attempts += 1
        kind = _KINDS[len(problems) % len(_KINDS)]
        sub = rng.choice(_SUBSTANCES)
        q = _problem(kind, sub, molar_mass[sub], rng, ctx)
        if q is None:
            continue
        fingerprint = (q["kind"], q["prompt"])
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        q["id"] = f"q{len(problems) + 1}"
        problems.append(q)
    if len(problems) < count:
        raise BuildError(f"{ctx}: gym could not generate {count} non-rejected problems at seed {seed}")
    return problems


# ------------------------------ ionic nomenclature (item 2, ADR-0027) ------------------------------

_DIRECTIONS = ["formula_to_name", "name_to_formula"]


def _nomenclature_problem(direction, cation, anion, data, ctx):
    """One ionic name↔formula problem, or None to reject (collapsed distractors)."""
    try:
        formula, n_cat, n_an = formula_ionic(cation, anion, ctx)
    except BuildError:
        return None
    name = name_ionic(cation, anion, ctx)
    c, a = cation.charge, -anion.charge                 # positive charge magnitudes
    variable = is_variable(cation, data.ions)
    base = base_cation_name(cation, data)

    if variable:
        others = other_charge_names(cation, data.ions)
        name_wrongs = [(f"{base} {anion.compound_name}",
                        "Dropped the Roman numeral — a variable-charge metal must state its charge (the Stock system).")]
        if others:
            name_wrongs.insert(0, (f"{others[0]} {anion.compound_name}",
                                   "Wrong oxidation state — the anion fixes the metal's charge here; check which Stock numeral balances it."))
    else:
        name_wrongs = [
            (f"{base}({roman(c)}) {anion.compound_name}",
             "Added a Roman numeral to a fixed-charge metal — only variable-charge metals take one."),
            (f"{greek(n_cat, drop_mono=False)}{base} {greek(n_an, drop_mono=False)}{anion.compound_name}",
             "Used Greek prefixes (mono-, di-, tri-) — those name covalent molecules, not ionic compounds."),
        ]

    formula_wrongs = [
        (assemble_with(cation, c, anion, a),
         "Used each ion's own charge as its subscript — you CROSS the charges (each subscript is the other ion's charge)."),
        (assemble_with(cation, 1, anion, 1),
         f"Combined one-to-one — the charges (+{c}, −{a}) don't cancel one-for-one; balance them."),
    ]

    if direction == "formula_to_name":
        prompt = f"What is the name of {formula}?"
        answer, wrongs = name, name_wrongs
        subscript = [formula, cation.id, anion.id]
        if variable:
            explain = (f"Charge balance sets the metal: {n_an}×{anion.compound_name} gives {n_an * a}− total, "
                       f"matched by {n_cat}×{cation.id} — so {formula} is {name}.")
        else:
            explain = (f"{cation.id} is the cation and {anion.id} the anion; a fixed-charge metal needs no "
                       f"numeral, so {formula} is {name}.")
    else:
        prompt = f"Write the formula for {name}."
        answer, wrongs = formula, formula_wrongs
        subscript = [formula] + [w for w, _ in formula_wrongs] + [cation.id, anion.id]
        explain = (f"{cation.id} and {anion.id} cross their charges: {n_cat}×{cation.formula} to "
                   f"{n_an}×({anion.compound_name}) gives the neutral {formula}.")

    seen = {answer}
    choices = [{"display": answer, "correct": True, "misconception": None}]
    for disp, why in wrongs:
        if disp in seen:
            return None                                  # a distractor collapsed onto another choice — reject
        seen.add(disp)
        choices.append({"display": disp, "correct": False, "misconception": why})
    if len(choices) != 3:
        return None

    return {
        "kind": f"ionic_{direction}",
        "prompt": prompt,
        "answer": {"value": answer, "display": answer},
        "derivation": {
            "kind": f"ionic_{direction}",
            "cation": {"id": cation.id, "formula_part": cation.formula, "charge": cation.charge,
                       "compound_name": cation.compound_name},
            "anion": {"id": anion.id, "formula_part": anion.formula, "charge": anion.charge,
                      "compound_name": anion.compound_name},
            "formula": formula,
            "name": name,
        },
        "choices": choices,
        "explain": explain,
        "subscript_tokens": subscript,
    }


def _generate_nomenclature(seed, count, data, ctx):
    cations = sorted((i for i in data.ions.values() if i.charge > 0 and i.compound_name and i.id != "H^+"),
                     key=lambda i: i.id)
    anions = sorted((i for i in data.ions.values() if i.charge < 0 and i.compound_name), key=lambda i: i.id)
    rng = random.Random(seed)
    problems: list[dict] = []
    seen: set = set()
    attempts = 0
    while len(problems) < count and attempts < 8000:
        attempts += 1
        direction = _DIRECTIONS[len(problems) % len(_DIRECTIONS)]
        q = _nomenclature_problem(direction, rng.choice(cations), rng.choice(anions), data, ctx)
        if q is None:
            continue
        fingerprint = (q["kind"], q["prompt"])
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        q["id"] = f"q{len(problems) + 1}"
        problems.append(q)
    if len(problems) < count:
        raise BuildError(f"{ctx}: nomenclature gym could not generate {count} problems at seed {seed}")
    return problems


_FAMILIES = {
    "solution_conversions_v1": _generate_conversions,
    "ionic_nomenclature_v1": _generate_nomenclature,
}


def generate_gym(spec: dict, data, ctx: str = "") -> dict:
    """Build a verified gym problem set from an authored spec (deterministic in `seed`)."""
    family = spec.get("family")
    generator = _FAMILIES.get(family)
    if generator is None:
        raise BuildError(f"{ctx}: unknown gym family '{family}'")
    seed, count = int(spec["seed"]), int(spec.get("count", 8))
    problems = generator(seed, count, data, ctx)

    return {
        "kind": "gym",
        "id": spec["id"],
        "title": spec["title"],
        "slug": spec["slug"],
        "topic": spec["topic"],
        "family": family,
        "seed": seed,
        "blurb": spec.get("blurb", ""),
        "skills": spec.get("skills", []),
        "reference_links": spec.get("reference_links", []),
        "problems": problems,
        "provenance": {
            "producer": "chemkernel",
            "version": __version__,
            "sources": {"atomic_weight": data.sources.get("atomic_weight", "")},
        },
    }
