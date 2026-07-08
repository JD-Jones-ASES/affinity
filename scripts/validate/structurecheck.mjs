// structurecheck.mjs — the shared pure-Node re-derivation of a Lewis ELECTRON ledger (ADR-0044/0045). This is
// the Node counterpart of chemkernel.structure.compute_ledger: given a molecule object (the `molecule` Atlas
// entry OR a structure lesson's embedded molecule block — identical structural shape), it RE-DERIVES the whole
// accounting from the exact formula + authored atoms/bonds and fails loud on any mismatch. One engine, called
// by both validate-reference.mjs (the molecule Atlas kind) and validate-solutions.mjs (the structure lesson) —
// so a structure lesson's electron ledger stands on its own re-proof, exactly as the Atlas entry's does.
//
// It re-checks: composition vs. the formula, the valence total (Σ group electrons − charge, from the sourced
// valence-table counts) and its breakdown, each bond's ΔEN (from the sourced electronegativities) + class (the
// sourced thresholds), electron conservation, every atom's octet/duet + formal charge (and their sum = charge),
// the VSEPR domain count, and polarity present-iff-neutral. The geometry NAMES are the sourced convention; the
// domain COUNT that keys them is re-derived here.

import { parseFormula } from "./formula.mjs";

// classify a bond's ΔEN against the Valence Table's sourced ΔEN thresholds (ADR-0033/0044) — half-open
// [min, max), so ΔEN 0.4 exactly is polar covalent.
export function classifyBond(delta, vt) {
  for (const c of vt?.bonding?.classes ?? []) {
    const lo = c.min != null ? Number(c.min) : null;
    const hi = c.max != null ? Number(c.max) : null;
    if ((lo === null || delta >= lo) && (hi === null || delta < hi)) return c.id;
  }
  return "(unclassified)";
}

