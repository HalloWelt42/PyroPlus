<script lang="ts">
  import { oled } from '$lib/stores/oled.svelte';
  import { ui } from '$lib/stores/ui.svelte';
  import Segment from '$lib/bausteine/Segment.svelte';
  import Kontextmenue from './Kontextmenue.svelte';
  import { treffer, einrasten, W, H, begrenze } from './geometrie';
  import { zeichnung } from './zeichnung.svelte';
  import { entpacken, packen, setzePixel, linie, rechteck, ellipse, fuellen, verschieben, kopie, pixelAusPng, type Bitmap } from './bitmap';
  import type { Widget } from '$lib/api/types';

  /* onauswahl: der Nutzer hat auf dem Display ein Widget gewählt (Klick oder Rechtsklick) */
  let { onauswahl }: { onauswahl?: () => void } = $props();

  let schirm = $state<HTMLDivElement | null>(null);
  let feld = $state<HTMLDivElement | null>(null);
  let menue = $state<{ x: number; y: number } | null>(null);
  let cursor = $state<{ x: number; y: number } | null>(null);

  /* Vergrößerung: die gewählte Stufe, aber nie größer als der Platz in der Spalte erlaubt */
  const ZOOM_STUFEN = [2, 3, 4, 6];
  const RAND = 2 * 20 + 2 * 14 + 4;   // Innenabstand der Fläche, Rahmen des Geräts, Luft
  let feldBreite = $state(0);
  let feldHoehe = $state(0);
  const passend = $derived(feldBreite > 0 ? Math.max(1, Math.floor(Math.min((feldBreite - RAND) / W, (feldHoehe - RAND) / H))) : ui.zoom);
  const zoom = $derived(Math.min(ui.zoom, passend));
  const gewaehlt = $derived(oled.gewaehlte);
  const einzel = $derived(gewaehlt.length === 1 ? gewaehlt[0] : null);
  const bitmapWidget = $derived(oled.zeichnen && einzel && einzel.display === 'bitmap' ? einzel : null);
  const zustandText = $derived(
    oled.speicherzustand === 'gespeichert' ? 'Gespeichert'
      : oled.speicherzustand === 'fehler' ? 'Speichern fehlgeschlagen' : 'Wird gespeichert',
  );

  /* Ziehen von Widgets */
  let ziehen: { start: { x: number; y: number }; ursprung: Map<string, { x: number; y: number }>; bewegt: boolean } | null = null;

  /* Zeichnen im Pixelbild */
  let strich: { start: { x: number; y: number }; basis: Bitmap; wert: 0 | 1 } | null = null;

  function pixelPos(e: PointerEvent): { x: number; y: number } {
    const r = schirm!.getBoundingClientRect();
    return { x: begrenze(Math.floor((e.clientX - r.left) / zoom), 0, W - 1), y: begrenze(Math.floor((e.clientY - r.top) / zoom), 0, H - 1) };
  }

  function bitmapVon(w: Widget): Bitmap {
    return entpacken(w.opts.bitmap, w.opts.width ?? 32, w.opts.height ?? 16);
  }

  function bitmapSetzen(w: Widget, rows: Bitmap, merken: boolean): void {
    oled.optsAendern([w.id], { bitmap: packen(rows) }, merken);
  }

  function runter(e: PointerEvent): void {
    if (!schirm) return;
    menue = null;
    const p = pixelPos(e);
    schirm.setPointerCapture(e.pointerId);

    if (bitmapWidget) {
      if (e.button === 2 && zeichnung.werkzeug !== 'stift') return;
      zeichnenStart(bitmapWidget, p, e.button === 2 ? 0 : 1);
      return;
    }

    if (e.button !== 0) return;
    const box = treffer(oled.boxen, p.x, p.y);
    if (!box) {
      if (!e.shiftKey) oled.waehleWidget(null);
      return;
    }
    oled.waehleWidget(box.id, e.shiftKey);
    onauswahl?.();
    if (e.shiftKey) return;
    const ursprung = new Map<string, { x: number; y: number }>();
    for (const w of oled.gewaehlte) ursprung.set(w.id, { x: w.x, y: w.y });
    ziehen = { start: p, ursprung, bewegt: false };
  }

  function bewegen(e: PointerEvent): void {
    if (!schirm) return;
    const p = pixelPos(e);
    cursor = p;
    if (strich && bitmapWidget) { zeichnenBewegen(bitmapWidget, p); return; }
    if (!ziehen) return;
    let dx = p.x - ziehen.start.x;
    let dy = p.y - ziehen.start.y;
    if (dx === 0 && dy === 0) return;
    ziehen.bewegt = true;
    const pos = new Map<string, { x: number; y: number }>();
    for (const [id, u] of ziehen.ursprung) {
      let x = u.x + dx, y = u.y + dy;
      if (ui.einrasten) { x = einrasten(x, 8); y = einrasten(y, 8); }
      pos.set(id, { x, y });
    }
    oled.positionSetzen([...pos.keys()], pos, false);
  }

  function hoch(e: PointerEvent): void {
    if (strich && bitmapWidget) { zeichnenEnde(bitmapWidget, pixelPos(e)); return; }
    if (ziehen) {
      if (ziehen.bewegt) oled.merken();
      ziehen = null;
    }
  }

  /* Doppelklick auf ein Pixelbild startet das Zeichnen */
  function doppelt(e: MouseEvent): void {
    if (!schirm || bitmapWidget) return;
    const r = schirm.getBoundingClientRect();
    const box = treffer(oled.boxen, Math.floor((e.clientX - r.left) / zoom), Math.floor((e.clientY - r.top) / zoom));
    if (box) oled.zeichnenStarten(box.id);
  }

  function kontext(e: MouseEvent): void {
    e.preventDefault();
    if (!schirm || !feld || bitmapWidget) return;
    const r = schirm.getBoundingClientRect();
    const p = { x: Math.floor((e.clientX - r.left) / zoom), y: Math.floor((e.clientY - r.top) / zoom) };
    const box = treffer(oled.boxen, p.x, p.y);
    if (!box) { menue = null; return; }
    if (!oled.auswahl.includes(box.id)) oled.waehleWidget(box.id);
    const f = feld.getBoundingClientRect();
    menue = { x: e.clientX - f.left, y: e.clientY - f.top };
    onauswahl?.();
  }

  /* Zeichenlogik: Koordinaten relativ zum Widget */
  function lokal(w: Widget, p: { x: number; y: number }): { x: number; y: number } {
    return { x: p.x - w.x, y: p.y - w.y };
  }

  function zeichnenStart(w: Widget, p: { x: number; y: number }, wert: 0 | 1): void {
    const l = lokal(w, p);
    const basis = bitmapVon(w);
    const werkzeug = zeichnung.werkzeug;
    const setzWert: 0 | 1 = werkzeug === 'radierer' ? 0 : wert;
    if (werkzeug === 'fuellen') {
      const rows = kopie(basis);
      fuellen(rows, l.x, l.y, setzWert);
      bitmapSetzen(w, rows, true);
      return;
    }
    if (werkzeug === 'text') {
      void textEinsetzen(w, l);
      return;
    }
    strich = { start: l, basis, wert: setzWert };
    if (werkzeug === 'stift' || werkzeug === 'radierer') {
      const rows = kopie(basis);
      setzePixel(rows, l.x, l.y, setzWert, zeichnung.breite);
      strich.basis = rows;
      bitmapSetzen(w, rows, false);
      strich.start = l;
    }
  }

  function zeichnenBewegen(w: Widget, p: { x: number; y: number }): void {
    if (!strich) return;
    const l = lokal(w, p);
    const werkzeug = zeichnung.werkzeug;
    if (werkzeug === 'stift' || werkzeug === 'radierer') {
      const rows = strich.basis;
      linie(rows, strich.start.x, strich.start.y, l.x, l.y, strich.wert, zeichnung.breite);
      strich.start = l;
      bitmapSetzen(w, rows, false);
      return;
    }
    const rows = kopie(strich.basis);
    if (werkzeug === 'linie') linie(rows, strich.start.x, strich.start.y, l.x, l.y, strich.wert, zeichnung.breite);
    else if (werkzeug === 'rechteck') rechteck(rows, strich.start.x, strich.start.y, l.x, l.y, strich.wert, zeichnung.gefuellt);
    else if (werkzeug === 'ellipse') ellipse(rows, strich.start.x, strich.start.y, l.x, l.y, strich.wert, zeichnung.gefuellt);
    else if (werkzeug === 'verschieben') {
      const neu = verschieben(strich.basis, l.x - strich.start.x, l.y - strich.start.y);
      bitmapSetzen(w, neu, false);
      return;
    }
    bitmapSetzen(w, rows, false);
  }

  function zeichnenEnde(w: Widget, p: { x: number; y: number }): void {
    if (!strich) return;
    zeichnenBewegen(w, p);
    strich = null;
    oled.merken();
  }

  async function textEinsetzen(w: Widget, l: { x: number; y: number }): Promise<void> {
    const text = zeichnung.text.trim();
    if (!text) return;
    const probe: Widget = { id: 'text', source: 'text.frei', display: 'text', x: 0, y: 0, name: '', opts: { ...w.opts, bitmap: null, invert: false, text, scaleX: 1, scaleY: 1, align: 'left', boxW: 0, rotate: 0, width: null, height: null } };
    const ergebnis = await oled.renderEinzeln(probe);
    if (!ergebnis) return;
    const pixel = await pixelAusPng(ergebnis.bild, Math.min(W, ergebnis.w), Math.min(H, ergebnis.h));
    const rows = bitmapVon(w);
    for (let y = 0; y < pixel.length; y++) {
      for (let x = 0; x < pixel[0].length; x++) if (pixel[y][x]) setzePixel(rows, l.x + x, l.y + y, 1);
    }
    bitmapSetzen(w, rows, true);
  }
