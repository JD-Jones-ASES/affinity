<script>
  // The Valence Table flagship (brief §8, ADR-0033): four modes over one committed, machine-verified table.
  //   • Explore — the grid with five LENSES (ion charge, valence electrons, electronegativity, covalent
  //     radius, first ionization energy). Each lens colors the sourced values and opens a pattern panel
  //     (what pattern / why / exceptions / where) — the "why" renders under the interpretive marker
  //     (regime 4, Q4 resolved): a useful story, not a machine proof; the colored data is the evidence.
  //   • Trends — an SVG graph of the sourced values across a period or down a group. Gaps (noble-gas EN,
  //     transition-metal radii) render as gaps, never interpolated.
  //   • Formula builder — pick a cation and an anion; every pair's neutral formula was assembled by charge
  //     crossover, machine-verified, and NAMED by the producer; the classic own-charge mistake is shown
  //     proven wrong where it differs.
  //   • Bonding — pick two elements; ΔEN is computed by INTEGER arithmetic over build-time ×100 values
  //     (exact) and classified against the sourced OpenStax thresholds, caution always attached.
  // No chemistry runs here: every value, name, threshold, and mistake came from the producer and was
  // re-derived by validate-reference.mjs.
  let { table } = $props();
  const t = table;

  const bySym = Object.fromEntries(t.elements.map((e) => [e.symbol, e]));

  // ---------- modes ----------
  const MODES = [
    { id: "explore", label: "Explore" },
    { id: "trends", label: "Trends" },
    { id: "formula", label: "Formula builder" },
    { id: "bonding", label: "Bonding" },
  ];
  let mode = $state("explore");

  // ---------- explore: lenses + selection ----------
  let lensId = $state("ion-charge");
  const lens = $derived(t.lenses.find((l) => l.id === lensId));
  const numericLens = $derived(lens.property !== "common_ion");

  // color intensity: normalize the lens property across the elements that carry it (presentation only)
  const lensStats = $derived.by(() => {
    if (!numericLens) return null;
    const vals = t.elements.map((e) => e[lens.property]).filter((v) => v != null).map(Number);
    return { min: Math.min(...vals), max: Math.max(...vals) };
  });
  function lensShade(e) {
    const v = e[lens.property];
    if (v == null || !lensStats) return null;
    const f = lensStats.max === lensStats.min ? 0.5 : (Number(v) - lensStats.min) / (lensStats.max - lensStats.min);
    return Math.round(8 + f * 54); // 8%..62% accent mix
  }
  const lensValue = (e) => (lens.property === "valence_electrons" ? e.valence_electrons : e[lens.property]);

  let sel = $state({ type: "element", key: t.highlight[0] ?? t.elements[0].symbol });
  const chargeLabel = (n) => { const s = n > 0 ? "+" : "−"; const m = Math.abs(n); return m === 1 ? s : `${m}${s}`; };
  const selElement = $derived(sel.type === "element" ? bySym[sel.key] : null);
  const selPoly = $derived(sel.type === "poly" ? t.polyatomic.find((p) => p.id === sel.key) : null);
  const selIonId = $derived(selElement?.common_ion?.id ?? selPoly?.id ?? null);
  const salts = $derived(selIonId ? t.charge_balance.filter((c) => c.cation === selIonId || c.anion === selIonId) : []);
  const isHi = (sym) => t.highlight.includes(sym);

  // ---------- trends ----------
  const TREND_PROPS = [
    { key: "electronegativity", label: "Electronegativity", unit: "" },
    { key: "covalent_radius_pm", label: "Covalent radius", unit: "pm" },
    { key: "first_ionization_kj_mol", label: "First ionization energy", unit: "kJ/mol" },
  ];
  const SERIES = [
    ...[...new Set(t.elements.map((e) => e.period))].sort((a, b) => a - b)
      .map((n) => ({ kind: "period", n, label: `Period ${n}` })),
    ...[...new Set(t.elements.map((e) => e.group))].sort((a, b) => a - b)
      .filter((n) => t.elements.filter((e) => e.group === n).length >= 2)
      .map((n) => ({ kind: "group", n, label: `Group ${n}` })),
  ].filter((s) => s.kind === "group" || t.elements.filter((e) => e.period === s.n).length >= 2);
  let trendProp = $state("first_ionization_kj_mol");
  let seriesKey = $state("period|2");
  const series = $derived(SERIES.find((s) => `${s.kind}|${s.n}` === seriesKey) ?? SERIES[0]);
  const trendMeta = $derived(TREND_PROPS.find((p) => p.key === trendProp));
  const trendLens = $derived(t.lenses.find((l) => l.property === trendProp));

  const CHART = { w: 560, h: 230, padX: 40, padTop: 26, padBottom: 34 };
  const trendData = $derived.by(() => {
    const members = t.elements
      .filter((e) => (series.kind === "period" ? e.period === series.n : e.group === series.n))
      .sort((a, b) => (series.kind === "period" ? a.group - b.group : a.period - b.period));
    const defined = members.filter((e) => e[trendProp] != null);
    const vals = defined.map((e) => Number(e[trendProp]));
    const min = vals.length ? Math.min(...vals) : 0;
    const max = vals.length ? Math.max(...vals) : 1;
    const span = max - min || 1;
    const step = members.length > 1 ? (CHART.w - 2 * CHART.padX) / (members.length - 1) : 0;
    const points = members.map((e, i) => {
      const x = CHART.padX + i * step;
      const has = e[trendProp] != null;
      const y = has
        ? CHART.h - CHART.padBottom - ((Number(e[trendProp]) - min) / span) * (CHART.h - CHART.padTop - CHART.padBottom)
        : CHART.h - CHART.padBottom;
      return { e, x, y, has, value: e[trendProp] };
    });
    return { points, polyline: points.filter((p) => p.has).map((p) => `${p.x},${p.y}`).join(" ") };
  });
  const partialPeriod = $derived(series.kind === "period" && series.n === 4);

  // ---------- formula builder ----------
  const seen = new Set();
  const cationChips = t.charge_balance.filter((c) => !seen.has(c.cation) && seen.add(c.cation))
    .map((c) => ({ id: c.cation, pretty: c.cationPretty, name: c.cation_name }));
  seen.clear();
  const anionChips = t.charge_balance.filter((c) => !seen.has(c.anion) && seen.add(c.anion))
    .map((c) => ({ id: c.anion, pretty: c.anionPretty, name: c.anion_name }));
  let pickCat = $state("Ca^2+");
  let pickAn = $state("CO3^2-");
  const built = $derived(t.charge_balance.find((c) => c.cation === pickCat && c.anion === pickAn));

  // ---------- bonding ----------
  const enElements = t.elements.filter((e) => e.enCents != null);
  let bondA = $state("H");
  let bondB = $state("O");
  const elA = $derived(bySym[bondA]);
  const elB = $derived(bySym[bondB]);
  const dEnCents = $derived(Math.abs(elA.enCents - elB.enCents));
  const dEn = $derived((dEnCents / 100).toFixed(2));
  // classify against the sourced thresholds: strict at the open ends, boundary values fall to the bounded
  // middle class — matching OpenStax's "less than 0.4 / between 0.4 and 1.8 / greater than 1.8" exactly.
  const bondClass = $derived.by(() => {
    const cls = t.bonding?.classes ?? [];
    for (const c of cls) {
      const loOk = c.minCents == null ? true : dEnCents > c.minCents;
      const hiOk = c.maxCents == null ? true : dEnCents < c.maxCents;
      if (loOk && hiOk) return c;
    }
    return cls.find((c) => c.minCents != null && c.maxCents != null && dEnCents >= c.minCents && dEnCents <= c.maxCents) ?? cls[cls.length - 1];
  });
  const SPECTRUM_MAX = 330; // cents; F(3.98) − K(0.82) = 3.16 is the largest ΔEN in this set
  const spectrumPos = $derived(Math.min(100, (dEnCents / SPECTRUM_MAX) * 100));
