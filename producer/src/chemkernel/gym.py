"""Dimensional-analysis gym generator (Phase 1 / brief §17.1, ADR-0024).

Generates verified quantity-algebra whose whole point is **visible unit cancellation**: convert among volume,
molarity, moles, and mass, each conversion factor shown as a fraction whose units cancel into the next step.
The honesty model, applied to a *generated* problem set:

  - every value is exact (`Fraction`); a candidate whose answer does not terminate as a decimal is rejected
    (like the practice reject-list), so nothing is silently rounded (ADR-0013);
  - every conversion's dimensions are re-checked by the **units engine** (`Quantity`), so the emitted chain is
    guaranteed dimensionally homogeneous — the machine, not the author, certifies that L × mol/L = mol;
  - **numeric answers are free-entry, not multiple choice** (ADR-0032): a menu of a number and its
    wrong-by-magnitude cousins (0.55 % vs 55 %) is gameable on sight, so the learner types the number and the
    **named mistakes become a diagnostic** of what they entered (skipped mL→L, inverted a factor, stopped
    early). Categorical answers (names, formulas, coefficient sets) stay multiple choice — every distractor is
    a plausible, same-form answer a specific misconception produces, so recognition can't shortcut them;
  - each problem carries a raw `derivation` block so `validate-gyms.mjs` re-derives the answer in pure Node.

Deterministic: a spec's seed always yields byte-identical problems (ADR-0008), so committed `derived/` is
reviewable. Molar masses come from `data/` (sourced, and separately tested in `test_data.py`).
"""

from __future__ import annotations

import random
import re
from decimal import Context, Decimal, ROUND_HALF_UP, localcontext
from fractions import Fraction

