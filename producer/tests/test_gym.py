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
SPEC_TRENDS = ROOT / "gyms" / "periodic-trends" / "periodic-trends.gym.toml"

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
_CHOICE_SPECS = [SPEC_NOMENCLATURE, SPEC_BALANCING, SPEC_TRENDS,
                 ROOT / "gyms" / "reaction-families" / "reaction-families.gym.toml"]


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


# ------------------------------ periodic trends (item 5b, ADR-0034) ------------------------------


def test_trends_shape_and_kind_rotation():
    g = _gym_from(SPEC_TRENDS)
    assert g["family"] == "periodic_trends_v1" and len(g["problems"]) == 10
    assert {p["kind"] for p in g["problems"]} == {"trend_compare", "predict_ion", "order_ionization"}
    # the drilled properties/charges carry their register ids in provenance (ADR-0034)
    src = g["provenance"]["sources"]
    assert src["ionization_energy"] == "nist-ionization-energies"
    assert src["covalent_radius"] == "cordero-2008-covalent-radii"
    assert src["electronegativity"] == "openstax-chemistry-2e" == src["ion_charge"]
    for p in g["problems"]:
        _assert_choice_menu(p)                             # comparisons/ions/orderings are categorical


def test_trend_compare_answers_come_from_the_data():
    data = ChemData.load(ROOT)
    for p in _gym_from(SPEC_TRENDS)["problems"]:
        if p["kind"] != "trend_compare":
            continue
        d = p["derivation"]
        vals = []
        for c in d["candidates"]:
            el = data.elements[c["symbol"]]
            assert c["value"] == str(getattr(el, d["property"]))          # embedded value IS the curated value
            assert el.block in ("s", "p") and c["symbol"] != "H"
            assert (el.period if d["series"]["kind"] == "period" else el.group) == d["series"]["n"]
            vals.append(Decimal(c["value"]))
        extreme = max(vals) if d["direction"] == "max" else min(vals)
        assert p["answer"]["value"] == d["candidates"][vals.index(extreme)]["symbol"]


def test_order_ionization_sorted_from_data_and_exceptions_named():
    data = ChemData.load(ROOT)
    for p in _gym_from(SPEC_TRENDS)["problems"]:
        if p["kind"] != "order_ionization":
            continue
        d = p["derivation"]
        by_value = sorted(d["candidates"], key=lambda c: Decimal(c["value"]))
        assert p["answer"]["value"] == ",".join(c["symbol"] for c in by_value)
        for c in d["candidates"]:
            assert c["value"] == str(data.elements[c["symbol"]].first_ionization_kj_mol)
        # when the data order breaks the left-to-right rule, the naive order must appear as a NAMED trap
        by_group = sorted(d["candidates"], key=lambda c: data.elements[c["symbol"]].group)
        if by_group != by_value:
            naive_disp = " < ".join(c["symbol"] for c in by_group)
            trap = next(c for c in p["choices"] if c["display"] == naive_disp)
            assert not trap["correct"] and "dip" in trap["misconception"]


def test_predict_ion_matches_the_valence_table_pick():
    from chemkernel.reference import common_monatomic_ions
    data = ChemData.load(ROOT)
    common = common_monatomic_ions(data)
    for p in _gym_from(SPEC_TRENDS)["problems"]:
        if p["kind"] != "predict_ion":
            continue
        d = p["derivation"]
        el = data.elements[d["element"]]
        assert el.block in ("s", "p") and d["element"] != "H"            # d-block + H are excluded
        ion = common[d["element"]]
        assert d["ion"]["id"] == ion.id == p["answer"]["value"]
        assert d["ion"]["charge"] == ion.charge
        # only fixed-charge elements are drilled — "the" common ion must be unambiguous
        assert sum(1 for i in data.ions.values()
                   if i.element == d["element"] and i.kind == "monatomic") == 1
        assert d["ion"]["id"] in p["subscript_tokens"]                   # the view subscripts the ion ids


def test_trends_deterministic():
    assert _gym_from(SPEC_TRENDS) == _gym_from(SPEC_TRENDS)
    assert _gym_from(SPEC_TRENDS, seed=99)["problems"] != _gym_from(SPEC_TRENDS)["problems"]


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


