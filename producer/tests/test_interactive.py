"""The interactive block: parity-verified closed forms + engine-computed samples (ADR-0011, ADR-0008).

The closed-form STRINGS the browser will evaluate are re-evaluated here in Python (Math.min -> min) and must
reproduce the engine-computed sample expectations — the same guarantee check-parity.mjs gives in Node, pinned
at producer-test time too.
"""

import tomllib
from pathlib import Path

from chemkernel.balance import balance
from chemkernel.build import build_problem
from chemkernel.data import ChemData
from chemkernel.formula import parse_formula
from chemkernel.interactive import build_interactive
from chemkernel.reaction import complete_ionic, net_ionic

ROOT = Path(__file__).resolve().parents[2]
SPEC = ROOT / "problems" / "precipitation" / "calcium-carbonate-limiting.problem.toml"
SPEC_NEUTRAL = ROOT / "problems" / "neutralization" / "hydrochloric-sodium-hydroxide.problem.toml"

CF_KEYS = {"n_cation", "n_anion", "xi", "mass", "leftover_cation", "leftover_anion",
           "n_spec_cation", "n_spec_anion"}


def _interactive(spec_path=SPEC):
    spec = tomllib.loads(spec_path.read_text(encoding="utf-8"))
    data = ChemData.load(ROOT)
    reactants = [parse_formula(s) for s in spec["reactants"]]
    products = [parse_formula(s) for s in spec["products"]]
    coeffs = balance(reactants, products)
    left, right = complete_ionic(reactants, products, coeffs, data)
    net_left, net_right, _ = net_ionic(left, right)
    return build_interactive(reactants, products, coeffs, spec["given"], data, net_left, net_right)


def _eval(expr: str, args: dict) -> float:
    # evaluate a JS-style closed form in Python; the strings are our own generated output (test-only eval)
    py = expr.replace("Math.min", "min")
    return eval(py, {"min": min}, {k: float(v) for k, v in args.items()})


def test_interactive_present_and_shaped():
    ix = _interactive()
    assert ix is not None
    assert [p["name"] for p in ix["params"]] == ["v1", "c1", "v2", "c2"]
    assert ix["cation"] == {"id": "Ca^2+", "source": "CaCl2", "per": 1, "net_coeff": 1}
    assert ix["anion"] == {"id": "CO3^2-", "source": "Na2CO3", "per": 1, "net_coeff": 1}
    assert ix["product"]["id"] == "CaCO3" and ix["product"]["molar_mass"] == "100.086"
    assert {s["id"]: s["per"] for s in ix["spectators"]} == {"Cl^-": 2, "Na^+": 2}
    assert set(ix["closed_form"]) == CF_KEYS


def test_closed_forms_reproduce_engine_samples():
    ix = _interactive()
    assert len(ix["samples"]) == 10
    for s in ix["samples"]:
        assert set(s["expect"]) == CF_KEYS
        for name, expr in ix["closed_form"].items():
            got = _eval(expr, s["args"])
            want = float(s["expect"][name])
            assert abs(got - want) <= 1e-9 + 1e-9 * abs(want), f"{name} @ {s['args']}: {got} vs {want}"


def test_default_and_switch_samples():
    ix = _interactive()
    default = ix["samples"][0]
    assert default["args"] == {"v1": "25.0", "c1": "0.100", "v2": "20.0", "c2": "0.150"}
    assert default["expect"]["xi"] == "0.0025"        # matches committed extent_mol
    assert default["expect"]["mass"] == "0.250215"    # matches committed precipitate mass_g
    assert default["expect"]["leftover_anion"] == "0.0005" and default["expect"]["leftover_cation"] == "0"

    # a richer cation solution flips the limiting reagent to the anion (the switch the slider reveals)
    flip = next(s for s in ix["samples"] if s["args"]["c1"] == "0.150" and s["args"]["v1"] == "25.0")
    assert flip["expect"]["leftover_cation"] != "0"   # cation now in excess
    assert flip["expect"]["leftover_anion"] == "0"    # anion limits


def test_interactive_included_in_full_build():
    sol, _ = build_problem(SPEC, ROOT)
    assert "interactive" in sol
    assert sol["interactive"]["closed_form"]["xi"] == "Math.min(v1/1000*c1, v2/1000*c2)"


def test_neutralization_interactive_is_water_product():
    """The generalized interactive (ADR-0037): for a neutralization the net-ionic product is WATER (phase l),
    the reacting ions are H+ / OH-, and the salt ions are the spectators — all engine-derived, not assumed."""
    ix = _interactive(SPEC_NEUTRAL)
    assert ix is not None
    assert ix["product"]["id"] == "H2O" and ix["product"]["phase"] == "l"
    assert ix["cation"]["id"] == "H^+" and ix["cation"]["source"] == "HCl"
    assert ix["anion"]["id"] == "OH^-" and ix["anion"]["source"] == "NaOH"
    assert {s["id"] for s in ix["spectators"]} == {"Cl^-", "Na^+"}   # the salt, sitting out
    # the closed forms still reproduce the engine at every sample (parity holds for a water product too)
    for s in ix["samples"]:
        for name, expr in ix["closed_form"].items():
            got = _eval(expr, s["args"])
            assert abs(got - float(s["expect"][name])) <= 1e-9 + 1e-9 * abs(float(s["expect"][name]))
