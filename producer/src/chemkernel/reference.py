"""Chemical Atlas builder: the Valence Table (periodic lens) + authored concept entries (brief §10, §16).

Two emitted shapes under derived/reference/:
  - `valence-table.json` — a projection of data/ (elements in their IUPAC positions + the sourced ion
    charges) plus **machine-verified charge-balance examples**: the neutral formula of a cation+anion pair is
    assembled by charge crossover and re-checked for neutrality, so "CaCO3 follows from charge balance" is
    derived, not asserted (regime-1 assembly over regime-3 charges).
  - `<slug>.json` — an authored concept entry (`reference/**/*.toml`): term, definition, related edges
    (the concept graph), and the lessons it appears in.

Nothing here is hard-coded chemistry: elements and charges come from ChemData, formulas are assembled by
crossover and verified with the parser.
"""

from __future__ import annotations

import re
from decimal import Decimal
from math import gcd

from . import BuildError
from .balance import balance
from .formula import parse_formula
from .reaction import classify_reaction, complete_ionic, net_ionic

_MONATOMIC = re.compile(r"^[A-Z][a-z]?$")
_PHASE_SUFFIX = re.compile(r"\((?:s|l|g|aq)\)$")


def _group_str(formula: str, n: int) -> str:
    """One ion's contribution to an assembled formula: subscript if n>1, parenthesised if polyatomic."""
    if n == 1:
        return formula
    return f"{formula}{n}" if _MONATOMIC.match(formula) else f"({formula}){n}"


def assemble_formula(cation, anion, ctx: str = "") -> tuple[str, int, int]:
    """Neutral formula of a cation+anion pair by charge crossover; verified neutral. Returns (formula, n_cat, n_an)."""
    c, a = cation.charge, -anion.charge  # both positive magnitudes
    if c <= 0 or a <= 0:
        raise BuildError(f"{ctx}: assemble_formula needs a positive cation and negative anion")
    g = gcd(c, a)
    n_cat, n_an = a // g, c // g
    formula = _group_str(cation.formula, n_cat) + _group_str(anion.formula, n_an)
    parsed = parse_formula(formula, ctx=ctx)
    if parsed.charge != 0:
        raise BuildError(f"{ctx}: assembled {formula} is not neutral (charge {parsed.charge})")
    # composition must equal n_cat·cation + n_an·anion
    expect: dict[str, int] = {}
    for src, mult in ((cation.formula, n_cat), (anion.formula, n_an)):
        for el, k in parse_formula(src).counts.items():
            expect[el] = expect.get(el, 0) + k * mult
    if dict(parsed.counts) != expect:
        raise BuildError(f"{ctx}: assembled {formula} composition {dict(parsed.counts)} != {expect}")
    return formula, n_cat, n_an


def valence_electrons(el) -> int | None:
    """Main-group valence-electron count from the IUPAC group (ADR-0033): groups 1–2 → the group number,
    groups 13–18 → group − 10, He → 2 (its first shell fills at two). d-block counts are convention-dependent
    and honestly omitted (None) — the same discipline as the noble gases' undefined electronegativity."""
    if el.block not in ("s", "p"):
        return None
    if el.symbol == "He":
        return 2
    return el.group if el.group <= 2 else el.group - 10


def common_monatomic_ions(data) -> dict:
    """One deterministic 'common ion' per element for the lens — the lowest charge magnitude wins (Fe²⁺ over
    Fe³⁺, Cu⁺ over Cu²⁺). Shared with the periodic-trends gym so drill answers match the table (ADR-0034)."""
    by_element: dict = {}
    for ion in data.ions.values():
        if ion.kind != "monatomic" or not ion.element:
            continue
        cur = by_element.get(ion.element)
        if cur is None or (abs(ion.charge), ion.id) < (abs(cur.charge), cur.id):
            by_element[ion.element] = ion
    return by_element


