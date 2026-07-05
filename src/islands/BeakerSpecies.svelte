<script>
  // The beaker / species view (ADR-0011): what's actually in solution. BEFORE mixing, two beakers of FREE
  // IONS (not intact CaCl2 / Na2CO3 molecules — misconception target). AFTER mixing, the solid precipitate
  // forms, the spectator ions stay dissolved (they don't vanish — misconception target), and the excess
  // reacting ion is left over. Particle counts are representative (schematic), scaled from the parity-verified
  // ion amounts; the honest mole numbers are the readouts. Drag the sliders: the limiting ion is consumed and
  // the leftover species switches.
  import { prettyIon } from "../lib/view.js";

  let { interactive } = $props();
  const ix = interactive;

  const compile = (expr) => new Function(...ix.closed_form_params, `"use strict"; return (${expr});`);
  const fns = Object.fromEntries(Object.entries(ix.closed_form).map(([k, e]) => [k, compile(e)]));

  let vals = $state(Object.fromEntries(ix.params.map((p) => [p.name, Number(p.default)])));
  let phase = $state("before");
  const args = $derived(ix.closed_form_params.map((p) => vals[p]));
  const ev = (k) => fns[k](...args);

  const catId = prettyIon(ix.cation.id), anId = prettyIon(ix.anion.id);
  const spec1 = ix.spectators[0], spec2 = ix.spectators[1]; // cation-side (e.g. Cl-), anion-side (e.g. Na+)
  const spec1Id = prettyIon(spec1.id), spec2Id = prettyIon(spec2.id);
  const solidId = prettyIon(ix.product.id);

  const SCALE = 2000, CAP = 14;
  const N = (amt) => (amt <= 1e-12 ? 0 : Math.min(CAP, Math.max(1, Math.round(amt * SCALE))));
  const mmol = (m) => { const v = m * 1000; return (Math.abs(v) >= 10 ? v.toFixed(1) : v.toFixed(2)).replace(/\.?0+$/, "") || "0"; };

  // deterministic jittered slot grid for a beaker region, shuffled so species scatter spatially (no Math.random)
  function slots(x0, y0, w, h, cols, rows) {
    const out = [];
    for (let r = 0; r < rows; r++)
      for (let c = 0; c < cols; c++) {
        const s = r * cols + c;
        const jx = Math.sin(s * 12.9898) * 0.42, jy = Math.cos(s * 4.1414) * 0.42;
        out.push({ x: x0 + (c + 0.5 + jx) * (w / cols), y: y0 + (r + 0.5 + jy) * (h / rows), k: Math.sin(s * 7.77) });
      }
    return out.sort((a, b) => a.k - b.k);
  }
  // lay a list of {cls, n} groups into a slot array, in order
  function place(groups, slotArr) {
    const pts = [];
    let i = 0;
    for (const g of groups)
      for (let j = 0; j < g.n && i < slotArr.length; j++, i++)
        pts.push({ ...slotArr[i], cls: g.cls });
    return pts;
  }

  const nCat = $derived(N(ev("n_cation"))), nAn = $derived(N(ev("n_anion")));
  const nS1 = $derived(N(ev(spec1.key))), nS2 = $derived(N(ev(spec2.key)));
  const nSolid = $derived(N(ev("xi")));
  const nLeftCat = $derived(N(ev("leftover_cation"))), nLeftAn = $derived(N(ev("leftover_anion")));

  // BEFORE: two beakers of free ions
  const leftSlots = slots(30, 70, 150, 130, 6, 5);
  const rightSlots = slots(260, 70, 150, 130, 6, 5);
  const leftPts = $derived(place([{ cls: "c-cat", n: nCat }, { cls: "c-s1", n: nS1 }], leftSlots));
  const rightPts = $derived(place([{ cls: "c-an", n: nAn }, { cls: "c-s2", n: nS2 }], rightSlots));

  // AFTER: one beaker — spectators + the excess reacting ion scattered; solid piled at the bottom
  const afterSlots = slots(150, 60, 190, 110, 8, 4);
  const afterPts = $derived(place([
    { cls: "c-s1", n: nS1 }, { cls: "c-s2", n: nS2 },
    { cls: "c-cat", n: nLeftCat }, { cls: "c-an", n: nLeftAn },
  ], afterSlots));
  const solidSlots = slots(165, 188, 160, 34, 10, 2);
  const solidPts = $derived(place([{ cls: "c-solid", n: nSolid }], solidSlots));

  const excess = $derived(ev("leftover_cation") > 1e-12 ? catId : ev("leftover_anion") > 1e-12 ? anId : null);
</script>

