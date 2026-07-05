"""Ionic nomenclature — name ↔ formula, both directions (Phase 1 item 2, ADR-0027).

The authoritative name of an ionic compound is `cation.compound_name + " " + anion.compound_name` — a sourced
naming convention (`data/ions.toml`, regime 3): the element name for a fixed-charge cation (`sodium`), the
element name + Stock Roman numeral for a variable-charge metal (`iron(III)`), and the -ide/-ate name for an
anion (`chloride`, `sulfate`). The *formula* the two ions assemble into is machine-verified by charge
crossover (`reference.assemble_formula`, regime 1). This module is the single source of truth for both
directions; the nomenclature gym and (later) the Valence-Table formula mode call it, and `validate-gyms.mjs`
re-derives the same name and formula independently in Node.

`assemble_with`, `roman`, `greek`, and the variability helpers exist for the gym's distractors — every wrong
choice is a *named* mistake (wrong Stock numeral, charges-as-subscripts, covalent prefixes on an ionic
compound), never a random string.
"""

from __future__ import annotations

import re

from . import BuildError
from .reference import assemble_formula

_MONATOMIC = re.compile(r"^[A-Z][a-z]?$")
_ROMAN = {1: "I", 2: "II", 3: "III", 4: "IV", 5: "V", 6: "VI", 7: "VII"}
_GREEK = {1: "mono", 2: "di", 3: "tri", 4: "tetra", 5: "penta", 6: "hexa"}


def roman(n: int) -> str:
    if n not in _ROMAN:
        raise BuildError(f"no Roman numeral for {n}")
    return _ROMAN[n]


def greek(n: int, drop_mono: bool = True) -> str:
    """Greek multiplying prefix (di-, tri-, …). `mono` is dropped by convention unless asked for."""
    if n not in _GREEK:
        raise BuildError(f"no Greek prefix for {n}")
    return "" if (drop_mono and n == 1) else _GREEK[n]


def name_ionic(cation, anion, ctx: str = "") -> str:
    """Authoritative name of the ionic compound cation+anion (both must carry compound_name)."""
    if cation.charge <= 0 or anion.charge >= 0:
        raise BuildError(f"{ctx}: name_ionic needs a positive cation and a negative anion")
    if not cation.compound_name or not anion.compound_name:
        raise BuildError(f"{ctx}: nomenclature needs compound_name on '{cation.id}' and '{anion.id}'")
    return f"{cation.compound_name} {anion.compound_name}"


def formula_ionic(cation, anion, ctx: str = "") -> tuple[str, int, int]:
    """Neutral formula of cation+anion by verified charge crossover. Returns (formula, n_cat, n_an)."""
    return assemble_formula(cation, anion, ctx=ctx)


def assemble_with(cation, n_cat: int, anion, n_an: int) -> str:
    """Build a formula string with EXPLICIT subscripts (may be chemically wrong) — for gym distractors."""
    def group(part: str, n: int) -> str:
        if n == 1:
            return part
        return f"{part}{n}" if _MONATOMIC.match(part) else f"({part}){n}"
    return group(cation.formula, n_cat) + group(anion.formula, n_an)


def is_variable(cation, ions) -> bool:
    """True if the cation's element carries more than one common positive charge (needs a Stock numeral)."""
    if cation.element is None:
        return False
    return sum(1 for i in ions.values() if i.element == cation.element and i.charge > 0) > 1


def other_charge_names(cation, ions) -> list[str]:
    """compound_names of the element's OTHER positive ions (the wrong-Stock-numeral distractor)."""
    return [i.compound_name for i in ions.values()
            if i.element == cation.element and i.charge > 0 and i.id != cation.id and i.compound_name]


def base_cation_name(cation, data) -> str:
    """The cation's name with no Stock numeral (for the covalent-prefix distractor): the element name."""
    if cation.element and cation.element in data.elements:
        return data.elements[cation.element].name
    return cation.compound_name or cation.id