# ------------------------------ reaction families (item 6, ADR-0035/0036) ------------------------------

SPEC_FAMILIES = ROOT / "gyms" / "reaction-families" / "reaction-families.gym.toml"


def test_reaction_families_shape_and_kinds():
    g = _gym_from(SPEC_FAMILIES)
    assert g["family"] == "reaction_families_v1" and len(g["problems"]) == 10
    assert {p["kind"] for p in g["problems"]} == {"classify_family", "name_spectators"}
    assert g["provenance"]["sources"]["reaction_classes"] == "openstax-chemistry-2e"
    for p in g["problems"]:
        _assert_choice_menu(p)                                # classifying / naming spectators are categorical


def test_reaction_families_classify_answers_are_engine_classified():
    """Every classify_family answer is the family the classifier assigns to the emitted (balanced) equation."""
    from chemkernel.reaction import classify_reaction
    from chemkernel.reactivity import AcidBase, Decomposition
    from chemkernel.solubility import Solubility
    d = ChemData.load(ROOT)
    solub = Solubility.load(ROOT)
    ab = AcidBase.load(ROOT); ab.validate(d)
    dec = Decomposition.load(ROOT); dec.validate(d)
    seen_families = set()
    for p in _gym_from(SPEC_FAMILIES)["problems"]:
        if p["kind"] != "classify_family":
            continue
        sp = p["derivation"]["species"]
        r = [parse_formula(s["formula"]) for s in sp if s["role"] == "reactant"]
        pr = [parse_formula(s["formula"]) for s in sp if s["role"] == "product"]
        cls = classify_reaction(r, pr, d, solubility=solub, acidbase=ab, decomposition=dec)
        assert cls["family"] == p["derivation"]["family"] == p["answer"]["value"]
        seen_families.add(cls["family"])
    assert len(seen_families) >= 3                             # the corpus spans several families


def test_reaction_families_spectators_absent_from_net():
    """A named spectator never appears in the emitted net-ionic equation — it cancels, by definition."""
    problems = [p for p in _gym_from(SPEC_FAMILIES)["problems"] if p["kind"] == "name_spectators"]
    assert problems                                           # the corpus produces spectator drills
    for p in problems:
        d = p["derivation"]
        net_formulas = {s["formula"] for s in d["net_species"]}
        assert d["spectators"], "a spectator problem must name at least one spectator"
        for sp in d["spectators"]:
            assert sp not in net_formulas
        # the over-inclusion and reacting-ion distractors are present and wrong
        assert p["answer"]["value"] == ",".join(d["spectators"])


def test_reaction_families_deterministic():
    assert _gym_from(SPEC_FAMILIES) == _gym_from(SPEC_FAMILIES)
    assert _gym_from(SPEC_FAMILIES, seed=99)["problems"] != _gym_from(SPEC_FAMILIES)["problems"]


# --- gas laws (Phase 2, ADR-0040) ---------------------------------------------------------------------

SPEC_GAS = ROOT / "gyms" / "gas-laws" / "gas-laws.gym.toml"


def _rederive_ideal(gas):
    """Re-derive PV=nRT for the solved variable from the emitted state — the same arithmetic the gate does."""
    R, num, sf = float(gas["R"]), lambda k: float(gas[k]), gas["solve_for"]
    if sf == "P":
        return num("n_mol") * R * num("T_K") / num("V_L")
    if sf == "V":
        return num("n_mol") * R * num("T_K") / num("P_atm")
    if sf == "n":
        return num("P_atm") * num("V_L") / (R * num("T_K"))
    return num("P_atm") * num("V_L") / (num("n_mol") * R)          # T


def _rederive_combined(gas):
    num, sf = lambda k: float(gas[k]), gas["solve_for"]
    K = num("P1_atm") * num("V1_L") / num("T1_K")
    if sf == "P2":
        return K * num("T2_K") / num("V2_L")
    if sf == "V2":
        return K * num("T2_K") / num("P2_atm")
    return num("P2_atm") * num("V2_L") / K                         # T2


