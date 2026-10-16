<script lang="ts">
  import type { Widget } from '$lib/api/types';
  import { oled } from '$lib/stores/oled.svelte';
  import { ui } from '$lib/stores/ui.svelte';
  import Segment from '$lib/bausteine/Segment.svelte';
  import Schalter from '$lib/bausteine/Schalter.svelte';
  import { zeichnung, WERKZEUGE } from './zeichnung.svelte';
  import { entpacken, packen, leeren, umkehren, spiegeln, groesseAendern, zuschneiden } from './bitmap';

  let { widget }: { widget: Widget } = $props();
  const breite = $derived(widget.opts.width ?? 32);
  const hoehe = $derived(widget.opts.height ?? 16);

  function rows() { return entpacken(widget.opts.bitmap, breite, hoehe); }
  function setze(neu: number[][], extra: Partial<Widget['opts']> = {}): void {
    oled.optsAendern([widget.id], { bitmap: packen(neu), ...extra });
  }
  function groesse(b: number, h: number): void {
    const nb = Math.max(1, Math.min(128, b)), nh = Math.max(1, Math.min(64, h));
    setze(groesseAendern(rows(), nb, nh), { width: nb, height: nh });
  }
  function schneiden(): void {
    const erg = zuschneiden(rows());
    if (!erg) { ui.toast('Das Bild ist leer', 'info'); return; }
    oled.aendere((s) => {
      const w = s.widgets.find((x) => x.id === widget.id);
      if (!w) return;
      w.x += erg.dx; w.y += erg.dy;
      w.opts.width = erg.rows[0].length; w.opts.height = erg.rows.length;
      w.opts.bitmap = packen(erg.rows);
    });
  }
</script>

<div class="gruppe">
  <div class="gruppe-titel"><i class="fa-solid fa-pen"></i>Werkzeuge<button class="hilfe" title="Hilfe zum Zeichnen" onclick={() => ui.oeffneHilfe('pixelbilder')}>i</button></div>
  {#if !oled.zeichnen}
    <button class="btn btn-accent btn-breit" title="Zeichenmodus starten: dann wird im Rahmen des Bildes gezeichnet" onclick={() => (oled.zeichnen = true)}><i class="fa-solid fa-paintbrush"></i>Zeichnen</button>
  {:else}
    <div class="werkzeuge">
      {#each WERKZEUGE as w (w.id)}
        <button class="werkzeug" class:active={zeichnung.werkzeug === w.id} title="{w.titel} (Taste {w.taste})" onclick={() => (zeichnung.werkzeug = w.id)}><i class="fa-solid {w.symbol}"></i></button>
      {/each}
    </div>
    {#if zeichnung.werkzeug === 'stift' || zeichnung.werkzeug === 'radierer' || zeichnung.werkzeug === 'linie'}
      <div class="zeile"><span class="label">Stiftbreite</span>
        <Segment klein wert={String(zeichnung.breite)} onwahl={(v) => (zeichnung.breite = Number(v))}
          optionen={[{ wert: '1', label: '1' }, { wert: '2', label: '2' }, { wert: '3', label: '3' }, { wert: '4', label: '4' }]} />
      </div>
    {/if}
    {#if zeichnung.werkzeug === 'rechteck' || zeichnung.werkzeug === 'ellipse'}
      <div class="zeile"><span class="label">Gefüllt</span><Schalter an={zeichnung.gefuellt} klein titel="Form ausgefüllt statt nur Umriss" onwahl={(an) => (zeichnung.gefuellt = an)} /></div>
    {/if}
    {#if zeichnung.werkzeug === 'text'}
      <div class="zeile"><span class="label">Text</span><input class="feld" bind:value={zeichnung.text} title="Wird in Pixelschrift an der Klickstelle eingesetzt"></div>
    {/if}
    <div class="btn-reihe">
      <button class="btn btn-klein" title="Alle Pixel löschen" onclick={() => setze(leeren(rows()))}><i class="fa-solid fa-broom"></i>Leeren</button>
      <button class="btn btn-klein" title="Hell und dunkel tauschen" onclick={() => setze(umkehren(rows()))}><i class="fa-solid fa-circle-half-stroke"></i>Umkehren</button>
      <button class="btn btn-klein" title="Waagerecht spiegeln" onclick={() => setze(spiegeln(rows()))}><i class="fa-solid fa-left-right"></i>Spiegeln</button>
    </div>
  {/if}
</div>

<div class="gruppe">
  <div class="gruppe-titel"><i class="fa-solid fa-ruler-combined"></i>Bildgröße</div>
  <div class="zeile"><span class="label">Breite / Höhe</span>
    <div class="feld-zeile">
      <input class="feld feld-klein" type="number" min="1" max="128" value={breite} title="Breite des Bildes in Pixeln, 1 bis 128" onchange={(e) => groesse(Number((e.currentTarget as HTMLInputElement).value), hoehe)}>
      <input class="feld feld-klein" type="number" min="1" max="64" value={hoehe} title="Höhe des Bildes in Pixeln, 1 bis 64" onchange={(e) => groesse(breite, Number((e.currentTarget as HTMLInputElement).value))}>
      <button class="btn btn-klein btn-symbol" title="Auf den gezeichneten Inhalt zuschneiden" onclick={schneiden}><i class="fa-solid fa-crop-simple"></i></button>
    </div>
  </div>
  <div class="zeile"><span class="label">Invertiert</span><Schalter an={widget.opts.invert} klein titel="Bild als dunkle Form auf hellem Grund zeigen" onwahl={(an) => oled.optsAendern([widget.id], { invert: an })} /></div>
</div>
