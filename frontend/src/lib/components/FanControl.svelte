<script>
  let { state: s } = $props();

  const mode = $derived(s.fan?.mode || 'auto');
  let simTemp = $state(null);
  const currentTemp = $derived(simTemp !== null ? simTemp : (s.fan?.current_temp || s.stats?.cpu?.temp || 0));
  const currentSpeed = $derived(s.fan?.current_speed || 0);
  const estimatedRpm = $derived(s.fan?.estimated_rpm || 0);
  const settings = $derived(s.fan?.settings || {});

  /* Schwellwerte — lokal getrackt für sofortige UI-Reaktion */
  let thresholdOn = $state(50);
  let thresholdOff = $state(45);

  /* Sync vom Backend wenn Settings sich ändern */
  $effect(() => {
    if (settings.threshold_on) thresholdOn = settings.threshold_on;
    if (settings.threshold_off) thresholdOff = settings.threshold_off;
  });

  /* Temperatur-Verlauf aus Stats-History */
  const tempHistory = $derived(s.stats?.history?.temp || []);

  /* Temperatur → RGB-Farbe
     25-30°C → Blau
     30-40°C → Gelb
     40-55°C → Orange
     55-60°C → Rot
     60°C+   → Rot (blinkend) */
  function tempToRgb(t) {
    if (t <= 25) return { r: 0, g: 60, b: 255 };
    if (t <= 30) {
      const f = (t - 25) / 5;
      return { r: Math.round(255 * f), g: Math.round(60 + 180 * f), b: Math.round(255 * (1 - f)) };
    }
    if (t <= 40) {
      const f = (t - 30) / 10;
      return { r: 255, g: Math.round(240 - 100 * f), b: 0 };
    }
    if (t <= 55) {
      const f = (t - 40) / 15;
      return { r: 255, g: Math.round(140 - 100 * f), b: 0 };
    }
    return { r: 255, g: Math.round(40 * Math.max(0, 1 - (t - 55) / 5)), b: 0 };
  }

  /* Blinken ab 60°C */
  const isBlinking = $derived(currentTemp >= 60);

  /* 4 LED-Farben berechnen — leicht versetzt wie echte Hardware-LEDs */
  const ledColors = $derived(() => {
    const base = currentTemp;
    return [0, 1, 2, 3].map(i => {
      const offset = (i - 1.5) * 2;
      const c = tempToRgb(base + offset);
      return `rgb(${c.r},${c.g},${c.b})`;
    });
  });
  const ledGlows = $derived(() => {
    const base = currentTemp;
    return [0, 1, 2, 3].map(i => {
      const offset = (i - 1.5) * 2;
      const c = tempToRgb(base + offset);
      return `rgba(${c.r},${c.g},${c.b},0.5)`;
    });
  });

  const tempRgb = $derived(tempToRgb(currentTemp));
  const tempColorStr = $derived(`rgb(${tempRgb.r},${tempRgb.g},${tempRgb.b})`);
  const tempGlow = $derived(`rgba(${tempRgb.r},${tempRgb.g},${tempRgb.b},0.15)`);
  const tempGlowStrong = $derived(`rgba(${tempRgb.r},${tempRgb.g},${tempRgb.b},0.3)`);

  function tempColor(t) {
    const c = tempToRgb(t);
    return `rgb(${c.r},${c.g},${c.b})`;
  }

  /* ─── Diagramm-Konfiguration ─── */
  const CHART = { w: 500, h: 140, pl: 40, pr: 50, pt: 14, pb: 20 };
  const CW = CHART.w - CHART.pl - CHART.pr;
  const CH = CHART.h - CHART.pt - CHART.pb;

  /* Temperatur → Y-Koordinate im Diagramm */
  const chartMin = $derived(Math.min(30, ...tempHistory) - 2);
  const chartMax = $derived(Math.max(60, ...tempHistory) + 2);
  const chartRange = $derived(chartMax - chartMin || 1);

  function cy(t) { return CHART.pt + CH - ((t - chartMin) / chartRange) * CH; }
  function cx(i, len) { return CHART.pl + (i / Math.max(1, len - 1)) * CW; }

  /* Y-Achsen-Ticks (alle 5°C, gerundet) */
  const yTicks = $derived(() => {
    const ticks = [];
    const start = Math.ceil(chartMin / 5) * 5;
    for (let t = start; t <= chartMax; t += 5) ticks.push(t);
    return ticks;
  });

  /* Geglätteter Pfad (Catmull-Rom → Cubic Bezier) */
  function smoothPath(arr) {
    if (!arr || arr.length < 2) return '';
    const pts = arr.map((v, i) => ({ x: cx(i, arr.length), y: cy(v) }));

    if (pts.length === 2) return `M${pts[0].x.toFixed(1)},${pts[0].y.toFixed(1)}L${pts[1].x.toFixed(1)},${pts[1].y.toFixed(1)}`;

    let d = `M${pts[0].x.toFixed(1)},${pts[0].y.toFixed(1)}`;
    for (let i = 0; i < pts.length - 1; i++) {
      const p0 = pts[Math.max(0, i - 1)];
      const p1 = pts[i];
      const p2 = pts[Math.min(pts.length - 1, i + 1)];
      const p3 = pts[Math.min(pts.length - 1, i + 2)];
      const t = 0.3;
      d += `C${(p1.x + (p2.x - p0.x) * t).toFixed(1)},${(p1.y + (p2.y - p0.y) * t).toFixed(1)},${(p2.x - (p3.x - p1.x) * t).toFixed(1)},${(p2.y - (p3.y - p1.y) * t).toFixed(1)},${p2.x.toFixed(1)},${p2.y.toFixed(1)}`;
    }
    return d;
  }

  /* Flächenpfad (geschlossener Bereich unter der Kurve) */
  function areaPath(arr) {
    const line = smoothPath(arr);
    if (!line) return '';
    const lastX = cx(arr.length - 1, arr.length);
    const firstX = cx(0, arr.length);
    const bottom = CHART.pt + CH;
    return `${line}L${lastX.toFixed(1)},${bottom}L${firstX.toFixed(1)},${bottom}Z`;
  }

  function updSetting(key, e) {
    s.setFanSettings({ [key]: parseFloat(e.target.value) });
  }

  /* Schwellwert-Slider — live lokale Aktualisierung, Backend bei Loslassen */
  function onThresholdOnInput(e) {
    const val = parseInt(e.target.value);
    thresholdOn = val;
    if (thresholdOff >= val - 2) thresholdOff = val - 3;
  }
  function onThresholdOffInput(e) {
    const val = parseInt(e.target.value);
    thresholdOff = val;
    if (thresholdOn <= val + 2) thresholdOn = val + 3;
  }
  function commitThresholds() {
    s.setFanSettings({ threshold_on: thresholdOn, threshold_off: thresholdOff });
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


      <!-- LED-Temperaturanzeige -->
      <div class="led-strip">
        {#each [0,1,2,3] as i}
          <div class="led-housing">
            <div class="led-glow" class:blink={isBlinking} style="background:radial-gradient(circle, {ledGlows()[i]}, transparent 70%)"></div>
            <div class="led-pixel" class:blink={isBlinking} style="background:{ledColors()[i]};box-shadow:0 0 8px {ledGlows()[i]}, 0 0 20px {ledGlows()[i]}"></div>
          </div>
        {/each}
        <span class="led-title">LEDs</span>
        <span class="led-label" style="color:{tempColorStr}">{currentTemp.toFixed(1)}°C</span>
      </div>

      <!-- Temperatur-Diagramm -->
      <div class="chart" style="--temp-color:{tempColorStr};--temp-glow:{tempGlow}">
        <svg class="chart-svg" viewBox="0 0 {CHART.w} {CHART.h}">
          <defs>
            <linearGradient id="area-grad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stop-color={tempColorStr} stop-opacity="0.15"/>
              <stop offset="100%" stop-color={tempColorStr} stop-opacity="0.02"/>
            </linearGradient>
          </defs>

          <!-- Gitternetzlinien und Y-Achsenbeschriftung -->
          {#each yTicks() as t}
            <line x1={CHART.pl} y1={cy(t)} x2={CHART.pl + CW} y2={cy(t)} stroke="rgba(255,255,255,0.04)" stroke-width="0.5"/>
            <text x={CHART.pl - 6} y={cy(t) + 3.5} text-anchor="end" class="chart-label">{t}°</text>
          {/each}

          <!-- Schwellwert-Linien im Automatik-Modus -->
          {#if mode === 'auto'}
            <line x1={CHART.pl} y1={cy(thresholdOn)} x2={CHART.pl + CW} y2={cy(thresholdOn)} stroke="var(--red)" stroke-width="0.8" stroke-dasharray="4 3" opacity="0.5"/>
            <text x={CHART.pl + CW + 6} y={cy(thresholdOn) + 3.5} class="chart-label-on">{thresholdOn}° Ein</text>
            <line x1={CHART.pl} y1={cy(thresholdOff)} x2={CHART.pl + CW} y2={cy(thresholdOff)} stroke="var(--green)" stroke-width="0.8" stroke-dasharray="4 3" opacity="0.5"/>
            <text x={CHART.pl + CW + 6} y={cy(thresholdOff) + 3.5} class="chart-label-off">{thresholdOff}° Aus</text>
          {/if}

          <!-- Y-Achse und Grundlinie -->
          <line x1={CHART.pl} y1={CHART.pt} x2={CHART.pl} y2={CHART.pt + CH} stroke="rgba(255,255,255,0.08)" stroke-width="0.5"/>
          <line x1={CHART.pl} y1={CHART.pt + CH} x2={CHART.pl + CW} y2={CHART.pt + CH} stroke="rgba(255,255,255,0.08)" stroke-width="0.5"/>

          <!-- Daten -->
          {#if tempHistory.length > 2}
            <path d={areaPath(tempHistory)} fill="url(#area-grad)"/>
            <path d={smoothPath(tempHistory)} fill="none" stroke={tempColorStr} stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <!-- Aktueller Punkt (letzter Wert) -->
            <circle cx={cx(tempHistory.length - 1, tempHistory.length)} cy={cy(tempHistory[tempHistory.length - 1])} r="4" fill={tempColorStr} stroke="var(--bg-card)" stroke-width="2"/>
            <!-- Aktueller Wert als Label -->
            <text x={cx(tempHistory.length - 1, tempHistory.length)} y={cy(tempHistory[tempHistory.length - 1]) - 10} text-anchor="end" class="chart-value">{tempHistory[tempHistory.length - 1].toFixed(1)}°C</text>
          {:else}
            <text x={CHART.pl + CW / 2} y={CHART.pt + CH / 2} text-anchor="middle" class="chart-empty">Warte auf Messdaten…</text>
          {/if}
        </svg>
      </div>
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
            <input type="range" min="35" max="75" step="1" value={thresholdOn} oninput={onThresholdOnInput} onchange={commitThresholds} />
          </div>
          <div class="threshold-group">
            <div class="threshold-head">
              <span><i class="fa-solid fa-arrow-down" style="color:var(--green)"></i> Ausschalten bei</span>
              <span class="threshold-val">{thresholdOff}°C</span>
            </div>
            <input type="range" min="30" max="70" step="1" value={thresholdOff} oninput={onThresholdOffInput} onchange={commitThresholds} />
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

      <!-- Simulation -->
      <div class="side-section">
        <div class="side-title"><i class="fa-solid fa-flask"></i> Simulation</div>
        <label class="sim-toggle">
          <input type="checkbox" checked={simTemp !== null} onchange={(e) => { simTemp = e.target.checked ? 40 : null; }}>
          <span>Temperatur simulieren</span>
        </label>
        {#if simTemp !== null}
          <div class="sim-slider">
            <input type="range" min="20" max="85" step="0.5" value={simTemp} oninput={(e) => simTemp = parseFloat(e.target.value)}>
            <span class="sim-val" style="color:{tempColorStr}">{simTemp.toFixed(1)}°C</span>
          </div>
        {/if}
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


  /* ─── LED-Leiste ─── */
  .led-strip {
    display: flex; align-items: center; justify-content: center;
    gap: 16px; padding: 12px 20px; flex-shrink: 0;
    background: linear-gradient(180deg, #080808, #111);
    border-radius: var(--radius-sm); border: 1px solid #222;
  }
  .led-housing {
    position: relative; width: 32px; height: 32px;
    display: flex; align-items: center; justify-content: center;
  }
  .led-glow {
    position: absolute; width: 60px; height: 60px;
    border-radius: 50%; top: 50%; left: 50%;
    transform: translate(-50%, -50%); pointer-events: none;
  }
  .led-pixel {
    width: 20px; height: 20px; border-radius: 4px;
    border: 1px solid rgba(255,255,255,0.15);
    position: relative; z-index: 1;
    transition: background 1s ease, box-shadow 1s ease;
  }
  .led-title {
    font: 600 var(--fs-xs) var(--font);
    color: var(--text-muted); text-transform: uppercase;
    letter-spacing: 0.08em; margin-left: 12px;
  }
  .led-label {
    font: 700 var(--fs-base) var(--mono);
    margin-left: 4px;
    transition: color 1s;
  }
  .led-pixel.blink, .led-glow.blink {
    animation: ledBlink 0.6s ease-in-out infinite alternate;
  }
  @keyframes ledBlink {
    0% { opacity: 1; }
    100% { opacity: 0.15; }
  }

  /* ─── Diagramm ─── */
  .chart {
    flex: 1; min-height: 0;
    background: var(--bg-deep);
    border-radius: var(--radius-sm);
    padding: 8px 4px;
  }
  .chart-svg { width: 100%; height: 100%; display: block; }
  .chart-label { font: 10px var(--mono); fill: var(--text-muted); }
  .chart-label-on { font: 600 9px var(--mono); fill: var(--red); }
  .chart-label-off { font: 600 9px var(--mono); fill: var(--green); }
  .chart-value { font: 700 11px var(--mono); fill: var(--text-primary); }
  .chart-empty { font: 500 12px var(--font); fill: var(--text-muted); }

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

  /* ─── Simulation ─── */
  .sim-toggle {
    display: flex; align-items: center; gap: 8px;
    font: 500 var(--fs-sm) var(--font); color: var(--text-secondary);
    cursor: pointer; margin-bottom: 10px;
  }
  .sim-slider { display: flex; align-items: center; gap: 10px; }
  .sim-slider input { flex: 1; }
  .sim-val { font: 700 var(--fs-base) var(--mono); min-width: 64px; text-align: right; }

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
