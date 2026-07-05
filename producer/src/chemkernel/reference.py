"""Chemical Atlas builder: the Valence Table (periodic lens) + authored concept entries (brief §10, §16).

Two emitted shapes under derived/reference/:
  - `valence-table.json` — a projection of data/ (elements in their IUPAC positions + the sourced ion
    charges) plus **machine-verified charge-balance examples**: the neutral formula of a cation+anion pair is
    assembled by charge crossover and re-checked for neutrality, so "CaCO3 follows from charge balance" is
    derived, not asserted (regime-1 assembly over regime-3 charges).
  - `<slug>.json` — an authored concept entry (`reference/**/*.toml`): term, definition, related edges
    (the concept graph), and the lessons it appears in.

Nothing here is hard-coded chemistry: elements and charges come from ChemData, formulas are assembled by
crossover and verified with the parser.
"""

from __future__ import annotations

import re
from math import gcd

from . import BuildError
from .formula import parse_formula

_MONATOMIC = re.compile(r"^[A-Z][a-z]?$")


def _group_str(formula: str, n: int) -> str:
    """One ion's contribution to an assembled formula: subscript if n>1, parenthesised if polyatomic."""
    if n == 1:
        return formula
    return f"{formula}{n}" if _MONATOMIC.match(formula) else f"({formula}){n}"


def assemble_formula(cation, anion, ctx: str = "") -> tuple[str, int, int]:
    """Neutral formula of a cation+anion pair by charge crossover; verified neutral. Returns (formula, n_cat, n_an)."""
    c, a = cation.charge, -anion.charge  # both positive magnitudes
    if c <= 0 or a <= 0:
        raise BuildError(f"{ctx}: assemble_formula needs a positive cation and negative anion")
    g = gcd(c, a)
    n_cat, n_an = a // g, c // g
    formula = _group_str(cation.formula, n_cat) + _group_str(anion.formula, n_an)
    parsed = parse_formula(formula, ctx=ctx)
    if parsed.charge != 0:
        raise BuildError(f"{ctx}: assembled {formula} is not neutral (charge {parsed.charge})")
    # composition must equal n_cat·cation + n_an·anion
    expect: dict[str, int] = {}
    for src, mult in ((cation.formula, n_cat), (anion.formula, n_an)):
        for el, k in parse_formula(src).counts.items():
            expect[el] = expect.get(el, 0) + k * mult
    if dict(parsed.counts) != expect:
        raise BuildError(f"{ctx}: assembled {formula} composition {dict(parsed.counts)} != {expect}")
    return formula, n_cat, n_an


