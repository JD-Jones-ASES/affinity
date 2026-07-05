"""Equation balancer: conservation as linear algebra (ADR-0008, ADR-0014).

Balancing is not guessing — it is a conservation constraint. Build the element-and-charge conservation
matrix (one row per element plus one for charge; reactant counts positive, product counts negative) and
take its null space over the rationals. A well-posed reaction has a one-dimensional null space; scale it
to the smallest positive integer coefficients. Anything else — no solution, an ambiguous multi-dimensional
family, or a solution that can't be made all-positive — raises BuildError (the producer refuses to emit).

Subscripts are never touched: only coefficients are chosen, so conservation is enforced without ever
rewriting a formula (house-conventions §Notation). The integer solution is re-verified element by element
and for charge before it is returned.
"""

from __future__ import annotations

from math import gcd

import sympy as sp

from . import BuildError
from .formula import Formula


def balance(reactants: list[Formula], products: list[Formula], ctx: str = "") -> list[int]:
    """Return integer coefficients [reactants..., products...] balancing the reaction."""
    where = f"{ctx}: " if ctx else ""
    if not reactants or not products:
        raise BuildError(f"{where}a reaction needs at least one reactant and one product")

    species = reactants + products
    elements = sorted({el for f in species for el in f.counts})
    n_react = len(reactants)

    rows: list[list[int]] = []
    for el in elements:
        row = [f.counts.get(el, 0) for f in reactants] + [-f.counts.get(el, 0) for f in products]
        rows.append(row)
    rows.append([f.charge for f in reactants] + [-f.charge for f in products])

    null = sp.Matrix(rows).nullspace()
    if len(null) != 1:
        raise BuildError(
            f"{where}reaction is unbalanceable or ambiguous (conservation null-space "
            f"has dimension {len(null)}, expected 1)"
        )
    vec = null[0]

    denom_lcm = 1
    for entry in vec:
        q = int(sp.Rational(entry).q)
        denom_lcm = denom_lcm * q // gcd(denom_lcm, q)
    coeffs = [int(sp.Rational(entry) * denom_lcm) for entry in vec]

    if all(c <= 0 for c in coeffs):
        coeffs = [-c for c in coeffs]
    common = 0
    for c in coeffs:
        common = gcd(common, c)
    if common == 0:
        raise BuildError(f"{where}degenerate reaction (all-zero coefficients)")
    coeffs = [c // common for c in coeffs]

    if any(c <= 0 for c in coeffs):
        raise BuildError(f"{where}no all-positive integer balance exists (got {coeffs})")

    _verify(reactants, products, coeffs, elements, n_react, where)
    return coeffs


def _verify(
    reactants: list[Formula],
    products: list[Formula],
    coeffs: list[int],
    elements: list[str],
    n_react: int,
    where: str,
) -> None:
    for el in elements:
        lhs = sum(coeffs[i] * reactants[i].counts.get(el, 0) for i in range(n_react))
        rhs = sum(coeffs[n_react + j] * products[j].counts.get(el, 0) for j in range(len(products)))
        if lhs != rhs:
            raise BuildError(f"{where}element {el} not conserved ({lhs} vs {rhs})")
    lhs_q = sum(coeffs[i] * reactants[i].charge for i in range(n_react))
    rhs_q = sum(coeffs[n_react + j] * products[j].charge for j in range(len(products)))
    if lhs_q != rhs_q:
        raise BuildError(f"{where}charge not conserved ({lhs_q} vs {rhs_q})")
