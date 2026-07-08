// equilibriumcheck.mjs — re-prove an equilibrium lesson's reversible-extent solve in pure Node (ADR-0048,
// ADR-0008). The ICE table is the species ledger with the extent x solved from MASS ACTION: every equilibrium
// concentration is c_i = c_{i,0} + ν_i·x, and x is the value that makes the reaction quotient Q(x) = K. This
// module re-derives the whole spine independently of the Python engine — the ICE identity, an INDEPENDENT
// bisection re-solve of the root, the residual Q(committed)=K, the pH, and the percent ionization — so CI
// re-verifies the equilibrium with no Python. Shared (like structurecheck.mjs), used by validate-solutions.

// The mass-action reaction quotient Q = ∏ c_i^{ν_i} (ν signed: products multiply, reactants divide via a
// negative power). A species with inQ[i] false is a pure solid (activity 1, excluded from Q — the Ksp case,
// ADR-0048). Every included concentration must be positive (the caller stays on the physical interval).
export function reactionQuotient(concs, nus, inQ) {
  let q = 1;
  for (let i = 0; i < concs.length; i++) {
    if (inQ && !inQ[i]) continue;
    q *= Math.pow(concs[i], nus[i]);
  }
  return q;
}

// Independently solve for the extent x at which Q(x) = K by bisection. Q is strictly increasing in x, so exactly
// one root. A species with in_quotient false (a pure solid) is excluded from Q and, being in excess, does not
// bound the forward extent — so when no quotient reactant limits the forward direction the bracket is grown until
// Q > K (the Ksp dissolution). Node mirror of chemkernel.equilibrium.solve_equilibrium (float64 — ample here).
export function solveEquilibrium(species, K) {
  const nus = species.map((s) => s.nu);
  const c0 = species.map((s) => s.initial);
  const inQ = species.map((s) => s.in_quotient !== false);
  const idx = species.map((_s, i) => i);
  const concsAt = (x) => c0.map((c, i) => c + nus[i] * x);
  const f = (x) => reactionQuotient(concsAt(x), nus, inQ) - K;
  const prodRoom = idx.filter((i) => nus[i] > 0 && inQ[i]).map((i) => c0[i] / nus[i]);
  const rev = prodRoom.length ? Math.min(...prodRoom) : 0;
  const reactRoom = idx.filter((i) => nus[i] < 0 && inQ[i]).map((i) => c0[i] / -nus[i]);
  let lo, hi;
  if (reactRoom.length) {
    const fwd = Math.min(...reactRoom);
    const eps = (fwd + rev) * 1e-15;
    lo = -rev + eps; hi = fwd - eps;
  } else {
    lo = 1e-30; hi = 1;                              // a pure solid dissolving: grow hi until Q > K
    let guard = 0;
    while (f(hi) <= 0 && guard < 400) { hi *= 2; guard++; }
  }
  if (!(f(lo) < 0 && f(hi) > 0)) return { extent: NaN };  // caller flags an unbracketed root
  for (let k = 0; k < 200; k++) {
    const m = (lo + hi) / 2;
    if (f(m) > 0) hi = m; else lo = m;
  }
  const x = (lo + hi) / 2;
  return { extent: x, concs: concsAt(x), quotient: reactionQuotient(concsAt(x), nus, inQ) };
}

