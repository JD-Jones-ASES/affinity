"""Curated-data loader (ADR-0006, ADR-0012).

The ONLY path from producer logic to empirical constants: atomic weights and ion charges live in
data/*.toml, never hard-coded in code. Values are read as Decimal (never float — ADR-0013) so the
dataset's stated precision survives into molar-mass arithmetic.

On load, ChemData.validate() machine-checks the dataset: every ion formula parses and is composed of
elements that exist in elements.toml, and every monatomic ion agrees with its linked element. So the
*composition* of the ion table is regime-1 verified even though the ion *charges* are regime-3 sourced.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from . import BuildError
from .formula import parse_formula


@dataclass(frozen=True)
class Element:
    symbol: str
    Z: int
    name: str
    atomic_weight: Decimal
    group: int
    period: int
    block: str
    uncertainty: Decimal | None = None
    # periodic properties (ADR-0031); optional — omitted where the property is undefined (noble-gas
    # electronegativity) or deferred (transition-metal covalent radius). Decimal, never float (ADR-0013).
    electronegativity: Decimal | None = None        # Pauling scale (openstax-chemistry-2e)
    covalent_radius_pm: Decimal | None = None        # single-bond covalent radius, pm (cordero-2008)
    first_ionization_kj_mol: Decimal | None = None   # first ionization energy, kJ/mol (nist)


@dataclass(frozen=True)
class Ion:
    id: str
    formula: str
    charge: int
    name: str
    kind: str
    element: str | None = None
    compound_name: str | None = None   # the name this ion takes inside a compound (ADR-0027); None if unused


class ChemData:
    def __init__(self, elements: dict[str, Element], ions: dict[str, Ion], sources: dict[str, str],
                 constants: dict[str, Decimal] | None = None, bonding: dict | None = None,
                 constant_units: dict[str, str] | None = None, specific_heats: dict | None = None,
                 formation_enthalpies: dict | None = None, vsepr: dict | None = None,
                 boiling_points: dict | None = None, ionization_constants: dict | None = None,
                 solubility_products: dict | None = None, base_ionization_constants: dict | None = None,
                 water_kw: Decimal | None = None):
        self.elements = elements
        self.ions = ions
        self.sources = sources
        self.constants = constants or {}
        self.constant_units = constant_units or {}
        self.bonding = bonding or {}
        self.specific_heats = specific_heats or {}   # display name -> {name, phase, specific_heat (Decimal)}
        # standard enthalpies of formation (ADR-0043), keyed "formula(phase)" (H2O differs by state) ->
        # {name, element (bool), value (Decimal, kJ/mol)}. The energy ledger sums ν·ΔH_f° for Hess's law.
        self.formation_enthalpies = formation_enthalpies or {}
        # VSEPR geometry table (ADR-0044), keyed (domains, lone_pairs) -> the sourced geometry names + angle.
        # The molecule Atlas looks up the machine-derived domain count in this sourced table (regime-3 naming).
        self.vsepr = vsepr or {}
        # normal boiling points (ADR-0046), keyed by phase-less formula -> {name, temperature_c (Decimal),
        # phase_change}. Sourced empirical evidence (regime-3) for the intermolecular-forces concept: IMF strength
        # shows up in the boiling point. The molecule Atlas attaches it; the classification itself is structural.
        self.boiling_points = boiling_points or {}
        # acid ionization constants Ka (ADR-0048), keyed by neutral acid formula -> {name, ka (Decimal)}. The
        # equilibrium tier's sourced datum (regime-3): the equilibrium engine solves the ICE ledger for the extent
        # that satisfies mass action, Ka = [H+][A-]/[HA]. Small Ka => the equilibrium lies far to the left.
        self.ionization_constants = ionization_constants or {}
        # solubility-product constants Ksp (ADR-0048), keyed by salt formula -> {name, ksp (Decimal), cation,
        # anion, n_cation, n_anion}. The ion counts are derived by charge crossover + the salt composition
        # machine-checked on load (regime-1); the Ksp value is sourced (regime-3). The engine dissolves the solid
        # and solves the mass-action root for the molar solubility.
        self.solubility_products = solubility_products or {}
        # base ionization constants Kb (ADR-0048, 3rd increment), keyed by neutral base formula ->
        # {name, kb (Decimal), conjugate_acid}. The Kb value is sourced (regime-3); the base composition
        # (base + H+ = conjugate_acid, the conjugate acid a +1 cation) is machine-checked on load (regime-1). The
        # equilibrium engine ionizes the base against water (excluded from Q) and solves for [OH-]; K_w bridges to pH.
        self.base_ionization_constants = base_ionization_constants or {}
        # the ion-product constant of water K_w = [H+][OH-] (ADR-0048, 3rd increment), Decimal, sourced (regime-3).
        # The bridge between [OH-] and pH: [H+] = K_w/[OH-], so pH + pOH = pK_w = 14.00 at 25 °C.
        self.water_kw = water_kw

    @property
    def avogadro(self) -> Decimal:
        """The Avogadro constant N_A in mol^-1, from data/constants.toml (exact, ADR-0006/0013)."""
        if "avogadro" not in self.constants:
            raise BuildError("Avogadro constant not loaded — is data/constants.toml present?")
        return self.constants["avogadro"]

    def constant_unit(self, key: str) -> str:
        """The unit label a curated constant carries in data/constants.toml (e.g. R's L*atm/(mol*K))."""
        if key not in self.constants:
            raise BuildError(f"unknown constant '{key}' — not in data/constants.toml")
        return self.constant_units.get(key, "")

    def formation_enthalpy(self, formula: str, phase: str) -> dict:
        """The standard enthalpy of formation ΔH_f° (kJ/mol, Decimal) of a species by (formula core, phase),
        from data/formation-enthalpies.toml (ADR-0043). Raises if absent — the energy ledger refuses to guess
        a missing ΔH_f° (ADR-0008), and ΔH_f° depends on phase (H2O liquid vs vapor)."""
        key = f"{formula}({phase})"
        if key not in self.formation_enthalpies:
            raise BuildError(f"no standard enthalpy of formation for {key} in data/formation-enthalpies.toml")
        return self.formation_enthalpies[key]

    def ionization_constant(self, formula: str) -> dict:
        """The acid ionization constant Ka (Decimal) of a weak acid by neutral formula, from
        data/ionization-constants.toml (ADR-0048). Raises if absent — the equilibrium engine refuses to guess a
        missing Ka (ADR-0008); a sourced Ka is the empirical input the ICE ledger solves against."""
        if formula not in self.ionization_constants:
            raise BuildError(f"no ionization constant for '{formula}' in data/ionization-constants.toml")
        return self.ionization_constants[formula]

    def solubility_product(self, formula: str) -> dict:
        """The solubility-product constant Ksp (Decimal) of a sparingly soluble salt by formula, with its ions +
        derived counts, from data/solubility-products.toml (ADR-0048). Raises if absent — the equilibrium engine
        refuses to guess a missing Ksp (ADR-0008)."""
        if formula not in self.solubility_products:
            raise BuildError(f"no solubility product for '{formula}' in data/solubility-products.toml")
        return self.solubility_products[formula]

    def base_ionization_constant(self, formula: str) -> dict:
        """The base ionization constant Kb (Decimal) of a weak molecular base by neutral formula, with its
        conjugate acid, from data/ionization-constants.toml (ADR-0048). Raises if absent — the equilibrium engine
        refuses to guess a missing Kb (ADR-0008)."""
        if formula not in self.base_ionization_constants:
            raise BuildError(f"no base ionization constant for '{formula}' in data/ionization-constants.toml")
        return self.base_ionization_constants[formula]

    def water_ion_product(self) -> Decimal:
        """The ion-product constant of water K_w = [H+][OH-] (Decimal), from data/ionization-constants.toml
        (ADR-0048). The acid/base bridge: [H+] = K_w/[OH-]. Raises if absent (ADR-0008 — refuse to guess K_w)."""
        if self.water_kw is None:
            raise BuildError("no water ion-product K_w in data/ionization-constants.toml [water]")
        return self.water_kw

    @classmethod
    def load(cls, root: Path | None = None) -> "ChemData":
        d = (Path(root) if root is not None else Path.cwd()) / "data"
        el_doc = tomllib.loads((d / "elements.toml").read_text(encoding="utf-8"))
        ion_doc = tomllib.loads((d / "ions.toml").read_text(encoding="utf-8"))

        elements: dict[str, Element] = {}
        for symbol, e in el_doc.get("elements", {}).items():
            opt = lambda key: Decimal(e[key]) if key in e else None  # optional Decimal, never float (ADR-0013)
            try:
                elements[symbol] = Element(
                    symbol=symbol,
                    Z=int(e["Z"]),
                    name=e["name"],
                    atomic_weight=Decimal(e["atomic_weight"]),
                    group=int(e["group"]),
                    period=int(e["period"]),
                    block=e["block"],
                    uncertainty=opt("uncertainty"),
                    electronegativity=opt("electronegativity"),
                    covalent_radius_pm=opt("covalent_radius_pm"),
                    first_ionization_kj_mol=opt("first_ionization_kj_mol"),
                )
            except (KeyError, ArithmeticError) as exc:
                raise BuildError(f"data/elements.toml: bad entry for '{symbol}': {exc}") from exc

        ions: dict[str, Ion] = {}
        for ion_id, v in ion_doc.get("ions", {}).items():
            try:
                ions[ion_id] = Ion(
                    id=ion_id,
                    formula=v["formula"],
                    charge=int(v["charge"]),
                    name=v["name"],
                    kind=v["kind"],
                    element=v.get("element"),
                    compound_name=v.get("compound_name"),
                )
            except KeyError as exc:
                raise BuildError(f"data/ions.toml: bad entry for '{ion_id}': missing {exc}") from exc

        # physical constants (optional file; ADR-0006). Values read as Decimal, never float; the unit label
        # travels alongside so the formula sheet can thread a sourced constant (R) with its units (ADR-0039).
        constants: dict[str, Decimal] = {}
        constant_units: dict[str, str] = {}
        const_source = ""
        const_path = d / "constants.toml"
        if const_path.exists():
            const_doc = tomllib.loads(const_path.read_text(encoding="utf-8"))
            const_source = const_doc.get("source", "")
            for key, v in const_doc.items():
                if isinstance(v, dict) and "value" in v:
                    try:
                        constants[key] = Decimal(v["value"])
                    except ArithmeticError as exc:
                        raise BuildError(f"data/constants.toml: bad value for '{key}': {exc}") from exc
                    constant_units[key] = v.get("unit", "")

        # bond-classification ruleset (optional file; ADR-0033). ΔEN class thresholds are a sourced teaching
        # rule (OpenStax Fig 7.8), kept as data so the bonding mode never hard-codes an empirical boundary.
        bonding: dict = {}
        bonding_path = d / "bonding.toml"
        if bonding_path.exists():
            bonding = tomllib.loads(bonding_path.read_text(encoding="utf-8"))
            for key in ("source", "caution", "classes"):
                if key not in bonding:
                    raise BuildError(f"data/bonding.toml: missing '{key}'")
            for c in bonding["classes"]:
                for key in ("id", "label", "description"):
                    if key not in c:
                        raise BuildError(f"data/bonding.toml: class missing '{key}'")
                for bound in ("min", "max"):
                    if bound in c:
                        Decimal(c[bound])  # must parse exactly (ADR-0013); raises on garbage

        # specific-heat capacities (optional file; ADR-0006/0042). A measured, data-sourced datum (regime-3) for
        # the calorimetry gym — read as Decimal (ADR-0013), the substance keyed by its display name.
        specific_heats: dict = {}
        sh_source = ""
        sh_path = d / "specific-heats.toml"
        if sh_path.exists():
            sh_doc = tomllib.loads(sh_path.read_text(encoding="utf-8"))
            sh_source = sh_doc.get("source", "")
            for key, v in sh_doc.get("substances", {}).items():
                try:
                    specific_heats[key] = {"name": v["name"], "phase": v.get("phase"),
                                           "specific_heat": Decimal(v["specific_heat"])}
                except (KeyError, ArithmeticError) as exc:
                    raise BuildError(f"data/specific-heats.toml: bad entry for '{key}': {exc}") from exc

        # standard enthalpies of formation (optional file; ADR-0006/0043). A measured, data-sourced datum
        # (regime-3) for the energy ledger — read as Decimal (ADR-0013), keyed by formula AND phase (ΔH_f°
        # differs by state). An element in its standard state is 0 by definition (`element = true`).
        formation_enthalpies: dict = {}
        fe_source = ""
        fe_path = d / "formation-enthalpies.toml"
        if fe_path.exists():
            fe_doc = tomllib.loads(fe_path.read_text(encoding="utf-8"))
            fe_source = fe_doc.get("source", "")
            for v in fe_doc.get("substances", []):
                try:
                    key = f"{v['formula']}({v['phase']})"
                    if key in formation_enthalpies:
                        raise BuildError(f"data/formation-enthalpies.toml: duplicate entry for {key}")
                    formation_enthalpies[key] = {"name": v["name"], "element": bool(v.get("element", False)),
                                                 "value": Decimal(v["delta_h_f_kj_per_mol"])}
                except (KeyError, ArithmeticError) as exc:
                    raise BuildError(f"data/formation-enthalpies.toml: bad entry {v!r}: {exc}") from exc

        # VSEPR geometry table (optional file; ADR-0006/0044). The domain-count → geometry naming convention
        # (regime-3, OpenStax §7.6) the molecule Atlas keys into; the domain count itself is machine-derived.
        # Keyed (domains, lone_pairs) so a molecule's verified structure resolves to exactly one row.
        vsepr: dict = {}
        vsepr_source = ""
        vsepr_path = d / "vsepr.toml"
        if vsepr_path.exists():
            vsepr_doc = tomllib.loads(vsepr_path.read_text(encoding="utf-8"))
            vsepr_source = vsepr_doc.get("source", "")
            for g in vsepr_doc.get("geometries", []):
                try:
                    key = (int(g["domains"]), int(g["lone_pairs"]))
                    if key in vsepr:
                        raise BuildError(f"data/vsepr.toml: duplicate geometry for {key}")
                    vsepr[key] = {"electron_geometry": g["electron_geometry"],
                                  "molecular_shape": g["molecular_shape"], "ideal_angle": g["ideal_angle"],
                                  "angle_note": g.get("angle_note")}
                except (KeyError, ValueError) as exc:
                    raise BuildError(f"data/vsepr.toml: bad entry {g!r}: {exc}") from exc

        # normal boiling points (optional file; ADR-0006/0046). A measured, data-sourced datum (regime-3) — the
        # intermolecular-forces evidence — keyed by phase-less formula, read as Decimal (ADR-0013).
        boiling_points: dict = {}
        bp_source = ""
        bp_path = d / "boiling-points.toml"
        if bp_path.exists():
            bp_doc = tomllib.loads(bp_path.read_text(encoding="utf-8"))
            bp_source = bp_doc.get("source", "")
            for key, v in bp_doc.get("substances", {}).items():
                try:
                    pc = v.get("phase_change", "boiling")
                    if pc not in ("boiling", "sublimation"):
                        raise BuildError(f"data/boiling-points.toml: '{key}' phase_change '{pc}' invalid")
                    boiling_points[key] = {"name": v["name"], "temperature_c": Decimal(v["temperature_c"]),
                                           "phase_change": pc}
                except (KeyError, ArithmeticError) as exc:
                    raise BuildError(f"data/boiling-points.toml: bad entry for '{key}': {exc}") from exc

        # ionization constants (optional file; ADR-0006/0048). Measured, data-sourced data (regime-3) for the
        # equilibrium tier — read as Decimal (ADR-0013). Acids keyed by neutral acid formula (Ka); bases by
        # neutral base formula (Kb + conjugate acid, composition machine-checked below); water carries K_w.
        ionization_constants: dict = {}
        base_ionization_constants: dict = {}
        water_kw: Decimal | None = None
        ic_source = ""
        ic_path = d / "ionization-constants.toml"
        if ic_path.exists():
            ic_doc = tomllib.loads(ic_path.read_text(encoding="utf-8"))
            ic_source = ic_doc.get("source", "")
            for key, v in ic_doc.get("acids", {}).items():
                try:
                    ka = Decimal(v["ka"])
                    if ka <= 0:
                        raise BuildError(f"data/ionization-constants.toml: '{key}' ka must be positive")
                    ionization_constants[key] = {"name": v["name"], "ka": ka}
                except (KeyError, ArithmeticError) as exc:
                    raise BuildError(f"data/ionization-constants.toml: bad entry for '{key}': {exc}") from exc
            for key, v in ic_doc.get("bases", {}).items():
                try:
                    kb = Decimal(v["kb"])
                    if kb <= 0:
                        raise BuildError(f"data/ionization-constants.toml: base '{key}' kb must be positive")
                    # machine-check the base composition (regime-1): a neutral base + one proton = its named
                    # conjugate acid, a +1 cation in the ion table (so "NH3 + H+ is NH4+" is verified).
                    ca = ions.get(v["conjugate_acid"])
                    if ca is None:
                        raise BuildError(f"data/ionization-constants.toml: base '{key}' names unknown conjugate "
                                         f"acid '{v['conjugate_acid']}'")
                    if ca.charge != 1:
                        raise BuildError(f"data/ionization-constants.toml: base '{key}' conjugate acid "
                                         f"'{ca.id}' must be a +1 cation (a monobasic weak base)")
                    fb = parse_formula(key, ctx=f"data/ionization-constants.toml base '{key}'")
                    if fb.charge != 0:
                        raise BuildError(f"data/ionization-constants.toml: base '{key}' is not neutral")
                    expect = dict(fb.counts)
                    expect["H"] = expect.get("H", 0) + 1
                    if dict(parse_formula(ca.formula).counts) != expect:
                        raise BuildError(f"data/ionization-constants.toml: base '{key}' + H+ is not "
                                         f"{ca.id} ({expect} vs {dict(parse_formula(ca.formula).counts)})")
                    base_ionization_constants[key] = {"name": v["name"], "kb": kb,
                                                      "conjugate_acid": ca.id}
                except (KeyError, ArithmeticError) as exc:
                    raise BuildError(f"data/ionization-constants.toml: bad base entry for '{key}': {exc}") from exc
            water = ic_doc.get("water")
            if water is not None:
                try:
                    water_kw = Decimal(water["kw"])
                    if water_kw <= 0:
                        raise BuildError("data/ionization-constants.toml: [water] kw must be positive")
                except (KeyError, ArithmeticError) as exc:
                    raise BuildError(f"data/ionization-constants.toml: bad [water] entry: {exc}") from exc

        # solubility-product constants Ksp (optional file; ADR-0006/0048). The Ksp value is sourced (regime-3);
        # the ion counts are DERIVED by charge crossover and the salt composition machine-checked here (regime-1),
        # like data/acids-bases.toml — so "CaF2 is Ca^2+ + 2 F^-" is verified, the Ksp is the sourced datum.
        from math import gcd as _gcd
        solubility_products: dict = {}
        sp_source = ""
        sp_path = d / "solubility-products.toml"
        if sp_path.exists():
            sp_doc = tomllib.loads(sp_path.read_text(encoding="utf-8"))
            sp_source = sp_doc.get("source", "")
            for formula, v in sp_doc.get("salts", {}).items():
                try:
                    ksp = Decimal(v["ksp"])
                    if ksp <= 0:
                        raise BuildError(f"data/solubility-products.toml: '{formula}' ksp must be positive")
                    cation, anion = ions.get(v["cation"]), ions.get(v["anion"])
                    if cation is None or anion is None:
                        raise BuildError(f"data/solubility-products.toml: '{formula}' names an unknown ion "
                                         f"({v['cation']} / {v['anion']})")
                    z_cat, z_an = cation.charge, abs(anion.charge)
                    g = _gcd(z_cat, z_an)
                    n_cat, n_an = z_an // g, z_cat // g              # charge crossover → smallest integer counts
                    # machine-check the salt composition = n_cat cations + n_an anions (regime-1)
                    expect: dict[str, int] = {}
                    for cnt, ion in ((n_cat, cation), (n_an, anion)):
                        for el, k in parse_formula(ion.formula).counts.items():
                            expect[el] = expect.get(el, 0) + k * cnt
                    if dict(parse_formula(formula).counts) != expect:
                        raise BuildError(f"data/solubility-products.toml: '{formula}' is not {n_cat} {cation.id} "
                                         f"+ {n_an} {anion.id} ({expect})")
                    solubility_products[formula] = {"name": v["name"], "ksp": ksp, "cation": cation.id,
                                                    "anion": anion.id, "n_cation": n_cat, "n_anion": n_an}
                except (KeyError, ArithmeticError) as exc:
                    raise BuildError(f"data/solubility-products.toml: bad entry for '{formula}': {exc}") from exc

        sources = {
            "atomic_weight": el_doc.get("source", ""),
            "position": el_doc.get("position_source", ""),
            "electronegativity": el_doc.get("electronegativity_source", ""),
            "covalent_radius": el_doc.get("covalent_radius_source", ""),
            "ionization_energy": el_doc.get("ionization_energy_source", ""),
            "ion_charge": ion_doc.get("charge_source", ""),
            "constants": const_source,
            "bonding": bonding.get("source", ""),
            "specific_heats": sh_source,
            "formation_enthalpies": fe_source,
            "vsepr": vsepr_source,
            "boiling_points": bp_source,
            "ionization_constants": ic_source,
            "solubility_products": sp_source,
        }
        obj = cls(elements, ions, sources, constants, bonding, constant_units, specific_heats,
                  formation_enthalpies, vsepr, boiling_points, ionization_constants, solubility_products,
                  base_ionization_constants, water_kw)
        obj.validate()
        return obj

    def atomic_weight(self, symbol: str) -> Decimal:
        el = self.elements.get(symbol)
        if el is None:
            raise BuildError(f"unknown element '{symbol}' — not in data/elements.toml")
        return el.atomic_weight

    def molar_mass(self, formula) -> Decimal:
        """Molar mass in g/mol as an exact Decimal sum of atomic weights. Accepts a formula string or a
        parsed Formula. Raises BuildError if any element is absent from the dataset."""
        f = formula if hasattr(formula, "counts") else parse_formula(formula)
        total = Decimal(0)
        for el, k in f.counts.items():
            total += self.atomic_weight(el) * k
        return total

    def validate(self) -> None:
        """Machine-check dataset self-consistency (regime-1). Raises BuildError on any inconsistency."""
        for ion in self.ions.values():
            parsed = parse_formula(ion.formula, ctx=f"data/ions.toml '{ion.id}'")
            for el in parsed.counts:
                if el not in self.elements:
                    raise BuildError(
                        f"data/ions.toml '{ion.id}': formula uses element '{el}' "
                        f"absent from data/elements.toml"
                    )
            if ion.kind == "monatomic":
                if ion.element is None or ion.element not in self.elements:
                    raise BuildError(f"data/ions.toml '{ion.id}': monatomic ion needs a known `element`")
                if set(parsed.counts) != {ion.element} or parsed.counts[ion.element] != 1:
                    raise BuildError(
                        f"data/ions.toml '{ion.id}': monatomic formula '{ion.formula}' "
                        f"disagrees with element '{ion.element}'"
                    )
