<script lang="ts">
  /* Optionen eines Widgets, gesteuert durch die Felderliste der Darstellungsart aus dem Katalog. */
  import type { SourceInfo, WidgetOpts } from '$lib/api/types';
  import { oled } from '$lib/stores/oled.svelte';
  import Segment from '$lib/bausteine/Segment.svelte';
  import Regler from '$lib/bausteine/Regler.svelte';
  import Schalter from '$lib/bausteine/Schalter.svelte';
  import Stufen from '$lib/bausteine/Stufen.svelte';

  let { felder, opts, quelle, onaendern }: {
    felder: string[]; opts: WidgetOpts; quelle: SourceInfo | null; onaendern: (patch: Partial<WidgetOpts>) => void;
  } = $props();

  const hat = (f: string) => felder.includes(f);
  const istText = $derived(hat('prefix') || hat('text'));
  const skalierung = $derived(hat('scaleX'));
  const masse = $derived(hat('width') || hat('height') || hat('radius') || hat('size'));
</script>

{#if skalierung}
  <div class="gruppe">
    <div class="gruppe-titel"><i class="fa-solid fa-text-height"></i>Schriftgröße</div>
    <div class="zeile"><span class="label">Breite</span><Stufen wert={opts.scaleX} min={1} max={8} einheit="x" titel="Horizontale Vergrößerung der Pixelschrift, 1 bis 8" onwahl={(v) => onaendern({ scaleX: v })} /></div>
    <div class="zeile"><span class="label">Höhe</span><Stufen wert={opts.scaleY ?? opts.scaleX} min={1} max={8} einheit="x" titel="Vertikale Vergrößerung, 1 bis 8" onwahl={(v) => onaendern({ scaleY: v })} /></div>
  </div>
{/if}

{#if istText}
  <div class="gruppe">
    <div class="gruppe-titel"><i class="fa-solid fa-font"></i>Beschriftung</div>
    {#if hat('text')}
      <div class="zeile"><span class="label">Text</span><textarea class="feld text" rows="2" value={opts.text ?? ''} title="Eigener Text; Zeilenumbruch beginnt eine neue Zeile" oninput={(e) => onaendern({ text: (e.currentTarget as HTMLTextAreaElement).value })}></textarea></div>
    {/if}
    {#if hat('prefix')}
      <div class="zeile"><span class="label">Davor</span><input class="feld" value={opts.prefix} placeholder="z. B. CPU " title="Text vor dem Wert" oninput={(e) => onaendern({ prefix: (e.currentTarget as HTMLInputElement).value })}></div>
    {/if}
    {#if hat('suffix')}
      <div class="zeile"><span class="label">Danach</span><input class="feld" value={opts.suffix} placeholder="z. B. °C" title="Text nach dem Wert, zum Beispiel die Einheit" oninput={(e) => onaendern({ suffix: (e.currentTarget as HTMLInputElement).value })}></div>
    {/if}
    {#if hat('decimals') && quelle && (quelle.valueType === 'number' || quelle.valueType === 'percent')}
      <div class="zeile"><span class="label">Dezimal</span>
        <Segment klein wert={opts.decimals === null ? 'auto' : String(opts.decimals)} titel="Nachkommastellen; Auto nimmt die Vorgabe der Quelle"
          onwahl={(v) => onaendern({ decimals: v === 'auto' ? null : Number(v) })}
          optionen={[{ wert: 'auto', label: 'Auto' }, { wert: '0', label: '0' }, { wert: '1', label: '1' }, { wert: '2', label: '2' }]} />
      </div>
      {#if hat('thousands')}
        <div class="zeile"><span class="label">Tausender</span><Schalter an={opts.thousands} klein titel="Tausendertrenner, zum Beispiel 1.234" onwahl={(an) => onaendern({ thousands: an })} /></div>
      {/if}
    {/if}
    {#if hat('align')}
      <div class="zeile"><span class="label">Ausrichtung</span>
        <Segment klein wert={opts.align} titel="Ausrichtung innerhalb der Box; ohne Box bleibt der Text links"
          onwahl={(v) => onaendern({ align: v as WidgetOpts['align'], boxW: v === 'left' ? 0 : opts.boxW || 128 })}
          optionen={[{ wert: 'left', label: '', symbol: 'fa-align-left', titel: 'Links' }, { wert: 'center', label: '', symbol: 'fa-align-center', titel: 'Mitte' }, { wert: 'right', label: '', symbol: 'fa-align-right', titel: 'Rechts' }]} />
      </div>
      {#if opts.align !== 'left'}
        <div class="zeile"><span class="label">Boxbreite</span><Regler wert={opts.boxW} min={8} max={128} einheit=" px" titel="Breite des Bereichs, in dem ausgerichtet wird; 128 ist das ganze Display" onwahl={(v) => onaendern({ boxW: v })} /></div>
      {/if}
    {/if}
  </div>
{/if}

{#if masse}
  <div class="gruppe">
    <div class="gruppe-titel"><i class="fa-solid fa-ruler-combined"></i>Maße</div>
    {#if hat('width')}
      <div class="zeile"><span class="label">Breite</span><Regler wert={opts.width ?? 60} min={1} max={128} einheit=" px" titel="Breite in Pixeln, 1 bis 128" onwahl={(v) => onaendern({ width: v })} /></div>
    {/if}
    {#if hat('height')}
      <div class="zeile"><span class="label">Höhe</span><Regler wert={opts.height ?? 6} min={1} max={64} einheit=" px" titel="Höhe in Pixeln, 1 bis 64" onwahl={(v) => onaendern({ height: v })} /></div>
    {/if}
    {#if hat('radius')}
      <div class="zeile"><span class="label">Radius</span><Regler wert={opts.radius ?? 12} min={4} max={32} einheit=" px" titel="Radius des Halbkreises, 4 bis 32 Pixel" onwahl={(v) => onaendern({ radius: v })} /></div>
    {/if}
    {#if hat('size')}
      <div class="zeile"><span class="label">Größe</span>
        <Segment klein wert={String(opts.size ?? 16)} titel="Größe des Symbols in Pixeln" onwahl={(v) => onaendern({ size: Number(v) })}
          optionen={[{ wert: '8', label: '8' }, { wert: '16', label: '16' }, { wert: '32', label: '32' }]} />
      </div>
    {/if}
  </div>
{/if}

{#if quelle?.usesLocation}
  <div class="gruppe">
    <div class="gruppe-titel"><i class="fa-solid fa-location-dot"></i>Wetterort</div>
    {#if oled.orte.length === 0}
      <p class="hinweistext">Noch kein Ort angelegt. Über "Wetterorte" oben einen Ort hinzufügen.</p>
    {:else}
      <div class="zeile"><span class="label">Ort</span>
        <select class="feld" value={opts.locationId ?? ''} title="Ort, dessen Wetter dieses Widget zeigt; leer = Vorgabeort" onchange={(e) => onaendern({ locationId: (e.currentTarget as HTMLSelectElement).value || null })}>
          <option value="">Vorgabeort</option>
          {#each oled.orte as o (o.location.id)}<option value={o.location.id}>{o.location.name}</option>{/each}
        </select>
      </div>
    {/if}
  </div>
{/if}

<style>
  .feld.text { height: auto; padding: 8px 12px; resize: vertical; font-family: var(--font); }
  .hinweistext { font-size: var(--fs-sm); color: var(--text-muted); }
</style>
