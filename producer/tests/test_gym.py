"""Dimensional-analysis gym generator: verified conversions, determinism, independent re-derivation (ADR-0024)."""

import tomllib
from decimal import Decimal
from fractions import Fraction
from functools import reduce
from math import gcd
from pathlib import Path

import pytest

from chemkernel import BuildError
from chemkernel.data import ChemData
from chemkernel.formula import parse_formula
from chemkernel.gym import generate_gym

ROOT = Path(__file__).resolve().parents[2]
SPEC = ROOT / "gyms" / "dimensional-analysis" / "solution-conversions.gym.toml"
SPEC_NOMENCLATURE = ROOT / "gyms" / "nomenclature" / "ionic-compounds.gym.toml"
SPEC_BALANCING = ROOT / "gyms" / "balancing" / "balance-equations.gym.toml"
SPEC_MASS_STOICH = ROOT / "gyms" / "stoichiometry" / "mass-stoichiometry.gym.toml"
SPEC_PERCENT_YIELD = ROOT / "gyms" / "stoichiometry" / "percent-yield.gym.toml"
SPEC_LIMITING_MASS = ROOT / "gyms" / "stoichiometry" / "limiting-reagent.gym.toml"

_TARGET = {
    "volume_molarity_to_moles": "mol", "moles_molarity_to_volume": "mL", "mass_to_moles": "mol",
    "moles_to_mass": "g", "volume_molarity_to_mass": "g",
}


def _assert_numeric_response(p):
    """A numeric answer is free-entry (ADR-0032): a diagnostics catalogue, never a gameable menu. Each
    diagnostic names a mistake, shares the answer's unit, and is genuinely distinct from the answer (>3%,
    matching the gate) so it can never mis-flag a correct entry."""
    assert p["mode"] == "numeric"
    assert "choices" not in p                                    # no multiple-choice menu to eliminate
    ans = float(p["answer"]["value"])
    for dgn in p["diagnostics"]:
        assert dgn["misconception"]
        assert dgn["unit"] == p["answer"]["unit"]
        assert abs(float(dgn["value"]) - ans) > 0.03 * max(abs(ans), 1e-9)


def _assert_choice_menu(p):
    """A categorical answer is multiple choice: exactly one correct, distinct plausible same-form options,
    every wrong one names a mistake, and the correct one is the answer."""
    assert p["mode"] == "choice"
    assert "diagnostics" not in p
    assert sum(1 for c in p["choices"] if c["correct"]) == 1
    assert len({c["display"] for c in p["choices"]}) == len(p["choices"])
    for c in p["choices"]:
        assert c["correct"] or c["misconception"]
    assert p["answer"]["display"] == next(c["display"] for c in p["choices"] if c["correct"])


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
        _assert_numeric_response(p)                                        # free entry + a diagnostics catalogue


def test_answers_rederive_exactly_from_inputs():
    g = _gym()
    for p in g["problems"]:
        want = _rederive(p["derivation"]["kind"], p["derivation"]["inputs"])
        assert Fraction(Decimal(p["answer"]["value"])) == want            # engine value == independent re-derivation
        assert Fraction(Decimal(p["chain"][-1]["value"])) == want         # the chain ends exactly at the answer


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
        _assert_choice_menu(p)                                          # categorical → a plausible same-form menu


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


# ------------------------------ balancing family (item 3, ADR-0028) ------------------------------

def _bal_gym(seed=None):
    spec = dict(tomllib.loads(SPEC_BALANCING.read_text(encoding="utf-8")))
    if seed is not None:
        spec["seed"] = seed
    return generate_gym(spec, ChemData.load(ROOT), spec["id"])


def _side_total(species, coeffs, key, role):
    """Total of one conserved quantity (an element symbol or 'charge') on one side — computed independently."""
    return sum((s["charge"] if key == "charge" else s["counts"].get(key, 0)) * c
               for s, c in zip(species, coeffs) if s["role"] == role)


def test_balancing_shape_and_engine():
    g = _bal_gym()
    assert g["family"] == "balancing_v1"
    assert len(g["problems"]) == 10
    assert {p["kind"] for p in g["problems"]} == {"balancing"}
    for p in g["problems"]:
        d = p["derivation"]
        assert p["prompt"].startswith("Balance:")
        assert "chain" not in p and "unit" not in p["answer"]        # balancing carries no numeric chain/unit
        assert p["subscript_tokens"]                                  # formula tokens for view-side subscripting
        assert len(d["coefficients"]) == len(d["species"]) >= 2
        assert p["answer"]["value"] == ",".join(str(c) for c in d["coefficients"])
        _assert_choice_menu(p)                                        # coefficient sets → a plausible same-form menu


