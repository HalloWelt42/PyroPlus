<script>
  import { onMount } from 'svelte';
  import { api } from '../api/client.js';
  let { state: s } = $props();
  let tokenVisible = $state(false);
  let copyMsg = $state('');
  const host = window.location.hostname;

  /* Disk-Konfiguration */
  let allDisks = $state([]);
  let monitoredMounts = $state([]);
  let diskLoading = $state(true);
  let diskMsg = $state('');

  onMount(async () => {
    try {
      const [all, cfg] = await Promise.all([api.disks.all(), api.disks.config()]);
      allDisks = all?.disks || [];
      monitoredMounts = cfg?.monitored_mounts || ['/'];
    } catch (e) { console.error('Disk config:', e); }
    diskLoading = false;
  });

  function isDiskMonitored(mount) { return monitoredMounts.includes(mount); }

  async function toggleDisk(mount) {
    if (isDiskMonitored(mount)) {
      if (monitoredMounts.length <= 1) return; // Mindestens 1
      monitoredMounts = monitoredMounts.filter(m => m !== mount);
    } else {
      monitoredMounts = [...monitoredMounts, mount];
    }
    await api.disks.setConfig(monitoredMounts);
    diskMsg = 'Gespeichert!';
    setTimeout(() => diskMsg = '', 1500);
  }

  async function copyToken() {
    try { await navigator.clipboard.writeText(s.apiToken); copyMsg = 'Kopiert!'; }
    catch { copyMsg = 'Fehler'; }
    setTimeout(() => copyMsg = '', 2000);
  }
</script>