def test_gas_laws_shape_kinds_and_model_badge():
    gym = _gym_from(SPEC_GAS)
    kinds = {p["kind"] for p in gym["problems"]}
    assert kinds == {"gas_ideal", "gas_combined"}                 # both drills present
    # the gym is REGIME-2: it discloses the ideal-gas model assumption (the model-assumed badge, ADR-0040)
    assert gym["assumptions"] and gym["assumptions"][0]["kind"] == "model"
    assert "ideally" in gym["assumptions"][0]["claim"]
    assert gym["provenance"]["sources"]["constants"]              # R is a sourced datum
    for p in gym["problems"]:
        _assert_numeric_response(p)                               # free entry, never a gameable menu


def test_gas_laws_answers_reproduce_the_law():
    """Every committed answer re-derives from PV=nRT (or the combined law) within the rounding tolerance —
    the machine-checked part of a model-exact claim."""
    for p in _gym_from(SPEC_GAS)["problems"]:
        gas = p["derivation"]["gas"]
        got = _rederive_ideal(gas) if p["kind"] == "gas_ideal" else _rederive_combined(gas)
        want = float(p["answer"]["value"])
        assert abs(got - want) <= 0.005 * abs(want) + 1e-9, (p["kind"], gas, got, want)


def test_gas_laws_answers_are_physical():
    """The generator builds a CONSISTENT state, so no absurd temperatures/volumes ship."""
    for p in _gym_from(SPEC_GAS)["problems"]:
        v = float(p["answer"]["value"])
        assert 0.05 <= v <= 2000                                  # a sane, learnable magnitude


def test_gas_laws_celsius_conversion_is_a_diagnostic():
    """A problem that states its temperature in °C carries the 'forgot to convert to kelvin' diagnostic —
    the canonical gas-law mistake."""
    problems = [p for p in _gym_from(SPEC_GAS)["problems"]
                if p["kind"] == "gas_ideal" and "°C" in p["prompt"]]
    assert problems, "the seeded gym should include at least one Celsius-stated problem"
    for p in problems:
        assert any("kelvin" in d["misconception"].lower() for d in p["diagnostics"])


def test_gas_laws_deterministic():
    assert _gym_from(SPEC_GAS) == _gym_from(SPEC_GAS)
    assert _gym_from(SPEC_GAS, seed=7)["problems"] != _gym_from(SPEC_GAS)["problems"]


# --- calorimetry gym (ADR-0042) --------------------------------------------------------------------------
SPEC_CALOR = ROOT / "gyms" / "calorimetry" / "calorimetry.gym.toml"


def test_calorimetry_shape_kinds_and_both_badges():
    gym = _gym_from(SPEC_CALOR)
    assert {p["kind"] for p in gym["problems"]} == {"calorimetry"}
    # every one of the four solve targets appears across the seeded set
    assert {p["derivation"]["calorimetry"]["solve_for"] for p in gym["problems"]} == {"q", "m", "c", "dT"}
    # REGIME-2 + REGIME-3: it discloses the calorimetry model (model badge) AND cites the specific heats (sourced)
    assert gym["assumptions"] and all(a["kind"] == "model" for a in gym["assumptions"])
    assert gym["provenance"]["sources"]["specific_heats"]          # c is a sourced datum
    for p in gym["problems"]:
        _assert_numeric_response(p)                                # free entry, never a gameable menu


def test_calorimetry_answers_reproduce_q_equals_mcdt():
    """Every committed answer re-derives from q = m·c·ΔT within the rounding tolerance."""
    for p in _gym_from(SPEC_CALOR)["problems"]:
        d = p["derivation"]["calorimetry"]
        sf = d["solve_for"]
        if sf == "q":
            got = float(d["m"]) * float(d["c"]) * float(d["dT"])
        elif sf == "m":
            got = float(d["q"]) / (float(d["c"]) * float(d["dT"]))
        elif sf == "dT":
            got = float(d["q"]) / (float(d["m"]) * float(d["c"]))
        else:  # c
            got = float(d["q"]) / (float(d["m"]) * float(d["dT"]))
        want = float(p["answer"]["value"])
        assert abs(got - want) <= 0.005 * abs(want) + 1e-9, (sf, d, got, want)


