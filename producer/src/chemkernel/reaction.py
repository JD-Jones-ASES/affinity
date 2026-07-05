"""Reaction transforms: dissociation, complete ionic, net ionic (ADR-0017).

For an aqueous precipitation reaction, three views:
  molecular        CaCl2(aq) + Na2CO3(aq) -> CaCO3(s) + 2 NaCl(aq)
  complete ionic   dissociate every aqueous strong-electrolyte salt into its ions; keep solids intact
  net ionic        cancel spectator ions (present unchanged on both sides)

`dissociate` decomposes a neutral salt into one cation + one anion from the ion table by charge balance
and composition match — no ion identities are hard-coded. `net_ionic` re-verifies atom and charge
conservation on the reduced equation (refuse to emit if it fails).

v0 scope: every (aq) species that decomposes into table ions is treated as a strong electrolyte and fully
dissociated. Weak-electrolyte handling (a strong/weak flag so acetic acid stays intact) is deferred.
"""

from __future__ import annotations

import re
from math import gcd

from . import BuildError
from .formula import Formula, parse_formula

_PHASE_SUFFIX = re.compile(r"\((?:s|l|g|aq)\)$")

# a term on one side of an ionic equation
Term = tuple[str, int, int, "str | None"]   # (species_id, count, charge, phase)


def _core_id(f: Formula) -> str:
    return _PHASE_SUFFIX.sub("", f.raw)


def dissociate(formula: Formula, data, ctx: str = "") -> list[tuple[str, int]]:
    """Decompose a neutral ionic salt into [(cation_id, count), (anion_id, count)]."""
    where = f"{ctx}: " if ctx else ""
    if formula.charge != 0:
        raise BuildError(f"{where}{formula.raw} is already an ion; nothing to dissociate")

    cations = [ion for ion in data.ions.values() if ion.charge > 0]
    anions = [ion for ion in data.ions.values() if ion.charge < 0]
    for c in cations:
        c_comp = parse_formula(c.formula).counts
        for a in anions:
            a_comp = parse_formula(a.formula).counts
            g = gcd(-a.charge, c.charge)
            m = -a.charge // g   # cation count
            n = c.charge // g    # anion count
            combo: dict[str, int] = {}
            for el, k in c_comp.items():
                combo[el] = combo.get(el, 0) + k * m
            for el, k in a_comp.items():
                combo[el] = combo.get(el, 0) + k * n
            if combo == dict(formula.counts):
                return [(c.id, m), (a.id, n)]
    raise BuildError(f"{where}cannot dissociate {formula.raw} into a known cation + anion")


def complete_ionic(
    reactants: list[Formula], products: list[Formula], coeffs: list[int], data, ctx: str = ""
) -> tuple[list[Term], list[Term]]:
    """Expand a balanced, phased equation to complete-ionic terms per side."""
    n_react = len(reactants)

    def expand(species: list[Formula], cfs: list[int]) -> list[Term]:
        terms: list[Term] = []
        for f, cf in zip(species, cfs):
            if f.phase == "aq" and f.charge == 0:
                try:
                    ions = dissociate(f, data, ctx)
                except BuildError:
                    ions = None
                if ions:
                    for ion_id, k in ions:
                        terms.append((ion_id, cf * k, data.ions[ion_id].charge, "aq"))
                    continue
            terms.append((_core_id(f), cf, f.charge, f.phase))
        return terms

    return expand(reactants, coeffs[:n_react]), expand(products, coeffs[n_react:])


def net_ionic(
    left: list[Term], right: list[Term], ctx: str = ""
) -> tuple[dict[tuple[str, str | None], int], dict[tuple[str, str | None], int], list[str]]:
    """Cancel spectators and reduce; returns (net_left, net_right, spectator_ids). Verifies conservation."""
    where = f"{ctx}: " if ctx else ""
    L: dict[tuple[str, str | None], int] = {}
    R: dict[tuple[str, str | None], int] = {}
    for sid, cnt, _ch, ph in left:
        L[(sid, ph)] = L.get((sid, ph), 0) + cnt
    for sid, cnt, _ch, ph in right:
        R[(sid, ph)] = R.get((sid, ph), 0) + cnt

    spectators: list[str] = []
    net_left: dict[tuple[str, str | None], int] = {}
    net_right: dict[tuple[str, str | None], int] = {}
    for key in set(L) | set(R):
        left_n, right_n = L.get(key, 0), R.get(key, 0)
        common = min(left_n, right_n)
        nl, nr = left_n - common, right_n - common
        if common > 0 and nl == 0 and nr == 0:
            spectators.append(key[0])
        if nl > 0:
            net_left[key] = nl
        if nr > 0:
            net_right[key] = nr

    counts = list(net_left.values()) + list(net_right.values())
    g = 0
    for c in counts:
        g = gcd(g, c)
    if g > 1:
        net_left = {k: v // g for k, v in net_left.items()}
        net_right = {k: v // g for k, v in net_right.items()}

    if not net_left or not net_right:
        raise BuildError(f"{where}net ionic equation is empty (no net reaction)")
    _verify_ionic(net_left, net_right, where)
    return net_left, net_right, sorted(set(spectators))


def _verify_ionic(
    net_left: dict[tuple[str, str | None], int],
    net_right: dict[tuple[str, str | None], int],
    where: str,
) -> None:
    def totals(side):
        atoms: dict[str, int] = {}
        charge = 0
        for (sid, _ph), cnt in side.items():
            f = parse_formula(sid)
            for el, k in f.counts.items():
                atoms[el] = atoms.get(el, 0) + k * cnt
            charge += f.charge * cnt
        return atoms, charge

    la, lq = totals(net_left)
    ra, rq = totals(net_right)
    if la != ra:
        raise BuildError(f"{where}net ionic atoms not conserved ({la} vs {ra})")
    if lq != rq:
        raise BuildError(f"{where}net ionic charge not conserved ({lq} vs {rq})")
