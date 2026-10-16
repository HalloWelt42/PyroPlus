<script lang="ts">
  /* Bausteine: eigene gesicherte Widgets und mitgelieferte Vorlagen. Jede Kachel zeigt das
     Bild vom Vorschau-Endpunkt, ein Klick fügt den Baustein an einer freien Stelle ein. */
  import { onMount } from 'svelte';
  import { oled, type Vorschaubild } from '$lib/stores/oled.svelte';
  import type { Widget, WidgetPreset } from '$lib/api/types';
  import WidgetVorschau from './WidgetVorschau.svelte';

  let kategorie = $state('Alle');
  let bilder = $state<Record<string, Vorschaubild | null>>({});
  let umbenennen = $state<WidgetPreset | null>(null);
  let umbenennenText = $state('');
  let loeschenId = $state<string | null>(null);
  const angefragt = new Set<string>();

  onMount(() => { void oled.ladeVorlagen(); });

  const kategorien = $derived(['Alle', ...(oled.vorlagen?.categories.filter((k) => oled.vorlagen?.widgets.some((w) => w.category === k)) ?? [])]);
  const mitgeliefert = $derived((oled.vorlagen?.widgets ?? []).filter((w) => kategorie === 'Alle' || w.category === kategorie));

  async function bildFuer(schluessel: string, widget: Widget): Promise<void> {
    if (angefragt.has(schluessel)) return;
    angefragt.add(schluessel);
    /* Erst abwarten, dann einfügen: der Spread darf nicht vor dem await den alten Stand festhalten */
    const bild = await oled.renderEinzeln(widget);
    bilder = { ...bilder, [schluessel]: bild };
  }

  $effect(() => {
    for (const t of mitgeliefert) void bildFuer(`v:${t.id}`, t.widget);
    for (const p of oled.bausteine) void bildFuer(`p:${p.id}`, { id: p.id, source: p.source, display: p.display, x: 0, y: 0, name: p.name, opts: p.opts });
  });

  function umbenennenEnde(): void {
    if (umbenennen && umbenennenText.trim()) void oled.bausteinUmbenennen(umbenennen, umbenennenText.trim());
    umbenennen = null;
  }
</script>

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
          <WidgetVorschau bild={bilder[`p:${p.id}`] ?? null} hoehe={56} maxSkala={3} leer="Leer" />
          {#if umbenennen?.id === p.id}
            <!-- svelte-ignore a11y_autofocus -->
            <input class="feld klein" bind:value={umbenennenText} autofocus onclick={(e) => e.stopPropagation()} onblur={umbenennenEnde} onkeydown={(e) => { e.stopPropagation(); if (e.key === 'Enter') umbenennenEnde(); if (e.key === 'Escape') umbenennen = null; }}>
          {:else}
            <span class="name">{p.name}</span>
          {/if}
          <div class="aktionen">
            <button class="mini" title="Umbenennen" onclick={(e) => { e.stopPropagation(); umbenennen = p; umbenennenText = p.name; }}><i class="fa-solid fa-pen"></i></button>
            <button class="mini" class:warnung={loeschenId === p.id} title={loeschenId === p.id ? 'Noch einmal klicken: löschen' : 'Baustein löschen'} onclick={(e) => { e.stopPropagation(); if (loeschenId === p.id) { void oled.bausteinLoeschen(p.id); loeschenId = null; } else { loeschenId = p.id; setTimeout(() => { if (loeschenId === p.id) loeschenId = null; }, 3000); } }}><i class="fa-solid fa-trash-can"></i></button>
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
        <WidgetVorschau bild={bilder[`v:${t.id}`] ?? null} hoehe={56} maxSkala={3} leer="Leer" />
        <span class="name">{t.name}</span>
      </button>
    {/each}
  </div>
</div>

<style>
  .hinweistext { font-size: var(--fs-sm); color: var(--text-muted); }
  .baustein { position: relative; cursor: pointer; }
  .baustein .aktionen { position: absolute; top: 6px; right: 6px; display: none; gap: 4px; }
  .baustein:hover .aktionen { display: flex; }
  .mini { width: 26px; height: 26px; border-radius: 6px; background: rgba(0,0,0,0.6); color: var(--text-secondary); display: inline-flex; align-items: center; justify-content: center; font-size: 12px; }
  .mini:hover { color: var(--text-primary); }
  .mini.warnung { background: var(--red-glow); color: var(--red); }
  .feld.klein { height: 32px; padding: 0 8px; font-size: var(--fs-xs); }
</style>
