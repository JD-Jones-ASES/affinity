<script>
  // The dumb stepper: several reconciled views of one ChemKernel-verified scenario — the scenario, the three
  // equations (molecular -> complete ionic -> net ionic), the dimensional-analysis chains, and the species
  // ledger (the pivot object, ADR-0002). Plus the three honesty badges, the SHOWN checks, the misconception
  // register, and the disclosed assumptions. It computes nothing; every value came from the producer.
  //
  // The two interactive tabs (beaker + extent bar) hydrate only when the solution carries an `interactive`
  // block of parity-verified closed forms (ADR-0008/0011); a static build without it renders the full chain.
  import ExtentBar from "./ExtentBar.svelte";
  import BeakerSpecies from "./BeakerSpecies.svelte";
  import PracticeQuestion from "./PracticeQuestion.svelte";

  let { solution } = $props();
  const s = solution;

  const hasInteractive = !!s.interactive;
  const hasPractice = !!s.practice?.questions?.length;
  let tab = $state("equations");

  // The concrete answers, pulled from the verified result (never recomputed here). The reported product is a
  // solid precipitate; a collected gas (gas stoichiometry — headline is its VOLUME via PV=nRT, ADR-0041); or
  // the general product (water for an acid-base neutralization, ADR-0037). The dissolved salt is named when one
  // is left in solution. The beaker view — watching a solid settle out — only fits a precipitate.
  const reported = s.result.precipitate ?? s.result.product;
  const salt = s.result.salt;
  const gas = s.result.gas;           // gas-stoichiometry volume block (ADR-0041), or undefined
  const energy = s.result.energy;     // energy-ledger block (ADR-0043): q = ΔH_rxn·ξ, or undefined
  const isPrecip = !!s.result.precipitate;
  const isGas = !!gas;
  const isEnergy = !!energy;          // the headline is the HEAT, not a product mass — no reported product
  const showBeaker = hasInteractive && s.interactive?.product?.phase === "s";
  const leftover = s.result.leftover ?? [];
  // the energy misconception (reading ΔH_rxn as the total heat) refutes with the extent scaling: the naive
  // |ΔH_rxn| kJ vs the actual |q| the limiting reagent allows. Illustrative display arithmetic on verified
  // numbers — the real values (ΔH_rxn, q, ξ) all came from the producer.
  const energyScaleTrap = isEnergy && s.misconception?.refuted_by === "enthalpy_scales_with_extent";
  const naiveHeat = isEnergy ? Math.abs(Number(energy.delta_h_rxn_kj_per_mol)) : null;
  // q is signed (q < 0 = exothermic); its MAGNITUDE is what "released/absorbed" refers to. Keeping the two apart
  // avoids the sign-inconsistent "heat released −44.5 kJ" pairing (QC 2026-07-09 C8) — q stays signed, the amount
  // released/absorbed is |q|. Strip the leading minus to preserve the producer's sig-fig formatting.
  const qMag = isEnergy ? energy.q_kj_display.replace(/^-/, "") : null;
  // the "both reactants are fully consumed" trap: one runs out first, the other keeps a leftover — read off
  // the verified ledger (limiting row → 0, excess row → its final_mol). Only an exact-ratio mix cancels both.
  const bothConsumedTrap = s.misconception?.refuted_by === "neutralization_leaves_excess";

  // Data-driven refutation of the misconception, read straight off the verified ledger — never re-derived here.
  const fmtMmol = (mol) => {
    const v = Number(mol) * 1000;
    return Number.isInteger(v) ? String(v) : v.toFixed(4).replace(/\.?0+$/, "");
  };

  // The two reactant rows (ν<0): one limits, one is in excess. Their real capacities are initial ÷ |ν| — that
  // is what decides who runs out. When the coefficients differ, THAT is the punch line (not volume or raw
  // moles): the limiting reagent can even start with more moles. When they're equal, fall back to the volume
  // story (the classic "smaller amount must be limiting" trap).
  const reactantRows = (s.ledger.species ?? []).filter((r) => r.nu < 0);
  const limRow = reactantRows.find((r) => r.role === "limiting");
  const excRow = reactantRows.find((r) => r.role === "excess");
  const cap = (r) => Number(r.initial_mol) / Math.abs(r.nu);
  const coeffStory = !!limRow && !!excRow && Math.abs(limRow.nu) !== Math.abs(excRow.nu);
  const limStartsWithMore = coeffStory && Number(limRow.initial_mol) > Number(excRow.initial_mol);

  // volume fallback: is the smaller-volume solution actually the one in excess? (ledger.limiting holds
  // phase-stripped core ids, so strip the given's phase before comparing.)
  const stripPhase = (id) => String(id).replace(/\((?:s|l|g|aq)\)$/, "");
  const withVol = (s.given ?? []).filter((g) => g.volume_mL != null);
  const smallerVol = withVol.length === 2
    ? (Number(withVol[0].volume_mL) < Number(withVol[1].volume_mL) ? withVol[0] : withVol[1])
    : null;
  const limitingIds = new Set(s.ledger.limiting);
  const smallerVolLimits = smallerVol ? limitingIds.has(stripPhase(smallerVol.species)) : null;

  const roleLabel = { limiting: "limiting", excess: "excess", product: "product" };

  // gas stoichiometry (ADR-0041): the molar-volume misconception refutes with the verified gas block, not the
  // ledger. The wrong "22.4 L/mol everywhere" answer is illustrative display arithmetic on the verified moles
  // (like the mmol conversions above) — not a chemistry derivation; the real numbers come from the producer.
  const molarVolumeTrap = isGas && s.misconception?.refuted_by === "molar_volume_is_conditions_dependent";
  const wrong224 = isGas ? (Number(gas.moles) * 22.4).toPrecision(3) : null;
