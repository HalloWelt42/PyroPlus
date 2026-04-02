<script>
  let { state: s } = $props();

  const mode = $derived(s.fan?.mode || 'auto');
  const profile = $derived(s.fan?.profile || 'balanced');
  const curve = $derived(s.fan?.curve || []);
  const profiles = $derived(s.fan?.profiles || ['silent','balanced','performance','night','custom']);
  const settings = $derived(s.fan?.settings || {});
  const currentTemp = $derived(s.fan?.current_temp || s.stats?.cpu?.temp || 0);
  const currentSpeed = $derived(s.fan?.current_speed || 0);
  const estimatedRpm = $derived(s.fan?.estimated_rpm || 0);

  const W = 600, H = 220, PL = 50, PR = 20, PT = 25, PB = 30;
  const GW = W - PL - PR, GH = H - PT - PB;
  const TMIN = 25, TMAX = 80;

  function tx(t) { return PL + ((t - TMIN) / (TMAX - TMIN)) * GW; }
  function sy(sp) { return PT + GH - (sp / 100) * GH; }
  function xt(x) { return Math.round(Math.max(TMIN, Math.min(TMAX, TMIN + ((x - PL) / GW) * (TMAX - TMIN)))); }
  function ys(y) { return Math.round(Math.max(0, Math.min(100, ((PT + GH - y) / GH) * 100))); }

  function linePath(pts) {
    if (!pts.length) return '';
    const sorted = [...pts].sort((a, b) => a.temp - b.temp);
    return sorted.map((p, i) => `${i ? 'L' : 'M'}${tx(p.temp).toFixed(1)},${sy(p.speed).toFixed(1)}`).join(' ');
  }
  function fillPath(pts) {
    if (!pts.length) return '';
    const sorted = [...pts].sort((a, b) => a.temp - b.temp);
    const lp = linePath(pts);
    const last = sorted[sorted.length - 1], first = sorted[0];
    return `${lp} L${tx(last.temp).toFixed(1)},${sy(0)} L${tx(first.temp).toFixed(1)},${sy(0)} Z`;
  }

  let dragging = $state(-1);
  let svgEl = $state(null);

  function startDrag(i, e) {
    if (profile !== 'custom') {
      s.toast('Wechsle zu Custom um Punkte zu bewegen', 'info');
      return;
    }
    e.preventDefault(); dragging = i;
    window.addEventListener('mousemove', onDrag);
    window.addEventListener('mouseup', stopDrag);
    window.addEventListener('touchmove', onDrag, { passive: false });
    window.addEventListener('touchend', stopDrag);
  }
  function onDrag(e) {
    if (dragging < 0 || !svgEl) return;
    e.preventDefault();
    const rect = svgEl.getBoundingClientRect();
    const cx = e.touches ? e.touches[0].clientX : e.clientX;
    const cy = e.touches ? e.touches[0].clientY : e.clientY;
    /* CTM (Current Transform Matrix) für präzise SVG-Koordinaten */
    const pt = svgEl.createSVGPoint();
    pt.x = cx; pt.y = cy;
    const svgPt = pt.matrixTransform(svgEl.getScreenCTM().inverse());
    const pts = [...curve]; pts[dragging] = { temp: xt(svgPt.x), speed: ys(svgPt.y) };
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
  function updSetting(key, e) { s.setFanSettings({ [key]: parseFloat(e.target.value) }); }

  async function addPoint() {
    if (profile !== 'custom') { await selectProfile('custom'); }
    const pts = [...curve];
    pts.push({ temp: Math.round((TMIN + TMAX) / 2), speed: 50 });
    s.updateFan({ curve: pts });
    s.setFanCurve(pts);
  }
  async function removePoint(i) {
    if (curve.length <= 2) return;
    const pts = curve.filter((_, k) => k !== i);
    s.updateFan({ curve: pts });
    s.setFanCurve(pts);
  }

  const profIcons = { silent: 'fa-volume-xmark', balanced: 'fa-scale-balanced', performance: 'fa-rocket', night: 'fa-moon', custom: 'fa-sliders' };
  const profLabels = { silent: 'Leise', balanced: 'Ausgewogen', performance: 'Leistung', night: 'Nacht', custom: 'Benutzerdefiniert' };
  const tempTicks = [30, 40, 50, 60, 70, 80];
  const spdTicks = [0, 25, 50, 75, 100];
</script>

<div class="layout">
  <!-- ═══ KOPFZEILE ═══ -->
  <header class="topbar">
    <i class="fa-solid fa-fan topbar-icon"></i>
    <h1>Lüftersteuerung</h1>
  </header>

  <!-- ═══ INHALT ═══ -->
  <div class="content">
    <!-- Kurven-Editor -->
    <div class="panel panel-graph">
      <!-- Live-Anzeige oben rechts im Graph -->
      <div class="graph-live">
        <div class="live-item">
          <span class="live-label">Temperatur</span>
          <span class="live-value temp">{currentTemp.toFixed(1)}°C</span>
        </div>
        <div class="live-divider"></div>
        <div class="live-item">
          <span class="live-label">Geschwindigkeit</span>
          <span class="live-value speed">{Math.round(currentSpeed)}%</span>
        </div>
        {#if estimatedRpm > 0}
          <div class="live-divider"></div>
          <div class="live-item">
            <span class="live-label">Drehzahl</span>
            <span class="live-value rpm">{estimatedRpm} RPM</span>
          </div>
        {/if}
      </div>

      <div class="profile-bar">
        {#each profiles as p}
          <button class="profile-pill" class:active={profile===p} onclick={() => selectProfile(p)}>
            <i class="fa-solid {profIcons[p] || 'fa-circle'}"></i>
            <span>{profLabels[p] || p}</span>
          </button>
        {/each}
        {#if profile === 'custom'}
          <button class="profile-pill profile-add" onclick={addPoint} aria-label="Punkt hinzufügen">
            <i class="fa-solid fa-plus"></i>
            <span>Punkt</span>
          </button>
        {/if}
      </div>

      <div class="graph-wrap">
        <svg bind:this={svgEl} viewBox="0 0 {W} {H}" class="graph">
          <defs>
            <linearGradient id="cg" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stop-color="var(--accent)" stop-opacity="0.25"/>
              <stop offset="100%" stop-color="var(--accent)" stop-opacity="0"/>
            </linearGradient>
          </defs>
          <line x1={PL} y1={PT} x2={PL} y2={PT+GH} stroke="rgba(0,180,255,0.08)"/>
          <line x1={PL} y1={PT+GH} x2={PL+GW} y2={PT+GH} stroke="rgba(0,180,255,0.08)"/>
          {#each spdTicks as sp}
            <line x1={PL} y1={sy(sp)} x2={PL+GW} y2={sy(sp)} stroke="rgba(0,180,255,0.04)" stroke-dasharray="4"/>
            <text x={PL-8} y={sy(sp)+4} text-anchor="end" class="ax">{sp}%</text>
          {/each}
          {#each tempTicks as t}
            <line x1={tx(t)} y1={PT} x2={tx(t)} y2={PT+GH} stroke="rgba(0,180,255,0.03)" stroke-dasharray="2"/>
            <text x={tx(t)} y={PT+GH+16} text-anchor="middle" class="ax">{t}°</text>
          {/each}
          {#if currentTemp > TMIN}
            <line x1={tx(currentTemp)} y1={PT} x2={tx(currentTemp)} y2={PT+GH} stroke="var(--cyan)" stroke-width="1.5" stroke-dasharray="6 4" opacity="0.6"/>
            <text x={tx(currentTemp)} y={PT-6} text-anchor="middle" class="ax-now">{currentTemp.toFixed(1)}°</text>
          {/if}
          <path d={fillPath(curve)} fill="url(#cg)"/>
          <path d={linePath(curve)} fill="none" stroke="var(--accent)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" filter="drop-shadow(0 0 4px rgba(0,180,255,0.3))"/>
          {#each curve as pt, i}
            <circle cx={tx(pt.temp)} cy={sy(pt.speed)} r={dragging===i?10:7}
              class="pt" class:draggable={profile==='custom'} class:active={dragging===i}
              onmousedown={(e) => startDrag(i,e)} ontouchstart={(e) => startDrag(i,e)}/>
            <text x={tx(pt.temp)} y={sy(pt.speed)-12} text-anchor="middle" class="pt-lbl">{pt.temp}° / {pt.speed}%</text>
          {/each}
        </svg>
      </div>

      {#if profile === 'custom' && curve.length > 0}
        <div class="point-chips">
          {#each [...curve].sort((a,b)=>a.temp-b.temp) as pt}
            <div class="chip">
              <span class="chip-temp">{pt.temp}°C</span>
              <i class="fa-solid fa-arrow-right chip-arrow"></i>
              <span class="chip-speed">{pt.speed}%</span>
              {#if curve.length > 2}
                <button class="chip-delete" onclick={() => removePoint(curve.indexOf(pt))} aria-label="Punkt entfernen"><i class="fa-solid fa-xmark"></i></button>
              {/if}
            </div>
          {/each}
        </div>
      {/if}
    </div>

    <!-- Seitenleiste -->
    <div class="panel panel-side">
      <div class="side-section">
        <div class="side-title"><i class="fa-solid fa-sliders"></i> Feineinstellung</div>
        <div class="slider-group">
          <div class="slider-head"><span>Hysterese</span><span class="slider-val">{settings.hysteresis || 3}°C</span></div>
          <input type="range" min="1" max="10" step="0.5" value={settings.hysteresis || 3} onchange={(e) => updSetting('hysteresis', e)} />
        </div>
        <div class="slider-group">
          <div class="slider-head"><span>Anstiegsrampe</span><span class="slider-val">{settings.ramp_up || 3} Sekunden</span></div>
          <input type="range" min="0" max="15" step="0.5" value={settings.ramp_up || 3} onchange={(e) => updSetting('ramp_up', e)} />
        </div>
        <div class="slider-group">
          <div class="slider-head"><span>Mindestdrehzahl</span><span class="slider-val">{settings.min_speed || 0}%</span></div>
          <input type="range" min="0" max="40" step="1" value={settings.min_speed || 0} onchange={(e) => updSetting('min_speed', e)} />
        </div>
      </div>

      {#if mode === 'manual'}
        <div class="side-section">
          <div class="side-title"><i class="fa-solid fa-gauge-high"></i> Manuelle Steuerung</div>
          <div class="manual-row">
            <input type="range" min="0" max="100" step="5" value={s.fan?.manual_speed || 50} oninput={(e) => s.setFanManualSpeed(parseInt(e.target.value))} />
            <span class="manual-val">{Math.round(s.fan?.manual_speed || 0)}%</span>
          </div>
        </div>
      {/if}

      <div class="side-section">
        <div class="side-title"><i class="fa-solid fa-microchip"></i> Hardware</div>
        <div class="hw-rows">
          <div class="hw-row"><span class="hw-key">Steuerung</span><span>Kernel PWM</span></div>
          <div class="hw-row"><span class="hw-key">Anschluss</span><span>GPIO Pin 6</span></div>
          <div class="hw-row">
            <span class="hw-key">Status</span>
            <span class:hw-ok={s.fan?.available} class:hw-err={!s.fan?.available}>
              {s.fan?.available ? 'Verfügbar' : 'Nicht verfügbar'}
            </span>
          </div>
        </div>
      </div>

      <!-- Modus-Auswahl -->
      <div class="side-section side-mode">
        <div class="side-title"><i class="fa-solid fa-power-off"></i> Betriebsmodus</div>
        <div class="mode-buttons">
          <button class="mode-btn" class:active={mode==='auto'} onclick={() => s.setFanMode('auto')}>
            <i class="fa-solid fa-wand-magic-sparkles"></i><span>Automatik</span>
          </button>
          <button class="mode-btn" class:active={mode==='manual'} onclick={() => s.setFanMode('manual')}>
            <i class="fa-solid fa-hand"></i><span>Manuell</span>
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
  .topbar-icon { color: var(--accent); font-size: var(--fs-lg); }

  /* ─── Modus (im Seitenpanel) ─── */
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

  /* ─── Inhalt ─── */
  .content { display: grid; grid-template-columns: 1fr 280px; gap: 12px; flex: 1; min-height: 0; }
  .panel { background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--radius); overflow: hidden; }
  .panel-graph { display: flex; flex-direction: column; padding: 14px; position: relative; }

  /* ─── Live-Anzeige (Overlay oben rechts) ─── */
  .graph-live {
    position: absolute; top: 12px; right: 14px; z-index: 2;
    display: flex; align-items: center; gap: 14px;
    padding: 8px 16px; border-radius: var(--radius-sm);
    background: rgba(10, 14, 24, 0.85); border: 1px solid var(--border);
    backdrop-filter: blur(6px);
  }
  .live-item { display: flex; flex-direction: column; align-items: center; }
  .live-label { font: 500 var(--fs-xs) var(--font); color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; }
  .live-value { font: 700 var(--fs-base) var(--mono); }
  .live-value.temp { color: var(--cyan); }
  .live-value.speed { color: var(--accent); }
  .live-value.rpm { color: var(--text-secondary); }
  .live-divider { width: 1px; height: 30px; background: var(--border); }
  .panel-side { display: flex; flex-direction: column; overflow-y: auto; }

  /* ─── Profile ─── */
  .profile-bar { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 10px; flex-shrink: 0; }
  .profile-pill {
    height: var(--h-pill); padding: 0 16px;
    background: var(--bg-deep); border: 1px solid var(--border);
    border-radius: 99px; font: 500 var(--fs-xs) var(--font);
    cursor: pointer; color: var(--text-muted); transition: all 150ms;
    display: flex; align-items: center; gap: 6px;
  }
  .profile-pill:hover { border-color: var(--text-muted); }
  .profile-pill.active { background: var(--accent-dim); border-color: var(--accent); color: var(--accent); }
  .profile-add { border-style: dashed; }

  /* ─── Graph ─── */
  .graph-wrap { flex: 1; min-height: 0; }
  .graph { width: 100%; height: 100%; display: block; }
  .ax { font: 12px var(--mono); fill: var(--text-muted); }
  .ax-now { font: 600 13px var(--mono); fill: var(--cyan); }
  .pt-lbl { font: 600 10px var(--mono); fill: var(--text-muted); }
  .pt { fill: var(--accent); stroke: var(--bg-card); stroke-width: 3; transition: r 150ms; }
  .pt.draggable { cursor: grab; } .pt.draggable:hover { r: 10; } .pt.active { fill: var(--cyan); r: 10; }

  /* ─── Punkt-Chips ─── */
  .point-chips { display: flex; gap: 6px; flex-wrap: wrap; flex-shrink: 0; margin-top: 8px; }
  .chip {
    display: flex; align-items: center; gap: 6px;
    height: var(--h-pill); padding: 0 12px; border-radius: 99px;
    background: rgba(255,255,255,0.03); border: 1px solid var(--border);
    font: 500 var(--fs-xs) var(--mono);
  }
  .chip-temp { color: var(--cyan); }
  .chip-arrow { font-size: var(--fs-xs); color: var(--text-muted); }
  .chip-speed { color: var(--accent); }
  .chip-delete {
    background: none; border: none; color: var(--text-muted);
    cursor: pointer; font-size: var(--fs-xs); padding: 0 0 0 4px;
    display: flex; align-items: center;
  }
  .chip-delete:hover { color: var(--red); }

  /* ─── Seitenleiste ─── */
  .side-section { padding: 16px 18px; border-bottom: 1px solid var(--border); }
  .side-section:last-child { border-bottom: none; }
  .side-title {
    font: 600 var(--fs-sm) var(--font); color: var(--text-secondary);
    margin-bottom: 14px; display: flex; align-items: center; gap: 8px;
  }
  .side-title i { color: var(--accent); font-size: var(--fs-sm); }

  .slider-group { margin-bottom: 14px; }
  .slider-group:last-child { margin-bottom: 0; }
  .slider-head {
    display: flex; justify-content: space-between; align-items: center;
    font: 500 var(--fs-sm) var(--font); color: var(--text-secondary);
    margin-bottom: 8px;
  }
  .slider-val {
    font: 500 var(--fs-xs) var(--mono); color: var(--text-muted);
    background: var(--bg-deep); padding: 3px 10px; border-radius: var(--radius-sm);
  }

  .manual-row { display: flex; align-items: center; gap: 14px; }
  .manual-row input { flex: 1; }
  .manual-val { font: 700 var(--fs-lg) var(--mono); color: var(--accent); min-width: 56px; text-align: right; }

  .hw-rows { display: flex; flex-direction: column; gap: 8px; }
  .hw-row {
    display: flex; justify-content: space-between;
    font: 500 var(--fs-sm) var(--font); color: var(--text-secondary);
    padding: 3px 0;
  }
  .hw-key { color: var(--text-muted); }
  .hw-ok { color: var(--green); }
  .hw-err { color: var(--red); }

  /* ─── Responsive ─── */
  @media (max-width: 900px) {
    .content { grid-template-columns: 1fr; }
    .graph-live { position: static; margin-bottom: 10px; justify-content: center; background: var(--bg-elevated); }
  }
  @media (max-width: 600px) {
    .mode-btn span { display: none; }
  }
</style>
