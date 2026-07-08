"""End-to-end build: the authored Phase-0 spec through build_problem, key fields hand-checked."""

import os
import subprocess
import sys
from pathlib import Path

from chemkernel.build import build_problem

ROOT = Path(__file__).resolve().parents[2]
SPEC = ROOT / "problems" / "precipitation" / "calcium-carbonate-limiting.problem.toml"
SPEC_YIELD = ROOT / "problems" / "percent-yield" / "zinc-carbonate-percent-yield.problem.toml"
SPEC_NEUTRAL = ROOT / "problems" / "neutralization" / "hydrochloric-sodium-hydroxide.problem.toml"
SPEC_GAS = ROOT / "problems" / "gas-stoichiometry" / "zinc-hydrochloric-hydrogen.problem.toml"
SPEC_ENERGY = ROOT / "problems" / "thermochemistry" / "methane-combustion-enthalpy.problem.toml"


def test_builds_phase0_solution():
    sol, out_rel = build_problem(SPEC, ROOT)
    assert out_rel == "precipitation/calcium-carbonate-limiting.solution.json"
    assert sol["id"] == "precipitation-calcium-carbonate-limiting"

    assert sol["ledger"]["limiting"] == ["CaCl2"]
    assert sol["ledger"]["extent_mol"] == "0.0025"
    assert sol["result"]["precipitate"]["species"] == "CaCO3"
    assert sol["result"]["precipitate"]["mass_g"] == "0.250215"
    assert sol["result"]["precipitate"]["mass_g_display"] == "0.250"
    assert sol["result"]["leftover"] == [{"species": "Na2CO3", "moles": "0.0005"}]

    assert sol["equations"]["net_ionic"]["text"] == "Ca^2+ + CO3^2- -> CaCO3"
    assert sol["equations"]["spectators"] == ["Cl^-", "Na^+"]

    assert sol["solubility_basis"]["rule_id"] == "insol-carbonate"
    assert sol["solubility_basis"]["source"] == "openstax-chemistry-2e"

    assert all(sol["checks"].values())
    assert sol["provenance"]["sources"]["atomic_weight"] == "ciaaw-2021-atomic-weights"


def test_percent_yield_lesson():
    """The flagship percent-yield lesson (ADR-0029): theoretical = precipitate mass; percent = actual/theo×100."""
    from decimal import Decimal
    from fractions import Fraction

    sol, out_rel = build_problem(SPEC_YIELD, ROOT)
    assert out_rel == "percent-yield/zinc-carbonate-percent-yield.solution.json"
    assert sol["result"]["precipitate"]["species"] == "ZnCO3"
    assert sol["result"]["limiting_species"] == ["ZnCl2"]

    py = sol["result"]["percent_yield"]
    theoretical = Fraction(Decimal(py["theoretical_mass_g"]))
    actual = Fraction(Decimal(py["actual_mass_g"]))
    assert py["theoretical_mass_g"] == sol["result"]["precipitate"]["mass_g"]   # theoretical IS the ledger mass
    assert 0 < actual <= theoretical                                            # a physical yield
    assert abs(float(actual / theoretical * 100) - float(py["percent_display"])) <= 0.05  # display rounds to 0.1%
    # the lesson reuses the full precipitation pipeline (interactive + practice come for free)
    assert sol.get("interactive") and sol.get("practice")


def test_neutralization_lesson():
    """The first non-precipitation flagship (ADR-0037): acid + base → salt + water. The reported product is
    water (a general `product`, not a `precipitate`); the salt is named; there is no solubility claim."""
    sol, out_rel = build_problem(SPEC_NEUTRAL, ROOT)
    assert out_rel == "neutralization/hydrochloric-sodium-hydroxide.solution.json"
    # the net-ionic product is water; no solid precipitate
    assert "precipitate" not in sol["result"]
    assert sol["result"]["product"]["species"] == "H2O" and sol["result"]["product"]["phase"] == "l"
    assert sol["result"]["salt"]["species"] == "NaCl"
    assert sol["equations"]["net_ionic"]["text"] == "H^+ + OH^- -> H2O"
    assert sol["equations"]["spectators"] == ["Cl^-", "Na^+"]
    # the base runs out first (it is more dilute) — the smaller-VOLUME acid is actually in excess (the trap)
    assert sol["result"]["limiting_species"] == ["NaOH"]
    assert sol["result"]["leftover"] == [{"species": "HCl", "moles": "0.0005"}]
    # no rule-sourced regime, so no solubility source or basis (ADR-0037)
    assert [r["regime"] for r in sol["regimes"]] == ["ledger-exact", "model-exact"]
    assert "solubility" not in sol["provenance"]["sources"]
    assert "solubility_basis" not in sol
    # it still earns the full instrument: the limiting-reagent slider + generated practice
    assert sol["interactive"]["product"]["phase"] == "l"        # the interactive product is water
    assert sol["practice"]["family"] == "acid_base_limiting_reagent_v1"


