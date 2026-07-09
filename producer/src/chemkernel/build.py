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
from decimal import ROUND_HALF_UP, Decimal, localcontext
from fractions import Fraction
from pathlib import Path

from . import BuildError, __version__
from .balance import balance
from .data import ChemData
from .equilibrium import (build_buffer_lesson, build_equilibrium_lesson, build_polyprotic_lesson,
                          build_prediction_lesson, build_solubility_lesson, build_titration_lesson,
                          build_weak_base_lesson)
from .kinetics import build_kinetics_lesson
from .redox import build_electrochemistry_lesson
from .extent import solve_extent, species_mass_g, to_decimal
from .formula import Formula, parse_formula
from .gym import generate_gym
from .interactive import build_interactive
from .practice import generate_energy_practice, generate_gas_practice, generate_practice
from .reaction import complete_ionic, net_ionic
from .reactivity import AcidBase, Decomposition
from .reference import (build_formula_entry, build_reaction_family, build_reference_entry,
                        build_species_entry, build_valence_table)
from .solubility import Solubility
from .structure import build_comparison_lesson, build_molecule_entry, build_structure_lesson
from .units import Quantity

_REGIME_NAME = {"ledger": "ledger-exact", "solubility": "rule-sourced",
                "solution_behavior": "model-exact", "gas_behavior": "model-exact",
                "thermochemistry": "model-exact"}
# the default facet set when a spec omits `regimes` — the original three (pin it explicitly so adding a new
# facet key above never shifts an existing lesson's emitted regimes, keeping committed derived/ byte-stable).
_DEFAULT_REGIMES = ["ledger", "solubility", "solution_behavior"]
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


def _sigfig(d: Decimal, digits: int) -> str:
    """Round a Decimal to `digits` significant figures, fixed notation, trailing zeros trimmed. DISPLAY only:
    a gas volume computed through PV=nRT is model-exact-then-rounded (ADR-0040) — the ideal-gas answer is a
    rounded physical quantity, distinct from the exact terminating ledger amounts (ADR-0013). Mirrors the
    gas-laws gym's `_sigdec`."""
    if d == 0:
        return "0"
    with localcontext() as c:
        c.prec = digits
        c.rounding = ROUND_HALF_UP
        s = format(+d, "f")
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s or "0"


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


def _moles_and_chain(given: dict, data, ctx: str) -> tuple[Fraction, list[dict]]:
    """Initial moles of a given reactant + its dimensional-analysis chain. Two given shapes (ADR-0041):
    a **solution** (volume + molarity → moles) or a weighed **mass** (grams ÷ molar mass → moles). Both run
    through the units engine so the dimensions are certified; both must land on a terminating decimal (ADR-0013,
    the ledger-exactness guard) or the build fails."""
    if "mass_g" in given:
        mass = Quantity.of(Decimal(given["mass_g"]), "g")
        molar_mass = data.molar_mass(_core(given["species"]))
        n = mass / Quantity.of(molar_mass, "g/mol")   # g ÷ g/mol → mol (dimension certified)
        steps = [
            {"value": str(mass.value), "unit": "g", "note": "given mass (weighed)"},
            {"value": _exact_decimal_str(Fraction(n.value)), "unit": "mol",
             "note": f"÷ {molar_mass} g/mol (molar mass)"},
        ]
        return Fraction(n.value), steps
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