// Re-derive + verify a molecule's electron ledger. `mol` carries formula/charge/atoms/bonds/geometry/
// valence_electrons/valence_breakdown/electron_check (the shared shape). `tables` = { valenceE, electroneg, vt }
// built from the emitted valence-table.json. `fail(rel, msg)` reports and exits. Returns nothing.
export function verifyElectronLedger(rel, mol, { valenceE, electroneg, vt }, fail) {
  // re-parse the formula: charge reproduces, and the authored atoms reproduce its composition
  let parsed;
  try { parsed = parseFormula(mol.formula); }
  catch (e) { fail(rel, `formula '${mol.formula}' does not parse: ${e.message}`); }
  if (parsed.charge !== mol.charge) fail(rel, `charge ${mol.charge} != re-parsed ${parsed.charge}`);
  const elementOf = new Map();
  const lonePairs = new Map();
  const structCounts = {};
  for (const a of mol.atoms) {
    if (elementOf.has(a.id)) fail(rel, `duplicate atom id '${a.id}'`);
    elementOf.set(a.id, a.element);
    lonePairs.set(a.id, a.lone_pairs);
    structCounts[a.element] = (structCounts[a.element] ?? 0) + 1;
  }
  for (const el of new Set([...Object.keys(parsed.counts), ...Object.keys(structCounts)]))
    if (parsed.counts[el] !== structCounts[el])
      fail(rel, `atom count for '${el}' is ${structCounts[el] ?? "absent"} but the formula parses to ${parsed.counts[el] ?? "absent"}`);

  // valence total = Σ group valence electrons − charge (re-derived from the table's counts)
  let valence = 0;
  for (const a of mol.atoms) {
    const ve = valenceE.get(a.element);
    if (ve === undefined) fail(rel, `element '${a.element}' has no valence-electron count in the Valence Table`);
    valence += ve;
  }
  valence -= mol.charge;
  if (valence !== mol.valence_electrons) fail(rel, `valence_electrons ${mol.valence_electrons} != re-derived ${valence}`);
  // the per-element breakdown must re-sum to it (per_atom = the sourced count, subtotal = per_atom × count)
  let bdVal = 0;
  for (const b of mol.valence_breakdown) {
    if (valenceE.get(b.symbol) !== b.per_atom) fail(rel, `${b.symbol}: per_atom ${b.per_atom} != table ${valenceE.get(b.symbol)}`);
    if (b.subtotal !== b.per_atom * b.count) fail(rel, `${b.symbol}: subtotal ${b.subtotal} != per_atom × count`);
    bdVal += b.subtotal;
  }
  if (bdVal - mol.charge !== valence) fail(rel, `valence_breakdown Σ ${bdVal} − charge ${mol.charge} != ${valence}`);

  // re-accumulate per-atom bond-order totals + neighbour (domain) counts from the bond list
  const orderSum = new Map(mol.atoms.map((a) => [a.id, 0]));
  const neighbours = new Map(mol.atoms.map((a) => [a.id, 0]));
  for (const bd of mol.bonds) {
    if (!elementOf.has(bd.a) || !elementOf.has(bd.b)) fail(rel, `bond references unknown atom(s) '${bd.a}'/'${bd.b}'`);
    if (bd.a === bd.b) fail(rel, `bond from atom '${bd.a}' to itself`);
    orderSum.set(bd.a, orderSum.get(bd.a) + bd.order);
    orderSum.set(bd.b, orderSum.get(bd.b) + bd.order);
    neighbours.set(bd.a, neighbours.get(bd.a) + 1);
    neighbours.set(bd.b, neighbours.get(bd.b) + 1);
    // bond ΔEN re-derives from the sourced electronegativities; re-classify against the sourced thresholds
    const ea = electroneg.get(elementOf.get(bd.a)), eb = electroneg.get(elementOf.get(bd.b));
    if (ea === undefined || eb === undefined) fail(rel, `bond '${bd.a}-${bd.b}' element has no electronegativity`);
    const delta = Math.abs(ea - eb);
    if (Math.abs(delta - Number(bd.delta_en)) > 1e-9) fail(rel, `bond '${bd.a}-${bd.b}' ΔEN '${bd.delta_en}' != re-derived ${delta}`);
    const wantClass = classifyBond(delta, vt);
    if (bd.bond_class !== wantClass) fail(rel, `bond '${bd.a}-${bd.b}' class '${bd.bond_class}' != re-derived '${wantClass}'`);
    if (bd.polar !== (bd.bond_class !== "nonpolar-covalent")) fail(rel, `bond '${bd.a}-${bd.b}' polar flag disagrees with its class`);
    const want = [elementOf.get(bd.a), elementOf.get(bd.b)].sort();
    if (bd.between[0] !== want[0] || bd.between[1] !== want[1]) fail(rel, `bond '${bd.a}-${bd.b}' between [${bd.between}] != [${want}]`);
  }

  // electron conservation: Σ bond-order electrons (2·order, summed as orderSum totals) + Σ 2·lone_pairs = V
  let bondingE = 0, nonbondingE = 0, fcSum = 0;
  for (const a of mol.atoms) {
    const os = orderSum.get(a.id);
    if (a.bond_order_sum !== os) fail(rel, `atom '${a.id}' bond_order_sum ${a.bond_order_sum} != re-derived ${os}`);
    const target = a.element === "H" ? 2 : 8;
    const shell = 2 * os + 2 * a.lone_pairs;
    if (shell !== target) fail(rel, `atom '${a.id}' (${a.element}) shell ${shell} != completed ${target === 2 ? "duet" : "octet"} (${target})`);
    const ve = valenceE.get(a.element);
    const fc = ve - 2 * a.lone_pairs - os;
    if (a.formal_charge !== fc) fail(rel, `atom '${a.id}' formal_charge ${a.formal_charge} != re-derived ${fc}`);
    bondingE += os;                 // Σ over atoms of order = 2·Σ(bond order) = the bonding electrons
    nonbondingE += 2 * a.lone_pairs;
    fcSum += fc;
  }
  if (bondingE + nonbondingE !== valence)
    fail(rel, `electrons not conserved — ${bondingE} bonding + ${nonbondingE} nonbonding != ${valence} valence`);
  if (mol.electron_check.bonding !== bondingE || mol.electron_check.nonbonding !== nonbondingE || mol.electron_check.total !== bondingE + nonbondingE)
    fail(rel, `electron_check ${JSON.stringify(mol.electron_check)} != re-derived {bonding:${bondingE}, nonbonding:${nonbondingE}, total:${bondingE + nonbondingE}}`);
  if (fcSum !== mol.charge) fail(rel, `formal charges sum to ${fcSum}, not the molecular charge ${mol.charge}`);

  // the VSEPR domain count (bonded neighbours + lone pairs on the central atom) keys the sourced geometry
  const g = mol.geometry;
  if (!elementOf.has(g.central)) fail(rel, `geometry central '${g.central}' is not an atom`);
  if (g.central_element !== elementOf.get(g.central)) fail(rel, `geometry central_element '${g.central_element}' != '${elementOf.get(g.central)}'`);
  const domains = neighbours.get(g.central) + lonePairs.get(g.central);
  if (g.domains !== domains) fail(rel, `geometry domains ${g.domains} != re-derived ${domains}`);
  if (g.lone_pairs !== lonePairs.get(g.central)) fail(rel, `geometry lone_pairs ${g.lone_pairs} != central's ${lonePairs.get(g.central)}`);

  // polarity is authored + model-assumed: present iff the species is neutral (a charged ion carries a charge, not a dipole)
  if (mol.charge === 0 && mol.polarity === undefined) fail(rel, `neutral molecule states no polarity`);
  if (mol.charge !== 0 && mol.polarity !== undefined) fail(rel, `charged species must not state a molecular polarity`);
  if (mol.polarity !== undefined && !mol.polarity_reason) fail(rel, `polarity stated without a polarity_reason`);
}

// Build the { valenceE, electroneg } lookup Maps from an emitted valence-table.json object — one source of
// truth for both gates (as species molar masses re-sum the same table's weights, ADR-0038).
export function ledgerTables(vt) {
  return {
    valenceE: new Map((vt?.elements ?? []).filter((e) => e.valence_electrons != null).map((e) => [e.symbol, e.valence_electrons])),
    electroneg: new Map((vt?.elements ?? []).filter((e) => e.electronegativity != null).map((e) => [e.symbol, Number(e.electronegativity)])),
    vt,
  };
}
