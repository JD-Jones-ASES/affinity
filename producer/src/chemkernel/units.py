"""Quantity & units engine (ADR-0015).

A `Quantity` is an exact `Decimal` magnitude over a three-dimensional chemistry basis —
amount [mol], mass [g], volume [L] — carried as a `Dim` vector so units are tracked and cancelled through
every multiplication and division, and a dimension mismatch is a `BuildError`, never a silent coercion.
This is the machine behind the dimensional-analysis chain (brief §6.6): moles = molarity × volume,
mass = moles × molar mass, with the units doing the bookkeeping.

Never float (ADR-0013). Pressure and temperature basis components were added for gases (ADR-0040 —
ADR-0015's deferred extension); energy/charge follow when thermochemistry/electrochemistry need them.
Temperature here is ABSOLUTE (kelvin) only — a multiplicative basis; the affine °C→K offset (K = °C + 273.15)
is handled at the boundary by the caller (gas-law generator), never as a scaling unit, because °C is not a
ratio scale. Extent arithmetic that can produce non-terminating ratios lives in `extent.py` and uses exact
`Fraction`; this engine handles terminating conversions and now the gas-law products (mol·L·atm·mol⁻¹·K⁻¹·K/atm
→ L), whose Decimal quotients ride the ambient context precision (the gas constant R is non-terminating).
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
    pressure: int = 0       # gases (ADR-0040); atm is the canonical pressure unit
    temperature: int = 0    # gases (ADR-0040); K (absolute) is the canonical temperature unit
    energy: int = 0         # thermochemistry (ADR-0042); J is the canonical energy unit. Kept INDEPENDENT of
                            # pressure·volume — this is a chemistry-bookkeeping basis, not a physics-equivalence
                            # engine, so a gas-law product stays in L·atm and a calorimetry heat stays in J.

    def __add__(self, o: "Dim") -> "Dim":
        return Dim(self.amount + o.amount, self.mass + o.mass, self.volume + o.volume,
                   self.pressure + o.pressure, self.temperature + o.temperature, self.energy + o.energy)

    def __sub__(self, o: "Dim") -> "Dim":
        return Dim(self.amount - o.amount, self.mass - o.mass, self.volume - o.volume,
                   self.pressure - o.pressure, self.temperature - o.temperature, self.energy - o.energy)


# unit label -> (dimension, multiplicative factor to canonical base units [mol, g, L, atm, K])
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
    "atm": (Dim(pressure=1), Decimal(1)),
    "K": (Dim(temperature=1), Decimal(1)),
    # the molar gas constant's unit: L·atm·mol⁻¹·K⁻¹ (ADR-0040). Lets a gas-law product be built and its
    # dimension certified by the same units engine that proves L × mol/L = mol.
    "L*atm/(mol*K)": (Dim(volume=1, pressure=1, amount=-1, temperature=-1), Decimal(1)),
    # thermochemistry (ADR-0042): energy + the specific-heat unit, so q = m·c·ΔT is built and certified
    # (g × J·g⁻¹·K⁻¹ × K → J) by the same engine. ΔT rides the temperature basis (a difference: 1 °C = 1 K).
    "J": (Dim(energy=1), Decimal(1)),
    "kJ": (Dim(energy=1), Decimal(1000)),
    "J/(g*K)": (Dim(energy=1, mass=-1, temperature=-1), Decimal(1)),
}

# canonical display label for a derived dimension
_CANON_LABEL: dict[Dim, str] = {
    Dim(): "",
    Dim(amount=1): "mol",
    Dim(mass=1): "g",
    Dim(volume=1): "L",
    Dim(amount=1, volume=-1): "mol/L",
    Dim(mass=1, amount=-1): "g/mol",
    Dim(pressure=1): "atm",
    Dim(temperature=1): "K",
    Dim(volume=1, pressure=1, amount=-1, temperature=-1): "L*atm/(mol*K)",
    Dim(energy=1): "J",
    Dim(energy=1, mass=-1, temperature=-1): "J/(g*K)",
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