def _gas_volume_block(row, cond: dict, data, ctx: str) -> tuple[dict, list[dict]]:
    """The gas-stoichiometry payoff (ADR-0041): the ledger fixes the moles of the gas product; PV=nRT fixes its
    VOLUME at the stated collection conditions. Regime-2 (model-exact — ideal gas): the moles are exact (ledger),
    the volume is computed THROUGH the units engine (dimensions certified: mol·L·atm·mol⁻¹·K⁻¹·K / atm → L) and
    then rounded (R is non-terminating). °C is converted to kelvin at the boundary (K = °C + 273.15) — an affine
    offset, never a scaling unit (ADR-0040). Returns (gas block, the mol→L dimensional chain)."""
    if "gas_constant" not in data.constants:
        raise BuildError(f"{ctx}: a gas-stoichiometry result needs the gas constant in data/constants.toml")
    R = data.constants["gas_constant"]                       # Decimal, L·atm·mol⁻¹·K⁻¹ (sourced)
    pressure = Decimal(str(cond["pressure_atm"]))
    celsius = None
    if "temperature_K" in cond:
        temperature = Decimal(str(cond["temperature_K"]))
    elif "temperature_C" in cond:
        celsius = Decimal(str(cond["temperature_C"]))
        temperature = celsius + Decimal("273.15")            # affine boundary conversion (ADR-0040)
    else:
        raise BuildError(f"{ctx}: gas conditions need temperature_K or temperature_C")

    n = row.final_mol                                        # exact ledger moles of the gas (terminating)
    n_dec = Decimal(_exact_decimal_str(n))
    QR = Quantity.of(R, "L*atm/(mol*K)")
    volume = (Quantity.of(n_dec, "mol") * QR * Quantity.of(temperature, "K")
              / Quantity.of(pressure, "atm")).to("L").value  # Decimal (non-terminating)
    molar_volume = (QR * Quantity.of(temperature, "K") / Quantity.of(pressure, "atm")).canonical  # RT/P, L/mol

    block = {
        "species": _core(row.species),
        "phase": "g",
        "moles": _exact_decimal_str(n),
        "pressure_atm": format(pressure, "f"),
        "temperature_K": format(temperature, "f"),
        **({"temperature_C": format(celsius, "f")} if celsius is not None else {}),
        "gas_constant": format(R, "f"),
        "gas_constant_source": data.sources.get("constants", ""),
        "volume_L": _sigfig(volume, 4),                      # the checked value (4 sig figs)
        "volume_L_display": _sigfig(volume, 3),              # the headline (3 sig figs, ADR-0025/0040)
        "molar_volume_L_per_mol_display": _sigfig(molar_volume, 3),  # RT/P — for the STP-22.4 contrast
    }

    chain = [
        {"value": _exact_decimal_str(n), "unit": "mol",
         "note": f"moles of {_core(row.species)} from the ledger (= ξ × {row.nu})"},
        {"value": _sigfig(volume, 3), "unit": "L",
         "note": f"× RT/P = {_sigfig(molar_volume, 3)} L/mol (ideal gas, PV=nRT)"},
    ]
    return block, chain


