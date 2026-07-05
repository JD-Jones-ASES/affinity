"""End-to-end build: the authored Phase-0 spec through build_problem, key fields hand-checked."""

import os
import subprocess
import sys
from pathlib import Path

from chemkernel.build import build_problem

ROOT = Path(__file__).resolve().parents[2]
SPEC = ROOT / "problems" / "precipitation" / "calcium-carbonate-limiting.problem.toml"
SPEC_YIELD = ROOT / "problems" / "percent-yield" / "zinc-carbonate-percent-yield.problem.toml"


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
