"""Extent solver & species ledger — the pivot object (ADR-0002, ADR-0016).

The balanced equation tells you the allowed move; the ledger tells you how far it can go. For a reaction
with balanced coefficients, every amount is n_i = n_{i,0} + ν_i·ξ, where ν_i is the signed stoichiometric
coefficient (negative for reactants, positive for products) and ξ is the extent of reaction. The maximum
physical extent is the smallest ξ that drives a reactant to zero:

    ξ_max = min over reactants of  n_{i,0} / coeff_i

That reactant (or reactants, on a tie) is limiting; the rest are in excess and leave leftovers. The solver
works in exact `Fraction` (ADR-0013) so fractional extents never round, and refuses to emit a ledger with
any negative amount — the producer's nonnegative-extent guard (ADR-0008).

The ledger is species-agnostic: feed it the molecular equation or the net ionic equation (or a complete
ionic equation with spectators carried at ν=0) — it is the same machine either way.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction

from . import BuildError
from .formula import Formula


def _frac(x) -> Fraction:
    if isinstance(x, Fraction):
        return x
    if isinstance(x, (int, Decimal)):
        return Fraction(x)
    if isinstance(x, str):
        return Fraction(Decimal(x))
    raise BuildError(f"cannot interpret amount {x!r} as an exact quantity")


@dataclass(frozen=True)
class LedgerRow:
    species: str          # display id (e.g. "CaCl2", "Ca^2+", "CaCO3(s)")
    phase: str | None
    charge: int
    nu: int               # signed stoichiometric coefficient (− reactant, + product)
    initial_mol: Fraction
    final_mol: Fraction
    role: str             # "limiting" | "excess" | "product"


@dataclass(frozen=True)
class Ledger:
    rows: list[LedgerRow]
    extent_mol: Fraction        # ξ
    limiting: list[str]         # species id(s) that reach zero


def solve_extent(
    reactants: list[tuple[Formula, object]],
    products: list[tuple[Formula, object]],
    coeffs: list[int],
    ctx: str = "",
) -> Ledger:
    """Build the species ledger. `reactants`/`products` are (Formula, initial_amount) pairs where the
    amount is in moles (int/Decimal/Fraction/str); `coeffs` is balance()'s output [reactants..., products...]."""
    where = f"{ctx}: " if ctx else ""
    if len(coeffs) != len(reactants) + len(products):
        raise BuildError(f"{where}coefficient count {len(coeffs)} != species count "
                         f"{len(reactants) + len(products)}")

    n_react = len(reactants)
    react_coeffs = coeffs[:n_react]
    prod_coeffs = coeffs[n_react:]

    limits: list[tuple[Fraction, str]] = []
    for (f, n0), c in zip(reactants, react_coeffs):
        if c <= 0:
            raise BuildError(f"{where}reactant {f.raw} has nonpositive coefficient {c}")
        n0f = _frac(n0)
        if n0f < 0:
            raise BuildError(f"{where}reactant {f.raw} has negative initial amount {n0f}")
        limits.append((n0f / c, f.raw))

    if not limits:
        raise BuildError(f"{where}no reactants to consume")

    xi = min(limits, key=lambda t: t[0])[0]
    limiting = [name for lim, name in limits if lim == xi]

    rows: list[LedgerRow] = []
    for (f, n0), c in zip(reactants, react_coeffs):
        final = _frac(n0) - c * xi
        if final < 0:
            raise BuildError(f"{where}{f.raw} would go negative (final {final}) — extent is wrong")
        rows.append(LedgerRow(f.raw, f.phase, f.charge, -c, _frac(n0), final,
                              "limiting" if f.raw in limiting else "excess"))
    for (f, n0), c in zip(products, prod_coeffs):
        final = _frac(n0) + c * xi
        rows.append(LedgerRow(f.raw, f.phase, f.charge, c, _frac(n0), final, "product"))

    return Ledger(rows=rows, extent_mol=xi, limiting=limiting)


def species_mass_g(row: LedgerRow, data) -> Fraction:
    """Exact mass in grams of a ledger row's final amount, using data/ molar masses."""
    return row.final_mol * Fraction(data.molar_mass(row.species))


def to_decimal(value, places: int = 6) -> Decimal:
    """Render an exact amount/mass as a fixed-decimal-place `Decimal` for display (Q7 sig-fig policy is
    still open; this is a display helper, not the stored value)."""
    f = value if isinstance(value, Fraction) else _frac(value)
    quotient = Decimal(f.numerator) / Decimal(f.denominator)
    return quotient.quantize(Decimal(1).scaleb(-places))
