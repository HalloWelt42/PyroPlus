<script lang="ts">
  /* Zeigt das Bild eines einzelnen Widgets, wie es der Vorschau-Endpunkt liefert: ganzzahlig
     vergrößert, nie verzerrt, auf schwarzem Grund wie das Display. Ein Ort für alle Vorschauen. */
  import type { Vorschaubild } from '$lib/stores/oled.svelte';

  let { bild, hoehe = 56, breite = null, maxSkala = 4, leer = 'Keine Vorschau', mass = false }: {
    bild: Vorschaubild | null; hoehe?: number; breite?: number | null; maxSkala?: number; leer?: string; mass?: boolean;
  } = $props();

  let innenBreite = $state(0);
  const rand = 8;
  const skala = $derived.by(() => {
    if (!bild) return 1;
    const platzBreite = (breite ?? innenBreite) - rand;
    const platzHoehe = hoehe - rand;
    if (platzBreite <= 0) return 1;
    return Math.max(1, Math.min(maxSkala, Math.floor(Math.min(platzBreite / bild.w, platzHoehe / bild.h))));
  });
</script>

<div class="vorschau" style="height:{hoehe}px;{breite ? `width:${breite}px;` : ''}" bind:clientWidth={innenBreite}>
  {#if bild}
    <img src="data:image/png;base64,{bild.bild}" alt="" style="width:{bild.w * skala}px;height:{bild.h * skala}px">
  {:else}
    <span class="leer">{leer}</span>
  {/if}
</div>
{#if mass && bild}<span class="mass">{bild.w} x {bild.h} Pixel</span>{/if}

<style>
  .vorschau { display: flex; align-items: center; justify-content: center; background: #000; border-radius: 4px; border: 1px solid #2b3245; overflow: hidden; box-sizing: border-box; }
  .vorschau img { image-rendering: pixelated; max-width: 100%; max-height: 100%; object-fit: contain; display: block; }
  .leer { font-size: var(--fs-xs); color: var(--text-muted); }
  .mass { display: block; text-align: center; font: 500 var(--fs-xs) var(--mono); color: var(--text-muted); margin-top: 6px; }
</style>
