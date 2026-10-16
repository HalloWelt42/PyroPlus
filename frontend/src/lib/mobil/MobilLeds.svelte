<script lang="ts">
  import { live } from '$lib/stores/live.svelte';
  import { GRUPPEN, REAKTIV, PALETTE, effektLabel, EFFEKT_SYMBOL, rgbAusHex } from '$lib/leds/effekte';

  const leds = $derived(live.leds);
  const effekt = $derived(leds?.effect ?? 'off');
  const reaktiv = $derived(REAKTIV.includes(effekt));
  const bekannt = $derived(new Set(Object.values(live.effekte).flat().map((e) => e.id)));
  const alle = $derived(GRUPPEN.flatMap((g) => g.effekte).filter((e) => bekannt.size === 0 || bekannt.has(e)));
  const rgb = (c: { r: number; g: number; b: number }) => `rgb(${c.r},${c.g},${c.b})`;
  const glow = (c: { r: number; g: number; b: number }) => `rgba(${c.r},${c.g},${c.b},0.55)`;
</script>

<div class="mobil-kopf">
  <h1><i class="fa-solid fa-lightbulb" style="color:var(--accent);margin-right:10px"></i>LEDs</h1>
  <button class="btn" class:btn-accent={live.ledsAn} style="height:44px" onclick={() => live.toggleLeds()}><i class="fa-solid {live.ledsAn ? 'fa-toggle-on' : 'fa-toggle-off'}"></i>{live.ledsAn ? 'Ein' : 'Aus'}</button>
</div>
<div class="mobil-inhalt">
  <div class="streifen">
    {#each live.ledFarben as c, i (i)}<div class="led" style="background:{rgb(c)};box-shadow:0 0 14px {glow(c)}, 0 0 34px {glow(c)}"></div>{/each}
  </div>
  <div class="mobil-regler"><span class="label">Helligkeit</span><input type="range" min="1" max="100" value={Math.round((leds?.brightness ?? 500) / 10)} onchange={(e) => live.setLedBrightness(Number((e.currentTarget as HTMLInputElement).value) * 10)}><span class="wert">{Math.round((leds?.brightness ?? 500) / 10)} %</span></div>
  <div class="mobil-regler"><span class="label">Tempo</span><input type="range" min="1" max="100" value={Math.round((leds?.speed ?? 50) / 10)} onchange={(e) => live.setLedSpeed(Number((e.currentTarget as HTMLInputElement).value) * 10)}><span class="wert">{Math.round((leds?.speed ?? 50) / 10)} %</span></div>
  <div class="mobil-abschnitt">Farbe aus</div>
  <div class="segment">
    <button class:active={effekt === 'temp_reactive'} onclick={() => live.setLedEffect('temp_reactive')}><i class="fa-solid fa-temperature-half"></i>Temp</button>
    <button class:active={effekt === 'load_reactive'} onclick={() => live.setLedEffect('load_reactive')}><i class="fa-solid fa-microchip"></i>Last</button>
    <button class:active={!reaktiv} onclick={() => { if (reaktiv) void live.setLedEffect('static'); }}><i class="fa-solid fa-palette"></i>Effekt</button>
  </div>
  {#if !reaktiv}
    <div class="mobil-abschnitt">Hauptfarbe</div>
    <div class="palette">{#each PALETTE as h (h)}<button class="farbe" style="background:{h}" aria-label={h} onclick={() => live.setLedColor(rgbAusHex(h))}></button>{/each}</div>
    <div class="mobil-abschnitt">Effekt</div>
    <div class="effekte">
      {#each alle as e (e)}<button class="effekt" class:active={effekt === e} onclick={() => live.setLedEffect(e)}><i class="fa-solid {EFFEKT_SYMBOL[e] ?? 'fa-circle'}"></i>{effektLabel(e, live.effektName(e))}</button>{/each}
    </div>
  {:else}
    <p class="hinweis">Die Farben folgen {effekt === 'temp_reactive' ? 'der Temperatur' : 'der Auslastung'}: {live.cpuTemp.toFixed(1)} °C, {(live.stats?.cpu.percent ?? 0).toFixed(0)} % Last.</p>
  {/if}
</div>

<style>
  .streifen { background: #000; border: 1px solid #222; border-radius: 12px; padding: 22px; display: flex; justify-content: center; gap: 26px; }
  .led { width: 30px; height: 30px; border-radius: 7px; border: 2px solid #555; transition: background 0.6s, box-shadow 0.6s; }
  .palette { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 10px; }
  .farbe { aspect-ratio: 1; border-radius: 10px; border: 2px solid rgba(255,255,255,0.12); }
  .effekte { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 8px; }
  .effekt { min-width: 0; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; display: flex; align-items: center; gap: 10px; height: 48px; padding: 0 12px; border-radius: 12px; border: 1px solid var(--border); background: #0b0f1a; color: var(--text-secondary); font-size: 16px; }
  .effekt i { color: var(--accent); width: 22px; text-align: center; }
  .effekt.active { border-color: var(--accent); background: var(--accent-dim); color: var(--accent); }
  .hinweis { font-size: 15px; color: var(--text-muted); text-align: center; }
</style>
