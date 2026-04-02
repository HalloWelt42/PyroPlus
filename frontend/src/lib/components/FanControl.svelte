<script>
  let { state: s } = $props();

  const mode = $derived(s.fan?.mode || 'auto');
  const currentTemp = $derived(s.fan?.current_temp || s.stats?.cpu?.temp || 0);
  const currentSpeed = $derived(s.fan?.current_speed || 0);
  const estimatedRpm = $derived(s.fan?.estimated_rpm || 0);
  const settings = $derived(s.fan?.settings || {});

  /* Schwellwerte aus den Fan-Settings ableiten */
  const thresholdOn = $derived(settings.threshold_on || 50);
  const thresholdOff = $derived(settings.threshold_off || 45);

  /* Temperatur-Verlauf aus Stats-History */
  const tempHistory = $derived(s.stats?.history?.temp || []);

  /* Temperatur → RGB-Farbe (fließender Verlauf) */
  function tempToRgb(t) {
    const ratio = Math.max(0, Math.min(1, (t - 30) / 50));
    let r, g, b;
    if (ratio < 0.33) {
      const f = ratio / 0.33;
      r = 0; g = Math.round(200 + 55 * (1 - f)); b = Math.round(255 * (1 - f));
    } else if (ratio < 0.66) {
      const f = (ratio - 0.33) / 0.33;
      r = Math.round(255 * f); g = Math.round(200 * (1 - f * 0.3)); b = 0;
    } else {
      const f = (ratio - 0.66) / 0.34;
      r = 255; g = Math.round(140 * (1 - f)); b = Math.round(40 * f);
    }
    return { r, g, b };
  }

  const tempRgb = $derived(tempToRgb(currentTemp));
  const tempColorStr = $derived(`rgb(${tempRgb.r},${tempRgb.g},${tempRgb.b})`);
  const tempGlow = $derived(`rgba(${tempRgb.r},${tempRgb.g},${tempRgb.b},0.15)`);
  const tempGlowStrong = $derived(`rgba(${tempRgb.r},${tempRgb.g},${tempRgb.b},0.3)`);

  function tempColor(t) {
    const c = tempToRgb(t);
    return `rgb(${c.r},${c.g},${c.b})`;
  }

  /* Temperatur-Sparkline (geglättete Kurve via Catmull-Rom → Cubic Bezier) */
  function sparkPath(arr, w, h) {
    if (!arr || arr.length < 2) return '';
    const min = Math.min(...arr) - 3, max = Math.max(...arr) + 3;
    const range = max - min || 1;
    const step = w / (arr.length - 1);
    const pts = arr.map((v, i) => ({ x: i * step, y: h - ((v - min) / range) * h * 0.9 - h * 0.05 }));

    if (pts.length === 2) return `M${pts[0].x},${pts[0].y}L${pts[1].x},${pts[1].y}`;

    let d = `M${pts[0].x.toFixed(1)},${pts[0].y.toFixed(1)}`;
    for (let i = 0; i < pts.length - 1; i++) {
      const p0 = pts[Math.max(0, i - 1)];
      const p1 = pts[i];
      const p2 = pts[Math.min(pts.length - 1, i + 1)];
      const p3 = pts[Math.min(pts.length - 1, i + 2)];
      const tension = 0.3;
      const cp1x = p1.x + (p2.x - p0.x) * tension;
      const cp1y = p1.y + (p2.y - p0.y) * tension;
      const cp2x = p2.x - (p3.x - p1.x) * tension;
      const cp2y = p2.y - (p3.y - p1.y) * tension;
      d += `C${cp1x.toFixed(1)},${cp1y.toFixed(1)},${cp2x.toFixed(1)},${cp2y.toFixed(1)},${p2.x.toFixed(1)},${p2.y.toFixed(1)}`;
    }
    return d;
  }

  function updSetting(key, e) {
    s.setFanSettings({ [key]: parseFloat(e.target.value) });
  }

  /* Schwellwert-Slider */
  function setThresholdOn(e) {
    const val = parseInt(e.target.value);
    s.setFanSettings({ threshold_on: val, threshold_off: Math.min(thresholdOff, val - 3) });
  }
  function setThresholdOff(e) {
    const val = parseInt(e.target.value);
    s.setFanSettings({ threshold_off: val, threshold_on: Math.max(thresholdOn, val + 3) });
  }
</script>

