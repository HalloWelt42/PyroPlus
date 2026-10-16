<script lang="ts">
  /* LED-Bereich: Farben, wie die Hardware sie meldet, Effektgruppen, Palette, Einzel-LEDs. */
  import { live } from '$lib/stores/live.svelte';
  import { ui } from '$lib/stores/ui.svelte';
  import Segment from '$lib/bausteine/Segment.svelte';
  import Regler from '$lib/bausteine/Regler.svelte';
  import Schalter from '$lib/bausteine/Schalter.svelte';
  import { GRUPPEN, REAKTIV, PALETTE, hex, rgbAusHex, effektLabel, EFFEKT_SYMBOL } from './effekte';

  const leds = $derived(live.leds);
  const effekt = $derived(leds?.effect ?? 'off');
  const reaktiv = $derived(REAKTIV.includes(effekt));
  const bekannt = $derived(new Set(Object.values(live.effekte).flat().map((e) => e.id)));
  const gruppen = $derived(GRUPPEN.map((g) => ({ ...g, effekte: g.effekte.filter((e) => bekannt.size === 0 || bekannt.has(e)) })).filter((g) => g.effekte.length));
  const steuerung = $derived(reaktiv ? effekt : 'effekt');

  let gruppe = $state('farben');
  let ziel = $state<number>(-1);
  let helligkeit = $state<number | null>(null);
  let tempo = $state<number | null>(null);
  const helligkeitAnzeige = $derived(helligkeit ?? Math.round((leds?.brightness ?? 500) / 10));
  const tempoAnzeige = $derived(tempo ?? Math.round((leds?.speed ?? 50) / 10));

  $effect(() => {
    const g = GRUPPEN.find((x) => x.effekte.includes(effekt));
    if (g) gruppe = g.id;
  });

  const rgb = (c: { r: number; g: number; b: number }) => `rgb(${c.r},${c.g},${c.b})`;
  const glow = (c: { r: number; g: number; b: number }) => `rgba(${c.r},${c.g},${c.b},0.55)`;

  function farbeSetzen(h: string): void {
    const c = rgbAusHex(h);
    if (ziel === -1) void live.setLedColor(c);
    else if (ziel === -2) void live.setLedColor2(c);
    else void live.setLedIndColor(ziel, c);
  }
  function steuerungWaehlen(w: string): void {
    if (w === 'effekt') { if (reaktiv) void live.setLedEffect('static'); return; }
    void live.setLedEffect(w);
  }
</script>