def _ion_entry(ion) -> dict:
    return {"id": ion.id, "charge": ion.charge, "name": ion.name, "latex": parse_formula(ion.id).latex}


# The five lenses (brief §8.1, ADR-0033). Each pattern panel answers: what pattern / why / exceptions /
# where it shows up. The `why` text is regime-4 mechanistic/interpretive — a useful story, not a machine
# proof — so every panel is emitted `regime: "mechanistic"` and the player renders it under the amber
# model-assumed badge with an explicit "interpretive" marker (architecture Q4, resolved in ADR-0033). The
# colored values themselves are the sourced evidence; `source` keys into the table's sources map, and the
# gate requires it to resolve to a docs/SOURCES.md row.
_LENSES = [
    {
        "id": "ion-charge", "label": "Common ion charge", "property": "common_ion", "unit": "",
        "source": "ion_charge", "regime": "mechanistic",
        "panel": {
            "pattern": "Main-group metals form cations, nonmetals anions: group 1 → +1, group 2 → +2, "
                       "group 13 → +3; group 15 → −3, group 16 → −2, group 17 → −1. The noble gases form no "
                       "simple ion.",
            "why": "Atoms bond toward the nearest noble-gas electron count. A metal sheds its few valence "
                   "electrons to expose a full inner shell; a nonmetal gains the few it lacks — the charge is "
                   "just how many electrons moved.",
            "exceptions": "Transition metals (Fe and Cu here) hold more than one common charge — the Stock "
                          "numeral in a name says which. Hydrogen sits in group 1 but is no metal; it shares "
                          "electrons more often than it transfers them.",
            "where": "Formula writing (charge crossover), nomenclature (iron(II) vs iron(III)), and "
                     "predicting the products of double replacement.",
        },
    },
    {
        "id": "valence-electrons", "label": "Valence electrons", "property": "valence_electrons", "unit": "",
        "source": "position", "regime": "mechanistic",
        "panel": {
            "pattern": "The count repeats across each row: 1 and 2 on the left (s-block), then 3 through 8 "
                       "on the right (p-block). Elements in the same group carry the same count.",
            "why": "Group position IS the outer-shell electron count for main-group elements — the table was "
                   "arranged so that recurring chemistry lines up in columns, and the recurring thing is the "
                   "outer shell.",
            "exceptions": "Helium has 2, not 8 — its first shell fills at two electrons. The d-block count is "
                          "convention-dependent, so it is left blank here rather than asserted.",
            "where": "Ion charges (lose the count, or gain to reach 8), Lewis structures later, and why "
                     "period-neighbors differ while group-neighbors rhyme.",
        },
    },
    {
        "id": "electronegativity", "label": "Electronegativity", "property": "electronegativity", "unit": "",
        "source": "electronegativity", "regime": "mechanistic",
        "panel": {
            "pattern": "Rises left → right across a period, falls down a group — fluorine tops the scale "
                       "at 3.98.",
            "why": "Across a period the nuclear charge grows while electrons enter the same shell, so the "
                   "pull on a shared pair strengthens. Down a group the outer shell sits farther out, "
                   "screened by more inner shells, so the pull weakens.",
            "exceptions": "Undefined for the noble gases on the Pauling scale — shown blank, never zero. The "
                          "values are a fitted scale, not measured constants; other scales order a few "
                          "neighbors differently.",
            "where": "Bond polarity (the bonding mode's ΔEN), why oxygen and fluorine hog electron density, "
                     "and acid-strength stories later.",
        },
    },
    {
        "id": "covalent-radius", "label": "Covalent radius", "property": "covalent_radius_pm", "unit": "pm",
        "source": "covalent_radius", "regime": "mechanistic",
        "panel": {
            "pattern": "Shrinks left → right across a period, grows down a group — the biggest atoms sit "
                       "bottom-left.",
            "why": "Across a period, more protons pull the same shells in tighter. Down a group, each row "
                   "adds a whole new shell outside the last.",
            "exceptions": "A radius depends on how it is measured — these are single-bond covalent radii "
                          "(Cordero 2008). Transition-metal values depend on spin state and are left blank "
                          "rather than asserted.",
            "where": "Which-atom-is-larger drills, bond-length estimates, and the size story underneath "
                     "ionization energy and electronegativity.",
        },
    },
    {
        "id": "ionization-energy", "label": "First ionization energy", "property": "first_ionization_kj_mol",
        "unit": "kJ/mol", "source": "ionization_energy", "regime": "mechanistic",
        "panel": {
            "pattern": "Rises left → right across a period, falls down a group — helium is the hardest atom "
                       "in this set to ionize.",
            "why": "The same pull that shrinks atoms holds their electrons: more nuclear charge on the same "
                   "shell makes removal costlier; a farther, better-screened shell makes it cheaper.",
            "exceptions": "Two famous dips break the climb: boron below beryllium (the lone p electron is "
                          "easier to remove than a paired s), and oxygen below nitrogen (the first paired p "
                          "electron repels its roommate). Both are visible in this data.",
            "where": "Why metals give up electrons so readily, the order-by-ionization-energy drills, and "
                     "why successive ionizations jump at shell boundaries (later).",
        },
    },
]


