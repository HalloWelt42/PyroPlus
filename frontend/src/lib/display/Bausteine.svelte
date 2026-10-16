<script lang="ts">
  import { onMount } from 'svelte';
  import { oled } from '$lib/stores/oled.svelte';
  import type { Widget, WidgetPreset, WidgetTemplate } from '$lib/api/types';

  let kategorie = $state('Alle');
  let bilder = $state<Record<string, { bild: string; w: number; h: number }>>({});
  let umbenennen = $state<WidgetPreset | null>(null);
  let umbenennenText = $state('');
  let loeschenId = $state<string | null>(null);

  onMount(() => { void oled.ladeVorlagen(); });

  const kategorien = $derived(['Alle', ...(oled.vorlagen?.categories.filter((k) => oled.vorlagen?.widgets.some((w) => w.category === k)) ?? [])]);
  const mitgeliefert = $derived((oled.vorlagen?.widgets ?? []).filter((w) => kategorie === 'Alle' || w.category === kategorie));

  async function bildFuer(schluessel: string, widget: Widget): Promise<void> {
    if (bilder[schluessel]) return;
    const erg = await oled.renderEinzeln(widget);
    if (erg && erg.box.w > 0) bilder = { ...bilder, [schluessel]: { bild: erg.bild, w: erg.box.w, h: erg.box.h } };
  }

  $effect(() => {
    for (const t of oled.vorlagen?.widgets ?? []) void bildFuer(`v:${t.id}`, t.widget);
    for (const p of oled.bausteine) void bildFuer(`p:${p.id}:${p.name}`, { id: p.id, source: p.source, display: p.display, x: 0, y: 0, name: p.name, opts: p.opts });
  });

  function vorschau(schluessel: string): { bild: string; w: number; h: number } | null { return bilder[schluessel] ?? null; }
  function skala(b: { w: number; h: number }): number { return Math.max(1, Math.min(3, Math.floor(Math.min(150 / b.w, 46 / b.h)))); }
  function umbenennenEnde(): void {
    if (umbenennen && umbenennenText.trim()) void oled.bausteinUmbenennen(umbenennen, umbenennenText.trim());
    umbenennen = null;
  }
</script>

{#snippet bild(schluessel: string)}
  {@const b = vorschau(schluessel)}
  <div class="bild">
    {#if b}<div class="ausschnitt" style="width:{b.w * skala(b)}px;height:{b.h * skala(b)}px"><img src="data:image/png;base64,{b.bild}" alt="" style="width:{128 * skala(b)}px;height:{64 * skala(b)}px"></div>{/if}
  </div>
{/snippet}

<div class="chips" title="Bereich der Bausteine">
  {#each kategorien as k (k)}<button class="chip" class:active={kategorie === k} onclick={() => (kategorie = k)}>{k}</button>{/each}
</div>

<div class="gruppe">
  <div class="gruppe-titel"><i class="fa-solid fa-user"></i>Eigene Bausteine<span class="badge badge-neutral" style="margin-left:auto">{oled.bausteine.length}</span></div>
  {#if oled.bausteine.length === 0}
    <p class="hinweistext">Noch keine. Ein gewähltes Widget lässt sich über "Sichern" als Baustein ablegen.</p>
  {:else}
    <div class="bausteine">
      {#each oled.bausteine as p (p.id)}
        <div class="baustein" role="button" tabindex="0" title="Klick fügt den Baustein ein" onclick={() => oled.eigenenBausteinEinfuegen(p)} onkeydown={(e) => { if (e.key === 'Enter') void oled.eigenenBausteinEinfuegen(p); }}>
          {@render bild(`p:${p.id}:${p.name}`)}
          {#if umbenennen?.id === p.id}
            <!-- svelte-ignore a11y_autofocus -->
            <input class="feld klein" bind:value={umbenennenText} autofocus onclick={(e) => e.stopPropagation()} onblur={umbenennenEnde} onkeydown={(e) => { e.stopPropagation(); if (e.key === 'Enter') umbenennenEnde(); if (e.key === 'Escape') umbenennen = null; }}>
          {:else}
            <span class="name">{p.name}</span>
          {/if}
          <div class="aktionen">
            <button class="mini" title="Umbenennen" onclick={(e) => { e.stopPropagation(); umbenennen = p; umbenennenText = p.name; }}><i class="fa-solid fa-pen"></i></button>
            <button class="mini" class:warnung={loeschenId === p.id} title={loeschenId === p.id ? 'Noch einmal klicken: löschen' : 'Baustein löschen'} onclick={(e) => { e.stopPropagation(); if (loeschenId === p.id) { void oled.bausteinLoeschen(p.id); loeschenId = null; } else { loeschenId = p.id; setTimeout(() => (loeschenId = null), 3000); } }}><i class="fa-solid fa-trash-can"></i></button>
          </div>
        </div>
      {/each}
    </div>
  {/if}
</div>

<div class="gruppe">
  <div class="gruppe-titel"><i class="fa-solid fa-box"></i>Mitgeliefert<span class="badge badge-neutral" style="margin-left:auto">{mitgeliefert.length}</span></div>
  <div class="bausteine">
    {#each mitgeliefert as t (t.id)}
      <button class="baustein" title={t.description} onclick={() => oled.bausteinEinfuegen(t.id)}>
        {@render bild(`v:${t.id}`)}
        <span class="name">{t.name}</span>
      </button>
    {/each}
  </div>
</div>

<style>
  .ausschnitt { overflow: hidden; position: relative; }
  .ausschnitt img { position: absolute; left: 0; top: 0; image-rendering: pixelated; }
  .hinweistext { font-size: var(--fs-sm); color: var(--text-muted); }
  .baustein { position: relative; cursor: pointer; }
  .baustein .aktionen { position: absolute; top: 6px; right: 6px; display: none; gap: 4px; }
  .baustein:hover .aktionen { display: flex; }
  .mini { width: 26px; height: 26px; border-radius: 6px; background: rgba(0,0,0,0.6); color: var(--text-secondary); display: inline-flex; align-items: center; justify-content: center; font-size: 12px; }
  .mini:hover { color: var(--text-primary); }
  .mini.warnung { background: var(--red-glow); color: var(--red); }
  .feld.klein { height: 32px; padding: 0 8px; font-size: var(--fs-xs); }
</style>
