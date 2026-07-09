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

// pH at one point of a weak-acid/strong-base titration, by region — the Node mirror of equilibrium._titration_point.
// n = C·V (the units cancel in the ratios). Region is recomputed from the volume (a tolerance so the exact
// equivalence point is caught in float), so a tampered region label is rejected.
export function titrationPh(cAcid, vAcid, cBase, vBase, ka, kw) {
  const nAcid = cAcid * vAcid, nBase = cBase * vBase, vTot = vAcid + vBase;
  const tol = 1e-9 * nAcid;
  let hplus, region;
  if (nBase < nAcid - tol) {
    const ha0 = (nAcid - nBase) / vTot, a0 = nBase / vTot;
    const sol = solveEquilibrium([{ nu: -1, initial: ha0 }, { nu: 1, initial: 0 }, { nu: 1, initial: a0 }], ka);
    hplus = sol.extent; region = nBase === 0 ? "initial" : "buffer";
  } else if (nBase <= nAcid + tol) {
    const a0 = nAcid / vTot, kb = kw / ka;
    const sol = solveEquilibrium([{ nu: -1, initial: a0 }, { nu: -1, initial: 0, in_quotient: false },
                                  { nu: 1, initial: 0 }, { nu: 1, initial: 0 }], kb);
    hplus = kw / sol.extent; region = "equivalence";
  } else {
    hplus = kw / ((nBase - nAcid) / vTot); region = "excess-base";
  }
  return { pH: -Math.log10(hplus), region, hplus };
}