def _crossover_mistake(cation, anion, formula: str) -> dict | None:
    """The canonical formula-writing mistake for a pair — each ion's OWN charge as its own subscript — proven
    wrong at emit time (ADR-0033): either non-neutral (charge sum shown) or neutral-but-unreduced (not the
    smallest whole-number ratio). Returns None when the mistake coincides with the correct formula (1:1 pairs),
    where there is nothing deceptive to name."""
    c, a = cation.charge, -anion.charge
    naive = _group_str(cation.formula, c) + _group_str(anion.formula, a)
    if naive == formula:
        return None
    total = c * c - a * a  # c cations at +c, a anions at −a
    if total != 0:
        note = (f"Each ion's own charge became its own subscript — but {c}×({_sign(cation.charge)}) + "
                f"{a}×({_sign(anion.charge)}) = {total:+d}, not 0. CROSS the charges: each subscript is the "
                f"other ion's charge.")
        return {"formula": naive, "kind": "own-charge", "note": note}
    # equal charges > 1: the naive assembly is neutral but not reduced (the gcd was skipped)
    note = (f"Neutral, but not the smallest whole-number ratio — the charges cancel one-for-one, so {naive} "
            f"reduces by the common factor {c} to {formula}.")
    return {"formula": naive, "kind": "unreduced", "note": note}


