"""The reversible-extent solver + weak-acid equilibrium lesson (ADR-0048).

The ICE table is the species ledger with the extent solved from mass action (Q = K), not driven to a limiting
reagent. These tests pin the solver's numerics (the root satisfies Q = K to a tiny residual), the ICE identity,
the pH, and the producer's refusals — the honesty guards that make it safe to emit.
"""

from decimal import Decimal
from pathlib import Path

import pytest

from chemkernel import BuildError
from chemkernel.build import build_equilibrium
from chemkernel.data import ChemData
from chemkernel.equilibrium import (build_buffer_lesson, build_equilibrium_lesson, build_polyprotic_lesson,
                                    build_prediction_lesson, build_solubility_lesson, build_titration_lesson,
                                    build_weak_base_lesson, solve_equilibrium, _quotient)
from chemkernel.build import build_prediction
from chemkernel.reactivity import AcidBase

ROOT = Path(__file__).resolve().parents[2]
SPEC = ROOT / "problems" / "equilibrium" / "acetic-acid-ph.equilibrium.toml"
SPEC_KSP = ROOT / "problems" / "equilibrium" / "calcium-fluoride-solubility.equilibrium.toml"
SPEC_KSP_COMMON = ROOT / "problems" / "equilibrium" / "calcium-fluoride-common-ion.equilibrium.toml"
SPEC_POLY = ROOT / "problems" / "equilibrium" / "phosphoric-acid-ph.equilibrium.toml"
SPEC_TITRATION = ROOT / "problems" / "equilibrium" / "acetic-acid-titration.equilibrium.toml"
SPEC_BASE = ROOT / "problems" / "equilibrium" / "ammonia-ph.equilibrium.toml"
SPEC_BUFFER = ROOT / "problems" / "equilibrium" / "acetate-buffer.equilibrium.toml"
SPEC_PREDICTION = ROOT / "problems" / "equilibrium" / "calcium-fluoride-precipitation.prediction.toml"
SPEC_PREDICTION_NO = ROOT / "problems" / "equilibrium" / "magnesium-hydroxide-no-precipitate.prediction.toml"


def _acid_system(c0, hplus=Decimal(0)):
    return [
        {"id": "HA", "nu": -1, "initial_M": Decimal(c0)},
        {"id": "H^+", "nu": 1, "initial_M": hplus},
        {"id": "A^-", "nu": 1, "initial_M": Decimal(0)},
    ]


# ── the solver ──

def test_weak_acid_quadratic_root():
    """Acetic acid, 0.100 M, Ka = 1.8e-5 — the canonical quadratic. x = [H+] ≈ 1.333e-3; the residual is tiny."""
    r = solve_equilibrium(_acid_system("0.100"), Decimal("1.8e-5"), "acetic")
    assert abs(r["extent"] - Decimal("0.00133267")) < Decimal("1e-7")
    # the machine-check: Q at the root reproduces K essentially exactly
    assert r["residual"] < Decimal("1e-40")
    assert float(r["quotient"]) == pytest.approx(1.8e-5, rel=1e-9)


def test_root_satisfies_mass_action_generally():
    """A much stronger weak acid (Ka = 0.10, C0 = 0.10) where the small-x approximation would fail badly: the
    solver still lands the root (≈61.8% ionized), Q = K. Bisection, not the quadratic formula — the instrument."""
    r = solve_equilibrium(_acid_system("0.10"), Decimal("0.10"), "strong-weak")
    assert Decimal("0.06") < r["extent"] < Decimal("0.064")
    assert r["residual"] < Decimal("1e-40")
    # the naive √(Ka·C0) would give 0.10 (100% ionized) — the honest root is far from it
    assert r["extent"] < Decimal("0.07")


def test_root_is_bracketed_between_zero_and_reactant():
    r = solve_equilibrium(_acid_system("0.250"), Decimal("4.9e-10"), "very-weak")
    assert 0 < r["extent"] < Decimal("0.250")
    assert r["fwd_limit"] == Decimal("0.250")


def test_quotient_products_over_reactants():
    q = _quotient([Decimal("0.0987"), Decimal("0.00133"), Decimal("0.00133")], [-1, 1, 1])
    assert float(q) == pytest.approx(0.00133 * 0.00133 / 0.0987, rel=1e-9)


def test_solver_refuses_nonpositive_K():
    with pytest.raises(BuildError, match="must be positive"):
        solve_equilibrium(_acid_system("0.1"), Decimal(0), "bad")


def test_solver_refuses_negative_initial():
    with pytest.raises(BuildError, match="negative initial"):
        solve_equilibrium(_acid_system("-0.1"), Decimal("1e-5"), "bad")


def test_solver_refuses_missing_side():
    only_reactants = [{"id": "A", "nu": -1, "initial_M": Decimal("0.1")}]
    with pytest.raises(BuildError, match="at least one product"):
        solve_equilibrium(only_reactants, Decimal("1e-5"), "bad")


# ── the lesson builder ──

def _data_ab():
    data = ChemData.load(ROOT)
    ab = AcidBase.load(ROOT)
    ab.validate(data)
    return data, ab


def _spec(**over):
    base = {"id": "t", "title": "t", "slug": "t", "topic": "equilibrium", "scenario": "s",
            "acid": "HC2H3O2", "initial_molarity_M": "0.100",
            "misconception": {"claim": "c", "refuted_by": "weak_acid_partial_ionization"}}
    base.update(over)
    return base


