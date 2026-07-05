<script>
  // One generated practice item (ADR-0011, brief §6.8). The answer and every distractor came from the
  // producer (solver-verified, engine-derived); this island only reveals them. Pick a choice → see whether
  // it's right, why each wrong option is a specific misconception, and the worked explanation.
  let { question } = $props();
  const q = question;
  let picked = $state(null);

  const pick = (i) => { if (picked === null) picked = i; };
  // NB: don't name this `state` — that collides with Svelte 5's internal `state` import (used to compile
  // `$state`) and throws "Cannot access 'state' before initialization" at component init.
  const choiceClass = (i) => {
    if (picked === null) return "idle";
    if (q.choices[i].correct) return "correct";
    return i === picked ? "wrong" : "dim";
  };
</script>

<div class="q">
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
  .explain { margin: 0.7rem 0 0; font-size: 0.9rem; color: var(--ink-2); }
  .tag { font-size: 0.7rem; text-transform: uppercase; font-weight: 700; color: var(--accent); background: var(--accent-soft); padding: 0.05rem 0.4rem; border-radius: 5px; margin-right: 0.4rem; }
</style>