<div class="main">
  <header class="kopf">
    <div class="kopf-zeile">
      <h1><i class="fa-solid fa-lightbulb"></i>LEDs</h1>
      <span class="chip-status" class:aus={!leds?.available}><i class="fa-solid {leds?.available ? 'fa-circle-check' : 'fa-plug-circle-xmark'}"></i>{leds?.available ? 'LEDs erreichbar' : 'Keine LEDs'}</span>
      <span class="chip-status neutral"><i class="fa-solid {EFFEKT_SYMBOL[effekt] ?? 'fa-power-off'}"></i>{effekt === 'off' ? 'Aus' : effektLabel(effekt, live.effektName(effekt))}</span>
      <div class="kopf-rechts">
        <button class="btn" class:btn-accent={live.ledsAn} title={live.ledsAn ? 'LEDs ausschalten' : 'LEDs einschalten; der letzte Effekt kehrt zurück'} onclick={() => live.toggleLeds()}><i class="fa-solid {live.ledsAn ? 'fa-toggle-on' : 'fa-toggle-off'}"></i>{live.ledsAn ? 'Ein' : 'Aus'}</button>
        <button class="btn" style="width:44px;padding:0" title="Hilfe zu den LEDs" onclick={() => ui.oeffneHilfe('leds')}><i class="fa-solid fa-question"></i></button>
      </div>
    </div>
  </header>

  <div class="inhalt">
    <section class="panel">
      <div class="panel-kopf"><i class="fa-solid fa-lightbulb"></i><div><div class="titel">Die vier LEDs</div><div class="unter">Farben, wie die Hardware sie gerade meldet</div></div></div>
      <div class="streifen">
        {#each live.ledFarben as c, i (i)}
          <div class="led"><div class="chip-led" style="background:{rgb(c)};box-shadow:0 0 12px {glow(c)}, 0 0 30px {glow(c)}, 0 0 46px 10px {glow(c)}"><span>{i + 1}</span></div></div>
        {/each}
      </div>
      <div class="zeile"><span class="label"><i class="fa-solid fa-sun"></i> Helligkeit</span><Regler wert={helligkeitAnzeige} min={1} max={100} einheit=" %" titel="Helligkeit aller LEDs" onwahl={(v) => (helligkeit = v)} onende={(v) => { helligkeit = null; void live.setLedBrightness(v * 10); }} /></div>
      <div class="zeile"><span class="label"><i class="fa-solid fa-gauge-high"></i> Tempo</span><Regler wert={tempoAnzeige} min={1} max={100} einheit=" %" titel="Geschwindigkeit der Animationen" onwahl={(v) => (tempo = v)} onende={(v) => { tempo = null; void live.setLedSpeed(v * 10); }} /></div>

      <div class="zeile"><span class="label">Farbe aus</span>
        <Segment wert={steuerung} onwahl={steuerungWaehlen} optionen={[
          { wert: 'temp_reactive', label: 'Temperatur', symbol: 'fa-temperature-half', titel: 'Blau kalt bis rot heiß, automatisch' },
          { wert: 'load_reactive', label: 'Auslastung', symbol: 'fa-microchip', titel: 'Farbe nach Prozessorlast' },
          { wert: 'effekt', label: 'Effekt', symbol: 'fa-palette', titel: 'Farben und Effekte selbst wählen' },
        ]} />
      </div>

      {#if reaktiv}
        <div class="reaktiv">
          <span class="badge badge-info"><i class="fa-solid fa-temperature-half"></i>{live.cpuTemp.toFixed(1)} °C</span>
          <span class="badge badge-info"><i class="fa-solid fa-microchip"></i>{(live.stats?.cpu.percent ?? 0).toFixed(0)} % Last</span>
          <span class="hinweistext">Die Farben folgen den Systemwerten. Für eigene Farben "Effekt" wählen.</span>
        </div>
      {:else}
        <div class="zeile"><span class="label">Einzel-LEDs</span><div class="feld-zeile"><Schalter an={!!leds?.individual_mode} titel="Jede LED bekommt ihre eigene Farbe" onwahl={(an) => live.setLedIndividual(an)} /><span class="hinweistext">{leds?.individual_mode ? 'Unten eine LED wählen, dann eine Farbe tippen' : 'Alle LEDs zeigen den Effekt'}</span></div></div>
        <div class="ziele">
          <button class="ziel" class:active={ziel === -1} title="Hauptfarbe der Effekte" onclick={() => (ziel = -1)}><span class="probe" style="background:{hex(leds?.color)}"></span>Hauptfarbe</button>
          <button class="ziel" class:active={ziel === -2} title="Zweite Farbe, zum Beispiel für Verlauf" onclick={() => (ziel = -2)}><span class="probe" style="background:{hex(leds?.color2)}"></span>Zweitfarbe</button>
          {#if leds?.individual_mode}
            {#each leds.individual_colors as c, i (i)}
              <button class="ziel" class:active={ziel === i} onclick={() => (ziel = i)}><span class="probe" style="background:{hex(c)}"></span>LED {i + 1}</button>
            {/each}
          {/if}
        </div>
        <div class="palette">
          {#each PALETTE as h (h)}<button class="farbe" style="background:{h}" title={h} aria-label={h} onclick={() => farbeSetzen(h)}></button>{/each}
        </div>
      {/if}
    </section>

    <section class="panel">
      <div class="panel-kopf"><i class="fa-solid fa-wand-magic-sparkles"></i><div><div class="titel">Effekte</div><div class="unter">{reaktiv ? 'Im Temperaturmodus sind die Effekte abgeschaltet' : 'Ein Klick wechselt den Effekt sofort'}</div></div></div>
      {#if reaktiv}
        <div class="leer"><div class="symbol"><i class="fa-solid fa-temperature-half"></i></div><h3>Temperaturmodus</h3><p>Die LEDs zeigen die Prozessortemperatur. Links "Effekt" wählen, um Farben und Animationen zu nutzen.</p></div>
      {:else}
        <div class="chips">
          {#each gruppen as g (g.id)}<button class="chip" class:active={gruppe === g.id} onclick={() => (gruppe = g.id)}><i class="fa-solid {g.symbol}"></i>{g.label}</button>{/each}
        </div>
        {#each gruppen.filter((g) => g.id === gruppe) as g (g.id)}
          <p class="hinweistext">{g.text}</p>
          <div class="effekte">
            {#each g.effekte as e (e)}
              <button class="effekt" class:active={effekt === e} onclick={() => live.setLedEffect(e)}><i class="fa-solid {EFFEKT_SYMBOL[e] ?? 'fa-circle'}"></i><span>{effektLabel(e, live.effektName(e))}</span></button>
            {/each}
          </div>
        {/each}
      {/if}
    </section>
  </div>
</div>

<style>
  .inhalt { flex: 1; min-height: 0; overflow-y: auto; overflow-x: clip; padding: 16px 20px; display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 16px; align-content: start; }
  .panel { background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--radius); padding: 16px; display: flex; flex-direction: column; gap: 12px; min-width: 0; }
  .panel-kopf { display: flex; align-items: center; gap: 12px; }
  .panel-kopf > i { font-size: 26px; color: var(--accent); }
  .panel-kopf .titel { font-size: var(--fs-lg); font-weight: 700; line-height: 1.1; }
  .panel-kopf .unter { font-size: var(--fs-xs); color: var(--text-muted); }
  .streifen { background: #000; border: 1px solid #222; border-radius: var(--radius); padding: 22px; display: flex; justify-content: center; gap: 28px; }
  .led { position: relative; width: 52px; height: 52px; display: flex; align-items: center; justify-content: center; }
  .chip-led { width: 30px; height: 30px; border-radius: 7px; border: 2px solid #555; position: relative; display: flex; align-items: center; justify-content: center; transition: background 0.6s, box-shadow 0.6s; }
  .chip-led span { font: 700 11px var(--mono); color: rgba(255,255,255,0.45); }
  .zeile { grid-template-columns: 130px minmax(0, 1fr); }
  .zeile .label { display: flex; align-items: center; gap: 6px; }
  .zeile .label i { color: var(--accent); }
  .reaktiv { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
  .hinweistext { font-size: var(--fs-sm); color: var(--text-muted); }
  .ziele { display: flex; gap: 8px; flex-wrap: wrap; }
  .ziel { display: inline-flex; align-items: center; gap: 8px; height: 40px; padding: 0 12px; border-radius: var(--radius-sm); border: 1px solid var(--border); background: var(--bg-surface); color: var(--text-secondary); font-size: var(--fs-sm); }
  .ziel.active { border-color: var(--border-accent); background: var(--accent-dim); color: var(--accent); }
  .probe { width: 20px; height: 20px; border-radius: 5px; border: 1px solid rgba(255,255,255,0.25); }
  .palette { display: grid; grid-template-columns: repeat(10, minmax(0, 1fr)); gap: 8px; }
  .farbe { aspect-ratio: 1; border-radius: 8px; border: 2px solid rgba(255,255,255,0.12); }
  .farbe:hover { border-color: #fff; transform: scale(1.08); }
  .effekte { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 8px; }
  .effekt { display: flex; flex-direction: column; align-items: center; gap: 8px; padding: 14px 10px; border-radius: var(--radius-sm); border: 1px solid var(--border); background: var(--bg-surface); color: var(--text-secondary); font-size: var(--fs-sm); font-weight: 500; }
  .effekt i { font-size: 22px; color: var(--accent); }
  .effekt:hover { border-color: var(--border-strong); color: var(--text-primary); }
  .effekt.active { background: var(--accent-dim); border-color: var(--accent); color: var(--accent); }
  .chip-status.neutral { background: rgba(255,255,255,0.06); color: var(--text-secondary); }
  @media (max-width: 1100px) { .inhalt { grid-template-columns: minmax(0, 1fr); } }
</style>
