"""Orchestration: read an authored TOML spec, run the engine, write verified derived JSON (ADR-0019).

Entry point (pyproject.toml):
  build-problems   problems/**/*.problem.toml -> derived/<topic>/<slug>.solution.json

The producer REFUSES TO EMIT on any failure — an unbalanceable equation, non-conserved charge, a negative
extent, a phase that contradicts the solubility ruleset — because the underlying engine raises BuildError
(ADR-0008). Schema conformance and the honesty cross-checks are then re-enforced by the Node gates over the
committed output. Exact values are emitted as decimal strings (ADR-0013); a non-terminating amount is a
build failure rather than a silently rounded number.
"""

from __future__ import annotations

import json
import platform
import re
import sys
import tomllib
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

from . import BuildError, __version__
from .balance import balance
from .data import ChemData
from .extent import solve_extent, species_mass_g, to_decimal
from .formula import Formula, parse_formula
from .gym import generate_gym
from .interactive import build_interactive
from .practice import generate_practice
from .reaction import complete_ionic, net_ionic
from .reference import build_reference_entry, build_valence_table
from .solubility import Solubility
from .units import Quantity

_REGIME_NAME = {"ledger": "ledger-exact", "solubility": "rule-sourced", "solution_behavior": "model-exact"}
_PHASE_SUFFIX = re.compile(r"\((?:s|l|g|aq)\)$")


def _core(species_id: str) -> str:
    return _PHASE_SUFFIX.sub("", species_id)


def _write_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(obj, indent=2, ensure_ascii=False, allow_nan=False)
    # newline="\n": emit LF even on Windows so committed derived/ stays byte-stable (.gitattributes, ADR-0008)
    path.write_text(text + "\n", encoding="utf-8", newline="\n")


def _exact_decimal_str(value) -> str:
    """Exact decimal string for a Fraction/Decimal/int; BuildError if it does not terminate (ADR-0013)."""
    f = value if isinstance(value, Fraction) else Fraction(value if not isinstance(value, str) else Decimal(value))
    den = f.denominator
    while den % 2 == 0:
        den //= 2
    while den % 5 == 0:
        den //= 5
    if den != 1:
        raise BuildError(f"amount {f} is not a terminating decimal — refusing to emit a rounded exact value")
    return format(Decimal(f.numerator) / Decimal(f.denominator), "f")


def _species_latex(species_id: str) -> str:
    return parse_formula(species_id).latex


def _molecular_text(species: list[str], coeffs: list[int]) -> str:
    return " + ".join((f"{c} " if c != 1 else "") + s for s, c in zip(species, coeffs))


def _molecular_latex(species: list[Formula], coeffs: list[int]) -> str:
    return " + ".join((f"{c}\\," if c != 1 else "") + f.latex for f, c in zip(species, coeffs))


def _ionic_text(terms) -> str:
    return " + ".join((f"{c} " if c != 1 else "") + sid for sid, c, _ch, _ph in terms)


def _ionic_latex(terms) -> str:
    return " + ".join((f"{c}\\," if c != 1 else "") + _species_latex(sid) for sid, c, _ch, _ph in terms)


def _net_text(side: dict) -> str:
    return " + ".join((f"{c} " if c != 1 else "") + sid for (sid, _ph), c in side.items())


def _net_latex(side: dict) -> str:
    return " + ".join((f"{c}\\," if c != 1 else "") + _species_latex(sid) for (sid, _ph), c in side.items())


def _moles_and_chain(given: dict, ctx: str) -> tuple[Fraction, list[dict]]:
    vol = Quantity.of(Decimal(given["volume_mL"]), "mL")
    conc = Quantity.of(Decimal(given["molarity_M"]), "M")
    n = vol.to("L") * conc
    steps = [
        {"value": str(vol.value), "unit": "mL", "note": "given volume"},
        {"value": str(vol.to("L").value), "unit": "L", "note": "convert mL to L (÷ 1000)"},
        {"value": _exact_decimal_str(Fraction(n.value)), "unit": "mol",
         "note": f"× {given['molarity_M']} mol/L"},
    ]
    return Fraction(n.value), steps