def test_builds_acetic_acid_lesson():
    data, ab = _data_ab()
    L = build_equilibrium_lesson(_spec(), data, ab, "t")
    assert L["kind"] == "equilibrium"
    # the reaction is DRY-sourced from acids-bases.toml (proton count + conjugate base)
    assert L["reaction"]["text"] == "HC2H3O2 <=> H^+ + C2H3O2^-"
    assert L["reaction"]["conjugate_base"] == "C2H3O2^-"
    # Ka from the sourced dataset
    assert L["equilibrium_constant"]["value"] == "0.000018"
    assert L["equilibrium_constant"]["source"] == "openstax-chemistry-2e"
    # the solved position
    assert L["ice"]["extent_M_display"] == "0.00133"
    assert L["result"]["pH_display"] == "2.88"
    assert L["result"]["percent_ionization_display"] == "1.33"
    # all machine-checked facts true
    assert all(L["checks"].values())


def test_ice_identity_holds():
    """Every equilibrium concentration = initial + ν·x (the ledger identity, exact in what ships)."""
    data, ab = _data_ab()
    L = build_equilibrium_lesson(_spec(), data, ab, "t")
    x = Decimal(L["ice"]["extent_M"])
    for row in L["ice"]["species"]:
        expected = Decimal(row["initial_M"]) + row["nu"] * x
        assert abs(Decimal(row["equilibrium_M"]) - expected) < Decimal("1e-10")


def test_mass_action_residual_tiny():
    """Q at the committed equilibrium concentrations reproduces Ka — the machine-check."""
    data, ab = _data_ab()
    L = build_equilibrium_lesson(_spec(), data, ab, "t")
    concs = [Decimal(r["equilibrium_M"]) for r in L["ice"]["species"]]
    nus = [r["nu"] for r in L["ice"]["species"]]
    Q = _quotient(concs, nus)
    ka = Decimal(L["equilibrium_constant"]["value"])
    assert abs(Q - ka) / ka < Decimal("1e-6")


def test_regimes_layered():
    data, ab = _data_ab()
    L = build_equilibrium_lesson(_spec(), data, ab, "t")
    regimes = {r["regime"] for r in L["regimes"]}
    assert {"ledger-exact", "rule-sourced", "model-exact"} <= regimes


def test_refuses_strong_acid():
    data, ab = _data_ab()
    with pytest.raises(BuildError, match="not weak"):
        build_equilibrium_lesson(_spec(acid="HCl"), data, ab, "t")


def test_refuses_polyprotic_acid():
    data, ab = _data_ab()
    with pytest.raises(BuildError, match="polyprotic"):
        build_equilibrium_lesson(_spec(acid="H3PO4"), data, ab, "t")


def test_refuses_unknown_acid():
    data, ab = _data_ab()
    with pytest.raises(BuildError, match="not in data/acids-bases"):
        build_equilibrium_lesson(_spec(acid="HBr"), data, ab, "t")


def test_refuses_nonpositive_concentration():
    data, ab = _data_ab()
    with pytest.raises(BuildError, match="molarity must be positive"):
        build_equilibrium_lesson(_spec(initial_molarity_M="0"), data, ab, "t")


# ── the data layer ──

def test_ionization_constants_loaded():
    data = ChemData.load(ROOT)
    assert data.ionization_constant("HC2H3O2")["ka"] == Decimal("1.8e-5")
    assert data.sources["ionization_constants"] == "openstax-chemistry-2e"


def test_missing_ka_refused():
    data = ChemData.load(ROOT)
    with pytest.raises(BuildError, match="no ionization constant"):
        data.ionization_constant("HNO3")   # a strong acid — no Ka curated


# ── the build round-trip ──

def test_build_equilibrium_round_trip():
    lesson, out_rel = build_equilibrium(SPEC, ROOT)
    assert out_rel == "equilibrium/acetic-acid-ph.equilibrium.json"
    assert lesson["id"] == "acetic-acid-ph"
    assert lesson["kind"] == "equilibrium"
    assert lesson["subtype"] == "weak-acid"


# ── Ksp / solubility (the 2nd increment — the cubic, the pure solid excluded from Q) ──

def _ksp_system(ksp):
    # CaF2(s) <=> Ca2+ + 2 F- ; the solid excluded from Q -> Q = [Ca][F]^2 = 4s^3 (a CUBIC)
    return [
        {"id": "CaF2", "nu": -1, "initial_M": Decimal(0), "in_quotient": False},
        {"id": "Ca^2+", "nu": 1, "initial_M": Decimal(0)},
        {"id": "F^-", "nu": 2, "initial_M": Decimal(0)},
    ]


def test_ksp_cubic_root():
    """The 1:2 salt gives a CUBIC (4s³ = Ksp) — the reason the solver is bisection, not the quadratic formula."""
    r = solve_equilibrium(_ksp_system(Decimal("3.45e-11")), Decimal("3.45e-11"), "CaF2")
    expected = (Decimal("3.45e-11") / 4) ** (Decimal(1) / 3)
    assert abs(r["extent"] - expected) < Decimal("1e-10")
    assert r["residual"] < Decimal("1e-40")


def test_pure_solid_excluded_from_quotient():
    """Q is over the ions only — the pure solid (in_quotient False) never enters, whatever its 'concentration'."""
    q_ions = _quotient([Decimal("0.0002"), Decimal("0.0004")], [1, 2])
    q_all = _quotient([Decimal("99"), Decimal("0.0002"), Decimal("0.0004")], [-1, 1, 2],
                      in_q=[False, True, True])
    assert q_all == q_ions          # the solid's value is irrelevant