def test_balancing_coefficients_conserve_every_element_and_charge():
    """The emitted coefficients zero every element row AND the charge row — re-tallied independently here."""
    for p in _bal_gym()["problems"]:
        d = p["derivation"]
        sp, co = d["species"], d["coefficients"]
        keys = list(d["elements"]) + (["charge"] if any(s["charge"] for s in sp) else [])
        for key in keys:
            assert _side_total(sp, co, key, "reactant") == _side_total(sp, co, key, "product"), (p["id"], key)
        assert all(isinstance(c, int) and c >= 1 for c in co)         # positive integers …
        assert reduce(gcd, co) == 1                                   # … in smallest whole-number form


def test_balancing_species_counts_match_parser():
    """Every emitted per-species count + charge equals a fresh parse of that formula (no emission drift)."""
    for p in _bal_gym()["problems"]:
        for s in p["derivation"]["species"]:
            f = parse_formula(s["formula"])
            assert dict(f.counts) == s["counts"] and f.charge == s["charge"], s["formula"]


def test_balancing_includes_subscript_mutation_trap():
    """Both trapped reactions are guaranteed present, each offering the subscript-mutation distractor."""
    traps = [c for p in _bal_gym()["problems"] for c in p["choices"]
             if c["misconception"] and "different substance" in c["misconception"]]
    assert len(traps) >= 2


def test_balancing_deterministic():
    assert _bal_gym() == _bal_gym()                                   # byte-identical for a seed (ADR-0008)
    assert _bal_gym(seed=7)["problems"] != _bal_gym()["problems"]     # a different seed differs


# ------------------------------ stoichiometry families (item 4, ADR-0029) ------------------------------

def _gym_from(spec_path, seed=None):
    spec = dict(tomllib.loads(spec_path.read_text(encoding="utf-8")))
    if seed is not None:
        spec["seed"] = seed
    return generate_gym(spec, ChemData.load(ROOT), spec["id"])


def _rederive_theoretical(d):
    """Independent mass-stoichiometry: given mass ÷ M × (target/given coeff ratio) × target M — exact."""
    g, t = d["given"], d["target"]
    moles_given = Fraction(Decimal(g["mass_g"])) / Fraction(Decimal(g["molar_mass_g_per_mol"]))
    return moles_given * Fraction(t["coeff"], g["coeff"]) * Fraction(Decimal(t["molar_mass_g_per_mol"]))


def test_mass_stoichiometry_shape_and_rederive():
    g = _gym_from(SPEC_MASS_STOICH)
    assert g["family"] == "mass_stoichiometry_v1" and len(g["problems"]) == 10
    data = ChemData.load(ROOT)
    for p in g["problems"]:
        d = p["derivation"]
        assert p["kind"] == "mass_stoichiometry" and p["target_unit"] == "g" and p["answer"]["unit"] == "g"
        assert d["given"]["index"] != d["target"]["index"]
        assert d["species"][d["given"]["index"]]["role"] == "reactant"          # given is always a reactant
        # emitted molar masses come from data/ (no hand-typed constants)
        assert Decimal(d["given"]["molar_mass_g_per_mol"]) == data.molar_mass(d["given"]["formula"])
        assert Decimal(d["target"]["molar_mass_g_per_mol"]) == data.molar_mass(d["target"]["formula"])
        # the answer re-derives exactly, and the chain ends at it
        assert Fraction(Decimal(p["answer"]["value"])) == _rederive_theoretical(d)
        assert Fraction(Decimal(p["chain"][-1]["value"])) == _rederive_theoretical(d)
        _assert_numeric_response(p)


def test_percent_yield_shape_and_rederive():
    g = _gym_from(SPEC_PERCENT_YIELD)
    assert g["family"] == "percent_yield_v1" and len(g["problems"]) == 10
    for p in g["problems"]:
        d = p["derivation"]
        assert p["kind"] == "percent_yield" and p["target_unit"] == "%" and p["answer"]["unit"] == "%"
        assert d["species"][d["given"]["index"]]["role"] == "reactant"
        assert d["species"][d["target"]["index"]]["role"] == "product"           # yield is of a product
        theoretical = _rederive_theoretical(d)
        assert Fraction(Decimal(d["theoretical_mass_g"])) == theoretical
        percent = Fraction(Decimal(d["actual_mass_g"])) / theoretical * 100
        assert Fraction(Decimal(p["answer"]["value"])) == percent
        assert 0 < percent <= 100                                                 # a physical yield
        _assert_numeric_response(p)