def _energy_block(ledger, reactants, products, coeffs, data, ctx: str) -> tuple[dict, list[dict]]:
    """The energy-ledger payoff (ADR-0043): reaction enthalpy attached to extent. The ledger fixes ξ (moles of
    reaction); the heat is q = ΔH_rxn·ξ. ΔH_rxn is derived by **Hess's law** — ΔH_rxn = Σ_products ν·ΔH_f° −
    Σ_reactants ν·ΔH_f° — over the SOURCED standard enthalpies of formation (data/formation-enthalpies.toml),
    exact Decimal arithmetic (like average atomic mass: exact over sourced data). Honesty layered, not mixed:
    ξ is ledger-exact (machine-checked); the ΔH_f° are data-sourced (regime-3); the RELATIONS (Hess's law,
    q = ΔH_rxn·ξ at constant pressure to completion) are model-assumed (regime-2). q is EXACT here (all inputs
    terminate — distinct from the gas volume's non-terminating R), computed THROUGH the units engine so the
    dimension is certified (kJ·mol⁻¹ × mol → kJ). Returns (energy block, the ξ→q dimensional chain)."""
    n_r = len(reactants)
    xi = ledger.extent_mol                                    # exact ledger extent (Fraction, terminating)
    rows = ([(f, coeffs[i], "reactant") for i, f in enumerate(reactants)]
            + [(f, coeffs[n_r + i], "product") for i, f in enumerate(products)])
    hess = []
    total = Decimal(0)                                        # ΔH_rxn = Σ (sign · ν · ΔH_f°)
    for f, c, role in rows:
        core = _core(f.raw)
        rec = data.formation_enthalpy(core, f.phase)          # raises if a ΔH_f° is missing (refuse to guess)
        dhf = rec["value"]                                    # Decimal, kJ/mol (sourced)
        sign = 1 if role == "product" else -1                 # products add, reactants subtract (Hess)
        contribution = sign * c * dhf
        if contribution == 0:
            contribution = Decimal(0)                          # normalize a signed zero (elements: ΔH_f° = 0)
        total += contribution
        hess.append({
            "species": core, "role": role, "coeff": c, "phase": f.phase,
            "is_element": rec["element"],
            "delta_h_f_kj_per_mol": format(dhf, "f"),
            "contribution_kj_per_mol": format(contribution, "f"),
        })
    xi_dec = Decimal(_exact_decimal_str(xi))
    # q = ΔH_rxn·ξ through the units engine (dimension certified: kJ·mol⁻¹ × mol → kJ). Exact Decimal.
    q = (Quantity.of(total, "kJ/mol") * Quantity.of(xi_dec, "mol")).to("kJ").value
    classification = "exothermic" if total < 0 else ("endothermic" if total > 0 else "thermoneutral")

    block = {
        "delta_h_rxn_kj_per_mol": format(total, "f"),         # exact Hess sum over the sourced ΔH_f°
        "extent_mol": _exact_decimal_str(xi),                 # ξ (ledger-exact)
        "q_kj": format(q, "f"),                               # ΔH_rxn·ξ, exact (Decimal over sourced data)
        "q_kj_display": _sigfig(q, 3),                        # the headline heat, 3 sig figs (ADR-0025)
        "classification": classification,                    # exothermic (ΔH<0) / endothermic (ΔH>0)
        "source": data.sources.get("formation_enthalpies", ""),
        "hess": hess,
    }
    chain = [
        {"value": _exact_decimal_str(xi), "unit": "mol",
         "note": "extent ξ from the ledger (moles of reaction)"},
        {"value": _sigfig(q, 3), "unit": "kJ",
         "note": f"× ΔH_rxn = {format(total, 'f')} kJ/mol (Hess's law)"},
    ]
    return block, chain


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
        n, steps = _moles_and_chain(g, data, ctx)
        given_moles[g["species"]] = n
        dimensional.append({"target": f"moles of {g['species']}", "steps": steps})
        entry = {"species": g["species"]}
        if "mass_g" in g:
            entry["mass_g"] = g["mass_g"]                     # weighed reactant (ADR-0041)
        else:
            entry["volume_mL"], entry["molarity_M"] = g["volume_mL"], g["molarity_M"]
        entry["moles"] = _exact_decimal_str(n)
        given_out.append(entry)

    # phase consistency vs. the solubility ruleset (raises on mismatch); capture the precipitate's basis. The
    # ruleset classifies ionic COMPOUNDS — a free element (Zn(s) metal, H2(g)) has no solubility verdict and is
    # skipped (single element type); only a genuine multi-element neutral (aq)/(s) salt we cannot classify is a
    # build error, not a free element (ADR-0041).
    solubility_basis = None
    for f in reactants + products:
        try:
            verdict = solub.verify_phase(f, data, ctx)
        except BuildError:
            if f.charge == 0 and f.phase in ("aq", "s") and len(f.counts) > 1:
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

    # ionic equations — but only when the reaction actually HAS ions in solution. A fully molecular reaction
    # (gas-phase combustion, ADR-0043: CH4 + O2 -> CO2 + H2O) dissociates nothing, so its complete/net ionic
    # forms would just echo the molecular equation — honestly, there is no ionic equation. Detect it by "no
    # charged term survived complete_ionic" and omit the ionic views (schema makes them optional).
    left, right = complete_ionic(reactants, products, coeffs, data, ctx)
    has_ions = any(term[2] != 0 for term in left + right)     # Term = (species_id, count, charge, phase)
    if has_ions:
        net_left, net_right, spectators = net_ionic(left, right, ctx)
    else:
        net_left = net_right = spectators = None

    # result: the reported product + leftovers. The reported product is the net-ionic product — a solid
    # precipitate (precipitation) or, when no solid forms, the general product (water for an acid-base
    # neutralization, ADR-0037). A solid cites the solubility basis (ADR-0017); a neutralization additionally
    # names the dissolved salt. Both report species/phase/molar mass/moles/mass identically.
    leftovers = [{"species": _core(r.species), "moles": _exact_decimal_str(r.final_mol)}
                 for r in ledger.rows if r.nu < 0 and r.final_mol > 0]

    def _product_block(row) -> tuple[dict, object]:
        m = species_mass_g(row, data)
        block = {
            "species": _core(row.species), "phase": row.phase,
            "molar_mass_g_per_mol": str(data.molar_mass(row.species)),
            "moles": _exact_decimal_str(row.final_mol),
            "mass_g": _exact_decimal_str(m),
            "mass_g_display": str(to_decimal(m, 3)),
        }
        return block, m

    # the reported-product block goes FIRST (precipitation lessons keep their field order byte-for-byte), then
    # limiting_species + leftover. Three reported-product shapes (ADR-0037/0041): a solid precipitate; a collected
    # GAS (gas stoichiometry — the headline is its volume via PV=nRT); or the general net-ionic product (water,
    # neutralization).
    result = {}
    gas_chain = None
    energy_chain = None
    reported_mass = None
    conditions = spec.get("conditions")
    energetics = spec.get("energetics")
    solid_row = next((r for r in ledger.rows if r.phase == "s" and r.role == "product"), None)
    if solid_row is not None:
        result["precipitate"], reported_mass = _product_block(solid_row)
    elif conditions is not None:
        # gas stoichiometry: the reported product is the collected gas; its VOLUME comes from PV=nRT (ADR-0041).
        gas_id = conditions.get("gas_species") or next(
            (_core(r.species) for r in ledger.rows if r.phase == "g" and r.role == "product"), None)
        gas_row = next((r for r in ledger.rows
                        if _core(r.species) == gas_id and r.role == "product"), None)
        if gas_row is None or gas_row.phase != "g":
            raise BuildError(f"{ctx}: gas product {gas_id} is not a gas-phase product ledger row")
        result["product"], reported_mass = _product_block(gas_row)   # mass/moles (ledger-exact)
        result["gas"], gas_chain = _gas_volume_block(gas_row, conditions, data, ctx)  # volume (model-exact)
        # name the dissolved salt: the other (aqueous) product left in solution
        salt_row = next((r for r in ledger.rows
                         if r.role == "product" and _core(r.species) != gas_id), None)
        if salt_row is not None:
            result["salt"], _ = _product_block(salt_row)
    elif energetics is not None:
        # the energy ledger (ADR-0043): the headline is the HEAT q = ΔH_rxn·ξ, not a product mass. No
        # precipitate/product/gas — the ledger tab shows the products formed; the energy block is the payoff.
        result["energy"], energy_chain = _energy_block(ledger, reactants, products, coeffs, data, ctx)
    else:
        # the net-ionic product (the single species on the right of the net ionic — e.g. H2O)
        if net_right is None:
            raise BuildError(f"{ctx}: reaction has no ions in solution and no gas/energetics/solid product "
                             f"— nothing to report (add [conditions] or [energetics], or a solid product)")
        net_product_id = next(iter(net_right))[0]
        prod_row = next((r for r in ledger.rows
                         if _core(r.species) == net_product_id and r.role == "product"), None)
        if prod_row is None:
            raise BuildError(f"{ctx}: net-ionic product {net_product_id} has no product ledger row")
        result["product"], reported_mass = _product_block(prod_row)
        # name the dissolved salt: the other product (not the net-ionic product)
        salt_row = next((r for r in ledger.rows
                         if r.role == "product" and _core(r.species) != net_product_id), None)
        if salt_row is not None:
            result["salt"], _ = _product_block(salt_row)
    result["limiting_species"] = [_core(x) for x in ledger.limiting]
    result["leftover"] = leftovers
    if gas_chain is not None:
        dimensional.append({"target": f"volume of {result['gas']['species']} gas at "
                            f"{result['gas']['pressure_atm']} atm, {result['gas']['temperature_K']} K",
                            "steps": gas_chain})
    if energy_chain is not None:
        dimensional.append({"target": f"heat of reaction q = ΔH_rxn × ξ "
                            f"({result['energy']['classification']})", "steps": energy_chain})

    # molecular always; the complete/net ionic views only when the reaction has ions in solution (ADR-0043 —
    # a fully molecular combustion has no ionic equation, so it emits only the molecular). Key order preserved
    # so existing aqueous lessons stay byte-identical.
    equations = {
        "molecular": {"text": _molecular_text(spec["reactants"], coeffs[:len(reactants)])
                      + " -> " + _molecular_text(spec["products"], coeffs[len(reactants):]),
                      "latex": _molecular_latex(reactants, coeffs[:len(reactants)])
                      + r" \rightarrow " + _molecular_latex(products, coeffs[len(reactants):])},
    }
    if has_ions:
        equations["complete_ionic"] = {"text": _ionic_text(left) + " -> " + _ionic_text(right),
                                       "latex": _ionic_latex(left) + r" \rightarrow " + _ionic_latex(right)}
        equations["net_ionic"] = {"text": _net_text(net_left) + " -> " + _net_text(net_right),
                                  "latex": _net_latex(net_left) + r" \rightarrow " + _net_latex(net_right)}
        equations["spectators"] = spectators

    solution = {
        "id": spec["id"],
        "title": spec["title"],
        "slug": spec["slug"],
        "topic": spec["topic"],
        "tags": spec.get("tags", []),
        "scenario": spec["scenario"],
        "regimes": [{"facet": k, "regime": _REGIME_NAME[k]} for k in spec.get("regimes", _DEFAULT_REGIMES)],
        "assumptions": spec.get("assumptions", []),
        "given": given_out,
        "equations": equations,
        "ledger": {
            "extent_symbol": "xi",
            "extent_mol": _exact_decimal_str(ledger.extent_mol),
            "limiting": [_core(x) for x in ledger.limiting],
            "species": ledger_species,
        },
        "dimensional_analysis": dimensional,
        "result": result,
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
            # solubility source travels only with a precipitation lesson (a solid product); a neutralization
            # has no solubility claim (ADR-0037), so its provenance omits it. A gas-stoichiometry lesson cites
            # the gas constant's source instead (ADR-0041), since its volume rides on R.
            "sources": {
                "atomic_weight": data.sources.get("atomic_weight", ""),
                "ion_charge": data.sources.get("ion_charge", ""),
                **({"solubility": solub.source} if solid_row is not None else {}),
                **({"constants": data.sources.get("constants", "")} if gas_chain is not None else {}),
                # the energy ledger cites the formation-enthalpy source the ΔH_rxn Hess sum rides on (ADR-0043)
                **({"formation_enthalpies": data.sources.get("formation_enthalpies", "")}
                   if energy_chain is not None else {}),
            },
        },
    }
    if solubility_basis is not None:
        solution["solubility_basis"] = solubility_basis

    # percent yield (ADR-0029): the theoretical yield IS the precipitate mass — the ledger at maximum extent.
    # The authored actual (measured) yield gives percent = actual ÷ theoretical × 100. Refuse a nonphysical
    # yield: actual must be positive and no greater than theoretical (you cannot collect more than forms —
    # that would break conservation of mass). Percent is a measured ratio, reported at 3 sig figs (ADR-0025).
    # Percent yield is a gravimetric-precipitation concept — only for a solid product.
    yield_spec = spec.get("yield")
    if yield_spec is not None:
        if solid_row is None:
            raise BuildError(f"{ctx}: percent yield needs a solid precipitate product")
        theoretical = reported_mass
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
    # for the supported single-precipitate double-displacement shape, which needs the net-ionic ion pair; a
    # molecular reaction (no ions, ADR-0043) has none, so skip it entirely.
    interactive = (build_interactive(reactants, products, coeffs, spec["given"], data, net_left, net_right, ctx)
                   if has_ions else None)
    if interactive is not None:
        solution["interactive"] = interactive

    # generated practice (ADR-0011, brief §6.8): deterministic solver-verified variants off the same reaction.
    # Optional; needs the interactive block (shares its engine-derived multiplicities). Refuses to emit fewer
    # than the requested count (a build failure beats silently short-changing practice).
    practice_spec = spec.get("practice")
    if practice_spec and interactive is not None:
        family = "precipitation_limiting_reagent_v1" if solid_row is not None else "acid_base_limiting_reagent_v1"
        noun = "precipitate" if solid_row is not None else ""
        practice = generate_practice(interactive, int(practice_spec["seed"]),
                                     int(practice_spec.get("count", 4)), ctx, family=family, product_noun=noun)
        if practice is None:
            raise BuildError(f"{ctx}: practice generator could not produce {practice_spec.get('count', 4)} "
                             f"non-rejected variants at seed {practice_spec['seed']}")
        solution["practice"] = practice
    elif practice_spec and gas_chain is not None:
        # gas-stoichiometry practice (ADR-0041): the single-replacement shape has no cation/anion interactive, so
        # its variants re-derive from the reaction constants (metal + acid coefficients, R, T, P) that travel in
        # the practice block — check-parity re-proves each answer in Node. metal = the free-element reactant.
        metal_f = next((f for f in reactants if f.charge == 0 and len(f.counts) == 1), None)
        acid_f = next((f for f in reactants if f is not metal_f), None)
        if metal_f is None or acid_f is None:
            raise BuildError(f"{ctx}: gas practice needs a free-element metal + an acid reactant")
        idx = {id(f): i for i, f in enumerate(reactants)}
        gas_id = result["gas"]["species"]
        gas_prod_i = next(i for i, f in enumerate(products) if _core(f.raw) == gas_id)
        practice = generate_gas_practice(
            int(practice_spec["seed"]), int(practice_spec.get("count", 6)), ctx,
            metal={"id": _core(metal_f.raw), "molar_mass": data.molar_mass(metal_f.raw),
                   "coeff": coeffs[idx[id(metal_f)]]},
            acid={"id": _core(acid_f.raw), "coeff": coeffs[idx[id(acid_f)]]},
            gas={"id": gas_id, "coeff": coeffs[len(reactants) + gas_prod_i], "molar_mass": data.molar_mass(gas_id)},
            R=data.constants["gas_constant"], temperature_K=Decimal(result["gas"]["temperature_K"]),
            pressure_atm=Decimal(result["gas"]["pressure_atm"]))
        if practice is None:
            raise BuildError(f"{ctx}: gas practice generator could not produce {practice_spec.get('count', 6)} "
                             f"non-rejected variants at seed {practice_spec['seed']}")
        solution["practice"] = practice
    elif practice_spec and energy_chain is not None:
        # energy-ledger practice (ADR-0043): vary the two reactant masses → the heat q=ΔH_rxn·ξ + leftover +
        # limiting. No interactive; the reaction constants (each reactant's molar mass + coefficient, ΔH_rxn)
        # travel in the practice `energetics` block so check-parity re-derives every answer in Node.
        if len(reactants) != 2:
            raise BuildError(f"{ctx}: energy practice expects exactly two reactants")
        practice = generate_energy_practice(
            int(practice_spec["seed"]), int(practice_spec.get("count", 6)), ctx,
            reactant_a={"id": _core(reactants[0].raw), "molar_mass": data.molar_mass(reactants[0].raw),
                        "coeff": coeffs[0]},
            reactant_b={"id": _core(reactants[1].raw), "molar_mass": data.molar_mass(reactants[1].raw),
                        "coeff": coeffs[1]},
            delta_h_rxn=Decimal(result["energy"]["delta_h_rxn_kj_per_mol"]))
        if practice is None:
            raise BuildError(f"{ctx}: energy practice generator could not produce {practice_spec.get('count', 6)} "
                             f"non-rejected variants at seed {practice_spec['seed']}")
        solution["practice"] = practice

    return solution, f"{spec['topic']}/{spec['slug']}.solution.json"


