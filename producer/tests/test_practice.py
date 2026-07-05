"""Generated practice: solver-verified variants, misconception distractors, determinism (brief §6.8)."""

import tomllib
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

from chemkernel.balance import balance
from chemkernel.build import build_problem
from chemkernel.data import ChemData
from chemkernel.formula import parse_formula
from chemkernel.interactive import build_interactive
from chemkernel.practice import generate_practice
from chemkernel.reaction import complete_ionic, net_ionic

ROOT = Path(__file__).resolve().parents[2]
SPEC = ROOT / "problems" / "precipitation" / "calcium-carbonate-limiting.problem.toml"


def _interactive():
    spec = tomllib.loads(SPEC.read_text(encoding="utf-8"))
    data = ChemData.load(ROOT)
    reactants = [parse_formula(s) for s in spec["reactants"]]
    products = [parse_formula(s) for s in spec["products"]]
    coeffs = balance(reactants, products)
    left, right = complete_ionic(reactants, products, coeffs, data)
    net_left, net_right, _ = net_ionic(left, right)
    return build_interactive(reactants, products, coeffs, spec["given"], data, net_left, net_right)


def test_generates_requested_count_and_shape():
    p = generate_practice(_interactive(), seed=20260705, count=6)
    assert p is not None
    assert p["family"] == "precipitation_limiting_reagent_v1"
    assert len(p["questions"]) == 6
    for q in p["questions"]:
        assert q["kind"] in ("limiting", "mass", "leftover")
        assert sum(1 for c in q["choices"] if c["correct"]) == 1          # exactly one correct
        assert len({c["display"] for c in q["choices"]}) == len(q["choices"])  # distinct displays
        correct = next(c for c in q["choices"] if c["correct"])
        assert correct["display"] == q["answer"]["display"]
        for c in q["choices"]:                                            # every wrong choice names a misconception
            assert c["correct"] or c["misconception"]
        assert set(q["args"]) == {"v1", "c1", "v2", "c2"}


def test_answers_are_solver_correct():
    ix = _interactive()
    p = generate_practice(ix, seed=20260705, count=6)
    M = Fraction(Decimal(ix["product"]["molar_mass"]))
    for q in p["questions"]:
        a = q["args"]
        n_cat = Fraction(Decimal(a["v1"])) / 1000 * Fraction(Decimal(a["c1"]))
        n_an = Fraction(Decimal(a["v2"])) / 1000 * Fraction(Decimal(a["c2"]))
        xi = min(n_cat, n_an)
        tol = Fraction(1, 1000)
        if q["kind"] == "limiting":
            want = ix["cation"]["source"] if n_cat < n_an else ix["anion"]["source"]
            assert q["answer"]["value"] == want
        elif q["kind"] == "mass":
            assert abs(Fraction(Decimal(q["answer"]["value"])) - xi * M) <= tol
        else:  # leftover, in mmol
            left = (n_an - xi) if n_cat < n_an else (n_cat - xi)
            assert abs(Fraction(Decimal(q["answer"]["value"])) - left * 1000) <= tol


def test_deterministic_same_seed():
    a = generate_practice(_interactive(), seed=20260705, count=6)
    b = generate_practice(_interactive(), seed=20260705, count=6)
    assert a == b                       # byte-identical for a given seed (ADR-0008)
    c = generate_practice(_interactive(), seed=1, count=6)
    assert c["questions"] != a["questions"]   # a different seed gives different variants


def test_included_in_full_build():
    sol, _ = build_problem(SPEC, ROOT)
    assert "practice" in sol
    assert sol["practice"]["seed"] == 20260705
    assert len(sol["practice"]["questions"]) == 6