// Re-derive + verify one equilibrium lesson (all six subtypes — weak-acid pH, buffer, weak-base pH, Ksp
// solubility incl. the common-ion variant, polyprotic staged ionization, and a titration curve, ADR-0048).
// `fail(rel, msg)` exits.
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
    // the common-ion variant: one of the salt's ions is ALREADY present (a nonzero initial product — the core
    // re-solve above already accounts for it). Re-check the ion's initial matches the reaction block, and re-solve
    // the salt in PURE water (both ions at 0) to reproduce the suppression contrast the misconception denies.
    if (les.reaction.common_ion) {
      const commonRow = species.find((s) => s.id === les.reaction.common_ion);
      if (!commonRow || !(commonRow.nu > 0)) fail(rel, `common ion ${les.reaction.common_ion} is not a product ion of the salt`);
      if (!(commonRow.initial > 0)) fail(rel, `common ion ${les.reaction.common_ion} initial ${commonRow.initial} is not > 0 (that is plain solubility, not a common-ion lesson)`);
      if (!rc(commonRow.initial, Number(les.reaction.common_ion_molarity_M)))
        fail(rel, `common ion initial ${commonRow.initial} != reaction.common_ion_molarity_M ${les.reaction.common_ion_molarity_M}`);
      const pure = species.map((s) => ({ nu: s.nu, initial: 0, in_quotient: s.in_quotient }));
      const solo = solveEquilibrium(pure, K);
      if (Number.isNaN(solo.extent)) fail(rel, "pure-water (no common ion) re-solve not bracketed");
      if (!rc(Number(les.result.molar_solubility_pure_water_M), solo.extent, 1e-4))
        fail(rel, `result.molar_solubility_pure_water_M ${les.result.molar_solubility_pure_water_M} != pure-water s ${solo.extent}`);
      const suppression = solo.extent / x;                  // s(pure water) / s(with common ion) — many-fold
      if (!rc(suppression, Number(les.result.suppression_factor_display), 5e-3))
        fail(rel, `result.suppression_factor_display ${les.result.suppression_factor_display} != s_pure/s = ${suppression}`);
    }
  } else if (les.subtype === "polyprotic") {
    // the top-level ice IS stage 1 (already re-solved above). Walk result.later_stages, each an independent
    // re-solve on the PREVIOUS stage's equilibrium concentrations (the successive treatment), and re-derive the
    // accumulated [H+], the pH, and the species ladder — so the "each Ka is 10^5 smaller, so later stages barely
    // move [H+]" payoff is re-proven, not asserted.
    const r = les.result;
    const acid = species.find((s) => s.nu < 0);
    const hplus1 = species.find((s) => s.id === "H^+");
    const anion1 = species.find((s) => s.nu > 0 && s.id !== "H^+");
    if (!acid || !hplus1 || !anion1) fail(rel, "polyprotic stage 1 needs a reactant acid, H^+, and its conjugate base");
    const c0 = acid.initial;
    const xs = [x];                                   // x = stage-1 extent (top-level ice)
    let prevReactantEqm = anion1.equilibrium;         // stage 2's reactant is stage 1's anion
    let prevHydronium = hplus1.equilibrium;           // the running [H+]
    for (const st of (r.later_stages || [])) {
      if (!rc(Number(st.initial_reactant_M), prevReactantEqm, 1e-4))
        fail(rel, `stage ${st.index}: initial_reactant_M ${st.initial_reactant_M} != previous anion equilibrium ${prevReactantEqm}`);
      if (!rc(Number(st.initial_hydronium_M), prevHydronium, 1e-4))
        fail(rel, `stage ${st.index}: initial_hydronium_M ${st.initial_hydronium_M} != running [H+] ${prevHydronium}`);
      if (Number(st.initial_anion_M) !== 0) fail(rel, `stage ${st.index}: initial_anion_M must start at 0`);
      const ka = Number(st.ka_value);
      if (!(ka > 0)) fail(rel, `stage ${st.index}: ka_value ${st.ka_value} not positive`);
      const sys = [{ nu: -1, initial: Number(st.initial_reactant_M), in_quotient: true },
                   { nu: 1, initial: Number(st.initial_hydronium_M), in_quotient: true },
                   { nu: 1, initial: 0, in_quotient: true }];
      const sol = solveEquilibrium(sys, ka);
      const xj = Number(st.extent_M);
      if (Number.isNaN(sol.extent)) fail(rel, `stage ${st.index}: root not bracketed on re-solve`);
      if (!rc(xj, sol.extent, 1e-3)) fail(rel, `stage ${st.index}: extent_M ${st.extent_M} != re-solved ${sol.extent}`);
      const reEq = Number(st.initial_reactant_M) - xj, hEq = Number(st.initial_hydronium_M) + xj, anEq = xj;
      const Q = (hEq * anEq) / reEq;                  // [H+][anion]/[reactant]
      if (!rc(Q, ka, 1e-4)) fail(rel, `stage ${st.index}: Q ${Q} != Ka ${ka}`);
      if (!rc(Number(st.anion_equilibrium_M), anEq, 1e-4)) fail(rel, `stage ${st.index}: anion_equilibrium_M != initial_anion + x`);
      xs.push(xj);
      prevReactantEqm = anEq;                          // this stage's anion feeds the next stage
      prevHydronium = hEq;
    }
    const hplusTotal = xs.reduce((a, b) => a + b, 0);  // [H+] accumulates across the stages
    if (!rc(Number(r.hydronium_M), hplusTotal, 1e-4)) fail(rel, `result.hydronium_M ${r.hydronium_M} != Σ stage extents ${hplusTotal}`);
    const pH = -Math.log10(hplusTotal);
    if (Math.abs(pH - Number(r.pH)) > 1e-3) fail(rel, `result.pH ${r.pH} != -log10[H+] = ${pH.toFixed(6)}`);
    const percent = (x / c0) * 100;
    if (!rc(percent, Number(r.percent_ionization), 1e-3)) fail(rel, `result.percent_ionization ${r.percent_ionization} != x1/c0·100 = ${percent}`);
    // the species ladder: [acid] = c0 − x1; [anion_k] = x_k − x_{k+1}; [last anion] = x_last
    const ladder = r.species_ladder || [], N = xs.length;
    if (ladder.length !== N + 1) fail(rel, `species_ladder length ${ladder.length} != acid + ${N} anions`);
    const expected = [c0 - xs[0]];
    for (let k = 0; k < N; k++) expected.push(k < N - 1 ? xs[k] - xs[k + 1] : xs[k]);
    for (let k = 0; k < ladder.length; k++)
      if (!rc(Number(ladder[k].equilibrium_M), expected[k], 1e-3))
        fail(rel, `species_ladder[${k}] ${ladder[k].id} = ${ladder[k].equilibrium_M} != expected ${expected[k]}`);
  } else if (les.subtype === "titration") {
    // the top-level ice is the INITIAL point (already re-solved by the core above). Recompute the WHOLE curve
    // independently — every point's region + pH from the titrant/acid inputs + Kₐ + K_w — and re-check the three
    // landmarks (half-equivalence pH = pKₐ; equivalence basic; initial = result.pH).
    const t = les.titration;
    if (!t) fail(rel, "titration lesson missing the `titration` block");
    const cAcid = Number(t.acid_molarity_M), vAcid = Number(t.acid_volume_mL), cBase = Number(t.titrant_molarity_M);
    const kw = Number(t.kw), Ka = K;                    // K = the acid's Kₐ (equilibrium_constant.value)
    if (!(cAcid > 0 && vAcid > 0 && cBase > 0 && kw > 0)) fail(rel, "titration inputs must be positive");
    const vEq = (cAcid * vAcid) / cBase;
    if (!rc(vEq, Number(t.equivalence_volume_mL), 1e-4)) fail(rel, `equivalence_volume_mL ${t.equivalence_volume_mL} != c_a·v_a/c_b = ${vEq}`);
    if (!rc(vEq / 2, Number(t.half_equivalence_volume_mL), 1e-4)) fail(rel, `half_equivalence_volume_mL ${t.half_equivalence_volume_mL} != V_eq/2`);
    const pKa = -Math.log10(Ka);
    if (Math.abs(pKa - Number(t.pKa)) > 1e-3) fail(rel, `titration pKa ${t.pKa} != -log10(Kₐ) = ${pKa.toFixed(4)}`);
    if (!(t.curve.length >= 3)) fail(rel, "titration curve needs ≥ 3 points");
    for (const p of t.curve) {                          // recompute every point, region + pH
      const got = titrationPh(cAcid, vAcid, cBase, Number(p.volume_mL), Ka, kw);
      if (got.region !== p.region) fail(rel, `curve V=${p.volume_mL}: region '${p.region}' != recomputed '${got.region}'`);
      if (Math.abs(got.pH - Number(p.pH)) > 5e-3) fail(rel, `curve V=${p.volume_mL}: pH ${p.pH} != recomputed ${got.pH.toFixed(4)}`);
      if (!rc(Number(p.hydronium_M), got.hplus, 5e-3)) fail(rel, `curve V=${p.volume_mL}: hydronium_M ${p.hydronium_M} != recomputed ${got.hplus}`);
    }
    const lm = t.landmarks;
    const half = titrationPh(cAcid, vAcid, cBase, Number(lm.half_equivalence.volume_mL), Ka, kw);
    if (Math.abs(half.pH - pKa) > 0.05) fail(rel, `half-equivalence pH ${half.pH.toFixed(3)} not ≈ pKₐ ${pKa.toFixed(3)} — the defining buffer landmark`);
    if (Math.abs(half.pH - Number(lm.half_equivalence.pH)) > 5e-3) fail(rel, `half_equivalence landmark pH ${lm.half_equivalence.pH} != recomputed ${half.pH.toFixed(4)}`);
    const eq = titrationPh(cAcid, vAcid, cBase, Number(lm.equivalence.volume_mL), Ka, kw);
    if (!(eq.pH > 7)) fail(rel, `equivalence pH ${eq.pH.toFixed(3)} is not basic (>7) — a weak acid + strong base is basic at equivalence`);
    if (eq.region !== "equivalence") fail(rel, `equivalence landmark is region '${eq.region}', not equivalence`);
    if (Math.abs(eq.pH - Number(lm.equivalence.pH)) > 5e-3) fail(rel, `equivalence landmark pH ${lm.equivalence.pH} != recomputed ${eq.pH.toFixed(4)}`);
    if (Math.abs(Number(lm.initial.pH) - Number(les.result.pH)) > 1e-6) fail(rel, `result.pH ${les.result.pH} != initial landmark pH ${lm.initial.pH}`);
  } else {
    fail(rel, `unknown equilibrium subtype '${les.subtype}'`);
  }
}
