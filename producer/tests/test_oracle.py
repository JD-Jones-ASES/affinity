"""Independent-oracle cross-checks (ADR-0026): third-party chemistry libraries re-verify the engine.

The verification thesis wants redundant, independent proof. These tests check our curated data and our
balancer against libraries with entirely separate data pipelines and algorithms:
  - `periodictable` — element masses (independent of our CIAAW-curated data/elements.toml),
  - `chempy` — formula-parsed molar masses and SymPy-based equation balancing.

Oracles are DEV-ONLY (pyproject dependency-group `dev`, ADR-0026): they never run at build time and never
supply a shipped value; runtime constants still come exclusively from cited `data/` (ADR-0006/0012).
Tolerances are loose (different atomic-weight editions round differently) — these catch transcription and
logic errors, not last-digit revisions. `importorskip` degrades gracefully if an oracle can't install.
"""

import tomllib
from decimal import Decimal
from pathlib import Path

import pytest

from chemkernel.balance import balance
from chemkernel.data import ChemData
from chemkernel.formula import parse_formula
from chemkernel.gym import _REACTIONS

chempy = pytest.importorskip("chempy")
periodictable = pytest.importorskip("periodictable")
mendeleev = pytest.importorskip("mendeleev")

ROOT = Path(__file__).resolve().parents[2]

_EV_TO_KJMOL = 96.485  # 1 eV in kJ/mol (see docs/SOURCES.md `nist-ionization-energies`)

# the balancing gym's neutral corpus (ADR-0028) — chempy parses element formulas, not caret-charge net-ionic
_NEUTRAL_REACTIONS = [r for r in _REACTIONS
                      if not any("^" in f for f in r["reactants"] + r["products"])]
# every distinct species the mass-stoichiometry / percent-yield gyms draw molar masses from (ADR-0029)
_CORPUS_SPECIES = sorted({f for r in _NEUTRAL_REACTIONS for f in r["reactants"] + r["products"]})

# every substance the corpus uses (gym salts ∪ lesson species)
_SUBSTANCES = ["NaCl", "CaCl2", "Na2CO3", "CaCO3", "Na3PO4", "Ca3(PO4)2"]


def _data():
    return ChemData.load(ROOT)


def test_all_118_elements_present():
    """The full periodic table (ADR-0052): exactly 118 elements, Z 1..118 each exactly once."""
    data = _data()
    zs = sorted(el.Z for el in data.elements.values())
    assert zs == list(range(1, 119)), f"expected Z 1..118, got {len(zs)} ({zs[:3]}..{zs[-3:]})"


def test_identity_matches_mendeleev():
    """Every element's Z, name, group, period, and block agree with mendeleev's independent element table
    (ADR-0052). mendeleev leaves the f-block (Ce-Lu, Th-Lr) without a group_id — our data must match."""
    data = _data()
    for sym, el in data.elements.items():
        m = mendeleev.element(sym)
        assert el.Z == m.atomic_number, f"{sym}: Z {el.Z} vs mendeleev {m.atomic_number}"
        assert el.name == m.name.lower(), f"{sym}: name '{el.name}' vs mendeleev '{m.name.lower()}'"
        assert el.period == m.period, f"{sym}: period {el.period} vs mendeleev {m.period}"
        assert el.block == m.block, f"{sym}: block '{el.block}' vs mendeleev '{m.block}'"
        assert el.group == m.group_id, f"{sym}: group {el.group} vs mendeleev group_id {m.group_id}"


def test_element_weights_match_periodictable():
    """Every curated CIAAW standard atomic weight agrees with periodictable's independent element table. The
    no-standard-weight elements (mass_number only, ADR-0052) are checked separately below."""
    data = _data()
    checked = 0
    for sym, el in data.elements.items():
        if el.atomic_weight is None:
            continue
        oracle = getattr(periodictable, sym).mass
        tol = max(float(getattr(el, "uncertainty", 0) or 0), 0.01)
        assert abs(float(el.atomic_weight) - oracle) <= tol, (
            f"{sym}: ours {el.atomic_weight} vs periodictable {oracle}")
        checked += 1
    assert checked == 84, f"expected 84 standard atomic weights, checked {checked}"