from . import BuildError, __version__
from .balance import balance
from .formula import parse_formula
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

    # a numeric answer is a FREE-ENTRY drill (ADR-0032): the learner types the number and the named cancellation
    # mistakes become a diagnostic of what they entered, not a menu that hands away the answer by magnitude.
    correct_disp, diagnostics = _numeric_response(answer, target, wrongs)

    return {
        "kind": kind,
        "mode": "numeric",
        "prompt": prompt,
        "chain": chain,
        "target_unit": target,
        "answer": {"value": _exact(answer), "unit": target, "display": correct_disp},
        "derivation": {"kind": kind, "inputs": deriv},
        "diagnostics": diagnostics,
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
        "mode": "choice",              # a name/formula is categorical — a plausible same-form menu (ADR-0032)
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


# ------------------------------ balancing (item 3, ADR-0028) ------------------------------

# Curated skeletal reactions spanning the archetypes a first course balances (synthesis, combustion,
# decomposition, replacement, double-displacement, net-ionic). Each is BALANCED BY THE ENGINE — balance()'s
# rational null space (ADR-0014), never authored coefficients — so the answer is machine-derived and
# re-verified element-by-element and for charge before it is emitted. Every formula parses under grammar v0.
# `trap` is the canonical subscript-mutation misconception for a reaction: a *different real substance* that
# makes the atoms look balanced without coefficients. It is emitted only where genuinely deceptive, and the
# producer proves it atom-balances AND that it changed a formula (else it refuses) — an honest trap, not a
# strawman. The charged net-ionic reactions load the charge row (house-conventions §Notation).
_REACTIONS = [
    {"reactants": ["H2", "O2"], "products": ["H2O"], "archetype": "synthesis",
     "trap": {"reactants": ["H2", "O2"], "products": ["H2O2"], "coeffs": [1, 1, 1],
              "note": "You balanced oxygen by changing a subscript — but H2O2 (hydrogen peroxide) is a "
                      "different substance from H2O (water). Coefficients balance an equation; subscripts "
                      "define the compound and must never be changed."}},
    {"reactants": ["C", "O2"], "products": ["CO"], "archetype": "combustion",
     "trap": {"reactants": ["C", "O2"], "products": ["CO2"], "coeffs": [1, 1, 1],
              "note": "You balanced oxygen by changing a subscript — but CO2 (carbon dioxide) is a different "
                      "substance from CO (carbon monoxide). Only the coefficients out front may change; the "
                      "formula CO stays CO."}},
    {"reactants": ["N2", "H2"], "products": ["NH3"], "archetype": "synthesis"},
    {"reactants": ["CH4", "O2"], "products": ["CO2", "H2O"], "archetype": "combustion"},
    {"reactants": ["C3H8", "O2"], "products": ["CO2", "H2O"], "archetype": "combustion"},
    {"reactants": ["C2H6", "O2"], "products": ["CO2", "H2O"], "archetype": "combustion"},
    {"reactants": ["KClO3"], "products": ["KCl", "O2"], "archetype": "decomposition"},
    {"reactants": ["Zn", "HCl"], "products": ["ZnCl2", "H2"], "archetype": "single replacement"},
    {"reactants": ["Al", "O2"], "products": ["Al2O3"], "archetype": "synthesis"},
    {"reactants": ["Fe", "O2"], "products": ["Fe2O3"], "archetype": "synthesis"},
    {"reactants": ["NaOH", "H2SO4"], "products": ["Na2SO4", "H2O"], "archetype": "acid-base neutralization"},
    {"reactants": ["CaCl2", "Na3PO4"], "products": ["Ca3(PO4)2", "NaCl"], "archetype": "double replacement"},
    {"reactants": ["Ca^2+", "PO4^3-"], "products": ["Ca3(PO4)2"], "archetype": "net-ionic precipitation"},
    {"reactants": ["Ca^2+", "CO3^2-"], "products": ["CaCO3"], "archetype": "net-ionic precipitation"},
]


def _species_of(reactants, products, ctx):
    """Parse a skeletal reaction into ordered species dicts (formula, role, element counts, charge)."""
    r = [parse_formula(s, ctx) for s in reactants]
    p = [parse_formula(s, ctx) for s in products]
    species = [{"formula": f.raw, "role": "reactant", "counts": dict(f.counts), "charge": f.charge} for f in r]
    species += [{"formula": f.raw, "role": "product", "counts": dict(f.counts), "charge": f.charge} for f in p]
    return r, p, species


def _eq_str(species, coeffs, arrow="→"):
    """A reaction string 'c1 F1 + c2 F2 → …' with the coefficient 1 omitted (house style, _molecular_text)."""
    def side(role):
        return " + ".join((f"{c} " if c != 1 else "") + s["formula"]
                          for s, c in zip(species, coeffs) if s["role"] == role)
    return f"{side('reactant')} {arrow} {side('product')}"


def _tally(species, coeffs, key):
    """(left, right) totals for one conserved quantity: an element symbol, or 'charge'."""
    def amount(s):
        return s["charge"] if key == "charge" else s["counts"].get(key, 0)
    left = sum(amount(s) * c for s, c in zip(species, coeffs) if s["role"] == "reactant")
    right = sum(amount(s) * c for s, c in zip(species, coeffs) if s["role"] == "product")
    return left, right


def _first_unbalanced(species, coeffs):
    """The first element (sorted) — or 'charge' — that a coefficient vector fails to conserve, else None."""
    for el in sorted({e for s in species for e in s["counts"]}):
        left, right = _tally(species, coeffs, el)
        if left != right:
            return el, left, right
    if any(s["charge"] for s in species):
        left, right = _tally(species, coeffs, "charge")
        if left != right:
            return "charge", left, right
    return None


def _fmt_charge(q: int) -> str:
    return f"{'+' if q >= 0 else '−'}{abs(q)}"


def _balancing_problem(reaction, rng, ctx):
    """One balancing problem: engine-derived coefficients + named-mistake distractors, or None to reject."""
    r_forms, p_forms, species = _species_of(reaction["reactants"], reaction["products"], ctx)
    coeffs = balance(r_forms, p_forms, ctx)                 # machine-derived, re-verified (ADR-0014)
    n = len(species)
    elements = sorted({e for s in species for e in s["counts"]})
    charged = any(s["charge"] for s in species)

    prompt = "Balance:  " + _eq_str(species, [1] * n)
    answer_display = _eq_str(species, coeffs)
    tokens = {s["formula"] for s in species}

    choices = [{"display": answer_display, "correct": True, "misconception": None}]
    seen = {answer_display}
    wrongs: list[tuple[str, str]] = []

    # (a) the subscript-mutation trap — the star misconception, authored per reaction and proven honest
    trap = reaction.get("trap")
    if trap:
        _tr, _tp, t_species = _species_of(trap["reactants"], trap["products"], ctx)
        if _first_unbalanced(t_species, trap["coeffs"]) is not None:
            raise BuildError(f"{ctx}: trap for '{prompt}' does not atom-balance — not a convincing trap")
        if not (set(s["formula"] for s in t_species) - set(s["formula"] for s in species)):
            raise BuildError(f"{ctx}: trap for '{prompt}' changed no formula — not a subscript mutation")
        disp = _eq_str(t_species, trap["coeffs"])
        if disp not in seen:
            seen.add(disp)
            wrongs.append((disp, trap["note"]))
            tokens |= {s["formula"] for s in t_species}

    # (b) coefficient-error distractors: perturb the unique balance; name the element it throws off. Adding 1
    # to any single coefficient always breaks conservation (the null space is 1-D, ADR-0014), so distractors
    # are guaranteed constructible; the "all-ones" skeletal is added when the reaction isn't already 1:1:….
    perturbs = [[c + (1 if i == j else 0) for i, c in enumerate(coeffs)] for j in range(n)]
    if any(c != 1 for c in coeffs):
        perturbs.append([1] * n)
    perturbs += [[c - (1 if i == j else 0) for i, c in enumerate(coeffs)] for j in range(n) if coeffs[j] > 1]
    rng.shuffle(perturbs)

    for v in perturbs:
        if len(wrongs) >= 2:
            break
        off = _first_unbalanced(species, v)
        if off is None:
            continue                                       # coincidentally balanced (a scalar multiple) — skip
        disp = _eq_str(species, v)
        if disp in seen:
            continue
        seen.add(disp)
        key, left, right = off
        if key == "charge":
            why = (f"That unbalances the charge — {_fmt_charge(left)} on the left, {_fmt_charge(right)} on the "
                   f"right. Balance atoms and charge together, and only with coefficients.")
        else:
            why = (f"That leaves {key} unbalanced — {left} on the left, {right} on the right. Fix it with the "
                   f"coefficients; the subscripts stay put.")
        wrongs.append((disp, why))

    if len(wrongs) != 2:
        return None                                        # couldn't build two distinct named distractors

    for disp, why in wrongs:
        choices.append({"display": disp, "correct": False, "misconception": why})

    check = "; ".join(f"{el} {_tally(species, coeffs, el)[0]}={_tally(species, coeffs, el)[1]}" for el in elements)
    if charged:
        lq, rq = _tally(species, coeffs, "charge")
        check += f"; charge {lq}={rq}"
    explain = (f"Coefficients — never subscripts — balance the equation. {answer_display} conserves every atom "
               f"({check}); ChemKernel derives them as the single integer solution of the conservation matrix.")

    return {
        "kind": "balancing",
        "mode": "choice",              # coefficient sets are categorical — a plausible same-form menu (ADR-0032)
        "prompt": prompt,
        "answer": {"value": ",".join(str(c) for c in coeffs), "display": answer_display},
        "derivation": {
            "kind": "balancing",
            "archetype": reaction["archetype"],
            "species": species,
            "coefficients": list(coeffs),
            "elements": elements,
        },
        "choices": choices,
        "explain": explain,
        "subscript_tokens": sorted(t for t in tokens if any(ch.isdigit() for ch in t) or "^" in t),
    }


def _generate_balancing(seed, count, data, ctx):
    rng = random.Random(seed)
    # the subscript-mutation trap is the highest-value teaching moment (brief §13.3), so guarantee every
    # trapped reaction is selected: draw trapped reactions first, then fill from the rest. The final display
    # order is shuffled so the trap problems aren't always up front.
    trapped = [i for i, r in enumerate(_REACTIONS) if "trap" in r]
    others = [i for i, r in enumerate(_REACTIONS) if "trap" not in r]
    rng.shuffle(trapped)
    rng.shuffle(others)

    selected: list[dict] = []
    seen: set = set()
    for idx in trapped + others:
        if len(selected) >= count:
            break
        q = _balancing_problem(_REACTIONS[idx], rng, ctx)
        if q is None or q["prompt"] in seen:
            continue
        seen.add(q["prompt"])
        selected.append(q)
    if len(selected) < count:
        raise BuildError(f"{ctx}: balancing gym could not generate {count} problems at seed {seed} "
                         f"(corpus has {len(_REACTIONS)})")

    rng.shuffle(selected)
    for i, q in enumerate(selected):
        q["id"] = f"q{i + 1}"
    return selected


# ------------------------------ stoichiometry (item 4, ADR-0029) ------------------------------

# Mass stoichiometry reuses the balancing corpus's *neutral* reactions (every species' molar mass resolves
# from data/). Problems are generated FORWARD from a clean mole amount (like the conversion gym): pick moles
# of the given species, so mass = moles × M is an exact terminating decimal; carry it across the mole ratio
# (from the engine's balance) and back to a mass, rejecting any non-terminating candidate. The dimensional
# chain (mass → mol → mol → mass) is the same units-cancellation the conversion gym proves.
_STOICH_MOLES = [Decimal(n) for n in ("0.0500", "0.100", "0.150", "0.200", "0.250", "0.500", "1.00", "2.00")]
_PERCENTS = [Decimal(p) for p in ("55", "60", "65", "70", "75", "80", "85", "90", "92", "95")]


def _neutral_reactions():
    """Balancing-corpus reactions with no charged species — chempy-checkable and molar-mass-resolvable."""
    return [r for r in _REACTIONS if not any("^" in f for f in r["reactants"] + r["products"])]


def _stoich_forward(species, coeffs, gi, ti, moles_given, data):
    """Carry moles_given from species[gi] to species[ti] across the balanced equation. None if non-terminating."""
    Mg, Mt = data.molar_mass(species[gi]["formula"]), data.molar_mass(species[ti]["formula"])
    ratio = Fraction(coeffs[ti], coeffs[gi])
    moles_target = moles_given * ratio
    mass_given, mass_target = moles_given * _fr(Mg), moles_target * _fr(Mt)
    if not (_terminates(mass_given) and _terminates(moles_target) and _terminates(mass_target)):
        return None
    return {"Mg": Mg, "Mt": Mt, "ratio": ratio, "moles_target": moles_target,
            "mass_given": mass_given, "mass_target": mass_target}


def _rel_close(a: float, b: float, tol: float) -> bool:
    return abs(a - b) <= tol * max(abs(b), 1e-9) + 1e-12


def _numeric_response(answer, unit, wrongs):
    """Free-entry diagnostics for a numeric answer (ADR-0032). A numeric answer is NOT offered as a menu — a
    human eliminates a distractor like 0.55 % or a 1000×-too-large mass on sight, so the menu drills nothing.
    Instead the learner PRODUCES the number, and these named-mistake *values* diagnose what they typed: if the
    entry matches a mistake, the mistake is named. That turns the very values that made lazy distractors —
    forgot ×100, skipped mL→L — into precise feedback. Drops any candidate within 0.5 % of the answer (so a
    correct entry is never mis-flagged as a mistake) and any duplicate display.

    Returns (display, diagnostics): the exact answer display + a list of {value, unit, misconception}."""
    correct = _disp(answer, unit)
    ans = float(answer)
    diags, seen = [], set()
    for val, why in wrongs:
        try:
            fval = float(val)
        except (ZeroDivisionError, ValueError):
            continue
        if fval != fval or _rel_close(fval, ans, 0.035):    # NaN, or too near the answer to diagnose safely
            continue
        key = _sig(val, 4)
        if key in seen:
            continue
        seen.add(key)
        diags.append({"value": _sig(val, 6), "unit": unit, "misconception": why})
    return correct, diags


def _stoich_derivation(kind, species, coeffs, gi, ti, s, extra=None):
    """The emitted derivation: the full equation (so the gate re-verifies the balance) + given/target facts."""
    d = {
        "kind": kind,
        "species": species,
        "coefficients": list(coeffs),
        "given": {"index": gi, "formula": species[gi]["formula"], "coeff": coeffs[gi],
                  "molar_mass_g_per_mol": _trim(str(s["Mg"])), "mass_g": _trim(_exact(s["mass_given"]))},
        "target": {"index": ti, "formula": species[ti]["formula"], "coeff": coeffs[ti],
                   "molar_mass_g_per_mol": _trim(str(s["Mt"]))},
    }
    if extra:
        d.update(extra)
    return d


def _mass_stoich_problem(reaction, rng, data, ctx):
    r_forms, p_forms, species = _species_of(reaction["reactants"], reaction["products"], ctx)
    coeffs = balance(r_forms, p_forms, ctx)
    reactant_idx = [i for i, sp in enumerate(species) if sp["role"] == "reactant"]
    gi = rng.choice(reactant_idx)
    ti = rng.choice([j for j in range(len(species)) if j != gi])
    s = _stoich_forward(species, coeffs, gi, ti, _fr(rng.choice(_STOICH_MOLES)), data)
    if s is None:
        return None

    given_f, target_f = species[gi]["formula"], species[ti]["formula"]
    cg, ct = coeffs[gi], coeffs[ti]
    eq, mg = _eq_str(species, coeffs), _trim(_exact(s["mass_given"]))
    verb = "are produced from" if species[ti]["role"] == "product" else "react with"
    prompt = f"For {eq}: how many grams of {target_f} {verb} {mg} g of {given_f}?"
    chain = [
        {"value": mg, "unit": "g", "note": f"mass of {given_f}"},
        {"value": _trim(_exact(s["mass_given"] / _fr(s["Mg"]))), "unit": "mol",
         "note": f"÷ {_trim(str(s['Mg']))} g/mol"},
        {"value": _trim(_exact(s["moles_target"])), "unit": "mol",
         "note": f"× ({ct} mol {target_f} / {cg} mol {given_f})"},
        {"value": _trim(_exact(s["mass_target"])), "unit": "g", "note": f"× {_trim(str(s['Mt']))} g/mol"},
    ]
    _verify_dims(Quantity.of(mg, "g") / Quantity.of(str(s["Mg"]), "g/mol"), "mol", ctx)
    _verify_dims(Quantity.of(_exact(s["moles_target"]), "mol") * Quantity.of(str(s["Mt"]), "g/mol"), "g", ctx)

    moles_given = s["mass_given"] / _fr(s["Mg"])
    wrongs = [
        (moles_given * Fraction(cg, ct) * _fr(s["Mt"]),
         f"Flipped the mole ratio — read it from given to target: × ({ct} mol {target_f} / {cg} mol {given_f})."),
        (moles_given * _fr(s["Mt"]),
         f"Skipped the mole ratio — the equation says {cg} mol {given_f} : {ct} mol {target_f}, not 1 : 1."),
        (s["mass_given"] * s["ratio"] * _fr(s["Mt"]),
         f"Skipped grams → moles — divide by the molar mass of {given_f} before the mole ratio."),
        (s["moles_target"],
         f"Stopped at moles — multiply by {target_f}'s molar mass to get grams."),
    ]
    correct, diagnostics = _numeric_response(s["mass_target"], "g", wrongs)
    explain = (f"Divide by molar mass, cross the mole ratio, multiply back: {mg} g {given_f} ÷ "
               f"{_trim(str(s['Mg']))} g/mol × ({ct}/{cg}) × {_trim(str(s['Mt']))} g/mol = "
               f"{_trim(_exact(s['mass_target']))} g {target_f}. The recipe is the coefficients of {eq}.")
    return {
        "kind": "mass_stoichiometry", "mode": "numeric", "prompt": prompt, "chain": chain, "target_unit": "g",
        "answer": {"value": _exact(s["mass_target"]), "unit": "g", "display": correct},
        "derivation": _stoich_derivation("mass_stoichiometry", species, coeffs, gi, ti, s),
        "diagnostics": diagnostics, "explain": explain,
        "subscript_tokens": sorted({sp["formula"] for sp in species if any(c.isdigit() for c in sp["formula"])}),
    }


def _percent_yield_problem(reaction, rng, data, ctx):
    r_forms, p_forms, species = _species_of(reaction["reactants"], reaction["products"], ctx)
    coeffs = balance(r_forms, p_forms, ctx)
    reactant_idx = [i for i, sp in enumerate(species) if sp["role"] == "reactant"]
    product_idx = [i for i, sp in enumerate(species) if sp["role"] == "product"]
    gi, ti = rng.choice(reactant_idx), rng.choice(product_idx)
    s = _stoich_forward(species, coeffs, gi, ti, _fr(rng.choice(_STOICH_MOLES)), data)
    if s is None:
        return None
    pct = _fr(rng.choice(_PERCENTS))
    actual = s["mass_target"] * pct / 100
    if not _terminates(actual):
        return None

    given_f, target_f = species[gi]["formula"], species[ti]["formula"]
    eq = _eq_str(species, coeffs)
    mg, theo, act = _trim(_exact(s["mass_given"])), _trim(_exact(s["mass_target"])), _trim(_exact(actual))
    prompt = (f"For {eq}: {mg} g of {given_f} is reacted and {act} g of {target_f} is collected. "
              f"What is the percent yield?")
    chain = [
        {"value": mg, "unit": "g", "note": f"{given_f} reacted"},
        {"value": theo, "unit": "g", "note": "theoretical yield (mass stoichiometry)"},
        {"value": act, "unit": "g", "note": "actual yield (measured)"},
        {"value": _trim(_exact(pct)), "unit": "%", "note": "actual ÷ theoretical × 100"},
    ]
    wrongs = [
        (s["mass_target"] / actual * 100,
         "Divided upside down — percent yield is actual ÷ theoretical, not theoretical ÷ actual."),
        (actual / s["mass_target"],
         "That's the fraction, not the percent — multiply by 100."),
        (actual / s["mass_given"] * 100,
         f"Compared to the {given_f} mass — percent yield uses the *theoretical* {target_f} yield as the denominator."),
    ]
    correct, diagnostics = _numeric_response(pct, "%", wrongs)
    explain = (f"Theoretical yield first: {mg} g {given_f} gives {theo} g {target_f} by stoichiometry. "
               f"Then percent yield = actual ÷ theoretical × 100 = {act} ÷ {theo} × 100 = {_trim(_exact(pct))}%.")
    return {
        "kind": "percent_yield", "mode": "numeric", "prompt": prompt, "chain": chain, "target_unit": "%",
        "answer": {"value": _exact(pct), "unit": "%", "display": correct},
        "derivation": _stoich_derivation("percent_yield", species, coeffs, gi, ti, s,
                                         {"actual_mass_g": _exact(actual),
                                          "theoretical_mass_g": _exact(s["mass_target"])}),
        "diagnostics": diagnostics, "explain": explain,
        "subscript_tokens": sorted({sp["formula"] for sp in species if any(c.isdigit() for c in sp["formula"])}),
    }


def _limiting_mass_problem(reaction, rng, data, ctx):
    """Limiting reagent from two reactant MASSES → the maximum (theoretical) product mass. None to reject."""
    r_forms, p_forms, species = _species_of(reaction["reactants"], reaction["products"], ctx)
    reactant_idx = [i for i, s in enumerate(species) if s["role"] == "reactant"]
    product_idx = [i for i, s in enumerate(species) if s["role"] == "product"]
    if len(reactant_idx) < 2:
        return None
    coeffs = balance(r_forms, p_forms, ctx)
    ia, ib = sorted(rng.sample(reactant_idx, 2))
    ti = rng.choice(product_idx)
    na, nb = _fr(rng.choice(_STOICH_MOLES)), _fr(rng.choice(_STOICH_MOLES))
    xa, xb = na / coeffs[ia], nb / coeffs[ib]                       # reaction extent each reactant can reach
    if xa == xb:
        return None                                                # need an unambiguous limiting reagent
    Ma, Mb, Mt = (data.molar_mass(species[i]["formula"]) for i in (ia, ib, ti))
    mass_a, mass_b = na * _fr(Ma), nb * _fr(Mb)
    x_lim = min(xa, xb)
    prod_mass = x_lim * coeffs[ti] * _fr(Mt)
    if not all(_terminates(v) for v in (mass_a, mass_b, prod_mass)):
        return None

    li, ei = (ia, ib) if xa < xb else (ib, ia)                     # limiting / excess species indices
    lim_f, exc_f, tgt_f = species[li]["formula"], species[ei]["formula"], species[ti]["formula"]
    x_exc = max(xa, xb)
    lim_moles = na if li == ia else nb
    eq = _eq_str(species, coeffs)
    ma, mb = _trim(_exact(mass_a)), _trim(_exact(mass_b))
    prompt = (f"For {eq}: {ma} g of {species[ia]['formula']} is mixed with {mb} g of "
              f"{species[ib]['formula']}. What is the maximum mass of {tgt_f} that can form?")
    chain = [
        {"value": _trim(_exact(mass_a if li == ia else mass_b)), "unit": "g", "note": f"{lim_f} (the limiting reagent)"},
        {"value": _trim(_exact(lim_moles)), "unit": "mol", "note": f"÷ {_trim(str(Ma if li == ia else Mb))} g/mol"},
        {"value": _trim(_exact(x_lim * coeffs[ti])), "unit": "mol",
         "note": f"× ({coeffs[ti]} mol {tgt_f} / {coeffs[li]} mol {lim_f})"},
        {"value": _trim(_exact(prod_mass)), "unit": "g", "note": f"× {_trim(str(Mt))} g/mol"},
    ]
    _verify_dims(Quantity.of(_trim(_exact(prod_mass)), "g"), "g", ctx)
    wrongs = [
        (x_exc * coeffs[ti] * _fr(Mt),
         f"Used {exc_f} to size the yield, but it is in EXCESS — the limiting reagent {lim_f} (smaller "
         f"moles ÷ coefficient) sets how much {tgt_f} forms."),
        (lim_moles * coeffs[ti] * _fr(Mt),
         f"Skipped {lim_f}'s coefficient — divide its moles by {coeffs[li]} to get the reaction extent first."),
        ((xa + xb) * coeffs[ti] * _fr(Mt),
         "Added both reactants' capacities — only the limiting reagent's extent counts, not the sum."),
    ]
    correct, diagnostics = _numeric_response(prod_mass, "g", wrongs)
    explain = (f"Compare reaction extents: {species[ia]['formula']} gives {_trim(_exact(xa))} mol, "
               f"{species[ib]['formula']} gives {_trim(_exact(xb))} mol — {lim_f} is smaller, so it limits. "
               f"Its extent × {coeffs[ti]} × {_trim(str(Mt))} g/mol = {_trim(_exact(prod_mass))} g {tgt_f}.")
    return {
        "kind": "limiting_mass", "mode": "numeric", "prompt": prompt, "chain": chain, "target_unit": "g",
        "answer": {"value": _exact(prod_mass), "unit": "g", "display": correct},
        "derivation": {
            "kind": "limiting_mass", "species": species, "coefficients": list(coeffs),
            "reactants": [
                {"index": ia, "formula": species[ia]["formula"], "coeff": coeffs[ia],
                 "molar_mass_g_per_mol": _trim(str(Ma)), "mass_g": ma},
                {"index": ib, "formula": species[ib]["formula"], "coeff": coeffs[ib],
                 "molar_mass_g_per_mol": _trim(str(Mb)), "mass_g": mb},
            ],
            "target": {"index": ti, "formula": tgt_f, "coeff": coeffs[ti], "molar_mass_g_per_mol": _trim(str(Mt))},
            "limiting_index": li,
        },
        "diagnostics": diagnostics, "explain": explain,
        "subscript_tokens": sorted({s["formula"] for s in species if any(c.isdigit() for c in s["formula"])}),
    }


def _rotating_generator(problem_fn):
    """Shared driver for the stoichiometry families: rotate reactions, reject/dedupe, require `count`."""
    def generate(seed, count, data, ctx):
        rng = random.Random(seed)
        reactions = _neutral_reactions()
        problems: list[dict] = []
        seen: set = set()
        attempts = 0
        while len(problems) < count and attempts < 8000:
            attempts += 1
            q = problem_fn(rng.choice(reactions), rng, data, ctx)
            if q is None or q["prompt"] in seen:
                continue
            seen.add(q["prompt"])
            q["id"] = f"q{len(problems) + 1}"
            problems.append(q)
        if len(problems) < count:
            raise BuildError(f"{ctx}: stoichiometry gym could not generate {count} problems at seed {seed}")
        return problems
    return generate


# ------------------------------ periodic trends (item 5b, ADR-0034) ------------------------------

# The practice mode of the Valence-Table flagship (brief §8.5): drills generated from the SAME curated data
# the table renders — sourced properties compared/ordered/predicted, never the naive trend rule. Where the
# data contradicts the left-to-right story (the B/Be and O/N ionization dips), the data wins and the
# explanation names the exception. All three kinds are categorical menus (ADR-0032): an element, an ion, or
# an ordering is a plausible same-form choice. validate-gyms.mjs re-compares/re-sorts every value in pure
# Node and cross-checks each against the committed valence-table.json (one source of truth, ADR-0034).

_TREND_PROPS = {
    "covalent_radius_pm": {"label": "covalent radius", "unit": "pm", "hi": "largest", "lo": "smallest",
                           "period": "Across a period the growing nuclear charge pulls the same shells in "
                                     "tighter, so atoms shrink left → right.",
                           "group": "Down a group each row adds a whole shell, so atoms grow top → bottom."},
    "first_ionization_kj_mol": {"label": "first ionization energy", "unit": "kJ/mol", "hi": "highest", "lo": "lowest",
                                "period": "Ionization energy climbs left → right across a period — same "
                                          "shell, more nuclear pull — though the s→p and p-pairing dips "
                                          "break the climb.",
                                "group": "Ionization energy falls down a group — the outer electron sits "
                                         "farther out and better screened."},
    "electronegativity": {"label": "electronegativity", "unit": "", "hi": "highest", "lo": "lowest",
                          "period": "Electronegativity rises left → right across a period.",
                          "group": "Electronegativity falls down a group."},
}


def _with_unit(value, unit: str) -> str:
    return f"{value} {unit}".strip()


def _trend_series(data, prop):
    """Same-period rows and same-group columns with ≥3 main-group members holding `prop`. H is excluded
    (its group-1 placement is conventional, not alkali chemistry); the d-block is excluded (partial period 4
    would put a hole in the middle of an 'across the period' story)."""
    members = [el for el in data.elements.values()
               if el.block in ("s", "p") and el.symbol != "H" and getattr(el, prop) is not None]
    series = []
    for kind, of, order in (("period", lambda e: e.period, lambda e: e.group),
                            ("group", lambda e: e.group, lambda e: e.period)):
        rows: dict = {}
        for el in members:
            rows.setdefault(of(el), []).append(el)
        for n, els in sorted(rows.items()):
            if len(els) >= 3:
                series.append({"kind": kind, "n": n, "members": sorted(els, key=order)})
    return series


def _trend_compare_problem(rng, data, ctx):
    """Which of three same-series elements has the largest/smallest property — answered from the data."""
    prop = rng.choice(sorted(_TREND_PROPS))
    meta = _TREND_PROPS[prop]
    series = _trend_series(data, prop)
    if not series:
        return None
    s = rng.choice(series)
    trio = sorted(rng.sample(s["members"], 3), key=lambda e: e.group if s["kind"] == "period" else e.period)
    direction = rng.choice(("max", "min"))
    values = [getattr(el, prop) for el in trio]
    extreme = max(values) if direction == "max" else min(values)
    if values.count(extreme) != 1:
        return None                                        # tied extreme — no unambiguous answer
    ans = trio[values.index(extreme)]
    adjective = meta["hi"] if direction == "max" else meta["lo"]
    where = f"period {s['n']}" if s["kind"] == "period" else f"group {s['n']}"
    names = ", ".join(el.symbol for el in trio)
    prompt = f"Which of {names} — all in {where} — has the {adjective} {meta['label']}?"
    trend_note = meta[s["kind"]]

    choices = []
    for el in trio:
        if el is ans:
            choices.insert(0, {"display": f"{el.symbol} ({el.name})", "correct": True, "misconception": None})
        else:
            why = (f"{el.symbol} is {_with_unit(getattr(el, prop), meta['unit'])}; {ans.symbol} is "
                   f"{_with_unit(extreme, meta['unit'])}. {trend_note}")
            choices.append({"display": f"{el.symbol} ({el.name})", "correct": False, "misconception": why})

    ranked = sorted(trio, key=lambda e: getattr(e, prop))
    data_line = " < ".join(f"{el.symbol} ({_with_unit(getattr(el, prop), meta['unit'])})" for el in ranked)
    # honesty note: when the extreme is not where the naive position rule puts it. IE/EN rise across a period
    # and fall down a group; radius does the opposite — so the property "rises with position" exactly when the
    # series kind and the radius-ness disagree.
    rises = (s["kind"] == "period") != (prop == "covalent_radius_pm")
    naive_extreme = trio[-1] if (direction == "max") == rises else trio[0]
    exception = "" if naive_extreme is ans else (
        f" That breaks the naive position rule — the curated data is the authority, and here "
        f"{ans.symbol} beats {naive_extreme.symbol}.")
    explain = f"The data decides: {data_line}. {trend_note}{exception}"

    return {
        "kind": "trend_compare", "mode": "choice", "prompt": prompt,
        "answer": {"value": ans.symbol, "display": f"{ans.symbol} ({ans.name})"},
        "derivation": {
            "kind": "trend_compare", "property": prop, "direction": direction,
            "series": {"kind": s["kind"], "n": s["n"]},
            "candidates": [{"symbol": el.symbol, "value": str(getattr(el, prop))} for el in trio],
        },
        "choices": choices, "explain": explain,
    }


def _ion_id(symbol: str, charge: int) -> str:
    """House caret form (house-conventions §Notation): Na^+, Ca^2+, S^2-."""
    sign = "+" if charge > 0 else "-"
    mag = abs(charge)
    return f"{symbol}^{sign}" if mag == 1 else f"{symbol}^{mag}{sign}"


def _predict_ion_problem(rng, data, common, ctx):
    """Predict the common monatomic ion for a fixed-charge main-group element (the sourced charge is the
    answer; distractors are the sign flip and the miscounted charge)."""
    pool = []
    for sym, ion in sorted(common.items()):
        el = data.elements[sym]
        if el.block not in ("s", "p") or sym == "H":
            continue
        if sum(1 for i in data.ions.values() if i.element == sym and i.kind == "monatomic") > 1:
            continue                                       # variable-charge — "the" common ion is ambiguous
        pool.append((el, ion))
    if not pool:
        return None
    el, ion = rng.choice(pool)
    ve = el.group if el.group <= 2 else el.group - 10
    c = ion.charge

    flip = _ion_id(el.symbol, -c)
    if c > 0:
        flip_why = f"{el.name.capitalize()} is a metal — it LOSES electrons, forming a cation (+), not an anion."
        wrong_charge = c + 1 if c == 1 else c - 1
        miscount = _ion_id(el.symbol, wrong_charge)
        miscount_why = (f"Miscounted the valence electrons — {el.name} (group {el.group}) has {ve}; it loses "
                        f"all {ve}, so the charge is +{ve}.")
        story = f"loses all {ve}, leaving a full inner shell — charge +{c}"
    else:
        flip_why = f"{el.name.capitalize()} is a nonmetal — it GAINS electrons, forming an anion (−), not a cation."
        miscount = _ion_id(el.symbol, -ve)
        miscount_why = (f"The charge counts electrons GAINED to reach eight, not the {ve} already there — "
                        f"{el.name} gains 8 − {ve} = {8 - ve}.")
        story = f"gains 8 − {ve} = {8 - ve} to fill the shell — charge −{abs(c)}"

    choices = [{"display": ion.id, "correct": True, "misconception": None}]
    seen = {ion.id}
    for disp, why in ((flip, flip_why), (miscount, miscount_why)):
        if disp in seen:
            return None
        seen.add(disp)
        choices.append({"display": disp, "correct": False, "misconception": why})

    explain = (f"{el.name.capitalize()} sits in group {el.group} with {ve} valence electrons — it {story}. "
               f"The charge is sourced data, and the pattern explains it.")
    return {
        "kind": "predict_ion", "mode": "choice",
        "prompt": f"Predict the common ion for {el.name} ({el.symbol}).",
        "answer": {"value": ion.id, "display": ion.id},
        "derivation": {"kind": "predict_ion", "element": el.symbol,
                       "ion": {"id": ion.id, "charge": ion.charge}},
        "choices": choices, "explain": explain,
        "subscript_tokens": sorted(seen),
    }


def _order_ionization_problem(rng, data, ctx):
    """Order three same-period elements by increasing first ionization energy — the data decides, and where
    it disagrees with the left-to-right rule, the naive order itself becomes the named distractor."""
    prop = "first_ionization_kj_mol"
    series = [s for s in _trend_series(data, prop) if s["kind"] == "period"]
    if not series:
        return None
    s = rng.choice(series)
    trio = rng.sample(s["members"], 3)
    values = {el.symbol: getattr(el, prop) for el in trio}
    if len(set(values.values())) != 3:
        return None
    ascending = sorted(trio, key=lambda e: values[e.symbol])
    naive = sorted(trio, key=lambda e: e.group)
    disp = lambda seq: " < ".join(el.symbol for el in seq)

    prompt_order = list(trio)
    rng.shuffle(prompt_order)                              # the prompt must not leak either ordering
    prompt = (f"Order by FIRST IONIZATION ENERGY, lowest → highest: "
              f"{', '.join(el.symbol for el in prompt_order)} (all in period {s['n']}).")

    choices = [{"display": disp(ascending), "correct": True, "misconception": None}]
    seen = {disp(ascending)}
    wrongs: list[tuple[str, str]] = []
    if disp(naive) != disp(ascending):
        # the naive order disagrees with the data, so some adjacent pair in it must run downhill — the dip
        a, b = next((x, y) for x, y in zip(naive, naive[1:]) if values[x.symbol] > values[y.symbol])
        wrongs.append((disp(naive),
                       f"That is the left-to-right rule — but the data dips: {b.symbol} "
                       f"({values[b.symbol]} kJ/mol) sits BELOW {a.symbol} ({values[a.symbol]} kJ/mol). "
                       f"The trend is a guide; the measured values decide."))
    wrongs.append((disp(list(reversed(ascending))),
                   "Reversed — ionization energy generally RISES across a period, so this is the "
                   "decreasing order."))
    if len(wrongs) < 2:
        mid = [ascending[1], ascending[0], ascending[2]]   # swap the two lowest — a checkable near-miss
        a, b = ascending[0], ascending[1]
        wrongs.append((disp(mid),
                       f"Check the data: {a.symbol} is {values[a.symbol]} kJ/mol and {b.symbol} is "
                       f"{values[b.symbol]} — {a.symbol} comes first."))
    for d, why in wrongs[:2]:
        if d in seen:
            return None
        seen.add(d)
        choices.append({"display": d, "correct": False, "misconception": why})
    if len(choices) != 3:
        return None

    data_line = " < ".join(f"{el.symbol} ({values[el.symbol]} kJ/mol)" for el in ascending)
    exception = "" if disp(naive) == disp(ascending) else (
        " Note the dip — an exception the naive rule can't see; the curated data is the authority.")
    explain = f"The data: {data_line}. Ionization energy climbs across period {s['n']} overall.{exception}"

    return {
        "kind": "order_ionization", "mode": "choice", "prompt": prompt,
        "answer": {"value": ",".join(el.symbol for el in ascending), "display": disp(ascending)},
        "derivation": {
            "kind": "order_ionization", "property": prop,
            "series": {"kind": "period", "n": s["n"]},
            "candidates": [{"symbol": el.symbol, "value": str(values[el.symbol])} for el in prompt_order],
        },
        "choices": choices, "explain": explain,
    }


_TREND_KINDS = ["trend_compare", "predict_ion", "order_ionization"]


def _generate_trends(seed, count, data, ctx):
    from .reference import common_monatomic_ions           # deferred: reference lazily imports nomenclature
    common = common_monatomic_ions(data)
    rng = random.Random(seed)
    problems: list[dict] = []
    seen: set = set()
    attempts = 0
    while len(problems) < count and attempts < 8000:
        attempts += 1
        kind = _TREND_KINDS[len(problems) % len(_TREND_KINDS)]
        if kind == "trend_compare":
            q = _trend_compare_problem(rng, data, ctx)
        elif kind == "predict_ion":
            q = _predict_ion_problem(rng, data, common, ctx)
        else:
            q = _order_ionization_problem(rng, data, ctx)
        if q is None or (q["kind"], q["prompt"]) in seen:
            continue
        seen.add((q["kind"], q["prompt"]))
        q["id"] = f"q{len(problems) + 1}"
        problems.append(q)
    if len(problems) < count:
        raise BuildError(f"{ctx}: periodic-trends gym could not generate {count} problems at seed {seed}")
    return problems


# ------------------------------ reaction families (item 6, ADR-0035/0036) ------------------------------

# A curated corpus of phased reactions spanning the first-course families — the same reactions the Atlas
# ships (reference/reactions/*.toml). Each is balanced + classified BY THE ENGINE at generation time, so the
# gym never trusts an authored label; classify_reaction is the single source of truth (ADR-0035).
_FAMILY_REACTIONS = [
    {"reactants": ["CH4(g)", "O2(g)"], "products": ["CO2(g)", "H2O(g)"]},
    {"reactants": ["C3H8(g)", "O2(g)"], "products": ["CO2(g)", "H2O(g)"]},
    {"reactants": ["N2(g)", "H2(g)"], "products": ["NH3(g)"]},
    {"reactants": ["Na(s)", "Cl2(g)"], "products": ["NaCl(s)"]},
    {"reactants": ["KClO3(s)"], "products": ["KCl(s)", "O2(g)"]},
    {"reactants": ["CaCO3(s)"], "products": ["CaO(s)", "CO2(g)"]},
    {"reactants": ["Zn(s)", "HCl(aq)"], "products": ["ZnCl2(aq)", "H2(g)"]},
    {"reactants": ["Fe(s)", "CuSO4(aq)"], "products": ["FeSO4(aq)", "Cu(s)"]},
    {"reactants": ["CaCl2(aq)", "Na2CO3(aq)"], "products": ["CaCO3(s)", "NaCl(aq)"]},
    {"reactants": ["MgCl2(aq)", "NaOH(aq)"], "products": ["Mg(OH)2(s)", "NaCl(aq)"]},
    {"reactants": ["HCl(aq)", "NaOH(aq)"], "products": ["NaCl(aq)", "H2O(l)"]},
    {"reactants": ["H2SO4(aq)", "NaOH(aq)"], "products": ["Na2SO4(aq)", "H2O(l)"]},
    {"reactants": ["HCl(aq)", "Na2CO3(aq)"], "products": ["NaCl(aq)", "H2O(l)", "CO2(g)"]},
    {"reactants": ["NH4Cl(aq)", "NaOH(aq)"], "products": ["NaCl(aq)", "NH3(g)", "H2O(l)"]},
]

_FAMILY_LABEL = {
    "combustion": "Combustion",
    "synthesis": "Synthesis (combination)",
    "decomposition": "Decomposition",
    "single-replacement": "Single replacement",
    "double-replacement": "Double replacement",
    "precipitation": "Precipitation",
    "acid-base": "Acid-base neutralization",
    "gas-evolution": "Gas evolution",
}
# a definitional (always-true) description of each family — used as a wrong choice's misconception so the gym
# never makes a false claim about the specific reaction, only states what the wrong family would require.
_FAMILY_DEF = {
    "combustion": "Combustion is a fuel burning in O2 to give carbon dioxide and water.",
    "synthesis": "A synthesis combines two or more reactants into a single product.",
    "decomposition": "A decomposition breaks a single compound into two or more products.",
    "single-replacement": "Single replacement has a free element trade places with one inside a compound.",
    "precipitation": "Precipitation forms an insoluble solid that drops out of two solutions.",
    "acid-base": "Acid-base neutralization combines an acid and a base into a salt and water.",
    "gas-evolution": "Gas evolution forms a product that decomposes and releases a gas.",
}


def _load_reactivity(data, root_ctx):
    """Load the sourced datasets the classifier needs, validating them (regime-1 composition check)."""
    from pathlib import Path
    from .reactivity import AcidBase, Decomposition
    from .solubility import Solubility
    root = Path.cwd()
    solub = Solubility.load(root)
    ab = AcidBase.load(root)
    ab.validate(data)
    dec = Decomposition.load(root)
    dec.validate(data)
    return solub, ab, dec


def _fam_species(reaction, ctx):
    r_forms, p_forms, species = _species_of(reaction["reactants"], reaction["products"], ctx)
    coeffs = balance(r_forms, p_forms, ctx)
    return r_forms, p_forms, species, coeffs


def _fam_tokens(species, extra=()):
    """Phase-stripped formula tokens for the view (ADR-0025). Cores (H2, ZnCl2) still match inside the phased
    prompt text ('H2(g)'), and they match the phase-stripped cores the classifier's evidence prose uses."""
    cores = {re.sub(r"\((?:s|l|g|aq)\)$", "", s["formula"]) for s in species}
    toks = {t for t in cores if any(c.isdigit() for c in t) or "^" in t}
    return sorted(toks | set(extra))


def _classify_family_problem(reaction, rng, data, rx, ctx):
    from .reaction import classify_reaction
    solub, ab, dec = rx
    r_forms, p_forms, species, coeffs = _fam_species(reaction, ctx)
    cls = classify_reaction(r_forms, p_forms, data, solubility=solub, acidbase=ab, decomposition=dec, ctx=ctx)
    fam = cls["family"]
    prompt = "Classify this reaction:  " + _eq_str(species, coeffs)
    # distractors: other specific families (never the parent 'double-replacement', which a sub-type also is)
    pool = [k for k in _FAMILY_LABEL if k not in (fam, "double-replacement")]
    rng.shuffle(pool)
    choices = [{"display": _FAMILY_LABEL[fam], "correct": True, "misconception": None}]
    for k in pool[:2]:
        choices.append({"display": _FAMILY_LABEL[k], "correct": False, "misconception": _FAMILY_DEF[k]})
    explain = f"{_FAMILY_LABEL[fam]}. {cls['evidence']}"
    if cls.get("redox_reason"):
        explain += f" {cls['redox_reason']}"
    tokens = _fam_tokens(species)
    return {
        "kind": "classify_family", "mode": "choice", "prompt": prompt,
        "answer": {"value": fam, "display": _FAMILY_LABEL[fam]},
        "derivation": {"kind": "classify_family", "species": species, "coefficients": list(coeffs), "family": fam},
        "choices": choices, "explain": explain, "subscript_tokens": tokens,
    }


def _ion_list(ids):
    """A readable ion set for a choice display (ASCII caret ids; the view prettifies)."""
    return ", ".join(ids)


def _name_spectators_problem(reaction, rng, data, rx, ctx):
    from .reaction import complete_ionic, net_ionic
    r_forms, p_forms, species, coeffs = _fam_species(reaction, ctx)
    try:
        left, right = complete_ionic(r_forms, p_forms, coeffs, data, ctx)
        net_left, net_right, spectators = net_ionic(left, right, ctx)
    except BuildError:
        return None
    if len(spectators) < 1:
        return None
    # the net equation as species + coefficients (for the gate to re-verify it balances), and the ions that
    # actually react (charged net species) for building honest distractors
    def _net_row(sid, role):
        f = parse_formula(sid)
        return {"formula": sid, "role": role, "counts": dict(f.counts), "charge": f.charge}
    net_species = ([_net_row(sid, "reactant") for (sid, _ph) in net_left]
                   + [_net_row(sid, "product") for (sid, _ph) in net_right])
    net_coeffs = list(net_left.values()) + list(net_right.values())
    participating_ions = sorted({sid for (sid, _ph) in list(net_left) + list(net_right)
                                 if parse_formula(sid).charge != 0})
    if not participating_ions:
        return None                                            # nothing to build an over-inclusion distractor
    spectators = sorted(spectators)
    correct = _ion_list(spectators)
    seen = {correct}
    choices = [{"display": correct, "correct": True, "misconception": None}]
    # distractor A: spectators + one reacting ion (over-inclusion)
    intruder = participating_ions[0]
    over = _ion_list(sorted(spectators + [intruder]))
    if over not in seen:
        seen.add(over)
        choices.append({"display": over, "correct": False,
                        "misconception": f"{intruder} is not a spectator — it changes and appears in the net "
                                         f"ionic equation."})
    # distractor B: the reacting ions themselves (the opposite of spectators)
    react = _ion_list(participating_ions)
    if react not in seen:
        seen.add(react)
        choices.append({"display": react, "correct": False,
                        "misconception": "Those are the ions that react (the net ionic equation) — the "
                                         "spectators are the ones that stay unchanged."})
    if len(choices) < 3:
        return None
    eq = _eq_str(species, coeffs)
    prompt = f"Which ions are spectators (unchanged on both sides) in:  {eq}?"
    explain = (f"Spectators: {correct}. They appear unchanged on both sides of the complete ionic equation, "
               f"so they cancel — leaving the net ionic equation with only {_ion_list(participating_ions)}.")
    tokens = _fam_tokens(species, extra=set(spectators) | set(participating_ions))
    return {
        "kind": "name_spectators", "mode": "choice", "prompt": prompt,
        "answer": {"value": ",".join(spectators), "display": correct},
        "derivation": {"kind": "name_spectators", "species": species, "coefficients": list(coeffs),
                       "net_species": net_species, "net_coefficients": net_coeffs, "spectators": spectators},
        "choices": choices, "explain": explain, "subscript_tokens": tokens,
    }


_FAMILY_KINDS = ["classify_family", "name_spectators"]


def _generate_reaction_families(seed, count, data, ctx):
    rx = _load_reactivity(data, ctx)
    rng = random.Random(seed)
    problems: list[dict] = []
    seen: set = set()
    order = list(range(len(_FAMILY_REACTIONS)))
    attempts = 0
    while len(problems) < count and attempts < 8000:
        attempts += 1
        kind = _FAMILY_KINDS[len(problems) % len(_FAMILY_KINDS)]
        reaction = _FAMILY_REACTIONS[rng.choice(order)]
        if kind == "classify_family":
            q = _classify_family_problem(reaction, rng, data, rx, ctx)
        else:
            q = _name_spectators_problem(reaction, rng, data, rx, ctx)
        if q is None or (q["kind"], q["prompt"]) in seen:
            continue
        seen.add((q["kind"], q["prompt"]))
        q["id"] = f"q{len(problems) + 1}"
        problems.append(q)
    if len(problems) < count:
        raise BuildError(f"{ctx}: reaction-families gym could not generate {count} problems at seed {seed}")
    return problems


_FAMILIES = {
    "solution_conversions_v1": _generate_conversions,
    "ionic_nomenclature_v1": _generate_nomenclature,
    "balancing_v1": _generate_balancing,
    "mass_stoichiometry_v1": _rotating_generator(_mass_stoich_problem),
    "percent_yield_v1": _rotating_generator(_percent_yield_problem),
    "limiting_mass_v1": _rotating_generator(_limiting_mass_problem),
    "periodic_trends_v1": _generate_trends,
    "reaction_families_v1": _generate_reaction_families,
}


def generate_gym(spec: dict, data, ctx: str = "") -> dict:
    """Build a verified gym problem set from an authored spec (deterministic in `seed`)."""
    family = spec.get("family")
    generator = _FAMILIES.get(family)
    if generator is None:
        raise BuildError(f"{ctx}: unknown gym family '{family}'")
    seed, count = int(spec["seed"]), int(spec.get("count", 8))
    problems = generator(seed, count, data, ctx)

    # provenance: every family rests on the sourced atomic weights; the periodic-trends family additionally
    # embeds the sourced properties/charges it drills (ADR-0034), so their register ids travel with the gym.
    sources = {"atomic_weight": data.sources.get("atomic_weight", "")}
    if family == "periodic_trends_v1":
        for key in ("position", "ion_charge", "electronegativity", "covalent_radius", "ionization_energy"):
            sources[key] = data.sources.get(key, "")
    if family == "reaction_families_v1":
        # the family labels + spectator determination rest on the sourced classification data (solubility
        # rules, acid/base + decomposition tables — all openstax-chemistry-2e, via the ion-charge source key)
        sources["ion_charge"] = data.sources.get("ion_charge", "")
        sources["reaction_classes"] = data.sources.get("ion_charge", "")

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
            "sources": sources,
        },
    }