def test_calorimetry_specific_heat_is_the_sourced_value():
    """A 'solve for c' problem's answer is the substance's sourced specific heat — identify-the-metal, from data."""
    data = ChemData.load(ROOT)
    for p in _gym_from(SPEC_CALOR)["problems"]:
        d = p["derivation"]["calorimetry"]
        if d["solve_for"] != "c":
            continue
        sourced = next(v["specific_heat"] for v in data.specific_heats.values() if v["name"] == d["substance"])
        assert abs(float(p["answer"]["value"]) - float(sourced)) <= 0.005 * float(sourced)


def test_calorimetry_wrong_substance_c_is_a_diagnostic():
    """A q/m/ΔT problem carries the 'used another substance's specific heat' diagnostic — the canonical error."""
    problems = [p for p in _gym_from(SPEC_CALOR)["problems"]
                if p["derivation"]["calorimetry"]["solve_for"] in ("q", "m", "dT")]
    assert any(any("specific heat of another" in dg["misconception"] for dg in p["diagnostics"])
               for p in problems)


def test_calorimetry_deterministic():
    assert _gym_from(SPEC_CALOR) == _gym_from(SPEC_CALOR)
    assert _gym_from(SPEC_CALOR, seed=7)["problems"] != _gym_from(SPEC_CALOR)["problems"]


# ------------------------------ Lewis structures (Phase 2 bonding, ADR-0044) ------------------------------

SPEC_LEWIS = ROOT / "gyms" / "lewis-structures" / "lewis-structures.gym.toml"


def test_lewis_shape_kinds_and_sources():
    g = _gym_from(SPEC_LEWIS)
    assert g["family"] == "lewis_structures_v1" and len(g["problems"]) == 10
    assert {p["kind"] for p in g["problems"]} == {"lewis_valence", "lewis_domains", "lewis_geometry"}
    # valence electrons trace to the IUPAC group positions; the geometry names to the VSEPR table (ADR-0044)
    assert g["provenance"]["sources"]["position"] == "iupac-periodic-table"
    assert g["provenance"]["sources"]["vsepr"] == "openstax-chemistry-2e"
    for p in g["problems"]:
        if p["kind"] == "lewis_geometry":
            _assert_choice_menu(p)                             # a shape name is a categorical same-form menu
        else:
            _assert_numeric_response(p)                        # counts are free-entry, never a gameable menu


def test_lewis_valence_and_domains_reproduce_from_the_structure():
    """Every counting answer re-derives independently from the emitted structure — valence = Σ group electrons −
    charge; electron domains = the central atom's bonded neighbours + lone pairs."""
    from chemkernel.reference import valence_electrons
    data = ChemData.load(ROOT)
    for p in _gym_from(SPEC_LEWIS)["problems"]:
        d = p["derivation"]["lewis"]
        if p["kind"] == "lewis_valence":
            valence = sum(valence_electrons(data.elements[a["element"]]) for a in d["atoms"]) - d["charge"]
            assert int(p["answer"]["value"]) == valence
        elif p["kind"] == "lewis_domains":
            lp = next(a["lone_pairs"] for a in d["atoms"] if a["id"] == d["central"])
            neighbours = sum(1 for b in d["bonds"] if d["central"] in (b["a"], b["b"]))
            assert int(p["answer"]["value"]) == neighbours + lp
        else:  # lewis_geometry — the domain count keys the sourced shape, and the correct choice is that shape
            lp = next(a["lone_pairs"] for a in d["atoms"] if a["id"] == d["central"])
            neighbours = sum(1 for b in d["bonds"] if d["central"] in (b["a"], b["b"]))
            assert d["domains"] == neighbours + lp and d["lone_pairs"] == lp
            assert p["answer"]["display"] == d["molecular_shape"]


def test_lewis_geometry_offers_the_electron_domain_geometry_distractor():
    """A lone-pair shape (bent / trigonal pyramidal) offers its electron-domain geometry as the star distractor —
    the 'lone pairs are invisible in the shape' misconception."""
    problems = [p for p in _gym_from(SPEC_LEWIS)["problems"]
                if p["kind"] == "lewis_geometry" and p["derivation"]["lewis"]["lone_pairs"] > 0]
    assert problems, "the seeded set should contain a lone-pair geometry question"
    assert any(any("electron-domain geometry" in c["misconception"] for c in p["choices"] if not c["correct"])
               for p in problems)


