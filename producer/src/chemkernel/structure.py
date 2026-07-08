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

import platform
from decimal import Decimal

from . import BuildError, __version__
from .formula import parse_formula
from .reference import valence_electrons

_POLARITY = ("polar", "nonpolar")

# The four teaching steps of a structure lesson, always in this order (ADR-0045). The producer fixes each
# step's title + regime (so the honesty badge is uniform across structure lessons — as a reaction lesson's
# tab names are fixed); the author supplies only the prose. Each step's regime is the badge the player shows:
# the electron ledger is machine-checked (regime-1), the shape is sourced (regime-3), polarity is a disclosed
# model (regime-2). This is the three-badge honesty model, layered over one molecule.
_STEP_META = [
    ("valence", "Count the valence electrons", "ledger-exact"),
    ("lewis", "Build the Lewis structure", "ledger-exact"),
    ("shape", "Predict the shape (VSEPR)", "rule-sourced"),
    ("polarity", "Decide the polarity", "model-exact"),
]
# the per-facet regime summary a structure lesson always carries — the electron ledger (machine-checked), the
# VSEPR geometry (sourced), and molecular polarity (disclosed model). Fixed: it IS the lesson's honesty shape.
_STRUCTURE_REGIMES = [
    {"facet": "electron ledger", "regime": "ledger-exact"},
    {"facet": "molecular geometry", "regime": "rule-sourced"},
    {"facet": "molecular polarity", "regime": "model-exact"},
]


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


def compute_ledger(atoms_spec: list, bonds_spec: list, central: str, formula_str: str, data,
                   ctx: str = "") -> dict:
    """The Lewis electron ledger of a structure — the machine-checked core (ADR-0044), shared by the molecule
    Atlas builder and the `lewis_structures_v1` gym. Given the atoms (id, element, lone_pairs) + bonds (a, b,
    order) + the central atom + the phase-less formula, it derives + VERIFIES the accounting and refuses any
    structure that fails: valence total, electron conservation, per-atom octet/duet, formal charge (Σ = charge),
    the VSEPR domain count → geometry, and each bond's ΔEN. Returns the emitted-shape blocks (latex, charge,
    valence_electrons, valence_breakdown, electron_check, atoms, bonds, geometry)."""
    f = parse_formula(formula_str, ctx)
    if f.phase is not None:
        raise BuildError(f"{ctx}: molecule formula '{formula_str}' must be phase-less (structure is authored)")

    # atoms: unique ids, known main-group elements with a defined valence-electron count
    atoms: dict[str, dict] = {}
    for a in atoms_spec:
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
                         f"'{formula_str}' composition {dict(f.counts)}")

    # bonds: valid endpoints, positive order; accumulate per-atom bond-order totals + neighbor (domain) counts
    order_sum = {aid: 0 for aid in atoms}
    neighbors = {aid: 0 for aid in atoms}
    if central not in atoms:
        raise BuildError(f"{ctx}: central atom '{central}' is not one of the atoms")
    bonds_out = []
    for b in bonds_spec:
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

    return {
        "latex": f.latex, "charge": charge, "valence_electrons": valence,
        "valence_breakdown": valence_breakdown,
        "electron_check": {"bonding": bonding_e, "nonbonding": nonbonding_e, "total": bonding_e + nonbonding_e},
        "atoms": atoms_out, "bonds": bonds_out, "geometry": geometry,
    }


_HBOND_ACCEPTORS = ("N", "O", "F")   # the small, strongly electronegative atoms that make a bonded H a donor


def classify_imf(atoms: list, bonds: list, polarity: str) -> dict:
    """The dominant intermolecular force of a NEUTRAL molecule (ADR-0046), derived from its VERIFIED structure +
    the machine-derived polarity. Every molecule has **London dispersion**; a **polar** molecule adds
    **dipole–dipole**; a molecule with an H bonded directly to N, O, or F adds **hydrogen bonding**. The DOMINANT
    force is the strongest TYPE present (hydrogen bonding > dipole–dipole > London dispersion) — the standard
    intro-chemistry rule (regime-3, a sourced convention; disclosed caveat: dispersion strength grows with
    size/polarizability, so for large molecules it can overtake a small dipole). The H-bond-donor detection is
    exact over the atoms + bonds (a graph fact of the verified structure); the ranking is the sourced rule."""
    element_of = {a["id"]: a["element"] for a in atoms}
    h_bond_donor = False
    for b in bonds:
        pair = {element_of.get(b["a"]), element_of.get(b["b"])}
        if "H" in pair and (pair & set(_HBOND_ACCEPTORS)):
            h_bond_donor = True
            break
    forces = ["london-dispersion"]                    # present in every molecule
    if polarity == "polar":
        forces.append("dipole-dipole")
    if h_bond_donor and polarity == "polar":          # hydrogen bonding presupposes a molecular dipole
        forces.append("hydrogen-bonding")
    dominant = ("hydrogen-bonding" if "hydrogen-bonding" in forces
                else "dipole-dipole" if "dipole-dipole" in forces
                else "london-dispersion")
    return {"dominant": dominant, "forces": forces, "h_bond_donor": h_bond_donor}


