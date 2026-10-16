<script lang="ts">
  import { onDestroy, onMount } from 'svelte';
  import { oled } from '$lib/stores/oled.svelte';
  import { live } from '$lib/stores/live.svelte';
  import { ui } from '$lib/stores/ui.svelte';
  import DisplayKopf from './DisplayKopf.svelte';
  import BildschirmListe from './BildschirmListe.svelte';
  import Canvas from './Canvas.svelte';
  import RechteSpalte from './RechteSpalte.svelte';
  import VorlagenFenster from './VorlagenFenster.svelte';
  import WetterorteFenster from './WetterorteFenster.svelte';
  import ProfileFenster from './ProfileFenster.svelte';
  import HilfeFenster from '$lib/hilfe/HilfeFenster.svelte';
  import { zeichnung, WERKZEUGE } from './zeichnung.svelte';

  let rechteSpalte = $state<RechteSpalte | null>(null);

  onMount(() => {
    void oled.laden();
    oled.aktivieren();
  });
  onDestroy(() => {
    oled.deaktivieren();
    oled.setzeProbe(null);
  });

  /* Bildschirmliste nachladen, wenn das Backend eine neue Version meldet */
  $effect(() => {
    const version = live.oled?.screensVersion;
    if (version !== undefined && oled.geladen) void oled.abgleich(version);
  });

  function tastatur(e: KeyboardEvent): void {
    const ziel = e.target as HTMLElement | null;
    if (ziel && (ziel.tagName === 'INPUT' || ziel.tagName === 'TEXTAREA' || ziel.isContentEditable)) return;
    if (ui.fenster) return;
    const strg = e.ctrlKey || e.metaKey;
    const ids = oled.auswahl;
    if (strg && e.key.toLowerCase() === 'z') { e.preventDefault(); if (e.shiftKey) oled.wiederholen(); else oled.rueckgaengig(); return; }
    if (strg && e.key.toLowerCase() === 'y') { e.preventDefault(); oled.wiederholen(); return; }
    if (strg && e.key.toLowerCase() === 'a') { e.preventDefault(); oled.alleWaehlen(); return; }
    if (strg && e.key.toLowerCase() === 'd' && ids.length) { e.preventDefault(); oled.duplizierenWidgets(ids); return; }
    if ((e.key === 'Delete' || e.key === 'Backspace') && ids.length && !oled.zeichnen) { e.preventDefault(); oled.entfernen(ids); return; }
    if (e.key === 'Escape') { oled.waehleWidget(null); oled.setzeProbe(null); return; }
    if (ids.length && ['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(e.key)) {
      e.preventDefault();
      const schritt = e.shiftKey ? 8 : 1;
      const dx = e.key === 'ArrowLeft' ? -schritt : e.key === 'ArrowRight' ? schritt : 0;
      const dy = e.key === 'ArrowUp' ? -schritt : e.key === 'ArrowDown' ? schritt : 0;
      oled.verschieben(ids, dx, dy);
      return;
    }
    if (oled.zeichnen) {
      const w = WERKZEUGE.find((x) => x.taste === e.key.toUpperCase());
      if (w && !strg) zeichnung.werkzeug = w.id;
    }
  }
</script>

<svelte:window onkeydown={tastatur} />

<div class="main">
  <DisplayKopf />
  <div class="editor">
    <BildschirmListe />
    <Canvas onkontext={(id) => rechteSpalte?.zeigeEigenschaften()} />
    <RechteSpalte bind:this={rechteSpalte} />
  </div>
</div>

{#if ui.fenster === 'vorlagen'}<VorlagenFenster onschliessen={() => (ui.fenster = null)} />{/if}
{#if ui.fenster === 'wetterorte'}<WetterorteFenster onschliessen={() => (ui.fenster = null)} />{/if}
{#if ui.fenster === 'profile'}<ProfileFenster onschliessen={() => (ui.fenster = null)} />{/if}
{#if ui.fenster === 'hilfe'}<HilfeFenster onschliessen={() => (ui.fenster = null)} />{/if}