def test_gas_stoichiometry_lesson():
    """The Phase-2 gas-stoichiometry flagship (ADR-0041): a weighed metal + acid; the ledger fixes the moles of
    H2 and PV=nRT fixes its VOLUME. First lesson with a MASS given (g→mol) and a gas result block."""
    from decimal import Decimal
    from fractions import Fraction

    sol, out_rel = build_problem(SPEC_GAS, ROOT)
    assert out_rel == "gas-stoichiometry/zinc-hydrochloric-hydrogen.solution.json"

    # the weighed-mass given: 3.269 g Zn ÷ 65.38 g/mol = 0.0500 mol (exact, terminating)
    zn_given = next(g for g in sol["given"] if g["species"] == "Zn(s)")
    assert zn_given["mass_g"] == "3.269" and zn_given["moles"] == "0.05" and "volume_mL" not in zn_given
    zn_chain = next(c for c in sol["dimensional_analysis"] if c["target"] == "moles of Zn(s)")
    assert zn_chain["steps"][0]["unit"] == "g" and zn_chain["steps"][-1]["value"] == "0.05"

    # the ledger: Zn limits (0.0500 < 0.0600 capacity), HCl left over 0.0200 mol
    assert sol["ledger"]["limiting"] == ["Zn"] and sol["ledger"]["extent_mol"] == "0.05"
    assert sol["result"]["leftover"] == [{"species": "HCl", "moles": "0.02"}]
    assert sol["equations"]["net_ionic"]["text"] == "Zn + 2 H^+ -> Zn^2+ + H2"
    assert sol["equations"]["spectators"] == ["Cl^-"]

    # the reported product is the collected gas H2 (phase g); the dissolved salt is ZnCl2
    assert "precipitate" not in sol["result"]
    assert sol["result"]["product"]["species"] == "H2" and sol["result"]["product"]["phase"] == "g"
    assert sol["result"]["salt"]["species"] == "ZnCl2"

    # the gas block: moles ledger-exact; volume model-exact (PV=nRT), reported to 3 sig figs
    gas = sol["result"]["gas"]
    assert gas["species"] == "H2" and gas["moles"] == "0.05"
    assert gas["pressure_atm"] == "1.00" and gas["temperature_C"] == "25.00" and gas["temperature_K"] == "298.15"
    assert gas["volume_L_display"] == "1.22" and gas["volume_L"] == "1.223"
    assert gas["molar_volume_L_per_mol_display"] == "24.5"    # RT/P here, NOT 22.4 (the STP-only value)
    # re-derive V = nRT/P exactly and confirm the emitted value rounds to it
    R = Decimal(gas["gas_constant"])
    V = Decimal(gas["moles"]) * R * Decimal(gas["temperature_K"]) / Decimal(gas["pressure_atm"])
    assert abs(V - Decimal(gas["volume_L"])) < Decimal("0.001")

    # honesty layering: ledger-exact + model-exact regimes; the gas constant is sourced; no solubility claim
    assert [r["regime"] for r in sol["regimes"]] == ["ledger-exact", "model-exact"]
    assert sol["provenance"]["sources"]["constants"] == "bipm-si-2019"
    assert "solubility" not in sol["provenance"]["sources"] and "solubility_basis" not in sol
    # a gas lesson is not the double-displacement shape → no cation/anion interactive block
    assert "interactive" not in sol

    # gas-stoichiometry practice (ADR-0041): free-entry volume/leftover + categorical limiting, re-derived by
    # check-parity from the reaction constants that travel with the set (no interactive block)
    prac = sol["practice"]
    assert prac["family"] == "gas_stoichiometry_v1"
    assert prac["gas"]["metal_id"] == "Zn" and prac["gas"]["gas_constant"] == "0.0820573660809596"
    assert prac["gas"]["metal_coeff"] == 1 and prac["gas"]["acid_coeff"] == 2
    kinds = {q["kind"] for q in prac["questions"]}
    assert kinds == {"volume", "limiting", "leftover"}          # all three question kinds present
    limits = {q["answer"]["value"] for q in prac["questions"] if q["kind"] == "limiting"}
    assert limits == {"Zn", "HCl"}                               # the limiting reagent genuinely switches
    for q in prac["questions"]:
        assert q["mode"] == ("choice" if q["kind"] == "limiting" else "numeric")
        assert ("choices" in q) == (q["kind"] == "limiting")    # numeric is free entry, not a menu (ADR-0032)


