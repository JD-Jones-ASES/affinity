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


def _numeric_choices(answer, unit, wrongs):
    """Correct (exact) + up to two distinct named-wrong choices (rounded display). None if it can't fill 3."""
    correct = _disp(answer, unit)
    choices = [{"display": correct, "correct": True, "misconception": None}]
    seen = {correct}
    for val, why in wrongs:
        if sum(1 for c in choices if not c["correct"]) >= 2:
            break
        disp = f"{_sig(val)} {unit}"
        if disp in seen:
            continue
        seen.add(disp)
        choices.append({"display": disp, "correct": False, "misconception": why})
    return (choices, correct) if len(choices) == 3 else None


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
    made = _numeric_choices(s["mass_target"], "g", wrongs)
    if made is None:
        return None
    choices, correct = made
    explain = (f"Divide by molar mass, cross the mole ratio, multiply back: {mg} g {given_f} ÷ "
               f"{_trim(str(s['Mg']))} g/mol × ({ct}/{cg}) × {_trim(str(s['Mt']))} g/mol = "
               f"{_trim(_exact(s['mass_target']))} g {target_f}. The recipe is the coefficients of {eq}.")
    return {
        "kind": "mass_stoichiometry", "prompt": prompt, "chain": chain, "target_unit": "g",
        "answer": {"value": _exact(s["mass_target"]), "unit": "g", "display": correct},
        "derivation": _stoich_derivation("mass_stoichiometry", species, coeffs, gi, ti, s),
        "choices": choices, "explain": explain,
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
    made = _numeric_choices(pct, "%", wrongs)
    if made is None:
        return None
    choices, correct = made
    explain = (f"Theoretical yield first: {mg} g {given_f} gives {theo} g {target_f} by stoichiometry. "
               f"Then percent yield = actual ÷ theoretical × 100 = {act} ÷ {theo} × 100 = {_trim(_exact(pct))}%.")
    return {
        "kind": "percent_yield", "prompt": prompt, "chain": chain, "target_unit": "%",
        "answer": {"value": _exact(pct), "unit": "%", "display": correct},
        "derivation": _stoich_derivation("percent_yield", species, coeffs, gi, ti, s,
                                         {"actual_mass_g": _exact(actual),
                                          "theoretical_mass_g": _exact(s["mass_target"])}),
        "choices": choices, "explain": explain,
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
    made = _numeric_choices(prod_mass, "g", wrongs)
    if made is None:
        return None
    choices, correct = made
    explain = (f"Compare reaction extents: {species[ia]['formula']} gives {_trim(_exact(xa))} mol, "
               f"{species[ib]['formula']} gives {_trim(_exact(xb))} mol — {lim_f} is smaller, so it limits. "
               f"Its extent × {coeffs[ti]} × {_trim(str(Mt))} g/mol = {_trim(_exact(prod_mass))} g {tgt_f}.")
    return {
        "kind": "limiting_mass", "prompt": prompt, "chain": chain, "target_unit": "g",
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
        "choices": choices, "explain": explain,
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


_FAMILIES = {
    "solution_conversions_v1": _generate_conversions,
    "ionic_nomenclature_v1": _generate_nomenclature,
    "balancing_v1": _generate_balancing,
    "mass_stoichiometry_v1": _rotating_generator(_mass_stoich_problem),
    "percent_yield_v1": _rotating_generator(_percent_yield_problem),
    "limiting_mass_v1": _rotating_generator(_limiting_mass_problem),
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