<div class="layout">
  <!-- ═══ KOPFZEILE ═══ -->
  <header class="topbar">
    <i class="fa-solid fa-fan topbar-icon" class:spinning={currentSpeed > 0}></i>
    <h1>Lüftersteuerung</h1>
  </header>

  <!-- ═══ INHALT ═══ -->
  <div class="content">
    <!-- ─── Hauptbereich ─── -->
    <div class="panel panel-main">
      <!-- Live-Status -->
      <div class="status-bar">
        <div class="status-item">
          <span class="status-label">Temperatur</span>
          <span class="status-value" style="color:{tempColor(currentTemp)}">{currentTemp.toFixed(1)}°C</span>
        </div>
        <div class="status-divider"></div>
        <div class="status-item">
          <span class="status-label">Lüfter</span>
          <span class="status-value" style="color:{currentSpeed > 0 ? 'var(--green)' : 'var(--text-muted)'}">
            {currentSpeed > 0 ? 'Läuft' : 'Aus'}
          </span>
        </div>
        {#if estimatedRpm > 0}
          <div class="status-divider"></div>
          <div class="status-item">
            <span class="status-label">Drehzahl</span>
            <span class="status-value">{estimatedRpm} RPM</span>
          </div>
        {/if}
      </div>

      <!-- Temperatur-Visualisierung -->
      <div class="temp-display" style="--temp-color:{tempColorStr};--temp-glow:{tempGlow};--temp-glow-strong:{tempGlowStrong}">
        <div class="temp-orb">
          <div class="orb-ring"></div>
          <div class="orb-core">
            <span class="temp-big">{currentTemp.toFixed(1)}</span>
            <span class="temp-unit">°C</span>
          </div>
        </div>
        <div class="temp-right">
          <div class="temp-gauge">
            <div class="gauge-track">
              <div class="gauge-fill" style="width:{Math.min(100, Math.max(0, (currentTemp - 25) / 55 * 100))}%; background:linear-gradient(90deg, var(--green), {tempColorStr})"></div>
              {#if mode === 'auto'}
                <div class="gauge-marker marker-off" style="left:{Math.max(0, (thresholdOff - 25) / 55 * 100)}%" title="Ausschalten bei {thresholdOff}°C"></div>
                <div class="gauge-marker marker-on" style="left:{Math.max(0, (thresholdOn - 25) / 55 * 100)}%" title="Einschalten bei {thresholdOn}°C"></div>
              {/if}
            </div>
            <div class="gauge-labels">
              <span>25°C</span>
              <span>80°C</span>
            </div>
          </div>
          <div class="temp-meta">
            <span style="color:var(--text-muted)">Minimum {s.stats?.cpu?.temp_min || '—'}°C</span>
            <span style="color:var(--text-muted)">Maximum {s.stats?.cpu?.temp_max || '—'}°C</span>
          </div>
        </div>
      </div>

      <!-- Temperatur-Verlauf -->
      {#if tempHistory.length > 2}
        <div class="history" style="--temp-color:{tempColorStr};--temp-glow:{tempGlow}">
          <div class="history-label">Temperaturverlauf</div>
          <svg class="sparkline" viewBox="0 0 400 80" preserveAspectRatio="none">
            <defs>
              <linearGradient id="spark-grad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stop-color={tempColorStr} stop-opacity="0.2"/>
                <stop offset="100%" stop-color={tempColorStr} stop-opacity="0"/>
              </linearGradient>
            </defs>
            <path d="{sparkPath(tempHistory, 400, 80)} L400,80 L0,80 Z" fill="url(#spark-grad)"/>
            <path d={sparkPath(tempHistory, 400, 80)} fill="none" stroke={tempColorStr} stroke-width="2.5" stroke-linecap="round" filter="drop-shadow(0 0 4px {tempGlow})"/>
          </svg>
        </div>
      {/if}
    </div>

    <!-- ─── Seitenleiste ─── -->
    <div class="panel panel-side">
      <!-- Automatik-Einstellungen -->
      {#if mode === 'auto'}
        <div class="side-section">
          <div class="side-title"><i class="fa-solid fa-temperature-half"></i> Temperaturschwelle</div>
          <div class="threshold-group">
            <div class="threshold-head">
              <span><i class="fa-solid fa-arrow-up" style="color:var(--red)"></i> Einschalten bei</span>
              <span class="threshold-val">{thresholdOn}°C</span>
            </div>
            <input type="range" min="35" max="75" step="1" value={thresholdOn} oninput={setThresholdOn} />
          </div>
          <div class="threshold-group">
            <div class="threshold-head">
              <span><i class="fa-solid fa-arrow-down" style="color:var(--green)"></i> Ausschalten bei</span>
              <span class="threshold-val">{thresholdOff}°C</span>
            </div>
            <input type="range" min="30" max="70" step="1" value={thresholdOff} oninput={setThresholdOff} />
          </div>
          <div class="threshold-info">
            Hysterese: {thresholdOn - thresholdOff}°C
          </div>
        </div>
      {/if}

      <!-- Hardware-Info -->
      <div class="side-section">
        <div class="side-title"><i class="fa-solid fa-microchip"></i> Hardware</div>
        <div class="hw-rows">
          <div class="hw-row"><span class="hw-key">Typ</span><span>GPIO Digital (An/Aus)</span></div>
          <div class="hw-row"><span class="hw-key">Anschluss</span><span>GPIO Pin 6</span></div>
          <div class="hw-row">
            <span class="hw-key">Status</span>
            <span class:hw-ok={s.fan?.available} class:hw-err={!s.fan?.available}>
              {s.fan?.available ? 'Verfügbar' : 'Nicht verfügbar'}
            </span>
          </div>
        </div>
      </div>

      <!-- Betriebsmodus -->
      <div class="side-section side-mode">
        <div class="side-title"><i class="fa-solid fa-power-off"></i> Betriebsmodus</div>
        <div class="mode-buttons">
          <button class="mode-btn" class:active={mode==='auto'} onclick={() => s.setFanMode('auto')}>
            <i class="fa-solid fa-wand-magic-sparkles"></i><span>Automatik</span>
          </button>
          <button class="mode-btn" class:active={mode==='manual'} onclick={() => s.setFanMode('manual')}>
            <i class="fa-solid fa-toggle-on"></i><span>Dauerbetrieb</span>
          </button>
          <button class="mode-btn" class:active={mode==='off'} onclick={() => s.setFanMode('off')}>
            <i class="fa-solid fa-power-off"></i><span>Aus</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</div>

<style>
  .layout { display: flex; flex-direction: column; height: 100%; gap: 12px; }

  /* ─── Kopfzeile ─── */
  .topbar { display: flex; align-items: center; gap: 10px; flex-shrink: 0; }
  .topbar h1 { font-size: var(--fs-xl); }
  .topbar-icon { color: var(--accent); font-size: var(--fs-lg); transition: transform 300ms; }
  .topbar-icon.spinning { animation: spin 1.5s linear infinite; }
  @keyframes spin { to { transform: rotate(360deg); } }

  /* ─── Inhalt ─── */
  .content { display: grid; grid-template-columns: 1fr 280px; gap: 12px; flex: 1; min-height: 0; }
  .panel { background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--radius); overflow: hidden; }
  .panel-main { display: flex; flex-direction: column; padding: 20px; gap: 20px; }
  .panel-side { display: flex; flex-direction: column; overflow-y: auto; }

  /* ─── Status-Leiste ─── */
  .status-bar {
    display: flex; align-items: center; gap: 16px;
    padding: 10px 18px; border-radius: var(--radius-sm);
    background: var(--bg-elevated); border: 1px solid var(--border);
    flex-shrink: 0;
  }
  .status-item { display: flex; flex-direction: column; align-items: center; }
  .status-label { font: 500 var(--fs-xs) var(--font); color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; }
  .status-value { font: 700 var(--fs-base) var(--mono); }
  .status-divider { width: 1px; height: 32px; background: var(--border); }

  /* ─── Temperatur-Anzeige ─── */
  .temp-display { display: flex; align-items: center; gap: 28px; flex-shrink: 0; }

  .temp-orb {
    position: relative; width: 140px; height: 140px; flex-shrink: 0;
    display: flex; align-items: center; justify-content: center;
  }
  .orb-ring {
    position: absolute; inset: 0;
    border-radius: 50%;
    border: 3px solid var(--temp-color);
    box-shadow: 0 0 20px var(--temp-glow), 0 0 50px var(--temp-glow), inset 0 0 20px var(--temp-glow);
    transition: border-color 1s, box-shadow 1s;
  }
  .orb-core {
    display: flex; flex-direction: column; align-items: center;
    position: relative; z-index: 1;
  }
  .temp-big { font: 800 42px var(--mono); color: var(--temp-color); line-height: 1; transition: color 1s; }
  .temp-unit { font: 500 var(--fs-sm) var(--font); color: var(--text-muted); margin-top: 2px; }

  .temp-right { flex: 1; display: flex; flex-direction: column; gap: 10px; }
  .temp-gauge { }
  .gauge-track {
    height: 10px; background: rgba(255,255,255,0.06);
    border-radius: 5px; overflow: visible; position: relative;
  }
  .gauge-fill {
    height: 100%; border-radius: 5px;
    transition: width 1s ease;
    box-shadow: 0 0 8px var(--temp-glow);
  }
  .gauge-marker {
    position: absolute; top: -5px; width: 3px; height: 20px;
    border-radius: 2px; transform: translateX(-1px);
  }
  .marker-on { background: var(--red); }
  .marker-off { background: var(--green); }
  .gauge-labels {
    display: flex; justify-content: space-between;
    font: 500 var(--fs-xs) var(--mono); color: var(--text-muted);
    margin-top: 6px;
  }
  .temp-meta {
    display: flex; justify-content: space-between;
    font: 500 var(--fs-xs) var(--font);
  }

  /* ─── Verlauf ─── */
  .history { flex: 1; min-height: 0; display: flex; flex-direction: column; }
  .history-label { font: 500 var(--fs-xs) var(--font); color: var(--text-muted); margin-bottom: 6px; }
  .sparkline { width: 100%; flex: 1; display: block; }

  /* ─── Seitenleiste ─── */
  .side-section { padding: 16px 18px; border-bottom: 1px solid var(--border); }
  .side-section:last-child { border-bottom: none; }
  .side-title {
    font: 600 var(--fs-sm) var(--font); color: var(--text-secondary);
    margin-bottom: 14px; display: flex; align-items: center; gap: 8px;
  }
  .side-title i { color: var(--accent); font-size: var(--fs-sm); }

  /* ─── Schwellwerte ─── */
  .threshold-group { margin-bottom: 14px; }
  .threshold-group:last-of-type { margin-bottom: 8px; }
  .threshold-head {
    display: flex; justify-content: space-between; align-items: center;
    font: 500 var(--fs-sm) var(--font); color: var(--text-secondary);
    margin-bottom: 8px;
  }
  .threshold-head i { font-size: var(--fs-xs); }
  .threshold-val {
    font: 600 var(--fs-sm) var(--mono); color: var(--text-primary);
    background: var(--bg-deep); padding: 3px 10px; border-radius: var(--radius-sm);
  }
  .threshold-info {
    font: 500 var(--fs-xs) var(--mono); color: var(--text-muted);
    text-align: center; padding: 4px; border-radius: var(--radius-sm);
    background: var(--bg-deep);
  }

  /* ─── Hardware ─── */
  .hw-rows { display: flex; flex-direction: column; gap: 8px; }
  .hw-row {
    display: flex; justify-content: space-between;
    font: 500 var(--fs-sm) var(--font); color: var(--text-secondary);
    padding: 3px 0;
  }
  .hw-key { color: var(--text-muted); }
  .hw-ok { color: var(--green); }
  .hw-err { color: var(--red); }

  /* ─── Betriebsmodus ─── */
  .side-mode { margin-top: auto; }
  .mode-buttons { display: flex; flex-direction: column; gap: 6px; }
  .mode-btn {
    height: var(--h-btn); border-radius: var(--radius-sm);
    border: 1px solid var(--border); background: var(--bg-elevated);
    color: var(--text-muted); font: 500 var(--fs-sm) var(--font);
    cursor: pointer; transition: all 150ms;
    display: flex; align-items: center; justify-content: center; gap: 8px;
    width: 100%;
  }
  .mode-btn:hover { border-color: var(--text-muted); color: var(--text-secondary); }
  .mode-btn.active { background: var(--accent-dim); border-color: var(--accent); color: var(--accent); }

  /* ─── Responsive ─── */
  @media (max-width: 900px) {
    .content { grid-template-columns: 1fr; }
    .temp-big { font-size: 48px; }
  }
  @media (max-width: 600px) {
    .temp-display { flex-direction: column; align-items: flex-start; }
    .temp-big { font-size: 40px; }
  }
</style>
