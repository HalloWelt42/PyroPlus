<script>
import { onMount, onDestroy } from 'svelte';
import { getState } from './lib/stores/state.svelte.js';
import FanControl from './lib/components/FanControl.svelte';
import LEDLab from './lib/components/LEDLab.svelte';
import OLEDStudio from './lib/components/OLEDStudio.svelte';

const s = getState();

const nav = [
  { id: 'fan', icon: 'fa-solid fa-fan', label: 'Lüfter' },
  { id: 'leds', icon: 'fa-solid fa-lightbulb', label: 'LEDs' },
  { id: 'oled', icon: 'fa-solid fa-display', label: 'Display' },
];

let now = $state(new Date());
let clockTimer;
let viewKey = $state(0);
let sidebarOpen = $state(true);

onMount(() => { s.init(); clockTimer = setInterval(() => now = new Date(), 1000); });
onDestroy(() => { s.destroy(); clearInterval(clockTimer); });

function selectView(id) {
  if (s.currentView === id) return;
  s.currentView = id;
  viewKey++;
}

function tempToColor(t) {
  if (t <= 25) return 'rgb(0,60,255)';
  if (t <= 30) { const f = (t-25)/5; return `rgb(${Math.round(255*f)},${Math.round(60+180*f)},${Math.round(255*(1-f))})`; }
  if (t <= 40) { const f = (t-30)/10; return `rgb(255,${Math.round(240-100*f)},0)`; }
  if (t <= 55) { const f = (t-40)/15; return `rgb(255,${Math.round(140-100*f)},0)`; }
  return `rgb(255,${Math.round(40*Math.max(0,1-(t-55)/5))},0)`;
}
const tempColor = $derived(tempToColor(s.stats?.cpu?.temp || 0));
</script>