def test_builds_calcium_fluoride_lesson():
    data = ChemData.load(ROOT)
    L = build_solubility_lesson({"id": "t", "title": "t", "slug": "t", "topic": "equilibrium", "scenario": "s",
                                 "salt": "CaF2",
                                 "misconception": {"claim": "c", "refuted_by": "stoichiometry_in_ksp"}}, data, "t")
    assert L["subtype"] == "solubility"
    assert L["equilibrium_constant"]["symbol"] == "K_sp"
    assert L["equilibrium_constant"]["value"] == "0.000000000040"
    assert L["reaction"]["text"] == "CaF2(s) <=> Ca^2+(aq) + 2 F^-(aq)"
    # the solid row is present, excluded from Q, and carries no concentration
    solid = L["ice"]["species"][0]
    assert solid["id"] == "CaF2" and solid["in_quotient"] is False and "equilibrium_M" not in solid
    # the molar solubility ≈ 2.15e-4, solubility ≈ 0.0168 g/L (OpenStax App-J Ksp 4.0e-11, QC 2026-07-09)
    assert L["result"]["molar_solubility_M_display"] == "0.000215"
    assert L["result"]["solubility_g_per_L_display"] == "0.0168"
    assert all(L["checks"].values())


def test_ksp_mass_action_residual_tiny():
    data = ChemData.load(ROOT)
    L = build_solubility_lesson({"id": "t", "title": "t", "slug": "t", "topic": "equilibrium", "scenario": "s",
                                 "salt": "CaF2",
                                 "misconception": {"claim": "c", "refuted_by": "stoichiometry_in_ksp"}}, data, "t")
    ions = [r for r in L["ice"]["species"] if r.get("in_quotient") is not False]
    Q = _quotient([Decimal(r["equilibrium_M"]) for r in ions], [r["nu"] for r in ions])
    ksp = Decimal(L["equilibrium_constant"]["value"])
    assert abs(Q - ksp) / ksp < Decimal("1e-6")


def test_refuses_unknown_salt():
    data = ChemData.load(ROOT)
    with pytest.raises(BuildError, match="no solubility product"):
        build_solubility_lesson({"id": "t", "title": "t", "slug": "t", "topic": "equilibrium", "scenario": "s",
                                 "salt": "NaCl", "misconception": {"claim": "c", "refuted_by": "x"}}, data, "t")


def test_solubility_products_loaded():
    data = ChemData.load(ROOT)
    rec = data.solubility_product("CaF2")
    assert rec["ksp"] == Decimal("4.0e-11")
    assert rec["n_cation"] == 1 and rec["n_anion"] == 2       # crossover derived + composition machine-checked
    assert data.sources["solubility_products"] == "openstax-chemistry-2e"


def test_build_solubility_round_trip():
    lesson, out_rel = build_equilibrium(SPEC_KSP, ROOT)
    assert out_rel == "equilibrium/calcium-fluoride-solubility.equilibrium.json"
    assert lesson["subtype"] == "solubility"


def test_plain_solubility_carries_no_common_ion_fields():
    """The common-ion machinery is OPTIONAL — a plain Ksp lesson emits neither the reaction nor the result additions."""
    data = ChemData.load(ROOT)
    L = build_solubility_lesson({"id": "t", "title": "t", "slug": "t", "topic": "equilibrium", "scenario": "s",
                                 "salt": "CaF2",
                                 "misconception": {"claim": "c", "refuted_by": "stoichiometry_in_ksp"}}, data, "t")
    assert "common_ion" not in L["reaction"]
    assert "molar_solubility_pure_water_M" not in L["result"]
    # both ions still start at zero in pure water
    assert all(r["initial_M"] == "0" for r in L["ice"]["species"] if r.get("in_quotient") is not False)


# ── the common-ion effect (the 6th increment — a shared ion pre-loaded suppresses solubility, on the CUBIC) ──

def test_common_ion_solver_nonzero_initial_product():
    """CaF2 into 0.10 M F⁻: the solver's nonzero-initial-product case (the buffer's move) on the Ksp cubic. Q=Ksp
    is met at a far smaller extent — s drops roughly Ksp/[F⁻]² ≈ 3.45e-9, not 2.05e-4."""
    sys = [
        {"id": "CaF2", "nu": -1, "initial_M": Decimal(0), "in_quotient": False},
        {"id": "Ca^2+", "nu": 1, "initial_M": Decimal(0)},
        {"id": "F^-", "nu": 2, "initial_M": Decimal("0.10")},
    ]
    r = solve_equilibrium(sys, Decimal("3.45e-11"), "CaF2/F-")
    assert Decimal("3e-9") < r["extent"] < Decimal("4e-9")     # ~Ksp / 0.10² = 3.45e-9
    assert r["residual"] < Decimal("1e-30")


def _common_spec(common_ion="F^-", molarity="0.10"):
    return {"id": "t", "title": "t", "slug": "t", "topic": "equilibrium", "scenario": "s", "salt": "CaF2",
            "common_ion": common_ion, "common_ion_molarity_M": molarity,
            "misconception": {"claim": "c", "refuted_by": "common_ion_suppresses_solubility"}}


