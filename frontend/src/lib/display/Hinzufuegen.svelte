<script lang="ts">
  /* Datenquelle und Darstellung wählen; das neue Widget wird im Bild mitgerendert, bis es eingefügt wird.
     Mit wechselFuer wird statt dessen die Quelle eines bestehenden Widgets getauscht. */
  import { onDestroy } from 'svelte';
  import { oled, leereOpts } from '$lib/stores/oled.svelte';
  import { ui } from '$lib/stores/ui.svelte';
  import type { DisplayModeInfo, SourceInfo, Tab, Widget, WidgetOpts } from '$lib/api/types';
  import OptionFelder from './OptionFelder.svelte';
  import Regler from '$lib/bausteine/Regler.svelte';

  let { wechselFuer = null, onfertig }: { wechselFuer?: Widget | null; onfertig: () => void } = $props();

  let tab = $state<Tab>('cpu');
  let quelleId = $state<string | null>(null);
  let modusId = $state<string | null>(null);
  let opts = $state<WidgetOpts>(leereOpts());
  let name = $state('');
  let probewert = $state<number | null>(null);
  let klein = $state<{ bild: string; w: number; h: number } | null>(null);
  let kleinTimer: ReturnType<typeof setTimeout> | null = null;

  const quellen = $derived((oled.katalog?.sources ?? []).filter((s) => s.tab === tab));
  const quelle = $derived(quelleId ? oled.quelle(quelleId) : null);
  const modi = $derived(oled.darstellungenFuer(quelle));
  const modus = $derived(modusId ? oled.darstellung(modusId as DisplayModeInfo['id']) : null);
  const gruppen = $derived.by(() => {
    const liste: Array<{ gruppe: string; quellen: SourceInfo[] }> = [];
    for (const q of quellen) {
      let g = liste.find((x) => x.gruppe === q.group);
      if (!g) { g = { gruppe: q.group, quellen: [] }; liste.push(g); }
      g.quellen.push(q);
    }
    return liste;
  });

  $effect(() => {
    if (wechselFuer) {
      const q = oled.quelle(wechselFuer.source);
      if (q) tab = q.tab;
    }
  });

  function waehleQuelle(q: SourceInfo): void {
    if (wechselFuer) {
      const neueModi = oled.darstellungenFuer(q);
      const passt = neueModi.some((m) => m.id === wechselFuer!.display);
      oled.aendere((s) => {
        const w = s.widgets.find((x) => x.id === wechselFuer!.id);
        if (!w) return;
        w.source = q.id;
        if (!passt && neueModi[0]) { w.display = neueModi[0].id; w.opts = { ...leereOpts(), ...neueModi[0].defaults, locationId: w.opts.locationId }; }
        if (!w.name || w.name === oled.quelle(wechselFuer!.source)?.label) w.name = q.label;
      });
      ui.toast(`Quelle: ${q.label}`);
      onfertig();
      return;
    }
    quelleId = q.id;
    name = q.label;
    const neueModi = oled.darstellungenFuer(q);
    const erster = neueModi.find((m) => m.id === modusId) ?? neueModi[0];
    setzeModus(erster ?? null, q);
  }

  function setzeModus(m: DisplayModeInfo | null, q: SourceInfo | null = quelle): void {
    modusId = m?.id ?? null;
    if (m) {
      opts = { ...leereOpts(), ...m.defaults };
      /* Die Einheit der Quelle schlägt die allgemeine Vorgabe der Darstellung: 50 °C statt 50 % */
      if (q && q.unit && m.fields.includes('suffix')) opts.suffix = ` ${q.unit}`;
    }
    probeAktualisieren();
  }

  function variante(v: WidgetOpts): void {
    if (!modus) return;
    const patch: Partial<WidgetOpts> = {};
    for (const f of modus.fields) {
      const wert = (v as unknown as Record<string, unknown>)[f];
      if (wert !== null && wert !== undefined) (patch as Record<string, unknown>)[f] = wert;
    }
    opts = { ...opts, ...patch };
    probeAktualisieren();
  }

  function aendern(patch: Partial<WidgetOpts>): void {
    opts = { ...opts, ...patch };
    probeAktualisieren();
  }

  function widget(): Widget | null {
    if (!quelleId || !modusId) return null;
    return { id: 'probe', source: quelleId, display: modusId as Widget['display'], x: 0, y: 0, name, opts: JSON.parse(JSON.stringify(opts)) as WidgetOpts };
  }

  function probeAktualisieren(): void {
    const w = widget();
    oled.simulate = probewert !== null && quelleId ? { [quelleId]: probewert } : {};
    oled.probeBox = null;
    oled.setzeProbe(w);
    if (kleinTimer) clearTimeout(kleinTimer);
    kleinTimer = setTimeout(async () => {
      if (!w) { klein = null; return; }
      const erg = await oled.renderEinzeln(w);
      klein = erg && erg.box.w > 0 ? { bild: erg.bild, w: erg.box.w, h: erg.box.h } : null;
    }, 80);
  }

  function einfuegen(): void {
    oled.probeEinfuegen();
    oled.simulate = {};
    probewert = null;
    onfertig();
  }

  onDestroy(() => { oled.setzeProbe(null); oled.simulate = {}; });
