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

  const W = 600, H = 250, PL = 50, PR = 20, PT = 30, PB = 35;
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
    const svgX = (cx - rect.left) * (W / rect.width);
    const svgY = (cy - rect.top) * (H / rect.height);
    const pts = [...curve]; pts[dragging] = { temp: xt(svgX), speed: ys(svgY) };
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
    const newTemp = Math.round((TMIN + TMAX) / 2);
    pts.push({ temp: newTemp, speed: 50 });
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
  const profLabels = { silent: 'Silent', balanced: 'Balanced', performance: 'Performance', night: 'Night', custom: 'Custom' };
  const tempTicks = [30, 40, 50, 60, 70, 80];
  const spdTicks = [0, 25, 50, 75, 100];
</script>

<div class="page">
  <div class="page-head">
    <h1><i class="fa-solid fa-fan"></i> Lüftersteuerung</h1>
    <p class="sub">Kurveneditor · PWM 4-Stufen</p>
  </div>

  <!-- Modus-Auswahl -->
  <div class="mode-bar">
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

  <!-- Kurven-Editor -->
  <div class="card">
    <div class="card-header">
      <div class="card-title"><i class="fa-solid fa-chart-line"></i> Kurven-Editor</div>
      <div class="card-info">
        <span class="temp-val">{currentTemp.toFixed(1)}°C</span>
        <i class="fa-solid fa-arrow-right" style="color:var(--text-muted);font-size:10px"></i>
        <span class="speed-val">{Math.round(currentSpeed)}%</span>
        {#if estimatedRpm > 0}<span class="rpm-val"> · {estimatedRpm} RPM</span>{/if}
      </div>
    </div>

    <!-- Profil-Auswahl -->
    <div class="profile-bar">
      {#each profiles as p}
        <button class="profile-pill" class:active={profile===p} onclick={() => selectProfile(p)}>
          <i class="fa-solid {profIcons[p] || 'fa-circle'}"></i> {profLabels[p] || p}
        </button>
      {/each}
    </div>

    {#if profile === 'custom'}
      <div class="hint"><i class="fa-solid fa-circle-info"></i> Punkte ziehen zum Bearbeiten</div>
    {/if}

    <!-- SVG Graph -->
    <div class="graph-wrap">
      <svg bind:this={svgEl} viewBox="0 0 {W} {H}" class="graph">
        <defs>
          <linearGradient id="curve-grad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="var(--accent)" stop-opacity="0.3"/>
            <stop offset="100%" stop-color="var(--accent)" stop-opacity="0"/>
          </linearGradient>
        </defs>
        <line x1={PL} y1={PT} x2={PL} y2={PT+GH} stroke="rgba(0,180,255,0.08)"/>
        <line x1={PL} y1={PT+GH} x2={PL+GW} y2={PT+GH} stroke="rgba(0,180,255,0.08)"/>
        {#each spdTicks as sp}
          <line x1={PL} y1={sy(sp)} x2={PL+GW} y2={sy(sp)} stroke="rgba(0,180,255,0.05)" stroke-dasharray="4"/>
          <text x={PL-10} y={sy(sp)+4} text-anchor="end" class="axis-label">{sp}%</text>
        {/each}
        {#each tempTicks as t}
          <line x1={tx(t)} y1={PT} x2={tx(t)} y2={PT+GH} stroke="rgba(0,180,255,0.03)" stroke-dasharray="2"/>
          <text x={tx(t)} y={PT+GH+18} text-anchor="middle" class="axis-label">{t}°C</text>
        {/each}
        {#if currentTemp > TMIN}
          <line x1={tx(currentTemp)} y1={PT} x2={tx(currentTemp)} y2={PT+GH} stroke="var(--cyan)" stroke-width="1.5" stroke-dasharray="6 4" opacity="0.7"/>
          <text x={tx(currentTemp)} y={PT-8} text-anchor="middle" class="temp-label">{currentTemp.toFixed(1)}°C</text>
        {/if}
        <path d={fillPath(curve)} fill="url(#curve-grad)"/>
        <path d={linePath(curve)} fill="none" stroke="var(--accent)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" class="curve-line"/>
        {#each curve as pt, i}
          <circle cx={tx(pt.temp)} cy={sy(pt.speed)} r={dragging===i?10:7} class="point" class:draggable={profile==='custom'} class:active={dragging===i}
            role="slider" aria-label="Punkt {pt.temp}°C → {pt.speed}%" aria-valuenow={pt.speed} tabindex="0"
            onmousedown={(e) => startDrag(i,e)} ontouchstart={(e) => startDrag(i,e)}/>
          <text x={tx(pt.temp)} y={sy(pt.speed)-14} text-anchor="middle" class="point-label">{pt.temp}°/{pt.speed}%</text>
        {/each}
      </svg>
    </div>

    {#if profile === 'custom'}
      <div class="point-actions">
        <button class="btn btn-accent btn-sm" onclick={addPoint}><i class="fa-solid fa-plus"></i> Punkt</button>
        <span class="point-count">{curve.length} Punkte</span>
      </div>
      <div class="point-list">
        {#each [...curve].sort((a,b)=>a.temp-b.temp) as pt, i}
          <div class="point-item">
            <span class="pt-temp">{pt.temp}°C</span>
            <i class="fa-solid fa-arrow-right" style="color:var(--text-muted);font-size:9px"></i>
            <span class="pt-speed">{pt.speed}%</span>
            {#if curve.length > 2}
              <button class="pt-del" onclick={() => removePoint(curve.indexOf(pt))}><i class="fa-solid fa-xmark"></i></button>
            {/if}
          </div>
        {/each}
      </div>
    {/if}

    <!-- Feineinstellungen -->
    <div class="settings-row">
      <div class="setting">
        <div class="setting-head"><span>Hysterese</span><span class="setting-val">{settings.hysteresis||3}°C</span></div>
        <input type="range" min="1" max="10" step="0.5" value={settings.hysteresis||3} onchange={(e)=>updSetting('hysteresis',e)}/>
      </div>
      <div class="setting">
        <div class="setting-head"><span>Rampe (Anstieg)</span><span class="setting-val">{settings.ramp_up||3}s</span></div>
        <input type="range" min="0" max="15" step="0.5" value={settings.ramp_up||3} onchange={(e)=>updSetting('ramp_up',e)}/>
      </div>
      <div class="setting">
        <div class="setting-head"><span>Min. Drehzahl</span><span class="setting-val">{settings.min_speed||0}%</span></div>
        <input type="range" min="0" max="40" step="1" value={settings.min_speed||0} onchange={(e)=>updSetting('min_speed',e)}/>
      </div>
    </div>
  </div>

  <!-- Manuelle Geschwindigkeit -->
  {#if mode === 'manual'}
    <div class="card">
      <div class="card-header">
        <div class="card-title"><i class="fa-solid fa-sliders"></i> Manuelle Geschwindigkeit</div>
        <span class="speed-val" style="font-size:18px;font-weight:700">{Math.round(s.fan?.manual_speed||0)}%</span>
      </div>
      <input type="range" min="0" max="100" step="5" value={s.fan?.manual_speed||50} oninput={(e) => s.setFanManualSpeed(parseInt(e.target.value))}/>
    </div>
  {/if}

  <!-- Hardware-Info -->
  <div class="card">
    <div class="card-header">
      <div class="card-title"><i class="fa-solid fa-microchip"></i> Hardware</div>
    </div>
    <div class="hw-grid">
      <div class="hw-item"><span class="hw-label">Typ</span>Kernel PWM</div>
      <div class="hw-item"><span class="hw-label">GPIO</span>Pin 6</div>
      <div class="hw-item"><span class="hw-label">Verfügbar</span><span class:text-green={s.fan?.available} class:text-red={!s.fan?.available}>{s.fan?.available ? 'Ja' : 'Nein'}</span></div>
      <div class="hw-item"><span class="hw-label">Ist-Speed</span>{currentSpeed.toFixed(0)}% → {estimatedRpm} RPM</div>
    </div>
  </div>
</div>

<style>
  .page { display: flex; flex-direction: column; gap: 18px; }
  .page-head h1 { display: flex; align-items: center; gap: 10px; font-size: 22px; }
  .page-head h1 i { color: var(--accent); }
  .sub { color: var(--text-muted); font-size: 13px; margin-top: 2px; }

  .mode-bar { display: flex; gap: 8px; }
  .mode-btn {
    flex: 1; padding: 10px; border-radius: var(--radius);
    border: 1px solid var(--border); background: var(--bg-surface);
    color: var(--text-secondary); font: 500 13px/1 var(--font);
    cursor: pointer; transition: all 0.2s; display: flex; align-items: center; justify-content: center; gap: 8px;
  }
  .mode-btn:hover { border-color: var(--text-muted); }
  .mode-btn.active { background: var(--accent-dim); border-color: var(--accent); color: var(--accent); }

  .card-title { font: 600 12px/1 var(--font); text-transform: uppercase; letter-spacing: 0.08em; color: var(--text-secondary); display: flex; align-items: center; gap: 8px; }
  .card-title i { color: var(--accent); font-size: 14px; }
  .card-info { font: 12px var(--mono); color: var(--text-muted); display: flex; align-items: center; gap: 6px; }
  .temp-val { color: var(--cyan); font-weight: 600; }
  .speed-val { color: var(--accent); font-weight: 600; }
  .rpm-val { color: var(--text-muted); }

  .profile-bar { display: flex; gap: 8px; margin-bottom: 16px; flex-wrap: wrap; }
  .profile-pill {
    padding: 7px 16px; background: var(--bg-deep); border: 1px solid var(--border);
    border-radius: 20px; font: 500 12px/1 var(--font); cursor: pointer;
    color: var(--text-secondary); transition: all 0.2s; display: flex; align-items: center; gap: 6px;
  }
  .profile-pill:hover { border-color: var(--text-muted); }
  .profile-pill.active { background: var(--accent-dim); border-color: var(--accent); color: var(--accent); }

  .hint { font: 11px var(--font); color: var(--accent); opacity: 0.7; margin-bottom: 8px; display: flex; align-items: center; gap: 6px; }

  .graph-wrap { background: var(--bg-deep); border-radius: 12px; padding: 12px; margin-bottom: 16px; }
  .graph { width: 100%; display: block; }
  .axis-label { font: 10px var(--mono); fill: var(--text-muted); }
  .temp-label { font: 600 11px var(--mono); fill: var(--cyan); }
  .point-label { font: 600 9px var(--mono); fill: var(--text-muted); }
  .curve-line { filter: drop-shadow(0 0 6px rgba(0,180,255,0.35)); }
  .point { fill: var(--accent); stroke: var(--bg-surface); stroke-width: 3; transition: r 0.15s; filter: drop-shadow(0 0 6px rgba(0,180,255,0.35)); }
  .point.draggable { cursor: grab; } .point.draggable:hover { r: 10; } .point.active { fill: var(--cyan); r: 10; }

  .point-actions { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }
  .point-count { font: 11px var(--mono); color: var(--text-muted); }
  .point-list { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 16px; }
  .point-item { display: flex; align-items: center; gap: 4px; padding: 4px 8px; border-radius: 6px; background: rgba(255,255,255,0.03); border: 1px solid var(--border); font: 11px var(--mono); }
  .pt-temp { color: var(--cyan); } .pt-speed { color: var(--accent); }
  .pt-del { width: 18px; height: 18px; border-radius: 4px; border: none; background: transparent; color: var(--text-muted); cursor: pointer; font-size: 10px; display: flex; align-items: center; justify-content: center; margin-left: 4px; }
  .pt-del:hover { background: rgba(255,64,96,0.1); color: var(--red); }

  .settings-row { display: flex; gap: 20px; }
  .setting { flex: 1; }
  .setting-head { display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 12px; color: var(--text-secondary); }
  .setting-val { font-family: var(--mono); color: var(--text-muted); background: var(--bg-deep); padding: 2px 8px; border-radius: 4px; }

  .hw-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
  .hw-item { font: 12px var(--mono); }
  .hw-label { display: block; font-size: 10px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 2px; }
  .text-green { color: var(--green); }
  .text-red { color: var(--red); }

  @media (max-width: 768px) {
    .mode-bar { flex-direction: column; }
    .settings-row { flex-direction: column; gap: 12px; }
    .hw-grid { grid-template-columns: 1fr 1fr; }
  }
</style>
