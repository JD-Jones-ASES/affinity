<script>
  // The extent-bar instrument (ADR-0011): two "capacity" bars — how far each reacting ion can drive the
  // reaction (moles ÷ its net-ionic coefficient). The shorter one runs out first and caps the extent ξ; the
  // taller one keeps a leftover above the ξ line. Drag the sliders and the limiting reagent switches — the
  // whole point. Every number comes from a parity-verified closed form (check-parity.mjs); nothing is
  // computed here that the engine hasn't proven.
  import { prettyIon } from "../lib/view.js";

  let { interactive, precipitateSymbol } = $props();
  const ix = interactive;

  const compile = (expr) => new Function(...ix.closed_form_params, `"use strict"; return (${expr});`);
  const fns = Object.fromEntries(Object.entries(ix.closed_form).map(([k, e]) => [k, compile(e)]));

  // slider state, seeded from the emitted defaults
  let vals = $state(Object.fromEntries(ix.params.map((p) => [p.name, Number(p.default)])));
  const args = $derived(ix.closed_form_params.map((p) => vals[p]));
  const ev = (k) => fns[k](...args);

  const nCat = $derived(ev("n_cation"));
  const nAn = $derived(ev("n_anion"));
  const xi = $derived(ev("xi"));
  const mass = $derived(ev("mass"));
  const leftCat = $derived(ev("leftover_cation"));
  const leftAn = $derived(ev("leftover_anion"));

  const aCat = ix.cation.net_coeff, aAn = ix.anion.net_coeff;
  const capCat = $derived(nCat / aCat);
  const capAn = $derived(nAn / aAn);
  const catId = prettyIon(ix.cation.id), anId = prettyIon(ix.anion.id);

  // limiting verdict (tie when within a hair)
  const limiting = $derived(Math.abs(capCat - capAn) < 1e-12 ? "both" : capCat < capAn ? "cat" : "an");

  // geometry — auto-scaled to the taller bar so the comparison stays readable across the whole slider range
  const W = 440, H = 250, BASE = 200, TOP = 26;
  const usable = BASE - TOP;
  const maxCap = $derived(Math.max(capCat, capAn, 1e-9));
  const barH = (c) => (c / maxCap) * usable;
  const xiY = $derived(BASE - barH(xi));

  const mmol = (m) => {
    const v = m * 1000;
    return (Math.abs(v) >= 10 ? v.toFixed(1) : v.toFixed(2)).replace(/\.?0+$/, "") || "0";
  };
  const gDisp = (g) => (g >= 1 ? g.toFixed(2) : g.toFixed(3));
  const bars = $derived([
    { key: "cat", x: 120, cap: capCat, id: catId, cls: "cat", limits: limiting === "cat" || limiting === "both" },
    { key: "an", x: 260, cap: capAn, id: anId, cls: "an", limits: limiting === "an" || limiting === "both" },
  ]);
  const BW = 84;
</script>

