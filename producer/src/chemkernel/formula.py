"""Chemical formula parser (ADR-0014).

Parses a formula string into an element-count vector, total charge, and phase. Grammar v0:

    elements     [A-Z][a-z]?
    subscripts   integer after an element or a ')'
    groups       ( ... ) with an optional subscript, nestable, e.g. Fe(CN)6, Ca(OH)2
    charge       a trailing caret form: ^2-, ^+, ^-, ^3+   (house-conventions §Notation)
    phase        an optional trailing (s) | (l) | (g) | (aq)

Hydrates (·, e.g. CuSO4·5H2O) and isotopes are out of scope for v0 (architecture Q3).

This module is PURE: no empirical data (ADR-0006). Counts, charge, phase, and display LaTeX depend only
on the string. Molar mass — which needs atomic weights — lives in data.ChemData.molar_mass().
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from . import BuildError

_PHASE_RE = re.compile(r"\((s|l|g|aq)\)$")
_CHARGE_RE = re.compile(r"\^(\d*)([+-])$")
_ELEMENT_RE = re.compile(r"[A-Z][a-z]?")


@dataclass(frozen=True)
class Formula:
    """A parsed formula. `counts` maps element symbol -> integer count; `charge` is signed (0 if neutral);
    `phase` is one of s/l/g/aq or None; `latex` is KaTeX-ready display markup."""

    raw: str
    counts: dict[str, int]
    charge: int
    phase: str | None
    latex: str


def parse_formula(text: str, ctx: str = "") -> Formula:
    where = f"{ctx}: " if ctx else ""
    raw = text.strip()
    if not raw:
        raise BuildError(f"{where}empty formula")

    body = raw

    phase: str | None = None
    m = _PHASE_RE.search(body)
    if m:
        phase = m.group(1)
        body = body[: m.start()]

    charge = 0
    m = _CHARGE_RE.search(body)
    if m:
        magnitude = int(m.group(1)) if m.group(1) else 1
        charge = magnitude if m.group(2) == "+" else -magnitude
        body = body[: m.start()]

    if not body:
        raise BuildError(f"{where}formula '{raw}' has a charge/phase but no chemical body")

    counts = _parse_body(body, raw, where)
    latex = _to_latex(body, charge, phase)
    return Formula(raw=raw, counts=counts, charge=charge, phase=phase, latex=latex)


def _parse_body(body: str, raw: str, where: str) -> dict[str, int]:
    stack: list[dict[str, int]] = [{}]
    i, n = 0, len(body)
    while i < n:
        c = body[i]
        if c == "(":
            stack.append({})
            i += 1
        elif c == ")":
            i += 1
            j = i
            while j < n and body[j].isdigit():
                j += 1
            mult = int(body[i:j]) if j > i else 1
            i = j
            if len(stack) == 1:
                raise BuildError(f"{where}unbalanced ')' in '{raw}'")
            group = stack.pop()
            top = stack[-1]
            for el, k in group.items():
                top[el] = top.get(el, 0) + k * mult
        else:
            m = _ELEMENT_RE.match(body, i)
            if not m:
                raise BuildError(f"{where}unexpected character {c!r} in '{raw}'")
            el = m.group(0)
            i = m.end()
            j = i
            while j < n and body[j].isdigit():
                j += 1
            sub = int(body[i:j]) if j > i else 1
            i = j
            top = stack[-1]
            top[el] = top.get(el, 0) + sub
    if len(stack) != 1:
        raise BuildError(f"{where}unbalanced '(' in '{raw}'")
    if not stack[0]:
        raise BuildError(f"{where}no elements parsed from '{raw}'")
    return stack[0]


def _to_latex(body: str, charge: int, phase: str | None) -> str:
    out = re.sub(r"(\d+)", r"_{\1}", body)
    if charge:
        magnitude = abs(charge)
        sign = "+" if charge > 0 else "-"
        out += "^{" + (f"{magnitude}{sign}" if magnitude != 1 else sign) + "}"
    if phase:
        out += r"\,\text{(" + phase + ")}"
    return out
