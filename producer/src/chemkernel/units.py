"""Quantity & units engine (ADR-0015).

A `Quantity` is an exact `Decimal` magnitude over a three-dimensional chemistry basis —
amount [mol], mass [g], volume [L] — carried as a `Dim` vector so units are tracked and cancelled through
every multiplication and division, and a dimension mismatch is a `BuildError`, never a silent coercion.
This is the machine behind the dimensional-analysis chain (brief §6.6): moles = molarity × volume,
mass = moles × molar mass, with the units doing the bookkeeping.

Never float (ADR-0013). Pressure/energy/temperature/charge dimensions are deferred until gases and
thermochemistry need them; add basis components then. Extent arithmetic that can produce non-terminating
ratios lives in `extent.py` and uses exact `Fraction`; this engine handles the terminating-decimal
conversions (mL↔L, mol/L·L→mol, mol·g/mol→g).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from . import BuildError


@dataclass(frozen=True)
class Dim:
    amount: int = 0
    mass: int = 0
    volume: int = 0

    def __add__(self, o: "Dim") -> "Dim":
        return Dim(self.amount + o.amount, self.mass + o.mass, self.volume + o.volume)

    def __sub__(self, o: "Dim") -> "Dim":
        return Dim(self.amount - o.amount, self.mass - o.mass, self.volume - o.volume)


# unit label -> (dimension, multiplicative factor to canonical base units [mol, g, L])
_REGISTRY: dict[str, tuple[Dim, Decimal]] = {
    "": (Dim(), Decimal(1)),
    "mol": (Dim(amount=1), Decimal(1)),
    "mmol": (Dim(amount=1), Decimal("0.001")),
    "g": (Dim(mass=1), Decimal(1)),
    "kg": (Dim(mass=1), Decimal(1000)),
    "mg": (Dim(mass=1), Decimal("0.001")),
    "L": (Dim(volume=1), Decimal(1)),
    "mL": (Dim(volume=1), Decimal("0.001")),
    "M": (Dim(amount=1, volume=-1), Decimal(1)),
    "mol/L": (Dim(amount=1, volume=-1), Decimal(1)),
    "g/mol": (Dim(mass=1, amount=-1), Decimal(1)),
}

# canonical display label for a derived dimension
_CANON_LABEL: dict[Dim, str] = {
    Dim(): "",
    Dim(amount=1): "mol",
    Dim(mass=1): "g",
    Dim(volume=1): "L",
    Dim(amount=1, volume=-1): "mol/L",
    Dim(mass=1, amount=-1): "g/mol",
}


def _to_decimal(value) -> Decimal:
    return value if isinstance(value, Decimal) else Decimal(str(value))


@dataclass(frozen=True)
class Quantity:
    canonical: Decimal   # magnitude in base units (mol, g, L)
    dim: Dim
    label: str           # current display unit

    @classmethod
    def of(cls, value, unit: str) -> "Quantity":
        if unit not in _REGISTRY:
            raise BuildError(f"unknown unit '{unit}'")
        dim, factor = _REGISTRY[unit]
        return cls(_to_decimal(value) * factor, dim, unit)

    @property
    def value(self) -> Decimal:
        """Magnitude expressed in `label`'s unit."""
        _, factor = _REGISTRY[self.label]
        return self.canonical / factor

    def to(self, unit: str) -> "Quantity":
        if unit not in _REGISTRY:
            raise BuildError(f"unknown unit '{unit}'")
        dim, _ = _REGISTRY[unit]
        if dim != self.dim:
            raise BuildError(f"cannot convert {self.label} (dim {self.dim}) to {unit} (dim {dim})")
        return Quantity(self.canonical, self.dim, unit)

    def __mul__(self, o) -> "Quantity":
        o = o if isinstance(o, Quantity) else Quantity.of(o, "")
        dim = self.dim + o.dim
        return Quantity(self.canonical * o.canonical, dim, _CANON_LABEL.get(dim, "?"))

    def __truediv__(self, o) -> "Quantity":
        o = o if isinstance(o, Quantity) else Quantity.of(o, "")
        dim = self.dim - o.dim
        return Quantity(self.canonical / o.canonical, dim, _CANON_LABEL.get(dim, "?"))

    def __add__(self, o: "Quantity") -> "Quantity":
        if not isinstance(o, Quantity) or o.dim != self.dim:
            raise BuildError(f"cannot add {self.dim} and {getattr(o, 'dim', o)}")
        return Quantity(self.canonical + o.canonical, self.dim, self.label)

    def __sub__(self, o: "Quantity") -> "Quantity":
        if not isinstance(o, Quantity) or o.dim != self.dim:
            raise BuildError(f"cannot subtract {getattr(o, 'dim', o)} from {self.dim}")
        return Quantity(self.canonical - o.canonical, self.dim, self.label)

    def __str__(self) -> str:
        return f"{self.value} {self.label}".rstrip()