<div class="extent">
  <svg viewBox={`0 0 ${W} ${H}`} role="img"
       aria-label="Extent bars: each reacting ion's capacity to drive the reaction; the shorter one limits and caps the extent.">
    <!-- the ξ line: how far the reaction actually runs before a reactant hits zero -->
    <line x1={70} y1={xiY} x2={W - 20} y2={xiY} class="xiline" />
    <text x={W - 20} y={xiY - 5} class="xilbl" text-anchor="end">ξ reached</text>

    {#each bars as b}
      <!-- full capacity outline -->
      <rect x={b.x} y={BASE - barH(b.cap)} width={BW} height={barH(b.cap)} class={`cap ${b.cls}`} />
      <!-- consumed portion (0 .. ξ) -->
      <rect x={b.x} y={xiY} width={BW} height={Math.max(0, BASE - xiY)} class={`used ${b.cls}`} />
      <line x1={b.x} y1={BASE} x2={b.x + BW} y2={BASE} class="axis" />
      <text x={b.x + BW / 2} y={BASE + 16} class="lbl sym" text-anchor="middle">{b.id}</text>
      <text x={b.x + BW / 2} y={BASE + 30} class="lbl" text-anchor="middle">{b.limits ? "limiting" : "excess"}</text>
      {#if b.cap - xi > 1e-12}
        <text x={b.x + BW / 2} y={(BASE - barH(b.cap) + xiY) / 2} class="leftlbl" text-anchor="middle">leftover</text>
      {/if}
    {/each}
  </svg>

  <div class="readout">
    <div class="r"><span class="rl">Extent ξ</span><span class="rv">{mmol(xi)}<span class="ru">mmol</span></span></div>
    <div class="r"><span class="rl">{precipitateSymbol} formed</span><span class="rv">{gDisp(mass)}<span class="ru">g</span></span></div>
    <div class="r"><span class="rl">Left over</span><span class="rv">
      {#if leftCat > 1e-12}{catId} {mmol(leftCat)}<span class="ru">mmol</span>
      {:else if leftAn > 1e-12}{anId} {mmol(leftAn)}<span class="ru">mmol</span>
      {:else}none (exact){/if}</span></div>
  </div>

  <p class="annot">
    {#if limiting === "both"}
      Exactly matched — both ions run out together at ξ = <strong>{mmol(xi)} mmol</strong>, so nothing is left over.
    {:else}
      <strong>{limiting === "cat" ? catId : anId}</strong> runs out first — it <strong>limits</strong> the reaction
      at ξ = <strong>{mmol(xi)} mmol</strong>, leaving {limiting === "cat" ? anId : catId} in excess. The
      precipitate mass tracks ξ. Raise the limiting ion’s volume or concentration and watch the taller bar —
      and the limiting reagent — switch.
    {/if}
  </p>

  <div class="sliders">
    {#each ix.params as p}
      <label>
        <span class="pname">{p.label} = {vals[p.name]}{p.unit === "M" ? "" : " "}{p.unit}</span>
        <input type="range" min={Number(p.min)} max={Number(p.max)} step={Number(p.step)} bind:value={vals[p.name]} />
      </label>
    {/each}
  </div>
</div>

<style>
  .extent { display: grid; gap: 0.6rem; }
  svg { width: 100%; height: auto; background: var(--paper); border: 1px solid var(--line); border-radius: var(--radius); }
  .cap.cat { fill: color-mix(in srgb, var(--ion-ca) 22%, transparent); stroke: var(--ion-ca); stroke-width: 1; }
  .cap.an { fill: color-mix(in srgb, var(--ion-co3) 22%, transparent); stroke: var(--ion-co3); stroke-width: 1; }
  .used.cat { fill: var(--ion-ca); }
  .used.an { fill: var(--ion-co3); }
  .axis { stroke: var(--ink-faint); stroke-width: 1.5; }
  .xiline { stroke: var(--accent); stroke-width: 1.6; stroke-dasharray: 5 3; }
  .xilbl { fill: var(--accent); font-size: 11px; font-family: var(--font-mono); }
  .lbl { fill: var(--ink-faint); font-size: 11px; font-family: var(--font-mono); }
  .lbl.sym { fill: var(--ink); font-size: 13px; font-weight: 600; }
  .leftlbl { fill: var(--ink-faint); font-size: 10px; font-family: var(--font-mono); }

  .readout { display: grid; grid-template-columns: repeat(auto-fit, minmax(9rem, 1fr)); gap: 0.5rem; }
  .r { background: var(--paper); border: 1px solid var(--line); border-radius: 8px; padding: 0.5rem 0.7rem; }
  .rl { display: block; font-size: 0.75rem; color: var(--ink-faint); }
  .rv { font-family: var(--font-mono); font-weight: 600; font-size: 1.05rem; }
  .ru { font-size: 0.8rem; color: var(--ink-2); margin-left: 0.2rem; font-weight: 400; }

  .annot { margin: 0; font-size: 0.92rem; color: var(--ink-2); line-height: 1.5; }
  .sliders { display: grid; gap: 0.35rem; padding-top: 0.2rem; }
  .sliders label { display: grid; grid-template-columns: 12rem 1fr; align-items: center; gap: 0.8rem; }
  .pname { font-family: var(--font-mono); font-size: 0.82rem; }
  .sliders input[type="range"] { width: 100%; accent-color: var(--accent); }
  @media (max-width: 30rem) { .sliders label { grid-template-columns: 1fr; gap: 0.1rem; } }
</style>
