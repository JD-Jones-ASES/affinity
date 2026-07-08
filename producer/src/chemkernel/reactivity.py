"""Reaction-behavior datasets for the classifier (ADR-0035, Phase-1 item 6).

Two sourced curated tables, each loaded like `Solubility` and self-checked on load so their *composition* is
regime-1 verified even though their *classification* (acid/base, "unstable") is a regime-3 sourced convention:

  - `AcidBase` (data/acids-bases.toml): the acids and bases of a first course, with names + strong/weak.
    On load, each acid's formula must equal `protons` H plus its named anion (which must exist in the ion
    table); each base's formula must equal its cation plus |charge| hydroxide. So the *identity* "HCl acts as
    an acid" is sourced, but "HCl is H+ + Cl-" is machine-checked.
  - `Decomposition` (data/decomposition.toml): unstable intermediates that release a gas, so a
    double-replacement that would form one is a *gas-evolution* reaction. On load, every key and product
    formula must parse from known elements and the named gas must appear among the products.

Neither module is imported by `reaction.py` (which would be a cycle — `solubility` already imports
`reaction`); the classifier takes loaded instances as injected parameters instead.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

from . import BuildError
from .formula import parse_formula

_PHASE_SUFFIX = re.compile(r"\((?:s|l|g|aq)\)$")


def _core(species: str) -> str:
    return _PHASE_SUFFIX.sub("", species)


class AcidBase:
    """Acids and bases (data/acids-bases.toml). Keys are neutral formulas in the house ASCII form."""

    def __init__(self, acids: dict, bases: dict, source: str):
        self.acids = acids      # formula -> {name, strength, protons, anion}
        self.bases = bases      # formula -> {name, strength, cation}
        self.source = source

    @classmethod
    def load(cls, root: Path | None = None) -> "AcidBase":
        d = (Path(root) if root is not None else Path.cwd()) / "data"
        doc = tomllib.loads((d / "acids-bases.toml").read_text(encoding="utf-8"))
        return cls(acids=doc.get("acids", {}), bases=doc.get("bases", {}), source=doc.get("source", ""))

    def validate(self, data) -> None:
        """Machine-check every acid/base composition against the ion table (regime-1). Raises on any mismatch."""
        for formula, a in self.acids.items():
            f = parse_formula(formula, ctx=f"data/acids-bases.toml acid '{formula}'")
            if f.charge != 0:
                raise BuildError(f"data/acids-bases.toml: acid '{formula}' is not neutral")
            anion = data.ions.get(a.get("anion"))
            if anion is None:
                raise BuildError(f"data/acids-bases.toml: acid '{formula}' names unknown anion '{a.get('anion')}'")
            protons = int(a["protons"])
            expect = dict(parse_formula(anion.formula).counts)
            expect["H"] = expect.get("H", 0) + protons
            if dict(f.counts) != expect:
                raise BuildError(f"data/acids-bases.toml: acid '{formula}' ({dict(f.counts)}) is not "
                                 f"{protons} H + {anion.id} ({expect})")
        for formula, b in self.bases.items():
            f = parse_formula(formula, ctx=f"data/acids-bases.toml base '{formula}'")
            if f.charge != 0:
                raise BuildError(f"data/acids-bases.toml: base '{formula}' is not neutral")
            cation = data.ions.get(b.get("cation"))
            if cation is None:
                raise BuildError(f"data/acids-bases.toml: base '{formula}' names unknown cation '{b.get('cation')}'")
            n_oh = cation.charge
            expect = dict(parse_formula(cation.formula).counts)
            for el, k in parse_formula("OH").counts.items():
                expect[el] = expect.get(el, 0) + k * n_oh
            if dict(f.counts) != expect:
                raise BuildError(f"data/acids-bases.toml: base '{formula}' ({dict(f.counts)}) is not "
                                 f"{cation.id} + {n_oh} OH ({expect})")

    def is_acid(self, core: str) -> bool:
        return core in self.acids

    def is_base(self, core: str) -> bool:
        return core in self.bases

    def acid_name(self, core: str) -> str:
        return self.acids.get(core, {}).get("name", core)

    def base_name(self, core: str) -> str:
        return self.bases.get(core, {}).get("name", core)


class Decomposition:
    """Unstable gas-evolving intermediates (data/decomposition.toml)."""

    def __init__(self, decompositions: dict, source: str):
        self.decompositions = decompositions   # formula -> {name, products, gas, note}
        self.source = source

    @classmethod
    def load(cls, root: Path | None = None) -> "Decomposition":
        d = (Path(root) if root is not None else Path.cwd()) / "data"
        doc = tomllib.loads((d / "decomposition.toml").read_text(encoding="utf-8"))
        return cls(decompositions=doc.get("decompositions", {}), source=doc.get("source", ""))

    def validate(self, data) -> None:
        """Machine-check every intermediate + its products parse from known elements; the gas is a product."""
        for formula, e in self.decompositions.items():
            for f in [formula] + list(e.get("products", [])):
                parsed = parse_formula(_core(f), ctx=f"data/decomposition.toml '{formula}'")
                for el in parsed.counts:
                    if el not in data.elements:
                        raise BuildError(f"data/decomposition.toml '{formula}': uses unknown element '{el}'")
            gas_cores = [_core(p) for p in e.get("products", [])]
            if e.get("gas") not in gas_cores:
                raise BuildError(f"data/decomposition.toml '{formula}': gas '{e.get('gas')}' is not a product")

    def justifies(self, product_cores: list[str], gas_cores: list[str]) -> dict | None:
        """The unstable intermediate whose decomposition products are all present and whose gas is emitted —
        i.e. this reaction's products (salt + water + gas) are exactly the gas-evolution outcome. None if no
        entry fits (so a stray (g) product cannot masquerade as gas evolution)."""
        products = set(product_cores)
        for formula, e in self.decompositions.items():
            prod = {_core(p) for p in e.get("products", [])}
            if prod <= products and e.get("gas") in gas_cores:
                return {"formula": formula, "name": e["name"], "gas": e["gas"],
                        "note": e["note"], "products": list(e["products"])}
        return None