def test_common_ion_suppresses_solubility():
    data = ChemData.load(ROOT)
    L = build_solubility_lesson(_common_spec(), data, "t")
    assert L["subtype"] == "solubility"                         # same subtype — a variant, not a new shape
    assert L["reaction"]["common_ion"] == "F^-"
    assert L["reaction"]["common_ion_molarity_M"] == "0.10"
    # the fluoride row starts at 0.10, not 0; the calcium row at 0
    fluoride = next(r for r in L["ice"]["species"] if r["id"] == "F^-")
    calcium = next(r for r in L["ice"]["species"] if r["id"] == "Ca^2+")
    assert fluoride["initial_M"] == "0.10" and calcium["initial_M"] == "0"
    # solubility is far below the pure-water value, and the contrast is emitted
    assert Decimal(L["result"]["molar_solubility_M"]) < Decimal(L["result"]["molar_solubility_pure_water_M"])
    assert L["result"]["molar_solubility_M_display"] == "0.000000004"
    assert L["result"]["molar_solubility_pure_water_M_display"] == "0.000215"
    # suppression = s(pure) / s(common ion), ~5.4e4-fold
    supp = Decimal(L["result"]["molar_solubility_pure_water_M"]) / Decimal(L["result"]["molar_solubility_M"])
    assert Decimal("5e4") < supp < Decimal("7e4")
    assert all(L["checks"].values())


def test_common_ion_mass_action_still_reproduces_ksp():
    """The pre-loaded fluoride is in the quotient: Q = [Ca²⁺][F⁻]² over the COMMITTED concentrations = Ksp."""
    data = ChemData.load(ROOT)
    L = build_solubility_lesson(_common_spec(), data, "t")
    ions = [r for r in L["ice"]["species"] if r.get("in_quotient") is not False]
    Q = _quotient([Decimal(r["equilibrium_M"]) for r in ions], [r["nu"] for r in ions])
    ksp = Decimal(L["equilibrium_constant"]["value"])
    assert abs(Q - ksp) / ksp < Decimal("1e-6")


def test_common_ion_refuses_foreign_ion():
    """A 'common' ion must be shared with the salt — Cl⁻ is not one of CaF2's ions."""
    data = ChemData.load(ROOT)
    with pytest.raises(BuildError, match="not one of"):
        build_solubility_lesson(_common_spec(common_ion="Cl^-"), data, "t")


def test_common_ion_refuses_nonpositive_molarity():
    data = ChemData.load(ROOT)
    with pytest.raises(BuildError, match="positive common_ion_molarity_M"):
        build_solubility_lesson(_common_spec(molarity="0"), data, "t")


def test_build_common_ion_round_trip():
    lesson, out_rel = build_equilibrium(SPEC_KSP_COMMON, ROOT)
    assert out_rel == "equilibrium/calcium-fluoride-common-ion.equilibrium.json"
    assert lesson["subtype"] == "solubility" and lesson["reaction"]["common_ion"] == "F^-"


# ── polyprotic (staged ionization — Kₐ1 ≫ Kₐ2 ≫ Kₐ3, each stage solved on the previous stage's output) ──

def test_polyprotic_data_loaded_decreasing_ka():
    data = ChemData.load(ROOT)
    rec = data.polyprotic_constant("H3PO4")
    kas = [s["ka"] for s in rec["stages"]]
    assert kas == [Decimal("7.5e-3"), Decimal("6.2e-8"), Decimal("4.2e-13")]
    assert kas[0] > kas[1] > kas[2]                                   # strictly decreasing (checked on load)
    assert [s["anion"] for s in rec["stages"]] == ["H2PO4^-", "HPO4^2-", "PO4^3-"]


def _poly_spec():
    return {"id": "t", "title": "t", "slug": "t", "topic": "equilibrium", "scenario": "s", "acid": "H3PO4",
            "initial_molarity_M": "0.100", "misconception": {"claim": "c", "refuted_by": "later_stages_negligible"}}


def test_builds_phosphoric_acid_lesson():
    data, acidbase = ChemData.load(ROOT), AcidBase.load(ROOT)
    L = build_polyprotic_lesson(_poly_spec(), data, acidbase, "t")
    assert L["subtype"] == "polyprotic"
    assert L["equilibrium_constant"]["symbol"] == "K_a1" and L["equilibrium_constant"]["value"] == "0.0075"
    # the first ionization sets the pH: [H+] ≈ 0.0239, pH ≈ 1.62, ~23.9% of the first proton ionized
    assert L["result"]["pH_display"] == "1.62"
    assert L["result"]["hydronium_M_display"] == "0.0239"
    assert L["result"]["percent_ionization_display"] == "23.9"
    assert L["result"]["proton_count"] == 3
    # the ladder is the acid + its three successive anions; two later stages (2 and 3)
    assert [s["id"] for s in L["result"]["species_ladder"]] == ["H3PO4", "H2PO4^-", "HPO4^2-", "PO4^3-"]
    assert [ls["index"] for ls in L["result"]["later_stages"]] == [2, 3]
    assert all(L["checks"].values())


def test_polyprotic_amphiprotic_middle_equals_ka2():
    """The signature polyprotic result: [HPO4²⁻] ≈ Kₐ2, because after stage 1 [H+] ≈ [H2PO4⁻] collapses the
    second stage's mass-action law to Kₐ2 ≈ [HPO4²⁻]. It falls out of the machine solve, not asserted."""
    data, acidbase = ChemData.load(ROOT), AcidBase.load(ROOT)
    L = build_polyprotic_lesson(_poly_spec(), data, acidbase, "t")
    hpo4 = next(s for s in L["result"]["species_ladder"] if s["id"] == "HPO4^2-")
    ka2 = Decimal(L["result"]["later_stages"][0]["ka_value"])
    assert abs(Decimal(hpo4["equilibrium_M"]) - ka2) / ka2 < Decimal("1e-3")
    # and the fully-stripped phosphate is essentially absent (< 1e-15 M)
    po4 = next(s for s in L["result"]["species_ladder"] if s["id"] == "PO4^3-")
    assert Decimal(po4["equilibrium_M"]) < Decimal("1e-15")


