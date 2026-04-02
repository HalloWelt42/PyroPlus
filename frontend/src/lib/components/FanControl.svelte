<script>
  import { api } from '../api/client.js';
  let { state: s } = $props();

  /* ═══ GEMEINSAMER STATE ═══ */
  const realTemp = $derived(s.fan?.current_temp || s.stats?.cpu?.temp || 0);
  const currentDuty = $derived(s.fan?.current_duty || 0);
  const currentRpm = $derived(s.fan?.current_rpm || 0);
  const mode = $derived(s.fan?.mode || 'auto');
  const profile = $derived(s.fan?.profile || 'balanced');
  const curve = $derived(s.fan?.curve || []);
  const profiles = $derived(s.fan?.profiles || ['silent','balanced','performance','night','custom']);
  const hysteresis = $derived(s.fan?.hysteresis || 3);
  const safetyTemp = $derived(s.fan?.safety_temp || 80);
  const tempHistory = $derived(s.stats?.history?.temp || []);

  /* Simulationen — getrennt für jeden Lüfter */
  let simCaseTemp = $state(null);   // Gehäuselüfter: lokale Simulation (nur Anzeige)
  let simCpuTemp = $state(null);    // CPU-Lüfter: echte Simulation (wirkt auf Hardware)
  let _simTimer = 0;

  /* Temperatur die der jeweilige Bereich sieht */
  const caseFanTemp = $derived(simCaseTemp !== null ? simCaseTemp : realTemp);
  const cpuFanTemp = $derived(simCpuTemp !== null ? simCpuTemp : realTemp);
  /* currentTemp für gemeinsame Elemente (LEDs, Farbe) — CPU-Sim hat Vorrang */
  const currentTemp = $derived(simCpuTemp !== null ? simCpuTemp : (simCaseTemp !== null ? simCaseTemp : realTemp));

  function simCaseLive(val) { simCaseTemp = val; }
  function simCpuLive(val) {
    simCpuTemp = val;
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
  const isBlinking = $derived(currentTemp >= 60);
  const ledColors = $derived(() => [0,1,2,3].map(i => { const c = tempToRgb(currentTemp + (i - 1.5) * 2); return `rgb(${c.r},${c.g},${c.b})`; }));
  const ledGlows = $derived(() => [0,1,2,3].map(i => { const c = tempToRgb(currentTemp + (i - 1.5) * 2); return `rgba(${c.r},${c.g},${c.b},0.5)`; }));

  /* ═══ GEHÄUSELÜFTER — Schwellwerte ═══ */
  let caseFanOn = $derived(s.fan?.gpio_on || false);
  let thresholdOn = $state(50);
  let thresholdOff = $state(45);
  $effect(() => { if (s.fan?.threshold_on) thresholdOn = s.fan.threshold_on; if (s.fan?.threshold_off) thresholdOff = s.fan.threshold_off; });
  function onThresholdOnInput(e) { thresholdOn = parseInt(e.target.value); if (thresholdOff >= thresholdOn - 2) thresholdOff = thresholdOn - 3; }
  function onThresholdOffInput(e) { thresholdOff = parseInt(e.target.value); if (thresholdOn <= thresholdOff + 2) thresholdOn = thresholdOff + 3; }
  function commitCaseFan() { s.setFanSettings({ threshold_on: thresholdOn, threshold_off: thresholdOff }); }

  /* ═══ TEMPERATUR-DIAGRAMM ═══ */
  const CHART = { w: 460, h: 200, pl: 36, pr: 50, pt: 12, pb: 24 };
  const CW = CHART.w - CHART.pl - CHART.pr, CH = CHART.h - CHART.pt - CHART.pb;
  const chartMin = $derived(Math.min(30, ...tempHistory) - 2);
  const chartMax = $derived(Math.max(60, ...tempHistory) + 2);
  const chartRange = $derived(chartMax - chartMin || 1);
  function cy(t) { return CHART.pt + CH - ((t - chartMin) / chartRange) * CH; }
  function chx(i, len) { return CHART.pl + (i / Math.max(1, len - 1)) * CW; }
  const yTicks = $derived(() => { const ticks = []; for (let t = Math.ceil(chartMin / 5) * 5; t <= chartMax; t += 5) ticks.push(t); return ticks; });
  function smoothPath(arr) {
    if (!arr || arr.length < 2) return '';
    const pts = arr.map((v, i) => ({ x: chx(i, arr.length), y: cy(v) }));
    let d = `M${pts[0].x.toFixed(1)},${pts[0].y.toFixed(1)}`;
    for (let i = 0; i < pts.length - 1; i++) {
      const p0 = pts[Math.max(0, i - 1)], p1 = pts[i], p2 = pts[Math.min(pts.length - 1, i + 1)], p3 = pts[Math.min(pts.length - 1, i + 2)];
      const t = 0.3;
      d += `C${(p1.x+(p2.x-p0.x)*t).toFixed(1)},${(p1.y+(p2.y-p0.y)*t).toFixed(1)},${(p2.x-(p3.x-p1.x)*t).toFixed(1)},${(p2.y-(p3.y-p1.y)*t).toFixed(1)},${p2.x.toFixed(1)},${p2.y.toFixed(1)}`;
    }
    return d;
  }
  function areaPath(arr) { const l = smoothPath(arr); return l ? `${l}L${chx(arr.length-1,arr.length).toFixed(1)},${CHART.pt+CH}L${chx(0,arr.length).toFixed(1)},${CHART.pt+CH}Z` : ''; }

  /* ═══ KURVEN-EDITOR ═══ */
  const CURVE = { w: 460, h: 220, pl: 36, pr: 50, pt: 40, pb: 24 };
  const KW = CURVE.w - CURVE.pl - CURVE.pr, KH = CURVE.h - CURVE.pt - CURVE.pb;
  const TMIN = 25, TMAX = 80;
  function ktx(t) { return CURVE.pl + ((t - TMIN) / (TMAX - TMIN)) * KW; }
  function ksy(sp) { return CURVE.pt + KH - (sp / 100) * KH; }
  function kxt(x) { return Math.round(Math.max(TMIN, Math.min(TMAX, TMIN + ((x - CURVE.pl) / KW) * (TMAX - TMIN)))); }
  function kys(y) { return Math.round(Math.max(0, Math.min(100, ((CURVE.pt + KH - y) / KH) * 100))); }
  function curveLine(pts) { if (!pts.length) return ''; const s = [...pts].sort((a,b)=>a.temp-b.temp); return s.map((p,i)=>`${i?'L':'M'}${ktx(p.temp).toFixed(1)},${ksy(p.speed).toFixed(1)}`).join(' '); }
  function curveFill(pts) { if (!pts.length) return ''; const s = [...pts].sort((a,b)=>a.temp-b.temp); return `${curveLine(pts)}L${ktx(s[s.length-1].temp).toFixed(1)},${ksy(0)}L${ktx(s[0].temp).toFixed(1)},${ksy(0)}Z`; }

  let dragging = $state(-1);
  let curveEl = $state(null);
  function startDrag(i, e) { if (profile !== 'custom') { s.toast('Wechsle zu Benutzerdefiniert', 'info'); return; } e.preventDefault(); dragging = i; window.addEventListener('mousemove', onDrag); window.addEventListener('mouseup', stopDrag); window.addEventListener('touchmove', onDrag, { passive: false }); window.addEventListener('touchend', stopDrag); }
  function onDrag(e) { if (dragging < 0 || !curveEl) return; e.preventDefault(); const pt = curveEl.createSVGPoint(); pt.x = e.touches ? e.touches[0].clientX : e.clientX; pt.y = e.touches ? e.touches[0].clientY : e.clientY; const svgPt = pt.matrixTransform(curveEl.getScreenCTM().inverse()); const pts = [...curve]; pts[dragging] = { temp: kxt(svgPt.x), speed: kys(svgPt.y) }; s.updateFan({ curve: pts }); }
  function stopDrag() { if (dragging >= 0) { s.setFanCurve(curve); dragging = -1; } window.removeEventListener('mousemove', onDrag); window.removeEventListener('mouseup', stopDrag); window.removeEventListener('touchmove', onDrag); window.removeEventListener('touchend', stopDrag); }

  const profIcons = { silent: 'fa-volume-xmark', balanced: 'fa-scale-balanced', performance: 'fa-rocket', night: 'fa-moon', custom: 'fa-sliders' };
  const profLabels = { silent: 'Leise', balanced: 'Ausgewogen', performance: 'Leistung', night: 'Nacht', custom: 'Eigene' };
  /* Fan-Animation: proportional zu RPM aber immer wahrnehmbar.
     0 RPM = steht, 500 RPM = 3s/Umdrehung, 3500 RPM = 0.4s/Umdrehung */
  const fanSpinDuration = $derived(currentRpm > 0
    ? (3.0 - Math.min(2.6, (currentRpm / 3500) * 2.6)).toFixed(1) + 's'
    : '0s');
</script>

<div class="layout">
  <div class="content">
    <!-- ═══════════════════════════════════════════════════
         LINKS — Gehäuselüfter (GPIO An/Aus)
         ═══════════════════════════════════════════════════ -->
    <div class="panel">
      <div class="fan-header">
        <i class="fa-solid fa-hard-drive fan-icon"></i>
        <div><div class="fan-title">Gehäuselüfter</div><div class="fan-sub">GPIO Pin 6 · An/Aus · Schwellwert</div></div>
        <div class="fan-badge" class:on={caseFanOn}><i class="fa-solid fa-fan" class:spinning={caseFanOn} style="animation-duration:1.5s"></i> {caseFanOn ? 'Läuft' : 'Aus'}</div>
      </div>

      <!-- Diagramm mit Schwellwerten -->
      <div class="chart">
        <svg viewBox="0 0 {CHART.w} {CHART.h}">
          <defs><linearGradient id="ag" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color={tempColorStr} stop-opacity="0.15"/><stop offset="100%" stop-color={tempColorStr} stop-opacity="0.02"/></linearGradient></defs>
          {#each yTicks() as t}<line x1={CHART.pl} y1={cy(t)} x2={CHART.pl+CW} y2={cy(t)} stroke="rgba(255,255,255,0.04)" stroke-width="0.5"/><text x={CHART.pl-5} y={cy(t)+3.5} text-anchor="end" class="ax">{t}°</text>{/each}
          <line x1={CHART.pl} y1={CHART.pt} x2={CHART.pl} y2={CHART.pt+CH} stroke="rgba(255,255,255,0.08)"/>
          <line x1={CHART.pl} y1={CHART.pt+CH} x2={CHART.pl+CW} y2={CHART.pt+CH} stroke="rgba(255,255,255,0.08)"/>
          <line x1={CHART.pl} y1={cy(thresholdOn)} x2={CHART.pl+CW} y2={cy(thresholdOn)} stroke="var(--red)" stroke-width="0.8" stroke-dasharray="4 3" opacity="0.5"/>
          <text x={CHART.pl+CW+4} y={cy(thresholdOn)+3.5} class="ax-on">{thresholdOn}° Ein</text>
          <line x1={CHART.pl} y1={cy(thresholdOff)} x2={CHART.pl+CW} y2={cy(thresholdOff)} stroke="var(--green)" stroke-width="0.8" stroke-dasharray="4 3" opacity="0.5"/>
          <text x={CHART.pl+CW+4} y={cy(thresholdOff)+3.5} class="ax-off">{thresholdOff}° Aus</text>
          {#if tempHistory.length > 2}
            {#each [60,30,0] as ago}<text x={chx(Math.max(0,tempHistory.length-1-ago),tempHistory.length)} y={CHART.pt+CH+16} text-anchor="middle" class="ax">{ago===0?'jetzt':`-${ago}s`}</text>{/each}
            <path d={areaPath(tempHistory)} fill="url(#ag)"/>
            <path d={smoothPath(tempHistory)} fill="none" stroke={tempColorStr} stroke-width="2" stroke-linecap="round"/>
            <circle cx={chx(tempHistory.length-1,tempHistory.length)} cy={cy(tempHistory[tempHistory.length-1])} r="4" fill={tempColorStr} stroke="var(--bg-card)" stroke-width="2"/>
          {/if}
        </svg>
      </div>

      <!-- Schwellwert-Regler -->
      <div class="ctrl">
        <div class="ctrl-row"><span><i class="fa-solid fa-arrow-up" style="color:var(--red)"></i> Einschalten</span><input type="range" min="35" max="75" step="1" value={thresholdOn} oninput={onThresholdOnInput} onchange={commitCaseFan}><span class="ctrl-val">{thresholdOn}°C</span></div>
        <div class="ctrl-row"><span><i class="fa-solid fa-arrow-down" style="color:var(--green)"></i> Ausschalten</span><input type="range" min="30" max="70" step="1" value={thresholdOff} oninput={onThresholdOffInput} onchange={commitCaseFan}><span class="ctrl-val">{thresholdOff}°C</span></div>
      </div>

      <!-- Gehäuse-Simulation (nur lokal, zeigt Schwellwert-Reaktion) -->
      <div class="sim">
        <span>Simulation</span>
        <button class="tog" class:on={simCaseTemp!==null} onclick={()=>{ simCaseTemp = simCaseTemp !== null ? null : 40; }} aria-label="Simulation"></button>
        {#if simCaseTemp!==null}<input type="range" min="20" max="85" step="0.5" value={simCaseTemp} oninput={(e)=>simCaseLive(parseFloat(e.target.value))}><span class="sim-v" style="color:{tempColorStr}">{simCaseTemp.toFixed(0)}°</span>{/if}
      </div>
    </div>

    <!-- ═══════════════════════════════════════════════════
         RECHTS — CPU-Lüfter (Temperaturkurve)
         ═══════════════════════════════════════════════════ -->
    <div class="panel">
      <div class="fan-header">
        <i class="fa-solid fa-microchip fan-icon"></i>
        <div><div class="fan-title">CPU-Lüfter</div><div class="fan-sub">Kernel PWM · 0-100% stufenlos</div></div>
        <div class="fan-badge" class:on={currentRpm > 0}><i class="fa-solid fa-fan" style="animation-duration:{fanSpinDuration}" class:spinning={currentRpm > 0}></i> {currentRpm > 0 ? `${currentRpm} RPM` : 'Aus'}</div>
      </div>

      <!-- Kurveneditor mit Profilen und LEDs oben -->
      <div class="chart chart-with-profiles">
        <div class="chart-topbar">
          <div class="chart-profiles">
            {#each profiles as p}<button class="pill" class:active={profile===p} onclick={()=>s.setFanProfile(p)}><i class="fa-solid {profIcons[p]||'fa-circle'}"></i> {profLabels[p]||p}</button>{/each}
          </div>
          <div class="chart-leds">
            {#each [0,1,2,3] as i}
              <div class="led-sm" class:blink={isBlinking} style="background:{ledColors()[i]};box-shadow:0 0 6px {ledGlows()[i]}"></div>
            {/each}
          </div>
        </div>
        <svg bind:this={curveEl} viewBox="0 0 {CURVE.w} {CURVE.h}">
          <defs><linearGradient id="cg" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="var(--accent)" stop-opacity="0.2"/><stop offset="100%" stop-color="var(--accent)" stop-opacity="0"/></linearGradient></defs>
          {#each [0,25,50,75,100] as sp}<line x1={CURVE.pl} y1={ksy(sp)} x2={CURVE.pl+KW} y2={ksy(sp)} stroke="rgba(255,255,255,0.04)" stroke-dasharray="4"/><text x={CURVE.pl-5} y={ksy(sp)+4} text-anchor="end" class="ax">{sp}%</text>{/each}
          {#each [30,40,50,60,70,80] as t}<line x1={ktx(t)} y1={CURVE.pt} x2={ktx(t)} y2={CURVE.pt+KH} stroke="rgba(255,255,255,0.03)" stroke-dasharray="2"/><text x={ktx(t)} y={CURVE.pt+KH+16} text-anchor="middle" class="ax">{t}°</text>{/each}
          <line x1={CURVE.pl} y1={CURVE.pt} x2={CURVE.pl} y2={CURVE.pt+KH} stroke="rgba(255,255,255,0.08)"/>
          <line x1={CURVE.pl} y1={CURVE.pt+KH} x2={CURVE.pl+KW} y2={CURVE.pt+KH} stroke="rgba(255,255,255,0.08)"/>
          <line x1={ktx(safetyTemp)} y1={CURVE.pt} x2={ktx(safetyTemp)} y2={CURVE.pt+KH} stroke="var(--red)" stroke-width="1" stroke-dasharray="4 3" opacity="0.4"/>
          <text x={ktx(safetyTemp)} y={CURVE.pt-4} text-anchor="middle" class="ax-on">Notfall</text>
          {#if cpuFanTemp > TMIN}<line x1={ktx(cpuFanTemp)} y1={CURVE.pt} x2={ktx(cpuFanTemp)} y2={CURVE.pt+KH} stroke={tempColorStr} stroke-width="1.5" stroke-dasharray="6 4" opacity="0.6"/><text x={ktx(cpuFanTemp)} y={CURVE.pt-4} text-anchor="middle" class="ax-now">{cpuFanTemp.toFixed(1)}°</text>{/if}
          <path d={curveFill(curve)} fill="url(#cg)"/>
          <path d={curveLine(curve)} fill="none" stroke="var(--accent)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" filter="drop-shadow(0 0 4px rgba(0,180,255,0.3))"/>
          {#each curve as pt, i}<circle cx={ktx(pt.temp)} cy={ksy(pt.speed)} r={dragging===i?10:7} class="dot" class:drag={profile==='custom'} class:act={dragging===i} onmousedown={(e)=>startDrag(i,e)} ontouchstart={(e)=>startDrag(i,e)}/><text x={ktx(pt.temp)} y={ksy(pt.speed)-12} text-anchor="middle" class="ax-pt">{pt.temp}°/{pt.speed}%</text>{/each}
        </svg>
      </div>

      <!-- Steuerung -->
      <div class="ctrl">
        <div class="ctrl-row"><span>Hysterese</span><input type="range" min="1" max="10" step="0.5" value={hysteresis} onchange={(e)=>s.setFanSettings({hysteresis:parseFloat(e.target.value)})}><span class="ctrl-val">{hysteresis}°C</span></div>
      </div>
      <div class="modes">
        <button class="mode" class:active={mode==='auto'} onclick={()=>s.setFanMode('auto')}><i class="fa-solid fa-wand-magic-sparkles"></i> Automatik</button>
        <button class="mode" class:active={mode==='manual'} onclick={()=>s.setFanMode('manual')}><i class="fa-solid fa-hand"></i> Manuell</button>
        <button class="mode" class:active={mode==='off'} onclick={()=>s.setFanMode('off')}><i class="fa-solid fa-power-off"></i> Aus</button>
      </div>
      {#if mode==='manual'}<div class="ctrl"><div class="ctrl-row"><span>Geschwindigkeit</span><input type="range" min="0" max="100" step="5" value={s.fan?.manual_speed||50} oninput={(e)=>s.setFanManualSpeed(parseInt(e.target.value))}><span class="ctrl-val">{s.fan?.manual_speed||50}%</span></div></div>{/if}

      <!-- CPU-Simulation (wirkt auf echte Hardware: PWM + LEDs) -->
      <div class="sim">
        <span>Simulation</span>
        <button class="tog" class:on={simCpuTemp!==null} onclick={()=>{if(simCpuTemp!==null){simCpuTemp=null;api.simulate.stop();}else{simCpuTemp=40;api.simulate.temp(40);}}} aria-label="Simulation"></button>
        {#if simCpuTemp!==null}<input type="range" min="20" max="85" step="0.5" value={simCpuTemp} oninput={(e)=>simCpuLive(parseFloat(e.target.value))}><span class="sim-v" style="color:{tempColorStr}">{simCpuTemp.toFixed(0)}°</span>{/if}
      </div>
    </div>
  </div>
</div>

<style>
  .layout { display: flex; flex-direction: column; height: 100%; }
  .content { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; flex: 1; min-height: 0; align-items: start; }
  .panel {
    background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--radius);
    padding: 14px; display: flex; flex-direction: column; gap: 10px;
  }

  /* Lüfter-Header */
  .fan-header { display: flex; align-items: center; gap: 10px; }
  .fan-icon { font-size: var(--fs-lg); color: var(--accent); }
  .fan-title { font: 700 var(--fs-xl) var(--font); }
  .fan-sub { font: 500 var(--fs-sm) var(--mono); color: var(--text-muted); }
  .fan-badge { margin-left: auto; display: flex; align-items: center; gap: 8px; padding: 6px 14px; border-radius: 99px; background: rgba(255,255,255,0.04); border: 1px solid var(--border); font: 500 var(--fs-sm) var(--mono); color: var(--text-muted); }
  .fan-badge.on { color: var(--green); border-color: rgba(0,232,138,0.2); background: rgba(0,232,138,0.06); }
  .fan-badge i { font-size: var(--fs-lg); }
  .spinning { animation: spin 1s linear infinite; animation-duration: inherit; }
  @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }

  @keyframes blink { 0% { opacity: 1; } 50% { opacity: 0; } }

  /* Diagramm */
  .chart { height: 40vh; background: var(--bg-deep); border-radius: var(--radius-sm); padding: 4px; overflow: hidden; }
  .chart svg { width: 100%; height: 100%; display: block; }
  .ax { font: 10px var(--mono); fill: var(--text-muted); }
  .ax-on { font: 600 9px var(--mono); fill: var(--red); }
  .ax-off { font: 600 9px var(--mono); fill: var(--green); }
  .ax-now { font: 600 10px var(--mono); fill: var(--text-primary); }
  .ax-pt { font: 600 9px var(--mono); fill: var(--text-muted); }

  /* Profile + LEDs (im Chart-Bereich) */
  .chart-with-profiles { position: relative; }
  .chart-topbar {
    position: absolute; top: 6px; left: 6px; right: 6px; z-index: 2;
    display: flex; align-items: center; justify-content: space-between;
  }
  .chart-profiles { display: flex; gap: 4px; flex-wrap: wrap; }
  .chart-leds { display: flex; gap: 6px; align-items: center; }
  .led-sm { width: 14px; height: 14px; border-radius: 3px; border: 1px solid rgba(255,255,255,0.1); transition: background 1s, box-shadow 1s; }
  .led-sm.blink { animation: blink 0.33s steps(1) infinite; }
  .pill { padding: 4px 10px; background: rgba(10,14,24,0.85); backdrop-filter: blur(4px); border: 1px solid var(--border); border-radius: 99px; font: 500 var(--fs-xs) var(--font); cursor: pointer; color: var(--text-muted); transition: all 150ms; display: flex; align-items: center; gap: 4px; }
  .pill:hover { border-color: var(--text-muted); }
  .pill.active { background: var(--accent-dim); border-color: var(--accent); color: var(--accent); }

  /* Kurven-Punkte */
  .dot { fill: var(--accent); stroke: var(--bg-card); stroke-width: 3; transition: r 150ms; }
  .dot.drag { cursor: grab; } .dot.drag:hover { r: 10; } .dot.act { fill: var(--cyan); r: 10; }

  /* Steuerung */
  .ctrl { display: flex; flex-direction: column; gap: 6px; }
  .ctrl-row { display: flex; align-items: center; gap: 10px; font: 500 var(--fs-sm) var(--font); color: var(--text-secondary); }
  .ctrl-row span:first-child { min-width: 110px; display: flex; align-items: center; gap: 6px; white-space: nowrap; }
  .ctrl-row input { flex: 1; }
  .ctrl-val { font: 600 var(--fs-sm) var(--mono); color: var(--text-primary); background: var(--bg-deep); padding: 3px 10px; border-radius: var(--radius-sm); min-width: 44px; text-align: center; }

  /* Modus */
  .modes { display: flex; gap: 6px; }
  .mode { flex: 1; height: 38px; border-radius: var(--radius-sm); border: 1px solid var(--border); background: var(--bg-elevated); color: var(--text-muted); font: 500 var(--fs-sm) var(--font); cursor: pointer; transition: all 150ms; display: flex; align-items: center; justify-content: center; gap: 6px; }
  .mode:hover { border-color: var(--text-muted); }
  .mode.active { background: var(--accent-dim); border-color: var(--accent); color: var(--accent); }

  /* Simulation */
  .sim { display: flex; align-items: center; gap: 10px; padding: 8px 12px; border-radius: var(--radius-sm); background: var(--bg-elevated); font: 500 var(--fs-sm) var(--font); color: var(--text-muted); }
  .sim input { flex: 1; }
  .sim-v { font: 700 var(--fs-sm) var(--mono); min-width: 32px; text-align: right; }
  .tog { width: 34px; height: 18px; border-radius: 9px; border: none; background: rgba(255,255,255,0.1); cursor: pointer; position: relative; transition: background var(--tr); flex-shrink: 0; }
  .tog.on { background: var(--green); }
  .tog::after { content: ''; position: absolute; top: 2px; left: 2px; width: 14px; height: 14px; border-radius: 50%; background: #fff; transition: transform var(--tr); box-shadow: 0 1px 2px rgba(0,0,0,0.3); }
  .tog.on::after { transform: translateX(16px); }

  @media (max-width: 900px) { .content { grid-template-columns: 1fr; } }
</style>
