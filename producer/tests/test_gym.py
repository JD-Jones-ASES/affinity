"""Dimensional-analysis gym generator: verified conversions, determinism, independent re-derivation (ADR-0024)."""

import tomllib
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

import pytest

from chemkernel import BuildError
from chemkernel.data import ChemData
from chemkernel.gym import generate_gym

ROOT = Path(__file__).resolve().parents[2]
SPEC = ROOT / "gyms" / "dimensional-analysis" / "solution-conversions.gym.toml"
SPEC_NOMENCLATURE = ROOT / "gyms" / "nomenclature" / "ionic-compounds.gym.toml"

_TARGET = {
    "volume_molarity_to_moles": "mol", "moles_molarity_to_volume": "mL", "mass_to_moles": "mol",
    "moles_to_mass": "g", "volume_molarity_to_mass": "g",
}


def _spec():
    return tomllib.loads(SPEC.read_text(encoding="utf-8"))


def _gym(seed=None, count=None):
    spec = dict(_spec())
    if seed is not None:
        spec["seed"] = seed
    if count is not None:
        spec["count"] = count
    return generate_gym(spec, ChemData.load(ROOT), spec["id"])


def _rederive(kind, i):
    """The same unit arithmetic a student does — computed independently of the generator, exactly."""
    v = lambda k: Fraction(Decimal(i[k]))
    return {
        "volume_molarity_to_moles": lambda: v("v_mL") / 1000 * v("c_M"),
        "moles_molarity_to_volume": lambda: v("n_mol") / v("c_M") * 1000,
        "mass_to_moles": lambda: v("m_g") / v("molar_mass_g_per_mol"),
        "moles_to_mass": lambda: v("n_mol") * v("molar_mass_g_per_mol"),
        "volume_molarity_to_mass": lambda: v("v_mL") / 1000 * v("c_M") * v("molar_mass_g_per_mol"),
    }[kind]()


def test_shape_and_kind_coverage():
    g = _gym()
    assert g["kind"] == "gym" and g["id"] == "dimensional-analysis-solution-conversions"
    assert g["family"] == "solution_conversions_v1"
    assert len(g["problems"]) == 10
    assert {p["kind"] for p in g["problems"]} == set(_TARGET)              # all five conversion kinds appear
    assert g["provenance"]["sources"]["atomic_weight"] == "ciaaw-2021-atomic-weights"
    for p in g["problems"]:
        assert p["id"].startswith("q") and p["prompt"] and p["explain"]
        assert len(p["chain"]) >= 2
        assert p["chain"][-1]["unit"] == p["target_unit"] == p["answer"]["unit"] == _TARGET[p["kind"]]
        assert sum(1 for c in p["choices"] if c["correct"]) == 1
        assert len({c["display"] for c in p["choices"]}) == len(p["choices"])   # distinct displays
        for c in p["choices"]:
            assert c["correct"] or c["misconception"]                     # every wrong choice names a mistake


def test_answers_rederive_exactly_from_inputs():
    g = _gym()
    for p in g["problems"]:
        want = _rederive(p["derivation"]["kind"], p["derivation"]["inputs"])
        assert Fraction(Decimal(p["answer"]["value"])) == want            # engine value == independent re-derivation
        assert Fraction(Decimal(p["chain"][-1]["value"])) == want         # the chain ends exactly at the answer
        assert p["answer"]["display"] == next(c["display"] for c in p["choices"] if c["correct"])


def test_answers_are_terminating_decimals():
    for p in _gym()["problems"]:
        s = p["answer"]["value"]
        assert "/" not in s and "e" not in s.lower()                      # a plain terminating decimal, not a ratio
        Decimal(s)


def test_deterministic_same_seed():
    assert _gym(seed=4242043) == _gym(seed=4242043)                       # byte-identical for a given seed (ADR-0008)
    assert _gym(seed=1)["problems"] != _gym(seed=4242043)["problems"]     # a different seed gives different problems


def test_unknown_family_refused():
    spec = dict(_spec())
    spec["family"] = "not_a_real_family"
    with pytest.raises(BuildError):
        generate_gym(spec, ChemData.load(ROOT), "x")


# ------------------------------ ionic nomenclature family (item 2) ------------------------------

def _nom_gym(seed=None):
    spec = dict(tomllib.loads(SPEC_NOMENCLATURE.read_text(encoding="utf-8")))
    if seed is not None:
        spec["seed"] = seed
    return generate_gym(spec, ChemData.load(ROOT), spec["id"])


def test_nomenclature_shape_and_both_directions():
    g = _nom_gym()
    assert g["family"] == "ionic_nomenclature_v1"
    assert len(g["problems"]) == 10
    assert {p["kind"] for p in g["problems"]} == {"ionic_formula_to_name", "ionic_name_to_formula"}
    for p in g["problems"]:
        assert "chain" not in p and "unit" not in p["answer"]          # nomenclature carries no numeric chain
        assert p["subscript_tokens"]                                    # tokens for view-side subscripting
        assert sum(1 for c in p["choices"] if c["correct"]) == 1
        assert len({c["display"] for c in p["choices"]}) == len(p["choices"])
        for c in p["choices"]:
            assert c["correct"] or c["misconception"]


def test_nomenclature_answers_match_engine():
    from chemkernel.nomenclature import formula_ionic, name_ionic
    data = ChemData.load(ROOT)
    for p in _nom_gym()["problems"]:
        d = p["derivation"]
        cat, an = data.ions[d["cation"]["id"]], data.ions[d["anion"]["id"]]
        assert name_ionic(cat, an) == d["name"]                        # engine reproduces the emitted name
        assert formula_ionic(cat, an)[0] == d["formula"]               # and the emitted formula
        want = d["name"] if p["kind"] == "ionic_formula_to_name" else d["formula"]
        other = d["formula"] if p["kind"] == "ionic_formula_to_name" else d["name"]
        assert p["answer"]["value"] == want
        assert other in p["prompt"]                                    # the prompt states the other representation


def test_nomenclature_deterministic():
    assert _nom_gym() == _nom_gym()
    assert _nom_gym(seed=99)["problems"] != _nom_gym()["problems"]
