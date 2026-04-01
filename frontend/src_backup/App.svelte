<script>
import { onMount, onDestroy } from 'svelte';
import { getState } from './lib/stores/state.svelte.js';
import Dashboard from './lib/components/Dashboard.svelte';
import FanControl from './lib/components/FanControl.svelte';
import LEDLab from './lib/components/LEDLab.svelte';
import OLEDStudio from './lib/components/OLEDStudio.svelte';
import Settings from './lib/components/Settings.svelte';

const s = getState();

const nav = [
  { id: 'dashboard', icon: '◆', label: 'Übersicht' },
  { id: 'fan', icon: '⟳', label: 'Lüfter' },
  { id: 'leds', icon: '◈', label: 'LEDs' },
  { id: 'oled', icon: '▣', label: 'Display' },
  { id: 'settings', icon: '⚙', label: 'Einstellungen' },
];

let now = $state(new Date());
let clockTimer;
onMount(() => { s.init(); clockTimer = setInterval(() => now = new Date(), 1000); });
onDestroy(() => { s.destroy(); clearInterval(clockTimer); });
</script>

<div class="toast-container">
  {#each s.toasts as t (t.id)}<div class="toast toast-{t.type}">{t.msg}</div>{/each}
</div>

<div class="shell">
  <aside class="sidebar">
    <!-- Logo -->
    <div class="sb-logo">
      <div class="sb-logo-icon">P</div>
      <div class="sb-logo-text">PironMan <span>DLX</span></div>
    </div>

    <!-- Navigation -->
    <div class="sb-section">
      <div class="sb-section-title">Navigation</div>
      {#each nav as item}
        <button class="nav-btn" class:active={s.currentView === item.id}
          onclick={() => s.currentView = item.id}>
          <span class="nav-icon">{item.icon}</span>
          <span>{item.label}</span>
        </button>
      {/each}
    </div>

    <!-- Power Toggles -->
    <div class="sb-power">
      <div class="sb-section-title">Schnellzugriff</div>
      <div class="power-row">
        <span class="power-dot" class:on={s.fanActive}></span>
        <span class="power-label">Lüfter</span>
        <button class="power-toggle" class:on={s.fanActive} onclick={() => s.toggleFan()} aria-label="Lüfter umschalten"></button>
      </div>
      <div class="power-row">
        <span class="power-dot" class:on={s.ledsActive}></span>
        <span class="power-label">LEDs</span>
        <button class="power-toggle" class:on={s.ledsActive} onclick={() => s.toggleLeds()} aria-label="LEDs umschalten"></button>
      </div>
      <div class="power-row">
        <span class="power-dot" class:on={s.oledActive}></span>
        <span class="power-label">Display</span>
        <button class="power-toggle" class:on={s.oledActive} onclick={() => s.toggleOled()} aria-label="Display umschalten"></button>
      </div>
    </div>

    <!-- Footer -->
    <div class="sb-footer">
      <div class="sb-status"><span class="dot" class:on={s.connected}></span>{s.connected ? 'WebSocket verbunden' : 'Getrennt'}</div>
      <div class="sb-version">Frontend v2.5.4 · Backend v{s.version || '?'} · HW {s.hwProxy?.version || '?'}</div>
      <div class="sb-clock">{now.toLocaleTimeString('de-DE')}</div>
    </div>
  </aside>

  <main class="main">
    {#if s.currentView === 'dashboard'}<Dashboard state={s} />
    {:else if s.currentView === 'fan'}<FanControl state={s} />
    {:else if s.currentView === 'leds'}<LEDLab state={s} />
    {:else if s.currentView === 'oled'}<OLEDStudio state={s} />
    {:else if s.currentView === 'settings'}<Settings state={s} />
    {/if}
  </main>
</div>

<style>
  .shell { display: grid; grid-template-columns: 240px 1fr; height: 100vh; }
  .sidebar {
    background: var(--bg-base); border-right: 1px solid var(--border);
    display: flex; flex-direction: column; padding: 16px 10px; overflow: hidden;
  }
  .sb-logo { display: flex; align-items: center; gap: 10px; padding: 8px 10px; margin-bottom: 20px; }
  .sb-logo-icon { width: 32px; height: 32px; border-radius: 8px; background: linear-gradient(135deg, var(--accent), #0066ff); display: flex; align-items: center; justify-content: center; font-size: 16px; color: #fff; font-weight: 700; }
  .sb-logo-text { font-size: 15px; font-weight: 700; letter-spacing: -0.02em; }
  .sb-logo-text span { color: var(--accent); }

  .sb-section { margin-bottom: 16px; }
  .sb-section-title { font-size: 10px; text-transform: uppercase; letter-spacing: 0.1em; color: var(--text-muted); padding: 0 12px; margin-bottom: 6px; font-weight: 600; }

  .nav-btn {
    display: flex; align-items: center; gap: 10px; padding: 8px 12px; width: 100%;
    border-radius: var(--radius-sm); border: none; background: none;
    color: var(--text-secondary); font-size: 13px; font-family: inherit;
    cursor: pointer; transition: all var(--tr); text-align: left;
  }
  .nav-btn:hover { background: rgba(255,255,255,0.04); color: var(--text-primary); }
  .nav-btn.active { background: var(--accent-dim); color: var(--accent); border: 1px solid var(--border-accent); }
  .nav-icon { width: 20px; text-align: center; font-size: 14px; }

  .sb-power { padding: 10px 4px; margin-top: 8px; }
  .power-row { display: flex; align-items: center; gap: 8px; padding: 6px 8px; border-radius: var(--radius-sm); margin-bottom: 3px; }
  .power-row:hover { background: rgba(255,255,255,0.02); }
  .power-label { font-size: 12px; color: var(--text-secondary); flex: 1; }
  .power-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--text-muted); transition: all var(--tr); }
  .power-dot.on { background: var(--green); box-shadow: 0 0 6px rgba(0,232,138,0.5); }
  .power-toggle {
    width: 36px; height: 20px; border-radius: 10px; border: none;
    background: rgba(255,255,255,0.1); cursor: pointer; position: relative;
    transition: background var(--tr);
  }
  .power-toggle.on { background: var(--green); }
  .power-toggle::after {
    content: ''; position: absolute; top: 2px; left: 2px;
    width: 16px; height: 16px; border-radius: 50%; background: #fff;
    transition: transform var(--tr); box-shadow: 0 1px 3px rgba(0,0,0,0.3);
  }
  .power-toggle.on::after { transform: translateX(16px); }

  .sb-footer { margin-top: auto; padding: 12px 8px; border-top: 1px solid var(--border); }
  .sb-status { display: flex; align-items: center; gap: 6px; font-size: 11px; color: var(--text-muted); }
  .dot { width: 6px; height: 6px; border-radius: 50%; background: var(--red); }
  .dot.on { background: var(--green); box-shadow: 0 0 6px rgba(0,232,138,0.4); }
  .sb-version { font-family: var(--mono); font-size: 10px; color: var(--text-muted); margin-top: 4px; }
  .sb-clock { font-family: var(--mono); font-size: 12px; color: var(--text-label); margin-top: 2px; }

  .main { overflow-y: auto; padding: 24px 28px; }
</style>
