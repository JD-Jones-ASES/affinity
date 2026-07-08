"""Lewis electron-ledger engine — the bonding tier's machine-checkable core (ADR-0044).

Where the species ledger accounts for ATOMS over reaction extent, this accounts for the VALENCE ELECTRONS of
one molecule. The thesis (AGENTS.md) says chemistry is "species accounting plus electron structure"; this is
the electron-structure ledger, and it is exact integer arithmetic — regime-1, machine-checked:

  - **Valence total** V = Σ (group valence electrons of each atom) − charge. The group rule is `reference.
    valence_electrons` (ADR-0033); an element with no defined count (the d-block) can't be Lewis-accounted, so
    the producer refuses it.
  - **Electron conservation** 2·(Σ bond orders) + 2·(Σ lone pairs) = V — the structure spends exactly the
    valence electrons, no more, no fewer.
  - **Octet / duet** per atom: 2·(bond orders on it) + 2·(its lone pairs) = 8 (H: 2). A completed shell.
  - **Formal charge** per atom = (group electrons) − 2·(lone pairs) − (bond orders on it), and Σ formal
    charges = the molecular charge. Both re-derived in pure Node by the gate.

The producer REFUSES to emit a structure that violates any of these (ADR-0008), exactly as build.py refuses an
unbalanced reaction — the author supplies the connectivity (a modeling choice, the Lewis localized-pair model),
the machine verifies its electron accounting.

Two further facets ride other badges, layered not mixed (the three-badge honesty model, ADR-0003):
  - **VSEPR geometry** — the electron-domain count (a machine-derived integer) keys into the SOURCED geometry
    table (`data/vsepr.toml`, regime-3); the naming is the sourced convention.
  - **Bond ΔEN** — each bond's electronegativity difference, computed from the sourced Pauling values and
    classified against the sourced ΔEN thresholds (`data/bonding.toml`) — the same path the Valence Table's
    bonding mode uses (ADR-0033).

Molecular polarity is AUTHORED and disclosed under the model-assumed badge (a dipole-cancellation argument
over the geometry), never claimed as a machine proof — the entry checks the bond dipoles and the geometry, and
discloses the net-polarity conclusion.
"""

from __future__ import annotations

from decimal import Decimal

from . import BuildError
from .formula import parse_formula
from .reference import valence_electrons

_POLARITY = ("polar", "nonpolar")


def _bond_class(delta: Decimal, data, ctx: str) -> str:
    """Classify a bond's ΔEN against the sourced thresholds (data/bonding.toml) — the ADR-0033 rule. Half-open
    intervals [min, max): ΔEN 0.4 exactly is polar covalent. Refuses if the ruleset is absent (honest — the
    bonding tier needs it)."""
    if not data.bonding:
        raise BuildError(f"{ctx}: bond classification needs data/bonding.toml")
    for c in data.bonding["classes"]:
        lo = Decimal(c["min"]) if "min" in c else None
        hi = Decimal(c["max"]) if "max" in c else None
        if (lo is None or delta >= lo) and (hi is None or delta < hi):
            return c["id"]
    raise BuildError(f"{ctx}: no bond class for ΔEN {delta}")


