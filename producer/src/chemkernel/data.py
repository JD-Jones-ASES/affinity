"""Curated-data loader (ADR-0006, ADR-0012).

The ONLY path from producer logic to empirical constants: atomic weights and ion charges live in
data/*.toml, never hard-coded in code. Values are read as Decimal (never float — ADR-0013) so the
dataset's stated precision survives into molar-mass arithmetic.

On load, ChemData.validate() machine-checks the dataset: every ion formula parses and is composed of
elements that exist in elements.toml, and every monatomic ion agrees with its linked element. So the
*composition* of the ion table is regime-1 verified even though the ion *charges* are regime-3 sourced.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from . import BuildError
from .formula import parse_formula


@dataclass(frozen=True)
class Element:
    symbol: str
    Z: int
    name: str
    atomic_weight: Decimal
    group: int
    period: int
    block: str
    uncertainty: Decimal | None = None


@dataclass(frozen=True)
class Ion:
    id: str
    formula: str
    charge: int
    name: str
    kind: str
    element: str | None = None
    compound_name: str | None = None   # the name this ion takes inside a compound (ADR-0027); None if unused


class ChemData:
    def __init__(self, elements: dict[str, Element], ions: dict[str, Ion], sources: dict[str, str]):
        self.elements = elements
        self.ions = ions
        self.sources = sources

    @classmethod
    def load(cls, root: Path | None = None) -> "ChemData":
        d = (Path(root) if root is not None else Path.cwd()) / "data"
        el_doc = tomllib.loads((d / "elements.toml").read_text(encoding="utf-8"))
        ion_doc = tomllib.loads((d / "ions.toml").read_text(encoding="utf-8"))

        elements: dict[str, Element] = {}
        for symbol, e in el_doc.get("elements", {}).items():
            try:
                elements[symbol] = Element(
                    symbol=symbol,
                    Z=int(e["Z"]),
                    name=e["name"],
                    atomic_weight=Decimal(e["atomic_weight"]),
                    group=int(e["group"]),
                    period=int(e["period"]),
                    block=e["block"],
                    uncertainty=Decimal(e["uncertainty"]) if "uncertainty" in e else None,
                )
            except (KeyError, ArithmeticError) as exc:
                raise BuildError(f"data/elements.toml: bad entry for '{symbol}': {exc}") from exc

        ions: dict[str, Ion] = {}
        for ion_id, v in ion_doc.get("ions", {}).items():
            try:
                ions[ion_id] = Ion(
                    id=ion_id,
                    formula=v["formula"],
                    charge=int(v["charge"]),
                    name=v["name"],
                    kind=v["kind"],
                    element=v.get("element"),
                    compound_name=v.get("compound_name"),
                )
            except KeyError as exc:
                raise BuildError(f"data/ions.toml: bad entry for '{ion_id}': missing {exc}") from exc

        sources = {
            "atomic_weight": el_doc.get("source", ""),
            "position": el_doc.get("position_source", ""),
            "ion_charge": ion_doc.get("charge_source", ""),
        }
        obj = cls(elements, ions, sources)
        obj.validate()
        return obj

    def atomic_weight(self, symbol: str) -> Decimal:
        el = self.elements.get(symbol)
        if el is None:
            raise BuildError(f"unknown element '{symbol}' — not in data/elements.toml")
        return el.atomic_weight

    def molar_mass(self, formula) -> Decimal:
        """Molar mass in g/mol as an exact Decimal sum of atomic weights. Accepts a formula string or a
        parsed Formula. Raises BuildError if any element is absent from the dataset."""
        f = formula if hasattr(formula, "counts") else parse_formula(formula)
        total = Decimal(0)
        for el, k in f.counts.items():
            total += self.atomic_weight(el) * k
        return total

    def validate(self) -> None:
        """Machine-check dataset self-consistency (regime-1). Raises BuildError on any inconsistency."""
        for ion in self.ions.values():
            parsed = parse_formula(ion.formula, ctx=f"data/ions.toml '{ion.id}'")
            for el in parsed.counts:
                if el not in self.elements:
                    raise BuildError(
                        f"data/ions.toml '{ion.id}': formula uses element '{el}' "
                        f"absent from data/elements.toml"
                    )
            if ion.kind == "monatomic":
                if ion.element is None or ion.element not in self.elements:
                    raise BuildError(f"data/ions.toml '{ion.id}': monatomic ion needs a known `element`")
                if set(parsed.counts) != {ion.element} or parsed.counts[ion.element] != 1:
                    raise BuildError(
                        f"data/ions.toml '{ion.id}': monatomic formula '{ion.formula}' "
                        f"disagrees with element '{ion.element}'"
                    )
