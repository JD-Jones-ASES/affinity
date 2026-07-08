"""Lewis electron-ledger engine (ADR-0044): valence total, octet/duet, formal charge, VSEPR geometry, bond
ΔEN — the machine-checked electron accounting, and every refusal that keeps a bad structure from shipping."""

import copy
import tomllib
from pathlib import Path

import pytest

from chemkernel import BuildError
from chemkernel.data import ChemData
from chemkernel.structure import build_molecule_entry, build_structure_lesson, classify_imf

ROOT = Path(__file__).resolve().parents[2]


def _data():
    return ChemData.load(ROOT)


def _mol(spec):
    return build_molecule_entry(spec, _data(), ctx=spec.get("id", "test"))


def _lesson(spec, molecule_spec):
    return build_structure_lesson(spec, molecule_spec, _data(), ctx=spec.get("id", "test"))


# ── base specs (valid) — copied + mutated for the refusal tests ──
WATER = {
    "kind": "molecule", "id": "molecule-water", "title": "Water", "formula": "H2O",
    "names": ["water"], "central": "O1", "summary": "water", "source": "openstax-chemistry-2e",
    "polarity": "polar", "polarity_reason": "bent, so the O–H dipoles do not cancel",
    "atoms": [{"id": "O1", "element": "O", "lone_pairs": 2},
              {"id": "H1", "element": "H", "lone_pairs": 0},
              {"id": "H2", "element": "H", "lone_pairs": 0}],
    "bonds": [{"a": "O1", "b": "H1", "order": 1}, {"a": "O1", "b": "H2", "order": 1}],
}
CO2 = {
    "kind": "molecule", "id": "molecule-carbon-dioxide", "title": "Carbon dioxide", "formula": "CO2",
    "names": ["carbon dioxide"], "central": "C1", "summary": "co2", "source": "openstax-chemistry-2e",
    "polarity": "nonpolar", "polarity_reason": "linear, the two C=O dipoles cancel",
    "atoms": [{"id": "C1", "element": "C", "lone_pairs": 0},
              {"id": "O1", "element": "O", "lone_pairs": 2},
              {"id": "O2", "element": "O", "lone_pairs": 2}],
    "bonds": [{"a": "C1", "b": "O1", "order": 2}, {"a": "C1", "b": "O2", "order": 2}],
}
NH4 = {
    "kind": "molecule", "id": "molecule-ammonium", "title": "Ammonium", "formula": "NH4^+",
    "names": ["ammonium"], "central": "N1", "summary": "ammonium", "source": "openstax-chemistry-2e",
    "atoms": [{"id": "N1", "element": "N", "lone_pairs": 0},
              {"id": "H1", "element": "H", "lone_pairs": 0},
              {"id": "H2", "element": "H", "lone_pairs": 0},
              {"id": "H3", "element": "H", "lone_pairs": 0},
              {"id": "H4", "element": "H", "lone_pairs": 0}],
    "bonds": [{"a": "N1", "b": "H1", "order": 1}, {"a": "N1", "b": "H2", "order": 1},
              {"a": "N1", "b": "H3", "order": 1}, {"a": "N1", "b": "H4", "order": 1}],
}


def test_water_electron_ledger():
    m = _mol(WATER)
    assert m["valence_electrons"] == 8                      # 2×1 (H) + 6 (O)
    assert m["electron_check"] == {"bonding": 4, "nonbonding": 4, "total": 16 - 8}  # 4 bonding + 4 nonbonding = 8
    assert all(a["formal_charge"] == 0 for a in m["atoms"])
    o = next(a for a in m["atoms"] if a["id"] == "O1")
    assert o["lone_pairs"] == 2 and o["bond_order_sum"] == 2
    # 4 domains (2 bonds + 2 lone pairs), tetrahedral electron geometry → bent molecular shape
    assert m["geometry"]["domains"] == 4 and m["geometry"]["lone_pairs"] == 2
    assert m["geometry"]["electron_geometry"] == "tetrahedral" and m["geometry"]["molecular_shape"] == "bent"
    assert m["geometry"]["source"] == "openstax-chemistry-2e"
    # bond ΔEN from the sourced electronegativities: |3.44 − 2.20| = 1.24, polar covalent
    assert m["bonds"][0]["delta_en"] == "1.24" and m["bonds"][0]["bond_class"] == "polar-covalent"
    assert m["polarity"] == "polar"