def test_mass_numbers_match_mendeleev():
    """Every no-standard-weight element's mass_number (IUPAC longest-lived isotope, ADR-0052) sits within 5 of
    mendeleev's most-stable-isotope mass. The window is loose because the 'longest-lived isotope' for the
    superheavies is genuinely source/date-dependent; the check catches a gross transcription error, not the
    isotope choice. mass_number never enters arithmetic — it is display provenance only."""
    data = _data()
    n = 0
    for sym, el in data.elements.items():
        if el.mass_number is None:
            continue
        assert el.atomic_weight is None, f"{sym}: has both atomic_weight and mass_number"
        oracle = round(mendeleev.element(sym).mass)
        assert abs(el.mass_number - oracle) <= 5, (
            f"{sym}: mass_number {el.mass_number} vs round(mendeleev.mass) {oracle}")
        n += 1
    assert n == 34, f"expected 34 no-standard-weight elements, got {n}"


def test_molar_masses_match_chempy():
    """Our molar-mass sums agree with chempy's independent parser + mass table."""
    data = _data()
    for f in _SUBSTANCES:
        ours = float(data.molar_mass(f))
        oracle = chempy.Substance.from_formula(f).mass
        assert abs(ours - oracle) <= 0.02, f"{f}: ours {ours} vs chempy {oracle}"


@pytest.mark.parametrize("formula", _CORPUS_SPECIES)
def test_corpus_molar_masses_match_chempy(formula):
    """Every species the stoichiometry gyms use (ADR-0029) has a molar mass chempy independently reproduces."""
    ours = float(_data().molar_mass(formula))
    oracle = chempy.Substance.from_formula(formula).mass
    assert abs(ours - oracle) <= 0.02, f"{formula}: ours {ours} vs chempy {oracle}"


@pytest.mark.parametrize("reactants,products", [
    (["CaCl2", "Na2CO3"], ["CaCO3", "NaCl"]),        # the carbonate lesson
    (["CaCl2", "Na3PO4"], ["Ca3(PO4)2", "NaCl"]),    # the phosphate lesson (3:2:1:6)
])
def test_balancer_matches_chempy(reactants, products):
    """Our conservation-matrix balancer and chempy's SymPy balancer agree exactly."""
    ours = balance([parse_formula(s) for s in reactants], [parse_formula(s) for s in products])
    r_or, p_or = chempy.balance_stoichiometry(set(reactants), set(products))
    oracle = [int(r_or[s]) for s in reactants] + [int(p_or[s]) for s in products]
    assert ours == oracle


@pytest.mark.parametrize("reaction", _NEUTRAL_REACTIONS,
                         ids=[" + ".join(r["reactants"]) for r in _NEUTRAL_REACTIONS])
def test_gym_balancing_corpus_matches_chempy(reaction):
    """Every neutral reaction the balancing gym ships (ADR-0028) balances identically under chempy."""
    reactants, products = reaction["reactants"], reaction["products"]
    ours = balance([parse_formula(s) for s in reactants], [parse_formula(s) for s in products])
    r_or, p_or = chempy.balance_stoichiometry(set(reactants), set(products))
    oracle = [int(r_or[s]) for s in reactants] + [int(p_or[s]) for s in products]
    assert ours == oracle


# the item-6 reaction-families corpus (ADR-0035), core neutral formulas — one per first-course family. chempy
# independently balances each, so the reactions the classifier/Atlas/gym ship are real, not just plausible.
_FAMILIES_CORPUS = [
    (["CH4", "O2"], ["CO2", "H2O"]), (["C3H8", "O2"], ["CO2", "H2O"]),
    (["N2", "H2"], ["NH3"]), (["Na", "Cl2"], ["NaCl"]), (["Mg", "O2"], ["MgO"]),
    (["KClO3"], ["KCl", "O2"]), (["CaCO3"], ["CaO", "CO2"]),
    (["Zn", "HCl"], ["ZnCl2", "H2"]), (["Fe", "CuSO4"], ["FeSO4", "Cu"]),
    (["HCl", "NaOH"], ["NaCl", "H2O"]), (["H2SO4", "NaOH"], ["Na2SO4", "H2O"]),
    (["HCl", "Na2CO3"], ["NaCl", "H2O", "CO2"]), (["HCl", "CaCO3"], ["CaCl2", "H2O", "CO2"]),
    (["NH4Cl", "NaOH"], ["NaCl", "NH3", "H2O"]),
    (["CaCl2", "Na2CO3"], ["CaCO3", "NaCl"]), (["MgCl2", "NaOH"], ["Mg(OH)2", "NaCl"]),
    (["CuSO4", "Na2CO3"], ["CuCO3", "Na2SO4"]),
]


