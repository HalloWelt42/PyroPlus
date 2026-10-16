<script lang="ts">
  import { live } from '$lib/stores/live.svelte';

  const fan = $derived(live.fan);
  const profile: Record<string, string> = { silent: 'Leise', balanced: 'Ausgewogen', performance: 'Leistung', custom: 'Eigene' };
</script>

<div class="mobil-kopf">
  <h1><i class="fa-solid fa-fan" style="color:var(--accent);margin-right:10px"></i>Lüfter</h1>
  <span class="temp">{live.cpuTemp.toFixed(1)}°</span>
</div>
<div class="mobil-inhalt">
  <div class="werte">
    <div class="wert"><span class="zahl">{fan?.current_rpm ?? 0}</span><span class="einheit">RPM</span></div>
    <div class="wert"><span class="zahl">{Math.round(fan?.current_duty ?? 0)}</span><span class="einheit">% Leistung</span></div>
    <div class="wert"><span class="zahl" style="color:{fan?.case_on ? 'var(--green)' : 'var(--text-muted)'}">{fan?.case_on ? 'An' : 'Aus'}</span><span class="einheit">Gehäuse</span></div>
  </div>
  <div class="mobil-abschnitt">CPU-Lüfter</div>
  <div class="segment">
    <button class:active={fan?.mode === 'auto'} onclick={() => live.setFanMode('auto')}><i class="fa-solid fa-wand-magic-sparkles"></i>Auto</button>
    <button class:active={fan?.mode === 'manual'} onclick={() => live.setFanMode('manual')}><i class="fa-solid fa-hand"></i>Manuell</button>
    <button class:active={fan?.mode === 'off'} onclick={() => live.setFanMode('off')}><i class="fa-solid fa-power-off"></i>Aus</button>
  </div>
  {#if fan?.mode === 'manual'}
    <div class="mobil-regler"><span class="label">Leistung</span><input type="range" min="0" max="100" step="5" value={fan.manual_speed} onchange={(e) => live.setFanManualSpeed(Number((e.currentTarget as HTMLInputElement).value))}><span class="wert">{fan.manual_speed} %</span></div>
  {/if}
  <div class="mobil-abschnitt">Profil</div>
  <div class="chips">
    {#each fan?.profiles ?? [] as p (p)}<button class="chip gross" class:active={fan?.profile === p} onclick={() => live.setFanProfile(p)}>{profile[p] ?? p}</button>{/each}
  </div>
  <div class="mobil-abschnitt">Gehäuselüfter</div>
  <div class="mobil-regler"><span class="label">Ein ab</span><input type="range" min="35" max="75" value={fan?.threshold_on ?? 55} onchange={(e) => live.setFanSettings({ threshold_on: Number((e.currentTarget as HTMLInputElement).value), case_profile: 'custom' })}><span class="wert">{fan?.threshold_on ?? 55} °C</span></div>
  <div class="mobil-regler"><span class="label">Aus unter</span><input type="range" min="30" max="70" value={fan?.threshold_off ?? 48} onchange={(e) => live.setFanSettings({ threshold_off: Number((e.currentTarget as HTMLInputElement).value), case_profile: 'custom' })}><span class="wert">{fan?.threshold_off ?? 48} °C</span></div>
  <p class="hinweis">Die Temperaturkurve bearbeitest du am Rechner.</p>
</div>

<style>
  .werte { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) minmax(0, 1fr); gap: 10px; }
  .wert { display: flex; flex-direction: column; align-items: center; padding: 12px 6px; border-radius: 12px; border: 1px solid var(--border); background: #0b0f1a; }
  .zahl { font: 700 24px var(--mono); }
  .einheit { font-size: 14px; color: var(--text-muted); }
  .chip.gross { height: 44px; padding: 0 16px; font-size: 16px; }
  .hinweis { font-size: 15px; color: var(--text-muted); text-align: center; }
</style>