</script>

<div class="vt">
  <div class="modes" role="tablist" aria-label="Valence Table modes">
    {#each MODES as m}
      <button class="mode {mode === m.id ? 'on' : ''}" role="tab" aria-selected={mode === m.id}
        onclick={() => (mode = m.id)}>{m.label}</button>
    {/each}
  </div>

  {#if mode === "explore"}
    <div class="lenses">
      <span class="lens-cap">Lens:</span>
      {#each t.lenses as l}
        <button class="chip small {lensId === l.id ? 'sel' : ''}" onclick={() => (lensId = l.id)}>{l.label}</button>
      {/each}
    </div>

    <div class="grid" role="grid" aria-label="Periodic table (the elements in this dataset)">
      {#each t.elements as e}
        {@const shade = numericLens ? lensShade(e) : null}
        <button
          class="cell {isHi(e.symbol) ? 'hi' : ''} {sel.type === 'element' && sel.key === e.symbol ? 'sel' : ''} {numericLens ? '' : `b-${e.block}`}"
          style={`grid-column:${e.group}; grid-row:${e.period};` + (shade != null ? ` background: color-mix(in srgb, var(--accent) ${shade}%, var(--paper-2));` : "")}
          onclick={() => (sel = { type: "element", key: e.symbol })}
          aria-label={`${e.name}, ${e.common_ion ? "common ion " + chargeLabel(e.common_ion.charge) : "no simple ion"}`}>
          <span class="z">{e.Z}</span>
          {#if !numericLens && e.common_ion}<span class="ch">{chargeLabel(e.common_ion.charge)}</span>{/if}
          <span class="sym">{e.symbol}</span>
          <span class="aw">{numericLens ? (lensValue(e) ?? "—") : e.atomic_weight}</span>
        </button>
      {/each}
      <div class="legend" style="grid-column:3 / 13; grid-row:1 / 3;">
        <p class="blurb">{numericLens ? `${lens.label}${lens.unit ? ` (${lens.unit})` : ""} — darker is higher. Blank cells carry no curated value.` : t.blurb}</p>
        {#if !numericLens}
          <div class="blocks"><span class="sw b-s"></span>s-block<span class="sw b-p"></span>p-block</div>
        {/if}
      </div>
    </div>

    <div class="panel">
      <p class="panel-head">
        <strong>{lens.label}</strong>
        <span class="badge sourced tiny"><span class="dot"></span>data-sourced ({t.sources[lens.source]})</span>
        <span class="badge model tiny"><span class="dot"></span>interpretive — story, not proof</span>
      </p>
      <dl class="panel-rows">
        <dt>What pattern?</dt><dd>{lens.panel.pattern}</dd>
        <dt>Why (the story)</dt><dd>{lens.panel.why}</dd>
        <dt>Exceptions</dt><dd>{lens.panel.exceptions}</dd>
        <dt>Where it shows up</dt><dd>{lens.panel.where}</dd>
      </dl>
    </div>

    <p class="poly-label">Polyatomic ions — click one:</p>
    <div class="poly">
      {#each t.polyatomic as p}
        <button class="chip {sel.type === 'poly' && sel.key === p.id ? 'sel' : ''}" onclick={() => (sel = { type: "poly", key: p.id })}>
          {@html p.latexHtml} <span class="pn">{p.name}</span>
        </button>
      {/each}
    </div>

    <div class="detail">
      {#if selElement}
        <div class="d-head">
          <span class="d-sym">{selElement.symbol}</span>
          <div>
            <div class="d-name">{selElement.name}</div>
            <div class="d-meta">Z = {selElement.Z} · {selElement.atomic_weight} g/mol · group {selElement.group}, period {selElement.period}{selElement.valence_electrons ? ` · ${selElement.valence_electrons} valence e⁻` : ""}</div>
          </div>
        </div>
        {#if selElement.common_ion}
          <p class="d-ion">Common ion: <strong>{@html selElement.common_ion.latexHtml}</strong> ({selElement.common_ion.name}) —
            charge <strong>{chargeLabel(selElement.common_ion.charge)}</strong>.
            {#if selElement.other_ions}
              also forms {#each selElement.other_ions as o, i}{i > 0 ? ", " : ""}<strong>{@html o.latexHtml}</strong> ({o.name}){/each} — the Stock numeral in a name says which.
            {/if}
            <span class="badge sourced tiny"><span class="dot"></span>rule-sourced ({t.sources.ion_charge})</span></p>
          <p class="d-why muted">{t.group_charge_note}</p>
        {:else}
          <p class="d-ion muted">No simple monatomic ion in this dataset — {selElement.symbol} appears in polyatomic ions and covalent compounds instead.</p>
        {/if}

        {#if selElement.first_ionization_kj_mol || selElement.electronegativity || selElement.covalent_radius_pm}
          <div class="props">
            <p class="props-label">Periodic properties <span class="badge sourced tiny"><span class="dot"></span>data-sourced</span></p>
            <div class="prop-grid">
              {#if selElement.electronegativity}
                <div class="prop"><span class="pk">Electronegativity</span><span class="pv">{selElement.electronegativity}</span><span class="ps">Pauling · {t.sources.electronegativity}</span></div>
              {/if}
              {#if selElement.covalent_radius_pm}
                <div class="prop"><span class="pk">Covalent radius</span><span class="pv">{selElement.covalent_radius_pm} pm</span><span class="ps">{t.sources.covalent_radius}</span></div>
              {/if}
              {#if selElement.first_ionization_kj_mol}
                <div class="prop"><span class="pk">First ionization energy</span><span class="pv">{selElement.first_ionization_kj_mol} kJ/mol</span><span class="ps">{t.sources.ionization_energy}</span></div>
              {/if}
            </div>
            {#if !selElement.electronegativity}<p class="prop-note faint">Electronegativity is undefined for the noble gases on the Pauling scale.</p>{/if}
          </div>
        {/if}
      {:else if selPoly}
        <div class="d-head">
          <span class="d-sym poly-sym">{@html selPoly.latexHtml}</span>
          <div>
            <div class="d-name">{selPoly.name}</div>
            <div class="d-meta">polyatomic ion · charge {chargeLabel(selPoly.charge)}</div>
          </div>
        </div>
        <p class="d-ion">A charged group of atoms that stays together through the reaction. Charge <strong>{chargeLabel(selPoly.charge)}</strong>.
          <span class="badge sourced tiny"><span class="dot"></span>rule-sourced ({t.sources.ion_charge})</span></p>
      {/if}

      {#if salts.length}
        <div class="salts">
          <p class="salts-label">Neutral formulas from charge balance <span class="badge machine tiny"><span class="dot"></span>verified</span></p>
          <div class="salt-scroll">
            {#each salts as c}
              <div class="salt">
                <span class="ion">{c.cationPretty}</span> + <span class="ion">{c.anionPretty}</span>
                <span class="arrow">→</span> <strong>{@html c.latexHtml}</strong>
                <span class="sname muted">{c.name}</span>
                <span class="cross faint">{c.note}</span>
              </div>
            {/each}
          </div>
          <p class="hint faint">The subscripts aren't guessed — they're whatever makes the total charge zero (charge crossover), then re-checked atom-by-atom. Try any pair in the Formula builder.</p>
        </div>
      {/if}
    </div>

  {:else if mode === "trends"}
    <div class="lenses">
      <span class="lens-cap">Property:</span>
      {#each TREND_PROPS as p}
        <button class="chip small {trendProp === p.key ? 'sel' : ''}" onclick={() => (trendProp = p.key)}>{p.label}</button>
      {/each}
    </div>
    <div class="lenses">
      <span class="lens-cap">Series:</span>
      {#each SERIES as s}
        <button class="chip small {seriesKey === `${s.kind}|${s.n}` ? 'sel' : ''}" onclick={() => (seriesKey = `${s.kind}|${s.n}`)}>{s.label}</button>
      {/each}
    </div>

    <div class="chart-box">
      <p class="chart-title">{trendMeta.label}{trendMeta.unit ? ` (${trendMeta.unit})` : ""} — {series.label}
        <span class="badge sourced tiny"><span class="dot"></span>data-sourced ({t.sources[trendLens.source]})</span></p>
      <svg viewBox={`0 0 ${CHART.w} ${CHART.h}`} role="img"
        aria-label={`${trendMeta.label} ${series.kind === "period" ? "across" : "down"} ${series.label}`}>
        <line x1={CHART.padX - 10} y1={CHART.h - CHART.padBottom} x2={CHART.w - CHART.padX + 10} y2={CHART.h - CHART.padBottom} class="axis" />
        {#if trendData.polyline.includes(" ")}
          <polyline points={trendData.polyline} class="trendline" />
        {/if}
        {#each trendData.points as p}
          {#if p.has}
            <circle cx={p.x} cy={p.y} r="4" class="dot-pt" />
            <text x={p.x} y={p.y - 9} class="val" text-anchor="middle">{p.value}</text>
            <text x={p.x} y={CHART.h - CHART.padBottom + 16} class="sym-lbl" text-anchor="middle">{p.e.symbol}</text>
          {:else}
            <text x={p.x} y={CHART.h - CHART.padBottom + 16} class="sym-lbl gone" text-anchor="middle">{p.e.symbol}</text>
            <text x={p.x} y={CHART.h - CHART.padBottom - 8} class="gone-mark" text-anchor="middle">—</text>
          {/if}
        {/each}
      </svg>
      <p class="chart-note muted">{trendLens.panel.pattern}
        {#if trendData.points.some((p) => !p.has)}
          <span class="faint">Blank marks carry no curated value ({trendProp === "electronegativity" ? "Pauling electronegativity is undefined for the noble gases" : "transition-metal covalent radii are spin-state-dependent and not yet curated"}) — shown as gaps, never interpolated.</span>
        {/if}
        {#if partialPeriod}<span class="faint">Period 4 is partial — only the curated elements (K, Ca, Fe, Cu, Zn) are shown.</span>{/if}
      </p>
    </div>

  {:else if mode === "formula"}
    <p class="fm-lede muted">Pick a cation and an anion. The producer assembled every pair by charge crossover,
      re-checked it atom-by-atom for neutrality, and named it with the same engine the nomenclature gym drills —
      nothing here is computed in your browser.</p>
    <div class="pickers">
      <div class="picker">
        <p class="picker-label">Cation</p>
        <div class="picker-chips">
          {#each cationChips as c}
            <button class="chip small {pickCat === c.id ? 'sel' : ''}" onclick={() => (pickCat = c.id)}>{c.pretty} <span class="pn">{c.name}</span></button>
          {/each}
        </div>
      </div>
      <div class="picker">
        <p class="picker-label">Anion</p>
        <div class="picker-chips">
          {#each anionChips as a}
            <button class="chip small {pickAn === a.id ? 'sel' : ''}" onclick={() => (pickAn = a.id)}>{a.pretty} <span class="pn">{a.name}</span></button>
          {/each}
        </div>
      </div>
    </div>
    {#if built}
      <div class="built">
        <div class="built-main">
          <span class="ion">{built.cationPretty}</span> + <span class="ion">{built.anionPretty}</span>
          <span class="arrow">→</span> <span class="built-formula">{@html built.latexHtml}</span>
        </div>
        <p class="built-name"><strong>{built.name}</strong>
          <span class="badge machine tiny"><span class="dot"></span>verified neutral</span></p>
        <p class="built-cross">{built.cation_n} × ({built.cationPretty}) and {built.anion_n} × ({built.anionPretty}): {built.note}</p>
        {#if built.mistake}
          <div class="mistake">
            <p class="mk-head">Not <strong>{built.mistake.pretty}</strong> —</p>
            <p class="mk-note">{built.mistake.note}</p>
          </div>
        {/if}
      </div>
    {/if}

  {:else if mode === "bonding"}
    <p class="fm-lede muted">Pick two elements. The difference in their Pauling electronegativities (ΔEN)
      estimates how the bonding electrons are shared — the thresholds are OpenStax's, and OpenStax's own
      caution comes with them.</p>
    <div class="pickers">
      <div class="picker">
        <p class="picker-label">Element A</p>
        <div class="picker-chips">
          {#each enElements as e}
            <button class="chip small {bondA === e.symbol ? 'sel' : ''}" onclick={() => (bondA = e.symbol)}>{e.symbol}</button>
          {/each}
        </div>
      </div>
      <div class="picker">
        <p class="picker-label">Element B</p>
        <div class="picker-chips">
          {#each enElements as e}
            <button class="chip small {bondB === e.symbol ? 'sel' : ''}" onclick={() => (bondB = e.symbol)}>{e.symbol}</button>
          {/each}
        </div>
      </div>
    </div>
    <div class="built">
      <p class="bond-en">EN({elA.symbol}) = {elA.electronegativity} · EN({elB.symbol}) = {elB.electronegativity}
        <span class="badge sourced tiny"><span class="dot"></span>data-sourced ({t.sources.electronegativity})</span></p>
      <p class="bond-den">ΔEN = <strong>{dEn}</strong> → <strong class="bond-class">{bondClass?.label}</strong>
        <span class="badge sourced tiny"><span class="dot"></span>rule-sourced ({t.bonding.source})</span></p>
      <p class="muted">{bondClass?.description}</p>
      <div class="spectrum" role="img" aria-label={`Polarity spectrum: ΔEN ${dEn}, ${bondClass?.label}`}>
        <div class="spec-bar">
          {#each t.bonding.classes as c}
            {#if c.minCents != null}<span class="spec-tick" style={`left:${(c.minCents / SPECTRUM_MAX) * 100}%`}><i>{c.min}</i></span>{/if}
          {/each}
          <span class="spec-marker" style={`left:${spectrumPos}%`}></span>
        </div>
        <div class="spec-labels">
          {#each t.bonding.classes as c}<span>{c.label}</span>{/each}
        </div>
      </div>
      <p class="caution"><span class="badge model tiny"><span class="dot"></span>interpretive — a guide, not a law</span>
        {t.bonding.caution}</p>
    </div>
  {/if}
</div>

<style>
  .vt { display: grid; gap: 0.9rem; }

  .modes { display: flex; gap: 0.35rem; flex-wrap: wrap; border-bottom: 1px solid var(--line); padding-bottom: 0.55rem; }
  .mode { font: inherit; cursor: pointer; background: var(--paper-2); border: 1px solid var(--line); border-radius: 8px; padding: 0.35rem 0.8rem; color: var(--ink-2); font-weight: 600; }
  .mode:hover { border-color: var(--accent); }
  .mode.on { background: var(--accent); border-color: var(--accent); color: white; }

  .lenses { display: flex; align-items: center; gap: 0.35rem; flex-wrap: wrap; }
  .lens-cap { font-size: 0.8rem; color: var(--ink-faint); margin-right: 0.15rem; }

  .grid { display: grid; grid-template-columns: repeat(18, minmax(0, 1fr)); gap: 3px; }
  .cell {
    position: relative; aspect-ratio: 1; min-width: 0; border: 1px solid var(--line); border-radius: 6px;
    background: var(--paper-2); cursor: pointer; font: inherit; color: var(--ink); padding: 2px; overflow: hidden;
    display: flex; flex-direction: column; align-items: center; justify-content: center; line-height: 1;
  }
  .cell.b-s { background: color-mix(in srgb, var(--ion-na) 12%, var(--paper-2)); }
  .cell.b-p { background: color-mix(in srgb, var(--ion-co3) 12%, var(--paper-2)); }
  .cell:hover { border-color: var(--accent); }
  .cell.hi { border-color: var(--ion-ca); box-shadow: 0 0 0 2px color-mix(in srgb, var(--ion-ca) 45%, transparent); }
  .cell.sel { border-color: var(--accent); box-shadow: 0 0 0 2px var(--accent); }
  .cell .sym { font-weight: 700; font-size: clamp(0.7rem, 2.2vw, 1.1rem); }
  .cell .z { position: absolute; top: 2px; left: 3px; font-size: 0.55rem; color: var(--ink-faint); }
  .cell .ch { position: absolute; top: 2px; right: 3px; font-size: 0.6rem; font-weight: 700; color: var(--accent); }
  .cell .aw { font-size: 0.5rem; color: var(--ink-faint); font-family: var(--font-mono); }
  .legend { align-self: center; padding: 0 0.5rem; }
  .legend .blurb { margin: 0; font-size: clamp(0.62rem, 1.4vw, 0.85rem); color: var(--ink-2); line-height: 1.35; }
  .blocks { display: flex; align-items: center; gap: 0.3rem; font-size: 0.72rem; color: var(--ink-faint); margin-top: 0.3rem; flex-wrap: wrap; }
  .blocks .sw { width: 0.7rem; height: 0.7rem; border-radius: 3px; display: inline-block; margin-left: 0.5rem; }
  .blocks .sw.b-s { background: color-mix(in srgb, var(--ion-na) 40%, var(--paper-2)); margin-left: 0; }
  .blocks .sw.b-p { background: color-mix(in srgb, var(--ion-co3) 40%, var(--paper-2)); }

  .panel { background: var(--paper-2); border: 1px solid var(--line); border-radius: var(--radius); padding: 0.85rem 1.05rem; }
  .panel-head { margin: 0 0 0.55rem; display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap; }
  .panel-rows { margin: 0; display: grid; grid-template-columns: auto 1fr; gap: 0.35rem 0.9rem; }
  .panel-rows dt { font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.03em; font-weight: 700; color: var(--ink-faint); padding-top: 0.1rem; white-space: nowrap; }
  .panel-rows dd { margin: 0; font-size: 0.9rem; color: var(--ink-2); }

  .poly-label { margin: 0.2rem 0 0; font-size: 0.85rem; color: var(--ink-faint); }
  .poly { display: flex; flex-wrap: wrap; gap: 0.4rem; }
  .chip { font: inherit; cursor: pointer; background: var(--paper-2); border: 1px solid var(--line); border-radius: 999px; padding: 0.25rem 0.7rem; color: var(--ink); display: inline-flex; align-items: center; gap: 0.4rem; }
  .chip:hover { border-color: var(--accent); }
  .chip.sel { border-color: var(--accent); background: var(--accent-soft); }
  .chip .pn { font-size: 0.78rem; color: var(--ink-2); }
  .chip.small { padding: 0.18rem 0.6rem; font-size: 0.85rem; }

  .detail { background: var(--paper-2); border: 1px solid var(--line); border-radius: var(--radius); padding: 1rem 1.15rem; }
  .d-head { display: flex; align-items: center; gap: 0.9rem; }
  .d-sym { font-size: 2rem; font-weight: 700; color: var(--accent); min-width: 2.2rem; text-align: center; }
  .d-sym.poly-sym { font-size: 1.4rem; }
  .d-name { font-weight: 600; text-transform: capitalize; }
  .d-meta { font-size: 0.82rem; color: var(--ink-faint); font-family: var(--font-mono); }
  .d-ion { margin: 0.7rem 0 0; }
  .d-why { margin: 0.4rem 0 0; font-size: 0.88rem; }
  .badge.tiny { font-size: 0.66rem; padding: 0.04rem 0.4rem; }

  .props { margin-top: 0.9rem; border-top: 1px solid var(--line); padding-top: 0.7rem; }
  .props-label { margin: 0 0 0.5rem; font-size: 0.85rem; color: var(--ink-faint); display: flex; align-items: center; gap: 0.5rem; }
  .prop-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(9rem, 1fr)); gap: 0.5rem; }
  .prop { display: flex; flex-direction: column; gap: 0.1rem; background: var(--paper); border: 1px solid var(--line); border-radius: 8px; padding: 0.45rem 0.6rem; }
  .prop .pk { font-size: 0.72rem; color: var(--ink-faint); }
  .prop .pv { font-weight: 700; font-family: var(--font-mono); color: var(--ink); }
  .prop .ps { font-size: 0.6rem; color: var(--ink-faint); font-family: var(--font-mono); }
  .prop-note { margin: 0.5rem 0 0; font-size: 0.8rem; }

  .salts { margin-top: 0.9rem; border-top: 1px solid var(--line); padding-top: 0.7rem; display: grid; gap: 0.4rem; }
  .salts-label { margin: 0; font-size: 0.85rem; color: var(--ink-faint); display: flex; align-items: center; gap: 0.5rem; }
  .salt-scroll { display: grid; gap: 0.35rem; max-height: 14rem; overflow-y: auto; padding-right: 0.3rem; }
  .salt { display: flex; align-items: center; gap: 0.4rem; flex-wrap: wrap; }
  .salt .ion { font-family: var(--font-mono); }
  .salt .arrow { color: var(--ink-faint); }
  .salt .sname { font-size: 0.85rem; }
  .salt .cross { font-family: var(--font-mono); font-size: 0.74rem; margin-left: 0.3rem; }
  .hint { font-size: 0.82rem; margin: 0.2rem 0 0; }

  /* trends */
  .chart-box { background: var(--paper-2); border: 1px solid var(--line); border-radius: var(--radius); padding: 0.85rem 1.05rem; display: grid; gap: 0.5rem; }
  .chart-title { margin: 0; font-weight: 600; display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap; }
  svg { width: 100%; height: auto; }
  .axis { stroke: var(--line); stroke-width: 1; }
  .trendline { fill: none; stroke: var(--accent); stroke-width: 2; }
  .dot-pt { fill: var(--accent); }
  .val { font-size: 11px; fill: var(--ink-2); font-family: var(--font-mono); }
  .sym-lbl { font-size: 13px; font-weight: 700; fill: var(--ink); }
  .sym-lbl.gone { fill: var(--ink-faint); font-weight: 400; }
  .gone-mark { font-size: 12px; fill: var(--ink-faint); }
  .chart-note { margin: 0; font-size: 0.86rem; }
  .chart-note .faint { display: block; margin-top: 0.2rem; }

  /* formula builder + bonding */
  .fm-lede { margin: 0; font-size: 0.92rem; max-width: 46rem; }
  .pickers { display: grid; grid-template-columns: 1fr 1fr; gap: 0.9rem; }
  @media (max-width: 720px) { .pickers { grid-template-columns: 1fr; } }
  .picker { background: var(--paper-2); border: 1px solid var(--line); border-radius: var(--radius); padding: 0.7rem 0.85rem; }
  .picker-label { margin: 0 0 0.45rem; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.03em; font-weight: 700; color: var(--ink-faint); }
  .picker-chips { display: flex; flex-wrap: wrap; gap: 0.3rem; max-height: 11rem; overflow-y: auto; }

  .built { background: var(--paper-2); border: 1px solid var(--line); border-radius: var(--radius); padding: 0.9rem 1.1rem; display: grid; gap: 0.45rem; }
  .built-main { display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap; font-size: 1.15rem; }
  .built-main .ion { font-family: var(--font-mono); }
  .built-main .arrow { color: var(--ink-faint); }
  .built-formula { font-size: 1.3rem; }
  .built-name { margin: 0; display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap; }
  .built-cross { margin: 0; font-family: var(--font-mono); font-size: 0.82rem; color: var(--ink-faint); }
  .mistake { border-left: 3px solid var(--warn); background: var(--warn-soft); border-radius: 6px; padding: 0.5rem 0.75rem; }
  .mk-head { margin: 0; color: var(--warn); }
  .mk-note { margin: 0.2rem 0 0; font-size: 0.88rem; color: var(--ink-2); }

  .bond-en { margin: 0; font-family: var(--font-mono); font-size: 0.92rem; display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap; }
  .bond-den { margin: 0; font-size: 1.05rem; display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap; }
  .bond-class { color: var(--accent); }
  .spectrum { display: grid; gap: 0.25rem; margin-top: 0.2rem; }
  .spec-bar { position: relative; height: 0.7rem; border-radius: 999px; border: 1px solid var(--line);
    background: linear-gradient(90deg, color-mix(in srgb, var(--ion-co3) 45%, var(--paper-2)), color-mix(in srgb, var(--ion-na) 45%, var(--paper-2)), color-mix(in srgb, var(--ion-ca) 55%, var(--paper-2))); }
  .spec-marker { position: absolute; top: -0.3rem; width: 3px; height: 1.3rem; background: var(--ink); border-radius: 2px; transform: translateX(-50%); }
  .spec-tick { position: absolute; top: 100%; width: 1px; height: 0.35rem; background: var(--ink-faint); }
  .spec-tick i { position: absolute; top: 0.3rem; left: -0.6rem; font-style: normal; font-size: 0.64rem; color: var(--ink-faint); font-family: var(--font-mono); }
  .spec-labels { display: flex; justify-content: space-between; font-size: 0.72rem; color: var(--ink-faint); margin-top: 0.85rem; }
  .caution { margin: 0.4rem 0 0; font-size: 0.88rem; color: var(--ink-2); }
  .caution .badge { margin-right: 0.4rem; }
</style>
