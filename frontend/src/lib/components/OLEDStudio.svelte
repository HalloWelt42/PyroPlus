<script>
  import { onMount, onDestroy } from 'svelte';
  let { state: s } = $props();

  /* ═══════════════════════════════════════════════════════
     OLED PIXEL ENGINE — 128×64, 1-Bit, Multi-Layer
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
  function addLayer(name) {
    const id = _nextId++;
    layers = [...layers, { id, name: name || `Ebene ${id}`, pixels: new Uint8Array(W * H), visible: true, locked: false }];
    activeLayer = id;
    return id;
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
  function toggleVis(id) { layers = layers.map(l => l.id === id ? { ...l, visible: !l.visible } : l); }

  /* Layer Drag & Drop */
  let dragFrom = $state(-1);
  let dragOver = $state(-1);
  function onLayerDragStart(e, idx) { dragFrom = idx; e.dataTransfer.effectAllowed = 'move'; }
  function onLayerDragOver(e, idx) { e.preventDefault(); dragOver = idx; }
  function onLayerDrop(e, idx) {
    e.preventDefault(); dragOver = -1;
    if (dragFrom === idx || dragFrom === -1) return;
    const arr = [...layers]; const [moved] = arr.splice(dragFrom, 1); arr.splice(idx, 0, moved);
    layers = arr; dragFrom = -1;
  }
  function onLayerDragEnd() { dragFrom = -1; dragOver = -1; }

  /* ─── Composite ─── */
  function composite() {
    const result = new Uint8Array(W * H);
    for (const layer of layers) {
      if (!layer.visible) continue;
      for (let i = 0; i < W * H; i++) if (layer.pixels[i]) result[i] = 1;
    }
    return result;
  }

  /* ─── Pixel-Ops ─── */
  function getPixel(x, y) { const px = getActivePixels(); return (x >= 0 && x < W && y >= 0 && y < H && px) ? px[y * W + x] : 0; }
  function setPixel(x, y, val) { const px = getActivePixels(); if (x >= 0 && x < W && y >= 0 && y < H && px) px[y * W + x] = val ? 1 : 0; }

  /* ─── History ─── */
  let history = [];
  let historyIdx = -1;
  function pushHistory() {
    const snap = layers.map(l => ({ ...l, pixels: new Uint8Array(l.pixels) }));
    history = [...history.slice(0, historyIdx + 1), snap];
    if (history.length > 30) history = history.slice(-30);
    historyIdx = history.length - 1;
  }
  function undo() { if (historyIdx > 0) { historyIdx--; layers = history[historyIdx].map(l => ({ ...l, pixels: new Uint8Array(l.pixels) })); render(); } }
  function redo() { if (historyIdx < history.length - 1) { historyIdx++; layers = history[historyIdx].map(l => ({ ...l, pixels: new Uint8Array(l.pixels) })); render(); } }

  /* ═══ ZEICHENFUNKTIONEN ═══ */
  function plotPixel(x, y) {
    const val = activeTool === 'eraser' ? 0 : 1;
    if (penSize === 1) { setPixel(x, y, val); return; }
    const off = Math.floor(penSize / 2);
    for (let dy = 0; dy < penSize; dy++) for (let dx = 0; dx < penSize; dx++) setPixel(x-off+dx, y-off+dy, val);
  }
  function bLine(x0,y0,x1,y1,fn){const dx=Math.abs(x1-x0),dy=Math.abs(y1-y0);const sx=x0<x1?1:-1,sy=y0<y1?1:-1;let e=dx-dy;while(true){fn(x0,y0);if(x0===x1&&y0===y1)break;const e2=2*e;if(e2>-dy){e-=dy;x0+=sx;}if(e2<dx){e+=dx;y0+=sy;}}}
  function dRect(x0,y0,x1,y1,fn,f){const a=Math.min(x0,x1),b=Math.min(y0,y1),c=Math.max(x0,x1),d=Math.max(y0,y1);if(f){for(let y=b;y<=d;y++)for(let x=a;x<=c;x++)fn(x,y);}else{for(let x=a;x<=c;x++){fn(x,b);fn(x,d);}for(let y=b+1;y<d;y++){fn(a,y);fn(c,y);}}}
  function dCircle(cx,cy,x1,y1,fn,f){const r=Math.round(Math.sqrt((x1-cx)**2+(y1-cy)**2));if(r===0){fn(cx,cy);return;}if(f){for(let y=-r;y<=r;y++)for(let x=-r;x<=r;x++)if(x*x+y*y<=r*r)fn(cx+x,cy+y);}else{let x=r,y=0,d=1-r;while(x>=y){fn(cx+x,cy+y);fn(cx-x,cy+y);fn(cx+x,cy-y);fn(cx-x,cy-y);fn(cx+y,cy+x);fn(cx-y,cy+x);fn(cx+y,cy-x);fn(cx-y,cy-x);y++;if(d<=0)d+=2*y+1;else{x--;d+=2*(y-x)+1;}}}}
  function dEllipse(cx,cy,x1,y1,fn,f){const rx=Math.abs(x1-cx),ry=Math.abs(y1-cy);if(rx===0&&ry===0){fn(cx,cy);return;}if(f){for(let y=-ry;y<=ry;y++)for(let x=-rx;x<=rx;x++)if(rx>0&&ry>0&&(x*x)/(rx*rx)+(y*y)/(ry*ry)<=1)fn(cx+x,cy+y);}else{let x=0,y=ry,d1=ry*ry-rx*rx*ry+0.25*rx*rx;while(2*ry*ry*x<=2*rx*rx*y){fn(cx+x,cy+y);fn(cx-x,cy+y);fn(cx+x,cy-y);fn(cx-x,cy-y);x++;if(d1<0)d1+=2*ry*ry*x+ry*ry;else{y--;d1+=2*ry*ry*x-2*rx*rx*y+ry*ry;}}let d2=ry*ry*(x+0.5)*(x+0.5)+rx*rx*(y-1)*(y-1)-rx*rx*ry*ry;while(y>=0){fn(cx+x,cy+y);fn(cx-x,cy+y);fn(cx+x,cy-y);fn(cx-x,cy-y);y--;if(d2>0)d2-=2*rx*rx*y+rx*rx;else{x++;d2+=2*ry*ry*x-2*rx*rx*y+rx*rx;}}}}
  function floodFill(sx,sy,fv){const px=getActivePixels();if(!px||sx<0||sx>=W||sy<0||sy>=H)return;const t=px[sy*W+sx];if(t===fv)return;const st=[sy*W+sx],vi=new Uint8Array(W*H);while(st.length>0){const p=st.pop();if(vi[p])continue;vi[p]=1;if(px[p]!==t)continue;px[p]=fv;const x=p%W,y=(p-x)/W;if(x>0)st.push(p-1);if(x<W-1)st.push(p+1);if(y>0)st.push(p-W);if(y<H-1)st.push(p+W);}}

  const FONT={'A':'01110,10001,10001,11111,10001,10001,10001','B':'11110,10001,10001,11110,10001,10001,11110','C':'01110,10001,10000,10000,10000,10001,01110','D':'11110,10001,10001,10001,10001,10001,11110','E':'11111,10000,10000,11110,10000,10000,11111','F':'11111,10000,10000,11110,10000,10000,10000','G':'01110,10001,10000,10111,10001,10001,01110','H':'10001,10001,10001,11111,10001,10001,10001','I':'01110,00100,00100,00100,00100,00100,01110','L':'10000,10000,10000,10000,10000,10000,11111','M':'10001,11011,10101,10101,10001,10001,10001','N':'10001,11001,10101,10011,10001,10001,10001','O':'01110,10001,10001,10001,10001,10001,01110','P':'11110,10001,10001,11110,10000,10000,10000','R':'11110,10001,10001,11110,10100,10010,10001','S':'01110,10001,10000,01110,00001,10001,01110','T':'11111,00100,00100,00100,00100,00100,00100','U':'10001,10001,10001,10001,10001,10001,01110','V':'10001,10001,10001,10001,01010,01010,00100','W':'10001,10001,10001,10101,10101,11011,10001','X':'10001,01010,00100,00100,00100,01010,10001','Y':'10001,01010,00100,00100,00100,00100,00100','Z':'11111,00001,00010,00100,01000,10000,11111','0':'01110,10001,10011,10101,11001,10001,01110','1':'00100,01100,00100,00100,00100,00100,01110','2':'01110,10001,00001,00010,00100,01000,11111','3':'01110,10001,00001,00110,00001,10001,01110','4':'00010,00110,01010,10010,11111,00010,00010','5':'11111,10000,11110,00001,00001,10001,01110','6':'00110,01000,10000,11110,10001,10001,01110','7':'11111,00001,00010,00100,01000,01000,01000','8':'01110,10001,10001,01110,10001,10001,01110','9':'01110,10001,10001,01111,00001,00010,01100',' ':'00000,00000,00000,00000,00000,00000,00000','.':'00000,00000,00000,00000,00000,00000,00100',':':'00000,00100,00100,00000,00100,00100,00000','-':'00000,00000,00000,11111,00000,00000,00000','°':'01100,10010,01100,00000,00000,00000,00000','a':'00000,00000,01110,00001,01111,10001,01111','b':'10000,10000,11110,10001,10001,10001,11110','c':'00000,00000,01110,10000,10000,10001,01110','d':'00001,00001,01111,10001,10001,10001,01111','e':'00000,00000,01110,10001,11111,10000,01110','o':'00000,00000,01110,10001,10001,10001,01110','r':'00000,00000,10110,11001,10000,10000,10000','s':'00000,00000,01111,10000,01110,00001,11110','t':'01000,01000,11100,01000,01000,01001,00110','u':'00000,00000,10001,10001,10001,10011,01101'};
  function drawText(str,sx,sy,sc=1){let cx=sx;for(const ch of str){const g=FONT[ch]||FONT[ch.toUpperCase()];if(!g){cx+=4*sc;continue;}g.split(',').forEach((row,ry)=>{for(let rx=0;rx<row.length;rx++)if(row[rx]==='1')for(let dy=0;dy<sc;dy++)for(let dx=0;dx<sc;dx++)setPixel(cx+rx*sc+dx,sy+ry*sc+dy,1);});cx+=6*sc;}}

  /* ═══ WERKZEUGE ═══ */
  let activeTool = $state('pencil');
  let penSize = $state(1);
  let filled = $state(false);
  let textInput = $state('HELLO');
  let textScale = $state(1);
  let showGrid = $state(true);
  let zoom = $state(6);
  let cursorX = $state(-1), cursorY = $state(-1);

  const drawingTools = [
    { id: 'pencil', icon: 'fa-pen', label: 'Stift', key: 'P' },
    { id: 'eraser', icon: 'fa-eraser', label: 'Radierer', key: 'E' },
    { id: 'line', icon: 'fa-minus', label: 'Linie', key: 'L' },
    { id: 'rect', icon: 'fa-square', label: 'Rechteck', key: 'R' },
    { id: 'circle', icon: 'fa-circle', label: 'Kreis', key: 'C' },
    { id: 'ellipse', icon: 'fa-egg', label: 'Ellipse', key: 'O' },
    { id: 'fill', icon: 'fa-fill-drip', label: 'Füllen', key: 'F' },
    { id: 'text', icon: 'fa-font', label: 'Text', key: 'T' },
  ];
  const selectTools = [
    { id: 'move', icon: 'fa-up-down-left-right', label: 'Verschieben', key: 'V' },
  ];

  /* ─── Panel Collapse States ─── */
  let propsOpen = $state(true);
  let layersOpen = $state(true);
  let widgetsOpen = $state(false);
  let displayOpen = $state(true);

  /* ═══ WIDGETS ═══ */
  const widgetCatalog = [
    { id:'clock', cat:'zeit', label:'Uhr HH:MM', w:58, h:14, draw:(x,y)=>drawText('14:32',x,y,2) },
    { id:'clock_s', cat:'zeit', label:'Uhr HH:MM:SS', w:48, h:7, draw:(x,y)=>drawText('14:32:07',x,y) },
    { id:'clock_l', cat:'zeit', label:'Uhr Groß', w:90, h:21, draw:(x,y)=>drawText('14:32',x,y,3) },
    { id:'date', cat:'zeit', label:'Datum', w:60, h:7, draw:(x,y)=>drawText('02.04.2026',x,y) },
    { id:'weekday', cat:'zeit', label:'Wochentag', w:12, h:7, draw:(x,y)=>drawText('Do',x,y) },
    { id:'cpu', cat:'sys', label:'CPU Temp', w:24, h:7, draw:(x,y)=>drawText('42°C',x,y) },
    { id:'cpu_pct', cat:'sys', label:'CPU %', w:42, h:7, draw:(x,y)=>drawText('CPU 12',x,y) },
    { id:'ram', cat:'sys', label:'RAM', w:54, h:7, draw:(x,y)=>drawText('RAM 4.2 16G',x,y) },
    { id:'ip', cat:'sys', label:'IP-Adresse', w:60, h:7, draw:(x,y)=>drawText('10.0.0.1',x,y) },
    { id:'uptime', cat:'sys', label:'Uptime', w:60, h:7, draw:(x,y)=>drawText('Up 3d 14:32',x,y) },
    { id:'label', cat:'deko', label:'Textfeld', w:48, h:7, draw:(x,y)=>drawText('Text',x,y) },
    { id:'line_h', cat:'deko', label:'Linie ─', w:60, h:1, draw:(x,y)=>{for(let i=0;i<60;i++)setPixel(x+i,y,1);} },
    { id:'rect_w', cat:'deko', label:'Rahmen □', w:40, h:20, draw:(x,y)=>dRect(x,y,x+39,y+19,(px,py)=>setPixel(px,py,1),false) },
  ];
  const widgetCats = [
    { id:'zeit', label:'Zeit', icon:'fa-clock' },
    { id:'sys', label:'System', icon:'fa-microchip' },
    { id:'deko', label:'Dekoration', icon:'fa-pen' },
  ];

  function placeWidget(w) {
    const id = addLayer(w.label);
    pushHistory();
    w.draw(4, 4);
    render();
    s.toast(`${w.label} eingefügt`, 'ok');
  }

  /* ═══ CANVAS ═══ */
  let canvasEl = $state(null);
  let previewEl = $state(null);

  function render() {
    if (!canvasEl) return;
    const ctx = canvasEl.getContext('2d');
    const z = zoom, comp = composite();
    ctx.imageSmoothingEnabled = false;
    ctx.fillStyle = '#000'; ctx.fillRect(0, 0, W*z, H*z);
    ctx.fillStyle = '#fff';
    for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) if (comp[y*W+x]) ctx.fillRect(x*z, y*z, z, z);
    if (showGrid && z >= 4) {
      ctx.strokeStyle = 'rgba(100,200,255,0.06)'; ctx.lineWidth = 0.5;
      for (let x = 0; x <= W; x++) { ctx.beginPath(); ctx.moveTo(x*z,0); ctx.lineTo(x*z,H*z); ctx.stroke(); }
      for (let y = 0; y <= H; y++) { ctx.beginPath(); ctx.moveTo(0,y*z); ctx.lineTo(W*z,y*z); ctx.stroke(); }
    }
    if (previewEl) {
      const pc = previewEl.getContext('2d');
      pc.imageSmoothingEnabled = false; pc.fillStyle='#000'; pc.fillRect(0,0,W,H);
      pc.fillStyle='#fff';
      for (let y=0;y<H;y++) for(let x=0;x<W;x++) if(comp[y*W+x]) pc.fillRect(x,y,1,1);
    }
  }

  /* ═══ MAUS ═══ */
  let drawing = $state(false);
  let startX=0,startY=0,lastX=-1,lastY=-1;
  let previewSnap=null, moveStart=null;

  function m2p(e){const r=canvasEl.getBoundingClientRect();return[Math.max(0,Math.min(W-1,Math.floor((e.clientX-r.left)/zoom))),Math.max(0,Math.min(H-1,Math.floor((e.clientY-r.top)/zoom)))];}

  function onDown(e) {
    if (!canvasEl) return;
    const layer = getLayer(activeLayer);
    if (layer?.locked) { s.toast('Ebene gesperrt', 'info'); return; }
    const [x,y] = m2p(e);
    drawing=true; startX=x; startY=y; lastX=x; lastY=y;
    if (activeTool==='pencil'||activeTool==='eraser') { pushHistory(); plotPixel(x,y); render(); }
    else if (activeTool==='fill') { pushHistory(); floodFill(x,y,getPixel(x,y)===1?0:1); render(); drawing=false; }
    else if (activeTool==='text') { pushHistory(); drawText(textInput,x,y,textScale); render(); drawing=false; }
    else if (activeTool==='move') { moveStart={x,y,snap:new Uint8Array(layer.pixels)}; }
    else { previewSnap = new Uint8Array(getActivePixels()); }
  }
  function onMove(e) {
    if (!canvasEl) return;
    const [x,y] = m2p(e);
    cursorX=x; cursorY=y;
    if (!drawing) return;
    if (activeTool==='pencil'||activeTool==='eraser') { bLine(lastX,lastY,x,y,plotPixel); lastX=x; lastY=y; render(); }
    else if (activeTool==='move'&&moveStart) {
      const layer=getLayer(activeLayer); if(!layer)return;
      const dx=x-moveStart.x, dy=y-moveStart.y;
      layer.pixels.fill(0);
      for(let py=0;py<H;py++) for(let px=0;px<W;px++) if(moveStart.snap[py*W+px]){const nx=px+dx,ny=py+dy;if(nx>=0&&nx<W&&ny>=0&&ny<H)layer.pixels[ny*W+nx]=1;}
      layers=[...layers]; render();
    } else if (previewSnap) {
      const layer=getLayer(activeLayer); if(!layer)return;
      layer.pixels=new Uint8Array(previewSnap);
      const plot=(px,py)=>setPixel(px,py,1);
      if(activeTool==='line') bLine(startX,startY,x,y,plot);
      else if(activeTool==='rect') dRect(startX,startY,x,y,plot,filled);
      else if(activeTool==='circle') dCircle(startX,startY,x,y,plot,filled);
      else if(activeTool==='ellipse') dEllipse(startX,startY,x,y,plot,filled);
      render();
    }
  }
  function onUp(){if(!drawing)return;if(previewSnap)pushHistory();if(activeTool==='move'&&moveStart){pushHistory();moveStart=null;}drawing=false;previewSnap=null;}

  function clearLayer(){pushHistory();getActivePixels()?.fill(0);render();}
  function invertLayer(){pushHistory();const px=getActivePixels();if(px)for(let i=0;i<px.length;i++)px[i]=px[i]?0:1;render();}

  async function sendToOled(){s.toast('An OLED gesendet','ok');}

  function onKey(e){
    if(e.target.tagName==='INPUT'||e.target.tagName==='TEXTAREA')return;
    if(e.ctrlKey&&e.key==='z'){undo();e.preventDefault();}
    if(e.ctrlKey&&e.key==='y'){redo();e.preventDefault();}
    if(e.key==='g'){showGrid=!showGrid;render();}
    if(e.key==='+')zoom=Math.min(16,zoom+1);
    if(e.key==='-')zoom=Math.max(2,zoom-1);
    const dt=[...drawingTools,...selectTools].find(t=>t.key===e.key.toUpperCase());
    if(dt&&!e.ctrlKey)activeTool=dt.id;
  }

  onMount(()=>{pushHistory();render();});
  $effect(()=>{zoom;showGrid;render();});