def test_co2_polar_bonds_nonpolar_molecule():
    m = _mol(CO2)
    assert m["valence_electrons"] == 16
    assert m["electron_check"] == {"bonding": 8, "nonbonding": 8, "total": 16}
    assert all(a["formal_charge"] == 0 for a in m["atoms"])
    assert m["geometry"]["domains"] == 2 and m["geometry"]["molecular_shape"] == "linear"
    # each C=O is a polar bond, yet the molecule is nonpolar — the marquee teaching contrast
    assert all(b["polar"] and b["delta_en"] == "0.89" for b in m["bonds"])
    assert m["polarity"] == "nonpolar"


def test_ammonium_formal_charge_on_nitrogen():
    m = _mol(NH4)
    assert m["charge"] == 1
    assert m["valence_electrons"] == 8                      # 5 (N) + 4×1 (H) − 1 (charge)
    n = next(a for a in m["atoms"] if a["id"] == "N1")
    assert n["formal_charge"] == 1                          # 5 − 0 − 4 = +1: the ion's charge sits on N
    assert sum(a["formal_charge"] for a in m["atoms"]) == 1  # Σ formal charges = the ion charge
    assert m["geometry"]["molecular_shape"] == "tetrahedral"
    assert "polarity" not in m                              # a charged species states no molecular polarity


def test_refuse_electrons_not_conserved():
    bad = copy.deepcopy(WATER)
    bad["atoms"][0]["lone_pairs"] = 1                       # O with one lone pair → only 6 electrons placed
    with pytest.raises(BuildError, match="not conserved"):
        _mol(bad)


def test_refuse_incomplete_octet():
    # BeH2: electrons conserve (4 = 2 bonds), but beryllium reaches only 4 — the strict octet is enforced,
    # electron-deficient molecules are deferred (documents the opener's scope).
    beh2 = copy.deepcopy(WATER)
    beh2.update(id="beh2", formula="BeH2", central="Be1", polarity="nonpolar", polarity_reason="x",
                atoms=[{"id": "Be1", "element": "Be", "lone_pairs": 0},
                       {"id": "H1", "element": "H", "lone_pairs": 0},
                       {"id": "H2", "element": "H", "lone_pairs": 0}],
                bonds=[{"a": "Be1", "b": "H1", "order": 1}, {"a": "Be1", "b": "H2", "order": 1}])
    with pytest.raises(BuildError, match="octet"):
        _mol(beh2)


def test_refuse_off_dataset_element():
    bad = copy.deepcopy(WATER)
    bad["atoms"][0]["element"] = "Xe"                       # not in data/elements.toml
    with pytest.raises(BuildError, match="absent from data/elements.toml"):
        _mol(bad)


def test_refuse_non_main_group_element():
    bad = copy.deepcopy(WATER)
    bad.update(formula="FeH2", atoms=[{"id": "O1", "element": "Fe", "lone_pairs": 2},
                                      {"id": "H1", "element": "H", "lone_pairs": 0},
                                      {"id": "H2", "element": "H", "lone_pairs": 0}])
    with pytest.raises(BuildError, match="no defined valence-electron count"):
        _mol(bad)


def test_refuse_phase_in_formula():
    bad = copy.deepcopy(WATER)
    bad["formula"] = "H2O(l)"
    with pytest.raises(BuildError, match="phase-less"):
        _mol(bad)


def test_refuse_atoms_disagree_with_formula():
    bad = copy.deepcopy(WATER)
    bad["formula"] = "H2O2"                                 # atoms are H2O, formula says H2O2
    with pytest.raises(BuildError, match="do not match the formula"):
        _mol(bad)


def test_refuse_polarity_on_a_charged_species():
    bad = copy.deepcopy(NH4)
    bad["polarity"] = "polar"
    bad["polarity_reason"] = "x"
    with pytest.raises(BuildError, match="charged species"):
        _mol(bad)


def test_refuse_neutral_without_polarity():
    bad = copy.deepcopy(WATER)
    del bad["polarity"]
    with pytest.raises(BuildError, match="must state its .polarity"):
        _mol(bad)