def build_valence_table(data) -> dict:
    """Emit the Valence Table from data/ — elements in IUPAC positions, sourced ion charges + properties,
    the five lenses (ADR-0033), the full verified+named crossover product, and the sourced bonding rule."""
    # deferred import: nomenclature imports assemble_formula from this module (ADR-0027), so the name hookup
    # (the item-2 deferral this table now closes) must import lazily to avoid the cycle.
    from .nomenclature import name_ionic

    monatomic_by_element = common_monatomic_ions(data)

    elements = []
    for sym, el in sorted(data.elements.items(), key=lambda kv: kv[1].Z):
        entry = {
            "symbol": sym, "Z": el.Z, "name": el.name, "atomic_weight": str(el.atomic_weight),
            "group": el.group, "period": el.period, "block": el.block,
        }
        # periodic properties (ADR-0031); emitted as strings only where curated (optional — the noble gases
        # carry no electronegativity, the transition metals no covalent radius). The lens badges each source.
        if el.electronegativity is not None:
            entry["electronegativity"] = str(el.electronegativity)
        if el.covalent_radius_pm is not None:
            entry["covalent_radius_pm"] = str(el.covalent_radius_pm)
        if el.first_ionization_kj_mol is not None:
            entry["first_ionization_kj_mol"] = str(el.first_ionization_kj_mol)
        ve = valence_electrons(el)
        if ve is not None:
            entry["valence_electrons"] = ve
        ion = monatomic_by_element.get(sym)
        if ion is not None:
            entry["common_ion"] = _ion_entry(ion)
            # a variable-charge metal surfaces ALL its common ions (ADR-0033, closing the item-2 deferral);
            # the lens keeps the deterministic lowest-charge pick as primary.
            others = sorted((i for i in data.ions.values()
                             if i.kind == "monatomic" and i.element == sym and i.id != ion.id),
                            key=lambda i: (abs(i.charge), i.id))
            if others:
                entry["other_ions"] = [_ion_entry(i) for i in others]
        elements.append(entry)

    polyatomic = [
        {"id": ion.id, "formula": ion.formula, "charge": ion.charge, "name": ion.name,
         "latex": parse_formula(ion.id).latex}
        for ion in data.ions.values() if ion.kind == "polyatomic"
    ]

    # the formula-builder product (ADR-0033): EVERY cation×anion pair in the ion table (H⁺ excluded — acid
    # naming is the deferred item-2 follow-up), assembled by verified charge crossover, named by the
    # nomenclature engine, with the own-charge mistake named where it differs. The gate re-derives the name
    # by concatenation, the subscripts by gcd crossover, and the mistake's dishonesty — in pure Node.
    cations = sorted((i for i in data.ions.values() if i.charge > 0 and i.compound_name and i.id != "H^+"),
                     key=lambda i: i.id)
    anions = sorted((i for i in data.ions.values() if i.charge < 0 and i.compound_name), key=lambda i: i.id)
    charge_balance = []
    for cation in cations:
        for anion in anions:
            formula, n_cat, n_an = assemble_formula(cation, anion, ctx="valence-table")
            entry = {
                "cation": cation.id, "anion": anion.id, "cation_n": n_cat, "anion_n": n_an,
                "cation_name": cation.compound_name, "anion_name": anion.compound_name,
                "name": name_ionic(cation, anion, ctx="valence-table"),
                "formula": formula, "latex": parse_formula(formula).latex,
                "note": f"{n_cat}×({_sign(cation.charge)}) + {n_an}×({_sign(anion.charge)}) = 0",
            }
            mistake = _crossover_mistake(cation, anion, formula)
            if mistake is not None:
                entry["mistake"] = mistake
            charge_balance.append(entry)

    # the bonding rule (ADR-0033): sourced ΔEN classes + OpenStax's own caveat, emitted verbatim from
    # data/bonding.toml — the player classifies against these thresholds and never hard-codes a boundary.
    bonding = None
    if data.bonding:
        bonding = {
            "source": data.sources.get("bonding", ""),
            "caution": data.bonding["caution"],
            "classes": [{k: c[k] for k in ("id", "label", "description", "min", "max") if k in c}
                        for c in data.bonding["classes"]],
        }

    table = {
        "kind": "valence-table",
        "id": "valence-table",
        "title": "The Valence Table",
        "blurb": "The periodic table as a charge machine: an element's group sets its common ion charge, and "
                 "a cation and anion combine in whatever ratio makes the compound neutral.",
        "group_charge_note": "Main-group metals lose electrons to a full shell (group 1 → +1, group 2 → +2); "
                             "nonmetals gain them (group 16 → −2, group 17 → −1). Charges below are sourced, "
                             "not inferred — the pattern is a guide, the data is the authority.",
        "highlight": ["Ca", "Na"],
        "elements": elements,
        "polyatomic": polyatomic,
        "lenses": _LENSES,
        "charge_balance": charge_balance,
        "sources": {
            "atomic_weight": data.sources.get("atomic_weight", ""),
            "position": data.sources.get("position", ""),
            "ion_charge": data.sources.get("ion_charge", ""),
            "electronegativity": data.sources.get("electronegativity", ""),
            "covalent_radius": data.sources.get("covalent_radius", ""),
            "ionization_energy": data.sources.get("ionization_energy", ""),
            "bonding": data.sources.get("bonding", ""),
        },
    }
    if bonding is not None:
        table["bonding"] = bonding
    return table


