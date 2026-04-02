<script>
  import { api } from '../api/client.js';
  let { state: s } = $props();

  /* ═══ STATE ═══ */
  const mode = $derived(s.fan?.mode || 'auto');
  const profile = $derived(s.fan?.profile || 'balanced');
  const curve = $derived(s.fan?.curve || []);
  const profiles = $derived(s.fan?.profiles || ['silent','balanced','performance','night','custom']);
  const currentTemp = $derived(simTemp !== null ? simTemp : (s.fan?.current_temp || s.stats?.cpu?.temp || 0));
  const currentDuty = $derived(s.fan?.current_duty || 0);
  const currentRpm = $derived(s.fan?.current_rpm || 0);
  const hysteresis = $derived(s.fan?.hysteresis || 3);
  const safetyTemp = $derived(s.fan?.safety_temp || 80);
  const tempHistory = $derived(s.stats?.history?.temp || []);

  /* Simulation */
  let simTemp = $state(null);
  let _simTimer = 0;
  function simTempLive(val) {
    simTemp = val;
    clearTimeout(_simTimer);
    _simTimer = setTimeout(() => api.simulate.temp(val), 200);
  }

  /* ═══ TEMPERATUR → FARBE ═══ */
  function tempToRgb(t) {
    if (t <= 25) return { r: 0, g: 60, b: 255 };
    if (t <= 30) { const f = (t - 25) / 5; return { r: Math.round(255 * f), g: Math.round(60 + 180 * f), b: Math.round(255 * (1 - f)) }; }
    if (t <= 40) { const f = (t - 30) / 10; return { r: 255, g: Math.round(240 - 100 * f), b: 0 }; }
    if (t <= 55) { const f = (t - 40) / 15; return { r: 255, g: Math.round(140 - 100 * f), b: 0 }; }
    return { r: 255, g: Math.round(40 * Math.max(0, 1 - (t - 55) / 5)), b: 0 };
  }
  const tempRgb = $derived(tempToRgb(currentTemp));
  const tempColorStr = $derived(`rgb(${tempRgb.r},${tempRgb.g},${tempRgb.b})`);
  const tempGlow = $derived(`rgba(${tempRgb.r},${tempRgb.g},${tempRgb.b},0.15)`);
  const isBlinking = $derived(currentTemp >= 60);

  /* LED-Farben mit Versatz */
  const ledColors = $derived(() => [0,1,2,3].map(i => { const c = tempToRgb(currentTemp + (i - 1.5) * 2); return `rgb(${c.r},${c.g},${c.b})`; }));
  const ledGlows = $derived(() => [0,1,2,3].map(i => { const c = tempToRgb(currentTemp + (i - 1.5) * 2); return `rgba(${c.r},${c.g},${c.b},0.5)`; }));

  /* ═══ DIAGRAMM ═══ */
  const CHART = { w: 500, h: 210, pl: 40, pr: 10, pt: 14, pb: 28 };
  const CW = CHART.w - CHART.pl - CHART.pr;
  const CH = CHART.h - CHART.pt - CHART.pb;
  const chartMin = $derived(Math.min(30, ...tempHistory) - 2);
  const chartMax = $derived(Math.max(60, ...tempHistory) + 2);
  const chartRange = $derived(chartMax - chartMin || 1);

  function cy(t) { return CHART.pt + CH - ((t - chartMin) / chartRange) * CH; }
  function chx(i, len) { return CHART.pl + (i / Math.max(1, len - 1)) * CW; }

  const yTicks = $derived(() => {
    const ticks = [];
    const start = Math.ceil(chartMin / 5) * 5;
    for (let t = start; t <= chartMax; t += 5) ticks.push(t);
    return ticks;
  });

  function smoothPath(arr) {
    if (!arr || arr.length < 2) return '';
    const pts = arr.map((v, i) => ({ x: chx(i, arr.length), y: cy(v) }));
    let d = `M${pts[0].x.toFixed(1)},${pts[0].y.toFixed(1)}`;
    for (let i = 0; i < pts.length - 1; i++) {
      const p0 = pts[Math.max(0, i - 1)], p1 = pts[i];
      const p2 = pts[Math.min(pts.length - 1, i + 1)], p3 = pts[Math.min(pts.length - 1, i + 2)];
      const t = 0.3;
      d += `C${(p1.x+(p2.x-p0.x)*t).toFixed(1)},${(p1.y+(p2.y-p0.y)*t).toFixed(1)},${(p2.x-(p3.x-p1.x)*t).toFixed(1)},${(p2.y-(p3.y-p1.y)*t).toFixed(1)},${p2.x.toFixed(1)},${p2.y.toFixed(1)}`;
    }
    return d;
  }
  function areaPath(arr) {
    const line = smoothPath(arr);
    if (!line) return '';
    return `${line}L${chx(arr.length-1,arr.length).toFixed(1)},${(CHART.pt+CH)}L${chx(0,arr.length).toFixed(1)},${(CHART.pt+CH)}Z`;
  }

  /* ═══ KURVEN-EDITOR ═══ */
  const CURVE = { w: 400, h: 200, pl: 40, pr: 15, pt: 15, pb: 28 };
  const KW = CURVE.w - CURVE.pl - CURVE.pr;
  const KH = CURVE.h - CURVE.pt - CURVE.pb;
  const TMIN = 25, TMAX = 80;

  function ktx(t) { return CURVE.pl + ((t - TMIN) / (TMAX - TMIN)) * KW; }
  function ksy(sp) { return CURVE.pt + KH - (sp / 100) * KH; }
  function kxt(x) { return Math.round(Math.max(TMIN, Math.min(TMAX, TMIN + ((x - CURVE.pl) / KW) * (TMAX - TMIN)))); }
  function kys(y) { return Math.round(Math.max(0, Math.min(100, ((CURVE.pt + KH - y) / KH) * 100))); }

  function curveLine(pts) {
    if (!pts.length) return '';
    const sorted = [...pts].sort((a, b) => a.temp - b.temp);
    return sorted.map((p, i) => `${i ? 'L' : 'M'}${ktx(p.temp).toFixed(1)},${ksy(p.speed).toFixed(1)}`).join(' ');
  }
  function curveFill(pts) {
    if (!pts.length) return '';
    const sorted = [...pts].sort((a, b) => a.temp - b.temp);
    return `${curveLine(pts)}L${ktx(sorted[sorted.length-1].temp).toFixed(1)},${ksy(0)}L${ktx(sorted[0].temp).toFixed(1)},${ksy(0)}Z`;
  }

  let dragging = $state(-1);
  let curveEl = $state(null);

  function startDrag(i, e) {
    if (profile !== 'custom') { s.toast('Wechsle zu Benutzerdefiniert um Punkte zu bewegen', 'info'); return; }
    e.preventDefault(); dragging = i;
    window.addEventListener('mousemove', onDrag);
    window.addEventListener('mouseup', stopDrag);
    window.addEventListener('touchmove', onDrag, { passive: false });
    window.addEventListener('touchend', stopDrag);
  }
  function onDrag(e) {
    if (dragging < 0 || !curveEl) return;
    e.preventDefault();
    const pt = curveEl.createSVGPoint();
    pt.x = e.touches ? e.touches[0].clientX : e.clientX;
    pt.y = e.touches ? e.touches[0].clientY : e.clientY;
    const svgPt = pt.matrixTransform(curveEl.getScreenCTM().inverse());
    const pts = [...curve]; pts[dragging] = { temp: kxt(svgPt.x), speed: kys(svgPt.y) };
    s.updateFan({ curve: pts });
  }
  function stopDrag() {
    if (dragging >= 0) { s.setFanCurve(curve); dragging = -1; }
    window.removeEventListener('mousemove', onDrag);
    window.removeEventListener('mouseup', stopDrag);
    window.removeEventListener('touchmove', onDrag);
    window.removeEventListener('touchend', stopDrag);
  }

  async function selectProfile(p) { await s.setFanProfile(p); }

  const profIcons = { silent: 'fa-volume-xmark', balanced: 'fa-scale-balanced', performance: 'fa-rocket', night: 'fa-moon', custom: 'fa-sliders' };
  const profLabels = { silent: 'Leise', balanced: 'Ausgewogen', performance: 'Leistung', night: 'Nacht', custom: 'Benutzerdefiniert' };

  /* Fan-Animation: Drehgeschwindigkeit proportional zu RPM */
  const fanSpinDuration = $derived(currentRpm > 0 ? Math.max(0.1, 60 / currentRpm) + 's' : '0s');
