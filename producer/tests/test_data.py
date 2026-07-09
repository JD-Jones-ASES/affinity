"""Dataset loading + self-consistency. Values hand-checked against CIAAW abridged atomic weights;
molar masses computed independently here, not by re-reading the producer's own output."""

from decimal import Decimal
from pathlib import Path

import pytest

from chemkernel import BuildError
from chemkernel.data import ChemData

ROOT = Path(__file__).resolve().parents[2]


def data():
    return ChemData.load(ROOT)


def test_loads_and_self_validates():
    d = data()  # ChemData.load() runs validate(); a bad dataset would raise here
    assert d.elements["Ca"].Z == 20
    assert d.elements["Ca"].atomic_weight == Decimal("40.078")
    assert d.elements["Cl"].atomic_weight == Decimal("35.45")
    assert d.elements["Na"].group == 1 and d.elements["Na"].period == 3


def test_atomic_weights_are_decimal_not_float():
    d = data()
    n_w = n_mn = 0
    for el in d.elements.values():
        # exactly one of atomic_weight (Decimal, never float — ADR-0013) / mass_number (int) per element (ADR-0052)
        assert (el.atomic_weight is None) != (el.mass_number is None), f"{el.symbol}: need exactly one"
        if el.atomic_weight is not None:
            assert isinstance(el.atomic_weight, Decimal)
            n_w += 1
        else:
            assert isinstance(el.mass_number, int)
            n_mn += 1
    assert (n_w, n_mn) == (84, 34), f"expected 84 standard weights + 34 mass numbers, got {n_w}+{n_mn}"


def test_avogadro_constant_loaded_exact():
    d = data()  # the 2019 SI redefinition fixed N_A exactly (ADR-0006); read as Decimal, never float
    assert isinstance(d.avogadro, Decimal)
    assert d.avogadro == Decimal("6.02214076e23")
    assert d.sources["constants"] == "bipm-si-2019"


def test_formation_enthalpies_loaded_by_formula_and_phase():
    # standard ΔH_f° (ADR-0043): a data-sourced datum, keyed by formula AND phase (H2O differs by state); read
    # as Decimal (never float). Elements in their standard state are 0 by definition.
    d = data()
    assert d.sources["formation_enthalpies"] == "openstax-chemistry-2e"
    assert d.formation_enthalpy("CO2", "g")["value"] == Decimal("-393.51")
    assert d.formation_enthalpy("H2O", "l")["value"] == Decimal("-285.83")
    assert d.formation_enthalpy("H2O", "g")["value"] == Decimal("-241.82")   # vapor differs from liquid
    o2 = d.formation_enthalpy("O2", "g")
    assert o2["value"] == Decimal("0") and o2["element"] is True             # element → reference level
    assert all(isinstance(v["value"], Decimal) for v in d.formation_enthalpies.values())


def test_missing_formation_enthalpy_refuses():
    # the energy ledger refuses to guess a missing ΔH_f° (ADR-0008/0043) — and it is phase-specific
    d = data()
    with pytest.raises(BuildError):
        d.formation_enthalpy("C6H12O6", "s")   # glucose is not curated
    with pytest.raises(BuildError):
        d.formation_enthalpy("CO2", "l")        # wrong phase for CO2


def test_molar_mass_caco3_matches_hand_value():
    # 40.078 + 12.011 + 3*15.999 = 100.086  (brief quotes 100.09 to 2 dp)
    d = data()
    assert d.molar_mass("CaCO3") == Decimal("100.086")
    assert d.molar_mass("CaCO3").quantize(Decimal("0.01")) == Decimal("100.09")


def test_molar_mass_cacl2_and_na2co3():
    d = data()
    assert d.molar_mass("CaCl2") == Decimal("40.078") + 2 * Decimal("35.45")   # 110.978
    assert d.molar_mass("Na2CO3") == 2 * Decimal("22.990") + Decimal("12.011") + 3 * Decimal("15.999")


def test_unknown_element_raises():
    d = data()
    with pytest.raises(BuildError):
        d.molar_mass("Zz")  # a fictitious element — all 118 real ones now exist (ADR-0052)


def test_no_standard_weight_element_refuses_molar_mass():
    # a no-standard-weight element (mass_number only, ADR-0052) has no value for arithmetic — refuse, not guess
    d = data()
    assert d.elements["Tc"].atomic_weight is None and d.elements["Tc"].mass_number == 97
    with pytest.raises(BuildError):
        d.molar_mass("Tc")  # technetium: mass_number 97, no standard atomic weight


def test_every_ion_composition_is_known():
    d = data()
    assert d.ions["CO3^2-"].charge == -2
    assert d.ions["Ca^2+"].kind == "monatomic" and d.ions["Ca^2+"].element == "Ca"
    # every ion formula must be composed of elements present in elements.toml (validate() guarantees this)
    from chemkernel.formula import parse_formula
    for ion in d.ions.values():
        for el in parse_formula(ion.formula).counts:
            assert el in d.elements