def _sign(charge: int) -> str:
    return f"{'+' if charge > 0 else '−'}{abs(charge)}"


def _core_no_phase(raw: str) -> str:
    return _PHASE_SUFFIX.sub("", raw)


def _side_text(forms, coeffs) -> str:
    return " + ".join((f"{c} " if c != 1 else "") + f.raw for f, c in zip(forms, coeffs))


def _side_latex(forms, coeffs) -> str:
    return " + ".join((f"{c}\\," if c != 1 else "") + f.latex for f, c in zip(forms, coeffs))


def _net_side_text(side: dict) -> str:
    return " + ".join((f"{c} " if c != 1 else "") + (sid + (f"({ph})" if ph else ""))
                      for (sid, ph), c in side.items())


def _net_side_latex(side: dict) -> str:
    parts = []
    for (sid, ph), c in side.items():
        lat = parse_formula(sid).latex
        if ph:
            lat += r"\,\text{(" + ph + ")}"
        parts.append((f"{c}\\," if c != 1 else "") + lat)
    return " + ".join(parts)


def build_reaction_family(spec: dict, data, *, solubility, acidbase, decomposition, ctx: str = "") -> dict:
    """An authored reaction-family entry → the emitted Atlas object (ADR-0035). Each authored example is
    BALANCED BY THE ENGINE and CLASSIFIED — the producer refuses to emit an example that does not classify as
    the entry's declared family, so "this is a precipitation reaction" is machine-verified, not asserted. The
    net-ionic particle view is emitted where spectators actually cancel; the redox flag comes from the
    classifier's free-element signature (ADR-0035). The Node gate re-proves each example's balance + redox."""
    for key in ("id", "kind", "title", "family", "general_form", "summary", "source", "examples",
                "misconceptions"):
        if key not in spec:
            raise BuildError(f"{ctx}: reaction-family entry missing required key '{key}'")
    if spec["kind"] != "reaction-family":
        raise BuildError(f"{ctx}: build_reaction_family got kind '{spec['kind']}'")
    family = spec["family"]

    # TOML trap #4 guard: a top-level bare key authored AFTER an array-of-tables header (`[[examples]]`,
    # `[[misconceptions]]`) is silently absorbed into that table's last element — which is exactly how the
    # item-6 families shipped with empty `related`/`lessons`. An example/misconception carrying an unexpected
    # key is that absorption; fail loud so it can never happen silently again.
    for ex in spec["examples"]:
        extra = set(ex) - {"reactants", "products"}
        if extra:
            raise BuildError(f"{ctx}: reaction-family example carries unexpected key(s) {sorted(extra)} — a "
                             f"top-level bare key was absorbed into the last [[examples]] table (TOML trap: "
                             f"bare keys like related/lessons must precede any array-of-tables header)")
    for m in spec["misconceptions"]:
        extra = set(m) - {"claim", "refute"}
        if extra:
            raise BuildError(f"{ctx}: reaction-family misconception carries unexpected key(s) {sorted(extra)} "
                             f"— a top-level bare key was absorbed into a [[misconceptions]] table")

    examples = []
    redox_flags = []
    for ex in spec["examples"]:
        r_forms = [parse_formula(s, ctx) for s in ex["reactants"]]
        p_forms = [parse_formula(s, ctx) for s in ex["products"]]
        coeffs = balance(r_forms, p_forms, ctx)                    # engine-derived, re-verified (ADR-0014)
        cls = classify_reaction(r_forms, p_forms, data, solubility=solubility, acidbase=acidbase,
                                decomposition=decomposition, ctx=ctx)
        if cls["family"] != family:
            raise BuildError(f"{ctx}: example '{' + '.join(ex['reactants'])} -> {' + '.join(ex['products'])}' "
                             f"classifies as '{cls['family']}', not the declared family '{family}'")
        n_r = len(r_forms)
        cr, cp = coeffs[:n_r], coeffs[n_r:]
        species = []
        for f, role in [(x, "reactant") for x in r_forms] + [(x, "product") for x in p_forms]:
            if f.phase is None:
                raise BuildError(f"{ctx}: reaction-family example species '{f.raw}' needs an explicit phase")
            species.append({"formula": f.raw, "role": role, "counts": dict(f.counts), "charge": f.charge,
                            "phase": f.phase, "latex": f.latex})

        entry = {
            "equation": {"text": _side_text(r_forms, cr) + " -> " + _side_text(p_forms, cp),
                         "latex": _side_latex(r_forms, cr) + r" \rightarrow " + _side_latex(p_forms, cp)},
            "species": species,
            "coefficients": list(coeffs),
            "family": cls["family"],
            "family_label": cls["family_label"],
            "redox": cls["redox"],
            "evidence": cls["evidence"],
        }
        if "redox_reason" in cls:
            entry["redox_reason"] = cls["redox_reason"]

        # the net-ionic particle view, where spectators actually cancel (double/single replacement in
        # solution). Combustion/synthesis/decomposition have nothing to cancel — omitted, not faked.
        spectators: list[str] = []
        try:
            left, right = complete_ionic(r_forms, p_forms, coeffs, data, ctx)
            net_left, net_right, spectators = net_ionic(left, right, ctx)
        except BuildError:
            net_left = None
        if net_left and spectators:
            entry["net_ionic"] = {"text": _net_side_text(net_left) + " -> " + _net_side_text(net_right),
                                  "latex": _net_side_latex(net_left) + r" \rightarrow " + _net_side_latex(net_right)}
            entry["spectators"] = spectators

        tokens = {_core_no_phase(f.raw) for f in r_forms + p_forms
                  if any(ch.isdigit() for ch in f.raw) or "^" in f.raw}
        tokens |= set(spectators)
        if tokens:
            entry["subscript_tokens"] = sorted(tokens)
        redox_flags.append(cls["redox"])
        examples.append(entry)

    out = {
        "kind": "reaction-family",
        "id": spec["id"],
        "title": spec["title"],
        "family": family,
        "general_form": spec["general_form"],
        "summary": spec["summary"],
        "regime": spec.get("regime", "rule-sourced"),
        "source": spec["source"],
        "conditions": spec.get("conditions", []),
        "misconceptions": [{"claim": m["claim"], "refute": m["refute"]} for m in spec["misconceptions"]],
        "examples": examples,
        "related": spec.get("related", []),
        "lessons": spec.get("lessons", []),
    }
    if "general_form_latex" in spec:
        out["general_form_latex"] = spec["general_form_latex"]
    # prose formula tokens for the view (ADR-0025): every example's species tokens, plus any author-declared
    # intermediates that never appear as a species (carbonic acid in gas evolution). The view subscripts only
    # these in the summary/conditions/misconceptions — measurement numbers are never touched.
    prose = {t for ex in examples for t in ex.get("subscript_tokens", [])}
    prose |= set(spec.get("prose_tokens", []))
    out["prose_tokens"] = sorted(prose)
    # a family-level redox flag only when every example agrees (combustion/single-replacement always;
    # precipitation/acid-base/gas-evolution never); omitted for mixed families (some synthesis/decomposition)
    if all(redox_flags):
        out["redox"] = True
    elif not any(redox_flags):
        out["redox"] = False
    return out