<div class="page">
  <div class="page-head">
    <h1>Einstellungen</h1>
    <p class="sub">System, API-Zugang, Dienste</p>
  </div>

  <!-- System Info -->
  <div class="section">
    <div class="section-title">Systeminformation</div>
    <div class="card">
      <div class="info-row"><span class="info-label">Version</span><span class="info-val">v{s.version}</span></div>
      <div class="info-row"><span class="info-label">Hardware-Proxy</span><span class="badge" class:badge-ok={s.hwProxy?.status==='ok'} class:badge-err={s.hwProxy?.status!=='ok'}>{s.hwProxy?.status==='ok'?`Online v${s.hwProxy.version}`:'Offline'}</span></div>
      <div class="info-row"><span class="info-label">WebSocket</span><span class="badge" class:badge-ok={s.connected} class:badge-err={!s.connected}>{s.connected?'Verbunden':'Getrennt'}</span></div>
      <div class="info-row"><span class="info-label">IP-Adresse</span><span class="info-val mono">{s.stats?.network?.ip || 'N/A'} ({s.stats?.network?.interface || '?'})</span></div>
      <div class="info-row"><span class="info-label">CPU</span><span class="info-val mono">{s.stats?.cpu?.cores || '?'} Kerne · ARM Cortex-A76</span></div>
      <div class="info-row"><span class="info-label">RAM</span><span class="info-val mono">{s.stats?.ram?.total_gb || '?'} GB</span></div>
      <div class="info-row last"><span class="info-label">Uptime</span><span class="info-val mono">{s.stats?.uptime?.formatted || '-'}</span></div>
    </div>
  </div>

  <!-- Laufwerk-Überwachung -->
  <div class="section">
    <div class="section-title">Laufwerk-Überwachung {#if diskMsg}<span class="saved-msg">{diskMsg}</span>{/if}</div>
    <div class="card">
      <p class="desc">Wähle welche Laufwerke auf dem Dashboard angezeigt werden. Mindestens 1 muss aktiv sein.</p>
      {#if diskLoading}
        <p class="desc">Lade Laufwerke...</p>
      {:else if allDisks.length === 0}
        <p class="desc">Keine Laufwerke erkannt.</p>
      {:else}
        <div class="disk-list">
          {#each allDisks as disk}
            <button class="disk-item" class:active={isDiskMonitored(disk.mount)} onclick={()=>toggleDisk(disk.mount)}>
              <span class="disk-check">{isDiskMonitored(disk.mount) ? '☑' : '☐'}</span>
              <div class="disk-info">
                <span class="disk-label">{disk.label}</span>
                <span class="disk-detail">{disk.mount} · {disk.device} · {disk.total_gb} GB · {disk.fstype}{disk.model ? ' · '+disk.model : ''}</span>
              </div>
              <span class="disk-pct">{disk.percent}%</span>
            </button>
          {/each}
        </div>
      {/if}
    </div>
  </div>

  <!-- API Token -->
  <div class="section">
    <div class="section-title">API-Zugang</div>
    <div class="card">
      <p class="desc">Alle API-Aufrufe erfordern den Token als <code>X-API-Token</code> Header.</p>
      <div class="token-box">{tokenVisible ? s.apiToken : 'xK9mQ2p_aB7cD4eF-gH1iJ3kL5nO8rS...'}</div>
      <div class="token-actions">
        <button class="btn" onclick={() => tokenVisible = !tokenVisible}>{tokenVisible ? '🙈 Verbergen' : '👁 Anzeigen'}</button>
        <button class="btn btn-accent" onclick={copyToken}>{copyMsg || '📋 Kopieren'}</button>
      </div>
    </div>
  </div>

  <!-- Links -->
  <div class="section">
    <div class="section-title">Dienste</div>
    <div class="grid-2">
      {#each [
        { icon: '📖', title: 'Swagger-UI', url: `:8071/docs`, href: `http://${host}:8071/docs` },
        { icon: '🌤️', title: 'WeatherCache', url: `:8060`, href: `http://${host}:8060` },
        { icon: '🔧', title: 'HW-Proxy Health', url: `:8072/health`, href: `http://${host}:8072/health` },
        { icon: '🖥️', title: 'Frontend', url: `:8070`, href: `http://${host}:8070` },
      ] as link}
        <a class="link-card" href={link.href} target="_blank">
          <span class="link-icon">{link.icon}</span>
          <div><div class="link-title">{link.title}</div><div class="link-url">{link.url}</div></div>
        </a>
      {/each}
    </div>
  </div>

  <!-- Hardware -->
  <div class="section">
    <div class="section-title">Hardware-Übersicht</div>
    <div class="card">
      <div class="hw-grid">
        <div class="hw-detail">
          <h3>⟳ Lüfter (PWM Fan)</h3>
          <p>Kernel-gesteuert · <code>/sys/class/thermal/cooling_device0</code></p>
          <p>4 Stufen: Aus · Leise · Mittel · Voll</p>
          <p>GPIO Pin 6 (On/Off) · Pin 5 (LED) · RPM via hwmon</p>
        </div>
        <div class="hw-detail">
          <h3>◈ WS2812B LEDs (4×)</h3>
          <p>SPI (<code>/dev/spidev0.0</code>) · neopixel_spi</p>
          <p>Pixel-Order: GRB · 6.4 MHz · 27 Effekte</p>
        </div>
        <div class="hw-detail">
          <h3>▣ OLED Display (SSD1306)</h3>
          <p>128×64 Pixel · I²C Bus (0x3C)</p>
          <p>Bibliothek: luma.oled · Rotierbare Screens</p>
        </div>
      </div>
    </div>
  </div>
</div>

<style>
  .page { display: flex; flex-direction: column; gap: 20px; }
  .page-head p { font-size: 12px; color: var(--text-muted); margin-top: 2px; }
  .section { display: flex; flex-direction: column; gap: 8px; }
  .mono { font-family: var(--mono); }
  .desc { font-size: 12px; color: var(--text-secondary); margin-bottom: 10px; }
  .desc code { background: rgba(255,255,255,0.06); padding: 1px 5px; border-radius: 3px; font-family: var(--mono); font-size: 11px; }

  .info-row { display: flex; justify-content: space-between; align-items: center; padding: 10px 0; border-bottom: 1px solid var(--border); }
  .info-row.last { border: none; }
  .info-label { font-size: 13px; color: var(--text-muted); }
  .info-val { font-size: 13px; }

  .token-box { font-family: var(--mono); font-size: 12px; background: rgba(255,255,255,0.04); padding: 10px 14px; border-radius: var(--radius-sm); border: 1px solid var(--border); margin-top: 4px; }
  .token-actions { display: flex; gap: 6px; margin-top: 8px; }

  .link-card { display: flex; align-items: center; gap: 10px; padding: 12px; border-radius: var(--radius-sm); border: 1px solid var(--border); background: rgba(255,255,255,0.02); text-decoration: none; color: var(--text-primary); transition: all var(--tr); }
  .link-card:hover { border-color: var(--border-accent); background: var(--accent-dim); }
  .link-icon { font-size: 22px; }
  .link-title { font-size: 12px; font-weight: 600; }
  .link-url { font-family: var(--mono); font-size: 10px; color: var(--text-muted); }

  .hw-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 16px; }
  .hw-detail h3 { font-size: 13px; margin-bottom: 6px; text-transform: none; letter-spacing: normal; }
  .hw-detail p { font-size: 12px; color: var(--text-muted); line-height: 1.5; margin-top: 2px; }
  .hw-detail code { background: rgba(255,255,255,0.06); padding: 1px 4px; border-radius: 3px; font-family: var(--mono); font-size: 10px; }

  .disk-list { display: flex; flex-direction: column; gap: 4px; }
  .disk-item { display: flex; align-items: center; gap: 10px; padding: 10px 12px; border-radius: 8px; border: 1px solid var(--border); background: transparent; color: var(--text-primary); cursor: pointer; text-align: left; font-family: inherit; transition: all .15s; width: 100%; }
  .disk-item:hover { border-color: var(--accent); background: rgba(99,102,241,0.04); }
  .disk-item.active { border-color: var(--accent); background: rgba(99,102,241,0.08); }
  .disk-check { font-size: 16px; min-width: 20px; }
  .disk-info { flex: 1; display: flex; flex-direction: column; gap: 2px; }
  .disk-label { font-size: 13px; font-weight: 600; }
  .disk-detail { font-size: 10px; color: var(--text-muted); font-family: var(--mono); }
  .disk-pct { font-family: var(--mono); font-size: 12px; color: var(--text-secondary); min-width: 36px; text-align: right; }
  .saved-msg { font-size: 11px; color: var(--accent); font-weight: 400; margin-left: 8px; }
</style>