def _load_molecule_specs(root: Path) -> dict[str, dict]:
    """Map every authored molecule Atlas entry's id → its parsed TOML spec (ADR-0045). A structure lesson names
    a molecule by id and REUSES its authored connectivity — one source of truth for the structure, so the lesson
    and the Atlas can never drift."""
    specs: dict[str, dict] = {}
    for path in sorted((root / "reference" / "molecules").glob("*.toml")):
        spec = tomllib.loads(path.read_text(encoding="utf-8"))
        mid = spec.get("id")
        if mid is None:
            raise BuildError(f"{path.name}: molecule spec has no id")
        specs[mid] = spec
    return specs


def build_structure(path: Path, root: Path) -> tuple[dict, str]:
    """An authored structure lesson (ADR-0045): a single molecule stepped valence → Lewis → VSEPR → polarity.
    Resolves the referenced `molecule` Atlas entry, then hands both specs to `build_structure_lesson`, which
    re-derives + machine-checks the electron ledger via the shared `compute_ledger` engine."""
    spec = tomllib.loads(path.read_text(encoding="utf-8"))
    ctx = spec.get("id", path.stem)
    data = ChemData.load(root)
    mol_id = spec.get("molecule")
    if not mol_id:
        raise BuildError(f"{ctx}: structure lesson needs a `molecule` (a molecule Atlas entry id)")
    molecules = _load_molecule_specs(root)
    molecule_spec = molecules.get(mol_id)
    if molecule_spec is None:
        raise BuildError(f"{ctx}: molecule '{mol_id}' resolves to no reference/molecules/*.toml entry")
    lesson = build_structure_lesson(spec, molecule_spec, data, ctx)
    return lesson, f"{spec['topic']}/{spec['slug']}.structure.json"