def build_species_entry(spec: dict, data, ctx: str = "") -> dict:
    """An authored species entry → the emitted Atlas object (ADR-0038). The composition, signed charge, and
    molar mass are DERIVED from the authored `formula` by the parser + the sourced atomic weights — never
    asserted: "the molar mass of CaCO3 is 100.086 g/mol" follows from re-parsing the formula and summing the
    CIAAW weights (regime-1 arithmetic over regime-3 data). Names, the typical phase, and the prose are
    authored + labeled. The producer refuses a formula that uses an element absent from the dataset, or a
    class/charge mismatch (an "element"/"compound" must be neutral; either ion class must be charged)."""
    for key in ("id", "kind", "title", "formula", "species_class", "names", "summary", "source"):
        if key not in spec:
            raise BuildError(f"{ctx}: species entry missing required key '{key}'")
    if spec["kind"] != "species":
        raise BuildError(f"{ctx}: build_species_entry got kind '{spec['kind']}'")
    if not spec["names"]:
        raise BuildError(f"{ctx}: species entry needs at least one name")

    f = parse_formula(spec["formula"], ctx)
    if f.phase is not None:
        raise BuildError(f"{ctx}: species formula '{spec['formula']}' must be phase-less (phase is a field)")

    # composition + molar mass, both derived from the parsed counts and the sourced atomic weights (exact
    # Decimal, ADR-0013). data.atomic_weight raises for an unknown element, so an off-dataset species fails.
    composition = []
    total = Decimal(0)
    for el, k in f.counts.items():
        aw = data.atomic_weight(el)
        subtotal = aw * k
        total += subtotal
        composition.append({"symbol": el, "count": k, "atomic_weight": str(aw), "subtotal": str(subtotal)})

    cls = spec["species_class"]
    is_ion = cls in ("monatomic-ion", "polyatomic-ion")
    if is_ion and f.charge == 0:
        raise BuildError(f"{ctx}: species_class '{cls}' but formula '{spec['formula']}' is neutral")
    if not is_ion and f.charge != 0:
        raise BuildError(f"{ctx}: species_class '{cls}' but formula '{spec['formula']}' carries charge {f.charge}")
    if cls == "monatomic-ion" and len(f.counts) != 1:
        raise BuildError(f"{ctx}: monatomic-ion '{spec['formula']}' has more than one element")

    entry = {
        "kind": "species",
        "id": spec["id"],
        "title": spec["title"],
        "formula": spec["formula"],
        "latex": f.latex,
        "species_class": cls,
        "names": list(spec["names"]),
        "charge": f.charge,
        "composition": composition,
        "molar_mass_g_per_mol": str(total),
        "summary": spec["summary"],
        "regime": spec.get("regime", "ledger-exact"),
        "source": spec["source"],
        "related": spec.get("related", []),
        "lessons": spec.get("lessons", []),
    }
    if "phase" in spec:
        entry["phase"] = spec["phase"]
    if "notes" in spec:
        entry["notes"] = spec["notes"]
    if "reactions" in spec:
        entry["reactions"] = spec["reactions"]
    return entry


def build_reference_entry(spec: dict, ctx: str = "") -> dict:
    """An authored concept entry → the emitted reference object (the term, definition, edges, lessons)."""
    for key in ("id", "kind", "title", "term", "definition"):
        if key not in spec:
            raise BuildError(f"{ctx}: reference entry missing required key '{key}'")
    if spec["kind"] != "concept":
        raise BuildError(f"{ctx}: unknown reference kind '{spec['kind']}'")
    entry = {
        "kind": "concept",
        "id": spec["id"],
        "title": spec["title"],
        "term": spec["term"],
        "definition": spec["definition"],
        "related": spec.get("related", []),
        "lessons": spec.get("lessons", []),
    }
    if "regime" in spec:
        entry["regime"] = spec["regime"]
    if "source" in spec:
        entry["source"] = spec["source"]
    if "latex" in spec:
        entry["latex"] = spec["latex"]
    # a rule-sourced concept must cite where the rule comes from (the honesty model, ADR-0003)
    if entry.get("regime") == "rule-sourced" and "source" not in entry:
        raise BuildError(f"{ctx}: rule-sourced concept '{entry['id']}' needs a `source`")
    return entry
