"""End-to-end build: the authored Phase-0 spec through build_problem, key fields hand-checked."""

from pathlib import Path

from chemkernel.build import build_problem

ROOT = Path(__file__).resolve().parents[2]
SPEC = ROOT / "problems" / "precipitation" / "calcium-carbonate-limiting.problem.toml"


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
