// equilibriumcheck.mjs — re-prove an equilibrium lesson's reversible-extent solve in pure Node (ADR-0048,
// ADR-0008). The ICE table is the species ledger with the extent x solved from MASS ACTION: every equilibrium
// concentration is c_i = c_{i,0} + ν_i·x, and x is the value that makes the reaction quotient Q(x) = K. This
// module re-derives the whole spine independently of the Python engine — the ICE identity, an INDEPENDENT
// bisection re-solve of the root, the residual Q(committed)=K, the pH, and the percent ionization — so CI
// re-verifies the equilibrium with no Python. Shared (like structurecheck.mjs), used by validate-solutions.

// The mass-action reaction quotient Q = ∏ c_i^{ν_i} (ν signed: products multiply, reactants divide via a
// negative power). Every concentration must be positive (the caller stays on the physical interval).
export function reactionQuotient(concs, nus) {
  let q = 1;
  for (let i = 0; i < concs.length; i++) q *= Math.pow(concs[i], nus[i]);
  return q;
}

// Independently solve for the extent x at which Q(x) = K, by bisection over the physical interval
// (−rev_limit, +fwd_limit) — a reactant hits 0 at x=fwd_limit, a product at x=−rev_limit. Q is strictly
// increasing across it, so exactly one root. This is the Node mirror of chemkernel.equilibrium.solve_equilibrium
// (float64 here — ample against 12-significant-figure committed values).
export function solveEquilibrium(species, K) {
  const nus = species.map((s) => s.nu);
  const c0 = species.map((s) => s.initial);
  const idx = species.map((_s, i) => i);
  const fwd = Math.min(...idx.filter((i) => nus[i] < 0).map((i) => c0[i] / -nus[i]));
  const prodRoom = idx.filter((i) => nus[i] > 0).map((i) => c0[i] / nus[i]);
  const rev = prodRoom.length ? Math.min(...prodRoom) : 0;
  const span = fwd + rev;
  const eps = span * 1e-15;
  let lo = -rev + eps, hi = fwd - eps;
  const concsAt = (x) => c0.map((c, i) => c + nus[i] * x);
  const f = (x) => reactionQuotient(concsAt(x), nus) - K;
  if (!(f(lo) < 0 && f(hi) > 0)) return { extent: NaN, fwd, rev };  // caller flags an unbracketed root
  for (let k = 0; k < 200; k++) {
    const m = (lo + hi) / 2;
    if (f(m) > 0) hi = m; else lo = m;
  }
  const x = (lo + hi) / 2;
  return { extent: x, fwd, rev, concs: concsAt(x), quotient: reactionQuotient(concsAt(x), nus) };
}

// Re-derive + verify one equilibrium lesson. `fail(rel, msg)` exits the process (the caller's fail).
export function verifyEquilibrium(rel, les, fail) {
  const rc = (g, w, t = 1e-6) => Math.abs(g - w) <= t * Math.abs(w) + 1e-12;
  const ice = les.ice;
  const x = Number(ice.extent_M);
  if (!(x > 0)) fail(rel, `ice.extent_M ${ice.extent_M} is not positive`);

  const species = ice.species.map((s) => ({
    id: s.id, nu: s.nu, role: s.role, initial: Number(s.initial_M),
    equilibrium: Number(s.equilibrium_M), change: Number(s.change_M),
  }));
  if (!species.some((s) => s.nu < 0)) fail(rel, "no reactant (ν<0) in the ICE table");
  if (!species.some((s) => s.nu > 0)) fail(rel, "no product (ν>0) in the ICE table");

  // 1. the ICE identity, re-derived: equilibrium = initial + ν·x, change = ν·x; roles agree with the ν signs.
  for (const s of species) {
    if ((s.nu > 0) !== (s.role === "product"))
      fail(rel, `${s.id}: role ${s.role} disagrees with ν sign ${s.nu}`);
    if (!rc(s.equilibrium, s.initial + s.nu * x))
      fail(rel, `${s.id}: equilibrium_M ${s.equilibrium} != initial + ν·x = ${(s.initial + s.nu * x)}`);
    if (!rc(s.change, s.nu * x))
      fail(rel, `${s.id}: change_M ${s.change} != ν·x = ${s.nu * x}`);
    if (s.equilibrium < 0) fail(rel, `${s.id}: equilibrium concentration is negative`);
  }

  const K = Number(les.equilibrium_constant.value);
  if (!(K > 0)) fail(rel, `equilibrium constant ${les.equilibrium_constant.value} is not positive`);

  // 2. the extent is physical: 0 < x < the reactant's initial concentration (nothing goes negative)
  const solve = solveEquilibrium(species.map((s) => ({ nu: s.nu, initial: s.initial })), K);
  if (!(x > 0 && x < solve.fwd + 1e-12))
    fail(rel, `extent ${x} is not strictly between 0 and the forward limit ${solve.fwd}`);

  // 3. INDEPENDENT re-solve of the mass-action root matches the committed extent (the reversible-extent solve)
  if (Number.isNaN(solve.extent)) fail(rel, "mass-action root not bracketed on re-solve");
  if (!rc(x, solve.extent, 1e-4))
    fail(rel, `ice.extent_M ${ice.extent_M} != independently re-solved root ${solve.extent} (Q=K)`);

  // 4. mass action satisfied: Q at the COMMITTED equilibrium concentrations reproduces K (the residual is the
  // machine-check — a reader can plug the table back in and get K). Both the emitted quotient + residual agree.
  const Qc = reactionQuotient(species.map((s) => s.equilibrium), species.map((s) => s.nu));
  if (!rc(Qc, K, 1e-5)) fail(rel, `Q at the committed concentrations ${Qc} != K ${K}`);
  if (!rc(Number(les.mass_action.quotient_at_equilibrium), K, 1e-3))
    fail(rel, `mass_action.quotient_at_equilibrium ${les.mass_action.quotient_at_equilibrium} != K ${K}`);
  const residual = Math.abs(Qc - K) / K;
  if (residual > 1e-5) fail(rel, `residual |Q-K|/K = ${residual} is too large — the extent does not satisfy mass action`);

  // 5. the reported results: [H⁺] is the hydronium row's equilibrium concentration; pH = −log₁₀[H⁺]; percent
  // ionization = x / [HA]₀ × 100.
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
}