def build_molecule_entry(spec: dict, data, ctx: str = "") -> dict:
    """An authored molecule entry → the emitted Atlas object (ADR-0044). The electron ledger (valence total,
    octet, per-atom formal charge) is DERIVED from the authored atoms + bonds and machine-verified (via
    `compute_ledger`); the VSEPR geometry keys a sourced table on the machine-derived domain count; bond ΔEN
    comes from the sourced electronegativities; molecular polarity is authored + disclosed. The producer refuses
    any structure that fails electron conservation, an octet, or the formal-charge sum."""
    for key in ("id", "kind", "title", "formula", "names", "central", "summary", "source", "atoms", "bonds"):
        if key not in spec:
            raise BuildError(f"{ctx}: molecule entry missing required key '{key}'")
    if spec["kind"] != "molecule":
        raise BuildError(f"{ctx}: build_molecule_entry got kind '{spec['kind']}'")
    if not spec["names"]:
        raise BuildError(f"{ctx}: molecule entry needs at least one name")

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

    led = compute_ledger(spec["atoms"], spec["bonds"], spec["central"], spec["formula"], data, ctx)
    charge = led["charge"]

    entry = {
        "kind": "molecule",
        "id": spec["id"],
        "title": spec["title"],
        "formula": spec["formula"],
        "latex": led["latex"],
        "names": list(spec["names"]),
        "charge": charge,
        "valence_electrons": led["valence_electrons"],
        "valence_breakdown": led["valence_breakdown"],
        "electron_check": led["electron_check"],
        "atoms": led["atoms"],
        "bonds": led["bonds"],
        "geometry": led["geometry"],
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

    # intermolecular forces (ADR-0046) — for a NEUTRAL molecule only (IMFs act between neutral molecules; an ion's
    # interactions are ionic, a different regime). Derived from the verified structure + polarity; the sourced
    # normal boiling point is attached as evidence when curated (`data/boiling-points.toml`), keyed by formula.
    if charge == 0:
        imf = classify_imf(led["atoms"], led["bonds"], polarity)
        imf_block = {"dominant": imf["dominant"], "forces": imf["forces"], "h_bond_donor": imf["h_bond_donor"]}
        bp = data.boiling_points.get(spec["formula"])
        if bp is not None:
            imf_block["boiling_point_c"] = format(bp["temperature_c"], "f")
            imf_block["phase_change"] = bp["phase_change"]
            imf_block["boiling_source"] = data.sources.get("boiling_points", "")
        entry["intermolecular"] = imf_block

    if "notes" in spec:
        entry["notes"] = list(spec["notes"])
    return entry


_IMF_RANK = {"london-dispersion": 1, "dipole-dipole": 2, "hydrogen-bonding": 3}   # strength order (ADR-0046)


def build_comparison_lesson(spec: dict, molecule_entries: dict, data, ctx: str = "") -> dict:
    """An authored multi-molecule comparison lesson → the verified `*.comparison.json` object (ADR-0047) — the
    third lesson shape. It lines up several molecules against a measurable property (boiling point) and teaches
    the trend, and its machine-checkable spine is exactly that trend: **sorted by boiling point ascending, the
    dominant-IMF rank is non-decreasing** (IMF strength predicts the ordering). Each row is re-embedded from the
    verified `molecule` Atlas entry (`molecule_entries[id]`, built by build_molecule_entry — so the IMF + boiling
    point are the same machine-derived/sourced values, no drift). The producer REFUSES to emit if the authored
    corpus does not exhibit the trend (ADR-0008) — it will not teach a false claim."""
    for key in ("id", "title", "slug", "topic", "scenario", "property", "molecules", "trend", "takeaway",
                "misconception"):
        if key not in spec:
            raise BuildError(f"{ctx}: comparison lesson missing required key '{key}'")
    mol_ids = spec["molecules"]
    if not isinstance(mol_ids, list) or len(mol_ids) < 2:
        raise BuildError(f"{ctx}: a comparison lesson needs at least two `molecules`")

    rows = []
    for mid in mol_ids:
        entry = molecule_entries.get(mid)
        if entry is None:
            raise BuildError(f"{ctx}: molecule '{mid}' resolves to no reference/molecules/*.toml entry")
        imf = entry.get("intermolecular")
        if imf is None:
            raise BuildError(f"{ctx}: '{mid}' has no intermolecular block (a charged species?) — cannot compare IMFs")
        if "boiling_point_c" not in imf:
            raise BuildError(f"{ctx}: '{mid}' has no curated boiling point in data/boiling-points.toml — "
                             f"cannot compare on boiling point")
        rows.append({
            "ref_id": mid, "formula": entry["formula"], "latex": entry["latex"], "names": list(entry["names"]),
            "dominant": imf["dominant"], "forces": list(imf["forces"]), "imf_rank": _IMF_RANK[imf["dominant"]],
            "boiling_point_c": imf["boiling_point_c"], "phase_change": imf["phase_change"],
            "boiling_source": imf["boiling_source"],
        })

    # sort ascending by boiling point (Decimal — exact compare, ADR-0013)
    rows.sort(key=lambda r: Decimal(r["boiling_point_c"]))
    # the machine-checked payoff: the dominant-IMF rank is non-decreasing as the boiling point rises. If the
    # authored corpus breaks it (a stronger IMF at a lower boiling point), REFUSE — the lesson would teach a
    # false trend.
    for a, b in zip(rows, rows[1:]):
        if b["imf_rank"] < a["imf_rank"]:
            raise BuildError(f"{ctx}: IMF trend not monotonic — {a['formula']} ({a['dominant']}, "
                             f"{a['boiling_point_c']} °C) then {b['formula']} ({b['dominant']}, "
                             f"{b['boiling_point_c']} °C): a stronger intermolecular force at a lower boiling "
                             f"point breaks the claim this lesson teaches")

    return {
        "kind": "comparison",
        "id": spec["id"],
        "title": spec["title"],
        "slug": spec["slug"],
        "topic": spec["topic"],
        "tags": spec.get("tags", []),
        "scenario": spec["scenario"],
        "property": spec["property"],
        "regimes": [dict(r) for r in _STRUCTURE_REGIMES],   # electron ledger / geometry / polarity all feed the IMF
        "assumptions": spec.get("assumptions", []),
        "rows": rows,
        "trend": {"property": spec["property"], "monotonic": True, "claim": spec["trend"]},
        "takeaway": spec["takeaway"],
        "misconception": spec["misconception"],
        "reference_links": spec.get("reference_links", []),
        "checks": {"sorted_ascending": True, "imf_trend_monotonic": True, "rows_match_atlas": True},
        "provenance": {
            "producer": "chemkernel",
            "version": __version__,
            "python": platform.python_version(),
            "author": spec.get("author", "Affinity"),
            "created": spec.get("created", ""),
            "sources": {"boiling_points": data.sources.get("boiling_points", "")},
        },
    }


def build_structure_lesson(spec: dict, molecule_spec: dict, data, ctx: str = "") -> dict:
    """An authored structure lesson → the verified `*.structure.json` lesson object (ADR-0045). This is the
    electron ledger's presentation shape generalised past a reaction to a single molecule: no equations, no
    species ledger over extent, no reported product — the pivot is the Lewis ELECTRON ledger, machine-checked.

    The lesson names a `molecule` Atlas entry (`spec['molecule']`); `molecule_spec` is that entry's authored
    TOML, resolved by build.py. The ledger is re-derived from its authored atoms + bonds by `compute_ledger` —
    the SAME engine the Atlas builder and the `lewis_structures_v1` gym use, so the lesson can never describe a
    different structure than the Atlas (and the gate re-derives it again in pure Node + matches it to the Atlas
    JSON). The producer REFUSES to emit on any electron-accounting failure, exactly as build.py refuses an
    unbalanced reaction (ADR-0008). The four teaching steps carry authored prose over the fixed step frame."""
    for key in ("id", "title", "slug", "topic", "scenario", "molecule", "steps", "misconception"):
        if key not in spec:
            raise BuildError(f"{ctx}: structure lesson missing required key '{key}'")

    led = compute_ledger(molecule_spec["atoms"], molecule_spec["bonds"], molecule_spec["central"],
                         molecule_spec["formula"], data, ctx)
    # a structure lesson's payoff is molecular polarity — stated only for a neutral molecule (a charged ion
    # carries a net charge, not a dipole). So the lesson's molecule must be neutral and carry a disclosed reason.
    if led["charge"] != 0:
        raise BuildError(f"{ctx}: structure lesson molecule '{molecule_spec['formula']}' is charged "
                         f"({led['charge']}) — a polarity payoff needs a neutral molecule")
    for key in ("polarity", "polarity_reason", "names"):
        if not molecule_spec.get(key):
            raise BuildError(f"{ctx}: referenced molecule '{molecule_spec.get('id')}' is missing '{key}'")
    if molecule_spec["polarity"] not in _POLARITY:
        raise BuildError(f"{ctx}: molecule polarity '{molecule_spec['polarity']}' must be one of {_POLARITY}")

    molecule = {
        "ref_id": molecule_spec["id"],
        "formula": molecule_spec["formula"],
        "latex": led["latex"],
        "names": list(molecule_spec["names"]),
        "charge": led["charge"],
        "valence_electrons": led["valence_electrons"],
        "valence_breakdown": led["valence_breakdown"],
        "electron_check": led["electron_check"],
        "atoms": led["atoms"],
        "bonds": led["bonds"],
        "geometry": led["geometry"],   # carries its own sourced `source` (data/vsepr.toml)
        "polarity": molecule_spec["polarity"],
        "polarity_reason": molecule_spec["polarity_reason"],
        "en_source": data.sources.get("electronegativity", ""),
        "bonding_source": data.sources.get("bonding", ""),
    }

    # the four steps: fixed frame (key/title/regime) + authored prose. `[steps]` is a table of exactly the four
    # keys; an unexpected key is the TOML trap-#4 signature (a bare key absorbed into the table) — refuse it.
    steps_spec = spec["steps"]
    if not isinstance(steps_spec, dict):
        raise BuildError(f"{ctx}: [steps] must be a table with keys valence/lewis/shape/polarity")
    expected = {k for k, _t, _r in _STEP_META}
    extra = set(steps_spec) - expected
    if extra:
        raise BuildError(f"{ctx}: [steps] carries unexpected key(s) {sorted(extra)} — a top-level bare key was "
                         f"absorbed into [steps] (bare keys must precede any [table] header)")
    steps = []
    for key, title, regime in _STEP_META:
        prose = steps_spec.get(key)
        if not prose or not str(prose).strip():
            raise BuildError(f"{ctx}: [steps].{key} prose is missing or empty")
        steps.append({"key": key, "title": title, "regime": regime, "prose": prose})

    return {
        "kind": "structure",
        "id": spec["id"],
        "title": spec["title"],
        "slug": spec["slug"],
        "topic": spec["topic"],
        "tags": spec.get("tags", []),
        "scenario": spec["scenario"],
        "regimes": [dict(r) for r in _STRUCTURE_REGIMES],
        "assumptions": spec.get("assumptions", []),
        "molecule": molecule,
        "steps": steps,
        "misconception": spec["misconception"],
        "reference_links": spec.get("reference_links", []),
        # the machine-checked facts, SHOWN not asserted (compute_ledger raised if any failed) — the structure
        # lesson's counterpart of a reaction lesson's atom/charge/unit/extent checks.
        "checks": {"electrons_conserved": True, "octets_complete": True,
                   "formal_charge_sum": True, "geometry_keyed": True},
        "provenance": {
            "producer": "chemkernel",
            "version": __version__,
            "python": platform.python_version(),
            "author": spec.get("author", "Affinity"),
            "created": spec.get("created", ""),
            # every value is traceable: valence electrons from the IUPAC group (ADR-0033), the geometry from the
            # sourced VSEPR table, bond ΔEN from the sourced electronegativities + thresholds.
            "sources": {
                "valence_electrons": data.sources.get("position", ""),
                "geometry": data.sources.get("vsepr", ""),
                "electronegativity": data.sources.get("electronegativity", ""),
                "bonding": data.sources.get("bonding", ""),
            },
        },
    }