def test_polyprotic_each_stage_satisfies_its_ka():
    """Every stage's committed concentrations reproduce that stage's Kₐ (Q = Kₐ per stage)."""
    data, acidbase = ChemData.load(ROOT), AcidBase.load(ROOT)
    L = build_polyprotic_lesson(_poly_spec(), data, acidbase, "t")
    for ls in L["result"]["later_stages"]:
        re_eq = Decimal(ls["initial_reactant_M"]) - Decimal(ls["extent_M"])
        h_eq = Decimal(ls["initial_hydronium_M"]) + Decimal(ls["extent_M"])
        an_eq = Decimal(ls["anion_equilibrium_M"])
        Q = h_eq * an_eq / re_eq
        ka = Decimal(ls["ka_value"])
        assert abs(Q - ka) / ka < Decimal("1e-6")


def test_polyprotic_stages_chain():
    """Each later stage starts on the previous stage's equilibrium concentrations (the successive treatment)."""
    data, acidbase = ChemData.load(ROOT), AcidBase.load(ROOT)
    L = build_polyprotic_lesson(_poly_spec(), data, acidbase, "t")
    # stage 2's reactant [H2PO4⁻]₀ = stage 1's anion equilibrium (the top-level ice's product)
    anion1_eq = next(r for r in L["ice"]["species"] if r["id"] == "H2PO4^-")["equilibrium_M"]
    assert L["result"]["later_stages"][0]["initial_reactant_M"] == anion1_eq


def test_polyprotic_refuses_monoprotic_acid():
    data, acidbase = ChemData.load(ROOT), AcidBase.load(ROOT)
    spec = dict(_poly_spec(), acid="HC2H3O2")                          # acetic acid — one proton
    with pytest.raises(BuildError, match="polyprotic lesson needs"):
        build_polyprotic_lesson(spec, data, acidbase, "t")


def test_polyprotic_dispatch_routes_by_proton_count():
    """build_equilibrium routes a triprotic acid to polyprotic and a monoprotic acid to weak-acid."""
    poly, rel = build_equilibrium(SPEC_POLY, ROOT)
    assert rel == "equilibrium/phosphoric-acid-ph.equilibrium.json" and poly["subtype"] == "polyprotic"
    mono, _ = build_equilibrium(SPEC, ROOT)                            # acetic-acid-ph.equilibrium.toml
    assert mono["subtype"] == "weak-acid"


# ── titration (the ledger marched as strong base is added to a weak acid — a curve, region by region) ──

def _titration_spec(acid="HC2H3O2", titrant="NaOH"):
    return {"id": "t", "title": "t", "slug": "t", "topic": "equilibrium", "scenario": "s", "acid": acid,
            "acid_molarity_M": "0.100", "acid_volume_mL": "25.0", "titrant": titrant, "titrant_molarity_M": "0.100",
            "misconception": {"claim": "c", "refuted_by": "weak_acid_equivalence_is_basic"}}


def test_builds_titration_curve():
    data, acidbase = ChemData.load(ROOT), AcidBase.load(ROOT)
    L = build_titration_lesson(_titration_spec(), data, acidbase, "t")
    assert L["subtype"] == "titration"
    t = L["titration"]
    assert t["equivalence_volume_mL_display"] == "25"                  # 0.100·25.0 / 0.100
    assert t["half_equivalence_volume_mL_display"] == "12.5"
    assert t["pKa_display"] == "4.74"
    # the three landmark pH values: initial acidic, half-eq = pKa, equivalence basic
    assert t["landmarks"]["initial"]["pH_display"] == "2.88"
    assert t["landmarks"]["equivalence"]["pH_display"] == "8.72"
    assert len(t["curve"]) >= 3
    assert all(L["checks"].values())


def test_titration_half_equivalence_is_pka():
    """The defining landmark: at half-equivalence [HA] = [A⁻], so pH = pKₐ (to two decimals)."""
    data, acidbase = ChemData.load(ROOT), AcidBase.load(ROOT)
    t = build_titration_lesson(_titration_spec(), data, acidbase, "t")["titration"]
    assert t["landmarks"]["half_equivalence"]["pH_display"] == t["pKa_display"] or \
        abs(Decimal(t["landmarks"]["half_equivalence"]["pH"]) - Decimal(t["pKa"])) < Decimal("0.02")


def test_titration_equivalence_is_basic():
    """A weak acid + strong base is BASIC at equivalence (the conjugate base hydrolyses) — refutes the pH-7 idea."""
    data, acidbase = ChemData.load(ROOT), AcidBase.load(ROOT)
    t = build_titration_lesson(_titration_spec(), data, acidbase, "t")["titration"]
    assert Decimal(t["landmarks"]["equivalence"]["pH"]) > 7
    assert t["landmarks"]["equivalence"]["region"] == "equivalence"


def test_titration_curve_monotonic_and_regioned():
    """pH rises monotonically along the curve, and the regions appear in order (initial → buffer → equivalence → excess)."""
    data, acidbase = ChemData.load(ROOT), AcidBase.load(ROOT)
    t = build_titration_lesson(_titration_spec(), data, acidbase, "t")["titration"]
    pHs = [Decimal(p["pH"]) for p in t["curve"]]
    assert all(b >= a for a, b in zip(pHs, pHs[1:]))                   # non-decreasing
    regions = [p["region"] for p in t["curve"]]
    assert regions[0] == "initial" and "buffer" in regions and "equivalence" in regions and regions[-1] == "excess-base"