def test_limiting_mass_shape_and_rederive():
    g = _gym_from(SPEC_LIMITING_MASS)
    assert g["family"] == "limiting_mass_v1" and len(g["problems"]) == 10
    for p in g["problems"]:
        d = p["derivation"]
        assert p["kind"] == "limiting_mass" and p["target_unit"] == "g"
        assert len(d["reactants"]) == 2
        # each reactant's reaction extent = moles ÷ coefficient; the smaller one limits (re-derived here)
        extents = {}
        for r in d["reactants"]:
            assert d["species"][r["index"]]["role"] == "reactant"
            extents[r["index"]] = (Fraction(Decimal(r["mass_g"])) / Fraction(Decimal(r["molar_mass_g_per_mol"]))) / r["coeff"]
        lim = min(extents, key=extents.get)
        assert lim == d["limiting_index"]
        assert len(set(extents.values())) == 2                       # an unambiguous limiting reagent
        t = d["target"]
        theoretical = extents[lim] * t["coeff"] * Fraction(Decimal(t["molar_mass_g_per_mol"]))
        assert Fraction(Decimal(p["answer"]["value"])) == theoretical
        assert Fraction(Decimal(p["chain"][-1]["value"])) == theoretical
        _assert_numeric_response(p)


@pytest.mark.parametrize("spec", [SPEC_MASS_STOICH, SPEC_PERCENT_YIELD, SPEC_LIMITING_MASS])
def test_stoichiometry_equations_balance_and_terminate(spec):
    for p in _gym_from(spec)["problems"]:
        d = p["derivation"]
        for el in {e for s in d["species"] for e in s["counts"]}:                 # the emitted equation balances
            assert _side_total(d["species"], d["coefficients"], el, "reactant") == \
                   _side_total(d["species"], d["coefficients"], el, "product"), (p["id"], el)
        s = p["answer"]["value"]
        assert "/" not in s and "e" not in s.lower()                             # exact terminating decimal


@pytest.mark.parametrize("spec", [SPEC_MASS_STOICH, SPEC_PERCENT_YIELD, SPEC_LIMITING_MASS])
def test_stoichiometry_deterministic(spec):
    assert _gym_from(spec) == _gym_from(spec)
    assert _gym_from(spec, seed=13)["problems"] != _gym_from(spec)["problems"]


# ------------------------------ ADR-0032: practice must not be answerable by recognition ------------------------------

_NUMERIC_SPECS = [SPEC, SPEC_MASS_STOICH, SPEC_PERCENT_YIELD, SPEC_LIMITING_MASS]
_CHOICE_SPECS = [SPEC_NOMENCLATURE, SPEC_BALANCING]


@pytest.mark.parametrize("spec", _NUMERIC_SPECS, ids=lambda p: p.stem)
def test_numeric_gyms_are_free_entry_not_a_menu(spec):
    """No numeric gym offers a multiple-choice menu — a human eliminates 0.55 % or a 1000×-too-large answer on
    sight, so a menu drills nothing. Every problem is free entry with a diagnostics catalogue (ADR-0032)."""
    for p in _gym_from(spec)["problems"]:
        _assert_numeric_response(p)


@pytest.mark.parametrize("spec", _CHOICE_SPECS, ids=lambda p: p.stem)
def test_categorical_gyms_stay_plausible_menus(spec):
    """Names, formulas, and coefficient sets are categorical — a menu is fine because every distractor is a
    plausible, same-form answer a specific misconception produces."""
    for p in _gym_from(spec)["problems"]:
        _assert_choice_menu(p)


def test_percent_yield_diagnostics_replace_the_giveaway_menu():
    """The regression the owner caught: the percent-yield answer sat in a menu beside 0.55 % (forgot ×100) and
    a >100 % value (inverted) — both eliminable on sight, so the two-digit answer was always the pick. Those
    values are now diagnostics that name the mistake only if the learner actually enters one, and none sits
    within the entry tolerance of the answer."""
    for p in _gym_from(SPEC_PERCENT_YIELD)["problems"]:
        assert p["mode"] == "numeric" and "choices" not in p
        assert p["diagnostics"]                                                  # the mistakes are still captured
        ans = float(p["answer"]["value"])
        for dgn in p["diagnostics"]:
            assert abs(float(dgn["value"]) - ans) > 0.03 * max(abs(ans), 1e-9)
