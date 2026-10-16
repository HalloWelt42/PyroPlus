<script lang="ts">
  import { oled } from '$lib/stores/oled.svelte';
  import { ui } from '$lib/stores/ui.svelte';
  import type { Widget, WidgetOpts } from '$lib/api/types';
  import Segment from '$lib/bausteine/Segment.svelte';
  import OptionFelder from './OptionFelder.svelte';
  import PixelWerkzeuge from './PixelWerkzeuge.svelte';

  let { onquelleWechseln, onhinzufuegen, onbausteine }: {
    onquelleWechseln: (widget: Widget) => void; onhinzufuegen: () => void; onbausteine: () => void;
  } = $props();

  const gewaehlt = $derived(oled.gewaehlte);
  const einzel = $derived(gewaehlt.length === 1 ? gewaehlt[0] : null);
  const quelle = $derived(einzel ? oled.quelle(einzel.source) : null);
  const modus = $derived(einzel ? oled.darstellung(einzel.display) : null);
  const modi = $derived(oled.darstellungenFuer(quelle));
  const ids = $derived(gewaehlt.map((w) => w.id));
  const gemeinsamerModus = $derived(gewaehlt.length > 1 && gewaehlt.every((w) => w.display === gewaehlt[0].display) ? oled.darstellung(gewaehlt[0].display) : null);

  let sichernOffen = $state(false);
  let sichernName = $state('');

  const SYMBOLE: Record<string, string> = { cpu: 'fa-microchip', ram: 'fa-memory', disk: 'fa-hard-drive', net: 'fa-network-wired', fan: 'fa-fan', zeit: 'fa-clock', wetter: 'fa-cloud-sun', text: 'fa-font', layout: 'fa-shapes' };

  function aendern(patch: Partial<WidgetOpts>): void { oled.optsAendern(ids, patch); }
  function variante(opts: WidgetOpts): void { if (modus) oled.varianteAnwenden(ids, opts, modus.fields); }
  function aktiveVariante(): string {
    if (!einzel || !modus) return '';
    const o = einzel.opts;
    const treffer = modus.variants.find((v) => modus.fields.every((f) => {
      const wert = (v.opts as unknown as Record<string, unknown>)[f];
      return wert === null || wert === undefined || wert === (o as unknown as Record<string, unknown>)[f];
    }));
    return treffer?.id ?? '';
  }
  function sichern(): void {
    if (!einzel || !sichernName.trim()) return;
    void oled.alsBausteinSichern(einzel, sichernName.trim());
    sichernOffen = false;
  }
</script>