<!-- Toasts -->
<div class="toast-container">
  {#each s.toasts as t (t.id)}<div class="toast toast-{t.type}">{t.msg}</div>{/each}
</div>

<div class="app" class:sidebar-collapsed={!sidebarOpen}>
  <!-- ═══ SIDEBAR ═══ -->
  <aside class="sidebar">
    <div class="sb-top">
      <div class="sb-logo">
        <div class="sb-logo-icon"><i class="fa-solid fa-fire"></i></div>
        {#if sidebarOpen}<div class="sb-logo-text">Pyro<span>Plus</span></div>{/if}
      </div>

      <button class="sb-collapse" onclick={() => sidebarOpen = !sidebarOpen} aria-label="Seitenleiste umschalten">
        <i class="fa-solid" class:fa-angles-left={sidebarOpen} class:fa-angles-right={!sidebarOpen}></i>
      </button>
    </div>

    <!-- Temperatur -->
    <div class="sb-temp" style="color:{tempColor}">
      {#if sidebarOpen}
        <span class="sb-temp-val">{(s.stats?.cpu?.temp || 0).toFixed(1)}</span><span class="sb-temp-unit">°C</span>
      {:else}
        <span class="sb-temp-mini">{(s.stats?.cpu?.temp || 0).toFixed(0)}°</span>
      {/if}
    </div>

    <!-- LED-Status -->
    <div class="sb-leds">
      {#each s.ledColors as c}
        <div class="sb-led" style="background:{c.rgb};box-shadow:0 0 6px {c.glow}"></div>
      {/each}
    </div>

    <!-- OLED-Display 128×64 echte Pixel -->
    {#if sidebarOpen}
      <div class="sb-oled">
        <div class="sb-oled-screen">
          {#if s.oled?.preview}
            <img src="data:image/png;base64,{s.oled.preview}" alt="OLED" class="sb-oled-img"/>
          {:else}
            <div class="sb-oled-off"></div>
          {/if}
        </div>
      </div>
    {/if}

    <nav class="sb-nav">
      {#each nav as item}
        <button class="nav-btn" class:active={s.currentView === item.id}
          onclick={() => selectView(item.id)} title={sidebarOpen ? '' : item.label}>
          <i class="{item.icon}"></i>
          {#if sidebarOpen}<span>{item.label}</span>{/if}
        </button>
      {/each}
    </nav>

    {#if sidebarOpen}
      <div class="sb-toggles">
        <div class="sb-section-title">Schnellzugriff</div>
        {#each [
          { key: 'fan', label: 'Lüfter', active: s.fanActive, toggle: () => s.toggleFan() },
          { key: 'leds', label: 'LEDs', active: s.ledsActive, toggle: () => s.toggleLeds() },
          { key: 'oled', label: 'Display', active: s.oledActive, toggle: () => s.toggleOled() },
        ] as item}
          <div class="toggle-row">
            <span class="toggle-dot" class:on={item.active}></span>
            <span class="toggle-label">{item.label}</span>
            <button class="toggle-switch" class:on={item.active} onclick={item.toggle} aria-label="{item.label} umschalten"></button>
          </div>
        {/each}
      </div>
    {/if}

    <div class="sb-footer">
      <div class="sb-status"><span class="status-dot" class:on={s.connected}></span>{#if sidebarOpen}{s.connected ? 'Verbunden' : 'Getrennt'}{/if}</div>
      {#if sidebarOpen}
        <div class="sb-meta">Version {s.version || '?'} · Hardware {s.hwProxy?.version || '?'}</div>
        <div class="sb-clock">{now.toLocaleTimeString('de-DE')}</div>
      {/if}
    </div>
  </aside>

  <!-- ═══ HAUPTBEREICH ═══ -->
  <main class="main">
    {#key viewKey}
      <div class="view">
        {#if s.currentView === 'fan'}<FanControl state={s} />
        {:else if s.currentView === 'leds'}<LEDLab state={s} />
        {:else if s.currentView === 'oled'}<OLEDStudio state={s} />
        {/if}
      </div>
    {/key}
  </main>

  <!-- ═══ BOTTOM TAB BAR (Mobil) ═══ -->
  <nav class="bottom-bar">
    {#each nav as item}
      <button class="tab-btn" class:active={s.currentView === item.id}
        onclick={() => selectView(item.id)}>
        <i class="{item.icon}"></i>
        <span>{item.label}</span>
      </button>
    {/each}
  </nav>
</div>

<style>
  /* ═══ APP SHELL ═══ */
  .app {
    display: grid;
    grid-template-columns: 240px 1fr;
    grid-template-rows: 1fr;
    height: 100vh; width: 100vw;
    overflow: hidden;
    user-select: none;
    -webkit-user-select: none;
    transition: grid-template-columns 250ms ease;
  }
  .app.sidebar-collapsed {
    grid-template-columns: 64px 1fr;
  }

  /* ═══ SIDEBAR ═══ */
  .sidebar {
    background: var(--bg-base);
    border-right: 1px solid var(--border);
    display: flex; flex-direction: column;
    padding: 14px 10px;
    overflow: hidden;
    transition: all 250ms ease;
  }

  .sb-top { display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px; gap: 6px; }
  .sidebar-collapsed .sb-top { flex-direction: column; gap: 8px; }
  .sidebar-collapsed .sb-logo { padding: 4px 0; justify-content: center; }
  .sb-logo { display: flex; align-items: center; gap: 10px; padding: 4px 6px; }
  .sb-logo-icon {
    width: 40px; height: 40px; border-radius: var(--radius);
    background: linear-gradient(135deg, var(--accent), #0066ff);
    display: flex; align-items: center; justify-content: center;
    font-size: var(--fs-sm); color: #fff; flex-shrink: 0;
  }
  .sb-logo-text { font-size: var(--fs-lg); font-weight: 700; letter-spacing: -0.02em; white-space: nowrap; }
  .sb-logo-text span { color: var(--accent); }

  .sb-collapse {
    width: 32px; height: 32px; border-radius: var(--radius-sm);
    border: 1px solid var(--border); background: none;
    color: var(--text-muted); cursor: pointer;
    display: flex; align-items: center; justify-content: center;
    font-size: var(--fs-xs); transition: all var(--tr); flex-shrink: 0;
  }
  .sb-collapse:hover { color: var(--text-primary); border-color: var(--border-accent); }

  /* Temperatur in Sidebar */
  .sb-temp { text-align: center; margin-bottom: 16px; transition: color 1s; }
  .sb-temp-val { font: 800 48px var(--mono); line-height: 1; }
  .sb-temp-unit { font: 400 20px var(--font); color: var(--text-muted); }
  .sb-temp-mini { font: 700 24px var(--mono); }
  .sidebar-collapsed .sb-temp { margin-bottom: 8px; }

  /* LED-Status */
  .sb-leds { display: flex; justify-content: center; gap: 10px; margin-bottom: 16px; }
  .sb-led { width: 18px; height: 18px; border-radius: 4px; border: 1px solid rgba(255,255,255,0.08); transition: background 1s, box-shadow 1s; }
  .sidebar-collapsed .sb-leds { gap: 4px; }
  .sidebar-collapsed .sb-led { width: 10px; height: 10px; border-radius: 2px; }

  /* OLED-Display 1:1 */
  .sb-oled { display: flex; justify-content: center; margin: 14px 0 36px; }
  .sb-oled-screen {
    width: 132px; height: 68px;
    border: 2px solid #333;
    border-radius: 2px;
    background: #000;
    display: flex; align-items: center; justify-content: center;
    overflow: hidden;
  }
  .sb-oled-img {
    width: 128px; height: 64px;
    image-rendering: pixelated;
    display: block;
  }
  .sb-oled-off { width: 128px; height: 64px; }

  .sb-nav { display: flex; flex-direction: column; gap: 4px; margin-bottom: 16px; }
  .nav-btn {
    display: flex; align-items: center; gap: 12px;
    padding: 10px 14px; width: 100%;
    border-radius: var(--radius-sm); border: none; background: none;
    color: var(--text-secondary); font: 500 var(--fs-sm) var(--font);
    cursor: pointer; transition: all 150ms ease; text-align: left;
    white-space: nowrap;
  }
  .nav-btn i { width: 22px; text-align: center; font-size: var(--fs-base); flex-shrink: 0; }
  .nav-btn:hover { background: rgba(255,255,255,0.04); color: var(--text-primary); }
  .nav-btn.active {
    background: var(--accent-dim); color: var(--accent);
    border: 1px solid var(--border-accent);
  }
  .sidebar-collapsed .nav-btn { justify-content: center; padding: 10px 0; }

  .sb-toggles { padding: 10px 6px; }
  .sb-section-title {
    font: 600 var(--fs-xs) var(--font); text-transform: uppercase;
    letter-spacing: 0.1em; color: var(--text-muted);
    padding: 0 8px; margin-bottom: 8px;
  }
  .toggle-row { display: flex; align-items: center; gap: 10px; padding: 6px 8px; border-radius: var(--radius-sm); }
  .toggle-label { font: 500 var(--fs-sm) var(--font); color: var(--text-secondary); flex: 1; }
  .toggle-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--text-muted); transition: all var(--tr); flex-shrink: 0; }
  .toggle-dot.on { background: var(--green); box-shadow: 0 0 8px rgba(0,232,138,0.5); }
  .toggle-switch {
    width: 40px; height: 22px; border-radius: 11px; border: none;
    background: rgba(255,255,255,0.1); cursor: pointer; position: relative;
    transition: background var(--tr); flex-shrink: 0;
  }
  .toggle-switch.on { background: var(--green); }
  .toggle-switch::after {
    content: ''; position: absolute; top: 3px; left: 3px;
    width: 16px; height: 16px; border-radius: 50%; background: #fff;
    transition: transform var(--tr); box-shadow: 0 1px 3px rgba(0,0,0,0.3);
  }
  .toggle-switch.on::after { transform: translateX(18px); }

  .sb-footer { margin-top: auto; padding: 12px 10px; border-top: 1px solid var(--border); }
  .sb-status { display: flex; align-items: center; gap: 8px; font: 500 var(--fs-xs) var(--font); color: var(--text-muted); }
  .status-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--red); flex-shrink: 0; }
  .status-dot.on { background: var(--green); box-shadow: 0 0 8px rgba(0,232,138,0.4); }
  .sb-meta { font: 500 var(--fs-xs) var(--mono); color: var(--text-muted); margin-top: 4px; }
  .sb-clock { font: 600 var(--fs-sm) var(--mono); color: var(--text-label); margin-top: 3px; }

  /* ═══ HAUPTBEREICH ═══ */
  .main {
    overflow: hidden;
    display: flex;
    flex-direction: column;
  }
  .view {
    flex: 1;
    overflow-y: auto;
    overflow-x: hidden;
    padding: 16px 20px;
    animation: viewIn 200ms ease;
  }
  @keyframes viewIn {
    from { opacity: 0; transform: translateY(4px); }
    to { opacity: 1; transform: translateY(0); }
  }

  /* ═══ BOTTOM BAR (nur Mobil) ═══ */
  .bottom-bar { display: none; }

  /* ═══ TOASTS ═══ */
  .toast-container { position: fixed; top: 14px; right: 14px; z-index: 9999; display: flex; flex-direction: column; gap: 8px; }

  /* ═══ MOBIL ═══ */
  @media (max-width: 768px) {
    .app, .app.sidebar-collapsed {
      grid-template-columns: 1fr;
      grid-template-rows: 1fr 60px;
    }
    .sidebar { display: none; }

    .bottom-bar {
      display: flex;
      background: var(--bg-base);
      border-top: 1px solid var(--border);
      padding: 0 8px;
      padding-bottom: env(safe-area-inset-bottom, 0);
    }
    .tab-btn {
      flex: 1; display: flex; flex-direction: column; align-items: center;
      justify-content: center; gap: 4px;
      border: none; background: none;
      color: var(--text-muted); font: 500 var(--fs-xs) var(--font);
      cursor: pointer; transition: color 150ms;
      padding: 8px 0;
    }
    .tab-btn i { font-size: var(--fs-lg); }
    .tab-btn.active { color: var(--accent); }

    .view { padding: 12px 12px; }
  }
</style>