def build_molecule_entry(spec: dict, data, ctx: str = "") -> dict:
    """An authored molecule entry → the emitted Atlas object (ADR-0044). The electron ledger (valence total,
    octet, per-atom formal charge) is DERIVED from the authored atoms + bonds and machine-verified; the VSEPR
    geometry keys a sourced table on the machine-derived domain count; bond ΔEN comes from the sourced
    electronegativities; molecular polarity is authored + disclosed. The producer refuses any structure that
    fails electron conservation, an octet, or the formal-charge sum."""
    for key in ("id", "kind", "title", "formula", "names", "central", "summary", "source", "atoms", "bonds"):
        if key not in spec:
            raise BuildError(f"{ctx}: molecule entry missing required key '{key}'")
    if spec["kind"] != "molecule":
        raise BuildError(f"{ctx}: build_molecule_entry got kind '{spec['kind']}'")
    if not spec["names"]:
        raise BuildError(f"{ctx}: molecule entry needs at least one name")

    f = parse_formula(spec["formula"], ctx)
    if f.phase is not None:
        raise BuildError(f"{ctx}: molecule formula '{spec['formula']}' must be phase-less (structure is authored)")

    # TOML trap #4 guard (ADR-0038): a bare key authored after a [[atoms]]/[[bonds]] header is silently
    # absorbed into that table's last element. An atom/bond carrying an unexpected key is that absorption.
    for a in spec["atoms"]:
        extra = set(a) - {"id", "element", "lone_pairs"}
        if extra:
            raise BuildError(f"{ctx}: molecule atom carries unexpected key(s) {sorted(extra)} — a top-level "
                             f"bare key was absorbed into the last [[atoms]] table (bare keys must precede any "
                             f"array-of-tables header)")
    for b in spec["bonds"]:
        extra = set(b) - {"a", "b", "order"}
        if extra:
            raise BuildError(f"{ctx}: molecule bond carries unexpected key(s) {sorted(extra)} — a top-level "
                             f"bare key was absorbed into the last [[bonds]] table")

    # atoms: unique ids, known main-group elements with a defined valence-electron count
    atoms: dict[str, dict] = {}
    for a in spec["atoms"]:
        aid = a["id"]
        if aid in atoms:
            raise BuildError(f"{ctx}: duplicate atom id '{aid}'")
        el = data.elements.get(a["element"])
        if el is None:
            raise BuildError(f"{ctx}: atom '{aid}' uses element '{a['element']}' absent from data/elements.toml")
        ve = valence_electrons(el)
        if ve is None:
            raise BuildError(f"{ctx}: element '{a['element']}' has no defined valence-electron count "
                             f"(the d-block is convention-dependent) — it cannot be Lewis-accounted")
        lp = int(a["lone_pairs"])
        if lp < 0:
            raise BuildError(f"{ctx}: atom '{aid}' has negative lone pairs")
        atoms[aid] = {"element": a["element"], "lone_pairs": lp, "ve": ve}

    # the atom multiset must equal the formula's composition — so this structure is really THIS molecule
    struct_counts: dict[str, int] = {}
    for at in atoms.values():
        struct_counts[at["element"]] = struct_counts.get(at["element"], 0) + 1
    if struct_counts != dict(f.counts):
        raise BuildError(f"{ctx}: the authored atoms {struct_counts} do not match the formula "
                         f"'{spec['formula']}' composition {dict(f.counts)}")

    # bonds: valid endpoints, positive order; accumulate per-atom bond-order totals + neighbor (domain) counts
    order_sum = {aid: 0 for aid in atoms}
    neighbors = {aid: 0 for aid in atoms}
    if spec["central"] not in atoms:
        raise BuildError(f"{ctx}: central atom '{spec['central']}' is not one of the atoms")
    bonds_out = []
    for b in spec["bonds"]:
        a1, a2, order = b["a"], b["b"], int(b["order"])
        if a1 not in atoms or a2 not in atoms:
            raise BuildError(f"{ctx}: bond references unknown atom(s) '{a1}'/'{a2}'")
        if a1 == a2:
            raise BuildError(f"{ctx}: bond from atom '{a1}' to itself")
        if order < 1:
            raise BuildError(f"{ctx}: bond '{a1}-{a2}' needs a positive order")
        order_sum[a1] += order
        order_sum[a2] += order
        neighbors[a1] += 1
        neighbors[a2] += 1
        el1, el2 = data.elements[atoms[a1]["element"]], data.elements[atoms[a2]["element"]]
        if el1.electronegativity is None or el2.electronegativity is None:
            raise BuildError(f"{ctx}: bond '{a1}-{a2}' needs electronegativity for both atoms")
        delta = abs(el1.electronegativity - el2.electronegativity)
        cls = _bond_class(delta, data, ctx)
        bonds_out.append({"a": a1, "b": a2, "order": order,
                          "between": sorted([atoms[a1]["element"], atoms[a2]["element"]]),
                          "delta_en": str(delta), "bond_class": cls,
                          "polar": cls != "nonpolar-covalent"})

    # ── the electron ledger — exact integer accounting, machine-verified (ADR-0044) ──
    charge = f.charge
    valence = sum(at["ve"] for at in atoms.values()) - charge
    if valence < 0:
        raise BuildError(f"{ctx}: negative valence-electron total ({valence})")
    valence_breakdown = []
    for el, k in sorted(f.counts.items()):
        per = valence_electrons(data.elements[el])
        valence_breakdown.append({"symbol": el, "count": k, "per_atom": per, "subtotal": per * k})

    bonding_e = sum(order_sum.values())       # = 2·Σ(bond order): each bond of order o holds 2o electrons
    nonbonding_e = sum(2 * at["lone_pairs"] for at in atoms.values())
    if bonding_e + nonbonding_e != valence:
        raise BuildError(f"{ctx}: electrons not conserved — {bonding_e} bonding + {nonbonding_e} nonbonding = "
                         f"{bonding_e + nonbonding_e} != {valence} valence electrons")

    atoms_out = []
    fc_sum = 0
    for aid, at in atoms.items():
        target = 2 if at["element"] == "H" else 8
        shell = 2 * order_sum[aid] + 2 * at["lone_pairs"]
        if shell != target:
            raise BuildError(f"{ctx}: atom '{aid}' ({at['element']}) has {shell} shell electrons, not the "
                             f"{target} a completed {'duet' if target == 2 else 'octet'} needs")
        fc = at["ve"] - 2 * at["lone_pairs"] - order_sum[aid]
        fc_sum += fc
        atoms_out.append({"id": aid, "element": at["element"], "lone_pairs": at["lone_pairs"],
                          "bond_order_sum": order_sum[aid], "formal_charge": fc})
    if fc_sum != charge:
        raise BuildError(f"{ctx}: formal charges sum to {fc_sum}, not the molecular charge {charge}")

    # ── VSEPR geometry — the machine-derived domain count keys the SOURCED table (regime-3, ADR-0044) ──
    if not data.vsepr:
        raise BuildError(f"{ctx}: molecule geometry needs data/vsepr.toml")
    central = spec["central"]
    lp_central = atoms[central]["lone_pairs"]
    domains = neighbors[central] + lp_central
    geo = data.vsepr.get((domains, lp_central))
    if geo is None:
        raise BuildError(f"{ctx}: no VSEPR geometry for ({domains} domains, {lp_central} lone pairs) in "
                         f"data/vsepr.toml — expanded octets are deferred")
    geometry = {"central": central, "central_element": atoms[central]["element"],
                "domains": domains, "lone_pairs": lp_central,
                "electron_geometry": geo["electron_geometry"], "molecular_shape": geo["molecular_shape"],
                "ideal_angle": geo["ideal_angle"], "source": data.sources.get("vsepr", "")}
    if geo["angle_note"]:
        geometry["angle_note"] = geo["angle_note"]

    entry = {
        "kind": "molecule",
        "id": spec["id"],
        "title": spec["title"],
        "formula": spec["formula"],
        "latex": f.latex,
        "names": list(spec["names"]),
        "charge": charge,
        "valence_electrons": valence,
        "valence_breakdown": valence_breakdown,
        "electron_check": {"bonding": bonding_e, "nonbonding": nonbonding_e, "total": bonding_e + nonbonding_e},
        "atoms": atoms_out,
        "bonds": bonds_out,
        "geometry": geometry,
        "summary": spec["summary"],
        "source": spec["source"],
        "en_source": data.sources.get("electronegativity", ""),
        "bonding_source": data.sources.get("bonding", ""),
        "related": spec.get("related", []),
        "lessons": spec.get("lessons", []),
    }

    # molecular polarity — authored + disclosed (model-assumed). A charged species carries a net charge, not a
    # dipole in the neutral-molecule sense, so polarity is stated only for neutral molecules and forbidden on ions.
    polarity = spec.get("polarity")
    if charge != 0:
        if polarity is not None:
            raise BuildError(f"{ctx}: a charged species ('{spec['formula']}') carries a net charge, not a "
                             f"molecular polarity — omit `polarity`")
    else:
        if polarity is None:
            raise BuildError(f"{ctx}: neutral molecule '{spec['formula']}' must state its `polarity`")
        if polarity not in _POLARITY:
            raise BuildError(f"{ctx}: polarity '{polarity}' must be one of {_POLARITY}")
        if not spec.get("polarity_reason"):
            raise BuildError(f"{ctx}: polarity needs a `polarity_reason` (the disclosed dipole argument)")
        entry["polarity"] = polarity
        entry["polarity_reason"] = spec["polarity_reason"]

    if "notes" in spec:
        entry["notes"] = list(spec["notes"])
    return entry
