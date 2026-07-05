"""Solubility classifier (ADR-0006, ADR-0017).

Applies the sourced solubility ruleset (data/solubility.toml) to decide whether an ionic compound is
soluble (→ aqueous) or insoluble (→ a precipitate), and returns the exact rule that governed the call so
the lesson can cite it (regime-3, data/rule-sourced badge). This is what makes a precipitate machine-
classified and rule-cited rather than author-asserted; `verify_phase` turns a mismatch between an authored
phase and the ruleset into a build failure.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

from . import BuildError
from .formula import Formula
from .reaction import dissociate


@dataclass(frozen=True)
class Verdict:
    soluble: bool
    rule_id: str
    statement: str
    cation: str
    anion: str


class Solubility:
    def __init__(self, soluble_cations, cation_rule, soluble, insoluble, source):
        self.soluble_cations = soluble_cations
        self.cation_rule = cation_rule
        self.soluble = soluble        # list of {id, anion, except, statement}
        self.insoluble = insoluble
        self.source = source

    @classmethod
    def load(cls, root: Path | None = None) -> "Solubility":
        d = (Path(root) if root is not None else Path.cwd()) / "data"
        doc = tomllib.loads((d / "solubility.toml").read_text(encoding="utf-8"))
        return cls(
            soluble_cations=doc.get("soluble_cations", []),
            cation_rule=doc.get("cation_rule", ""),
            soluble=doc.get("soluble", []),
            insoluble=doc.get("insoluble", []),
            source=doc.get("source", ""),
        )

    def _cation_in(self, cation_id: str, group: list[str], data) -> bool:
        for token in group:
            if token == "group1":
                ion = data.ions.get(cation_id)
                if ion and ion.kind == "monatomic" and ion.element:
                    el = data.elements.get(ion.element)
                    if el and el.group == 1:
                        return True
            elif token == cation_id:
                return True
        return False

    def classify(self, cation_id: str, anion_id: str, data, ctx: str = "") -> Verdict:
        where = f"{ctx}: " if ctx else ""
        if self._cation_in(cation_id, self.soluble_cations, data):
            return Verdict(True, "sol-cation", self.cation_rule, cation_id, anion_id)
        for r in self.soluble:
            if r["anion"] == anion_id:
                if self._cation_in(cation_id, r.get("except", []), data):
                    return Verdict(False, r["id"] + "-exception",
                                   f"{r['statement']} Here {cation_id} is an exception, so it is insoluble.",
                                   cation_id, anion_id)
                return Verdict(True, r["id"], r["statement"], cation_id, anion_id)
        for r in self.insoluble:
            if r["anion"] == anion_id:
                if self._cation_in(cation_id, r.get("except", []), data):
                    return Verdict(True, r["id"] + "-exception",
                                   f"{r['statement']} Here {cation_id} is an exception, so it is soluble.",
                                   cation_id, anion_id)
                return Verdict(False, r["id"], r["statement"], cation_id, anion_id)
        raise BuildError(f"{where}no solubility rule covers anion {anion_id}")

    def classify_compound(self, formula: Formula, data, ctx: str = "") -> Verdict:
        ions = dissociate(formula, data, ctx)
        cation = next(i for i, _ in ions if data.ions[i].charge > 0)
        anion = next(i for i, _ in ions if data.ions[i].charge < 0)
        return self.classify(cation, anion, data, ctx)

    def verify_phase(self, formula: Formula, data, ctx: str = "") -> Verdict:
        """Check an authored phase against the ruleset; raise on mismatch. Returns the governing verdict."""
        where = f"{ctx}: " if ctx else ""
        v = self.classify_compound(formula, data, ctx)
        expected = "aq" if v.soluble else "s"
        if formula.phase in ("aq", "s") and formula.phase != expected:
            raise BuildError(
                f"{where}{formula.raw} is labeled ({formula.phase}) but the ruleset says {expected} "
                f"({v.rule_id}: {v.statement})"
            )
        return v
