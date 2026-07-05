<script>
  // The Valence Table (brief §16): the periodic table as a charge machine. Click an element to see its common
  // ion and why; click a polyatomic ion to see how neutral formulas fall out of charge balance. Ca and Na are
  // highlighted (the lesson's ions). Every charge is sourced (data/ions.toml, ADR-0017); the salts were
  // assembled by charge crossover and verified neutral by the producer (ADR reference). No chemistry here —
  // it renders the committed table.
  let { table } = $props();
  const t = table;

  const bySym = Object.fromEntries(t.elements.map((e) => [e.symbol, e]));
  let sel = $state({ type: "element", key: t.highlight[0] ?? t.elements[0].symbol });

  const chargeLabel = (n) => { const s = n > 0 ? "+" : "−"; const m = Math.abs(n); return m === 1 ? s : `${m}${s}`; };
  const selElement = $derived(sel.type === "element" ? bySym[sel.key] : null);
  const selPoly = $derived(sel.type === "poly" ? t.polyatomic.find((p) => p.id === sel.key) : null);
  const selIonId = $derived(selElement?.common_ion?.id ?? selPoly?.id ?? null);
  // salts where the selected ion appears (as cation or anion)
  const salts = $derived(selIonId ? t.charge_balance.filter((c) => c.cation === selIonId || c.anion === selIonId) : []);
  const isHi = (sym) => t.highlight.includes(sym);
</script>

<div class="vt">
  <div class="grid" role="grid" aria-label="Periodic table (the elements in this dataset)">
    {#each t.elements as e}
      <button
        class="cell {isHi(e.symbol) ? 'hi' : ''} {sel.type === 'element' && sel.key === e.symbol ? 'sel' : ''} b-{e.block}"
        style={`grid-column:${e.group}; grid-row:${e.period};`}
        onclick={() => (sel = { type: "element", key: e.symbol })}
        aria-label={`${e.name}, ${e.common_ion ? "common ion " + chargeLabel(e.common_ion.charge) : "no simple ion"}`}>
        <span class="z">{e.Z}</span>
        {#if e.common_ion}<span class="ch">{chargeLabel(e.common_ion.charge)}</span>{/if}
        <span class="sym">{e.symbol}</span>
        <span class="aw">{e.atomic_weight}</span>
      </button>
    {/each}
    <div class="legend" style="grid-column:3 / 13; grid-row:1 / 3;">
      <p class="blurb">{t.blurb}</p>
      <div class="blocks"><span class="sw b-s"></span>s-block<span class="sw b-p"></span>p-block</div>
    </div>
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
          <div class="d-meta">Z = {selElement.Z} · {selElement.atomic_weight} g/mol · group {selElement.group}, period {selElement.period}</div>
        </div>
      </div>
      {#if selElement.common_ion}
        <p class="d-ion">Common ion: <strong>{@html selElement.common_ion.latexHtml}</strong> ({selElement.common_ion.name}) —
          charge <strong>{chargeLabel(selElement.common_ion.charge)}</strong>.
          <span class="badge sourced tiny"><span class="dot"></span>rule-sourced ({t.sources.ion_charge})</span></p>
        <p class="d-why muted">{t.group_charge_note}</p>
      {:else}
        <p class="d-ion muted">No simple monatomic ion in this dataset — {selElement.symbol} appears in polyatomic ions and covalent compounds instead.</p>
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
        {#each salts as c}
          <div class="salt">
            <span class="ion">{c.cationPretty}</span> + <span class="ion">{c.anionPretty}</span>
            <span class="arrow">→</span> <strong>{@html c.latexHtml}</strong>
            <span class="cross muted">{c.note}</span>
          </div>
        {/each}
        <p class="hint faint">The subscripts aren't guessed — they're whatever makes the total charge zero (charge crossover), then re-checked atom-by-atom.</p>
      </div>
    {/if}
  </div>
</div>

<style>
  .vt { display: grid; gap: 0.9rem; }
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

  .poly-label { margin: 0.2rem 0 0; font-size: 0.85rem; color: var(--ink-faint); }
  .poly { display: flex; flex-wrap: wrap; gap: 0.4rem; }
  .chip { font: inherit; cursor: pointer; background: var(--paper-2); border: 1px solid var(--line); border-radius: 999px; padding: 0.25rem 0.7rem; color: var(--ink); display: inline-flex; align-items: center; gap: 0.4rem; }
  .chip:hover { border-color: var(--accent); }
  .chip.sel { border-color: var(--accent); background: var(--accent-soft); }
  .chip .pn { font-size: 0.78rem; color: var(--ink-2); }

  .detail { background: var(--paper-2); border: 1px solid var(--line); border-radius: var(--radius); padding: 1rem 1.15rem; }
  .d-head { display: flex; align-items: center; gap: 0.9rem; }
  .d-sym { font-size: 2rem; font-weight: 700; color: var(--accent); min-width: 2.2rem; text-align: center; }
  .d-sym.poly-sym { font-size: 1.4rem; }
  .d-name { font-weight: 600; text-transform: capitalize; }
  .d-meta { font-size: 0.82rem; color: var(--ink-faint); font-family: var(--font-mono); }
  .d-ion { margin: 0.7rem 0 0; }
  .d-why { margin: 0.4rem 0 0; font-size: 0.88rem; }
  .badge.tiny { font-size: 0.66rem; padding: 0.04rem 0.4rem; }

  .salts { margin-top: 0.9rem; border-top: 1px solid var(--line); padding-top: 0.7rem; display: grid; gap: 0.4rem; }
  .salts-label { margin: 0; font-size: 0.85rem; color: var(--ink-faint); display: flex; align-items: center; gap: 0.5rem; }
  .salt { display: flex; align-items: center; gap: 0.4rem; flex-wrap: wrap; }
  .salt .ion { font-family: var(--font-mono); }
  .salt .arrow { color: var(--ink-faint); }
  .salt .cross { font-family: var(--font-mono); font-size: 0.78rem; margin-left: 0.3rem; }
  .hint { font-size: 0.82rem; margin: 0.2rem 0 0; }
</style>
