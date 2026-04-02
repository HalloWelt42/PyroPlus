<script>
  import { onMount, onDestroy } from 'svelte';
  let { state: s } = $props();

  /* ═══════════════════════════════════════════════════════
     OLED PIXEL ENGINE — 128×64, 1-Bit, Multi-Layer
     Adaptiert aus PixelVault Pixel-Buffer + Drawing Engine
     ═══════════════════════════════════════════════════════ */
  const W = 128, H = 64;

  /* ─── Layer-System ─── */
  let layers = $state([
    { id: 0, name: 'Hintergrund', pixels: new Uint8Array(W * H), visible: true, locked: false },
  ]);
  let activeLayer = $state(0);
  let _nextId = 1;

  function getLayer(id) { return layers.find(l => l.id === id); }
  function getActivePixels() { return getLayer(activeLayer)?.pixels; }

  function addLayer() {
    const id = _nextId++;
    layers = [...layers, { id, name: `Ebene ${id}`, pixels: new Uint8Array(W * H), visible: true, locked: false }];
    activeLayer = id;
  }
  function removeLayer(id) {
    if (layers.length <= 1) return;
    layers = layers.filter(l => l.id !== id);
    if (activeLayer === id) activeLayer = layers[layers.length - 1].id;
  }
  function duplicateLayer(id) {
    const src = getLayer(id);
    if (!src) return;
    const nid = _nextId++;
    layers = [...layers, { id: nid, name: src.name + ' Kopie', pixels: new Uint8Array(src.pixels), visible: true, locked: false }];
    activeLayer = nid;
  }
  function moveLayer(fromIdx, toIdx) {
    const arr = [...layers];
    const [moved] = arr.splice(fromIdx, 1);
    arr.splice(toIdx, 0, moved);
    layers = arr;
  }
  function toggleLayerVisibility(id) {
    layers = layers.map(l => l.id === id ? { ...l, visible: !l.visible } : l);
  }

  /* ─── Composite: Alle sichtbaren Layer zusammenrechnen ─── */
  function composite() {
    const result = new Uint8Array(W * H);
    for (const layer of layers) {
      if (!layer.visible) continue;
      for (let i = 0; i < W * H; i++) {
        if (layer.pixels[i]) result[i] = 1;
      }
    }
    return result;
  }

  /* ─── Pixel-Operationen (auf aktivem Layer) ─── */
  function getPixel(x, y) {
    const px = getActivePixels();
    return (x >= 0 && x < W && y >= 0 && y < H && px) ? px[y * W + x] : 0;
  }
  function setPixel(x, y, val) {
    const px = getActivePixels();
    if (x >= 0 && x < W && y >= 0 && y < H && px) px[y * W + x] = val ? 1 : 0;
  }

  /* ─── History (pro Aktion, speichert alle Layer) ─── */
  let history = [];
  let historyIdx = -1;
  const MAX_HISTORY = 30;

  function pushHistory() {
    const snap = layers.map(l => ({ ...l, pixels: new Uint8Array(l.pixels) }));
    history = [...history.slice(0, historyIdx + 1), snap];
    if (history.length > MAX_HISTORY) history = history.slice(history.length - MAX_HISTORY);
    historyIdx = history.length - 1;
  }
  function undo() {
    if (historyIdx > 0) {
      historyIdx--;
      layers = history[historyIdx].map(l => ({ ...l, pixels: new Uint8Array(l.pixels) }));
      render();
    }
  }
  function redo() {
    if (historyIdx < history.length - 1) {
      historyIdx++;
      layers = history[historyIdx].map(l => ({ ...l, pixels: new Uint8Array(l.pixels) }));
      render();
    }
  }

  /* ═══ ZEICHENFUNKTIONEN (aus PixelVault Drawing Engine) ═══ */
  function plotPixel(x, y) {
    const val = tool === 'eraser' ? 0 : 1;
    if (penSize === 1) { setPixel(x, y, val); return; }
    const off = Math.floor(penSize / 2);
    for (let dy = 0; dy < penSize; dy++)
      for (let dx = 0; dx < penSize; dx++)
        setPixel(x - off + dx, y - off + dy, val);
  }

  function bresenhamLine(x0, y0, x1, y1, plotFn) {
    const dx = Math.abs(x1 - x0), dy = Math.abs(y1 - y0);
    const sx = x0 < x1 ? 1 : -1, sy = y0 < y1 ? 1 : -1;
    let err = dx - dy;
    while (true) {
      plotFn(x0, y0);
      if (x0 === x1 && y0 === y1) break;
      const e2 = 2 * err;
      if (e2 > -dy) { err -= dy; x0 += sx; }
      if (e2 < dx) { err += dx; y0 += sy; }
    }
  }

  function drawRect(x0, y0, x1, y1, plotFn, fill) {
    const minX = Math.min(x0, x1), minY = Math.min(y0, y1);
    const maxX = Math.max(x0, x1), maxY = Math.max(y0, y1);
    if (fill) { for (let y = minY; y <= maxY; y++) for (let x = minX; x <= maxX; x++) plotFn(x, y); }
    else { for (let x = minX; x <= maxX; x++) { plotFn(x, minY); plotFn(x, maxY); } for (let y = minY + 1; y < maxY; y++) { plotFn(minX, y); plotFn(maxX, y); } }
  }

  function drawCircle(cx, cy, x1, y1, plotFn, fill) {
    const r = Math.round(Math.sqrt((x1 - cx) ** 2 + (y1 - cy) ** 2));
    if (r === 0) { plotFn(cx, cy); return; }
    if (fill) { for (let y = -r; y <= r; y++) for (let x = -r; x <= r; x++) if (x*x+y*y<=r*r) plotFn(cx+x, cy+y); }
    else { let x=r,y=0,d=1-r; while(x>=y){plotFn(cx+x,cy+y);plotFn(cx-x,cy+y);plotFn(cx+x,cy-y);plotFn(cx-x,cy-y);plotFn(cx+y,cy+x);plotFn(cx-y,cy+x);plotFn(cx+y,cy-x);plotFn(cx-y,cy-x);y++;if(d<=0)d+=2*y+1;else{x--;d+=2*(y-x)+1;}} }
  }

  function floodFill(startX, startY, fillVal) {
    const px = getActivePixels();
    if (!px || startX < 0 || startX >= W || startY < 0 || startY >= H) return;
    const target = px[startY * W + startX];
    if (target === fillVal) return;
    const stack = [startY * W + startX];
    const visited = new Uint8Array(W * H);
    while (stack.length > 0) {
      const pi = stack.pop();
      if (visited[pi]) continue;
      visited[pi] = 1;
      if (px[pi] !== target) continue;
      px[pi] = fillVal;
      const x = pi % W, y = (pi - x) / W;
      if (x > 0) stack.push(pi - 1);
      if (x < W - 1) stack.push(pi + 1);
      if (y > 0) stack.push(pi - W);
      if (y < H - 1) stack.push(pi + W);
    }
  }

  /* 5×7 Bitmap-Font (Auswahl) */
  const FONT={'A':'01110,10001,10001,11111,10001,10001,10001','B':'11110,10001,10001,11110,10001,10001,11110','C':'01110,10001,10000,10000,10000,10001,01110','D':'11110,10001,10001,10001,10001,10001,11110','E':'11111,10000,10000,11110,10000,10000,11111','F':'11111,10000,10000,11110,10000,10000,10000','G':'01110,10001,10000,10111,10001,10001,01110','H':'10001,10001,10001,11111,10001,10001,10001','I':'01110,00100,00100,00100,00100,00100,01110','L':'10000,10000,10000,10000,10000,10000,11111','M':'10001,11011,10101,10101,10001,10001,10001','N':'10001,11001,10101,10011,10001,10001,10001','O':'01110,10001,10001,10001,10001,10001,01110','P':'11110,10001,10001,11110,10000,10000,10000','R':'11110,10001,10001,11110,10100,10010,10001','S':'01110,10001,10000,01110,00001,10001,01110','T':'11111,00100,00100,00100,00100,00100,00100','U':'10001,10001,10001,10001,10001,10001,01110','0':'01110,10001,10011,10101,11001,10001,01110','1':'00100,01100,00100,00100,00100,00100,01110','2':'01110,10001,00001,00010,00100,01000,11111','3':'01110,10001,00001,00110,00001,10001,01110','4':'00010,00110,01010,10010,11111,00010,00010','5':'11111,10000,11110,00001,00001,10001,01110','6':'00110,01000,10000,11110,10001,10001,01110','7':'11111,00001,00010,00100,01000,01000,01000','8':'01110,10001,10001,01110,10001,10001,01110','9':'01110,10001,10001,01111,00001,00010,01100',' ':'00000,00000,00000,00000,00000,00000,00000','.':'00000,00000,00000,00000,00000,00000,00100',':':'00000,00100,00100,00000,00100,00100,00000','-':'00000,00000,00000,11111,00000,00000,00000','°':'01100,10010,01100,00000,00000,00000,00000'};

  function drawText(str, startX, startY) {
    let cx = startX;
    for (const ch of str.toUpperCase()) {
      const g = FONT[ch]; if (!g) { cx += 4; continue; }
      g.split(',').forEach((row, ry) => { for (let rx = 0; rx < row.length; rx++) if (row[rx]==='1') setPixel(cx+rx,startY+ry,1); });
      cx += 6;
    }
  }

  /* ═══ WERKZEUGE ═══ */
  let tool = $state('pencil');
  let penSize = $state(1);
  let filled = $state(false);
  let textInput = $state('HELLO');
  let showGrid = $state(true);
  let zoom = $state(6);
  let cursorX = $state(-1), cursorY = $state(-1);

  const tools = [
    { id: 'pencil', icon: 'fa-pen', label: 'Stift', key: 'P' },
    { id: 'eraser', icon: 'fa-eraser', label: 'Radierer', key: 'E' },
    { id: 'line', icon: 'fa-minus', label: 'Linie', key: 'L' },
    { id: 'rect', icon: 'fa-square', label: 'Rechteck', key: 'R' },
    { id: 'circle', icon: 'fa-circle', label: 'Kreis', key: 'C' },
    { id: 'fill', icon: 'fa-fill-drip', label: 'Füllen', key: 'F' },
    { id: 'text', icon: 'fa-font', label: 'Text', key: 'T' },
    { id: 'move', icon: 'fa-up-down-left-right', label: 'Verschieben', key: 'V' },
  ];

  /* Aktiver Tab rechts */
  let rightTab = $state('tools');
  const rightTabs = [
    { id: 'tools', icon: 'fa-sliders', label: 'Werkzeug' },
    { id: 'layers', icon: 'fa-layer-group', label: 'Ebenen' },
    { id: 'widgets', icon: 'fa-puzzle-piece', label: 'Widgets' },
  ];

  /* ═══ CANVAS RENDERING ═══ */
  let canvasEl = $state(null);
  let previewEl = $state(null);

  function render() {
    if (!canvasEl) return;
    const ctx = canvasEl.getContext('2d');
    const z = zoom;
    const comp = composite();
    ctx.imageSmoothingEnabled = false;
    ctx.fillStyle = '#000';
    ctx.fillRect(0, 0, W * z, H * z);
    ctx.fillStyle = '#fff';
    for (let y = 0; y < H; y++)
      for (let x = 0; x < W; x++)
        if (comp[y * W + x]) ctx.fillRect(x * z, y * z, z, z);

    if (showGrid && z >= 4) {
      ctx.strokeStyle = 'rgba(100,200,255,0.06)';
      ctx.lineWidth = 0.5;
      for (let x = 0; x <= W; x++) { ctx.beginPath(); ctx.moveTo(x*z,0); ctx.lineTo(x*z,H*z); ctx.stroke(); }
      for (let y = 0; y <= H; y++) { ctx.beginPath(); ctx.moveTo(0,y*z); ctx.lineTo(W*z,y*z); ctx.stroke(); }
    }
    renderPreview();
  }

  function renderPreview() {
    if (!previewEl) return;
    const ctx = previewEl.getContext('2d');
    const comp = composite();
    ctx.imageSmoothingEnabled = false;
    ctx.fillStyle = '#000';
    ctx.fillRect(0, 0, W, H);
    ctx.fillStyle = '#fff';
    for (let y = 0; y < H; y++)
      for (let x = 0; x < W; x++)
        if (comp[y * W + x]) ctx.fillRect(x, y, 1, 1);
  }

  /* ═══ MAUS-INTERAKTION ═══ */
  let drawing = $state(false);
  let startX = 0, startY = 0;
  let lastX = -1, lastY = -1;
  let previewSnap = null; // Snapshot für Shape-Preview
  let moveStart = null; // Für Verschieben-Tool

  function mouseToPixel(e) {
    const rect = canvasEl.getBoundingClientRect();
    return [
      Math.max(0, Math.min(W - 1, Math.floor((e.clientX - rect.left) / zoom))),
      Math.max(0, Math.min(H - 1, Math.floor((e.clientY - rect.top) / zoom))),
    ];
  }

  function onDown(e) {
    if (!canvasEl) return;
    const layer = getLayer(activeLayer);
    if (layer?.locked) { s.toast('Ebene gesperrt', 'info'); return; }
    const [x, y] = mouseToPixel(e);
    drawing = true; startX = x; startY = y; lastX = x; lastY = y;

    if (tool === 'pencil' || tool === 'eraser') { pushHistory(); plotPixel(x, y); render(); }
    else if (tool === 'fill') { pushHistory(); floodFill(x, y, getPixel(x, y) === 1 ? 0 : 1); render(); drawing = false; }
    else if (tool === 'text') { pushHistory(); drawText(textInput, x, y); render(); drawing = false; }
    else if (tool === 'move') { moveStart = { x, y, snap: new Uint8Array(layer.pixels) }; }
    else { previewSnap = new Uint8Array(getActivePixels()); }
  }

  function onMove(e) {
    if (!canvasEl) return;
    const [x, y] = mouseToPixel(e);
    cursorX = x; cursorY = y;
    if (!drawing) return;
    if (x === lastX && y === lastY) return;

    if (tool === 'pencil' || tool === 'eraser') {
      bresenhamLine(lastX, lastY, x, y, plotPixel);
      lastX = x; lastY = y; render();
    } else if (tool === 'move' && moveStart) {
      const layer = getLayer(activeLayer);
      if (!layer) return;
      const dx = x - moveStart.x, dy = y - moveStart.y;
      layer.pixels.fill(0);
      for (let py = 0; py < H; py++)
        for (let px = 0; px < W; px++)
          if (moveStart.snap[py * W + px]) {
            const nx = px + dx, ny = py + dy;
            if (nx >= 0 && nx < W && ny >= 0 && ny < H) layer.pixels[ny * W + nx] = 1;
          }
      layers = [...layers]; // Svelte reaktivität triggern
      render();
    } else if (previewSnap) {
      const layer = getLayer(activeLayer);
      if (!layer) return;
      layer.pixels = new Uint8Array(previewSnap);
      const plot = (px, py) => setPixel(px, py, 1);
      if (tool === 'line') bresenhamLine(startX, startY, x, y, plot);
      else if (tool === 'rect') drawRect(startX, startY, x, y, plot, filled);
      else if (tool === 'circle') drawCircle(startX, startY, x, y, plot, filled);
      render();
    }
  }

  function onUp() {
    if (!drawing) return;
    if (previewSnap) pushHistory();
    if (tool === 'move' && moveStart) { pushHistory(); moveStart = null; }
    drawing = false; previewSnap = null;
  }

  function clearLayer() { pushHistory(); getActivePixels()?.fill(0); render(); }
  function invertLayer() { pushHistory(); const px = getActivePixels(); if (px) for (let i = 0; i < px.length; i++) px[i] = px[i] ? 0 : 1; render(); }

  /* ═══ WIDGETS (Vordefinierte Bausteine) ═══ */
  const widgetCatalog = [
    { id: 'clock', label: 'Uhr HH:MM', draw: (px,py) => drawText('14:32', px, py) },
    { id: 'clock_s', label: 'Uhr HH:MM:SS', draw: (px,py) => drawText('14:32:07', px, py) },
    { id: 'date', label: 'Datum', draw: (px,py) => drawText('02.04.2026', px, py) },
    { id: 'cpu_temp', label: 'CPU Temperatur', draw: (px,py) => drawText('42°C CPU 12', px, py) },
    { id: 'ram', label: 'RAM', draw: (px,py) => drawText('RAM 4.2 16G', px, py) },
    { id: 'ip', label: 'IP-Adresse', draw: (px,py) => drawText('10.0.0.1', px, py) },
    { id: 'uptime', label: 'Uptime', draw: (px,py) => drawText('UP 3D 14:32', px, py) },
  ];

  function placeWidget(widget) {
    addLayer();
    pushHistory();
    widget.draw(2, 2);
    render();
    s.toast(`${widget.label} platziert`, 'ok');
  }

  /* ═══ EXPORT ═══ */
  async function sendToOled() {
    s.toast('An OLED gesendet', 'ok');
  }

  /* ═══ KEYBOARD ═══ */
  function onKey(e) {
    if (e.target.tagName === 'INPUT') return;
    if (e.ctrlKey && e.key === 'z') { undo(); e.preventDefault(); }
    if (e.ctrlKey && e.key === 'y') { redo(); e.preventDefault(); }
    if (e.key === 'g') { showGrid = !showGrid; render(); }
    if (e.key === '+') { zoom = Math.min(16, zoom + 1); render(); }
    if (e.key === '-') { zoom = Math.max(2, zoom - 1); render(); }
    const t = tools.find(t => t.key === e.key.toUpperCase());
    if (t && !e.ctrlKey) tool = t.id;
  }

  onMount(() => { pushHistory(); render(); });
  $effect(() => { zoom; showGrid; layers; render(); });