def test_gas_practice_is_deterministic():
    """The gas practice must be byte-stable across builds (committed derived/, ADR-0008)."""
    a, _ = build_problem(SPEC_GAS, ROOT)
    b, _ = build_problem(SPEC_GAS, ROOT)
    assert a["practice"] == b["practice"]


def test_energy_ledger_lesson():
    """The Phase-2 energy-ledger flagship (ADR-0043): reaction enthalpy attached to extent. The ledger fixes ξ,
    ΔH_rxn is Hess's law over sourced ΔH_f°, and the heat is q = ΔH_rxn·ξ. First fully MOLECULAR lesson (no
    ionic equation) and first with an `energy` result headline (no product mass)."""
    from decimal import Decimal

    sol, out_rel = build_problem(SPEC_ENERGY, ROOT)
    assert out_rel == "thermochemistry/methane-combustion-enthalpy.solution.json"

    # both reactants weighed (g→mol); CH4 limits (0.05 < 0.06 capacity), O2 left over 0.02 mol
    assert sol["ledger"]["limiting"] == ["CH4"] and sol["ledger"]["extent_mol"] == "0.05"
    assert sol["result"]["leftover"] == [{"species": "O2", "moles": "0.02"}]

    # fully molecular: ONLY the molecular equation (no ions in solution → no ionic equation, ADR-0043)
    assert set(sol["equations"]) == {"molecular"}
    assert sol["equations"]["molecular"]["text"] == "CH4(g) + 2 O2(g) -> CO2(g) + 2 H2O(l)"

    # the headline is ENERGY — no precipitate/product/gas mass
    assert not ({"precipitate", "product", "gas"} & set(sol["result"]))
    e = sol["result"]["energy"]
    assert e["classification"] == "exothermic" and e["extent_mol"] == "0.05"
    assert e["source"] == "openstax-chemistry-2e"

    # Hess's law: ΔH_rxn = Σ (±coeff·ΔH_f°) — re-derive from the emitted breakdown
    total = Decimal(0)
    for h in e["hess"]:
        sign = 1 if h["role"] == "product" else -1
        contribution = sign * h["coeff"] * Decimal(h["delta_h_f_kj_per_mol"])
        assert Decimal(h["contribution_kj_per_mol"]) == contribution
        total += contribution
    assert total == Decimal("-890.57") == Decimal(e["delta_h_rxn_kj_per_mol"])
    # the free element O2 contributes exactly 0 (its ΔH_f° is 0 by definition — the reference level)
    o2 = next(h for h in e["hess"] if h["species"] == "O2")
    assert o2["is_element"] is True and o2["contribution_kj_per_mol"] == "0"

    # q = ΔH_rxn·ξ (EXACT here — all inputs terminate, unlike the gas volume's non-terminating R), 3-sf display
    q = total * Decimal(e["extent_mol"])
    assert Decimal(e["q_kj"]) == q == Decimal("-44.5285")
    assert e["q_kj_display"] == "-44.5"

    # the energy dimensional chain: extent ξ (mol) → heat q (kJ)
    echain = next(c for c in sol["dimensional_analysis"] if "ΔH_rxn" in c["target"])
    assert echain["steps"][0]["unit"] == "mol" and echain["steps"][-1]["unit"] == "kJ"

    # honesty: ledger-exact + model-exact regimes; ΔH_f° source cited; a molecular shape has no slider interactive
    assert [r["regime"] for r in sol["regimes"]] == ["ledger-exact", "model-exact"]
    assert sol["provenance"]["sources"]["formation_enthalpies"] == "openstax-chemistry-2e"
    assert "solubility" not in sol["provenance"]["sources"] and "constants" not in sol["provenance"]["sources"]
    assert "interactive" not in sol   # the molecular shape has no cation/anion slider interactive