def build_valence_table(data) -> dict:
    """Emit the Valence Table from data/ — elements in IUPAC positions, sourced ion charges, verified salts."""
    # one common ion per element for the lens; for a variable-charge metal (Fe, Cu) pick the lowest charge
    # deterministically (Fe²⁺, Cu⁺). Showing every oxidation state is an item-5 (flagship) enhancement.
    monatomic_by_element: dict = {}
    for ion in data.ions.values():
        if ion.kind != "monatomic" or not ion.element:
            continue
        cur = monatomic_by_element.get(ion.element)
        if cur is None or (abs(ion.charge), ion.id) < (abs(cur.charge), cur.id):
            monatomic_by_element[ion.element] = ion

    elements = []
    for sym, el in sorted(data.elements.items(), key=lambda kv: kv[1].Z):
        entry = {
            "symbol": sym, "Z": el.Z, "name": el.name, "atomic_weight": str(el.atomic_weight),
            "group": el.group, "period": el.period, "block": el.block,
        }
        # periodic properties (ADR-0031); emitted as strings only where curated (optional — the noble gases
        # carry no electronegativity, the transition metals no covalent radius). The lens badges each source.
        if el.electronegativity is not None:
            entry["electronegativity"] = str(el.electronegativity)
        if el.covalent_radius_pm is not None:
            entry["covalent_radius_pm"] = str(el.covalent_radius_pm)
        if el.first_ionization_kj_mol is not None:
            entry["first_ionization_kj_mol"] = str(el.first_ionization_kj_mol)
        ion = monatomic_by_element.get(sym)
        if ion is not None:
            entry["common_ion"] = {"id": ion.id, "charge": ion.charge, "name": ion.name,
                                   "latex": parse_formula(ion.id).latex}
        elements.append(entry)

    polyatomic = [
        {"id": ion.id, "formula": ion.formula, "charge": ion.charge, "name": ion.name,
         "latex": parse_formula(ion.id).latex}
        for ion in data.ions.values() if ion.kind == "polyatomic"
    ]

    # charge-balance examples: the salts of the two Phase-0 lessons, each assembled + verified from the table.
    # The phosphate pair (charge −3) shows the crossover ratios that make the calcium-phosphate lesson tick.
    pairs = [("Ca^2+", "CO3^2-"), ("Na^+", "CO3^2-"), ("Ca^2+", "Cl^-"), ("Na^+", "Cl^-"),
             ("Ca^2+", "PO4^3-"), ("Na^+", "PO4^3-")]
    charge_balance = []
    for cat_id, an_id in pairs:
        cation, anion = data.ions.get(cat_id), data.ions.get(an_id)
        if cation is None or anion is None:
            continue
        formula, n_cat, n_an = assemble_formula(cation, anion, ctx="valence-table")
        charge_balance.append({
            "cation": cat_id, "anion": an_id, "cation_n": n_cat, "anion_n": n_an,
            "formula": formula, "latex": parse_formula(formula).latex,
            "note": f"{n_cat}×({_sign(cation.charge)}) + {n_an}×({_sign(anion.charge)}) = 0",
        })

    return {
        "kind": "valence-table",
        "id": "valence-table",
        "title": "The Valence Table",
        "blurb": "The periodic table as a charge machine: an element's group sets its common ion charge, and "
                 "a cation and anion combine in whatever ratio makes the compound neutral.",
        "group_charge_note": "Main-group metals lose electrons to a full shell (group 1 → +1, group 2 → +2); "
                             "nonmetals gain them (group 16 → −2, group 17 → −1). Charges below are sourced, "
                             "not inferred — the pattern is a guide, the data is the authority.",
        "highlight": ["Ca", "Na"],
        "elements": elements,
        "polyatomic": polyatomic,
        "charge_balance": charge_balance,
        "sources": {
            "atomic_weight": data.sources.get("atomic_weight", ""),
            "position": data.sources.get("position", ""),
            "ion_charge": data.sources.get("ion_charge", ""),
            "electronegativity": data.sources.get("electronegativity", ""),
            "covalent_radius": data.sources.get("covalent_radius", ""),
            "ionization_energy": data.sources.get("ionization_energy", ""),
        },
    }


def _sign(charge: int) -> str:
    return f"{'+' if charge > 0 else '−'}{abs(charge)}"


def build_reference_entry(spec: dict, ctx: str = "") -> dict:
    """An authored concept entry → the emitted reference object (the term, definition, edges, lessons)."""
    for key in ("id", "kind", "title", "term", "definition"):
        if key not in spec:
            raise BuildError(f"{ctx}: reference entry missing required key '{key}'")
    if spec["kind"] != "concept":
        raise BuildError(f"{ctx}: unknown reference kind '{spec['kind']}'")
    entry = {
        "kind": "concept",
        "id": spec["id"],
        "title": spec["title"],
        "term": spec["term"],
        "definition": spec["definition"],
        "related": spec.get("related", []),
        "lessons": spec.get("lessons", []),
    }
    if "regime" in spec:
        entry["regime"] = spec["regime"]
    if "source" in spec:
        entry["source"] = spec["source"]
    if "latex" in spec:
        entry["latex"] = spec["latex"]
    # a rule-sourced concept must cite where the rule comes from (the honesty model, ADR-0003)
    if entry.get("regime") == "rule-sourced" and "source" not in entry:
        raise BuildError(f"{ctx}: rule-sourced concept '{entry['id']}' needs a `source`")
    return entry
