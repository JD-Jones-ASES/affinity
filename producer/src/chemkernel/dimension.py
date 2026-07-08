"""Dimensional-homogeneity engine for the Chemical Atlas formula sheet (brief §10.3, ADR-0039).

ADR-0015 deferred "symbolic dimensional homogeneity of reference formulas (PV=nRT etc.)" to when the formula
sheet lands, and anticipated adapting the sibling's SymPy `dims.py`. We diverge (ADR-0001 permits a
chemistry-motivated divergence): the formula-sheet relations are **monomials and sums of monomials**, so a
first-course relation is dimensionally homogeneous iff *every term shares one dimension vector* — plain
integer-vector arithmetic, no SymPy. The payoff is **pure-Node re-derivation parity** (ADR-0008): the
producer emits each variable's dimension vector + each term's factor list, and `validate-reference.mjs`
re-computes every term's dimension from those integers and re-checks equality (the ADR-0028 "emit the matrix,
re-tally in Node" pattern). This is the honesty model for a regime-2 relation: we cannot *prove* PV=nRT is
true (that is the disclosed model — model-assumed badge), but we machine-check that it is **dimensionally
consistent**, and that check is independently re-run in CI.

The Decimal units engine (`units.py`, amount/mass/volume, for the numeric conversion chain) and this SI
dimension engine (for reference-formula homogeneity) are deliberately NOT conflated — exactly as ADR-0015
required. Unit dimension signatures are *definitional* (the dimension of "atm" is a matter of SI structure,
not an empirical measurement), so they live in code here, like the `formula.py` grammar — not in `data/`.
"""

from __future__ import annotations

from . import BuildError

# The SI base dimensions, in a fixed order. Luminous intensity is never used in chemistry and is dropped;
# electric current is kept (always 0 until electrochemistry lands) so the emitted vector length never has to
# change. A Dimension is a 6-tuple of exponents over these bases.
BASES = ("mass", "length", "time", "amount", "temperature", "current")
_N = len(BASES)
Dimension = tuple[int, int, int, int, int, int]
DIMENSIONLESS: Dimension = (0, 0, 0, 0, 0, 0)


def _mk(**kw: int) -> Dimension:
    return tuple(int(kw.get(b, 0)) for b in BASES)  # type: ignore[return-value]


# Named composite dimensions, for the human-facing "both sides are <energy>" label the sheet renders.
_ENERGY = _mk(mass=1, length=2, time=-2)             # J = kg·m²·s⁻²
_PRESSURE = _mk(mass=1, length=-1, time=-2)          # Pa = kg·m⁻¹·s⁻²
_VOLUME = _mk(length=3)                              # m³ (litre is a volume)
_AMOUNT = _mk(amount=1)                              # mol
_MASS = _mk(mass=1)
_TEMPERATURE = _mk(temperature=1)
_CONCENTRATION = _mk(length=-3, amount=1)            # mol/L
_MOLAR_MASS = _mk(mass=1, amount=-1)                 # g/mol

DIM_NAMES: dict[Dimension, str] = {
    DIMENSIONLESS: "dimensionless",
    _AMOUNT: "amount",
    _MASS: "mass",
    _VOLUME: "volume",
    _TEMPERATURE: "temperature",
    _PRESSURE: "pressure",
    _ENERGY: "energy",
    _CONCENTRATION: "concentration",
    _MOLAR_MASS: "molar mass",
    _mk(mass=1, length=2, time=-2, amount=-1): "molar energy",   # kJ/mol — a reaction/formation enthalpy
    _mk(mass=1, length=2, time=-2, temperature=-1): "energy per temperature",
    _mk(mass=1, length=2, time=-2, amount=-1, temperature=-1): "energy per amount per temperature",
}

# Unit label -> its SI dimension vector. DEFINITIONAL, not empirical: these are the dimensional signatures a
# unit carries by definition, mirrored byte-for-byte by the Node gate's own table. Keys are canonical ASCII
# (the display string a variable renders is a separate field); `*` = multiply, `/` = divide in the label.
_UNIT_DIM: dict[str, Dimension] = {
    "": DIMENSIONLESS,
    "1": DIMENSIONLESS,
    "%": DIMENSIONLESS,                     # a percent is a scaled dimensionless ratio
    "mol": _AMOUNT,
    "mol^-1": _mk(amount=-1),               # per-mole, e.g. the Avogadro constant N_A
    "1/mol": _mk(amount=-1),
    "g": _MASS,
    "kg": _MASS,
    "mg": _MASS,
    "L": _VOLUME,
    "mL": _VOLUME,
    "M": _CONCENTRATION,
    "mol/L": _CONCENTRATION,
    "g/mol": _MOLAR_MASS,
    "kg/mol": _MOLAR_MASS,
    "atm": _PRESSURE,
    "Pa": _PRESSURE,
    "kPa": _PRESSURE,
    "K": _TEMPERATURE,
    "J": _ENERGY,
    "kJ": _ENERGY,
    "J/mol": _mk(mass=1, length=2, time=-2, amount=-1),                  # molar energy (ΔH per mole)
    "kJ/mol": _mk(mass=1, length=2, time=-2, amount=-1),
    "J/(g*K)": _mk(length=2, time=-2, temperature=-1),                  # specific heat capacity
    "J/(mol*K)": _mk(mass=1, length=2, time=-2, amount=-1, temperature=-1),   # molar gas constant R (SI)
    "L*atm/(mol*K)": _mk(mass=1, length=2, time=-2, amount=-1, temperature=-1),  # R in gas-law teaching units
}


def unit_dimension(unit: str, ctx: str = "") -> Dimension:
    """The SI dimension vector for a registered unit label. Raises on an unknown unit (refuse to guess)."""
    if unit not in _UNIT_DIM:
        raise BuildError(f"{ctx}: unknown unit '{unit}' — not in the dimension registry")
    return _UNIT_DIM[unit]


def add(a: Dimension, b: Dimension) -> Dimension:
    return tuple(x + y for x, y in zip(a, b))  # type: ignore[return-value]


def scale(a: Dimension, k: int) -> Dimension:
    return tuple(x * k for x in a)  # type: ignore[return-value]


def term_dimension(factors: list[tuple[Dimension, int]]) -> Dimension:
    """Dimension of a monomial: Σ (factor dimension × its integer power). A bare numeric constant (×100 in a
    percent) is dimensionless and simply omitted from `factors`."""
    total = DIMENSIONLESS
    for dim, power in factors:
        total = add(total, scale(dim, power))
    return total


def dimension_name(dim: Dimension) -> str:
    """A human label for a dimension vector, else a compact exponent string (never fabricated units)."""
    if dim in DIM_NAMES:
        return DIM_NAMES[dim]
    parts = [f"{b}^{e}" for b, e in zip(BASES, dim) if e]
    return "·".join(parts) if parts else "dimensionless"