def build_comparison(path: Path, root: Path) -> tuple[dict, str]:
    """An authored multi-molecule comparison lesson (ADR-0047): several molecules lined up against a property
    (boiling point) with the IMF-strength trend machine-verified. Builds every referenced `molecule` Atlas entry
    from its authored spec (so each row's IMF + boiling point is the same verified value the Atlas shows), then
    hands them to `build_comparison_lesson`, which sorts by boiling point and proves the trend is monotonic."""
    spec = tomllib.loads(path.read_text(encoding="utf-8"))
    ctx = spec.get("id", path.stem)
    data = ChemData.load(root)
    entries = {mid: build_molecule_entry(mspec, data, ctx=mid)
               for mid, mspec in _load_molecule_specs(root).items()}
    lesson = build_comparison_lesson(spec, entries, data, ctx)
    return lesson, f"{spec['topic']}/{spec['slug']}.comparison.json"


def build_equilibrium(path: Path, root: Path) -> tuple[dict, str]:
    """An authored equilibrium lesson (ADR-0048): the ICE table = the species ledger with the extent solved from
    mass action. Six subtypes, dispatched by the spec's keys: a **weak-acid** lesson (`acid` — the dissociation
    HA ⇌ H⁺ + A⁻ from acids-bases.toml + Kₐ from ionization-constants.toml → the pH), a **buffer** lesson (`acid`
    with `conjugate_base_molarity_M` — the same reaction but with A⁻ already present → the common-ion effect +
    Henderson–Hasselbalch), a **weak-base** lesson (`base` — B + H₂O ⇌ BH⁺ + OH⁻, K_b + the conjugate acid from
    ionization-constants.toml, water excluded from Q, → pOH → pH via K_w), a **solubility** lesson (`salt` —
    the dissolution from solubility-products.toml → the molar solubility; the solid excluded from Q, optionally with
    a **common ion** pre-loaded to suppress it), a **polyprotic** lesson (a `salt`/`acid` with ≥2 protons — staged
    Kₐ1≫Kₐ2≫Kₐ3, the solver run once per stage), or a **titration** lesson (a `titrant` key — a weak acid vs a strong
    base, the ledger marched by region into a build-time (volume, pH) curve)."""
    spec = tomllib.loads(path.read_text(encoding="utf-8"))
    ctx = spec.get("id", path.stem)
    data = ChemData.load(root)
    if "salt" in spec:
        lesson = build_solubility_lesson(spec, data, ctx)
    elif "base" in spec:
        lesson = build_weak_base_lesson(spec, data, ctx)
    elif "acid" in spec:
        acidbase = AcidBase.load(root)
        acidbase.validate(data)  # regime-1 composition self-check of the sourced acid/base table
        acid = acidbase.acids.get(spec["acid"])
        # `titrant` (a strong base being added) → a titration curve. Otherwise the acid's proton count decides:
        # a polyprotic acid (≥2 protons) ionizes in stages; a monoprotic acid is a weak-acid pH, or a buffer if
        # its conjugate base is also present.
        if "titrant" in spec:
            lesson = build_titration_lesson(spec, data, acidbase, ctx)
        elif acid is not None and int(acid.get("protons", 0)) >= 2:
            lesson = build_polyprotic_lesson(spec, data, acidbase, ctx)
        elif "conjugate_base_molarity_M" in spec:   # a buffer: HA + its conjugate base A⁻ both present
            lesson = build_buffer_lesson(spec, data, acidbase, ctx)
        else:
            lesson = build_equilibrium_lesson(spec, data, acidbase, ctx)
    else:
        raise BuildError(f"{ctx}: equilibrium lesson needs an `acid` (weak-acid pH / buffer / polyprotic), a "
                         f"`base` (weak-base pH), or a `salt` (Ksp solubility)")
    return lesson, f"{spec['topic']}/{spec['slug']}.equilibrium.json"