def test_lewis_all_electrons_diagnostic_present():
    """A valence-total drill names the 'counted every electron, not just valence' mistake."""
    problems = [p for p in _gym_from(SPEC_LEWIS)["problems"] if p["kind"] == "lewis_valence"]
    assert any(any("valence electrons" in dg["misconception"] for dg in p["diagnostics"]) for p in problems)


def test_lewis_deterministic():
    assert _gym_from(SPEC_LEWIS) == _gym_from(SPEC_LEWIS)
    assert _gym_from(SPEC_LEWIS, seed=42)["problems"] != _gym_from(SPEC_LEWIS)["problems"]


# --- weak-acid pH gym (ADR-0048) -------------------------------------------------------------------------
SPEC_WEAK_ACID = ROOT / "gyms" / "equilibrium" / "weak-acid-ph.gym.toml"

import math


def _rederive_weak_acid_ph(eq):
    """Independent weak-acid pH: solve Kₐ = x²/(c0 − x) for x = [H⁺] (the quadratic root), then −log₁₀."""
    ka, c0 = float(eq["ka"]), float(eq["c0"])
    x = (-ka + math.sqrt(ka * ka + 4 * ka * c0)) / 2      # positive root of x² + Kₐx − Kₐc0 = 0
    return -math.log10(x)


def test_weak_acid_ph_shape_kinds_and_both_badges():
    gym = _gym_from(SPEC_WEAK_ACID)
    assert {p["kind"] for p in gym["problems"]} == {"weak_acid_ph"}
    # REGIME-2 (model-assumed: the equilibrium/ideal-dilute model) AND data-sourced (Kₐ), like calorimetry
    assert gym["assumptions"] and all(a["kind"] == "model" for a in gym["assumptions"])
    assert gym["provenance"]["sources"]["ionization_constants"]
    for p in gym["problems"]:
        _assert_numeric_response(p)                       # free entry, never a gameable menu
        assert p["answer"]["unit"] == "" and "choices" not in p
        assert p["subscript_tokens"]                      # the acid formula, for prettyText subscripting


def test_weak_acid_ph_answers_reproduce_the_root():
    """Every committed pH re-derives from the mass-action root (the quadratic here matches the bisection)."""
    for p in _gym_from(SPEC_WEAK_ACID)["problems"]:
        got = _rederive_weak_acid_ph(p["derivation"]["equilibrium"])
        want = float(p["answer"]["value"])
        assert abs(got - want) <= 0.01 * abs(want) + 1e-3, (p["derivation"]["equilibrium"], got, want)


def test_weak_acid_ph_ka_round_trips():
    """The emitted Kₐ is fixed-notation and round-trips through float() (the scientific-string trim bug guard)."""
    for p in _gym_from(SPEC_WEAK_ACID)["problems"]:
        ka = float(p["derivation"]["equilibrium"]["ka"])
        assert 1e-11 < ka < 1e-3                          # the curated weak-acid Kₐ range (not mangled to ~0.5)


def test_weak_acid_ph_strong_acid_is_a_diagnostic():
    """Every problem carries the canonical 'treated the weak acid as strong' mistake as a diagnostic."""
    for p in _gym_from(SPEC_WEAK_ACID)["problems"]:
        assert any("strong" in d["misconception"].lower() for d in p["diagnostics"])


def test_weak_acid_ph_answers_are_learnable():
    for p in _gym_from(SPEC_WEAK_ACID)["problems"]:
        assert 0.5 <= float(p["answer"]["value"]) <= 11


def test_weak_acid_ph_deterministic():
    assert _gym_from(SPEC_WEAK_ACID) == _gym_from(SPEC_WEAK_ACID)
    assert _gym_from(SPEC_WEAK_ACID, seed=55)["problems"] != _gym_from(SPEC_WEAK_ACID)["problems"]
