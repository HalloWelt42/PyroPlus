<script lang="ts">
  /* Symbol aus der Bibliothek wählen: Gruppen als Chips, Kacheln mit Bild vom Backend. */
  import { oled } from '$lib/stores/oled.svelte';

  let { wert, onwahl, vorgabeErlaubt = false }: {
    wert: string | null; onwahl: (id: string | null) => void; vorgabeErlaubt?: boolean;
  } = $props();

  const VORSCHAU_GROESSE = 16;
  const symbole = $derived(oled.katalog?.symbols ?? []);
  const kategorien = $derived(oled.katalog?.symbolCategories ?? []);
  let kategorie = $state<string | null>(null);
  const aktiv = $derived(kategorie ?? symbole.find((s) => s.id === wert)?.category ?? kategorien[0] ?? '');
  const sichtbar = $derived(symbole.filter((s) => s.category === aktiv));
  const gewaehlt = $derived(symbole.find((s) => s.id === wert) ?? null);

  $effect(() => {
    for (const s of sichtbar) void oled.symbolVorschau(s.id, VORSCHAU_GROESSE);
  });
</script>

<div class="symbolwahl">
  <div class="chips">
    {#each kategorien as k (k)}<button class="chip" class:active={aktiv === k} onclick={() => (kategorie = k)}>{k}</button>{/each}
  </div>
  <div class="raster">
    {#each sichtbar as s (s.id)}
      {@const bild = oled.symbolbilder[`${s.id}@${VORSCHAU_GROESSE}`]}
      <button class="kachel" class:active={wert === s.id} title={s.label} onclick={() => onwahl(s.id)}>
        {#if bild}<img src="data:image/png;base64,{bild.bild}" alt={s.label} style="width:{bild.w * 2}px;height:{bild.h * 2}px">{/if}
      </button>
    {/each}
  </div>
  <div class="fuss">
    <span class="aktuell">{gewaehlt ? gewaehlt.label : vorgabeErlaubt ? 'Passend zur Quelle' : 'Kein Symbol gewählt'}</span>
    {#if vorgabeErlaubt && wert}
      <button class="btn btn-klein" title="Symbol wieder automatisch zur Datenquelle wählen" onclick={() => onwahl(null)}>Automatisch</button>
    {/if}
  </div>
</div>

<style>
  .symbolwahl { display: flex; flex-direction: column; gap: 8px; }
  .raster { display: grid; grid-template-columns: repeat(auto-fill, minmax(44px, 1fr)); gap: 6px; }
  .kachel { height: 44px; border-radius: var(--radius-sm); background: #000; border: 1px solid var(--border); display: flex; align-items: center; justify-content: center; cursor: pointer; }
  .kachel:hover { border-color: var(--border-strong); }
  .kachel.active { border-color: var(--border-accent); box-shadow: 0 0 0 1px var(--border-accent); }
  .kachel img { image-rendering: pixelated; display: block; }
  .fuss { display: flex; align-items: center; justify-content: space-between; gap: 8px; min-height: 32px; }
  .aktuell { font-size: var(--fs-sm); color: var(--text-secondary); }
</style>