</script>

<div class="layout">
  <header class="topbar">
    <i class="fa-solid fa-fan topbar-icon" style="animation-duration:{fanSpinDuration}" class:spinning={currentRpm > 0}></i>
    <h1>Lüftersteuerung</h1>
  </header>

  <div class="content">
    <!-- ═══ LINKS: Temperatur ═══ -->
    <div class="panel panel-left">
      <div class="panel-title">Temperatur</div>

      <!-- LED-Leiste -->
      <div class="led-strip">
        {#each [0,1,2,3] as i}
          <div class="led-housing">
            <div class="led-glow" class:blink={isBlinking} style="background:radial-gradient(circle, {ledGlows()[i]}, transparent 70%)"></div>
            <div class="led-pixel" class:blink={isBlinking} style="background:{ledColors()[i]};box-shadow:0 0 10px {ledGlows()[i]}, 0 0 25px {ledGlows()[i]}"></div>
          </div>
        {/each}
      </div>

      <!-- Große Temperaturanzeige -->
      <div class="temp-hero" style="color:{tempColorStr}">
        {currentTemp.toFixed(1)}<span class="temp-unit">°C</span>
      </div>

      <!-- Status-Zeile -->
      <div class="status-row">
        <div class="status-chip">
          <i class="fa-solid fa-gauge"></i>
          <span>{currentDuty.toFixed(0)}% PWM</span>
        </div>
        <div class="status-chip">
          <i class="fa-solid fa-fan" style="animation-duration:{fanSpinDuration}" class:spinning={currentRpm > 0}></i>
          <span>{currentRpm} RPM</span>
        </div>
      </div>

      <!-- Temperatur-Diagramm -->
      <div class="chart">
        <svg class="chart-svg" viewBox="0 0 {CHART.w} {CHART.h}">
          <defs>
            <linearGradient id="area-grad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stop-color={tempColorStr} stop-opacity="0.15"/>
              <stop offset="100%" stop-color={tempColorStr} stop-opacity="0.02"/>
            </linearGradient>
          </defs>
          {#each yTicks() as t}
            <line x1={CHART.pl} y1={cy(t)} x2={CHART.pl + CW} y2={cy(t)} stroke="rgba(255,255,255,0.04)" stroke-width="0.5"/>
            <text x={CHART.pl - 6} y={cy(t) + 3.5} text-anchor="end" class="chart-label">{t}°</text>
          {/each}
          <line x1={CHART.pl} y1={CHART.pt} x2={CHART.pl} y2={CHART.pt + CH} stroke="rgba(255,255,255,0.08)" stroke-width="0.5"/>
          <line x1={CHART.pl} y1={CHART.pt + CH} x2={CHART.pl + CW} y2={CHART.pt + CH} stroke="rgba(255,255,255,0.08)" stroke-width="0.5"/>
          {#if tempHistory.length > 2}
            {#each [60, 30, 0] as ago}
              {@const idx = Math.max(0, tempHistory.length - 1 - ago)}
              <text x={chx(idx, tempHistory.length)} y={CHART.pt + CH + 16} text-anchor="middle" class="chart-label">
                {ago === 0 ? 'jetzt' : `-${ago}s`}
              </text>
            {/each}
            <path d={areaPath(tempHistory)} fill="url(#area-grad)"/>
            <path d={smoothPath(tempHistory)} fill="none" stroke={tempColorStr} stroke-width="2" stroke-linecap="round"/>
            <circle cx={chx(tempHistory.length - 1, tempHistory.length)} cy={cy(currentTemp)} r="4" fill={tempColorStr} stroke="var(--bg-card)" stroke-width="2"/>
          {/if}
        </svg>
      </div>

      <!-- Simulation -->
      <div class="sim-row">
        <span class="sim-label">Simulation</span>
        <button class="toggle-switch" class:on={simTemp !== null} onclick={() => {
          if (simTemp !== null) { simTemp = null; api.simulate.stop(); }
          else { simTemp = 40; api.simulate.temp(40); }
        }} aria-label="Simulation umschalten"></button>
        {#if simTemp !== null}
          <input type="range" min="20" max="85" step="0.5" value={simTemp} oninput={(e) => simTempLive(parseFloat(e.target.value))}>
          <span class="sim-val" style="color:{tempColorStr}">{simTemp.toFixed(0)}°</span>
        {/if}
      </div>
    </div>

    <!-- ═══ RECHTS: Kurveneditor ═══ -->
    <div class="panel panel-right">
      <div class="panel-title">Lüfterkurve</div>

      <!-- Profile -->
      <div class="profile-bar">
        {#each profiles as p}
          <button class="profile-pill" class:active={profile===p} onclick={() => selectProfile(p)}>
            <i class="fa-solid {profIcons[p] || 'fa-circle'}"></i>
            <span>{profLabels[p] || p}</span>
          </button>
        {/each}
      </div>

      <!-- Kurven-SVG -->
      <div class="curve-wrap">
        <svg bind:this={curveEl} viewBox="0 0 {CURVE.w} {CURVE.h}" class="curve-svg">
          <defs>
            <linearGradient id="curve-grad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stop-color="var(--accent)" stop-opacity="0.2"/>
              <stop offset="100%" stop-color="var(--accent)" stop-opacity="0"/>
            </linearGradient>
          </defs>
          <!-- Gitternetz -->
          {#each [0, 25, 50, 75, 100] as sp}
            <line x1={CURVE.pl} y1={ksy(sp)} x2={CURVE.pl + KW} y2={ksy(sp)} stroke="rgba(255,255,255,0.04)" stroke-dasharray="4"/>
            <text x={CURVE.pl - 6} y={ksy(sp) + 4} text-anchor="end" class="curve-label">{sp}%</text>
          {/each}
          {#each [30, 40, 50, 60, 70, 80] as t}
            <line x1={ktx(t)} y1={CURVE.pt} x2={ktx(t)} y2={CURVE.pt + KH} stroke="rgba(255,255,255,0.03)" stroke-dasharray="2"/>
            <text x={ktx(t)} y={CURVE.pt + KH + 16} text-anchor="middle" class="curve-label">{t}°</text>
          {/each}
          <line x1={CURVE.pl} y1={CURVE.pt} x2={CURVE.pl} y2={CURVE.pt + KH} stroke="rgba(255,255,255,0.08)" stroke-width="0.5"/>
          <line x1={CURVE.pl} y1={CURVE.pt + KH} x2={CURVE.pl + KW} y2={CURVE.pt + KH} stroke="rgba(255,255,255,0.08)" stroke-width="0.5"/>
          <!-- Sicherheitslinie -->
          <line x1={ktx(safetyTemp)} y1={CURVE.pt} x2={ktx(safetyTemp)} y2={CURVE.pt + KH} stroke="var(--red)" stroke-width="1" stroke-dasharray="4 3" opacity="0.4"/>
          <text x={ktx(safetyTemp)} y={CURVE.pt - 4} text-anchor="middle" class="curve-safety">Notfall</text>
          <!-- Aktuelle Temperaturlinie -->
          {#if currentTemp > TMIN}
            <line x1={ktx(currentTemp)} y1={CURVE.pt} x2={ktx(currentTemp)} y2={CURVE.pt + KH} stroke={tempColorStr} stroke-width="1.5" stroke-dasharray="6 4" opacity="0.6"/>
            <text x={ktx(currentTemp)} y={CURVE.pt - 4} text-anchor="middle" class="curve-temp">{currentTemp.toFixed(1)}°</text>
          {/if}
          <!-- Kurve -->
          <path d={curveFill(curve)} fill="url(#curve-grad)"/>
          <path d={curveLine(curve)} fill="none" stroke="var(--accent)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" filter="drop-shadow(0 0 4px rgba(0,180,255,0.3))"/>
          <!-- Punkte -->
          {#each curve as pt, i}
            <circle cx={ktx(pt.temp)} cy={ksy(pt.speed)} r={dragging===i?10:7} class="curve-pt" class:draggable={profile==='custom'} class:active={dragging===i}
              onmousedown={(e) => startDrag(i,e)} ontouchstart={(e) => startDrag(i,e)}/>
            <text x={ktx(pt.temp)} y={ksy(pt.speed)-12} text-anchor="middle" class="curve-pt-label">{pt.temp}° / {pt.speed}%</text>
          {/each}
        </svg>
      </div>

      <!-- Hysterese -->
      <div class="setting-row">
        <span>Hysterese</span>
        <input type="range" min="1" max="10" step="0.5" value={hysteresis} onchange={(e) => s.setFanSettings({ hysteresis: parseFloat(e.target.value) })}>
        <span class="setting-val">{hysteresis}°C</span>
      </div>

      <!-- Modus -->
      <div class="mode-row">
        <button class="mode-btn" class:active={mode==='auto'} onclick={() => s.setFanMode('auto')}>
          <i class="fa-solid fa-wand-magic-sparkles"></i> Automatik
        </button>
        <button class="mode-btn" class:active={mode==='manual'} onclick={() => s.setFanMode('manual')}>
          <i class="fa-solid fa-hand"></i> Manuell
        </button>
        <button class="mode-btn" class:active={mode==='off'} onclick={() => s.setFanMode('off')}>
          <i class="fa-solid fa-power-off"></i> Aus
        </button>
      </div>

      {#if mode === 'manual'}
        <div class="manual-row">
          <span>Geschwindigkeit</span>
          <input type="range" min="0" max="100" step="5" value={s.fan?.manual_speed||50} oninput={(e) => s.setFanManualSpeed(parseInt(e.target.value))}>
          <span class="setting-val">{s.fan?.manual_speed||50}%</span>
        </div>
      {/if}
    </div>
  </div>
</div>

<style>
  .layout { display: flex; flex-direction: column; height: 100%; gap: 12px; }
  .topbar { display: flex; align-items: center; gap: 10px; flex-shrink: 0; }
  .topbar h1 { font-size: var(--fs-xl); }
  .topbar-icon { color: var(--accent); font-size: var(--fs-lg); }
  .topbar-icon.spinning { animation: spin var(--spin-dur, 1s) linear infinite; }
  @keyframes spin { to { transform: rotate(360deg); } }

  /* ─── Layout ─── */
  .content { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; flex: 1; min-height: 0; }
  .panel { background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--radius); padding: 16px; display: flex; flex-direction: column; overflow: hidden; }
  .panel-title { font: 600 var(--fs-sm) var(--font); color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 12px; }

  /* ─── LED-Leiste ─── */
  .led-strip {
    display: flex; align-items: center; justify-content: center;
    gap: 18px; padding: 16px 24px;
    background: #000; border-radius: var(--radius); border: 1px solid #222;
    margin-bottom: 12px;
  }
  .led-housing { position: relative; width: 40px; height: 40px; display: flex; align-items: center; justify-content: center; }
  .led-glow { position: absolute; width: 70px; height: 70px; border-radius: 50%; top: 50%; left: 50%; transform: translate(-50%,-50%); pointer-events: none; }
  .led-pixel { width: 22px; height: 22px; border-radius: 5px; border: 1px solid rgba(255,255,255,0.12); position: relative; z-index: 1; transition: background 1s, box-shadow 1s; }
  .led-pixel.blink, .led-glow.blink { animation: ledAlarm 0.33s steps(1) infinite; }
  @keyframes ledAlarm { 0% { opacity: 1; } 50% { opacity: 0; } }

  /* ─── Temperatur ─── */
  .temp-hero { font: 800 56px var(--mono); text-align: center; line-height: 1; transition: color 1s; margin-bottom: 8px; }
  .temp-unit { font-size: 24px; font-weight: 400; color: var(--text-muted); }

  .status-row { display: flex; justify-content: center; gap: 12px; margin-bottom: 10px; }
  .status-chip {
    display: flex; align-items: center; gap: 6px;
    padding: 4px 12px; border-radius: 99px;
    background: var(--bg-elevated); border: 1px solid var(--border);
    font: 500 var(--fs-xs) var(--mono); color: var(--text-secondary);
  }
  .status-chip .spinning { animation: spin var(--spin-dur, 1s) linear infinite; }

  /* ─── Diagramm ─── */
  .chart { flex: 1; min-height: 0; background: var(--bg-deep); border-radius: var(--radius-sm); padding: 4px; }
  .chart-svg { width: 100%; height: 100%; display: block; }
  .chart-label { font: 10px var(--mono); fill: var(--text-muted); }

  /* ─── Simulation ─── */
  .sim-row {
    display: flex; align-items: center; gap: 10px; flex-shrink: 0; margin-top: 8px;
    padding: 8px 12px; border-radius: var(--radius-sm); background: var(--bg-elevated);
  }
  .sim-label { font: 500 var(--fs-xs) var(--font); color: var(--text-muted); white-space: nowrap; }
  .sim-row input[type=range] { flex: 1; }
  .sim-val { font: 700 var(--fs-sm) var(--mono); min-width: 32px; text-align: right; }
  .toggle-switch {
    width: 36px; height: 20px; border-radius: 10px; border: none;
    background: rgba(255,255,255,0.1); cursor: pointer; position: relative;
    transition: background var(--tr); flex-shrink: 0;
  }
  .toggle-switch.on { background: var(--green); }
  .toggle-switch::after {
    content: ''; position: absolute; top: 2px; left: 2px;
    width: 16px; height: 16px; border-radius: 50%; background: #fff;
    transition: transform var(--tr); box-shadow: 0 1px 2px rgba(0,0,0,0.3);
  }
  .toggle-switch.on::after { transform: translateX(16px); }

  /* ─── Kurveneditor ─── */
  .profile-bar { display: flex; gap: 4px; flex-wrap: wrap; margin-bottom: 8px; }
  .profile-pill {
    padding: 4px 10px; background: var(--bg-deep); border: 1px solid var(--border);
    border-radius: 99px; font: 500 var(--fs-xs) var(--font); cursor: pointer;
    color: var(--text-muted); transition: all 150ms; display: flex; align-items: center; gap: 4px;
  }
  .profile-pill:hover { border-color: var(--text-muted); }
  .profile-pill.active { background: var(--accent-dim); border-color: var(--accent); color: var(--accent); }

  .curve-wrap { flex: 1; min-height: 0; background: var(--bg-deep); border-radius: var(--radius-sm); padding: 4px; }
  .curve-svg { width: 100%; height: 100%; display: block; }
  .curve-label { font: 10px var(--mono); fill: var(--text-muted); }
  .curve-safety { font: 600 9px var(--mono); fill: var(--red); }
  .curve-temp { font: 600 10px var(--mono); fill: var(--text-primary); }
  .curve-pt-label { font: 600 9px var(--mono); fill: var(--text-muted); }
  .curve-pt { fill: var(--accent); stroke: var(--bg-card); stroke-width: 3; transition: r 150ms; }
  .curve-pt.draggable { cursor: grab; } .curve-pt.draggable:hover { r: 10; } .curve-pt.active { fill: var(--cyan); r: 10; }

  /* ─── Einstellungen ─── */
  .setting-row, .manual-row {
    display: flex; align-items: center; gap: 10px;
    padding: 8px 0; font: 500 var(--fs-xs) var(--font); color: var(--text-secondary);
  }
  .setting-row input, .manual-row input { flex: 1; }
  .setting-val { font: 600 var(--fs-xs) var(--mono); color: var(--text-muted); min-width: 40px; text-align: right; }

  .mode-row { display: flex; gap: 6px; margin-top: 4px; }
  .mode-btn {
    flex: 1; height: 36px; border-radius: var(--radius-sm);
    border: 1px solid var(--border); background: var(--bg-elevated);
    color: var(--text-muted); font: 500 var(--fs-xs) var(--font);
    cursor: pointer; transition: all 150ms;
    display: flex; align-items: center; justify-content: center; gap: 6px;
  }
  .mode-btn:hover { border-color: var(--text-muted); }
  .mode-btn.active { background: var(--accent-dim); border-color: var(--accent); color: var(--accent); }

  /* ─── Responsive ─── */
  @media (max-width: 900px) {
    .content { grid-template-columns: 1fr; }
  }
</style>