<div class="beaker">
  <div class="phasetabs" role="tablist">
    <button role="tab" aria-selected={phase === "before"} onclick={() => (phase = "before")}>Before mixing</button>
    <button role="tab" aria-selected={phase === "after"} onclick={() => (phase = "after")}>After mixing</button>
  </div>

  {#if phase === "before"}
    <svg viewBox="0 0 440 250" role="img" aria-label="Two beakers of free ions before mixing">
      {#each [{ x: 20, w: 170, label: prettyIon(spec1.source), ions: `${catId} + ${spec1Id}` }, { x: 250, w: 170, label: prettyIon(spec2.source), ions: `${anId} + ${spec2Id}` }] as bk}
        <path d={`M${bk.x} 55 L${bk.x} 215 Q${bk.x} 225 ${bk.x + 10} 225 L${bk.x + bk.w - 10} 225 Q${bk.x + bk.w} 225 ${bk.x + bk.w} 215 L${bk.x + bk.w} 55`} class="glass" />
        <line x1={bk.x} y1={65} x2={bk.x + bk.w} y2={65} class="liquid-top" />
        <text x={bk.x + bk.w / 2} y={244} class="beaker-lbl" text-anchor="middle">{bk.label}(aq) — free ions</text>
      {/each}
      {#each leftPts as p}<circle cx={p.x} cy={p.y} r="6" class={p.cls} />{/each}
      {#each rightPts as p}<circle cx={p.x} cy={p.y} r="6" class={p.cls} />{/each}
    </svg>
    <p class="annot">In solution these salts are <strong>free ions</strong> — {catId} and {spec1Id} drifting
      apart on the left, {anId} and {spec2Id} on the right. There are no intact {prettyIon(spec1.source)} or
      {prettyIon(spec2.source)} molecules floating around; that is the misconception this view kills.</p>
  {:else}
    <svg viewBox="0 0 440 250" role="img" aria-label="One beaker after mixing: solid precipitate plus spectator ions">
      <path d="M120 45 L120 215 Q120 225 130 225 L330 225 Q340 225 340 215 L340 45" class="glass" />
      <line x1={120} y1={55} x2={340} y2={55} class="liquid-top" />
      <rect x={122} y={183} width={216} height={40} class="settle" />
      {#each afterPts as p}<circle cx={p.x} cy={p.y} r="6" class={p.cls} />{/each}
      {#each solidPts as p}<rect x={p.x - 4} y={p.y - 4} width="8" height="8" class={p.cls} />{/each}
      <text x={230} y={244} class="beaker-lbl" text-anchor="middle">{solidId}(s) settles; spectators stay dissolved</text>
    </svg>
    <p class="annot">
      The <span class="sw c-solid"></span><strong>{solidId}(s)</strong> lattice forms and settles.
      The spectators <span class="sw c-s1"></span>{spec1Id} and <span class="sw c-s2"></span>{spec2Id}
      <strong>remain dissolved</strong> — they don't disappear.
      {#if excess}The excess <strong>{excess}</strong> is left over ({mmol(Math.max(ev("leftover_cation"), ev("leftover_anion")))} mmol);
        the limiting ion is fully consumed.{:else}Both reacting ions are used up exactly.{/if}
    </p>
  {/if}

  <div class="legend">
    <span class="li"><span class="sw c-cat"></span>{catId}</span>
    <span class="li"><span class="sw c-an"></span>{anId}</span>
    <span class="li"><span class="sw c-s1"></span>{spec1Id}</span>
    <span class="li"><span class="sw c-s2"></span>{spec2Id}</span>
    <span class="li"><span class="sw c-solid sq"></span>{solidId}(s)</span>
    <span class="li faint">dots are representative, not literal counts</span>
  </div>

  <div class="sliders">
    {#each ix.params as p}
      <label>
        <span class="pname">{prettyIon(p.label)} = {vals[p.name]}{p.unit === "M" ? "" : " "}{p.unit}</span>
        <input type="range" min={Number(p.min)} max={Number(p.max)} step={Number(p.step)} bind:value={vals[p.name]} />
      </label>
    {/each}
  </div>
</div>

<style>
  .beaker { display: grid; gap: 0.6rem; }
  .phasetabs { display: flex; gap: 0.4rem; }
  .phasetabs button { border: 1px solid var(--line); background: var(--paper); color: var(--ink-2); border-radius: 999px; padding: 0.25rem 0.8rem; cursor: pointer; font: inherit; font-size: 0.85rem; }
  .phasetabs button[aria-selected="true"] { background: var(--accent-soft); color: var(--accent); border-color: color-mix(in srgb, var(--accent) 30%, transparent); font-weight: 600; }
  svg { width: 100%; height: auto; background: var(--paper); border: 1px solid var(--line); border-radius: var(--radius); }
  .glass { fill: color-mix(in srgb, var(--accent) 5%, transparent); stroke: var(--ink-faint); stroke-width: 1.5; }
  .liquid-top { stroke: color-mix(in srgb, var(--accent) 40%, transparent); stroke-width: 1.5; }
  .settle { fill: color-mix(in srgb, var(--solid) 14%, transparent); }
  .beaker-lbl { fill: var(--ink-faint); font-size: 11px; font-family: var(--font-mono); }
  circle.c-cat { fill: var(--ion-ca); } circle.c-an { fill: var(--ion-co3); }
  circle.c-s1 { fill: var(--ion-cl); } circle.c-s2 { fill: var(--ion-na); }
  rect.c-solid { fill: var(--solid); stroke: color-mix(in srgb, var(--ink) 25%, var(--solid)); stroke-width: 0.5; }

  .annot { margin: 0; font-size: 0.92rem; color: var(--ink-2); line-height: 1.5; }
  .legend { display: flex; flex-wrap: wrap; gap: 0.5rem 0.9rem; font-size: 0.82rem; color: var(--ink-2); align-items: center; }
  .li { display: inline-flex; align-items: center; gap: 0.3rem; }
  .sw { width: 0.7rem; height: 0.7rem; border-radius: 50%; display: inline-block; }
  .sw.sq { border-radius: 2px; }
  .sw.c-cat { background: var(--ion-ca); } .sw.c-an { background: var(--ion-co3); }
  .sw.c-s1 { background: var(--ion-cl); } .sw.c-s2 { background: var(--ion-na); }
  .sw.c-solid { background: var(--solid); }
  .sliders { display: grid; gap: 0.35rem; padding-top: 0.2rem; }
  .sliders label { display: grid; grid-template-columns: 12rem 1fr; align-items: center; gap: 0.8rem; }
  .pname { font-family: var(--font-mono); font-size: 0.82rem; }
  .sliders input[type="range"] { width: 100%; accent-color: var(--accent); }
  @media (max-width: 30rem) { .sliders label { grid-template-columns: 1fr; gap: 0.1rem; } }
</style>