def build_prediction(path: Path, root: Path) -> tuple[dict, str]:
    """An authored precipitation-prediction lesson (ADR-0048, 9th increment) → the `prediction` lesson kind: mix
    two solutions, dilute each ion into the combined volume, evaluate the reaction quotient Q = [cation]ᵃ[anion]ᵇ
    and compare it to Kₛₚ → does a precipitate form? A **snapshot comparison**, not an equilibrium solve — its own
    compact `*.prediction.json` shape. The salt's Kₛₚ + ion composition come from data/solubility-products.toml."""
    spec = tomllib.loads(path.read_text(encoding="utf-8"))
    ctx = spec.get("id", path.stem)
    data = ChemData.load(root)
    lesson = build_prediction_lesson(spec, data, ctx)
    return lesson, f"{spec['topic']}/{spec['slug']}.prediction.json"


def build_kinetics(path: Path, root: Path) -> tuple[dict, str]:
    """An authored kinetics lesson (ADR-0049) → the `kinetics` lesson kind: the species ledger with the extent
    evolving in TIME. A first-order reactant decays by the integrated rate law [A](t) = [A]₀·e^(−kt), with
    half-life t½ = ln2/k. The rate constant + order come from data/rate-constants.toml (sourced)."""
    spec = tomllib.loads(path.read_text(encoding="utf-8"))
    ctx = spec.get("id", path.stem)
    data = ChemData.load(root)
    lesson = build_kinetics_lesson(spec, data, ctx)
    return lesson, f"{spec['topic']}/{spec['slug']}.kinetics.json"