def build_problem(path: Path, root: Path) -> tuple[dict, str]:
    spec = tomllib.loads(path.read_text(encoding="utf-8"))
    ctx = spec.get("id", path.stem)
    data = ChemData.load(root)
    solub = Solubility.load(root)

    reactants = [parse_formula(s, ctx) for s in spec["reactants"]]
    products = [parse_formula(s, ctx) for s in spec["products"]]
    coeffs = balance(reactants, products, ctx)

    # initial moles + dimensional-analysis chains from the givens
    given_moles: dict[str, Fraction] = {}
    dimensional = []
    given_out = []
    for g in spec["given"]:
        n, steps = _moles_and_chain(g, ctx)
        given_moles[g["species"]] = n
        dimensional.append({"target": f"moles of {g['species']}", "steps": steps})
        given_out.append({"species": g["species"], "volume_mL": g["volume_mL"],
                          "molarity_M": g["molarity_M"], "moles": _exact_decimal_str(n)})

    # phase consistency vs. the solubility ruleset (raises on mismatch); capture the precipitate's basis
    solubility_basis = None
    for f in reactants + products:
        try:
            verdict = solub.verify_phase(f, data, ctx)
        except BuildError:
            if f.charge == 0 and f.phase in ("aq", "s"):
                raise
            continue
        if f.phase == "s" and not verdict.soluble:
            solubility_basis = {"species": _core(f.raw), "soluble": False, "rule_id": verdict.rule_id,
                                "statement": verdict.statement, "source": solub.source}

    # the species ledger (molecular level — carries molar mass and the numeric answers)
    react_pairs = [(f, given_moles[f.raw]) for f in reactants]
    prod_pairs = [(f, 0) for f in products]
    ledger = solve_extent(react_pairs, prod_pairs, coeffs, ctx)

    ledger_species = []
    for r in ledger.rows:
        core = _core(r.species)
        ledger_species.append({
            "id": core, "latex": _species_latex(core), "phase": r.phase, "charge": r.charge,
            "nu": r.nu, "initial_mol": _exact_decimal_str(r.initial_mol),
            "final_mol": _exact_decimal_str(r.final_mol), "role": r.role,
        })

    # ionic equations
    left, right = complete_ionic(reactants, products, coeffs, data, ctx)
    net_left, net_right, spectators = net_ionic(left, right, ctx)

    # result: precipitate + leftovers
    precipitate_row = next((r for r in ledger.rows if r.phase == "s" and r.role == "product"), None)
    if precipitate_row is None:
        raise BuildError(f"{ctx}: no solid product to report as a precipitate")
    mass = species_mass_g(precipitate_row, data)
    leftovers = [{"species": _core(r.species), "moles": _exact_decimal_str(r.final_mol)}
                 for r in ledger.rows if r.nu < 0 and r.final_mol > 0]

    solution = {
        "id": spec["id"],
        "title": spec["title"],
        "slug": spec["slug"],
        "topic": spec["topic"],
        "tags": spec.get("tags", []),
        "scenario": spec["scenario"],
        "regimes": [{"facet": k, "regime": _REGIME_NAME[k]} for k in spec.get("regimes", list(_REGIME_NAME))],
        "assumptions": spec.get("assumptions", []),
        "given": given_out,
        "equations": {
            "molecular": {"text": _molecular_text(spec["reactants"], coeffs[:len(reactants)])
                          + " -> " + _molecular_text(spec["products"], coeffs[len(reactants):]),
                          "latex": _molecular_latex(reactants, coeffs[:len(reactants)])
                          + r" \rightarrow " + _molecular_latex(products, coeffs[len(reactants):])},
            "complete_ionic": {"text": _ionic_text(left) + " -> " + _ionic_text(right),
                               "latex": _ionic_latex(left) + r" \rightarrow " + _ionic_latex(right)},
            "net_ionic": {"text": _net_text(net_left) + " -> " + _net_text(net_right),
                          "latex": _net_latex(net_left) + r" \rightarrow " + _net_latex(net_right)},
            "spectators": spectators,
        },
        "ledger": {
            "extent_symbol": "xi",
            "extent_mol": _exact_decimal_str(ledger.extent_mol),
            "limiting": [_core(x) for x in ledger.limiting],
            "species": ledger_species,
        },
        "dimensional_analysis": dimensional,
        "result": {
            "precipitate": {
                "species": _core(precipitate_row.species),
                "phase": precipitate_row.phase,
                "molar_mass_g_per_mol": str(data.molar_mass(precipitate_row.species)),
                "moles": _exact_decimal_str(precipitate_row.final_mol),
                "mass_g": _exact_decimal_str(mass),
                "mass_g_display": str(to_decimal(mass, 3)),
            },
            "limiting_species": [_core(x) for x in ledger.limiting],
            "leftover": leftovers,
        },
        "misconception": spec["misconception"],
        "visualizations": spec.get("visualizations", []),
        "reference_links": spec.get("reference_links", []),
        "checks": {"atom_balance": True, "charge_balance": True, "unit_check": True, "extent_nonnegative": True},
        "provenance": {
            "producer": "chemkernel",
            "version": __version__,
            "python": platform.python_version(),
            "author": spec.get("author", "Affinity"),
            "created": spec.get("created", ""),
            "sources": {
                "atomic_weight": data.sources.get("atomic_weight", ""),
                "ion_charge": data.sources.get("ion_charge", ""),
                "solubility": solub.source,
            },
        },
    }
    if solubility_basis is not None:
        solution["solubility_basis"] = solubility_basis

    # percent yield (ADR-0029): the theoretical yield IS the precipitate mass — the ledger at maximum extent.
    # The authored actual (measured) yield gives percent = actual ÷ theoretical × 100. Refuse a nonphysical
    # yield: actual must be positive and no greater than theoretical (you cannot collect more than forms —
    # that would break conservation of mass). Percent is a measured ratio, reported at 3 sig figs (ADR-0025).
    yield_spec = spec.get("yield")
    if yield_spec is not None:
        theoretical = mass
        actual = Fraction(Decimal(str(yield_spec["actual_mass_g"])))
        if not (0 < actual <= theoretical):
            raise BuildError(f"{ctx}: actual yield {actual} g must be > 0 and ≤ theoretical {theoretical} g")
        percent = actual / theoretical * 100
        solution["result"]["percent_yield"] = {
            "theoretical_mass_g": _exact_decimal_str(theoretical),
            "theoretical_display": str(to_decimal(theoretical, 3)),
            "actual_mass_g": _exact_decimal_str(actual),
            "actual_display": str(to_decimal(actual, 3)),
            "percent_display": str(to_decimal(percent, 1)),   # a percent, reported to 0.1% (ADR-0025)
        }

    # the interactive block: parity-verified closed forms for the sliders (ADR-0011). Optional — emitted only
    # for the supported single-precipitate double-displacement shape; the schema allows its absence.
    interactive = build_interactive(reactants, products, coeffs, spec["given"], data, net_left, net_right, ctx)
    if interactive is not None:
        solution["interactive"] = interactive

    # generated practice (ADR-0011, brief §6.8): deterministic solver-verified variants off the same reaction.
    # Optional; needs the interactive block (shares its engine-derived multiplicities). Refuses to emit fewer
    # than the requested count (a build failure beats silently short-changing practice).
    practice_spec = spec.get("practice")
    if practice_spec and interactive is not None:
        practice = generate_practice(interactive, int(practice_spec["seed"]),
                                     int(practice_spec.get("count", 4)), ctx)
        if practice is None:
            raise BuildError(f"{ctx}: practice generator could not produce {practice_spec.get('count', 4)} "
                             f"non-rejected variants at seed {practice_spec['seed']}")
        solution["practice"] = practice

    return solution, f"{spec['topic']}/{spec['slug']}.solution.json"


