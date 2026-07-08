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
    # periodic properties (ADR-0031); optional — omitted where the property is undefined (noble-gas
    # electronegativity) or deferred (transition-metal covalent radius). Decimal, never float (ADR-0013).
    electronegativity: Decimal | None = None        # Pauling scale (openstax-chemistry-2e)
    covalent_radius_pm: Decimal | None = None        # single-bond covalent radius, pm (cordero-2008)
    first_ionization_kj_mol: Decimal | None = None   # first ionization energy, kJ/mol (nist)


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
    def __init__(self, elements: dict[str, Element], ions: dict[str, Ion], sources: dict[str, str],
                 constants: dict[str, Decimal] | None = None, bonding: dict | None = None,
                 constant_units: dict[str, str] | None = None, specific_heats: dict | None = None):
        self.elements = elements
        self.ions = ions
        self.sources = sources
        self.constants = constants or {}
        self.constant_units = constant_units or {}
        self.bonding = bonding or {}
        self.specific_heats = specific_heats or {}   # display name -> {name, phase, specific_heat (Decimal)}

    @property
    def avogadro(self) -> Decimal:
        """The Avogadro constant N_A in mol^-1, from data/constants.toml (exact, ADR-0006/0013)."""
        if "avogadro" not in self.constants:
            raise BuildError("Avogadro constant not loaded — is data/constants.toml present?")
        return self.constants["avogadro"]

    def constant_unit(self, key: str) -> str:
        """The unit label a curated constant carries in data/constants.toml (e.g. R's L*atm/(mol*K))."""
        if key not in self.constants:
            raise BuildError(f"unknown constant '{key}' — not in data/constants.toml")
        return self.constant_units.get(key, "")

    @classmethod
    def load(cls, root: Path | None = None) -> "ChemData":
        d = (Path(root) if root is not None else Path.cwd()) / "data"
        el_doc = tomllib.loads((d / "elements.toml").read_text(encoding="utf-8"))
        ion_doc = tomllib.loads((d / "ions.toml").read_text(encoding="utf-8"))

        elements: dict[str, Element] = {}
        for symbol, e in el_doc.get("elements", {}).items():
            opt = lambda key: Decimal(e[key]) if key in e else None  # optional Decimal, never float (ADR-0013)
            try:
                elements[symbol] = Element(
                    symbol=symbol,
                    Z=int(e["Z"]),
                    name=e["name"],
                    atomic_weight=Decimal(e["atomic_weight"]),
                    group=int(e["group"]),
                    period=int(e["period"]),
                    block=e["block"],
                    uncertainty=opt("uncertainty"),
                    electronegativity=opt("electronegativity"),
                    covalent_radius_pm=opt("covalent_radius_pm"),
                    first_ionization_kj_mol=opt("first_ionization_kj_mol"),
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

        # physical constants (optional file; ADR-0006). Values read as Decimal, never float; the unit label
        # travels alongside so the formula sheet can thread a sourced constant (R) with its units (ADR-0039).
        constants: dict[str, Decimal] = {}
        constant_units: dict[str, str] = {}
        const_source = ""
        const_path = d / "constants.toml"
        if const_path.exists():
            const_doc = tomllib.loads(const_path.read_text(encoding="utf-8"))
            const_source = const_doc.get("source", "")
            for key, v in const_doc.items():
                if isinstance(v, dict) and "value" in v:
                    try:
                        constants[key] = Decimal(v["value"])
                    except ArithmeticError as exc:
                        raise BuildError(f"data/constants.toml: bad value for '{key}': {exc}") from exc
                    constant_units[key] = v.get("unit", "")

        # bond-classification ruleset (optional file; ADR-0033). ΔEN class thresholds are a sourced teaching
        # rule (OpenStax Fig 7.8), kept as data so the bonding mode never hard-codes an empirical boundary.
        bonding: dict = {}
        bonding_path = d / "bonding.toml"
        if bonding_path.exists():
            bonding = tomllib.loads(bonding_path.read_text(encoding="utf-8"))
            for key in ("source", "caution", "classes"):
                if key not in bonding:
                    raise BuildError(f"data/bonding.toml: missing '{key}'")
            for c in bonding["classes"]:
                for key in ("id", "label", "description"):
                    if key not in c:
                        raise BuildError(f"data/bonding.toml: class missing '{key}'")
                for bound in ("min", "max"):
                    if bound in c:
                        Decimal(c[bound])  # must parse exactly (ADR-0013); raises on garbage

        # specific-heat capacities (optional file; ADR-0006/0042). A measured, data-sourced datum (regime-3) for
        # the calorimetry gym — read as Decimal (ADR-0013), the substance keyed by its display name.
        specific_heats: dict = {}
        sh_source = ""
        sh_path = d / "specific-heats.toml"
        if sh_path.exists():
            sh_doc = tomllib.loads(sh_path.read_text(encoding="utf-8"))
            sh_source = sh_doc.get("source", "")
            for key, v in sh_doc.get("substances", {}).items():
                try:
                    specific_heats[key] = {"name": v["name"], "phase": v.get("phase"),
                                           "specific_heat": Decimal(v["specific_heat"])}
                except (KeyError, ArithmeticError) as exc:
                    raise BuildError(f"data/specific-heats.toml: bad entry for '{key}': {exc}") from exc

        sources = {
            "atomic_weight": el_doc.get("source", ""),
            "position": el_doc.get("position_source", ""),
            "electronegativity": el_doc.get("electronegativity_source", ""),
            "covalent_radius": el_doc.get("covalent_radius_source", ""),
            "ionization_energy": el_doc.get("ionization_energy_source", ""),
            "ion_charge": ion_doc.get("charge_source", ""),
            "constants": const_source,
            "bonding": bonding.get("source", ""),
            "specific_heats": sh_source,
        }
        obj = cls(elements, ions, sources, constants, bonding, constant_units, specific_heats)
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