def test_titration_refuses_strong_acid():
    data, acidbase = ChemData.load(ROOT), AcidBase.load(ROOT)
    with pytest.raises(BuildError, match="not a weak acid"):
        build_titration_lesson(_titration_spec(acid="HCl"), data, acidbase, "t")


def test_titration_refuses_non_base_titrant():
    data, acidbase = ChemData.load(ROOT), AcidBase.load(ROOT)
    with pytest.raises(BuildError, match="not in data/acids-bases.toml"):
        build_titration_lesson(_titration_spec(titrant="HCl"), data, acidbase, "t")


def test_titration_dispatch_and_round_trip():
    lesson, rel = build_equilibrium(SPEC_TITRATION, ROOT)
    assert rel == "equilibrium/acetic-acid-titration.equilibrium.json" and lesson["subtype"] == "titration"


# ── weak base (the 3rd increment — water excluded from Q like the solid; Kb → pOH → pH via Kw) ──

def _base_system(c0):
    # NH3 + H2O <=> NH4+ + OH- ; water excluded from Q (in_quotient False) -> Q = [NH4+][OH-]/[NH3]
    return [
        {"id": "NH3", "nu": -1, "initial_M": Decimal(c0)},
        {"id": "H2O", "nu": -1, "initial_M": Decimal(0), "in_quotient": False},
        {"id": "NH4^+", "nu": 1, "initial_M": Decimal(0)},
        {"id": "OH^-", "nu": 1, "initial_M": Decimal(0)},
    ]


def test_weak_base_root_mirrors_weak_acid():
    """0.100 M base, Kb = 1.8e-5 — the SAME equation as 0.100 M acetic acid, Ka = 1.8e-5, so the same extent
    (water is excluded from Q exactly like the Ksp solid). [OH-] ≈ 1.333e-3, residual tiny."""
    r = solve_equilibrium(_base_system("0.100"), Decimal("1.8e-5"), "ammonia")
    assert abs(r["extent"] - Decimal("0.00133267")) < Decimal("1e-7")
    assert r["residual"] < Decimal("1e-40")
    assert r["fwd_limit"] == Decimal("0.100")           # bounded by the base, not water


def test_water_excluded_from_base_quotient():
    """Q is over the dissolved ions/base only — water (in_quotient False) never enters, whatever its value."""
    q_ions = _quotient([Decimal("0.0987"), Decimal("0.00133"), Decimal("0.00133")], [-1, 1, 1])
    q_all = _quotient([Decimal("0.0987"), Decimal("55"), Decimal("0.00133"), Decimal("0.00133")],
                      [-1, -1, 1, 1], in_q=[True, False, True, True])
    assert q_all == q_ions


def _base_spec(**over):
    base = {"id": "t", "title": "t", "slug": "t", "topic": "equilibrium", "scenario": "s",
            "base": "NH3", "initial_molarity_M": "0.100",
            "misconception": {"claim": "c", "refuted_by": "weak_base_partial_ionization"}}
    base.update(over)
    return base


def test_builds_ammonia_lesson():
    data = ChemData.load(ROOT)
    L = build_weak_base_lesson(_base_spec(), data, "t")
    assert L["kind"] == "equilibrium" and L["subtype"] == "weak-base"
    assert L["reaction"]["text"] == "NH3(aq) + H2O(l) <=> NH4^+(aq) + OH^-(aq)"
    assert L["reaction"]["conjugate_acid"] == "NH4^+"
    assert L["equilibrium_constant"]["symbol"] == "K_b"
    assert L["equilibrium_constant"]["value"] == "0.000018"
    # the mirror of acetic acid: pOH 2.88 (= acetic's pH), pH 11.12
    assert L["ice"]["extent_M_display"] == "0.00133"
    assert L["result"]["pOH_display"] == "2.88"
    assert L["result"]["pH_display"] == "11.12"
    assert L["result"]["percent_ionization_display"] == "1.33"
    assert all(L["checks"].values())


def test_ammonia_kw_bridge_holds():
    """The K_w bridge: [H+] = Kw/[OH-], and pH + pOH = pKw = 14.00 (the load-bearing new relation)."""
    data = ChemData.load(ROOT)
    L = build_weak_base_lesson(_base_spec(), data, "t")
    oh = Decimal(L["result"]["hydroxide_M"])
    hplus = Decimal(L["result"]["hydronium_M"])
    kw = Decimal(L["result"]["kw"])
    assert abs(hplus - kw / oh) / (kw / oh) < Decimal("1e-6")
    assert abs(Decimal(L["result"]["pH"]) + Decimal(L["result"]["pOH"]) - Decimal(14)) < Decimal("1e-4")


def test_base_ice_identity_water_excluded():
    """Every dissolved row = initial + ν·x; the water row is the '—' excluded (in_quotient False) row."""
    data = ChemData.load(ROOT)
    L = build_weak_base_lesson(_base_spec(), data, "t")
    water = next(r for r in L["ice"]["species"] if r["id"] == "H2O")
    assert water["in_quotient"] is False and "equilibrium_M" not in water and water["phase"] == "l"
    x = Decimal(L["ice"]["extent_M"])
    for row in L["ice"]["species"]:
        if row.get("in_quotient") is False:
            continue
        assert abs(Decimal(row["equilibrium_M"]) - (Decimal(row["initial_M"]) + row["nu"] * x)) < Decimal("1e-10")