</script>

{#if wechselFuer}
  <div class="gruppe" style="border-color:var(--border-accent)">
    <div class="quelle-kopf"><div class="symbol"><i class="fa-solid fa-right-left"></i></div><div><div class="titel">Quelle wechseln</div><div class="unter">für "{wechselFuer.name || oled.quelle(wechselFuer.source)?.label}"</div></div></div>
    <button class="btn btn-klein" onclick={onfertig}><i class="fa-solid fa-xmark"></i>Abbrechen</button>
  </div>
{/if}

<div class="chips" title="Bereich der Datenquellen">
  {#each oled.katalog?.tabs ?? [] as t (t.id)}
    <button class="chip" class:active={tab === t.id} onclick={() => (tab = t.id)}>{t.label}</button>
  {/each}
</div>

<div class="gruppe">
  <div class="gruppe-titel"><i class="fa-solid fa-database"></i>Datenquelle<button class="hilfe" title="Hilfe zu Datenquellen" onclick={() => ui.oeffneHilfe('datenquellen')}>i</button></div>
  <div class="katalog-liste">
    {#each gruppen as g (g.gruppe)}
      {#if g.gruppe}<div class="katalog-gruppe">{g.gruppe}</div>{/if}
      {#each g.quellen as q (q.id)}
        <button class="quelle" class:active={quelleId === q.id} title={q.description || q.label} onclick={() => waehleQuelle(q)}>
          <span class="name">{q.label}</span>
          <span class="beispiel">{q.example}{q.unit && q.example ? ` ${q.unit}` : ''}</span>
        </button>
      {/each}
    {/each}
  </div>
</div>

{#if quelle && !wechselFuer}
  <div class="gruppe">
    <div class="gruppe-titel"><i class="fa-solid fa-shapes"></i>Darstellung<button class="hilfe" title="Hilfe zu Darstellungsarten" onclick={() => ui.oeffneHilfe('darstellungsarten')}>i</button></div>
    <div class="chips">
      {#each modi as m (m.id)}
        <button class="chip" class:active={modusId === m.id} title={m.description} onclick={() => setzeModus(m)}>{m.label}</button>
      {/each}
    </div>
    {#if modus && modus.variants.length}
      <div class="zeile"><span class="label">Vorgabe</span>
        <div class="chips">
          {#each modus.variants as v (v.id)}<button class="chip" onclick={() => variante(v.opts)}>{v.label}</button>{/each}
        </div>
      </div>
    {/if}
  </div>
  {#if modus}
    <OptionFelder felder={modus.fields} {opts} {quelle} onaendern={aendern} />
  {/if}
  <div class="gruppe">
    <div class="gruppe-titel"><i class="fa-solid fa-eye"></i>Vorschau<span class="badge badge-neutral" style="margin-left:auto">vom Backend</span></div>
    <div class="vorschau-box">
      {#if klein}
        <div class="ausschnitt" style="width:{klein.w * 3}px;height:{klein.h * 3}px"><img src="data:image/png;base64,{klein.bild}" alt="Vorschau des neuen Widgets" style="width:{128 * 3}px;height:{64 * 3}px"></div>
        <span class="mass">{klein.w} x {klein.h} Pixel</span>
      {:else}
        <span class="mass">Keine Vorschau</span>
      {/if}
    </div>
    {#if quelle.valueType === 'number' || quelle.valueType === 'percent'}
      <div class="zeile"><span class="label">Probewert</span>
        {#if probewert === null}
          <button class="btn btn-klein" title="Darstellung mit einem angenommenen Wert statt dem Livewert prüfen" onclick={() => { probewert = 50; probeAktualisieren(); }}><i class="fa-solid fa-flask"></i>Simulieren</button>
        {:else}
          <div class="feld-zeile">
            <Regler wert={probewert} min={0} max={100} onwahl={(v) => { probewert = v; probeAktualisieren(); }} />
            <button class="btn btn-klein" title="Zurück zum Livewert" onclick={() => { probewert = null; probeAktualisieren(); }}>Live</button>
          </div>
        {/if}
      </div>
    {/if}
    <div class="zeile"><span class="label">Name</span><input class="feld" bind:value={name} title="Eigener Name des Widgets" oninput={probeAktualisieren}></div>
  </div>
  <button class="btn btn-primary btn-breit" title="Widget an der markierten Stelle einfügen" onclick={einfuegen}><i class="fa-solid fa-plus"></i>Einfügen</button>
{/if}

<style>
  .ausschnitt { overflow: hidden; position: relative; max-width: 100%; }
  .ausschnitt img { position: absolute; left: 0; top: 0; image-rendering: pixelated; }
</style>