def build_reference_main(argv: list[str] | None = None) -> int:
    """Build the Chemical Atlas: the Valence Table (from data/) + authored concept entries (reference/**)."""
    root = Path.cwd()
    data = ChemData.load(root)

    try:
        table = build_valence_table(data)
    except BuildError as e:
        print(f"BUILD FAILED — {e}", file=sys.stderr)
        return 1
    _write_json(root / "derived" / "reference" / "valence-table.json", table)
    print(f"  built valence-table -> derived/reference/valence-table.json")

    ids = {table["id"]}
    for path in sorted((root / "reference").glob("**/*.toml")):
        spec = tomllib.loads(path.read_text(encoding="utf-8"))
        ctx = spec.get("id", path.stem)
        try:
            entry = build_reference_entry(spec, ctx)
        except BuildError as e:
            print(f"BUILD FAILED — {e}", file=sys.stderr)
            return 1
        if entry["id"] in ids:
            print(f"BUILD FAILED — duplicate reference id {entry['id']}", file=sys.stderr)
            return 1
        ids.add(entry["id"])
        _write_json(root / "derived" / "reference" / f"{entry['id']}.json", entry)
        print(f"  built {path.relative_to(root).as_posix()} -> derived/reference/{entry['id']}.json")
    return 0


def build_gyms_main(argv: list[str] | None = None) -> int:
    """Build the procedural gyms: gyms/**/*.gym.toml -> derived/gyms/<slug>.gym.json (Phase 1, ADR-0024)."""
    root = Path.cwd()
    data = ChemData.load(root)
    specs = sorted((root / "gyms").glob("**/*.gym.toml"))
    if not specs:
        print("no *.gym.toml found under gyms/", file=sys.stderr)
        return 1
    ids: set[str] = set()
    for path in specs:
        spec = tomllib.loads(path.read_text(encoding="utf-8"))
        ctx = spec.get("id", path.stem)
        try:
            gym = generate_gym(spec, data, ctx)
        except BuildError as e:
            print(f"BUILD FAILED — {e}", file=sys.stderr)
            return 1
        if gym["id"] in ids:
            print(f"BUILD FAILED — duplicate gym id {gym['id']}", file=sys.stderr)
            return 1
        ids.add(gym["id"])
        out_rel = f"gyms/{gym['slug']}.gym.json"
        _write_json(root / "derived" / out_rel, gym)
        print(f"  built {path.relative_to(root).as_posix()} -> derived/{out_rel}")
    return 0


def build_problems_main(argv: list[str] | None = None) -> int:
    root = Path.cwd()
    problems = sorted((root / "problems").glob("**/*.problem.toml"))
    if not problems:
        print("no *.problem.toml found under problems/", file=sys.stderr)
        return 1
    for path in problems:
        try:
            solution, out_rel = build_problem(path, root)
        except BuildError as e:
            print(f"BUILD FAILED — {e}", file=sys.stderr)
            return 1
        _write_json(root / "derived" / out_rel, solution)
        print(f"  built {path.relative_to(root).as_posix()} -> derived/{out_rel}")
    return 0
