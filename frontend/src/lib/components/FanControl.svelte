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
    const s = [...pts].sort((a, b) => a.temp - b.temp);
    return s.map((p, i) => `${i ? 'L' : 'M'}${tx(p.temp).toFixed(1)},${sy(p.speed).toFixed(1)}`).join(' ');
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

  const profLbl = { silent: '🤫 Silent', balanced: '⚖️ Balanced', performance: '🚀 Performance', night: '🌙 Night', custom: '🔧 Custom' };
  const tempTicks = [30, 40, 50, 60, 70, 80];
  const spdTicks = [0, 25, 50, 75, 100];
</script>

<div class="page">
  <div class="sh"><div class="st">Fan Control</div><div class="sd">Lüftersteuerung mit Kurveneditor · PWM 4-Stufen</div></div>

  <div class="mode-bar">
    <button class="mbtn" class:act={mode==='auto'} onclick={() => s.setFanMode('auto')}>⟳ Automatik</button>
    <button class="mbtn" class:act={mode==='manual'} onclick={() => s.setFanMode('manual')}>✋ Manuell</button>
    <button class="mbtn" class:act={mode==='off'} onclick={() => s.setFanMode('off')}>⏸ Aus</button>
  </div>

  <!-- Kurven-Editor -->
  <div class="card">
    <div class="ch">
      <div class="ct">📈 KURVEN-EDITOR</div>
      <div class="ci">
        <span class="vc">{currentTemp.toFixed(1)}°C</span> → <span class="va">{Math.round(currentSpeed)}%</span>
        {#if estimatedRpm > 0}<span class="vm"> · {estimatedRpm} RPM</span>{/if}
      </div>
    </div>
    <div class="cb">
      <div class="profs">
        {#each profiles as p}
          <button class="ppill" class:act={profile===p} onclick={() => selectProfile(p)}>{profLbl[p]||p}</button>
        {/each}
      </div>

      {#if profile === 'custom'}
        <div class="hint">Punkte ziehen zum Bearbeiten · Doppelklick auf Linie für neuen Punkt</div>
      {/if}

      <div class="gw">
        <svg bind:this={svgEl} viewBox="0 0 {W} {H}" class="fg">
          <defs>
            <linearGradient id="cg" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stop-color="var(--accent,#6366f1)" stop-opacity="0.3"/>
              <stop offset="100%" stop-color="var(--accent,#6366f1)" stop-opacity="0"/>
            </linearGradient>
          </defs>
          <!-- Grid -->
          <line x1={PL} y1={PT} x2={PL} y2={PT+GH} stroke="rgba(99,130,255,0.08)"/>
          <line x1={PL} y1={PT+GH} x2={PL+GW} y2={PT+GH} stroke="rgba(99,130,255,0.08)"/>
          {#each spdTicks as sp}
            <line x1={PL} y1={sy(sp)} x2={PL+GW} y2={sy(sp)} stroke="rgba(99,130,255,0.05)" stroke-dasharray="4"/>
            <text x={PL-10} y={sy(sp)+4} text-anchor="end" class="al">{sp}%</text>
          {/each}
          {#each tempTicks as t}
            <line x1={tx(t)} y1={PT} x2={tx(t)} y2={PT+GH} stroke="rgba(99,130,255,0.03)" stroke-dasharray="2"/>
            <text x={tx(t)} y={PT+GH+18} text-anchor="middle" class="al">{t}°C</text>
          {/each}
          <!-- Current temp line -->
          {#if currentTemp > TMIN}
            <line x1={tx(currentTemp)} y1={PT} x2={tx(currentTemp)} y2={PT+GH} stroke="var(--cyan,#22d3ee)" stroke-width="1.5" stroke-dasharray="6 4" opacity="0.7"/>
            <text x={tx(currentTemp)} y={PT-8} text-anchor="middle" class="tl">{currentTemp.toFixed(1)}°C</text>
          {/if}
          <!-- Curve -->
          <path d={fillPath(curve)} fill="url(#cg)"/>
          <path d={linePath(curve)} fill="none" stroke="var(--accent,#6366f1)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" class="cl"/>
          <!-- Points -->
          {#each curve as pt, i}
            <circle cx={tx(pt.temp)} cy={sy(pt.speed)} r={dragging===i?10:7} class="cp" class:drag={profile==='custom'} class:active={dragging===i}
              role="slider" aria-label="Punkt {pt.temp}°C → {pt.speed}%" aria-valuenow={pt.speed} tabindex="0"
              onmousedown={(e) => startDrag(i,e)} ontouchstart={(e) => startDrag(i,e)}/>
            <text x={tx(pt.temp)} y={sy(pt.speed)-14} text-anchor="middle" class="plbl">{pt.temp}°/{pt.speed}%</text>
          {/each}
        </svg>
      </div>

      {#if profile === 'custom'}
        <div class="point-actions">
          <button class="btn-sm" onclick={addPoint}>+ Punkt hinzufügen</button>
          <span class="pt-count">{curve.length} Punkte</span>
        </div>
        <div class="point-list">
          {#each [...curve].sort((a,b)=>a.temp-b.temp) as pt, i}
            <div class="pt-item">
              <span class="pt-temp">{pt.temp}°C</span>
              <span class="pt-arrow">→</span>
              <span class="pt-speed">{pt.speed}%</span>
              {#if curve.length > 2}
                <button class="pt-del" onclick={() => removePoint(curve.indexOf(pt))}>×</button>
              {/if}
            </div>
          {/each}
        </div>
      {/if}

      <div class="srow">
        <div class="sg"><div class="shead"><span>Hysterese</span><span class="sv">{settings.hysteresis||3}°C</span></div>
          <input type="range" min="1" max="10" step="0.5" value={settings.hysteresis||3} onchange={(e)=>updSetting('hysteresis',e)}/></div>
        <div class="sg"><div class="shead"><span>Rampe (Anstieg)</span><span class="sv">{settings.ramp_up||3}s</span></div>
          <input type="range" min="0" max="15" step="0.5" value={settings.ramp_up||3} onchange={(e)=>updSetting('ramp_up',e)}/></div>
        <div class="sg"><div class="shead"><span>Min. Drehzahl</span><span class="sv">{settings.min_speed||0}%</span></div>
          <input type="range" min="0" max="40" step="1" value={settings.min_speed||0} onchange={(e)=>updSetting('min_speed',e)}/></div>
      </div>
    </div>
  </div>

  {#if mode === 'manual'}
    <div class="card">
      <div class="ch"><div class="ct">🎛️ MANUELLE GESCHWINDIGKEIT</div><span class="va" style="font-size:18px;font-weight:700">{Math.round(s.fan?.manual_speed||0)}%</span></div>
      <div class="cb"><input type="range" min="0" max="100" step="5" value={s.fan?.manual_speed||50} oninput={(e) => s.setFanManualSpeed(parseInt(e.target.value))}/></div>
    </div>
  {/if}

  <div class="card">
    <div class="ch"><div class="ct">🔧 HARDWARE</div></div>
    <div class="cb">
      <div class="hwg">
        <div class="hwi"><span class="hwl">Typ</span>Kernel PWM</div>
        <div class="hwi"><span class="hwl">GPIO</span>Pin 6</div>
        <div class="hwi"><span class="hwl">Verfügbar</span>{s.fan?.available?'✅ Ja':'❌ Nein'}</div>
        <div class="hwi"><span class="hwl">Ist-Speed</span>{currentSpeed.toFixed(0)}% → {estimatedRpm} RPM</div>
      </div>
    </div>
  </div>
</div>

<style>
  .page{display:flex;flex-direction:column;gap:18px}
  .sh{margin-bottom:4px} .st{font-size:24px;font-weight:800;letter-spacing:-0.5px} .sd{color:var(--text-muted);font-size:14px}
  .mode-bar{display:flex;gap:8px}
  .mbtn{flex:1;padding:10px;border-radius:10px;border:1px solid var(--border);background:var(--bg-surface,rgba(255,255,255,0.02));color:var(--text-secondary);font:500 13px/1 inherit;cursor:pointer;transition:all 0.2s}
  .mbtn:hover{border-color:var(--text-muted)} .mbtn.act{background:var(--accent-dim,rgba(99,102,241,0.1));border-color:var(--accent);color:var(--accent)}
  .card{background:var(--bg-surface,#111827);border:1px solid var(--border);border-radius:16px}
  .card:hover{border-color:rgba(99,130,255,0.25)}
  .ch{padding:18px 22px 0;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px}
  .ct{font:600 13px/1 inherit;text-transform:uppercase;letter-spacing:0.8px;color:var(--text-secondary)}
  .cb{padding:16px 22px 22px}
  .ci{font:12px var(--mono,monospace);color:var(--text-muted)}
  .vc{color:var(--cyan,#22d3ee);font-weight:600} .va{color:var(--accent,#6366f1);font-weight:600} .vm{color:var(--text-muted)}
  .profs{display:flex;gap:8px;margin-bottom:16px;flex-wrap:wrap}
  .ppill{padding:7px 16px;background:var(--bg-deep,#0d1220);border:1px solid var(--border);border-radius:20px;font:500 12px/1 inherit;cursor:pointer;color:var(--text-secondary);transition:all 0.2s}
  .ppill:hover{border-color:var(--text-muted)} .ppill.act{background:var(--accent-dim,rgba(99,102,241,0.1));border-color:var(--accent);color:var(--accent)}
  .hint{font:11px inherit;color:var(--accent,#6366f1);opacity:0.7;margin-bottom:8px}
  .gw{background:var(--bg-deep,#0d1220);border-radius:12px;padding:12px;margin-bottom:16px}
  .fg{width:100%;display:block}
  .al{font:10px var(--mono,monospace);fill:var(--text-muted,#4a5568)}
  .tl{font:600 11px var(--mono,monospace);fill:var(--cyan,#22d3ee)}
  .plbl{font:600 9px var(--mono,monospace);fill:var(--text-muted,#4a5568)}
  .cl{filter:drop-shadow(0 0 6px rgba(99,102,241,0.35))}
  .cp{fill:var(--accent,#6366f1);stroke:var(--bg-surface,#111827);stroke-width:3;transition:r 0.15s;filter:drop-shadow(0 0 6px rgba(99,102,241,0.35))}
  .cp.drag{cursor:grab} .cp.drag:hover{r:10} .cp.active{fill:var(--cyan,#22d3ee);r:10}
  .point-actions{display:flex;align-items:center;gap:12px;margin-bottom:12px}
  .btn-sm{padding:6px 14px;border-radius:8px;border:1px solid var(--accent);background:var(--accent-dim);color:var(--accent);font:500 12px inherit;cursor:pointer}
  .btn-sm:hover{background:var(--accent);color:#fff}
  .pt-count{font:11px var(--mono,monospace);color:var(--text-muted)}
  .point-list{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:16px}
  .pt-item{display:flex;align-items:center;gap:4px;padding:4px 8px;border-radius:6px;background:rgba(255,255,255,0.03);border:1px solid var(--border);font:11px var(--mono,monospace)}
  .pt-temp{color:var(--cyan,#22d3ee)} .pt-arrow{color:var(--text-muted)} .pt-speed{color:var(--accent)}
  .pt-del{width:18px;height:18px;border-radius:4px;border:none;background:transparent;color:var(--text-muted);cursor:pointer;font-size:12px;display:flex;align-items:center;justify-content:center;margin-left:4px}
  .pt-del:hover{background:rgba(239,68,68,0.1);color:#ef4444}
  .srow{display:flex;gap:20px}
  .sg{flex:1} .shead{display:flex;justify-content:space-between;margin-bottom:8px;font-size:12px;color:var(--text-secondary)}
  .sv{font-family:var(--mono,monospace);color:var(--text-muted);background:var(--bg-deep,#0d1220);padding:2px 8px;border-radius:4px}
  input[type="range"]{-webkit-appearance:none;width:100%;height:6px;background:var(--bg-deep,#0d1220);border-radius:3px;outline:none}
  input[type="range"]::-webkit-slider-thumb{-webkit-appearance:none;width:16px;height:16px;border-radius:50%;background:var(--accent,#6366f1);cursor:pointer;box-shadow:0 0 8px rgba(99,102,241,0.4)}
  .hwg{display:grid;grid-template-columns:repeat(4,1fr);gap:12px} .hwi{font:12px var(--mono,monospace)}
  .hwl{display:block;font-size:10px;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.5px;margin-bottom:2px}
</style>