def test_base_regimes_layered():
    data = ChemData.load(ROOT)
    L = build_weak_base_lesson(_base_spec(), data, "t")
    assert {"ledger-exact", "rule-sourced", "model-exact"} <= {r["regime"] for r in L["regimes"]}


def test_refuses_unknown_base():
    data = ChemData.load(ROOT)
    with pytest.raises(BuildError, match="no base ionization constant"):
        build_weak_base_lesson(_base_spec(base="CH3NH2"), data, "t")


def test_refuses_nonpositive_base_concentration():
    data = ChemData.load(ROOT)
    with pytest.raises(BuildError, match="molarity must be positive"):
        build_weak_base_lesson(_base_spec(initial_molarity_M="0"), data, "t")


def test_base_ionization_constant_loaded():
    data = ChemData.load(ROOT)
    rec = data.base_ionization_constant("NH3")
    assert rec["kb"] == Decimal("1.8e-5") and rec["conjugate_acid"] == "NH4^+"
    assert data.water_ion_product() == Decimal("1.0e-14")


def test_build_weak_base_round_trip():
    lesson, out_rel = build_equilibrium(SPEC_BASE, ROOT)
    assert out_rel == "equilibrium/ammonia-ph.equilibrium.json"
    assert lesson["id"] == "ammonia-ph" and lesson["subtype"] == "weak-base"


# ── buffer (the 4th increment — the same reaction with A⁻ already present: common-ion + Henderson–Hasselbalch) ──

def _buffer_spec(**over):
    base = {"id": "t", "title": "t", "slug": "t", "topic": "equilibrium", "scenario": "s",
            "acid": "HC2H3O2", "acid_molarity_M": "0.100", "conjugate_base_molarity_M": "0.100",
            "misconception": {"claim": "c", "refuted_by": "common_ion_ignored"}}
    base.update(over)
    return base


def test_buffer_solver_nonzero_initial_product():
    """The buffer case: A⁻ starts at 0.100 M. The solver handles the nonzero initial product — the extent is tiny
    (~1.8e-5, the common ion suppresses ionization) and Q = Ka."""
    r = solve_equilibrium([
        {"id": "HA", "nu": -1, "initial_M": Decimal("0.100")},
        {"id": "H^+", "nu": 1, "initial_M": Decimal(0)},
        {"id": "A^-", "nu": 1, "initial_M": Decimal("0.100")},
    ], Decimal("1.8e-5"), "buffer")
    assert Decimal("1.7e-5") < r["extent"] < Decimal("1.9e-5")
    assert r["residual"] < Decimal("1e-40")


def test_builds_acetate_buffer_lesson():
    data, ab = _data_ab()
    L = build_buffer_lesson(_buffer_spec(), data, ab, "t")
    assert L["kind"] == "equilibrium" and L["subtype"] == "buffer"
    assert L["reaction"]["text"] == "HC2H3O2 <=> H^+ + C2H3O2^-"
    # equal concentrations → pH = pKa = 4.74
    assert L["result"]["pH_display"] == "4.74"
    assert L["result"]["pKa_display"] == "4.74"
    assert L["result"]["buffer_ratio_display"] == "1"
    assert all(L["checks"].values())


def test_buffer_henderson_hasselbalch_identity():
    """pH = pKa + log10([A⁻]/[HA]) on the EQUILIBRIUM concentrations reproduces −log10[H⁺] (H-H = mass action, logged)."""
    import math
    data, ab = _data_ab()
    L = build_buffer_lesson(_buffer_spec(), data, ab, "t")
    hplus = Decimal(L["ice"]["species"][1]["equilibrium_M"])   # the H^+ row
    pH = -math.log10(float(hplus))
    hh = float(Decimal(L["result"]["pKa"])) + math.log10(float(Decimal(L["result"]["buffer_ratio"])))
    assert abs(pH - hh) < 1e-6
    assert abs(float(Decimal(L["result"]["hh_pH"])) - pH) < 1e-6


def test_buffer_common_ion_suppression():
    """The common-ion contrast: the acid alone would give pH 2.88 and ionize ~74× more — the ledger shows it."""
    data, ab = _data_ab()
    L = build_buffer_lesson(_buffer_spec(), data, ab, "t")
    assert L["result"]["pH_no_buffer_display"] == "2.88"        # 0.100 M acetic acid alone
    assert Decimal("70") < Decimal(L["result"]["suppression_factor_display"]) < Decimal("78")


def test_buffer_dispatches_by_conjugate_base_key():
    """`acid` alone → weak-acid; `acid` + `conjugate_base_molarity_M` → buffer (build_equilibrium dispatch)."""
    lesson, out_rel = build_equilibrium(SPEC_BUFFER, ROOT)
    assert out_rel == "equilibrium/acetate-buffer.equilibrium.json"
    assert lesson["subtype"] == "buffer"
    # the plain weak-acid spec (no conjugate base) still builds the weak-acid subtype
    acid_only, _ = build_equilibrium(SPEC, ROOT)
    assert acid_only["subtype"] == "weak-acid"


def test_buffer_refuses_nonpositive_conjugate_base():
    data, ab = _data_ab()
    with pytest.raises(BuildError, match="positive acid and conjugate-base"):
        build_buffer_lesson(_buffer_spec(conjugate_base_molarity_M="0"), data, ab, "t")


# ── prediction (the 9th increment — Q vs Ksp: a SNAPSHOT comparison, not a solve; the `prediction` lesson kind) ──