</script>

<svelte:window onkeydown={onKey} />

<div class="studio">
  <!-- ═══ LINKES PANEL (PanelWrapper-Sektionen wie rechts) ═══ -->
  <div class="panel-left">
    <!-- Werkzeuge als Grid -->
    <div class="pw">
      <div class="pw-bar"><div class="pw-handle"><svg width="10" height="16" viewBox="0 0 10 16"><circle cx="3" cy="3" r="1.5" fill="currentColor"/><circle cx="7" cy="3" r="1.5" fill="currentColor"/><circle cx="3" cy="8" r="1.5" fill="currentColor"/><circle cx="7" cy="8" r="1.5" fill="currentColor"/><circle cx="3" cy="13" r="1.5" fill="currentColor"/><circle cx="7" cy="13" r="1.5" fill="currentColor"/></svg></div><div class="pw-title"><i class="fa-solid fa-pen"></i> Werkzeuge</div></div>
      <div class="pw-body">
        <div class="tool-grid">
          {#each drawingTools as t}
            <button class="tool-btn" class:active={activeTool===t.id} onclick={()=>activeTool=t.id} title="{t.label} ({t.key})">
              <i class="fa-solid {t.icon}"></i>
            </button>
          {/each}
          {#each selectTools as t}
            <button class="tool-btn" class:active={activeTool===t.id} onclick={()=>activeTool=t.id} title="{t.label} ({t.key})">
              <i class="fa-solid {t.icon}"></i>
            </button>
          {/each}
        </div>
        <!-- Werkzeug-Optionen -->
        {#if activeTool==='pencil'||activeTool==='eraser'}
          <div class="pl-row"><span class="pl-label">Größe</span><input type="range" min="1" max="8" value={penSize} oninput={(e)=>penSize=+e.target.value}><span class="pl-val">{penSize}</span></div>
        {/if}
        {#if activeTool==='rect'||activeTool==='circle'||activeTool==='ellipse'}
          <div class="pl-row"><span class="pl-label">Gefüllt</span><button class="tog" class:on={filled} onclick={()=>filled=!filled}></button></div>
        {/if}
        {#if activeTool==='text'}
          <div class="pl-row"><span class="pl-label">Text</span><input type="text" class="pl-input" bind:value={textInput} maxlength="20"></div>
          <div class="pl-row"><span class="pl-label">Größe</span><input type="range" min="1" max="3" value={textScale} oninput={(e)=>textScale=+e.target.value}><span class="pl-val">{textScale}×</span></div>
        {/if}
      </div>
    </div>

    <!-- Aktionen -->
    <div class="pw">
      <div class="pw-bar"><div class="pw-handle"><svg width="10" height="16" viewBox="0 0 10 16"><circle cx="3" cy="3" r="1.5" fill="currentColor"/><circle cx="7" cy="3" r="1.5" fill="currentColor"/><circle cx="3" cy="8" r="1.5" fill="currentColor"/><circle cx="7" cy="8" r="1.5" fill="currentColor"/><circle cx="3" cy="13" r="1.5" fill="currentColor"/><circle cx="7" cy="13" r="1.5" fill="currentColor"/></svg></div><div class="pw-title"><i class="fa-solid fa-bolt"></i> Aktionen</div></div>
      <div class="pw-body">
        <div class="action-grid">
          <button class="action-btn-sm" onclick={undo} title="Rückgängig (Strg+Z)"><i class="fa-solid fa-rotate-left"></i> Rückgängig</button>
          <button class="action-btn-sm" onclick={redo} title="Wiederholen (Strg+Y)"><i class="fa-solid fa-rotate-right"></i> Wiederholen</button>
          <button class="action-btn-sm" onclick={clearLayer} title="Löschen"><i class="fa-solid fa-trash-can"></i> Löschen</button>
          <button class="action-btn-sm" onclick={invertLayer} title="Invertieren"><i class="fa-solid fa-circle-half-stroke"></i> Invertieren</button>
        </div>
      </div>
    </div>

    <!-- Anzeige -->
    <div class="pw">
      <button class="pw-bar" onclick={()=>displayOpen=!displayOpen}><div class="pw-handle"><svg width="10" height="16" viewBox="0 0 10 16"><circle cx="3" cy="3" r="1.5" fill="currentColor"/><circle cx="7" cy="3" r="1.5" fill="currentColor"/><circle cx="3" cy="8" r="1.5" fill="currentColor"/><circle cx="7" cy="8" r="1.5" fill="currentColor"/><circle cx="3" cy="13" r="1.5" fill="currentColor"/><circle cx="7" cy="13" r="1.5" fill="currentColor"/></svg></div><div class="pw-title"><i class="fa-solid fa-eye"></i> Anzeige <i class="fa-solid fa-chevron-down pw-chev" class:rotated={!displayOpen}></i></div></button>
      {#if displayOpen}
        <div class="pw-body">
          <div class="pl-row"><span class="pl-label">Zoom</span><input type="range" min="2" max="16" value={zoom} oninput={(e)=>zoom=+e.target.value}><span class="pl-val">{zoom}×</span></div>
          <div class="pl-row"><span class="pl-label">Raster</span><button class="tog" class:on={showGrid} onclick={()=>{showGrid=!showGrid;}}></button></div>
        </div>
      {/if}
    </div>

    <!-- Farbe -->
    <div class="pw">
      <div class="pw-bar"><div class="pw-handle"><svg width="10" height="16" viewBox="0 0 10 16"><circle cx="3" cy="3" r="1.5" fill="currentColor"/><circle cx="7" cy="3" r="1.5" fill="currentColor"/><circle cx="3" cy="8" r="1.5" fill="currentColor"/><circle cx="7" cy="8" r="1.5" fill="currentColor"/><circle cx="3" cy="13" r="1.5" fill="currentColor"/><circle cx="7" cy="13" r="1.5" fill="currentColor"/></svg></div><div class="pw-title"><i class="fa-solid fa-palette"></i> Farbe</div></div>
      <div class="pw-body">
        <div class="color-pair">
          <div class="color-swatch white" class:active={activeTool!=='eraser'} onclick={()=>{if(activeTool==='eraser')activeTool='pencil';}} title="Weiß (Zeichnen)"></div>
          <div class="color-swatch black" class:active={activeTool==='eraser'} onclick={()=>activeTool='eraser'} title="Schwarz (Radieren)"></div>
        </div>
      </div>
    </div>
  </div>

  <!-- ═══ CANVAS (Mitte) ═══ -->
  <div class="canvas-area">
    <div class="canvas-scroll">
      <canvas bind:this={canvasEl} width={W*zoom} height={H*zoom}
        onpointerdown={onDown} onpointermove={onMove} onpointerup={onUp}
        style="width:{W*zoom}px;height:{H*zoom}px"></canvas>
    </div>
    <div class="status-bar">
      <span>{cursorX>=0?`${cursorX}, ${cursorY}`:''}</span>
      <span>128 × 64</span>
      <span>{layers.length} Ebenen</span>
      <span>Zoom {zoom}×</span>
      <span>{drawingTools.find(t=>t.id===activeTool)?.label || selectTools.find(t=>t.id===activeTool)?.label || ''}</span>
    </div>
  </div>

  <!-- ═══ RECHTES PANEL (Scrollbar mit PanelWrapper-Sektionen) ═══ -->
  <div class="panel-right">
    <!-- Vorschau-Panel -->
    <div class="pw">
      <div class="pw-bar"><div class="pw-handle"><svg width="10" height="16" viewBox="0 0 10 16"><circle cx="3" cy="3" r="1.5" fill="currentColor"/><circle cx="7" cy="3" r="1.5" fill="currentColor"/><circle cx="3" cy="8" r="1.5" fill="currentColor"/><circle cx="7" cy="8" r="1.5" fill="currentColor"/><circle cx="3" cy="13" r="1.5" fill="currentColor"/><circle cx="7" cy="13" r="1.5" fill="currentColor"/></svg></div><div class="pw-title"><i class="fa-solid fa-display"></i> Vorschau</div></div>
      <div class="pw-body preview-body">
        <div class="preview-bezel"><canvas bind:this={previewEl} width={W} height={H} class="preview-canvas"></canvas></div>
        <button class="send-btn" onclick={sendToOled}><i class="fa-solid fa-paper-plane"></i> An OLED senden</button>
      </div>
    </div>

    <!-- Eigenschaften-Panel -->
    <div class="pw">
      <button class="pw-bar" onclick={()=>propsOpen=!propsOpen}><div class="pw-handle"><svg width="10" height="16" viewBox="0 0 10 16"><circle cx="3" cy="3" r="1.5" fill="currentColor"/><circle cx="7" cy="3" r="1.5" fill="currentColor"/><circle cx="3" cy="8" r="1.5" fill="currentColor"/><circle cx="7" cy="8" r="1.5" fill="currentColor"/><circle cx="3" cy="13" r="1.5" fill="currentColor"/><circle cx="7" cy="13" r="1.5" fill="currentColor"/></svg></div><div class="pw-title"><i class="fa-solid fa-sliders"></i> Eigenschaften <i class="fa-solid fa-chevron-down pw-chev" class:rotated={!propsOpen}></i></div></button>
      {#if propsOpen}
        <div class="pw-body">
          <div class="rp-row"><span>Position</span><span class="mono">{cursorX >= 0 ? `${cursorX}, ${cursorY}` : '—'}</span></div>
          <div class="rp-row"><span>Ebene</span><span class="mono">{getLayer(activeLayer)?.name || '—'}</span></div>
          <div class="rp-row"><span>Pixel</span><span class="mono">{getActivePixels()?.reduce((a,v)=>a+v,0) || 0}</span></div>
        </div>
      {/if}
    </div>

    <!-- Ebenen-Panel -->
    <div class="pw">
      <button class="pw-bar" onclick={()=>layersOpen=!layersOpen}><div class="pw-handle"><svg width="10" height="16" viewBox="0 0 10 16"><circle cx="3" cy="3" r="1.5" fill="currentColor"/><circle cx="7" cy="3" r="1.5" fill="currentColor"/><circle cx="3" cy="8" r="1.5" fill="currentColor"/><circle cx="7" cy="8" r="1.5" fill="currentColor"/><circle cx="3" cy="13" r="1.5" fill="currentColor"/><circle cx="7" cy="13" r="1.5" fill="currentColor"/></svg></div><div class="pw-title"><i class="fa-solid fa-layer-group"></i> Ebenen <i class="fa-solid fa-chevron-down pw-chev" class:rotated={!layersOpen}></i></div></button>
      {#if layersOpen}
        <div class="pw-body">
          <div class="layer-list">
            {#each [...layers].reverse() as layer, ri}
              {@const idx = layers.length - 1 - ri}
              <div class="layer-item" class:active={layer.id===activeLayer} class:drag-over={dragOver===idx}
                draggable="true" onclick={()=>activeLayer=layer.id}
                ondragstart={(e)=>onLayerDragStart(e,idx)} ondragover={(e)=>onLayerDragOver(e,idx)}
                ondrop={(e)=>onLayerDrop(e,idx)} ondragend={onLayerDragEnd}>
                <span class="layer-handle"><svg width="8" height="14" viewBox="0 0 8 14"><circle cx="2.5" cy="2.5" r="1.2" fill="currentColor"/><circle cx="5.5" cy="2.5" r="1.2" fill="currentColor"/><circle cx="2.5" cy="7" r="1.2" fill="currentColor"/><circle cx="5.5" cy="7" r="1.2" fill="currentColor"/><circle cx="2.5" cy="11.5" r="1.2" fill="currentColor"/><circle cx="5.5" cy="11.5" r="1.2" fill="currentColor"/></svg></span>
                <button class="layer-vis" onclick={(e)=>{e.stopPropagation();toggleVis(layer.id);render();}}>
                  <i class="fa-solid {layer.visible?'fa-eye':'fa-eye-slash'}"></i>
                </button>
                <span class="layer-name" contenteditable="false" ondblclick={(e)=>{e.target.contentEditable='true';e.target.focus();}} onblur={(e)=>{e.target.contentEditable='false';layers=layers.map(l=>l.id===layer.id?{...l,name:e.target.textContent}:l);}} onkeydown={(e)=>{if(e.key==='Enter'){e.preventDefault();e.target.blur();}}}>{layer.name}</span>
              </div>
            {/each}
          </div>
          <div class="layer-actions">
            <button class="la-btn" onclick={()=>addLayer()} title="Neue Ebene"><i class="fa-solid fa-plus"></i></button>
            <button class="la-btn" onclick={()=>duplicateLayer(activeLayer)} title="Duplizieren"><i class="fa-solid fa-copy"></i></button>
            <button class="la-btn" onclick={()=>removeLayer(activeLayer)} title="Löschen"><i class="fa-solid fa-trash"></i></button>
          </div>
        </div>
      {/if}
    </div>

    <!-- Widgets-Panel -->
    <div class="pw">
      <button class="pw-bar" onclick={()=>widgetsOpen=!widgetsOpen}><div class="pw-handle"><svg width="10" height="16" viewBox="0 0 10 16"><circle cx="3" cy="3" r="1.5" fill="currentColor"/><circle cx="7" cy="3" r="1.5" fill="currentColor"/><circle cx="3" cy="8" r="1.5" fill="currentColor"/><circle cx="7" cy="8" r="1.5" fill="currentColor"/><circle cx="3" cy="13" r="1.5" fill="currentColor"/><circle cx="7" cy="13" r="1.5" fill="currentColor"/></svg></div><div class="pw-title"><i class="fa-solid fa-puzzle-piece"></i> Widgets <i class="fa-solid fa-chevron-down pw-chev" class:rotated={!widgetsOpen}></i></div></button>
      {#if widgetsOpen}
        <div class="pw-body">
          {#each widgetCats as cat}
            <div class="wc-cat"><i class="fa-solid {cat.icon}"></i> {cat.label}</div>
            <div class="wc-list">
              {#each widgetCatalog.filter(w=>w.cat===cat.id) as w}
                <button class="wc-btn" onclick={()=>placeWidget(w)}>
                  <i class="fa-solid fa-plus"></i>
                  <span class="wc-name">{w.label}</span>
                  <span class="wc-size">{w.w}×{w.h}</span>
                </button>
              {/each}
            </div>
          {/each}
        </div>
      {/if}
    </div>
  </div>
</div>

<style>
  .studio { display: flex; height: 100%; overflow: hidden; }

  /* ─── Linkes Panel (PanelWrapper-Container) ─── */
  .panel-left { width: 250px; flex-shrink: 0; background: var(--bg-base); border-right: 1px solid var(--border); padding: 4px; display: flex; flex-direction: column; gap: 4px; overflow-y: auto; }
  /* Tool-Grid */
  .tool-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 4px; margin-bottom: 8px; }
  .tool-btn { aspect-ratio: 1; border-radius: var(--radius-sm); border: 1.5px solid var(--border); background: none; color: var(--text-muted); cursor: pointer; font-size: var(--fs-base); display: flex; align-items: center; justify-content: center; transition: all 120ms; }
  .tool-btn:hover { background: rgba(255,255,255,0.04); color: var(--text-primary); }
  .tool-btn.active { color: var(--accent); background: rgba(0,180,255,0.1); border-color: var(--accent); }

  .action-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 4px; }
  .action-btn-sm { padding: 6px 8px; border-radius: var(--radius-sm); border: 1px solid var(--border); background: var(--bg-elevated); color: var(--text-muted); cursor: pointer; font: 500 var(--fs-xs) var(--font); display: flex; align-items: center; gap: 4px; }
  .action-btn-sm:hover { border-color: var(--accent); color: var(--accent); }

  .pl-row { display: flex; align-items: center; gap: 8px; font: 500 var(--fs-sm) var(--font); color: var(--text-secondary); }
  .pl-label { width: 55px; flex-shrink: 0; }
  .pl-row input[type=range] { flex: 1; }
  .pl-val { font: 600 var(--fs-sm) var(--mono); color: var(--text-primary); min-width: 32px; text-align: right; }
  .pl-input { flex: 1; padding: 5px 8px; border: 1px solid var(--border); background: var(--bg-elevated); color: var(--text-primary); border-radius: var(--radius-sm); font: 500 var(--fs-sm) var(--mono); }
  .color-pair { display: flex; gap: 8px; align-items: center; }
  .color-swatch { width: 32px; height: 32px; border-radius: var(--radius-sm); border: 2px solid var(--border); cursor: pointer; }
  .color-swatch.white { background: #fff; }
  .color-swatch.black { background: #000; }
  .color-swatch.active { border-color: var(--accent); box-shadow: 0 0 8px rgba(0,180,255,0.3); }

  .tog { width: 30px; height: 16px; border-radius: 8px; border: none; background: rgba(255,255,255,0.1); cursor: pointer; position: relative; transition: background 150ms; }
  .tog.on { background: var(--green); }
  .tog::after { content:''; position:absolute; top:2px; left:2px; width:12px; height:12px; border-radius:50%; background:#fff; transition:transform 150ms; }
  .tog.on::after { transform: translateX(14px); }

  /* ─── Canvas ─── */
  .canvas-area { flex: 1; display: flex; flex-direction: column; min-width: 0; background: #1a1a22; }
  .canvas-scroll { flex: 1; overflow: auto; display: flex; align-items: center; justify-content: center; }
  .canvas-scroll canvas { image-rendering: pixelated; touch-action: none; cursor: crosshair; box-shadow: 0 0 0 1px var(--border), 0 4px 20px rgba(0,0,0,0.4); }
  .status-bar { display: flex; gap: 16px; padding: 3px 10px; background: var(--bg-base); border-top: 1px solid var(--border); flex-shrink: 0; font: 500 var(--fs-xs) var(--mono); color: var(--text-muted); }

  /* ─── Rechtes Panel (PanelWrapper-Sektionen) ─── */
  .panel-right { width: 280px; flex-shrink: 0; background: var(--bg-base); border-left: 1px solid var(--border); display: flex; flex-direction: column; gap: 4px; padding: 4px; overflow-y: auto; }

  /* PanelWrapper */
  .pw { background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--radius); overflow: hidden; display: flex; flex-direction: column; }
  .pw-bar { display: flex; align-items: stretch; background: var(--bg-elevated); user-select: none; flex-shrink: 0; border: none; cursor: pointer; }
  .pw-handle { width: 28px; flex-shrink: 0; display: flex; align-items: center; justify-content: center; cursor: grab; color: var(--text-muted); position: relative; }
  .pw-handle::after { content:''; position:absolute; right:0; top:4px; bottom:4px; width:2px; border-radius:1px; background:var(--border); }
  .pw-handle:hover { background: rgba(0,232,138,0.08); color: var(--green); }
  .pw-handle:hover::after { background: var(--green); }
  .pw-title { flex:1; display:flex; align-items:center; gap:8px; padding:8px 10px; color:var(--text-secondary); font:600 var(--fs-sm) var(--font); text-transform:uppercase; letter-spacing:0.06em; text-align:left; }
  .pw-title i:first-child { color: var(--accent); }
  .pw-chev { font-size: var(--fs-xs); color: var(--text-muted); transition: transform 150ms; margin-left: auto; }
  .pw-chev.rotated { transform: rotate(-90deg); }
  .pw-body { padding: 10px; display: flex; flex-direction: column; gap: 8px; }
  .preview-body { align-items: center; }

  .preview-bezel { background: #000; padding: 3px; border-radius: 4px; border: 2px solid #444; }
  .preview-canvas { display: block; width: 128px; height: 64px; image-rendering: pixelated; }
  .send-btn { width: 100%; padding: 8px; border-radius: var(--radius-sm); border: 1px solid var(--accent); background: var(--accent-dim); color: var(--accent); font: 500 var(--fs-sm) var(--font); cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 6px; }
  .send-btn:hover { background: var(--accent); color: #fff; }

  .rp-row { display: flex; justify-content: space-between; font: 500 var(--fs-sm) var(--font); color: var(--text-muted); padding: 3px 0; }
  .mono { font-family: var(--mono); color: var(--text-secondary); }

  /* Layers */
  .layer-list { display: flex; flex-direction: column; gap: 2px; }
  .layer-item { display: flex; align-items: center; gap: 4px; padding: 4px 6px; border-radius: var(--radius-sm); cursor: pointer; font: 500 var(--fs-sm) var(--font); color: var(--text-muted); background: var(--bg-surface); border: 1px solid transparent; transition: all 120ms; }
  .layer-item:hover { background: var(--bg-elevated); }
  .layer-item.active { border-color: var(--accent); color: var(--accent); background: rgba(0,180,255,0.06); }
  .layer-item.drag-over { border-color: var(--green); border-style: dashed; }
  .layer-handle { color: var(--text-muted); cursor: grab; font-size: var(--fs-xs); padding: 0 2px; }
  .layer-vis { background: none; border: none; color: inherit; cursor: pointer; font-size: var(--fs-sm); padding: 2px; }
  .layer-name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .layer-actions { display: flex; gap: 3px; margin-top: 6px; }
  .la-btn { flex: 1; padding: 4px; border-radius: var(--radius-sm); border: 1px solid var(--border); background: var(--bg-elevated); color: var(--text-muted); cursor: pointer; font-size: var(--fs-sm); text-align: center; }
  .la-btn:hover { border-color: var(--accent); color: var(--accent); }

  /* Widgets */
  .wc-cat { font: 600 var(--fs-xs) var(--font); text-transform: uppercase; letter-spacing: 0.4px; color: var(--text-muted); display: flex; align-items: center; gap: 4px; margin-top: 6px; }
  .wc-cat i { color: var(--accent); font-size: var(--fs-xs); }
  .wc-list { display: flex; flex-direction: column; gap: 2px; }
  .wc-btn { display: flex; align-items: center; gap: 6px; padding: 5px 8px; border-radius: var(--radius-sm); border: 1px dashed var(--border); background: none; color: var(--text-secondary); font: 500 var(--fs-sm) var(--font); cursor: pointer; text-align: left; transition: all 120ms; width: 100%; }
  .wc-btn:hover { border-color: var(--accent); color: var(--accent); }
  .wc-btn i { color: var(--accent); font-size: var(--fs-xs); }
  .wc-name { flex: 1; }
  .wc-size { font: 500 var(--fs-xs) var(--mono); color: var(--text-muted); }

  @media (max-width: 900px) { .panel-left, .panel-right { display: none; } .rail { width: 36px; } }
</style>