@pytest.mark.parametrize("reactants,products", _FAMILIES_CORPUS,
                         ids=[" + ".join(r) for r, _ in _FAMILIES_CORPUS])
def test_families_corpus_balances_match_chempy(reactants, products):
    """Every reaction-families corpus reaction (ADR-0035) balances identically under chempy."""
    ours = balance([parse_formula(s) for s in reactants], [parse_formula(s) for s in products])
    r_or, p_or = chempy.balance_stoichiometry(set(reactants), set(products))
    oracle = [int(r_or[s]) for s in reactants] + [int(p_or[s]) for s in products]
    assert ours == oracle


# --- element-property oracle (ADR-0031): mendeleev independently re-checks the periodic-property curation.
# mendeleev's data pipeline is entirely separate from our cited sources (OpenStax/NIST/Cordero), so agreement
# is redundant proof and disagreement flags a transcription slip — exactly the failure mode ADR-0026 targets.

_NOBLE = {"He", "Ne", "Ar", "Kr", "Xe", "Rn", "Og"}


def test_electronegativity_matches_mendeleev():
    """Every SHIPPED revised-Pauling electronegativity agrees with mendeleev within 0.06 (ADR-0052). We do not
    require the converse: EN is honestly OMITTED wherever Allred-revised and the mendeleev cross-check diverge
    > 0.06 (ten compilation-disputed heavy metals) or where a value is undefined/unconfirmable — so a value
    mendeleev happens to carry (e.g. Xe) may still be omitted. The noble gases carry no EN (our editorial
    stance: undefined on the Pauling scale); we assert that stays true."""
    data = _data()
    shipped = 0
    for sym, el in data.elements.items():
        if sym in _NOBLE:
            assert el.electronegativity is None, f"{sym}: a noble gas must not ship an electronegativity"
        if el.electronegativity is None:
            continue
        oracle = mendeleev.element(sym).en_pauling
        assert oracle is not None, f"{sym}: we ship EN {el.electronegativity} but mendeleev has none"
        assert abs(float(el.electronegativity) - oracle) <= 0.06, (
            f"{sym}: ours {el.electronegativity} vs mendeleev en_pauling {oracle}")
        shipped += 1
    assert shipped == 71, f"expected 71 shipped electronegativities, got {shipped}"


def test_covalent_radius_matches_mendeleev():
    """Every curated covalent radius agrees with mendeleev's Cordero column (loose tol: C sp2/sp3 differ 3 pm)."""
    data = _data()
    shipped = 0
    for sym, el in data.elements.items():
        if el.covalent_radius_pm is None:
            continue
        oracle = mendeleev.element(sym).covalent_radius_cordero
        assert oracle is not None, f"{sym}: we ship a radius but mendeleev has no Cordero radius"
        assert abs(float(el.covalent_radius_pm) - oracle) <= 5.0, (
            f"{sym}: ours {el.covalent_radius_pm} vs mendeleev covalent_radius_cordero {oracle}")
        shipped += 1
    assert shipped >= 20, f"expected a covalent radius for every main-group Z≤20 element, got {shipped}"


def test_first_ionization_energy_matches_mendeleev():
    """Every SHIPPED first ionization energy agrees with mendeleev's NIST-derived value (eV → kJ/mol) within
    2.5 kJ/mol (ADR-0052). IE is shipped for Z 1..103 (measured/recommended); the transactinides (Z ≥ 104) are
    omitted (theoretical estimates, not confidently measured), so we check where present, not for every element."""
    data = _data()
    shipped = 0
    for sym, el in data.elements.items():
        if el.first_ionization_kj_mol is None:
            continue
        oracle_ev = mendeleev.element(sym).ionenergies.get(1)
        assert oracle_ev is not None, f"{sym}: mendeleev has no first ionization energy for {sym}"
        oracle_kj = oracle_ev * _EV_TO_KJMOL
        assert abs(float(el.first_ionization_kj_mol) - oracle_kj) <= 2.5, (
            f"{sym}: ours {el.first_ionization_kj_mol} vs mendeleev {oracle_kj:.1f} kJ/mol")
        shipped += 1
    assert shipped == 103, f"expected 103 shipped ionization energies, got {shipped}"