def _pred_spec(**over):
    spec = {"id": "t", "title": "t", "slug": "t", "topic": "equilibrium", "scenario": "s", "salt": "CaF2",
            "cation_source": {"formula": "Ca(NO3)2", "molarity_M": "0.010", "volume_mL": "40.0", "per_formula": 1},
            "anion_source": {"formula": "NaF", "molarity_M": "0.010", "volume_mL": "60.0", "per_formula": 1},
            "misconception": {"claim": "c", "refuted_by": "q_exceeds_ksp"}}
    spec.update(over)
    return spec


def test_prediction_builds_and_forms_precipitate():
    """The canonical case: mixing 0.010 M sources gives Q ≫ Ksp → a precipitate forms (the `prediction` kind)."""
    data = ChemData.load(ROOT)
    L = build_prediction_lesson(_pred_spec(), data, "t")
    assert L["kind"] == "prediction"
    assert L["result"]["verdict"] == "precipitate"
    assert L["result"]["forms_precipitate"] is True
    assert L["result"]["comparison_symbol"] == ">"
    assert L["equilibrium_constant"]["symbol"] == "K_sp"
    assert all(L["checks"].values())


def test_prediction_mixing_dilution_exact():
    """40.0 mL of 0.010 M into 100.0 mL total → 0.00400; 60.0 mL → 0.00600 (each diluted by V_source/V_total)."""
    data = ChemData.load(ROOT)
    L = build_prediction_lesson(_pred_spec(), data, "t")
    assert L["mixing"]["volume_total_mL"] == "100"
    assert Decimal(L["mixing"]["cation_source"]["mixed_M"]) == Decimal("0.004")
    assert Decimal(L["mixing"]["anion_source"]["mixed_M"]) == Decimal("0.006")


def test_prediction_quotient_and_margin():
    """Q = [Ca2+][F-]^2 = (0.004)(0.006)^2 = 1.44e-7, = 3600× above Ksp = 4.0e-11 (OpenStax App-J, QC 2026-07-09)."""
    data = ChemData.load(ROOT)
    L = build_prediction_lesson(_pred_spec(), data, "t")
    assert Decimal(L["quotient"]["value"]) == Decimal("1.44e-7")
    margin = Decimal("1.44e-7") / Decimal("4.0e-11")
    assert Decimal("3500") < Decimal(L["result"]["margin_display"]) < Decimal("3700")
    assert abs(margin - Decimal(L["result"]["margin_display"])) / margin < Decimal("0.01")
    assert L["result"]["margin_direction"] == "above"


def test_prediction_dilute_mix_stays_clear():
    """Verdict FLIPS when the ions are dilute enough: Q < Ksp → no precipitate (the verdict tracks Q vs Ksp)."""
    data = ChemData.load(ROOT)
    L = build_prediction_lesson(_pred_spec(
        cation_source={"formula": "Ca(NO3)2", "molarity_M": "0.00002", "volume_mL": "50.0", "per_formula": 1},
        anion_source={"formula": "NaF", "molarity_M": "0.00002", "volume_mL": "50.0", "per_formula": 1},
    ), data, "t")
    assert L["result"]["verdict"] == "no-precipitate"
    assert L["result"]["forms_precipitate"] is False
    assert L["result"]["comparison_symbol"] == "<"
    assert L["result"]["margin_direction"] == "below"


def test_prediction_refuses_unknown_salt():
    data = ChemData.load(ROOT)
    with pytest.raises(BuildError, match="no solubility product"):
        build_prediction_lesson(_pred_spec(salt="NaCl"), data, "t")


def test_prediction_refuses_source_without_its_ion():
    """The cation source must actually contain the cation the right number of times (monatomic, machine-checked)."""
    data = ChemData.load(ROOT)
    with pytest.raises(BuildError, match="does not release that many"):
        build_prediction_lesson(_pred_spec(
            cation_source={"formula": "NaCl", "molarity_M": "0.010", "volume_mL": "40.0", "per_formula": 1}), data, "t")


def test_prediction_refuses_nonneutral_source():
    data = ChemData.load(ROOT)
    with pytest.raises(BuildError, match="not a neutral compound"):
        build_prediction_lesson(_pred_spec(
            cation_source={"formula": "Ca^2+", "molarity_M": "0.010", "volume_mL": "40.0", "per_formula": 1}), data, "t")


def test_prediction_refuses_nonpositive_volume():
    data = ChemData.load(ROOT)
    with pytest.raises(BuildError, match="volumes must be positive"):
        build_prediction_lesson(_pred_spec(
            anion_source={"formula": "NaF", "molarity_M": "0.010", "volume_mL": "0", "per_formula": 1}), data, "t")


def test_prediction_round_trip():
    lesson, out_rel = build_prediction(SPEC_PREDICTION, ROOT)
    assert out_rel == "equilibrium/calcium-fluoride-precipitation.prediction.json"
    assert lesson["kind"] == "prediction"
    assert lesson["result"]["forms_precipitate"] is True


def test_prediction_no_precipitate_round_trip():
    """The Mg(OH)₂ lesson: a dilute mix where Q < Ksp → no precipitate (the other verdict, the 2nd curated Ksp salt,
    and a polyatomic-ion (OH⁻) source whose multiplicity rides the disclosed dissociation model)."""
    lesson, out_rel = build_prediction(SPEC_PREDICTION_NO, ROOT)
    assert out_rel == "equilibrium/magnesium-hydroxide-no-precipitate.prediction.json"
    assert lesson["reaction"]["salt"] == "Mg(OH)2"
    assert lesson["result"]["verdict"] == "no-precipitate"
    assert lesson["result"]["forms_precipitate"] is False
    assert lesson["result"]["comparison_symbol"] == "<"