</script>

<svelte:window onkeydown={onKey} />

<div class="layout">
  <div class="editor">
    <!-- ═══ TOOLBAR (links, vertikal) ═══ -->
    <div class="toolbar">
      {#each tools as t}
        <button class="tool-btn" class:active={tool === t.id} onclick={() => tool = t.id} title="{t.label} ({t.key})">
          <i class="fa-solid {t.icon}"></i>
        </button>
      {/each}
      <div class="tool-sep"></div>
      <button class="tool-btn" onclick={undo} title="Rückgängig (Strg+Z)"><i class="fa-solid fa-rotate-left"></i></button>
      <button class="tool-btn" onclick={redo} title="Wiederholen (Strg+Y)"><i class="fa-solid fa-rotate-right"></i></button>
      <div class="tool-sep"></div>
      <button class="tool-btn" onclick={clearLayer} title="Ebene löschen"><i class="fa-solid fa-trash-can"></i></button>
      <button class="tool-btn" onclick={invertLayer} title="Invertieren"><i class="fa-solid fa-circle-half-stroke"></i></button>
    </div>

    <!-- ═══ CANVAS (Mitte) ═══ -->
    <div class="canvas-area">
      <div class="canvas-scroll">
        <canvas bind:this={canvasEl} width={W * zoom} height={H * zoom}
          onpointerdown={onDown} onpointermove={onMove} onpointerup={onUp}
          style="width:{W*zoom}px;height:{H*zoom}px"></canvas>
      </div>
      <div class="canvas-bar">
        <span class="canvas-info">{cursorX >= 0 ? `${cursorX}, ${cursorY}` : ''}</span>
        <span class="canvas-info">128×64</span>
        <span class="canvas-info">{layers.length} Ebenen</span>
        <span class="canvas-info">Zoom {zoom}×</span>
      </div>
    </div>

    <!-- ═══ RECHTE SEITE (Tabs) ═══ -->
    <div class="sidebar-right">
      <!-- 1:1 Vorschau oben -->
      <div class="preview-box">
        <div class="preview-bezel">
          <canvas bind:this={previewEl} width={W} height={H} class="preview-canvas"></canvas>
        </div>
      </div>

      <!-- Tabs -->
      <div class="right-tabs">
        {#each rightTabs as tab}
          <button class="right-tab" class:active={rightTab === tab.id} onclick={() => rightTab = tab.id}>
            <i class="fa-solid {tab.icon}"></i> {tab.label}
          </button>
        {/each}
      </div>

      <div class="right-content">
        {#if rightTab === 'tools'}
          <!-- Werkzeug-Einstellungen -->
          <div class="section-title"><i class="fa-solid fa-sliders"></i> {tools.find(t=>t.id===tool)?.label}</div>
          {#if tool === 'pencil' || tool === 'eraser'}
            <div class="prop-row"><span>Stiftgröße</span><input type="range" min="1" max="8" value={penSize} oninput={(e)=>penSize=+e.target.value}><span class="prop-val">{penSize}px</span></div>
          {/if}
          {#if tool === 'rect' || tool === 'circle'}
            <div class="prop-row"><span>Gefüllt</span><button class="tog" class:on={filled} onclick={()=>filled=!filled}></button></div>
          {/if}
          {#if tool === 'text'}
            <div class="prop-row"><span>Text</span><input type="text" class="text-input" bind:value={textInput} maxlength="20"></div>
          {/if}
          <div class="prop-row"><span>Zoom</span><input type="range" min="2" max="16" value={zoom} oninput={(e)=>{zoom=+e.target.value;render();}}><span class="prop-val">{zoom}×</span></div>
          <div class="prop-row"><span>Raster</span><button class="tog" class:on={showGrid} onclick={()=>{showGrid=!showGrid;render();}}></button></div>

          <div class="section-title" style="margin-top:12px"><i class="fa-solid fa-paper-plane"></i> Export</div>
          <button class="action-btn" onclick={sendToOled}><i class="fa-solid fa-paper-plane"></i> An OLED senden</button>

        {:else if rightTab === 'layers'}
          <!-- Ebenen-Verwaltung -->
          <div class="section-title"><i class="fa-solid fa-layer-group"></i> Ebenen</div>
          <div class="layer-list">
            {#each [...layers].reverse() as layer, ri}
              {@const idx = layers.length - 1 - ri}
              <div class="layer-item" class:active={layer.id === activeLayer} onclick={() => activeLayer = layer.id}>
                <button class="layer-vis" onclick={(e) => { e.stopPropagation(); toggleLayerVisibility(layer.id); render(); }}>
                  <i class="fa-solid {layer.visible ? 'fa-eye' : 'fa-eye-slash'}"></i>
                </button>
                <span class="layer-name">{layer.name}</span>
              </div>
            {/each}
          </div>
          <div class="layer-actions">
            <button class="btn-sm" onclick={addLayer} title="Neue Ebene"><i class="fa-solid fa-plus"></i></button>
            <button class="btn-sm" onclick={() => duplicateLayer(activeLayer)} title="Duplizieren"><i class="fa-solid fa-copy"></i></button>
            <button class="btn-sm" onclick={() => removeLayer(activeLayer)} title="Löschen"><i class="fa-solid fa-trash"></i></button>
          </div>

        {:else if rightTab === 'widgets'}
          <!-- Widget-Katalog -->
          <div class="section-title"><i class="fa-solid fa-puzzle-piece"></i> Widget einfügen</div>
          <div class="widget-list">
            {#each widgetCatalog as w}
              <button class="widget-btn" onclick={() => placeWidget(w)}>
                <i class="fa-solid fa-plus"></i> {w.label}
              </button>
            {/each}
          </div>
        {/if}
      </div>
    </div>
  </div>
</div>

<style>
  .layout { display: flex; flex-direction: column; height: 100%; }
  .editor { display: flex; flex: 1; min-height: 0; gap: 0; }

  /* Toolbar */
  .toolbar { display: flex; flex-direction: column; gap: 3px; padding: 8px 6px; background: var(--bg-base); border-right: 1px solid var(--border); flex-shrink: 0; }
  .tool-btn { width: 34px; height: 34px; border-radius: var(--radius-sm); border: 1px solid transparent; background: none; color: var(--text-muted); cursor: pointer; font-size: 13px; display: flex; align-items: center; justify-content: center; transition: all 150ms; }
  .tool-btn:hover { background: rgba(255,255,255,0.04); color: var(--text-primary); }
  .tool-btn.active { background: var(--accent-dim); border-color: var(--accent); color: var(--accent); }
  .tool-sep { height: 1px; background: var(--border); margin: 3px 0; }

  /* Canvas */
  .canvas-area { flex: 1; display: flex; flex-direction: column; min-width: 0; background: var(--bg-deep); }
  .canvas-scroll { flex: 1; overflow: auto; display: flex; align-items: center; justify-content: center; }
  .canvas-scroll canvas { image-rendering: pixelated; touch-action: none; cursor: crosshair; }
  .canvas-bar { display: flex; gap: 12px; padding: 4px 10px; background: var(--bg-base); border-top: 1px solid var(--border); flex-shrink: 0; }
  .canvas-info { font: 500 11px var(--mono); color: var(--text-muted); }

  /* Rechte Sidebar */
  .sidebar-right { width: 260px; flex-shrink: 0; display: flex; flex-direction: column; background: var(--bg-card); border-left: 1px solid var(--border); overflow: hidden; }

  .preview-box { padding: 10px; display: flex; justify-content: center; border-bottom: 1px solid var(--border); }
  .preview-bezel { background: #000; padding: 3px; border-radius: 3px; border: 2px solid #333; }
  .preview-canvas { display: block; width: 128px; height: 64px; image-rendering: pixelated; }

  .right-tabs { display: flex; border-bottom: 1px solid var(--border); }
  .right-tab { flex: 1; padding: 8px 4px; border: none; background: none; color: var(--text-muted); font: 500 var(--fs-xs) var(--font); cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 4px; transition: all 150ms; }
  .right-tab.active { color: var(--accent); box-shadow: inset 0 -2px 0 var(--accent); }

  .right-content { flex: 1; overflow-y: auto; padding: 10px; display: flex; flex-direction: column; gap: 8px; }

  .section-title { font: 600 var(--fs-sm) var(--font); color: var(--text-secondary); display: flex; align-items: center; gap: 6px; }
  .section-title i { color: var(--accent); font-size: var(--fs-sm); }

  /* Properties */
  .prop-row { display: flex; align-items: center; gap: 8px; font: 500 var(--fs-sm) var(--font); color: var(--text-secondary); }
  .prop-row span:first-child { min-width: 70px; }
  .prop-row input[type=range] { flex: 1; }
  .prop-val { font: 600 var(--fs-xs) var(--mono); color: var(--text-primary); background: var(--bg-deep); padding: 2px 8px; border-radius: var(--radius-sm); min-width: 36px; text-align: center; }
  .text-input { flex: 1; padding: 5px 8px; border: 1px solid var(--border); background: var(--bg-elevated); color: var(--text-primary); border-radius: var(--radius-sm); font: 500 var(--fs-sm) var(--mono); }

  .tog { width: 34px; height: 18px; border-radius: 9px; border: none; background: rgba(255,255,255,0.1); cursor: pointer; position: relative; transition: background var(--tr); }
  .tog.on { background: var(--green); }
  .tog::after { content: ''; position: absolute; top: 2px; left: 2px; width: 14px; height: 14px; border-radius: 50%; background: #fff; transition: transform var(--tr); box-shadow: 0 1px 2px rgba(0,0,0,0.3); }
  .tog.on::after { transform: translateX(16px); }

  /* Layers */
  .layer-list { display: flex; flex-direction: column; gap: 2px; }
  .layer-item { display: flex; align-items: center; gap: 6px; padding: 5px 8px; border-radius: var(--radius-sm); cursor: pointer; font: 500 var(--fs-sm) var(--font); color: var(--text-muted); transition: all 150ms; }
  .layer-item:hover { background: rgba(255,255,255,0.03); }
  .layer-item.active { background: var(--accent-dim); color: var(--accent); }
  .layer-vis { background: none; border: none; color: inherit; cursor: pointer; font-size: var(--fs-sm); padding: 2px; }
  .layer-name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .layer-actions { display: flex; gap: 4px; margin-top: 6px; }
  .btn-sm { padding: 4px 10px; border-radius: var(--radius-sm); border: 1px solid var(--border); background: var(--bg-elevated); color: var(--text-muted); cursor: pointer; font-size: var(--fs-xs); }
  .btn-sm:hover { border-color: var(--accent); color: var(--accent); }

  /* Widgets */
  .widget-list { display: flex; flex-direction: column; gap: 4px; }
  .widget-btn { display: flex; align-items: center; gap: 8px; padding: 8px 10px; border-radius: var(--radius-sm); border: 1px dashed var(--border); background: none; color: var(--text-secondary); font: 500 var(--fs-sm) var(--font); cursor: pointer; text-align: left; transition: all 150ms; }
  .widget-btn:hover { border-color: var(--accent); color: var(--accent); }
  .widget-btn i { color: var(--accent); }

  /* Action */
  .action-btn { width: 100%; padding: 8px; border-radius: var(--radius-sm); border: 1px solid var(--accent); background: var(--accent-dim); color: var(--accent); font: 500 var(--fs-sm) var(--font); cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 6px; }
  .action-btn:hover { background: var(--accent); color: #fff; }

  @media (max-width: 900px) { .sidebar-right { width: 200px; } }
</style>