# --- periodic properties + widened element set (ADR-0031, Phase 1 item 5a) ---

_WIDENED_SET = ["H", "He", "Li", "Be", "B", "C", "N", "O", "F", "Ne", "Na", "Mg",
                "Al", "Si", "P", "S", "Cl", "Ar", "K", "Ca", "Fe", "Cu", "Zn"]


def test_element_set_widened_to_first_twenty_plus_transition_metals():
    d = data()
    for sym in _WIDENED_SET:
        assert sym in d.elements, f"{sym} missing from the widened element set"
    assert d.elements["Ne"].Z == 10 and d.elements["Ne"].group == 18
    assert d.elements["Li"].group == 1 and d.elements["F"].group == 17


def test_periodic_properties_load_as_decimal():
    d = data()
    ca = d.elements["Ca"]  # spot-check exact curated values (never float — ADR-0013)
    assert ca.electronegativity == Decimal("1.00")
    assert ca.covalent_radius_pm == Decimal("176")
    assert ca.first_ionization_kj_mol == Decimal("589.8")
    assert d.elements["F"].electronegativity == Decimal("3.98")
    assert d.elements["H"].first_ionization_kj_mol == Decimal("1312.0")
    for el in d.elements.values():
        for v in (el.electronegativity, el.covalent_radius_pm, el.first_ionization_kj_mol):
            assert v is None or isinstance(v, Decimal)


def test_property_optionality_matches_where_defined():
    d = data()
    # electronegativity (ADR-0052): 71 shipped; undefined for the noble gases (never zero), and omitted for the
    # ten compilation-disputed heavy metals + the lanthanides/actinides the oracle cannot confirm.
    for ng in ["He", "Ne", "Ar", "Kr", "Xe", "Rn", "Og"]:
        assert d.elements[ng].electronegativity is None
    for omit in ["Tc", "Lu", "W", "Pt", "Au", "Hg", "Tl", "Pb", "Bi", "U"]:
        assert d.elements[omit].electronegativity is None, f"{omit} EN should be omitted (compilation-disputed)"
    assert d.elements["F"].electronegativity == Decimal("3.98")
    assert d.elements["Fe"].electronegativity == Decimal("1.83")
    assert sum(1 for el in d.elements.values() if el.electronegativity is not None) == 71
    # covalent radius: shipped for main-group Z≤20, deferred (omitted) for the transition metals + everything above
    for tm in ["Fe", "Cu", "Zn"]:
        assert d.elements[tm].covalent_radius_pm is None
    assert d.elements["Cl"].covalent_radius_pm == Decimal("102")
    assert sum(1 for el in d.elements.values() if el.covalent_radius_pm is not None) == 20
    # first ionization energy: shipped for Z 1–103 (measured/recommended); the transactinides (Z≥104) are omitted
    assert d.elements["Lr"].first_ionization_kj_mol is not None
    assert d.elements["Rf"].first_ionization_kj_mol is None
    assert sum(1 for el in d.elements.values() if el.first_ionization_kj_mol is not None) == 103


def test_property_sources_registered():
    d = data()
    assert d.sources["electronegativity"] == "allred-1961-electronegativity"
    assert d.sources["covalent_radius"] == "cordero-2008-covalent-radii"
    assert d.sources["ionization_energy"] == "nist-ionization-energies"


def test_new_group_1_2_17_common_ions_present():
    d = data()
    for iid, el, ch in [("Li^+", "Li", 1), ("Be^2+", "Be", 2), ("F^-", "F", -1)]:
        assert d.ions[iid].charge == ch
        assert d.ions[iid].element == el
        assert el in d.elements  # composition machine-checked by validate() on load


def test_vsepr_table_loaded_and_sourced():
    d = data()
    # the sourced VSEPR table (ADR-0044), keyed (domains, lone_pairs) → the geometry names + ideal angle
    assert d.sources["vsepr"] == "openstax-chemistry-2e"
    assert d.vsepr[(2, 0)]["molecular_shape"] == "linear" and d.vsepr[(2, 0)]["ideal_angle"] == "180°"
    assert d.vsepr[(4, 0)]["electron_geometry"] == "tetrahedral"
    assert d.vsepr[(4, 1)]["molecular_shape"] == "trigonal pyramidal"
    assert d.vsepr[(4, 2)]["molecular_shape"] == "bent"        # water's shape
    assert (5, 0) not in d.vsepr                               # expanded octets deferred


def test_boiling_points_loaded_and_sourced():
    from decimal import Decimal
    d = data()
    # the sourced boiling-point evidence (ADR-0046) for the intermolecular-forces concept, keyed by formula
    assert d.sources["boiling_points"] == "nist-webbook-boiling-points"
    assert d.boiling_points["H2O"]["temperature_c"] == Decimal("100.0")
    assert d.boiling_points["H2O"]["phase_change"] == "boiling"
    assert d.boiling_points["CO2"]["phase_change"] == "sublimation"   # no liquid at 1 atm
    assert d.boiling_points["CH4"]["temperature_c"] == Decimal("-161.5")