</script>

<section class="player">
  <header class="head">
    <div class="badges">
      <span class="badge machine"><span class="dot"></span>Machine-checked — balanced, charge-conserved, extent-verified by ChemKernel</span>
      {#if s.solubility_basis}
        <span class="badge sourced"><span class="dot"></span>Solubility rule-sourced ({s.solubility_basis.source})</span>
      {/if}
      {#if isEnergy}
        <span class="badge sourced"><span class="dot"></span>Formation enthalpies data-sourced ({energy.source})</span>
      {/if}
      <span class="badge model"><span class="dot"></span>{s.assumptions.length} modeling assumption{s.assumptions.length === 1 ? "" : "s"} (disclosed)</span>
    </div>
    <p class="scenario">{@html s.scenarioHtml}</p>
  </header>

  <!-- the verified answers -->
  <div class="results">
    {#if isGas}
      <!-- gas stoichiometry: the VOLUME is the headline (model-exact, PV=nRT). The moles behind it are
           machine-checked; the volume rides on the disclosed ideal-gas model — so it carries its own badge. -->
      <div class="result gas">
        <div class="label">Volume of {@html gas.symbolHtml} gas <span class="badge model tiny"><span class="dot"></span>ideal gas</span></div>
        <div class="value">{gas.volume_L_display} <span class="unit">L</span></div>
        <div class="cond">at {gas.pressure_atm} atm, {gas.temperature_C ? `${gas.temperature_C} °C` : `${gas.temperature_K} K`}</div>
      </div>
    {/if}
    {#if isEnergy}
      <!-- energy ledger (ADR-0043): the HEAT is the headline (model-exact — Hess's law over sourced ΔH_f°). The
           ledger's ξ is machine-checked; ΔH_rxn rides the disclosed model — so the card carries its own badge. -->
      <div class="result energy">
        <div class="label">Heat of reaction q <span class="badge model tiny"><span class="dot"></span>{energy.classification}</span></div>
        <div class="value">{energy.q_kj_display} <span class="unit">kJ</span></div>
        <div class="cond">q = ΔH_rxn × ξ · {energy.classification === "exothermic" ? "q < 0 ⇒ heat released" : "q > 0 ⇒ heat absorbed"}</div>
      </div>
    {/if}
    {#if reported}
      <div class="result">
        <div class="label">Mass of {@html reported.symbolHtml} {isPrecip ? "precipitate" : "formed"}</div>
        <div class="value">{reported.mass_g_display} <span class="unit">g</span></div>
      </div>
    {/if}
    {#if salt}
      <div class="result">
        <div class="label">{isGas ? "Dissolved salt" : "Salt formed"} ({@html salt.symbolHtml})</div>
        <div class="value">{salt.mass_g_display} <span class="unit">g</span></div>
      </div>
    {/if}
    <div class="result">
      <div class="label">Limiting reagent</div>
      <div class="value">{s.result.limiting_speciesPretty.join(", ")}</div>
    </div>
    <div class="result">
      <div class="label">Left {isGas || isEnergy ? "over" : "in solution"}</div>
      <div class="value">
        {#if leftover.length}
          {#each leftover as l, i}{l.idPretty} {Number(l.moles) * 1000} mmol{i < leftover.length - 1 ? " · " : ""}{/each}
        {:else}—{/if}
      </div>
    </div>
  </div>

  {#if isGas}
    <!-- the model-exact leg spelled out: moles (machine-checked) → volume via PV=nRT, and the 22.4-L trap named -->
    <div class="gascard">
      <div class="ghead"><span class="badge model"><span class="dot"></span>Gas volume — model-exact (ideal gas)</span> the moles are machine-checked; PV=nRT converts them to a volume at the stated conditions</div>
      <div class="gflow">
        <div class="gcell"><span class="gv">{gas.moles}</span> <span class="gu">mol {@html gas.symbolHtml}</span><span class="gn">from the ledger (ξ)</span></div>
        <span class="gop">×</span>
        <div class="gcell"><span class="gv">{gas.molar_volume_L_per_mol_display}</span> <span class="gu">L/mol</span><span class="gn">RT/P at {gas.pressure_atm} atm, {gas.temperature_K} K</span></div>
        <span class="gop">=</span>
        <div class="gcell big"><span class="gv">{gas.volume_L_display}</span> <span class="gu">L</span><span class="gn">volume of {@html gas.symbolHtml}</span></div>
      </div>
      <p class="gnote">The molar volume is <strong>RT/P = {gas.molar_volume_L_per_mol_display} L/mol</strong> at these conditions — <em>not</em> the 22.4 L/mol you memorized for STP (0 °C, 1 atm). One mole of gas only fills 22.4 L at STP; change the temperature or pressure and you must use PV=nRT.</p>
    </div>
  {/if}

  {#if isEnergy}
    <!-- the energy ledger spelled out: ΔH_rxn by Hess's law (sourced ΔH_f°, ν-weighted), then × ξ = q. The
         ledger's ξ is machine-checked; ΔH_f° are data-sourced; the relations are model-assumed. -->
    <div class="energycard">
      <div class="ehead">
        <span class="badge model"><span class="dot"></span>Reaction enthalpy — model-exact (Hess's law)</span>
        <span class="badge sourced tiny"><span class="dot"></span>ΔH_f° sourced ({energy.source})</span>
        each ΔH_f° is a sourced measurement; ΔH_rxn is their ν-weighted sum, and the heat scales with the extent
      </div>
      <div class="tablewrap">
        <table class="hess">
          <thead>
            <tr><th>Species</th><th class="num">signed ν</th><th class="num">ΔH_f° (kJ/mol)</th><th class="num">ν·ΔH_f°</th></tr>
          </thead>
          <tbody>
            {#each energy.hess as h}
              <tr class={h.role}>
                <td class="sym">{@html h.symbolHtml} <span class="phase">{h.phaseTag}</span> <span class="rolechip {h.role === 'product' ? 'product' : 'excess'}">{h.role}</span></td>
                <td class="num">{h.role === "product" ? "+" : "−"}{h.coeff}</td>
                <td class="num">{h.delta_h_f_kj_per_mol}{h.is_element ? " (element → 0)" : ""}</td>
                <td class="num">{h.contribution_kj_per_mol}</td>
              </tr>
            {/each}
          </tbody>
          <tfoot>
            <tr><td colspan="3">ΔH_rxn = Σ ν·ΔH_f° (products − reactants)</td><td class="num total">{energy.delta_h_rxn_kj_per_mol}</td></tr>
          </tfoot>
        </table>
      </div>
      <div class="eflow">
        <div class="ecell"><span class="ev">{energy.delta_h_rxn_kj_per_mol}</span> <span class="eu">kJ/mol</span><span class="en">ΔH_rxn, per mole of reaction</span></div>
        <span class="eop">×</span>
        <div class="ecell"><span class="ev">{energy.extent_mol}</span> <span class="eu">mol</span><span class="en">extent ξ (capped by {s.result.limiting_speciesPretty.join(", ")})</span></div>
        <span class="eop">=</span>
        <div class="ecell big"><span class="ev">{energy.q_kj_display}</span> <span class="eu">kJ</span><span class="en">q, the heat of reaction</span></div>
      </div>
      <p class="enote">ΔH_rxn is <strong>per mole of reaction</strong> (one "run" of the balanced equation). This burn advances only ξ = {energy.extent_mol} mol before the limiting reagent runs out, so q = <strong>{energy.q_kj_display} kJ</strong> — it {energy.classification === "exothermic" ? "releases" : "absorbs"} {qMag} kJ, not {naiveHeat} kJ. Elements in their standard state have ΔH_f° = 0 (they are the reference level, not zero energy).</p>
    </div>
  {/if}

  <!-- percent yield: actual measured against the ledger's theoretical maximum (ADR-0029) -->
  {#if s.result.percent_yield}
    <div class="yieldcard">
      <div class="yhead"><span class="badge machine"><span class="dot"></span>Percent yield</span> theoretical is the ledger's maximum extent — the actual falls short</div>
      <div class="yflow">
        <div class="ycell"><span class="yv">{s.result.percent_yield.theoretical_display}</span> <span class="yu">g</span><span class="yn">theoretical (max from the ledger)</span></div>
        <span class="yop">→</span>
        <div class="ycell"><span class="yv">{s.result.percent_yield.actual_display}</span> <span class="yu">g</span><span class="yn">actually recovered</span></div>
        <span class="yop">=</span>
        <div class="ycell big"><span class="yv">{s.result.percent_yield.percent_display}</span><span class="yu">%</span><span class="yn">actual ÷ theoretical × 100</span></div>
      </div>
      <p class="ynote">A real yield falls short of the theoretical maximum — side reactions, incomplete precipitation, losses on filtering — and can never exceed 100%: that would create matter from nothing.</p>
    </div>
  {/if}

  <!-- view tabs -->
  <div class="tabs" role="tablist">
    <button role="tab" aria-selected={tab === "equations"} onclick={() => (tab = "equations")}>Equations</button>
    <button role="tab" aria-selected={tab === "chain"} onclick={() => (tab = "chain")}>Dimensional analysis</button>
    <button role="tab" aria-selected={tab === "ledger"} onclick={() => (tab = "ledger")}>Species ledger</button>
    {#if showBeaker}
      <button role="tab" aria-selected={tab === "beaker"} onclick={() => (tab = "beaker")}>Beaker</button>
    {/if}
    {#if hasInteractive}
      <button role="tab" aria-selected={tab === "extent"} onclick={() => (tab = "extent")}>Extent</button>
    {/if}
    {#if hasPractice}
      <button role="tab" aria-selected={tab === "practice"} onclick={() => (tab = "practice")}>Practice</button>
    {/if}
  </div>

  {#if tab === "equations"}
    <div class="panel eqs" role="tabpanel" aria-label="Equations">
      <div class="eq">
        <div class="eq-label">Molecular equation — what you combine</div>
        <div class="math">{@html s.equations.molecular.html}</div>
      </div>
      {#if s.equations.complete_ionic}
        <div class="eq">
          <div class="eq-label">Complete ionic — every strong electrolyte shown as free ions <span class="badge model tiny"><span class="dot"></span>strong-electrolyte model</span></div>
          <div class="math">{@html s.equations.complete_ionic.html}</div>
        </div>
        <div class="eq">
          <div class="eq-label">Net ionic — spectators cancelled, the reaction that actually happens</div>
          <div class="math">{@html s.equations.net_ionic.html}</div>
          {#if s.equations.spectatorsPretty.length}
            <p class="spectators">Spectator ions (unchanged, still dissolved): {#each s.equations.spectatorsPretty as sp, i}<span class="ion spec">{sp}</span>{i < s.equations.spectatorsPretty.length - 1 ? " " : ""}{/each}</p>
          {/if}
        </div>
      {:else}
        <p class="hint faint">There are no ions in solution here — every species is molecular (or a free element), so the complete-ionic and net-ionic equations would just repeat the molecular one. A reaction only has an ionic equation when strong electrolytes dissolve into ions.</p>
      {/if}
    </div>
  {:else if tab === "chain"}
    <div class="panel chains" role="tabpanel" aria-label="Dimensional analysis">
      {#each s.dimensional_analysis as chain}
        <div class="chain">
          <div class="chain-target">{chain.target}</div>
          <div class="chain-flow">
            {#each chain.steps as st, i}
              <div class="q">
                <span class="qv">{st.value}</span><span class="qu">{st.unit}</span>
                <span class="qn">{st.note}</span>
              </div>
              {#if i < chain.steps.length - 1}<span class="arrow">→</span>{/if}
            {/each}
          </div>
        </div>
      {/each}
      <p class="hint faint">Units carry through the arithmetic and cancel — the answer lands in moles because mL→L cancels against mol/L. ChemKernel checks this dimensionally (the unit check below).</p>
    </div>
  {:else if tab === "ledger"}
    <div class="panel" role="tabpanel" aria-label="Species ledger">
      <p class="ledger-lede muted">The pivot object: every amount is <code>n_i = n_i,0 + ν_i·ξ</code>. The extent
        <strong>ξ = {s.ledger.extent_mol} mol</strong> is as far as the reaction can run before a reactant hits zero.</p>
      <div class="tablewrap">
        <table class="ledger">
          <thead>
            <tr><th>Species</th><th>Phase</th><th class="num">ν</th><th class="num">initial (mol)</th><th class="num">final (mol)</th><th>role</th></tr>
          </thead>
          <tbody>
            {#each s.ledger.species as r}
              <tr class={r.role}>
                <td class="sym">{@html r.symbolHtml}</td>
                <td class="phase">{r.phaseTag}</td>
                <td class="num">{r.nu > 0 ? "+" : ""}{r.nu}</td>
                <td class="num">{r.initial_mol}</td>
                <td class="num final">{r.final_mol}</td>
                <td><span class="rolechip {r.role}">{roleLabel[r.role]}</span></td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
      <p class="hint faint">The <span class="rolechip limiting">limiting</span> row reaches exactly 0 — it runs
        out first and caps ξ. Products grow from 0 by <code>+ν·ξ</code>; the excess reactant keeps a leftover.</p>
    </div>
  {:else if tab === "beaker" && showBeaker}
    <div class="panel" role="tabpanel" aria-label="Beaker / species view">
      <BeakerSpecies interactive={s.interactive} {leftover} />
    </div>
  {:else if tab === "extent" && hasInteractive}
    <div class="panel" role="tabpanel" aria-label="Extent bar">
      <ExtentBar interactive={s.interactive} productSymbol={reported.idPretty} />
    </div>
  {:else if tab === "practice" && hasPractice}
    <div class="panel practicepanel" role="tabpanel" aria-label="Practice">
      <p class="practice-lede muted">Generated variants of this reaction, each solver-verified. Type the numeric
        answers — a wrong entry that matches a common mistake is named for you; the "which reagent limits?"
        questions offer only plausible choices. ({s.practice.questions.length} questions.)</p>
      {#each s.practice.questions as q (q.id)}
        <PracticeQuestion question={q} />
      {/each}
    </div>
  {/if}

  <!-- the checks, SHOWN not asserted -->
  <div class="proof">
    <div class="proof-head">
      <span class="badge machine"><span class="dot"></span>Verification</span>
      <strong>Every claim below was proven at build time — not asserted.</strong>
    </div>
    <ul class="checks">
      <li><span class="tick">✓</span> Atoms balance across the equation <span class="tier">[conservation matrix]</span></li>
      <li><span class="tick">✓</span> Charge balances (net ionic re-verified) <span class="tier">[charge row]</span></li>
      <li><span class="tick">✓</span> Units cancel through the dimensional chain <span class="tier">[units engine]</span></li>
      <li><span class="tick">✓</span> No amount goes negative — extent is physical <span class="tier">[nonnegative-extent guard]</span></li>
    </ul>
    {#if s.solubility_basis}
      <p class="basis"><span class="badge sourced tiny"><span class="dot"></span>rule-sourced</span>
        {@html s.solubility_basis.idPretty} is treated as {s.solubility_basis.soluble ? "soluble" : "insoluble"} by rule
        <code>{s.solubility_basis.rule_id}</code>: “{@html s.solubility_basis.statementHtml}” ({s.solubility_basis.source}).</p>
    {/if}
  </div>

  <!-- misconception register (ADR-0011 / brief §13) -->
  {#if s.misconception}
    <div class="misconception">
      <div class="mis-claim"><span class="x">✗</span> Common misconception: “{@html s.misconception.claimHtml}”</div>
      <p class="mis-fix">
        {#if energyScaleTrap}
          ΔH_rxn = <strong>{energy.delta_h_rxn_kj_per_mol} kJ/mol</strong> is the heat <em>per mole of reaction</em> —
          for exactly one "run" of the balanced equation. The actual heat is <strong>q = ΔH_rxn × ξ</strong>, and the
          extent ξ = {energy.extent_mol} mol is capped by the limiting reagent ({s.result.limiting_speciesPretty.join(", ")}).
          So this burn {energy.classification === "exothermic" ? "releases" : "absorbs"}
          <strong>{energy.q_kj_display} kJ</strong>, not {naiveHeat} kJ. The energy tracks the extent, exactly as the
          species amounts do — it is the ledger's other column.
        {:else if molarVolumeTrap}
          22.4 L/mol is the molar volume <strong>only at STP</strong> (0 °C, 1 atm). At {gas.pressure_atm} atm
          and {gas.temperature_C ? `${gas.temperature_C} °C` : `${gas.temperature_K} K`} it is
          <strong>RT/P = {gas.molar_volume_L_per_mol_display} L/mol</strong>, so {@html gas.symbolHtml} occupies
          <strong>{gas.volume_L_display} L</strong> — not {wrong224} L. Whenever you are not at STP, use
          <strong>PV = nRT</strong> at the actual pressure and temperature.
        {:else if bothConsumedTrap && limRow && excRow}
          Only when the amounts match the ratio exactly. Here one reactant runs out first and the other is left
          over: <strong>{limRow.idPretty}</strong> reaches 0 (all {fmtMmol(limRow.initial_mol)} mmol consumed),
          but <strong>{excRow.idPretty}</strong> keeps <strong>{fmtMmol(excRow.final_mol)} mmol</strong>
          unreacted — so both are <em>not</em> used up. Neutralization stops when the <strong>limiting</strong>
          reactant hits 0; whatever the other started with above the matching amount stays in solution.
        {:else if coeffStory}
          Divide each reactant's amount by its coefficient — that capacity is what runs out.
          <strong>{limRow.idPretty}</strong>: {fmtMmol(limRow.initial_mol)} mmol ÷ {Math.abs(limRow.nu)} =
          {fmtMmol(cap(limRow))} mmol of reaction; <strong>{excRow.idPretty}</strong>:
          {fmtMmol(excRow.initial_mol)} mmol ÷ {Math.abs(excRow.nu)} = {fmtMmol(cap(excRow))} mmol.
          {limRow.idPretty} is smaller, so it <strong>limits</strong>{limStartsWithMore ? ` — even though it starts with more moles (${fmtMmol(limRow.initial_mol)} vs ${fmtMmol(excRow.initial_mol)} mmol)` : ""}.
          Raw moles mislead when the coefficients differ; watch the <strong>final (mol)</strong> column.
        {:else if smallerVol && smallerVolLimits === false}
          The smaller-volume solution ({smallerVol.idPretty}, {smallerVol.volume_mL} mL) is actually in
          <strong>excess</strong>. Moles decide it, not volume: {s.result.limiting_speciesPretty.join(", ")}
          reaches 0 in the ledger and limits the reaction — watch the <strong>final (mol)</strong> column.
        {:else}
          Moles decide it, not volume: {s.result.limiting_speciesPretty.join(", ")} reaches 0 in the ledger
          first and limits the reaction — watch the <strong>final (mol)</strong> column.
        {/if}
      </p>
    </div>
  {/if}

  <!-- assumptions, disclosed not discharged (ADR-0003) -->
  <details class="assumptions">
    <summary><span class="badge model"><span class="dot"></span>Modeling assumptions</span> — author-asserted, disclosed not discharged</summary>
    <ul>
      {#each s.assumptions as a}<li><span class="akind {a.kind}">{a.kind}</span> {@html a.claimHtml}</li>{/each}
    </ul>
  </details>
</section>

<style>
  .player { display: grid; gap: 1.1rem; }
  .badges { display: flex; flex-wrap: wrap; gap: 0.5rem; }
  .scenario { font-size: 1.05rem; margin: 0.6rem 0 0; }

  .tabs { display: flex; gap: 0.4rem; border-bottom: 1px solid var(--line); flex-wrap: wrap; }
  .tabs button {
    border: none; background: none; padding: 0.5rem 0.9rem; cursor: pointer; font: inherit;
    color: var(--ink-2); border-bottom: 2px solid transparent; margin-bottom: -1px;
  }
  .tabs button[aria-selected="true"] { color: var(--accent); border-bottom-color: var(--accent); font-weight: 600; }

  .panel { background: var(--paper-2); border: 1px solid var(--line); border-radius: var(--radius); padding: 1rem 1.2rem; }
  .math { overflow-x: auto; }

  .eqs { display: grid; gap: 1rem; }
  .eq-label { font-size: 0.85rem; color: var(--ink-faint); margin-bottom: 0.3rem; display: flex; gap: 0.5rem; align-items: center; flex-wrap: wrap; }
  .badge.tiny { font-size: 0.68rem; padding: 0.05rem 0.4rem; }
  .spectators { margin: 0.5rem 0 0; font-size: 0.92rem; color: var(--ink-2); }
  .ion { font-family: var(--font-mono); padding: 0.05rem 0.35rem; border-radius: 6px; }
  .ion.spec { background: var(--paper-sunk); color: var(--ink-2); }

  .chains { display: grid; gap: 1rem; }
  .chain-target { font-size: 0.85rem; color: var(--ink-faint); margin-bottom: 0.4rem; }
  .chain-flow { display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap; }
  .q { background: var(--paper); border: 1px solid var(--line); border-radius: 8px; padding: 0.4rem 0.6rem; text-align: center; min-width: 5rem; }
  .qv { font-family: var(--font-mono); font-weight: 600; font-size: 1.05rem; }
  .qu { font-family: var(--font-mono); color: var(--accent); margin-left: 0.25rem; }
  .qn { display: block; font-size: 0.72rem; color: var(--ink-faint); margin-top: 0.15rem; }
  .arrow { color: var(--ink-faint); font-size: 1.2rem; }

  .ledger-lede { margin: 0 0 0.7rem; font-size: 0.95rem; }
  .tablewrap { overflow-x: auto; }
  table.ledger { width: 100%; border-collapse: collapse; font-size: 0.95rem; }
  table.ledger th, table.ledger td { padding: 0.45rem 0.6rem; text-align: left; border-bottom: 1px solid var(--line); }
  table.ledger th.num, table.ledger td.num { text-align: right; font-family: var(--font-mono); }
  table.ledger .sym { font-weight: 600; }
  table.ledger .phase { color: var(--ink-faint); font-family: var(--font-mono); font-size: 0.85rem; }
  table.ledger td.final { font-weight: 600; }
  tr.limiting td.final { color: var(--warn); }
  tr.product td.final { color: var(--accent); }
  .rolechip { font-size: 0.72rem; font-weight: 600; padding: 0.1rem 0.45rem; border-radius: 999px; }
  .rolechip.limiting { background: var(--warn-soft); color: var(--warn); }
  .rolechip.excess { background: var(--model-soft); color: var(--model); }
  .rolechip.product { background: var(--accent-soft); color: var(--accent); }
  .hint { font-size: 0.85rem; margin: 0.7rem 0 0; }

  .proof { border: 1px solid color-mix(in srgb, var(--accent) 30%, var(--line)); border-radius: var(--radius); padding: 0.6rem 0.9rem 0.9rem; }
  .proof-head { display: flex; align-items: center; gap: 0.7rem; padding: 0.3rem 0; flex-wrap: wrap; }
  .checks { list-style: none; padding: 0; margin: 0.3rem 0; display: grid; gap: 0.35rem; }
  .checks li { font-size: 0.93rem; }
  .tick { color: var(--accent); font-weight: 700; }
  .tier { color: var(--ink-faint); font-family: var(--font-mono); font-size: 0.78rem; }
  .basis { font-size: 0.9rem; color: var(--ink-2); margin: 0.6rem 0 0; }
  .basis code { color: var(--sourced); }

  .misconception { background: var(--warn-soft); border: 1px solid color-mix(in srgb, var(--warn) 35%, transparent); border-radius: var(--radius); padding: 0.8rem 1rem; }
  .mis-claim { font-weight: 600; color: var(--warn); }
  .mis-claim .x { font-weight: 700; }
  .mis-fix { margin: 0.4rem 0 0; color: var(--ink-2); font-size: 0.95rem; }

  .assumptions summary { cursor: pointer; color: var(--ink-2); }
  .assumptions ul { color: var(--ink-2); font-size: 0.93rem; }
  .akind { font-family: var(--font-mono); font-size: 0.7rem; text-transform: uppercase; padding: 0.05rem 0.35rem; border-radius: 5px; margin-right: 0.3rem; }
  .akind.model { background: var(--model-soft); color: var(--model); }
  .akind.rule { background: var(--sourced-soft); color: var(--sourced); }

  .practicepanel { display: grid; gap: 0.8rem; }
  .practice-lede { margin: 0; font-size: 0.95rem; }

  .yieldcard { background: var(--paper-2); border: 1px solid color-mix(in srgb, var(--accent) 30%, var(--line)); border-radius: var(--radius); padding: 0.8rem 1.1rem; }
  .yhead { font-size: 0.85rem; color: var(--ink-faint); display: flex; gap: 0.5rem; align-items: center; flex-wrap: wrap; margin-bottom: 0.6rem; }
  .yflow { display: flex; align-items: flex-start; gap: 0.6rem; flex-wrap: wrap; }
  .ycell { background: var(--paper); border: 1px solid var(--line); border-radius: 8px; padding: 0.45rem 0.7rem; text-align: center; min-width: 6rem; }
  .ycell.big { border-color: color-mix(in srgb, var(--accent) 45%, transparent); background: var(--accent-soft); }
  .yv { font-family: var(--font-mono); font-weight: 700; font-size: 1.15rem; }
  .ycell.big .yv { color: var(--accent); }
  .yu { font-family: var(--font-mono); color: var(--ink-faint); }
  .yn { display: block; font-size: 0.7rem; color: var(--ink-faint); margin-top: 0.15rem; }
  .yop { color: var(--ink-faint); font-size: 1.3rem; align-self: center; }
  .ynote { margin: 0.6rem 0 0; font-size: 0.88rem; color: var(--ink-2); }

  /* gas stoichiometry (ADR-0041): the volume card is the headline; the gascard spells out the model-exact leg */
  .result.gas { border-color: color-mix(in srgb, var(--model) 45%, var(--line)); background: var(--model-soft); }
  .result.gas .value { color: var(--model); }
  .result .cond { font-size: 0.72rem; color: var(--ink-faint); margin-top: 0.15rem; font-family: var(--font-mono); }
  .result .label .badge.tiny { margin-left: 0.35rem; }
  .gascard { background: var(--paper-2); border: 1px solid color-mix(in srgb, var(--model) 30%, var(--line)); border-radius: var(--radius); padding: 0.8rem 1.1rem; }
  .ghead { font-size: 0.85rem; color: var(--ink-faint); display: flex; gap: 0.5rem; align-items: center; flex-wrap: wrap; margin-bottom: 0.6rem; }
  .gflow { display: flex; align-items: flex-start; gap: 0.6rem; flex-wrap: wrap; }
  .gcell { background: var(--paper); border: 1px solid var(--line); border-radius: 8px; padding: 0.45rem 0.7rem; text-align: center; min-width: 6rem; }
  .gcell.big { border-color: color-mix(in srgb, var(--model) 45%, transparent); background: var(--model-soft); }
  .gv { font-family: var(--font-mono); font-weight: 700; font-size: 1.15rem; }
  .gcell.big .gv { color: var(--model); }
  .gu { font-family: var(--font-mono); color: var(--ink-faint); }
  .gn { display: block; font-size: 0.7rem; color: var(--ink-faint); margin-top: 0.15rem; }
  .gop { color: var(--ink-faint); font-size: 1.3rem; align-self: center; }
  .gnote { margin: 0.6rem 0 0; font-size: 0.88rem; color: var(--ink-2); }

  /* energy ledger (ADR-0043): the heat card is the headline; the energycard spells out Hess's law + q = ΔH·ξ */
  .result.energy { border-color: color-mix(in srgb, var(--model) 45%, var(--line)); background: var(--model-soft); }
  .result.energy .value { color: var(--model); }
  .energycard { background: var(--paper-2); border: 1px solid color-mix(in srgb, var(--model) 30%, var(--line)); border-radius: var(--radius); padding: 0.8rem 1.1rem; }
  .ehead { font-size: 0.85rem; color: var(--ink-faint); display: flex; gap: 0.5rem; align-items: center; flex-wrap: wrap; margin-bottom: 0.6rem; }
  table.hess { width: 100%; border-collapse: collapse; font-size: 0.92rem; margin-bottom: 0.7rem; }
  table.hess th, table.hess td { padding: 0.4rem 0.6rem; text-align: left; border-bottom: 1px solid var(--line); }
  table.hess th.num, table.hess td.num { text-align: right; font-family: var(--font-mono); }
  table.hess .sym { font-weight: 600; }
  table.hess .phase { color: var(--ink-faint); font-family: var(--font-mono); font-size: 0.8rem; font-weight: 400; }
  table.hess tr.product td.num:last-child { color: var(--accent); }
  table.hess tfoot td { font-weight: 700; border-bottom: none; border-top: 2px solid var(--line); }
  table.hess td.total { color: var(--model); font-family: var(--font-mono); }
  .eflow { display: flex; align-items: flex-start; gap: 0.6rem; flex-wrap: wrap; }
  .ecell { background: var(--paper); border: 1px solid var(--line); border-radius: 8px; padding: 0.45rem 0.7rem; text-align: center; min-width: 6rem; }
  .ecell.big { border-color: color-mix(in srgb, var(--model) 45%, transparent); background: var(--model-soft); }
  .ev { font-family: var(--font-mono); font-weight: 700; font-size: 1.15rem; }
  .ecell.big .ev { color: var(--model); }
  .eu { font-family: var(--font-mono); color: var(--ink-faint); }
  .en { display: block; font-size: 0.7rem; color: var(--ink-faint); margin-top: 0.15rem; }
  .eop { color: var(--ink-faint); font-size: 1.3rem; align-self: center; }
  .enote { margin: 0.6rem 0 0; font-size: 0.88rem; color: var(--ink-2); }
</style>
