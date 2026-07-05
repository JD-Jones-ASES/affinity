<script>
  // One generated practice item (ADR-0011, brief §6.8). The answer, every distractor, and every diagnostic
  // came from the producer (solver-verified, engine-derived); this island only reveals them. Two response
  // modes (ADR-0032): a **categorical** question (which reagent limits) is a multiple-choice menu; the
  // **numeric** questions (mass, leftover) are FREE ENTRY — the learner types the number, and a wrong entry
  // that matches a named mistake is named, rather than a menu whose wrong values could be eliminated on sight.
  let { question } = $props();
  const q = question;

  // choice mode
  let picked = $state(null);
  const pick = (i) => { if (picked === null) picked = i; };
  const choiceClass = (i) => {
    if (picked === null) return "idle";
    if (q.choices[i].correct) return "correct";
    return i === picked ? "wrong" : "dim";
  };

  // numeric mode
  let entry = $state("");
  let submitted = $state(false);
  let outcome = $state(null); // { correct } | { correct:false, diag } | { gaveUp:true }

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
    if (!Number.isFinite(val)) return;
    submitted = true;
    if (relClose(val, Number(q.answer.value))) outcome = { correct: true };
    else outcome = { correct: false, diag: (q.diagnostics ?? []).find((d) => relClose(val, Number(d.value))) ?? null };
  }
  function giveUp() {
    if (submitted) return;
    submitted = true;
    outcome = { correct: false, gaveUp: true };
  }

  const revealed = $derived(q.mode === "numeric" ? submitted : picked !== null);
</script>

<div class="q">
  <p class="prompt">{q.prompt}</p>

  {#if q.mode === "choice"}
    <ul class="choices" role="list">
      {#each q.choices as c, i}
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
    <p class="explain"><span class="tag">Why</span> {q.explain}</p>
  {/if}
</div>

<style>
  .q { background: var(--paper); border: 1px solid var(--line); border-radius: var(--radius); padding: 0.9rem 1.1rem; }
  .prompt { margin: 0 0 0.7rem; font-weight: 500; }
  .choices { list-style: none; padding: 0; margin: 0; display: grid; gap: 0.4rem; }
  .choice {
    width: 100%; text-align: left; font: inherit; cursor: pointer; display: flex; align-items: center; gap: 0.5rem;
    background: var(--paper-2); border: 1px solid var(--line); border-radius: 8px; padding: 0.5rem 0.7rem; color: var(--ink);
  }
  .choice:disabled { cursor: default; }
  .choice.idle:hover { border-color: var(--accent); }
  .choice.correct { background: var(--accent-soft); border-color: color-mix(in srgb, var(--accent) 45%, transparent); color: var(--accent); font-weight: 600; }
  .choice.wrong { background: var(--warn-soft); border-color: color-mix(in srgb, var(--warn) 45%, transparent); color: var(--warn); }
  .choice.dim { opacity: 0.55; }
  .mark { width: 1rem; font-weight: 700; }
  .mis { margin: 0.3rem 0 0.2rem 1.5rem; font-size: 0.86rem; color: var(--warn); }

  .entry { display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap; }
  .num {
    font: inherit; font-family: var(--font-mono); width: 10rem; max-width: 55vw; padding: 0.45rem 0.65rem;
    border: 1px solid var(--line); border-radius: 8px; background: var(--paper-2); color: var(--ink);
  }
  .num:focus { outline: none; border-color: var(--accent); box-shadow: 0 0 0 2px var(--accent-soft); }
  .num:disabled { opacity: 0.75; }
  .entry .unit { font-family: var(--font-mono); color: var(--accent); font-weight: 600; margin-left: -0.15rem; }
  .check { font: inherit; cursor: pointer; background: var(--accent); color: white; border: none; border-radius: 8px; padding: 0.45rem 0.9rem; font-weight: 600; }
  .check:hover:enabled { filter: brightness(1.05); }
  .check:disabled { opacity: 0.5; cursor: default; }
  .giveup { font: inherit; cursor: pointer; background: transparent; color: var(--ink-faint); border: 1px solid var(--line); border-radius: 8px; padding: 0.45rem 0.75rem; }
  .giveup:hover:enabled { border-color: var(--accent); color: var(--ink-2); }
  .giveup:disabled { opacity: 0.4; cursor: default; }

  .verdict { margin-top: 0.6rem; font-size: 0.95rem; display: flex; align-items: center; gap: 0.35rem; flex-wrap: wrap; }
  .verdict.ok { color: var(--accent); font-weight: 600; }
  .verdict.no { color: var(--ink-2); }
  .verdict .you { font-family: var(--font-mono); color: var(--warn); }
  .verdict .mark { width: auto; }

  .explain { margin: 0.7rem 0 0; font-size: 0.9rem; color: var(--ink-2); }
  .tag { font-size: 0.7rem; text-transform: uppercase; font-weight: 700; color: var(--accent); background: var(--accent-soft); padding: 0.05rem 0.4rem; border-radius: 5px; margin-right: 0.4rem; }
</style>