</script>

<section class="spalte spalte-canvas">
  <div class="canvas-leiste">
    <Segment klein wert={String(zoom)} titel="Vergrößerung der Vorschau; das Display hat 128 mal 64 Pixel" onwahl={(z) => ui.setzeZoom(Number(z))}
      optionen={ZOOM_STUFEN.map((z) => ({ wert: String(z), label: `${z}x`, gesperrt: z > passend && z > 2, titel: z > passend ? 'Passt hier nicht; das Fenster ist zu schmal' : '' }))} />
    <button class="btn btn-klein" class:active={ui.raster} title="Hilfslinien alle 8 Pixel einblenden" onclick={() => ui.setzeRaster(!ui.raster)}><i class="fa-solid fa-border-all"></i>Raster</button>
    <button class="btn btn-klein" class:active={ui.einrasten} title="Beim Verschieben auf das 8-Pixel-Raster einrasten" onclick={() => ui.setzeEinrasten(!ui.einrasten)}><i class="fa-solid fa-magnet"></i>Einrasten</button>
    <button class="btn btn-klein btn-symbol" title="Letzte Änderung zurücknehmen (Strg+Z)" disabled={!oled.kannRueckgaengig} onclick={() => oled.rueckgaengig()}><i class="fa-solid fa-rotate-left"></i></button>
    <button class="btn btn-klein btn-symbol" title="Zurückgenommene Änderung wiederholen (Strg+Y)" disabled={!oled.kannWiederholen} onclick={() => oled.wiederholen()}><i class="fa-solid fa-rotate-right"></i></button>
    {#if bitmapWidget}
      <span class="badge badge-warn"><i class="fa-solid fa-paintbrush"></i>Zeichenmodus: {bitmapWidget.name || 'Pixelbild'} ({bitmapWidget.opts.width} x {bitmapWidget.opts.height})</span>
    {/if}
    <div class="rechts">
      {#if oled.probe}
        <button class="btn btn-klein" title="Vorschau des neuen Widgets entfernen, ohne es einzufügen (Esc)" onclick={() => oled.vorschauVerwerfen()}><i class="fa-solid fa-xmark"></i>Vorschau verwerfen</button>
      {:else}
        <span class="badge" class:badge-ok={oled.speicherzustand === 'gespeichert'} class:badge-warn={oled.speicherzustand === 'wartet' || oled.speicherzustand === 'laeuft'} class:badge-err={oled.speicherzustand === 'fehler'}>
          <i class="fa-solid {oled.speicherzustand === 'gespeichert' ? 'fa-circle-check' : oled.speicherzustand === 'fehler' ? 'fa-triangle-exclamation' : 'fa-pen'}"></i>{zustandText}
        </span>
      {/if}
      {#if bitmapWidget}
        <button class="btn btn-klein" title="Zeichnen beenden; das Widget bleibt gewählt" onclick={() => (oled.zeichnen = false)}><i class="fa-solid fa-check"></i>Fertig</button>
      {:else if oled.entwurf && oled.aktiverBildschirmId !== oled.entwurf.id}
        <button class="btn btn-klein btn-accent" title="Diesen Bildschirm jetzt auf dem Display zeigen; die Rotation läuft von hier weiter" onclick={() => { if (oled.entwurf) void oled.anzeigen(oled.entwurf.id); }}><i class="fa-solid fa-eye"></i>Auf dem Display zeigen</button>
      {/if}
    </div>
  </div>

  <div class="canvas-feld" bind:this={feld} bind:clientWidth={feldBreite} bind:clientHeight={feldHoehe}>
    {#if oled.entwurf}
      <div class="geraet" style="--zoom:{zoom}">
        <div class="geraet-schirm" class:raster={ui.raster} class:zeichnet={!!bitmapWidget} bind:this={schirm}
          role="presentation"
          onpointerdown={runter} onpointermove={bewegen} onpointerup={hoch} onpointercancel={hoch}
          onpointerleave={() => (cursor = null)} oncontextmenu={kontext} ondblclick={doppelt}>
          {#if oled.bild}<img src="data:image/png;base64,{oled.bild}" alt="Vorschau vom Backend" draggable="false">{/if}
          {#if bitmapWidget}
            <div class="pixelrahmen" style="left:{bitmapWidget.x * zoom}px;top:{bitmapWidget.y * zoom}px;width:{(bitmapWidget.opts.width ?? 32) * zoom}px;height:{(bitmapWidget.opts.height ?? 16) * zoom}px">
              <span class="etikett">{bitmapWidget.name || 'Pixelbild'}: nur hier wird gezeichnet</span>
            </div>
          {:else}
            {#each oled.boxen.filter((b) => oled.auswahl.includes(b.id) && b.w > 0) as b (b.id)}
              {@const w = oled.entwurf.widgets.find((x) => x.id === b.id)}
              <div class="auswahl" class:neben={oled.auswahl[0] !== b.id} class:unten={b.y * zoom < 28} style="left:{b.x * zoom - 2}px;top:{b.y * zoom - 2}px;width:{b.w * zoom + 4}px;height:{b.h * zoom + 4}px">
                <span class="etikett">{w?.name || oled.quelle(w?.source ?? '')?.label || ''}</span>
              </div>
            {/each}
            {#if oled.probe && oled.probeBox && oled.probeBox.w > 0}
              <div class="auswahl neben" class:unten={oled.probeBox.y * zoom < 28} style="left:{oled.probeBox.x * zoom - 2}px;top:{oled.probeBox.y * zoom - 2}px;width:{oled.probeBox.w * zoom + 4}px;height:{oled.probeBox.h * zoom + 4}px">
                <span class="etikett">Neu: {oled.probe.name}</span>
              </div>
            {/if}
          {/if}
        </div>
      </div>
      {#if menue && einzel !== null || menue && gewaehlt.length > 1}
        <Kontextmenue x={menue.x} y={menue.y} onschliessen={() => (menue = null)} />
      {/if}
    {:else}
      <div class="leer"><div class="symbol"><i class="fa-solid fa-display"></i></div><h3>Kein Bildschirm gewählt</h3><p>Links einen Bildschirm wählen oder einen neuen anlegen.</p></div>
    {/if}
  </div>

  <div class="canvas-fuss">
    {#if bitmapWidget}
      <span>Pixel <span class="mono">{cursor ? `${cursor.x - bitmapWidget.x}, ${cursor.y - bitmapWidget.y}` : '-'}</span></span>
      <span>Bild <span class="mono">{bitmapWidget.opts.width} x {bitmapWidget.opts.height}</span></span>
      <span class="hinweis">Links setzt, rechts löscht · Ziehen zeichnet durch</span>
    {:else if einzel}
      {@const box = oled.boxen.find((b) => b.id === einzel.id)}
      <span>Position <span class="mono">{einzel.x}, {einzel.y}</span></span>
      <span>Größe <span class="mono">{box ? `${box.w} x ${box.h}` : '-'}</span></span>
      <span>Widgets <span class="mono">{oled.entwurf?.widgets.length ?? 0}</span></span>
      <span class="hinweis">Ziehen verschiebt · <span class="kbd">Pfeile</span> 1 px · <span class="kbd">Umschalt</span> 8 px · Rechtsklick: Menü</span>
    {:else if gewaehlt.length > 1}
      <span>Gewählt <span class="mono">{gewaehlt.length} Widgets</span></span>
      <span class="hinweis"><span class="kbd">Umschalt</span> + Klick wählt mehrere · Ziehen verschiebt die Gruppe</span>
    {:else}
      <span>Cursor <span class="mono">{cursor ? `${cursor.x}, ${cursor.y}` : '-'}</span></span>
      <span>Widgets <span class="mono">{oled.entwurf?.widgets.length ?? 0}</span></span>
      <span class="hinweis">Klick wählt ein Widget · Rechts hinzufügen oder einen Baustein wählen</span>
    {/if}
  </div>
</section>

<style>
  .canvas-feld { position: relative; }
  .geraet-schirm { cursor: default; touch-action: none; user-select: none; }
  .geraet-schirm.zeichnet { cursor: crosshair; }
  .geraet-schirm img { pointer-events: none; }
  .btn:disabled { opacity: 0.45; cursor: default; }
  .badge-err { background: var(--red-glow); color: var(--red); }
  .auswahl.unten .etikett { top: auto; bottom: -26px; }
</style>