def test_refuse_uncovered_geometry():
    # HCl with Cl as the central atom is 1 bond + 3 lone pairs = 4 domains / 3 lone pairs — a trivially linear
    # diatomic the VSEPR table deliberately omits (deferred). Octet + conservation pass; the geometry lookup
    # is what refuses it.
    hcl = copy.deepcopy(WATER)
    hcl.update(id="hcl", formula="HCl", central="Cl1", polarity="polar", polarity_reason="x",
               atoms=[{"id": "Cl1", "element": "Cl", "lone_pairs": 3},
                      {"id": "H1", "element": "H", "lone_pairs": 0}],
               bonds=[{"a": "Cl1", "b": "H1", "order": 1}])
    with pytest.raises(BuildError, match="no VSEPR geometry"):
        _mol(hcl)


def test_trap4_guard_rejects_absorbed_key():
    bad = copy.deepcopy(WATER)
    bad["atoms"][0]["lessons"] = []                          # a bare key absorbed into the last [[atoms]] table
    with pytest.raises(BuildError, match="unexpected key"):
        _mol(bad)


def test_all_authored_molecules_build():
    data = _data()
    for path in sorted((ROOT / "reference" / "molecules").glob("*.toml")):
        spec = tomllib.loads(path.read_text(encoding="utf-8"))
        entry = build_molecule_entry(spec, data, ctx=spec["id"])
        assert entry["kind"] == "molecule"
        # electron conservation holds for every shipped molecule
        assert entry["electron_check"]["total"] == entry["valence_electrons"]
        assert sum(a["formal_charge"] for a in entry["atoms"]) == entry["charge"]


# ── structure lessons (ADR-0045): the single-molecule lesson shape, sharing the compute_ledger engine ──
LESSON = {
    "id": "bonding-water-molecular-shape", "title": "Why water is bent", "slug": "water-molecular-shape",
    "topic": "bonding", "scenario": "Water looks linear. It isn't.", "molecule": "molecule-water",
    "steps": {"valence": "Count the 8 valence electrons.", "lewis": "Place two O–H bonds and two lone pairs.",
              "shape": "Four domains → bent.", "polarity": "Bent, so polar."},
    "misconception": {"claim": "Water is linear.", "refuted_by": "lone_pairs_are_electron_domains"},
}


def test_structure_lesson_shape():
    les = _lesson(LESSON, WATER)
    assert les["kind"] == "structure" and les["slug"] == "water-molecular-shape" and les["topic"] == "bonding"
    assert les["molecule"]["ref_id"] == "molecule-water"
    assert les["molecule"]["valence_electrons"] == 8 and les["molecule"]["charge"] == 0
    assert les["molecule"]["polarity"] == "polar"
    # the four steps in canonical order, with the producer-fixed titles/regimes + authored prose
    assert [s["key"] for s in les["steps"]] == ["valence", "lewis", "shape", "polarity"]
    assert [s["regime"] for s in les["steps"]] == ["ledger-exact", "ledger-exact", "rule-sourced", "model-exact"]
    assert les["steps"][0]["title"] == "Count the valence electrons"
    # the machine-checked facts are SHOWN (all true — compute_ledger raised otherwise)
    assert les["checks"] == {"electrons_conserved": True, "octets_complete": True,
                             "formal_charge_sum": True, "geometry_keyed": True}
    # the per-facet regime summary + traceable sources
    assert {r["regime"] for r in les["regimes"]} == {"ledger-exact", "rule-sourced", "model-exact"}
    assert les["provenance"]["sources"]["valence_electrons"] and les["provenance"]["sources"]["geometry"]


def test_structure_lesson_reuses_compute_ledger():
    # the lesson's embedded ledger must be identical to the molecule Atlas entry's — one engine, no drift
    les = _lesson(LESSON, WATER)
    atlas = _mol(WATER)
    for key in ("valence_electrons", "valence_breakdown", "electron_check", "atoms", "bonds", "geometry", "charge"):
        assert les["molecule"][key] == atlas[key], f"{key} drifts from the Atlas molecule"


def test_refuse_charged_molecule_lesson():
    # a structure lesson's payoff is polarity — forbidden on an ion; NH4+ must be refused
    with pytest.raises(BuildError, match="charged"):
        _lesson({**LESSON, "molecule": "molecule-ammonium"}, NH4)


def test_refuse_missing_step():
    bad = copy.deepcopy(LESSON)
    del bad["steps"]["shape"]
    with pytest.raises(BuildError, match="shape.* prose is missing"):
        _lesson(bad, WATER)