{#if !oled.entwurf}
  <div class="leer"><p>Kein Bildschirm gewählt.</p></div>
{:else if oled.entwurf.kind !== 'widgets'}
  <div class="gruppe">
    <div class="quelle-kopf"><div class="symbol"><i class="fa-solid fa-cloud-sun"></i></div><div><div class="titel">Fertiger Wetterbildschirm</div><div class="unter">Festes Layout mit Symbolen, kein Widget-Editor</div></div></div>
    <div class="zeile"><span class="label">Ort</span>
      <select class="feld" value={oled.entwurf.locationId ?? ''} title="Ort für diesen Bildschirm; leer = Vorgabeort" onchange={(e) => oled.aendere((s) => { s.locationId = (e.currentTarget as HTMLSelectElement).value || null; })}>
        <option value="">Vorgabeort</option>
        {#each oled.orte as o (o.location.id)}<option value={o.location.id}>{o.location.name}</option>{/each}
      </select>
    </div>
  </div>
{:else if oled.entwurf.widgets.length === 0}
  <div class="leer">
    <div class="symbol"><i class="fa-solid fa-wand-magic-sparkles"></i></div>
    <h3>Der Bildschirm ist noch leer</h3>
    <p>Drei Wege führen zum ersten Inhalt. Alles, was du einfügst, lässt sich danach verschieben und ändern.</p>
    <div class="schritte">
      <div class="schritt"><span class="nr">1</span><span class="text"><b>Vorlage einfügen:</b> fertiger Bildschirm, zum Beispiel Uhr oder Wetter. Schnellster Weg.</span></div>
      <div class="schritt"><span class="nr">2</span><span class="text"><b>Baustein wählen:</b> ein fertiges Widget wie "Uhr groß" oder "CPU-Balken".</span></div>
      <div class="schritt"><span class="nr">3</span><span class="text"><b>Selbst zusammenstellen:</b> Datenquelle und Darstellung wählen, Vorschau prüfen, einfügen.</span></div>
    </div>
    <div class="btn-reihe" style="width:100%">
      <button class="btn btn-primary" onclick={() => (ui.fenster = 'vorlagen')}><i class="fa-solid fa-layer-group"></i>Vorlagen</button>
      <button class="btn" onclick={onbausteine}><i class="fa-solid fa-puzzle-piece"></i>Bausteine</button>
      <button class="btn" onclick={onhinzufuegen}><i class="fa-solid fa-database"></i>Quellen</button>
    </div>
  </div>
{:else if gewaehlt.length === 0}
  <div class="leer">
    <div class="symbol"><i class="fa-solid fa-arrow-pointer"></i></div>
    <h3>Nichts gewählt</h3>
    <p>Klicke ein Widget auf der Vorschau, um es zu bearbeiten. Mit <span class="kbd">Umschalt</span> wählst du mehrere.</p>
    <button class="btn btn-accent" onclick={onhinzufuegen}><i class="fa-solid fa-plus"></i>Widget hinzufügen</button>
  </div>
{:else if einzel}
  <div class="gruppe">
    <div class="quelle-kopf">
      <div class="symbol"><i class="fa-solid {SYMBOLE[quelle?.tab ?? 'layout'] ?? 'fa-shapes'}"></i></div>
      <div>
        <div class="titel">{quelle?.label ?? einzel.source}</div>
        <div class="unter">{quelle ? `${quelle.group ? quelle.group + ' · ' : ''}${quelle.example ? 'jetzt ' + quelle.example + (quelle.unit ? ' ' + quelle.unit : '') : quelle.description}` : 'Unbekannte Quelle'}</div>
      </div>
    </div>
    <div class="zeile"><span class="label">Name</span><input class="feld" value={einzel.name} title="Eigener Name, erscheint in der Auswahl und im Kontextmenü" oninput={(e) => oled.widgetAendern(einzel.id, { name: (e.currentTarget as HTMLInputElement).value })}></div>
    {#if einzel.display !== 'bitmap'}
      <div class="zeile"><span class="label">Quelle</span><button class="btn btn-klein" title="Andere Datenquelle wählen; Darstellung und Optionen bleiben erhalten" onclick={() => onquelleWechseln(einzel)}><i class="fa-solid fa-right-left"></i>Wechseln</button></div>
    {/if}
  </div>

  {#if einzel.display === 'bitmap'}
    <PixelWerkzeuge widget={einzel} />
  {:else}
    <div class="gruppe">
      <div class="gruppe-titel"><i class="fa-solid fa-shapes"></i>Darstellung<button class="hilfe" title="Hilfe zu Darstellungsarten" onclick={() => ui.oeffneHilfe('darstellungsarten')}>i</button></div>
      <div class="chips">
        {#each modi as m (m.id)}
          <button class="chip" class:active={einzel.display === m.id} title={m.description} onclick={() => oled.darstellungSetzen(ids, m)}>{m.label}</button>
        {/each}
      </div>
      {#if modus && modus.variants.length}
        <div class="zeile"><span class="label">Vorgabe</span>
          <div class="chips">
            {#each modus.variants as v (v.id)}
              <button class="chip" class:active={aktiveVariante() === v.id} onclick={() => variante(v.opts)}>{v.label}</button>
            {/each}
          </div>
        </div>
      {/if}
    </div>
    {#if modus}
      <OptionFelder felder={modus.fields} opts={einzel.opts} {quelle} onaendern={aendern} />
    {/if}
  {/if}

  <div class="gruppe">
    <div class="gruppe-titel"><i class="fa-solid fa-arrows-up-down-left-right"></i>Position</div>
    <div class="zeile"><span class="label">X / Y</span>
      <div class="feld-zeile">
        <input class="feld feld-klein" type="number" min="0" max="127" value={einzel.x} title="Abstand vom linken Rand in Pixeln, 0 bis 127" onchange={(e) => oled.widgetAendern(einzel.id, { x: Math.max(0, Math.min(127, Number((e.currentTarget as HTMLInputElement).value))) })}>
        <input class="feld feld-klein" type="number" min="0" max="63" value={einzel.y} title="Abstand vom oberen Rand in Pixeln, 0 bis 63" onchange={(e) => oled.widgetAendern(einzel.id, { y: Math.max(0, Math.min(63, Number((e.currentTarget as HTMLInputElement).value))) })}>
        <button class="btn btn-klein" title="Waagerecht in der Mitte des Displays ausrichten" onclick={() => oled.zentrieren(ids)}><i class="fa-solid fa-align-center"></i>Mitte</button>
      </div>
    </div>
    {#if modus?.fields.includes('rotate')}
      <div class="zeile"><span class="label">Drehung</span>
        <Segment klein wert={String(einzel.opts.rotate)} titel="Widget um seine linke obere Ecke drehen" onwahl={(v) => aendern({ rotate: Number(v) as WidgetOpts['rotate'] })}
          optionen={[{ wert: '0', label: '0°' }, { wert: '90', label: '90°' }, { wert: '180', label: '180°' }, { wert: '270', label: '270°' }]} />
      </div>
    {/if}
  </div>

  {#if sichernOffen}
    <div class="gruppe">
      <div class="gruppe-titel"><i class="fa-solid fa-puzzle-piece"></i>Als Baustein sichern</div>
      <div class="feld-zeile">
        <!-- svelte-ignore a11y_autofocus -->
        <input class="feld" placeholder="Name des Bausteins" bind:value={sichernName} autofocus onkeydown={(e) => { if (e.key === 'Enter') sichern(); if (e.key === 'Escape') sichernOffen = false; }}>
        <button class="btn btn-klein btn-primary" onclick={sichern}>Sichern</button>
      </div>
    </div>
  {/if}
  <div class="btn-reihe">
    <button class="btn btn-klein" title="Kopie 4 Pixel versetzt einfügen" onclick={() => oled.duplizierenWidgets(ids)}><i class="fa-solid fa-copy"></i>Kopie</button>
    <button class="btn btn-klein" title="Als Baustein für andere Bildschirme sichern" onclick={() => { sichernOffen = true; sichernName = einzel?.name ?? ''; }}><i class="fa-solid fa-puzzle-piece"></i>Sichern</button>
    <button class="btn btn-klein btn-gefahr" title="Widget vom Bildschirm entfernen" onclick={() => oled.entfernen(ids)}><i class="fa-solid fa-trash-can"></i>Löschen</button>
  </div>
{:else}
  <div class="gruppe">
    <div class="quelle-kopf"><div class="symbol"><i class="fa-solid fa-object-group"></i></div><div><div class="titel">{gewaehlt.length} Widgets gewählt</div><div class="unter">{gewaehlt.map((w) => w.name || oled.quelle(w.source)?.label || w.source).join(', ')}</div></div></div>
  </div>
  <div class="gruppe">
    <div class="gruppe-titel"><i class="fa-solid fa-arrows-up-down-left-right"></i>Anordnen</div>
    <div class="btn-reihe">
      <button class="btn btn-klein" title="Oberkanten angleichen" onclick={() => oled.buendig(ids, 'oben')}><i class="fa-solid fa-arrow-up-short-wide"></i>Oben bündig</button>
      <button class="btn btn-klein" title="Linke Kanten angleichen" onclick={() => oled.buendig(ids, 'links')}><i class="fa-solid fa-align-left"></i>Links bündig</button>
    </div>
    <div class="btn-reihe">
      <button class="btn btn-klein" title="Jedes Widget waagerecht zentrieren" onclick={() => oled.zentrieren(ids)}><i class="fa-solid fa-align-center"></i>Zentrieren</button>
      <button class="btn btn-klein" title="Gleichmäßig über die Breite verteilen" disabled={ids.length < 3} onclick={() => oled.verteilen(ids)}><i class="fa-solid fa-arrows-left-right"></i>Verteilen</button>
    </div>
  </div>
  {#if gemeinsamerModus}
    <div class="gruppe">
      <div class="gruppe-titel"><i class="fa-solid fa-shapes"></i>Für alle: {gemeinsamerModus.label}</div>
      {#if gemeinsamerModus.variants.length}
        <div class="chips">
          {#each gemeinsamerModus.variants as v (v.id)}
            <button class="chip" onclick={() => { if (gemeinsamerModus) oled.varianteAnwenden(ids, v.opts, gemeinsamerModus.fields); }}>{v.label}</button>
          {/each}
        </div>
      {/if}
    </div>
    <OptionFelder felder={gemeinsamerModus.fields} opts={gewaehlt[0].opts} quelle={oled.quelle(gewaehlt[0].source)} onaendern={aendern} />
  {/if}
  <div class="btn-reihe">
    <button class="btn btn-klein" title="Alle kopieren" onclick={() => oled.duplizierenWidgets(ids)}><i class="fa-solid fa-copy"></i>Kopie</button>
    <button class="btn btn-klein btn-gefahr" title="Alle entfernen" onclick={() => oled.entfernen(ids)}><i class="fa-solid fa-trash-can"></i>Löschen</button>
  </div>
{/if}

<style>
  .btn:disabled { opacity: 0.45; cursor: default; }
</style>
