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
    # deterministic, chemically-conventional order: left terms in insertion order, then right-only terms
    # (NOT set union, whose iteration order varies and would make committed derived/ non-byte-stable)
    ordered_keys = list(L.keys()) + [k for k in R if k not in L]
    for key in ordered_keys:
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


# --------------------------- reaction classification (ADR-0035, item 6) ---------------------------
#
# `classify_reaction` labels a balanced, phased reaction with one of the first-course reaction families and a
# machine-checkable redox flag. It is a pure function of the formulas + the injected sourced datasets (the
# solubility ruleset, the acid/base table, the decomposition table) — no family is hard-coded chemistry:
# combustion/synthesis/decomposition/single-replacement are recognized structurally, precipitation cites the
# solubility rule, acid-base cites the acid+base identities, gas-evolution cites the decomposition table.
#
# Redox is detected honestly at the "oxidation-state level" a first course teaches WITHOUT assigning full
# oxidation numbers (a Phase-2 topic): an element that is FREE (uncombined, oxidation state 0) on one side and
# COMBINED on the other necessarily changed oxidation state, so electrons moved. This covers exactly the
# families a first course calls redox (combustion, single replacement, and element-bearing synthesis/
# decomposition) and never over-claims: a double replacement with no free element is correctly non-redox.


def _is_free_element(f: Formula) -> bool:
    """A free (uncombined) element — neutral, one element type (O2, Fe, H2, Cl2, C). Its atoms sit at
    oxidation state 0, so if this element appears combined on the other side, electrons were transferred."""
    return f.charge == 0 and len(f.counts) == 1


def redox_free_elements(reactants: list[Formula], products: list[Formula]) -> list[str]:
    """Elements that are free on one side and combined on the other (→ their oxidation state changed)."""
    free_l = {el for f in reactants if _is_free_element(f) for el in f.counts}
    free_r = {el for f in products if _is_free_element(f) for el in f.counts}
    comb_l = {el for f in reactants if not _is_free_element(f) for el in f.counts}
    comb_r = {el for f in products if not _is_free_element(f) for el in f.counts}
    return sorted((free_l & comb_r) | (free_r & comb_l))


def classify_reaction(reactants: list[Formula], products: list[Formula], data=None, *,
                      solubility=None, acidbase=None, decomposition=None, ctx: str = "") -> dict:
    """Classify a balanced, phased reaction into a first-course family + redox flag. Raises if unclassifiable
    (refuse to emit — the classifier runs on curated corpora, so a miss is a build bug, not a shrug)."""
    where = f"{ctx}: " if ctx else ""
    r_cores = [_core_id(f) for f in reactants]
    p_cores = [_core_id(f) for f in products]
    n_r, n_p = len(reactants), len(products)
    free_r = [f for f in reactants if _is_free_element(f)]
    free_p = [f for f in products if _is_free_element(f)]

    changed = redox_free_elements(reactants, products)
    redox = bool(changed)
    redox_reason = None
    if redox:
        names = ", ".join(changed)
        redox_reason = (f"{names} appears as a free element on one side and combined on the other, so its "
                        f"oxidation state changed — electrons were transferred (a redox reaction). Assigning "
                        f"full oxidation numbers is a later topic; here the free-element signature is enough.")

    def result(family: str, label: str, evidence: str, structure: str | None = None) -> dict:
        out = {"family": family, "family_label": label, "redox": redox, "evidence": evidence}
        if redox_reason:
            out["redox_reason"] = redox_reason
        if structure:
            out["structure"] = structure
        return out

    # 1. combustion — a single C/H(/O) fuel + O2 → only CO2 and/or H2O
    o2 = [f for f in reactants if _core_id(f) == "O2"]
    fuels = [f for f in reactants if _core_id(f) != "O2"]
    if o2 and p_cores and set(p_cores) <= {"CO2", "H2O"} and len(fuels) == 1 \
            and set(fuels[0].counts) <= {"C", "H", "O"} and ({"C", "H"} & set(fuels[0].counts)):
        prod = " and ".join(dict.fromkeys(p_cores))   # ordered, de-duplicated
        return result("combustion", "combustion",
                      f"{_core_id(fuels[0])} burns in O2, giving only {prod} — complete combustion.")

    # 2/3. synthesis (combination) / decomposition — by reactant/product count
    if n_p == 1 and n_r >= 2:
        return result("synthesis", "synthesis (combination)",
                      f"{' + '.join(r_cores)} combine into the single product {p_cores[0]}.")
    if n_r == 1 and n_p >= 2:
        return result("decomposition", "decomposition",
                      f"The single compound {r_cores[0]} breaks apart into {n_p} products.")

    # 4. single replacement — one free element on each side (A + BC → B + AC)
    if n_r == 2 and n_p == 2 and len(free_r) == 1 and len(free_p) == 1:
        return result("single-replacement", "single replacement",
                      f"The free element {_core_id(free_r[0])} displaces an element from a compound, "
                      f"releasing {_core_id(free_p[0])}.", structure="single-replacement")

    # sub-types of double replacement: two reactants (no free element) exchange partners
    if n_r == 2 and not free_r:
        acids = [f for f in reactants if acidbase and acidbase.is_acid(_core_id(f))]
        bases = [f for f in reactants if acidbase and acidbase.is_base(_core_id(f))]
        gases = [f for f in products if f.phase == "g"]
        has_water = "H2O" in p_cores

        # 5. acid-base neutralization — an acid + a base → salt + water
        if acids and bases and has_water:
            return result("acid-base", "acid-base neutralization",
                          f"{acidbase.acid_name(_core_id(acids[0]))} neutralizes "
                          f"{acidbase.base_name(_core_id(bases[0]))}: H+ and OH- combine to water, leaving a "
                          f"dissolved salt.", structure="double-replacement")

        # 6. gas evolution — a (g) product justified by an unstable intermediate in the decomposition table
        if gases and decomposition is not None:
            just = decomposition.justifies(p_cores, [_core_id(g) for g in gases])
            if just is not None:
                return result("gas-evolution", "gas evolution",
                              f"{just['name']} would form but is unstable — it decomposes to {just['gas']} gas "
                              f"and water. {just['note']}", structure="double-replacement")

        # 7. precipitation — an insoluble solid product (cite the governing solubility rule)
        if solubility is not None:
            for s in (f for f in products if f.phase == "s"):
                try:
                    verdict = solubility.classify_compound(s, data, ctx)
                except BuildError:
                    continue
                if not verdict.soluble:
                    return result("precipitation", "precipitation (double replacement)",
                                  f"{_core_id(s)} is insoluble ({verdict.rule_id}) and drops out as a solid.",
                                  structure="double-replacement")

        # 8. generic double replacement — two compounds swap partners, none of the above
        if n_p == 2:
            return result("double-replacement", "double replacement",
                          "Two compounds exchange partners (AB + CD → AD + CB).",
                          structure="double-replacement")

    raise BuildError(f"{where}cannot classify reaction {' + '.join(r_cores)} -> {' + '.join(p_cores)}")
