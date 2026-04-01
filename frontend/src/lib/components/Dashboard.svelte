<script>
  let { state: s } = $props();

  function tempCol(t) { return t < 45 ? 'var(--green,#34d399)' : t < 60 ? 'var(--amber,#fb923c)' : 'var(--red,#f87171)'; }
  function diskCol(p) { return p < 70 ? 'var(--accent,#6366f1)' : p < 90 ? 'var(--amber,#fb923c)' : 'var(--red,#f87171)'; }
  function fmt(gb) { return gb >= 1000 ? `${(gb/1000).toFixed(1)} TB` : gb >= 100 ? `${Math.round(gb)} GB` : `${gb.toFixed(1)} GB`; }
  function fmtBps(b) {
    if (b > 1048576) return `${(b/1048576).toFixed(1)} MB/s`;
    if (b > 1024) return `${(b/1024).toFixed(1)} KB/s`;
    return `${Math.round(b)} B/s`;
  }
  function ledColor(led, br) {
    const b = Math.pow((br || 50) / 1000, 0.6);
    return `rgb(${Math.round((led?.r||0)*b)},${Math.round((led?.g||0)*b)},${Math.round((led?.b||0)*b)})`;
  }
  function ledGlow(led, br) {
    const b = Math.pow((br || 50) / 1000, 0.6);
    return `rgba(${Math.round((led?.r||0)*b)},${Math.round((led?.g||0)*b)},${Math.round((led?.b||0)*b)},0.5)`;
  }
  const fanCols = ['var(--text-muted)', 'var(--green,#34d399)', 'var(--amber,#fb923c)', 'var(--red,#f87171)'];
  function spark(arr, w, h) {
    if (!arr || arr.length < 2) return '';
    const max = Math.max(...arr, 1);
    const step = w / (arr.length - 1);
    return arr.map((v, i) => `${i ? 'L' : 'M'}${(i * step).toFixed(1)},${(h - (v / max) * h * 0.9).toFixed(1)}`).join(' ');
  }
  function tempHistPath(arr, w, h) {
    if (!arr || arr.length < 2) return { line: '', area: '' };
    const min = Math.min(...arr) - 5, max = Math.max(...arr) + 5;
    const range = max - min || 1;
    const step = w / (arr.length - 1);
    const pts = arr.map((v, i) => ({ x: i * step, y: h - ((v - min) / range) * h }));
    const line = pts.map((p, i) => `${i ? 'L' : 'M'}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ');
    const area = `${line} L${pts[pts.length-1].x.toFixed(1)},${h} L0,${h} Z`;
    return { line, area };
  }
</script>

<div class="page">
  <div class="sh">
    <div class="st">Dashboard</div>
    <div class="sd">System-Übersicht · Uptime {s.stats?.uptime?.formatted || '-'} · {s.stats?.network?.ip || ''}</div>
  </div>

  <div class="grid4">
    <div class="card">
      <div class="ch"><span class="ct">🌡️ CPU TEMP</span><span class="badge-live">LIVE</span></div>
      <div class="cb">
        <div class="stat-big" style="color:{tempCol(s.stats?.cpu?.temp||0)}">{(s.stats?.cpu?.temp||0).toFixed(1)}<span class="su">°C</span></div>
        <div class="stat-sub">Min: {s.stats?.cpu?.temp_min||0}° · Max: {s.stats?.cpu?.temp_max||0}°</div>
        <svg class="sparkline" viewBox="0 0 200 40" preserveAspectRatio="none">
          <path d={spark(s.stats?.history?.temp||[], 200, 40)} fill="none" stroke="var(--cyan,#22d3ee)" stroke-width="1.5" opacity="0.8"/>
        </svg>
      </div>
    </div>
    <div class="card">
      <div class="ch"><span class="ct">⚡ CPU</span><span class="badge-live">LIVE</span></div>
      <div class="cb">
        <div class="stat-big" style="color:var(--accent,#6366f1)">{(s.stats?.cpu?.percent||0).toFixed(1)}<span class="su">%</span></div>
        <div class="stat-sub">{s.stats?.cpu?.cores||4} Cores · ARM Cortex-A76</div>
        <svg class="sparkline" viewBox="0 0 200 40" preserveAspectRatio="none">
          <path d={spark(s.stats?.history?.cpu||[], 200, 40)} fill="none" stroke="var(--accent,#6366f1)" stroke-width="1.5" opacity="0.8"/>
        </svg>
      </div>
    </div>
    <div class="card">
      <div class="ch"><span class="ct">🧠 RAM</span></div>
      <div class="cb">
        <div class="stat-big" style="color:var(--green,#34d399)">{s.stats?.ram?.used_gb||0}<span class="su">GB</span></div>
        <div class="stat-sub">von {s.stats?.ram?.total_gb||0} GB · {s.stats?.ram?.percent||0}%</div>
        <div class="pbar"><div class="pfill" style="width:{s.stats?.ram?.percent||0}%;background:linear-gradient(90deg,var(--green,#34d399),var(--cyan,#22d3ee))"></div></div>
      </div>
    </div>
    <div class="card">
      <div class="ch"><span class="ct">💾 SPEICHER</span><span class="badge-info">{(s.stats?.disks||[]).length}</span></div>
      <div class="cb">
        {#if (s.stats?.disks||[]).length > 0}
          {#each s.stats.disks as d}
            <div class="disk-entry">
              <div class="stat-big" style="color:var(--amber,#fb923c)">{fmt(d.used_gb)}<span class="su"> / {fmt(d.total_gb)}</span></div>
              <div class="stat-sub">{d.label} · {d.mount} · {d.percent}%</div>
              <div class="pbar"><div class="pfill" style="width:{d.percent}%;background:linear-gradient(90deg,var(--amber,#fb923c),var(--yellow,#fbbf24))"></div></div>
            </div>
          {/each}
        {:else}<div class="stat-sub">Keine Disks</div>{/if}
      </div>
    </div>
  </div>

  {#if (s.stats?.disks||[]).length > 1}
    <div class="section"><div class="stitle">Alle Festplatten</div>
      <div class="grid3">
        {#each (s.stats?.disks||[]) as disk}
          <div class="ditem">
            <div class="dhead"><span class="dname">{disk.label}</span><span class="dpct" style="color:{diskCol(disk.percent)}">{disk.percent}%</span></div>
            <div class="dbar-bg"><div class="dbar" style="width:{disk.percent}%;background:{diskCol(disk.percent)}"></div></div>
            <div class="dinfo"><span>{fmt(disk.used_gb)} / {fmt(disk.total_gb)}</span><span>{fmt(disk.available_gb)} frei</span></div>
            <div class="dmeta">{disk.model||disk.device} · {disk.fstype} · {disk.mount}</div>
          </div>
        {/each}
      </div>
    </div>
  {/if}

  <div class="grid2">
    <div class="card">
      <div class="ch"><span class="ct">🐳 DOCKER</span><span class="badge-info">{s.stats?.docker?.running||0}/{s.stats?.docker?.total||0} aktiv</span></div>
      <div class="cb">
        {#if (s.stats?.docker?.containers||[]).length > 0}
          <div class="docker-grid">
            {#each (s.stats?.docker?.containers||[]) as c}
              <div class="docker-cell" title="{c.name}" style="background:{c.status==='running'?'var(--green,#34d399)':'var(--amber,#fb923c)'}"></div>
            {/each}
          </div>
          <div class="docker-list">
            {#each (s.stats?.docker?.containers||[]) as c}
              <div class="dl-row">
                <span class="dl-dot" class:on={c.status==='running'}></span>
                <span class="dl-name">{c.name}</span>
                <span class="dl-port">{c.ports||''}</span>
              </div>
            {/each}
          </div>
        {:else}
          <div class="no-data">Keine Container erkannt</div>
          <div class="debug-hint">Prüfe: docker.sock Mount + docker SDK</div>
        {/if}
      </div>
    </div>
    <div class="card">
      <div class="ch"><span class="ct">🌐 NETZWERK</span><span class="badge-sm">{s.stats?.network?.interface||'?'}</span></div>
      <div class="cb">
        <div class="net-stats">
          <div><div class="net-label">↓ DOWNLOAD</div><div class="net-val" style="color:var(--green,#34d399)">{fmtBps(s.stats?.network?.rx_bytes_sec||0)}</div></div>
          <div><div class="net-label">↑ UPLOAD</div><div class="net-val" style="color:var(--cyan,#22d3ee)">{fmtBps(s.stats?.network?.tx_bytes_sec||0)}</div></div>
          <div><div class="net-label">UPTIME</div><div class="net-val">{s.stats?.uptime?.formatted||'?'}</div></div>
        </div>
        <svg class="sparkline" viewBox="0 0 300 40" preserveAspectRatio="none" style="margin-top:12px">
          <path d={spark(s.stats?.history?.net_rx||[], 300, 40)} fill="none" stroke="var(--green,#34d399)" stroke-width="1.5" opacity="0.7"/>
          <path d={spark(s.stats?.history?.net_tx||[], 300, 40)} fill="none" stroke="var(--cyan,#22d3ee)" stroke-width="1" opacity="0.5"/>
        </svg>
        <div class="net-ip">{s.stats?.network?.interface||'?'} · {s.stats?.network?.ip||'N/A'}</div>
      </div>
    </div>
  </div>

  <div class="card full">
    <div class="ch"><span class="ct">📈 TEMPERATUR-VERLAUF</span></div>
    <div class="cb">
      {#if true}
      {@const hist = s.stats?.history?.temp || []}
      {@const paths = tempHistPath(hist, 800, 120)}
      <div class="temp-graph">
        <svg width="100%" height="100%" viewBox="0 0 800 120" preserveAspectRatio="none">
          <defs><linearGradient id="tg" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="var(--cyan,#22d3ee)" stop-opacity="0.3"/><stop offset="100%" stop-color="var(--cyan,#22d3ee)" stop-opacity="0"/></linearGradient></defs>
          <path d={paths.area} fill="url(#tg)"/>
          <path d={paths.line} fill="none" stroke="var(--cyan,#22d3ee)" stroke-width="2" stroke-linecap="round" class="glow-line"/>
        </svg>
        <div class="temp-now">{(s.stats?.cpu?.temp||0).toFixed(1)}°C</div>
      </div>
      {/if}
    </div>
  </div>

  <div class="grid3">
    <div class="card">
      <div class="ch"><span class="ct">⟳ Lüfter</span><span class="badge-sm" class:badge-ok={s.fanActive}>{s.stats?.fan?.level_name||'Aus'}</span></div>
      <div class="cb">
        <div class="fan-bars">{#each [0,1,2,3] as lvl}<div class="fan-seg" style="background:{lvl<=(s.stats?.fan?.pwm_level||0)&&(s.stats?.fan?.pwm_level||0)>0?fanCols[s.stats?.fan?.pwm_level||0]:'rgba(255,255,255,0.05)'}"></div>{/each}</div>
        <div class="cmeta"><span>Stufe {s.stats?.fan?.pwm_level||0}/3</span><span>{s.stats?.fan?.rpm||0} RPM</span></div>
      </div>
    </div>
    <div class="card">
      <div class="ch"><span class="ct">◈ LEDs</span><span class="badge-sm" class:badge-ok={s.ledsActive}>{s.leds?.effect||'off'}</span></div>
      <div class="cb">
        <div class="led-row">
          {#each (s.leds?.led_states||[{r:0,g:0,b:0},{r:0,g:0,b:0},{r:0,g:0,b:0},{r:0,g:0,b:0}]) as led}
            <div class="led-dot" style="background:{ledColor(led,s.leds?.brightness)};box-shadow:0 0 12px {ledGlow(led,s.leds?.brightness)},0 0 24px {ledGlow(led,s.leds?.brightness)}"></div>
          {/each}
        </div>
        <div class="cmeta"><span>Helligkeit: {s.leds?.brightness||0}</span><span>Speed: {s.leds?.speed||50}</span></div>
      </div>
    </div>
    <div class="card">
      <div class="ch"><span class="ct">▣ OLED</span><span class="badge-sm" class:badge-ok={s.oledActive}>{s.oled?.mode||'off'}</span></div>
      <div class="cb">
        <div class="oled-wrap">
          <div class="oled-bezel"><div class="oled-screen">
            {#if s.oled?.preview}<img src="data:image/png;base64,{s.oled.preview}" alt="OLED" class="oled-img"/>
            {:else}<div class="oled-off">Display aus</div>{/if}
          </div></div>
          <div class="oled-meta">SSD1306 · 128×64</div>
        </div>
      </div>
    </div>
  </div>

  {#if Object.keys(s.customData||{}).length > 0}
    <div class="section"><div class="stitle">Benutzerdaten</div>
      <div class="grid3">
        {#each Object.values(s.customData) as e}
          <div class="custom-item"><span class="ci-icon">{e.icon}</span><div><div class="ci-label">{e.label}</div><div class="ci-val">{e.value}<span class="ci-unit">{e.unit}</span></div></div></div>
        {/each}
      </div>
    </div>
  {/if}
</div>

<style>
  .page{display:flex;flex-direction:column;gap:18px}
  .sh{margin-bottom:4px} .st{font-size:24px;font-weight:800;letter-spacing:-0.5px} .sd{color:var(--text-muted);font-size:13px}
  .section{display:flex;flex-direction:column;gap:10px}
  .stitle{font:600 12px/1 inherit;text-transform:uppercase;letter-spacing:0.8px;color:var(--text-secondary)}
  .grid4{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}
  .grid3{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}
  .grid2{display:grid;grid-template-columns:repeat(2,1fr);gap:14px}
  .full{grid-column:1/-1}
  @media(max-width:1100px){.grid4{grid-template-columns:repeat(2,1fr)}}
  @media(max-width:768px){.grid4,.grid3,.grid2{grid-template-columns:1fr}}
  .card{background:var(--bg-surface,#111827);border:1px solid var(--border);border-radius:16px;transition:all 0.3s}
  .card:hover{border-color:rgba(99,130,255,0.25)}
  .ch{padding:16px 18px 0;display:flex;align-items:center;justify-content:space-between;gap:8px}
  .ct{font:600 12px/1 inherit;text-transform:uppercase;letter-spacing:0.6px;color:var(--text-secondary)}
  .cb{padding:12px 18px 18px}
  .badge-live{font:600 10px var(--mono,monospace);background:rgba(52,211,153,0.1);color:var(--green,#34d399);padding:3px 10px;border-radius:12px}
  .badge-info{font:600 10px var(--mono,monospace);background:var(--accent-dim,rgba(99,102,241,0.1));color:var(--accent,#6366f1);padding:3px 10px;border-radius:12px}
  .badge-sm{font:600 10px var(--mono,monospace);padding:2px 8px;border-radius:8px;background:rgba(255,255,255,0.05);color:var(--text-muted)}
  .badge-ok{background:rgba(52,211,153,0.1);color:var(--green,#34d399)}
  .stat-big{font:800 32px/1 var(--mono,monospace);letter-spacing:-1px;font-variant-numeric:tabular-nums}
  .su{font-size:14px;font-weight:400;color:var(--text-secondary);margin-left:2px}
  .stat-sub{font:12px var(--mono,monospace);color:var(--text-muted);margin-top:6px}
  .sparkline{width:100%;height:40px;margin-top:10px;display:block}
  .pbar{height:6px;background:rgba(255,255,255,0.04);border-radius:3px;margin-top:12px;overflow:hidden}
  .pfill{height:100%;border-radius:3px;transition:width 1s}
  .disk-entry{padding:6px 0;border-bottom:1px solid var(--border)} .disk-entry:last-child{border:none}
  .ditem{padding:12px;border-radius:10px;background:rgba(255,255,255,0.015);border:1px solid var(--border)}
  .dhead{display:flex;justify-content:space-between;margin-bottom:8px}
  .dname{font-weight:600;font-size:13px} .dpct{font:700 16px var(--mono,monospace)}
  .dbar-bg{height:6px;background:rgba(255,255,255,0.06);border-radius:3px;overflow:hidden;margin-bottom:6px}
  .dbar{height:100%;border-radius:3px;transition:width 500ms}
  .dinfo{display:flex;justify-content:space-between;font:11px var(--mono,monospace);color:var(--text-secondary)}
  .dmeta{font:10px var(--mono,monospace);color:var(--text-muted);margin-top:3px}
  .docker-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(28px,1fr));gap:6px;margin-bottom:10px}
  .docker-cell{aspect-ratio:1;border-radius:6px;opacity:0.85}
  .docker-list{display:flex;flex-direction:column;gap:2px;max-height:200px;overflow-y:auto}
  .dl-row{display:flex;align-items:center;gap:8px;padding:3px 0;font-size:11px;border-bottom:1px solid rgba(255,255,255,0.02)}
  .dl-dot{width:6px;height:6px;border-radius:50%;background:var(--text-muted);flex-shrink:0}
  .dl-dot.on{background:var(--green,#34d399);box-shadow:0 0 4px rgba(52,211,153,0.4)}
  .dl-name{font:11px var(--mono,monospace);flex:1} .dl-port{font:10px var(--mono,monospace);color:var(--text-muted)}
  .no-data{font:12px var(--mono,monospace);color:var(--text-muted);padding:8px 0}
  .debug-hint{font:10px var(--mono,monospace);color:var(--text-muted);opacity:0.4}
  .net-stats{display:flex;gap:24px}
  .net-label{font:11px inherit;color:var(--text-muted);margin-bottom:4px}
  .net-val{font:700 18px var(--mono,monospace)}
  .net-ip{font:11px var(--mono,monospace);color:var(--text-muted);margin-top:8px}
  .temp-graph{height:120px;position:relative}
  .glow-line{filter:drop-shadow(0 0 4px rgba(34,211,238,0.4))}
  .temp-now{position:absolute;right:8px;top:8px;font:11px var(--mono,monospace);color:var(--text-muted)}
  .fan-bars{display:flex;gap:4px;height:28px;margin:8px 0}
  .fan-seg{flex:1;border-radius:4px;transition:background 0.3s}
  .cmeta{display:flex;justify-content:space-between;font:11px var(--mono,monospace);color:var(--text-muted)}
  .led-row{display:flex;gap:14px;justify-content:center;margin:12px 0 8px}
  .led-dot{width:28px;height:28px;border-radius:50%;border:1px solid rgba(255,255,255,0.08);transition:all 300ms}
  .oled-wrap{display:flex;flex-direction:column;align-items:center}
  .oled-bezel{background:#1a1a1a;padding:6px;border-radius:8px;border:2px solid #2a2a2a;box-shadow:0 4px 16px rgba(0,0,0,0.5)}
  .oled-screen{width:192px;height:96px;background:#000;border-radius:3px;display:flex;align-items:center;justify-content:center;overflow:hidden}
  .oled-img{image-rendering:pixelated;width:192px;height:96px;display:block}
  .oled-off{color:#333;font-size:11px}
  .oled-meta{font:10px var(--mono,monospace);color:var(--text-muted);margin-top:6px}
  .custom-item{display:flex;align-items:center;gap:10px;padding:10px;border-radius:10px;background:rgba(255,255,255,0.02);border:1px solid var(--border)}
  .ci-icon{font-size:20px;width:32px;text-align:center}
  .ci-label{font-size:11px;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.5px}
  .ci-val{font:600 16px var(--mono,monospace)} .ci-unit{font-size:11px;color:var(--text-muted);margin-left:4px}
</style>