def test_refuse_empty_step_prose():
    bad = copy.deepcopy(LESSON)
    bad["steps"]["polarity"] = "   "
    with pytest.raises(BuildError, match="polarity.* prose is missing"):
        _lesson(bad, WATER)


def test_steps_trap4_guard():
    bad = copy.deepcopy(LESSON)
    bad["steps"]["author"] = "Affinity"                     # a bare key absorbed into [steps]
    with pytest.raises(BuildError, match="unexpected key"):
        _lesson(bad, WATER)


def test_refuse_missing_required_lesson_key():
    bad = copy.deepcopy(LESSON)
    del bad["scenario"]
    with pytest.raises(BuildError, match="missing required key 'scenario'"):
        _lesson(bad, WATER)


# ── intermolecular forces (ADR-0046): dominant IMF from the verified structure + polarity ──
def _atoms(*pairs):
    return [{"id": i, "element": e} for i, e in pairs]


def test_imf_hydrogen_bonding_water():
    # H bonded to O + polar → hydrogen bonding is the dominant force; all three forces present
    imf = classify_imf(_atoms(("O1", "O"), ("H1", "H"), ("H2", "H")),
                        [{"a": "O1", "b": "H1"}, {"a": "O1", "b": "H2"}], "polar")
    assert imf["h_bond_donor"] is True
    assert imf["dominant"] == "hydrogen-bonding"
    assert imf["forces"] == ["london-dispersion", "dipole-dipole", "hydrogen-bonding"]


def test_imf_dipole_dipole_formaldehyde():
    # CH2O is polar, but its H's are bonded to CARBON (not N/O/F) — no H-bond DONOR, so dipole-dipole dominates
    imf = classify_imf(_atoms(("C1", "C"), ("O1", "O"), ("H1", "H"), ("H2", "H")),
                       [{"a": "C1", "b": "O1"}, {"a": "C1", "b": "H1"}, {"a": "C1", "b": "H2"}], "polar")
    assert imf["h_bond_donor"] is False
    assert imf["dominant"] == "dipole-dipole"
    assert "hydrogen-bonding" not in imf["forces"]


def test_imf_dispersion_only_nonpolar():
    # a nonpolar molecule (CH4) has only London dispersion, whatever its bonds
    imf = classify_imf(_atoms(("C1", "C"), ("H1", "H"), ("H2", "H"), ("H3", "H"), ("H4", "H")),
                       [{"a": "C1", "b": h} for h in ("H1", "H2", "H3", "H4")], "nonpolar")
    assert imf["dominant"] == "london-dispersion" and imf["forces"] == ["london-dispersion"]


def test_molecule_entry_carries_imf_block():
    m = _mol(WATER)
    assert m["intermolecular"]["dominant"] == "hydrogen-bonding"
    assert m["intermolecular"]["boiling_point_c"] == "100.0" and m["intermolecular"]["phase_change"] == "boiling"
    assert m["intermolecular"]["boiling_source"]                       # sourced evidence attached
    co2 = _mol(CO2)
    assert co2["intermolecular"]["dominant"] == "london-dispersion"
    assert co2["intermolecular"]["phase_change"] == "sublimation"      # CO2 has no liquid at 1 atm
    # a charged species carries NO intermolecular block (IMFs are between neutral molecules)
    assert "intermolecular" not in _mol(NH4)


def test_all_authored_structure_lessons_build():
    # every shipped structure lesson + its referenced molecule TOML build end to end
    data = _data()
    molecules = {}
    for path in (ROOT / "reference" / "molecules").glob("*.toml"):
        s = tomllib.loads(path.read_text(encoding="utf-8"))
        molecules[s["id"]] = s
    lessons = sorted((ROOT / "problems").glob("**/*.structure.toml"))
    assert lessons, "no structure lessons found"
    for path in lessons:
        spec = tomllib.loads(path.read_text(encoding="utf-8"))
        les = build_structure_lesson(spec, molecules[spec["molecule"]], data, ctx=spec["id"])
        assert les["kind"] == "structure" and les["molecule"]["ref_id"] == spec["molecule"]
        assert [s["key"] for s in les["steps"]] == ["valence", "lewis", "shape", "polarity"]
        assert les["molecule"]["charge"] == 0                # a structure lesson's molecule is neutral (polarity)
        # electron conservation holds for the embedded ledger
        assert les["molecule"]["electron_check"]["total"] == les["molecule"]["valence_electrons"]