// Re-derive + verify one equilibrium lesson (both subtypes — weak-acid pH + Ksp solubility, ADR-0048). `fail(rel,
// msg)` exits the process (the caller's fail).
export function verifyEquilibrium(rel, les, fail) {
  const rc = (g, w, t = 1e-6) => Math.abs(g - w) <= t * Math.abs(w) + 1e-12;
  const ice = les.ice;
  const x = Number(ice.extent_M);
  if (!(x > 0)) fail(rel, `ice.extent_M ${ice.extent_M} is not positive (extent physical)`);

  // a row with in_quotient false is a pure solid (activity 1) — no concentration, excluded from Q. Others carry
  // concentrations and enter Q. Keep the emitted in_quotient flag so the re-solve matches the producer.
  const species = ice.species.map((s) => ({
    id: s.id, nu: s.nu, role: s.role, in_quotient: s.in_quotient !== false,
    initial: Number(s.initial_M), equilibrium: Number(s.equilibrium_M), change: Number(s.change_M),
  }));
  if (!species.some((s) => s.nu < 0)) fail(rel, "no reactant (ν<0) in the ICE table");
  if (!species.some((s) => s.nu > 0 && s.in_quotient)) fail(rel, "no product in the quotient (ν>0)");

  // 1. the ICE identity, re-derived for each DISSOLVED row: equilibrium = initial + ν·x, change = ν·x; roles
  // agree with the ν signs. A pure-solid row (in_quotient false) has no concentration — only its role/ν is checked.
  for (const s of species) {
    if ((s.nu > 0) !== (s.role === "product"))
      fail(rel, `${s.id}: role ${s.role} disagrees with ν sign ${s.nu}`);
    if (!s.in_quotient) continue;                 // the pure solid carries no concentration to re-derive
    if (!rc(s.equilibrium, s.initial + s.nu * x))
      fail(rel, `${s.id}: equilibrium_M ${s.equilibrium} != initial + ν·x = ${(s.initial + s.nu * x)}`);
    if (!rc(s.change, s.nu * x))
      fail(rel, `${s.id}: change_M ${s.change} != ν·x = ${s.nu * x}`);
    if (s.equilibrium < 0) fail(rel, `${s.id}: equilibrium concentration is negative`);
  }

  const K = Number(les.equilibrium_constant.value);
  if (!(K > 0)) fail(rel, `equilibrium constant ${les.equilibrium_constant.value} is not positive`);

  // 2. INDEPENDENT re-solve of the mass-action root matches the committed extent (the reversible-extent solve —
  // the same machine handles the weak-acid quadratic AND the Ksp cubic, the solid excluded from Q)
  const solve = solveEquilibrium(species.map((s) => ({ nu: s.nu, initial: s.initial, in_quotient: s.in_quotient })), K);
  if (Number.isNaN(solve.extent)) fail(rel, "mass-action root not bracketed on re-solve");
  if (!rc(x, solve.extent, 1e-4))
    fail(rel, `ice.extent_M ${ice.extent_M} != independently re-solved root ${solve.extent} (Q=K)`);

  // 3. mass action satisfied: Q at the COMMITTED concentrations (the solid excluded) reproduces K — the residual
  // is the machine-check (a reader can plug the table back in and get K). The emitted quotient + residual agree.
  const concs = species.map((s) => s.equilibrium), nus = species.map((s) => s.nu), inQ = species.map((s) => s.in_quotient);
  const Qc = reactionQuotient(concs, nus, inQ);
  if (!rc(Qc, K, 1e-5)) fail(rel, `Q at the committed concentrations ${Qc} != K ${K}`);
  if (!rc(Number(les.mass_action.quotient_at_equilibrium), K, 1e-3))
    fail(rel, `mass_action.quotient_at_equilibrium ${les.mass_action.quotient_at_equilibrium} != K ${K}`);
  const residual = Math.abs(Qc - K) / K;
  if (residual > 1e-5) fail(rel, `residual |Q-K|/K = ${residual} is too large — the extent does not satisfy mass action`);

  // 4. the subtype-specific reported results.
  if (les.subtype === "weak-acid") {
    // [H⁺] is the hydronium row's equilibrium concentration; pH = −log₁₀[H⁺]; percent ionization = x / [HA]₀ × 100
    const hplus = species.find((s) => s.id === "H^+");
    if (!hplus) fail(rel, "no H^+ row — a weak-acid equilibrium must produce hydronium");
    if (!rc(Number(les.result.hydronium_M), hplus.equilibrium))
      fail(rel, `result.hydronium_M ${les.result.hydronium_M} != H^+ equilibrium ${hplus.equilibrium}`);
    const pH = -Math.log10(hplus.equilibrium);
    if (Math.abs(pH - Number(les.result.pH)) > 1e-3)
      fail(rel, `result.pH ${les.result.pH} != -log10[H+] = ${pH.toFixed(6)}`);
    const acid = species.find((s) => s.nu < 0);
    const percent = (x / acid.initial) * 100;
    if (!rc(percent, Number(les.result.percent_ionization), 1e-3))
      fail(rel, `result.percent_ionization ${les.result.percent_ionization} != x/[HA]0·100 = ${percent.toFixed(6)}`);
  } else if (les.subtype === "buffer") {
    // a buffer is the weak-acid equilibrium with the conjugate base A⁻ ALREADY present ([A⁻]₀ > 0). [H⁺] = the
    // H^+ row's equilibrium; pH = −log₁₀[H⁺]. The signature is Henderson–Hasselbalch, pH = pKₐ + log₁₀([A⁻]/[HA])
    // on the EQUILIBRIUM concentrations — which is just the mass-action law logged, so it must reproduce −log₁₀[H⁺].
    const hplus = species.find((s) => s.id === "H^+");
    const acid = species.find((s) => s.nu < 0);
    const conj = species.find((s) => s.nu > 0 && s.id !== "H^+");
    if (!hplus || !acid || !conj) fail(rel, "a buffer needs H^+, a weak-acid reactant, and its conjugate base");
    if (!(conj.initial > 0)) fail(rel, `buffer conjugate base [A⁻]₀ ${conj.initial} is not > 0 (that is a plain weak acid, not a buffer)`);
    if (!rc(Number(les.result.hydronium_M), hplus.equilibrium))
      fail(rel, `result.hydronium_M ${les.result.hydronium_M} != H^+ equilibrium ${hplus.equilibrium}`);
    const pH = -Math.log10(hplus.equilibrium);
    if (Math.abs(pH - Number(les.result.pH)) > 1e-3) fail(rel, `result.pH ${les.result.pH} != -log10[H+] = ${pH.toFixed(6)}`);
    const pKa = -Math.log10(K);
    if (Math.abs(pKa - Number(les.result.pKa)) > 1e-3) fail(rel, `result.pKa ${les.result.pKa} != -log10(Ka) = ${pKa.toFixed(6)}`);
    const ratio = conj.equilibrium / acid.equilibrium;      // equilibrium [A⁻]/[HA]
    if (!rc(ratio, Number(les.result.buffer_ratio), 1e-4))
      fail(rel, `result.buffer_ratio ${les.result.buffer_ratio} != [A⁻]/[HA] = ${ratio}`);
    const hhpH = pKa + Math.log10(ratio);                   // Henderson–Hasselbalch on equilibrium concentrations
    if (Math.abs(hhpH - pH) > 1e-3) fail(rel, `Henderson–Hasselbalch pH ${hhpH.toFixed(6)} != -log10[H+] ${pH.toFixed(6)} (hh_consistent)`);
    if (Math.abs(hhpH - Number(les.result.hh_pH)) > 1e-3) fail(rel, `result.hh_pH ${les.result.hh_pH} != pKa+log10([A⁻]/[HA]) = ${hhpH.toFixed(6)}`);
    // the common-ion contrast: re-solve the ACID ALONE ([A⁻]₀ = 0) — the pure weak-acid pH the misconception assumes
    const alone = [{ nu: acid.nu, initial: acid.initial, in_quotient: true },
                   { nu: 1, initial: 0, in_quotient: true }, { nu: 1, initial: 0, in_quotient: true }];
    const solo = solveEquilibrium(alone, K);
    if (Number.isNaN(solo.extent)) fail(rel, "no-buffer (acid-alone) re-solve not bracketed");
    if (!rc(Number(les.result.hydronium_no_buffer_M), solo.extent, 1e-4))
      fail(rel, `result.hydronium_no_buffer_M ${les.result.hydronium_no_buffer_M} != acid-alone [H+] ${solo.extent}`);
    const pH0 = -Math.log10(solo.extent);
    if (Math.abs(pH0 - Number(les.result.pH_no_buffer)) > 1e-3)
      fail(rel, `result.pH_no_buffer ${les.result.pH_no_buffer} != -log10[H+]_alone = ${pH0.toFixed(6)}`);
    const suppression = solo.extent / hplus.equilibrium;
    if (!rc(suppression, Number(les.result.suppression_factor_display), 5e-3))
      fail(rel, `result.suppression_factor_display ${les.result.suppression_factor_display} != x_alone/x = ${suppression}`);
    const percent = (x / acid.initial) * 100;
    if (!rc(percent, Number(les.result.percent_ionization), 1e-3))
      fail(rel, `result.percent_ionization ${les.result.percent_ionization} != x/[HA]0·100 = ${percent.toFixed(6)}`);
  } else if (les.subtype === "weak-base") {
    // [OH⁻] is the hydroxide row's equilibrium concentration (= x); pOH = −log₁₀[OH⁻]. The K_w BRIDGE: [H⁺] =
    // K_w/[OH⁻] → pH = −log₁₀[H⁺], and pH + pOH must equal pK_w. Water is the excluded (in_quotient false) row.
    const oh = species.find((s) => s.id === "OH^-");
    if (!oh) fail(rel, "no OH^- row — a weak-base equilibrium must produce hydroxide");
    if (!rc(Number(les.result.hydroxide_M), oh.equilibrium))
      fail(rel, `result.hydroxide_M ${les.result.hydroxide_M} != OH^- equilibrium ${oh.equilibrium}`);
    const solvent = species.filter((s) => !s.in_quotient);
    if (solvent.length !== 1 || solvent[0].nu >= 0)
      fail(rel, "a weak-base equilibrium needs exactly one pure-solvent reactant row (water, in_quotient false, ν<0)");
    const Kw = Number(les.result.kw);
    if (!(Kw > 0)) fail(rel, `result.kw ${les.result.kw} is not positive`);
    const pOH = -Math.log10(oh.equilibrium);
    if (Math.abs(pOH - Number(les.result.pOH)) > 1e-3)
      fail(rel, `result.pOH ${les.result.pOH} != -log10[OH-] = ${pOH.toFixed(6)}`);
    const hplus = Kw / oh.equilibrium;               // the K_w bridge, re-derived
    if (!rc(Number(les.result.hydronium_M), hplus, 1e-4))
      fail(rel, `result.hydronium_M ${les.result.hydronium_M} != Kw/[OH-] = ${hplus}`);
    const pH = -Math.log10(hplus);
    if (Math.abs(pH - Number(les.result.pH)) > 1e-3)
      fail(rel, `result.pH ${les.result.pH} != -log10(Kw/[OH-]) = ${pH.toFixed(6)}`);
    const pKw = -Math.log10(Kw);
    if (Math.abs(pH + pOH - pKw) > 1e-3)
      fail(rel, `pH + pOH = ${(pH + pOH).toFixed(4)} != pKw = ${pKw.toFixed(4)} (the K_w bridge)`);
    const base = species.find((s) => s.nu < 0 && s.in_quotient);
    const percent = (x / base.initial) * 100;
    if (!rc(percent, Number(les.result.percent_ionization), 1e-3))
      fail(rel, `result.percent_ionization ${les.result.percent_ionization} != x/[B]0·100 = ${percent.toFixed(6)}`);
  } else if (les.subtype === "solubility") {
    // the molar solubility IS the extent; solubility(g/L) = s × molar mass. Exactly one solid row, excluded from Q.
    const solids = species.filter((s) => !s.in_quotient);
    if (solids.length !== 1 || solids[0].nu >= 0) fail(rel, "a solubility lesson needs exactly one pure-solid reactant row (in_quotient false, ν<0)");
    if (!rc(Number(les.result.molar_solubility_M), x))
      fail(rel, `result.molar_solubility_M ${les.result.molar_solubility_M} != extent ${x}`);
    const gPerL = x * Number(les.result.molar_mass_g_per_mol);
    if (!rc(gPerL, Number(les.result.solubility_g_per_L), 1e-4))
      fail(rel, `result.solubility_g_per_L ${les.result.solubility_g_per_L} != s × molar mass = ${gPerL}`);
  } else {
    fail(rel, `unknown equilibrium subtype '${les.subtype}'`);
  }
}