def test_energy_practice():
    """The energy-ledger lesson's generated practice (ADR-0043): vary the two reactant masses → the heat
    q=ΔH_rxn·ξ (free entry) + leftover (free entry) + limiting (categorical), re-derived by check-parity from
    the `energetics` reaction constants with no interactive block."""
    from decimal import Decimal

    sol, _ = build_problem(SPEC_ENERGY, ROOT)
    prac = sol["practice"]
    assert prac["family"] == "energy_ledger_v1"
    e = prac["energetics"]
    assert e["reactant_a_id"] == "CH4" and e["reactant_b_id"] == "O2"
    assert e["reactant_a_coeff"] == 1 and e["reactant_b_coeff"] == 2
    assert e["delta_h_rxn_kj_per_mol"] == "-890.57"

    kinds = {q["kind"] for q in prac["questions"]}
    assert kinds == {"heat", "limiting", "leftover"}                 # all three kinds present
    limits = {q["answer"]["value"] for q in prac["questions"] if q["kind"] == "limiting"}
    assert limits == {"CH4", "O2"}                                   # the limiting reagent genuinely switches
    for q in prac["questions"]:
        assert q["mode"] == ("choice" if q["kind"] == "limiting" else "numeric")
        assert ("choices" in q) == (q["kind"] == "limiting")         # numeric is free entry, not a menu (ADR-0032)
        assert ("diagnostics" in q) == (q["kind"] != "limiting")

    # a heat answer must reproduce q = ΔH_rxn·ξ from its emitted args (mass → mol → capacity → ξ)
    dH = Decimal(e["delta_h_rxn_kj_per_mol"])
    Ma, Mb = Decimal(e["reactant_a_molar_mass"]), Decimal(e["reactant_b_molar_mass"])
    for q in prac["questions"]:
        if q["kind"] != "heat":
            continue
        na = Decimal(q["args"]["mass_a_g"]) / Ma
        nb = Decimal(q["args"]["mass_b_g"]) / Mb
        xi = min(na / e["reactant_a_coeff"], nb / e["reactant_b_coeff"])
        assert abs(dH * xi - Decimal(q["answer"]["value"])) < Decimal("0.05")   # within the 4-sf display


def test_energy_practice_is_deterministic():
    """The energy practice must be byte-stable across builds (committed derived/, ADR-0008)."""
    a, _ = build_problem(SPEC_ENERGY, ROOT)
    b, _ = build_problem(SPEC_ENERGY, ROOT)
    assert a["practice"] == b["practice"]


def test_neutralization_has_no_percent_yield_support(tmp_path):
    """Percent yield is a gravimetric-precipitation concept — a neutralization (no solid) refuses it (ADR-0037)."""
    import pytest
    from chemkernel import BuildError

    text = SPEC_NEUTRAL.read_text(encoding="utf-8")
    text += '\n[yield]\nactual_mass_g = "0.02"\n'
    tmp = tmp_path / "neutral-yield.problem.toml"
    tmp.write_text(text, encoding="utf-8")
    with pytest.raises(BuildError, match="solid precipitate"):
        build_problem(tmp, ROOT)


def test_percent_yield_refuses_superphysical_actual(tmp_path):
    """Refuse a yield above 100% — you cannot collect more than the theoretical maximum (ADR-0008)."""
    import pytest
    from chemkernel import BuildError

    text = SPEC_YIELD.read_text(encoding="utf-8").replace('actual_mass_g = "0.276"', 'actual_mass_g = "9.9"')
    tmp = tmp_path / "superphysical.problem.toml"
    tmp.write_text(text, encoding="utf-8")
    with pytest.raises(BuildError):
        build_problem(tmp, ROOT)


def test_build_is_deterministic_across_hash_seeds():
    # committed derived/ must be byte-stable (ADR-0008). PYTHONHASHSEED varies set/dict iteration ACROSS
    # processes, so build the spec under several seeds in subprocesses and require identical output.
    prog = (
        "import json,sys;from pathlib import Path;from chemkernel.build import build_problem;"
        "s,_=build_problem(Path(sys.argv[1]),Path(sys.argv[2]));"
        "sys.stdout.write(json.dumps(s,ensure_ascii=False,sort_keys=False))"
    )

    def run(seed: int) -> str:
        # PYTHONIOENCODING=utf-8 so the subprocess stdout matches how build.py actually writes the artifact
        # (_write_json uses utf-8, ensure_ascii=False); Windows' default cp1252 stdout can't encode ξ etc.
        env = dict(os.environ, PYTHONHASHSEED=str(seed), PYTHONIOENCODING="utf-8")
        r = subprocess.run([sys.executable, "-c", prog, str(SPEC), str(ROOT)],
                           capture_output=True, text=True, encoding="utf-8", env=env)
        assert r.returncode == 0, r.stderr
        return r.stdout

    outputs = {run(seed) for seed in (0, 1, 42, 12345)}
    assert len(outputs) == 1, "build output varies with PYTHONHASHSEED — non-deterministic ordering"
