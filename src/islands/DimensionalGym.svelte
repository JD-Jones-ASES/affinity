<script>
  // The generic gym drill (Phase 1, ADR-0024). Two response modes (ADR-0032):
  //   • "choice"  — a categorical answer (a name, a formula, a coefficient set). A multiple-choice menu whose
  //                 every distractor is a plausible, same-form answer a named misconception produces.
  //   • "numeric" — a numeric answer. NO menu: a menu of a number and its wrong-by-magnitude cousins (0.55 %
  //                 vs 55 %) is gameable on sight, so the learner TYPES the number and the producer's named
  //                 mistakes become a diagnostic — enter a mistake's value and it is named.
  // The reveal shows the worked reasoning (the cancellation chain, the balancing tally). This island computes
  // no chemistry: every value, distractor, and diagnostic came from the producer and was re-derived by
  // validate-gyms.mjs. Numeric checking is arithmetic on the producer's own answer (a 1% entry tolerance).
  let { gym } = $props();
  const problems = gym.problems;

  // The chain caption fits the family: units cancel in conversions, but stoichiometry crosses a mole ratio
  // and percent yield compares two masses — so the wording adapts (the flow itself is identical).
  const CHAIN_LABELS = {
    solution_conversions_v1: "Follow the units — each factor cancels into the next:",
    mass_stoichiometry_v1: "Convert to moles, cross the mole ratio, convert back:",
    percent_yield_v1: "Theoretical yield first, then compare the actual:",
    limiting_mass_v1: "From the limiting reagent, convert to the product mass:",
    gas_laws_v1: "Convert to kelvin, rearrange, and substitute:",
  };
  const chainLabel = CHAIN_LABELS[gym.family] ?? "Work through it, step by step:";

  let idx = $state(0);
  let score = $state(0);
  let answered = $state(0);
  // choice mode
  let picked = $state(null);
  // numeric mode
  let entry = $state("");
  let submitted = $state(false);
  let outcome = $state(null); // { correct } | { correct:false, diag } | { gaveUp:true }

  const q = $derived(problems[idx]);
  const finished = $derived(idx >= problems.length);
  const revealed = $derived(finished ? false : (q.mode === "numeric" ? submitted : picked !== null));

  function pick(i) {
    if (picked !== null) return;
    picked = i;
    answered += 1;
    if (q.choices[i].correct) score += 1;
  }

  // Accept the numbers a learner actually types: a plain or scientific decimal, optional sign, stray spaces or
  // commas, and a trailing "%" when the unit is percent. Anything else is treated as no-entry (submit ignored).
  function parseNum(s) {
    let t = String(s).trim().replace(/,/g, "").replace(/\s+/g, "").replace(/%$/, "");
    if (!/^[-+]?(\d+\.?\d*|\.\d+)([eE][-+]?\d+)?$/.test(t)) return NaN;
    return Number(t);
  }
  const relClose = (a, b) =>
    Number.isFinite(a) && Number.isFinite(b) && Math.abs(a - b) <= 0.01 * Math.max(Math.abs(b), 1e-9) + 1e-9;

  function submitNumeric() {
    if (submitted) return;
    const val = parseNum(entry);
    if (!Number.isFinite(val)) return;                      // ignore an empty / non-numeric submit
    submitted = true;
    answered += 1;
    if (relClose(val, Number(q.answer.value))) {
      outcome = { correct: true };
      score += 1;
    } else {
      const diag = (q.diagnostics ?? []).find((d) => relClose(val, Number(d.value)));
      outcome = { correct: false, diag: diag ?? null };
    }
  }
  function giveUp() {
    if (submitted) return;
    submitted = true;
    answered += 1;
    outcome = { correct: false, gaveUp: true };
  }

  function next() {
    picked = null; entry = ""; submitted = false; outcome = null; idx += 1;
  }
  function restart() {
    idx = 0; picked = null; entry = ""; submitted = false; outcome = null; score = 0; answered = 0;
  }

  const choiceClass = (i) => {
    if (picked === null) return "idle";
    if (q.choices[i].correct) return "correct";
    return i === picked ? "wrong" : "dim";
  };

  // Present the choices in a stable, non-trivial order (the producer always emits the correct choice first;
  // showing them in emission order would give the answer away). A deterministic permutation seeded by the
  // problem id is identical on the server and the client, so there is no hydration mismatch — and picking
  // still uses each choice's original index, so scoring/reveal are unaffected.
  function seededOrder(id, n) {
    let h = 2166136261 >>> 0;
    for (let k = 0; k < id.length; k++) { h ^= id.charCodeAt(k); h = Math.imul(h, 16777619); }
    const rnd = () => {
      h += 0x6d2b79f5; let t = Math.imul(h ^ (h >>> 15), 1 | h);
      t ^= t + Math.imul(t ^ (t >>> 7), 61 | t);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
    const a = Array.from({ length: n }, (_, i) => i);
    for (let i = n - 1; i > 0; i--) { const j = Math.floor(rnd() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; }
    return a;
  }
  const order = $derived(finished || q.mode !== "choice" ? [] : seededOrder(q.id, q.choices.length));

  // Balancing gyms (ADR-0028) carry the conservation matrix; tally every element (and charge) with the correct
  // coefficients to show both sides come out equal. Pure integer addition over producer-emitted data — the
  // island computes no chemistry, it re-adds a matrix ChemKernel already derived and validate-gyms re-proved.
  function conservation(prob) {
    const { species, coefficients: co, elements } = prob.derivation;
    const keys = [...elements];
    if (species.some((s) => s.charge !== 0)) keys.push("charge");
    return keys.map((key) => {
      let left = 0, right = 0;
      species.forEach((s, i) => {
        const amt = (key === "charge" ? s.charge : (s.counts[key] || 0)) * co[i];
        if (s.role === "reactant") left += amt; else right += amt;
      });
      return { key: key === "charge" ? "charge" : key, left, right };
    });
  }
</script>

<div class="gym">
  {#if !finished}
    <div class="bar">
      <span class="pos">Problem {idx + 1} <span class="of">/ {problems.length}</span></span>
      <span class="score">Score {score}/{answered}</span>
    </div>

    <p class="prompt">{q.prompt}</p>

    {#if q.mode === "choice"}
      <ul class="choices" role="list">
        {#each order as i (i)}
          {@const c = q.choices[i]}
          <li>
            <button class={`choice ${choiceClass(i)}`} onclick={() => pick(i)} disabled={picked !== null}>
              <span class="mark" aria-hidden="true">{picked !== null && c.correct ? "✓" : picked === i && !c.correct ? "✗" : ""}</span>
              <span class="txt">{c.display}</span>
            </button>
            {#if picked !== null && i === picked && !c.correct && c.misconception}
              <p class="mis">{c.misconception}</p>
            {/if}
          </li>
        {/each}
      </ul>
    {:else}
      <div class="entry">
        <input
          class="num" type="text" inputmode="decimal" autocomplete="off" spellcheck="false"
          bind:value={entry} disabled={submitted} placeholder="type your answer"
          aria-label="Your numeric answer"
          onkeydown={(e) => { if (e.key === "Enter") submitNumeric(); }} />
        <span class="unit">{q.answer.unit}</span>
        <button class="check" onclick={submitNumeric} disabled={submitted || entry.trim() === ""}>Check</button>
        <button class="giveup" onclick={giveUp} disabled={submitted}>Show answer</button>
      </div>

      {#if submitted}
        <div class={`verdict ${outcome.correct ? "ok" : "no"}`}>
          {#if outcome.correct}
            <span class="mark" aria-hidden="true">✓</span> Correct — <strong>{q.answer.display}</strong>
          {:else if outcome.gaveUp}
            The answer is <strong>{q.answer.display}</strong>.
          {:else}
            <span class="mark" aria-hidden="true">✗</span> Not quite — you entered <span class="you">{entry.trim()}</span>; the answer is <strong>{q.answer.display}</strong>.
          {/if}
        </div>
        {#if outcome.diag}
          <p class="mis">{outcome.diag.misconception}</p>
        {/if}
      {/if}
    {/if}

    {#if revealed}
      <div class="reveal">
        {#if q.chain}
          <div class="chain-label">{chainLabel}</div>
          <div class="chain-flow">
            {#each q.chain as st, i}
              <div class="cq">
                <span class="cv">{st.value}</span><span class="cu">{st.unit}</span>
                <span class="cn">{st.note}</span>
              </div>
              {#if i < q.chain.length - 1}<span class="arrow">→</span>{/if}
            {/each}
          </div>
        {/if}
        {#if q.kind === "balancing"}
          <div class="chain-label">Every element balances with the correct coefficients:</div>
          <table class="tally">
            <thead><tr><th>{q.derivation.species.some((s) => s.charge !== 0) ? "element / charge" : "element"}</th><th>reactants</th><th>products</th><th aria-label="balanced"></th></tr></thead>
            <tbody>
              {#each conservation(q) as row}
                <tr>
                  <td class="el">{row.key}</td>
                  <td class="num">{row.left}</td>
                  <td class="num">{row.right}</td>
                  <td class="ok" aria-hidden="true">✓</td>
                </tr>
              {/each}
            </tbody>
          </table>
        {/if}
        <p class="explain"><span class="tag">Why</span> {q.explain}</p>
        <button class="next" onclick={next}>{idx + 1 < problems.length ? "Next problem →" : "See results →"}</button>
      </div>
    {/if}
  {:else}
    <div class="results">
      <div class="big">{score} / {problems.length}</div>
      <p class="muted">{score === problems.length ? "Perfect run — every one checks out." : "Practice builds fluency — run it again."}</p>
      <button class="next" onclick={restart}>Run the gym again ↻</button>
    </div>
  {/if}
</div>

<style>
  .gym { display: grid; gap: 0.9rem; }
  .bar { display: flex; justify-content: space-between; align-items: baseline; font-size: 0.85rem; color: var(--ink-faint); font-family: var(--font-mono); }
  .pos { font-weight: 600; color: var(--ink-2); }
  .of { color: var(--ink-faint); font-weight: 400; }
  .prompt { font-size: 1.1rem; font-weight: 500; margin: 0; }

  .choices { list-style: none; padding: 0; margin: 0; display: grid; gap: 0.4rem; }
  .choice {
    width: 100%; text-align: left; font: inherit; cursor: pointer; display: flex; align-items: center; gap: 0.5rem;
    background: var(--paper-2); border: 1px solid var(--line); border-radius: 8px; padding: 0.55rem 0.75rem; color: var(--ink);
  }
  .choice:disabled { cursor: default; }
  .choice.idle:hover { border-color: var(--accent); }
  .choice.correct { background: var(--accent-soft); border-color: color-mix(in srgb, var(--accent) 45%, transparent); color: var(--accent); font-weight: 600; }
  .choice.wrong { background: var(--warn-soft); border-color: color-mix(in srgb, var(--warn) 45%, transparent); color: var(--warn); }
  .choice.dim { opacity: 0.5; }
  .mark { width: 1rem; font-weight: 700; }
  .txt { font-family: var(--font-mono); }
  .mis { margin: 0.3rem 0 0.2rem 1.5rem; font-size: 0.86rem; color: var(--warn); }

  /* numeric free entry (ADR-0032) */
  .entry { display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap; }
  .num {
    font: inherit; font-family: var(--font-mono); width: 11rem; max-width: 60vw; padding: 0.5rem 0.7rem;
    border: 1px solid var(--line); border-radius: 8px; background: var(--paper-2); color: var(--ink);
  }
  .num:focus { outline: none; border-color: var(--accent); box-shadow: 0 0 0 2px var(--accent-soft); }
  .num:disabled { opacity: 0.75; }
  .entry .unit { font-family: var(--font-mono); color: var(--accent); font-weight: 600; margin-left: -0.15rem; }
  .check { font: inherit; cursor: pointer; background: var(--accent); color: white; border: none; border-radius: 8px; padding: 0.5rem 0.95rem; font-weight: 600; }
  .check:hover:enabled { filter: brightness(1.05); }
  .check:disabled { opacity: 0.5; cursor: default; }
  .giveup { font: inherit; cursor: pointer; background: transparent; color: var(--ink-faint); border: 1px solid var(--line); border-radius: 8px; padding: 0.5rem 0.8rem; }
  .giveup:hover:enabled { border-color: var(--accent); color: var(--ink-2); }
  .giveup:disabled { opacity: 0.4; cursor: default; }

  .verdict { font-size: 0.98rem; display: flex; align-items: center; gap: 0.35rem; flex-wrap: wrap; }
  .verdict.ok { color: var(--accent); font-weight: 600; }
  .verdict.no { color: var(--ink-2); }
  .verdict .you { font-family: var(--font-mono); color: var(--warn); }
  .verdict .mark { width: auto; }

  .reveal { background: var(--paper-2); border: 1px solid var(--line); border-radius: var(--radius); padding: 0.9rem 1.1rem; display: grid; gap: 0.7rem; }
  .chain-label { font-size: 0.82rem; color: var(--ink-faint); }
  .chain-flow { display: flex; align-items: flex-start; gap: 0.4rem; flex-wrap: wrap; }
  .cq { background: var(--paper); border: 1px solid var(--line); border-radius: 8px; padding: 0.4rem 0.6rem; text-align: center; min-width: 5rem; }
  .cv { font-family: var(--font-mono); font-weight: 600; font-size: 1.02rem; }
  .cu { font-family: var(--font-mono); color: var(--accent); margin-left: 0.25rem; }
  .cn { display: block; font-size: 0.7rem; color: var(--ink-faint); margin-top: 0.15rem; }
  .arrow { color: var(--ink-faint); font-size: 1.2rem; align-self: center; }

  .tally { border-collapse: collapse; font-family: var(--font-mono); font-size: 0.88rem; }
  .tally th { text-align: left; font-weight: 600; color: var(--ink-faint); font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.02em; padding: 0.15rem 0.9rem 0.3rem 0; }
  .tally td { padding: 0.15rem 0.9rem 0.15rem 0; border-top: 1px solid var(--line); }
  .tally .el { color: var(--ink-2); font-weight: 600; }
  .tally .num { text-align: right; color: var(--ink); }
  .tally .ok { color: var(--accent); font-weight: 700; }

  .explain { margin: 0; font-size: 0.9rem; color: var(--ink-2); }
  .tag { font-size: 0.7rem; text-transform: uppercase; font-weight: 700; color: var(--accent); background: var(--accent-soft); padding: 0.05rem 0.4rem; border-radius: 5px; margin-right: 0.4rem; }

  .next { justify-self: start; font: inherit; cursor: pointer; background: var(--accent); color: white; border: none; border-radius: 8px; padding: 0.45rem 0.9rem; font-weight: 600; }
  .next:hover { filter: brightness(1.05); }

  .results { text-align: center; display: grid; gap: 0.6rem; justify-items: center; padding: 1.5rem 0; }
  .big { font-size: 2.6rem; font-weight: 700; color: var(--accent); font-family: var(--font-mono); }
</style>
