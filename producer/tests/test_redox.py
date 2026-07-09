"""Electrochemistry tier — the electron ledger (ADR-0050). Oxidation numbers + a galvanic cell (E°cell, ΔG=−nFE)."""

from decimal import Decimal
from pathlib import Path

import pytest

from chemkernel import BuildError
from chemkernel.build import build_electrochemistry
from chemkernel.data import ChemData
from chemkernel.redox import build_electrochemistry_lesson, oxidation_states

ROOT = Path(__file__).resolve().parents[2]
SPEC = ROOT / "problems" / "electrochemistry" / "daniell-cell.electrochemistry.toml"


@pytest.fixture(scope="module")
def data():
    return ChemData.load(ROOT)


def _spec(**over):
    s = {"id": "t", "title": "t", "slug": "t", "topic": "electrochemistry", "scenario": "s",
         "couples": ["Zn^2+", "Cu^2+"], "misconception": {"claim": "c", "refuted_by": "x"}}
    s.update(over)
    return s


# ── oxidation numbers ──

def test_free_element_and_monatomic_ion(data):
    assert oxidation_states("Zn", data, "t") == {"Zn": 0}
    assert oxidation_states("O2", data, "t") == {"O": 0}
    assert oxidation_states("Cu^2+", data, "t") == {"Cu": 2}
    assert oxidation_states("Cl^-", data, "t") == {"Cl": -1}


def test_oxoanions_solved_by_the_sum_constraint(data):
    assert oxidation_states("SO4^2-", data, "t")["S"] == 6      # O −2 ×4 = −8, S = −2 − (−8) = +6
    assert oxidation_states("MnO4^-", data, "t")["Mn"] == 7
    assert oxidation_states("NO3^-", data, "t")["N"] == 5
    assert oxidation_states("H2O", data, "t") == {"H": 1, "O": -2}
    assert oxidation_states("NaCl", data, "t") == {"Na": 1, "Cl": -1}


def test_solves_one_unknown_but_refuses_two(data):
    assert oxidation_states("PCl3", data, "t")["P"] == 3        # Cl −1 ×3 → P = +3 (one unknown, solved)
    with pytest.raises(BuildError, match="cannot assign|first-course"):
        oxidation_states("SiC", data, "t")                      # two rule-less elements → refuse (honest)


# ── the galvanic cell ──

def test_daniell_cell(data):
    L = build_electrochemistry_lesson(_spec(), data, "t")
    assert L["kind"] == "electrochemistry" and L["subtype"] == "galvanic"
    assert L["reaction"]["equation_text"] == "Zn + Cu^2+ -> Zn^2+ + Cu"
    assert L["reaction"]["electrons_transferred"] == 2
    assert L["half_reactions"]["oxidation"]["couple_name"] == "zinc(II)/zinc"       # Zn is the anode (lower E°)
    assert L["half_reactions"]["reduction"]["couple_name"] == "copper(II)/copper"   # Cu is the cathode (higher E°)
    assert L["cell"]["e_cell_display"] == "1.099"                # 0.337 − (−0.7618) = 1.0988 V
    assert L["result"]["delta_g_display"] == "-212"             # −nFE° = −2·96485·1.0988 = −212 kJ/mol
    assert L["result"]["spontaneous"] is True
    assert L["oxidation_states"]["oxidized"] == {"element": "Zn", "from": "0", "to": "+2"}
    assert L["oxidation_states"]["reduced"] == {"element": "Cu", "from": "+2", "to": "0"}
    assert all(L["checks"].values())


def test_cell_scales_electrons_to_the_lcm(data):
    # Cu (2 e⁻) with Ag⁺ (1 e⁻): n = lcm(2,1) = 2, so 2 Ag⁺ are reduced per Cu oxidized
    L = build_electrochemistry_lesson(_spec(couples=["Cu^2+", "Ag^+"]), data, "t")
    assert L["reaction"]["equation_text"] == "Cu + 2 Ag^+ -> Cu^2+ + 2 Ag"
    assert L["reaction"]["electrons_transferred"] == 2
    assert L["half_reactions"]["reduction"]["couple_name"] == "silver(I)/silver"    # Ag⁺ higher E° → cathode
    assert L["cell"]["e_cell_display"] == "0.4626"             # 0.7996 − 0.337
    assert all(L["checks"].values())


def test_e_cell_is_intensive_not_scaled_by_coefficients(data):
    """E°cell does not change when the electron count doubles — it is energy per charge, an intensive property."""
    daniell = build_electrochemistry_lesson(_spec(), data, "t")
    agcu = build_electrochemistry_lesson(_spec(couples=["Cu^2+", "Ag^+"]), data, "t")
    # both use n = 2 but the potentials differ only by the couples, not by any coefficient scaling
    assert Decimal(daniell["cell"]["e_cell_V"]) == Decimal("0.337") - Decimal("-0.7618")
    assert Decimal(agcu["cell"]["e_cell_V"]) == Decimal("0.7996") - Decimal("0.337")


def test_refuses_equal_potentials(data):
    with pytest.raises(BuildError, match="equal E°|no galvanic"):
        build_electrochemistry_lesson(_spec(couples=["Zn^2+", "Zn^2+"]), data, "t")


def test_refuses_unknown_couple(data):
    with pytest.raises(BuildError, match="no standard reduction potential"):
        build_electrochemistry_lesson(_spec(couples=["Zn^2+", "Au^3+"]), data, "t")


def test_faraday_and_reduction_potential_sourced(data):
    assert data.faraday == Decimal("96485.33212")
    assert data.reduction_potential("Cu^2+")["e_standard"] == Decimal("0.337")
    assert data.sources["reduction_potentials"] == "openstax-chemistry-2e"


def test_round_trip():
    L, out_rel = build_electrochemistry(SPEC, ROOT)
    assert out_rel == "electrochemistry/daniell-cell.electrochemistry.json"
    assert L["kind"] == "electrochemistry"
    assert L["cell"]["e_cell_display"] == "1.099"
    assert L["result"]["delta_g_display"] == "-212"
