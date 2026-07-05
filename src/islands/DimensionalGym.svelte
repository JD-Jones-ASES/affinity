<script>
  // The generic gym drill (Phase 1, ADR-0024): steps producer-generated, machine-verified problems from any
  // family. Pick an answer → the reveal shows the worked reasoning (the CANCELLATION CHAIN for conversion
  // gyms, when present) and, for a wrong pick, exactly which named mistake it was. Computes nothing; every
  // value and every distractor came from the producer and was re-derived by validate-gyms.mjs.
  let { gym } = $props();
  const problems = gym.problems;

  let idx = $state(0);
  let picked = $state(null);
  let score = $state(0);
  let answered = $state(0);

  const q = $derived(problems[idx]);
  const finished = $derived(idx >= problems.length);

  function pick(i) {
    if (picked !== null) return;
    picked = i;
    answered += 1;
    if (q.choices[i].correct) score += 1;
  }
  function next() { picked = null; idx += 1; }
  function restart() { idx = 0; picked = null; score = 0; answered = 0; }

  const choiceClass = (i) => {
    if (picked === null) return "idle";
    if (q.choices[i].correct) return "correct";
    return i === picked ? "wrong" : "dim";
  };
</script>

<div class="gym">
  {#if !finished}
    <div class="bar">
      <span class="pos">Problem {idx + 1} <span class="of">/ {problems.length}</span></span>
      <span class="score">Score {score}/{answered}</span>
    </div>

    <p class="prompt">{q.prompt}</p>

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

    {#if picked !== null}
      <div class="reveal">
        {#if q.chain}
          <div class="chain-label">Follow the units — each factor cancels into the next:</div>
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
        <p class="explain"><span class="tag">Why</span> {q.explain}</p>
        <button class="next" onclick={next}>{idx + 1 < problems.length ? "Next problem →" : "See results →"}</button>
      </div>
    {/if}
  {:else}
    <div class="results">
      <div class="big">{score} / {problems.length}</div>
      <p class="muted">{score === problems.length ? "Perfect — every unit cancelled." : "Units are a skill; run it again and watch the cancellations."}</p>
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

  .reveal { background: var(--paper-2); border: 1px solid var(--line); border-radius: var(--radius); padding: 0.9rem 1.1rem; display: grid; gap: 0.7rem; }
  .chain-label { font-size: 0.82rem; color: var(--ink-faint); }
  .chain-flow { display: flex; align-items: flex-start; gap: 0.4rem; flex-wrap: wrap; }
  .cq { background: var(--paper); border: 1px solid var(--line); border-radius: 8px; padding: 0.4rem 0.6rem; text-align: center; min-width: 5rem; }
  .cv { font-family: var(--font-mono); font-weight: 600; font-size: 1.02rem; }
  .cu { font-family: var(--font-mono); color: var(--accent); margin-left: 0.25rem; }
  .cn { display: block; font-size: 0.7rem; color: var(--ink-faint); margin-top: 0.15rem; }
  .arrow { color: var(--ink-faint); font-size: 1.2rem; align-self: center; }
  .explain { margin: 0; font-size: 0.9rem; color: var(--ink-2); }
  .tag { font-size: 0.7rem; text-transform: uppercase; font-weight: 700; color: var(--accent); background: var(--accent-soft); padding: 0.05rem 0.4rem; border-radius: 5px; margin-right: 0.4rem; }

  .next { justify-self: start; font: inherit; cursor: pointer; background: var(--accent); color: white; border: none; border-radius: 8px; padding: 0.45rem 0.9rem; font-weight: 600; }
  .next:hover { filter: brightness(1.05); }

  .results { text-align: center; display: grid; gap: 0.6rem; justify-items: center; padding: 1.5rem 0; }
  .big { font-size: 2.6rem; font-weight: 700; color: var(--accent); font-family: var(--font-mono); }
</style>