def build_electrochemistry(path: Path, root: Path) -> tuple[dict, str]:
    """An authored electrochemistry lesson (ADR-0050) → the `electrochemistry` lesson kind: the species ledger with
    ELECTRONS tracked. A galvanic cell from two sourced metal-ion/metal couples — oxidation numbers, half-reactions,
    the electron ledger (n), E°cell = E°(cathode) − E°(anode), and ΔG° = −nFE°. Data from
    data/reduction-potentials.toml + the Faraday constant in data/constants.toml (sourced)."""
    spec = tomllib.loads(path.read_text(encoding="utf-8"))
    ctx = spec.get("id", path.stem)
    data = ChemData.load(root)
    lesson = build_electrochemistry_lesson(spec, data, ctx)
    return lesson, f"{spec['topic']}/{spec['slug']}.electrochemistry.json"


def build_reference_main(argv: list[str] | None = None) -> int:
    """Build the Chemical Atlas: the Valence Table (from data/) + authored concept and reaction-family
    entries (reference/**). Reaction-family examples are balanced + classified by the engine (ADR-0035)."""
    root = Path.cwd()
    data = ChemData.load(root)
    solub = Solubility.load(root)
    acidbase = AcidBase.load(root)
    decomp = Decomposition.load(root)
    try:
        acidbase.validate(data)     # regime-1 composition self-check of the sourced acid/base + decomp tables
        decomp.validate(data)
    except BuildError as e:
        print(f"BUILD FAILED — {e}", file=sys.stderr)
        return 1

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
            kind = spec.get("kind")
            if kind == "reaction-family":
                entry = build_reaction_family(spec, data, solubility=solub, acidbase=acidbase,
                                              decomposition=decomp, ctx=ctx)
            elif kind == "species":
                entry = build_species_entry(spec, data, ctx)
            elif kind == "formula":
                entry = build_formula_entry(spec, data, ctx)
            elif kind == "molecule":
                entry = build_molecule_entry(spec, data, ctx)
            else:
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
    """Build every authored lesson under problems/ (ADR-0019/0045/0047/0048/0049/0050). Seven lesson shapes,
    dispatched by file extension: a **reaction** lesson `*.problem.toml` → `build_problem` (equations + species
    ledger over extent + a reported product); a **structure** lesson `*.structure.toml` → `build_structure` (a
    single molecule's Lewis electron ledger, stepped valence → shape → polarity); a **comparison** lesson
    `*.comparison.toml` → `build_comparison` (several molecules vs. a property, the IMF-strength trend
    machine-verified); an **equilibrium** lesson `*.equilibrium.toml` → `build_equilibrium` (the ICE table =
    the species ledger with the extent solved from mass action, ADR-0048); a **prediction** lesson
    `*.prediction.toml` → `build_prediction` (Q vs Kₛₚ — does a precipitate form?, ADR-0048); a **kinetics** lesson
    `*.kinetics.toml` → `build_kinetics` (the ledger in time, orders 0/1/2 with a decay curve, ADR-0049); and an
    **electrochemistry** lesson `*.electrochemistry.toml` → `build_electrochemistry` (the electron ledger —
    oxidation numbers → half-reactions → E°cell → ΔG = −nFE°, ADR-0050). All write verified derived JSON."""
    root = Path.cwd()
    reactions = sorted((root / "problems").glob("**/*.problem.toml"))
    structures = sorted((root / "problems").glob("**/*.structure.toml"))
    comparisons = sorted((root / "problems").glob("**/*.comparison.toml"))
    equilibria = sorted((root / "problems").glob("**/*.equilibrium.toml"))
    predictions = sorted((root / "problems").glob("**/*.prediction.toml"))
    kinetics = sorted((root / "problems").glob("**/*.kinetics.toml"))
    electrochem = sorted((root / "problems").glob("**/*.electrochemistry.toml"))
    if not (reactions or structures or comparisons or equilibria or predictions or kinetics or electrochem):
        print("no *.problem.toml / *.structure.toml / *.comparison.toml / *.equilibrium.toml / *.prediction.toml / "
              "*.kinetics.toml / *.electrochemistry.toml found under problems/", file=sys.stderr)
        return 1
    lessons = ([(p, build_problem) for p in reactions]
               + [(p, build_structure) for p in structures]
               + [(p, build_comparison) for p in comparisons]
               + [(p, build_equilibrium) for p in equilibria]
               + [(p, build_prediction) for p in predictions]
               + [(p, build_kinetics) for p in kinetics]
               + [(p, build_electrochemistry) for p in electrochem])
    for path, builder in lessons:
        try:
            obj, out_rel = builder(path, root)
        except BuildError as e:
            print(f"BUILD FAILED — {e}", file=sys.stderr)
            return 1
        _write_json(root / "derived" / out_rel, obj)
        print(f"  built {path.relative_to(root).as_posix()} -> derived/{out_rel}")
    return 0
