<script>
  import { onMount, onDestroy } from 'svelte';
  let { state: s } = $props();

  /* ═══════════════════════════════════════════════════════
     OLED PIXEL ENGINE — 128×64, 1-Bit (Schwarz/Weiß)
     ═══════════════════════════════════════════════════════ */
  const W = 128, H = 64;
  let pixels = new Uint8Array(W * H); // 0=schwarz, 1=weiß
  let history = $state([]);
  let historyIdx = $state(-1);
  const MAX_HISTORY = 30;

  function getPixel(x, y) { return (x >= 0 && x < W && y >= 0 && y < H) ? pixels[y * W + x] : 0; }
  function setPixel(x, y, val) { if (x >= 0 && x < W && y >= 0 && y < H) pixels[y * W + x] = val ? 1 : 0; }

  function pushHistory() {
    history = [...history.slice(0, historyIdx + 1), new Uint8Array(pixels)];
    if (history.length > MAX_HISTORY) history = history.slice(history.length - MAX_HISTORY);
    historyIdx = history.length - 1;
  }
  function undo() { if (historyIdx > 0) { historyIdx--; pixels = new Uint8Array(history[historyIdx]); render(); } }
  function redo() { if (historyIdx < history.length - 1) { historyIdx++; pixels = new Uint8Array(history[historyIdx]); render(); } }

  /* ═══ ZEICHENFUNKTIONEN ═══ */
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

  function drawRect(x0, y0, x1, y1, plotFn, filled) {
    const minX = Math.min(x0, x1), minY = Math.min(y0, y1);
    const maxX = Math.max(x0, x1), maxY = Math.max(y0, y1);
    if (filled) { for (let y = minY; y <= maxY; y++) for (let x = minX; x <= maxX; x++) plotFn(x, y); }
    else { for (let x = minX; x <= maxX; x++) { plotFn(x, minY); plotFn(x, maxY); } for (let y = minY + 1; y < maxY; y++) { plotFn(minX, y); plotFn(maxX, y); } }
  }

  function drawCircle(cx, cy, x1, y1, plotFn, filled) {
    const r = Math.round(Math.sqrt((x1 - cx) ** 2 + (y1 - cy) ** 2));
    if (r === 0) { plotFn(cx, cy); return; }
    if (filled) { for (let y = -r; y <= r; y++) for (let x = -r; x <= r; x++) if (x*x+y*y <= r*r) plotFn(cx+x, cy+y); }
    else { let x = r, y = 0, d = 1 - r; while (x >= y) { plotFn(cx+x,cy+y);plotFn(cx-x,cy+y);plotFn(cx+x,cy-y);plotFn(cx-x,cy-y);plotFn(cx+y,cy+x);plotFn(cx-y,cy+x);plotFn(cx+y,cy-x);plotFn(cx-y,cy-x); y++; if(d<=0)d+=2*y+1;else{x--;d+=2*(y-x)+1;} } }
  }

  function floodFill(startX, startY, fillVal) {
    if (startX < 0 || startX >= W || startY < 0 || startY >= H) return;
    const target = getPixel(startX, startY);
    if (target === fillVal) return;
    const stack = [startY * W + startX];
    const visited = new Uint8Array(W * H);
    while (stack.length > 0) {
      const pi = stack.pop();
      if (visited[pi]) continue;
      visited[pi] = 1;
      const x = pi % W, y = (pi - x) / W;
      if (pixels[pi] !== target) continue;
      pixels[pi] = fillVal;
      if (x > 0) stack.push(pi - 1);
      if (x < W - 1) stack.push(pi + 1);
      if (y > 0) stack.push(pi - W);
      if (y < H - 1) stack.push(pi + W);
    }
  }

  /* 5×7 Bitmap-Font */
  const FONT = {
    'A':'01110,10001,10001,11111,10001,10001,10001','B':'11110,10001,10001,11110,10001,10001,11110',
    'C':'01110,10001,10000,10000,10000,10001,01110','D':'11110,10001,10001,10001,10001,10001,11110',
    'E':'11111,10000,10000,11110,10000,10000,11111','F':'11111,10000,10000,11110,10000,10000,10000',
    'G':'01110,10001,10000,10111,10001,10001,01110','H':'10001,10001,10001,11111,10001,10001,10001',
    'I':'01110,00100,00100,00100,00100,00100,01110','L':'10000,10000,10000,10000,10000,10000,11111',
    'M':'10001,11011,10101,10101,10001,10001,10001','N':'10001,11001,10101,10011,10001,10001,10001',
    'O':'01110,10001,10001,10001,10001,10001,01110','P':'11110,10001,10001,11110,10000,10000,10000',
    'R':'11110,10001,10001,11110,10100,10010,10001','S':'01110,10001,10000,01110,00001,10001,01110',
    'T':'11111,00100,00100,00100,00100,00100,00100','U':'10001,10001,10001,10001,10001,10001,01110',
    '0':'01110,10001,10011,10101,11001,10001,01110','1':'00100,01100,00100,00100,00100,00100,01110',
    '2':'01110,10001,00001,00010,00100,01000,11111','3':'01110,10001,00001,00110,00001,10001,01110',
    '4':'00010,00110,01010,10010,11111,00010,00010','5':'11111,10000,11110,00001,00001,10001,01110',
    '6':'00110,01000,10000,11110,10001,10001,01110','7':'11111,00001,00010,00100,01000,01000,01000',
    '8':'01110,10001,10001,01110,10001,10001,01110','9':'01110,10001,10001,01111,00001,00010,01100',
    ' ':'00000,00000,00000,00000,00000,00000,00000','.':'00000,00000,00000,00000,00000,00000,00100',
    ':':'00000,00100,00100,00000,00100,00100,00000','-':'00000,00000,00000,11111,00000,00000,00000',
    '/':'00001,00010,00010,00100,01000,01000,10000','°':'01100,10010,01100,00000,00000,00000,00000',
  };

  function drawText(str, startX, startY) {
    let cx = startX;
    for (const ch of str.toUpperCase()) {
      const g = FONT[ch];
      if (!g) { cx += 4; continue; }
      const rows = g.split(',');
      rows.forEach((row, ry) => {
        for (let rx = 0; rx < row.length; rx++) {
          if (row[rx] === '1') setPixel(cx + rx, startY + ry, 1);
        }
      });
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

  const tools = [
    { id: 'pencil', icon: 'fa-pen', label: 'Stift' },
    { id: 'eraser', icon: 'fa-eraser', label: 'Radierer' },
    { id: 'line', icon: 'fa-minus', label: 'Linie' },
    { id: 'rect', icon: 'fa-square', label: 'Rechteck' },
    { id: 'circle', icon: 'fa-circle', label: 'Kreis' },
    { id: 'fill', icon: 'fa-fill-drip', label: 'Füllen' },
    { id: 'text', icon: 'fa-font', label: 'Text' },
  ];

  /* ═══ CANVAS RENDERING ═══ */
  let canvasEl = $state(null);
  let previewEl = $state(null);

  function render() {
    if (!canvasEl) return;
    const ctx = canvasEl.getContext('2d');
    const z = zoom;
    ctx.imageSmoothingEnabled = false;
    ctx.fillStyle = '#000';
    ctx.fillRect(0, 0, W * z, H * z);
    ctx.fillStyle = '#fff';
    for (let y = 0; y < H; y++)
      for (let x = 0; x < W; x++)
        if (pixels[y * W + x]) ctx.fillRect(x * z, y * z, z, z);

    // Grid
    if (showGrid && z >= 4) {
      ctx.strokeStyle = 'rgba(100,200,255,0.08)';
      ctx.lineWidth = 0.5;
      for (let x = 0; x <= W; x++) { ctx.beginPath(); ctx.moveTo(x * z, 0); ctx.lineTo(x * z, H * z); ctx.stroke(); }
      for (let y = 0; y <= H; y++) { ctx.beginPath(); ctx.moveTo(0, y * z); ctx.lineTo(W * z, y * z); ctx.stroke(); }
    }

    // 1:1 Vorschau
    renderPreview();
  }

  function renderPreview() {
    if (!previewEl) return;
    const ctx = previewEl.getContext('2d');
    ctx.imageSmoothingEnabled = false;
    ctx.fillStyle = '#000';
    ctx.fillRect(0, 0, W, H);
    ctx.fillStyle = '#fff';
    for (let y = 0; y < H; y++)
      for (let x = 0; x < W; x++)
        if (pixels[y * W + x]) ctx.fillRect(x, y, 1, 1);
  }

  /* ═══ MAUS-INTERAKTION ═══ */
  let drawing = $state(false);
  let startX = 0, startY = 0;
  let lastX = -1, lastY = -1;
  let previewPixels = null;

  function mouseToPixel(e) {
    const rect = canvasEl.getBoundingClientRect();
    const x = Math.floor((e.clientX - rect.left) / zoom);
    const y = Math.floor((e.clientY - rect.top) / zoom);
    return [Math.max(0, Math.min(W - 1, x)), Math.max(0, Math.min(H - 1, y))];
  }

  function onDown(e) {
    if (!canvasEl) return;
    const [x, y] = mouseToPixel(e);
    drawing = true;
    startX = x; startY = y;
    lastX = x; lastY = y;

    if (tool === 'pencil' || tool === 'eraser') {
      pushHistory();
      plotPixel(x, y);
      render();
    } else if (tool === 'fill') {
      pushHistory();
      floodFill(x, y, getPixel(x, y) === 1 ? 0 : 1);
      render();
      drawing = false;
    } else if (tool === 'text') {
      pushHistory();
      drawText(textInput, x, y);
      render();
      drawing = false;
    } else {
      // Shape-Start: Preview-Buffer anlegen
      previewPixels = new Uint8Array(pixels);
    }
  }

  function onMove(e) {
    if (!drawing || !canvasEl) return;
    const [x, y] = mouseToPixel(e);
    if (x === lastX && y === lastY) return;

    if (tool === 'pencil' || tool === 'eraser') {
      bresenhamLine(lastX, lastY, x, y, plotPixel);
      lastX = x; lastY = y;
      render();
    } else if (previewPixels) {
      // Shape-Preview: Auf Kopie zeichnen
      pixels = new Uint8Array(previewPixels);
      const plot = (px, py) => setPixel(px, py, 1);
      if (tool === 'line') bresenhamLine(startX, startY, x, y, plot);
      else if (tool === 'rect') drawRect(startX, startY, x, y, plot, filled);
      else if (tool === 'circle') drawCircle(startX, startY, x, y, plot, filled);
      render();
    }
  }

  function onUp(e) {
    if (!drawing) return;
    if (previewPixels && (tool === 'line' || tool === 'rect' || tool === 'circle')) {
      // Shape fertig: In History pushen
      pushHistory();
    }
    drawing = false;
    previewPixels = null;
  }

  function clearCanvas() { pushHistory(); pixels.fill(0); render(); }
  function invertCanvas() { pushHistory(); for (let i = 0; i < pixels.length; i++) pixels[i] = pixels[i] ? 0 : 1; render(); }

  /* ═══ EXPORT AN BACKEND ═══ */
  async function sendToOled() {
    // Canvas zu Base64 PNG
    const c = document.createElement('canvas');
    c.width = W; c.height = H;
    const ctx = c.getContext('2d');
    ctx.fillStyle = '#000';
    ctx.fillRect(0, 0, W, H);
    ctx.fillStyle = '#fff';
    for (let y = 0; y < H; y++)
      for (let x = 0; x < W; x++)
        if (pixels[y * W + x]) ctx.fillRect(x, y, 1, 1);
    // TODO: An Backend senden
    s.toast('An OLED gesendet', 'ok');
  }

  /* ═══ KEYBOARD ═══ */
  function onKey(e) {
    if (e.target.tagName === 'INPUT') return;
    if (e.ctrlKey && e.key === 'z') { undo(); e.preventDefault(); }
    if (e.ctrlKey && e.key === 'y') { redo(); e.preventDefault(); }
    if (e.key === 'g') showGrid = !showGrid;
    if (e.key === '+') zoom = Math.min(16, zoom + 1);
    if (e.key === '-') zoom = Math.max(2, zoom - 1);
  }

  onMount(() => { pushHistory(); render(); });

  $effect(() => { zoom; showGrid; render(); });
</script>

<svelte:window onkeydown={onKey} />

<div class="layout">
  <div class="content">
    <!-- ═══ LINKS: Werkzeuge + Canvas ═══ -->
    <div class="panel panel-editor">
      <div class="fan-header">
        <i class="fa-solid fa-display fan-icon"></i>
        <div>
          <div class="fan-title">OLED-Editor</div>
          <div class="fan-sub">128×64 · SSD1306 · 1-Bit Monochrom</div>
        </div>
      </div>

      <div class="editor-row">
        <!-- Werkzeugleiste -->
        <div class="toolbar">
          {#each tools as t}
            <button class="tool-btn" class:active={tool === t.id} onclick={() => tool = t.id} title={t.label}>
              <i class="fa-solid {t.icon}"></i>
            </button>
          {/each}
          <div class="tool-sep"></div>
          <button class="tool-btn" onclick={undo} title="Rückgängig (Strg+Z)"><i class="fa-solid fa-rotate-left"></i></button>
          <button class="tool-btn" onclick={redo} title="Wiederholen (Strg+Y)"><i class="fa-solid fa-rotate-right"></i></button>
          <div class="tool-sep"></div>
          <button class="tool-btn" onclick={clearCanvas} title="Löschen"><i class="fa-solid fa-trash-can"></i></button>
          <button class="tool-btn" onclick={invertCanvas} title="Invertieren"><i class="fa-solid fa-circle-half-stroke"></i></button>
        </div>

        <!-- Canvas -->
        <div class="canvas-area">
          <canvas bind:this={canvasEl} width={W * zoom} height={H * zoom}
            onpointerdown={onDown} onpointermove={onMove} onpointerup={onUp}
            style="width:{W * zoom}px;height:{H * zoom}px;cursor:{tool === 'fill' ? 'crosshair' : tool === 'text' ? 'text' : 'default'}"></canvas>
        </div>
      </div>
    </div>

    <!-- ═══ RECHTS: Einstellungen + Vorschau ═══ -->
    <div class="panel panel-settings">
      <div class="fan-header">
        <i class="fa-solid fa-sliders fan-icon"></i>
        <div>
          <div class="fan-title">Einstellungen</div>
          <div class="fan-sub">{tools.find(t => t.id === tool)?.label || ''}</div>
        </div>
      </div>

      <!-- Stiftgröße -->
      {#if tool === 'pencil' || tool === 'eraser'}
        <div class="ctrl">
          <div class="ctrl-row">
            <span>Stiftgröße</span>
            <input type="range" min="1" max="8" value={penSize} oninput={(e) => { penSize = +e.target.value; }}>
            <span class="ctrl-val">{penSize}px</span>
          </div>
        </div>
      {/if}

      <!-- Gefüllt -->
      {#if tool === 'rect' || tool === 'circle'}
        <div class="ctrl">
          <div class="ctrl-row">
            <span>Gefüllt</span>
            <button class="tog" class:on={filled} onclick={() => filled = !filled}></button>
          </div>
        </div>
      {/if}

      <!-- Text -->
      {#if tool === 'text'}
        <div class="ctrl">
          <div class="ctrl-row">
            <span>Text</span>
            <input type="text" class="text-input" value={textInput} oninput={(e) => textInput = e.target.value} maxlength="20">
          </div>
        </div>
      {/if}

      <!-- Zoom + Grid -->
      <div class="ctrl">
        <div class="ctrl-row">
          <span>Zoom</span>
          <input type="range" min="2" max="16" value={zoom} oninput={(e) => { zoom = +e.target.value; }}>
          <span class="ctrl-val">{zoom}×</span>
        </div>
        <div class="ctrl-row">
          <span>Raster</span>
          <button class="tog" class:on={showGrid} onclick={() => { showGrid = !showGrid; }}></button>
        </div>
      </div>

      <!-- 1:1 Vorschau -->
      <div class="preview-section">
        <div class="preview-label">Vorschau 1:1</div>
        <div class="preview-bezel">
          <canvas bind:this={previewEl} width={W} height={H} class="preview-canvas"></canvas>
        </div>
      </div>

      <!-- Aktionen -->
      <div class="actions">
        <button class="action-btn" onclick={sendToOled}><i class="fa-solid fa-paper-plane"></i> An OLED senden</button>
      </div>
    </div>
  </div>
</div>

<style>
  .layout { display: flex; flex-direction: column; height: 100%; }
  .content { display: grid; grid-template-columns: 1fr 280px; gap: 12px; flex: 1; min-height: 0; }
  .panel { background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--radius); padding: 14px; display: flex; flex-direction: column; gap: 10px; overflow: hidden; }

  .fan-header { display: flex; align-items: flex-start; gap: 10px; padding-bottom: 0.5em; flex-shrink: 0; }
  .fan-icon { font-size: var(--fs-xl); color: var(--accent); line-height: 1; margin-top: 2px; }
  .fan-title { font: 700 var(--fs-xl) var(--font); line-height: 1; }
  .fan-sub { font: 500 var(--fs-sm) var(--mono); color: var(--text-muted); }

  /* Editor-Layout */
  .editor-row { display: flex; gap: 10px; flex: 1; min-height: 0; }
  .toolbar { display: flex; flex-direction: column; gap: 4px; flex-shrink: 0; }
  .tool-btn {
    width: 36px; height: 36px; border-radius: var(--radius-sm);
    border: 1px solid var(--border); background: var(--bg-elevated);
    color: var(--text-muted); cursor: pointer; font-size: 14px;
    display: flex; align-items: center; justify-content: center;
    transition: all 150ms;
  }
  .tool-btn:hover { border-color: var(--text-muted); color: var(--text-primary); }
  .tool-btn.active { background: var(--accent-dim); border-color: var(--accent); color: var(--accent); }
  .tool-sep { height: 1px; background: var(--border); margin: 4px 0; }

  /* Canvas */
  .canvas-area { flex: 1; overflow: auto; background: var(--bg-deep); border-radius: var(--radius-sm); display: flex; align-items: center; justify-content: center; }
  .canvas-area canvas { image-rendering: pixelated; touch-action: none; }

  /* Einstellungen */
  .ctrl { display: flex; flex-direction: column; gap: 8px; }
  .ctrl-row { display: flex; align-items: center; gap: 10px; font: 500 var(--fs-sm) var(--font); color: var(--text-secondary); }
  .ctrl-row span:first-child { min-width: 80px; }
  .ctrl-row input[type=range] { flex: 1; }
  .ctrl-val { font: 600 var(--fs-sm) var(--mono); color: var(--text-primary); background: var(--bg-deep); padding: 3px 10px; border-radius: var(--radius-sm); min-width: 40px; text-align: center; }
  .text-input { flex: 1; padding: 6px 10px; border: 1px solid var(--border); background: var(--bg-elevated); color: var(--text-primary); border-radius: var(--radius-sm); font: 500 var(--fs-sm) var(--mono); }

  .tog { width: 36px; height: 20px; border-radius: 10px; border: none; background: rgba(255,255,255,0.1); cursor: pointer; position: relative; transition: background var(--tr); }
  .tog.on { background: var(--green); }
  .tog::after { content: ''; position: absolute; top: 2px; left: 2px; width: 16px; height: 16px; border-radius: 50%; background: #fff; transition: transform var(--tr); box-shadow: 0 1px 2px rgba(0,0,0,0.3); }
  .tog.on::after { transform: translateX(16px); }

  /* Vorschau */
  .preview-section { margin-top: auto; }
  .preview-label { font: 600 var(--fs-sm) var(--font); color: var(--text-secondary); margin-bottom: 8px; }
  .preview-bezel { background: #000; padding: 4px; border-radius: 4px; border: 2px solid #333; display: inline-block; }
  .preview-canvas { display: block; width: 128px; height: 64px; image-rendering: pixelated; }

  /* Aktionen */
  .actions { flex-shrink: 0; }
  .action-btn {
    width: 100%; height: 38px; border-radius: var(--radius-sm);
    border: 1px solid var(--accent); background: var(--accent-dim);
    color: var(--accent); font: 500 var(--fs-sm) var(--font);
    cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 8px;
  }
  .action-btn:hover { background: var(--accent); color: #fff; }

  @media (max-width: 900px) { .content { grid-template-columns: 1fr; } }
</style>
