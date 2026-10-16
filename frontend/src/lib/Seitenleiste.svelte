<script lang="ts">
  import { live } from '$lib/stores/live.svelte';
  import { ui, type Ansicht } from '$lib/stores/ui.svelte';
  import Schalter from '$lib/bausteine/Schalter.svelte';

  const nav: Array<{ id: Ansicht; symbol: string; label: string }> = [
    { id: 'fan', symbol: 'fa-fan', label: 'Lüfter' },
    { id: 'leds', symbol: 'fa-lightbulb', label: 'LEDs' },
    { id: 'display', symbol: 'fa-display', label: 'Display' },
  ];

  let jetzt = $state(new Date());
  $effect(() => {
    const t = setInterval(() => (jetzt = new Date()), 1000);
    return () => clearInterval(t);
  });

  function tempFarbe(t: number): string {
    if (t <= 25) return 'rgb(0,80,255)';
    if (t <= 35) { const f = (t - 25) / 10; return `rgb(${Math.round(200 * f)},${Math.round(80 + 175 * f)},${Math.round(255 * (1 - f))})`; }
    if (t <= 45) { const f = (t - 35) / 10; return `rgb(${Math.round(200 + 55 * f)},${Math.round(255 - 40 * f)},0)`; }
    if (t <= 55) { const f = (t - 45) / 10; return `rgb(255,${Math.round(215 - 115 * f)},0)`; }
    if (t <= 65) { const f = (t - 55) / 10; return `rgb(255,${Math.round(100 - 80 * f)},0)`; }
    return `rgb(255,${Math.round(20 * Math.max(0, 1 - (t - 65) / 10))},0)`;
  }
  const rgb = (c: { r: number; g: number; b: number }) => `rgb(${c.r},${c.g},${c.b})`;
  const glow = (c: { r: number; g: number; b: number }) => `rgba(${c.r},${c.g},${c.b},0.55)`;
  const offen = $derived(ui.seitenleisteOffen);
</script>

<aside class="sidebar" class:zu={!offen}>
  <div class="sb-top">
    <div class="sb-logo"><div class="sb-logo-icon"><i class="fa-solid fa-fire"></i></div>{#if offen}<div class="sb-logo-text">Pyro<span>Plus</span></div>{/if}</div>
    <button class="sb-collapse" title={offen ? 'Seitenleiste einklappen' : 'Seitenleiste ausklappen'} onclick={() => ui.setzeSeitenleiste(!offen)}><i class="fa-solid {offen ? 'fa-angles-left' : 'fa-angles-right'}"></i></button>
  </div>

  <div class="sb-temp" style="color:{tempFarbe(live.cpuTemp)}" title="Temperatur des Prozessors">
    {#if offen}<span class="sb-temp-val">{live.cpuTemp.toFixed(1)}</span><span class="sb-temp-unit">°C</span>{:else}<span class="sb-temp-mini">{live.cpuTemp.toFixed(0)}°</span>{/if}
  </div>

  <div class="sb-leds" title="Farben, wie die Hardware sie gerade meldet">
    {#each live.ledFarben as c, i (i)}
      <div class="sb-led" style="background:{rgb(c)};box-shadow:0 0 8px {glow(c)}, 0 0 18px {glow(c)}"></div>
    {/each}
  </div>

  {#if offen}
    <div class="sb-oled" title="Das Display gerade">
      <div class="sb-oled-screen">
        {#if live.oled?.preview && live.oledAn}<img src="data:image/png;base64,{live.oled.preview}" alt="Display jetzt">{:else}<div style="width:128px;height:64px"></div>{/if}
      </div>
    </div>
  {/if}

  <nav class="sb-nav">
    {#each nav as n (n.id)}
      <button class="nav-btn" class:active={ui.ansicht === n.id} title={offen ? '' : n.label} onclick={() => ui.zeige(n.id)}>
        <i class="fa-solid {n.symbol}"></i>{#if offen}<span>{n.label}</span>{/if}
      </button>
    {/each}
  </nav>

  {#if offen}
    <div class="sb-section-title">Schnellzugriff</div>
    <div class="toggle-row"><span class="toggle-label">Lüfter</span><Schalter klein an={live.fanAn} titel="Lüfter ein (Automatik) oder aus" onwahl={() => live.toggleFan()} /></div>
    <div class="toggle-row"><span class="toggle-label">LEDs</span><Schalter klein an={live.ledsAn} titel="LEDs ein oder aus" onwahl={() => live.toggleLeds()} /></div>
    <div class="toggle-row"><span class="toggle-label">Display</span><Schalter klein an={live.oledAn} titel="Display ein (Rotation) oder aus" onwahl={() => live.toggleOled()} /></div>
  {/if}

  <div class="sb-footer">
    <div><span class="status-dot" class:aus={!live.verbunden}></span>{#if offen}{live.verbunden ? 'Verbunden' : 'Getrennt'}{/if}</div>
    {#if offen}
      <div class="version" title="Version der Oberfläche{live.backendVersion && live.backendVersion !== ui.frontendVersion ? `, Backend ${live.backendVersion}` : ''}{live.hwProxy?.version ? `, Hardware-Proxy ${live.hwProxy.version}` : ''}">{ui.frontendVersion}{live.backendVersion && live.backendVersion !== ui.frontendVersion ? ` · Backend ${live.backendVersion}` : ''}</div>
      <div class="mono">{jetzt.toLocaleTimeString('de-DE')}</div>
    {/if}
  </div>
</aside>

<style>
  .sidebar.zu { padding: 14px 6px; align-items: center; }
  .sb-top { display: flex; align-items: center; justify-content: space-between; gap: 6px; }
  .sidebar.zu .sb-top { flex-direction: column; }
  .sb-collapse { width: 32px; height: 32px; border-radius: var(--radius-sm); border: 1px solid var(--border); color: var(--text-muted); display: inline-flex; align-items: center; justify-content: center; }
  .sb-collapse:hover { color: var(--text-primary); border-color: var(--border-accent); }
  .sb-temp-mini { font: 700 22px var(--mono); }
  .sidebar.zu .sb-leds { gap: 4px; }
  .sidebar.zu .sb-led { width: 10px; height: 10px; border-radius: 2px; }
  .sidebar.zu .nav-btn { justify-content: center; padding: 10px 0; width: 48px; }
  .status-dot.aus { background: var(--red); box-shadow: none; }
  .mono { font-family: var(--mono); }
  .version { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
</style>
