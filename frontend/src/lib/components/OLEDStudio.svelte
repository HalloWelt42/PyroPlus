<script>
  import { onMount } from 'svelte';
  import PanelWrapper from './oled/PanelWrapper.svelte';
  import WidgetStrip from './oled/WidgetStrip.svelte';
  import * as E from './oled/engine.js';
  let { state: s } = $props();
  const W = E.W, H = E.H;

  /* ═══ LAYER-SYSTEM ═══ */
  let layers = $state([{ id: 0, name: 'Hintergrund', pixels: new Uint8Array(W*H), visible: true }]);
  let activeLayer = $state(0);
  let _nid = 1;
  function gl(id) { return layers.find(l => l.id === id); }
  function ap() { return gl(activeLayer)?.pixels; }
  function addLayer(name) { const id = _nid++; layers = [...layers, { id, name: name||`Ebene ${id}`, pixels: new Uint8Array(W*H), visible: true }]; activeLayer = id; }
  function rmLayer(id) { if (layers.length <= 1) return; layers = layers.filter(l => l.id !== id); if (activeLayer === id) activeLayer = layers[layers.length-1].id; }
  function dupLayer(id) { const src = gl(id); if (!src) return; const nid = _nid++; layers = [...layers, { id: nid, name: src.name+' Kopie', pixels: new Uint8Array(src.pixels), visible: true }]; activeLayer = nid; }
  function toggleVis(id) { layers = layers.map(l => l.id === id ? { ...l, visible: !l.visible } : l); }

  /* Layer D&D */
  let ldFrom = $state(-1), ldOver = $state(-1);
  function ldStart(e, i) { ldFrom = i; e.dataTransfer.effectAllowed = 'move'; }
  function ldDragOver(e, i) { e.preventDefault(); ldOver = i; }
  function ldDrop(e, i) { e.preventDefault(); ldOver = -1; if (ldFrom === i) return; const a = [...layers]; const [m] = a.splice(ldFrom, 1); a.splice(i, 0, m); layers = a; ldFrom = -1; }
  function ldEnd() { ldFrom = -1; ldOver = -1; }

  /* ═══ HISTORY ═══ */
  let hist = [], hidx = -1;
  function pushH() { hist = [...hist.slice(0, hidx+1), layers.map(l => ({...l, pixels: new Uint8Array(l.pixels)}))]; if (hist.length > 30) hist = hist.slice(-30); hidx = hist.length - 1; }
  function undo() { if (hidx > 0) { hidx--; layers = hist[hidx].map(l => ({...l, pixels: new Uint8Array(l.pixels)})); render(); } }
  function redo() { if (hidx < hist.length-1) { hidx++; layers = hist[hidx].map(l => ({...l, pixels: new Uint8Array(l.pixels)})); render(); } }

  /* ═══ PIXEL-OPS ═══ */
  function gp(x, y) { const px = ap(); return (x>=0&&x<W&&y>=0&&y<H&&px) ? px[y*W+x] : 0; }
  function sp(x, y, v) { const px = ap(); if (x>=0&&x<W&&y>=0&&y<H&&px) px[y*W+x] = v?1:0; }
  function plot(x, y) { const v = tool==='eraser'?0:1; if (penSize===1){sp(x,y,v);return;} const o=Math.floor(penSize/2); for(let dy=0;dy<penSize;dy++)for(let dx=0;dx<penSize;dx++)sp(x-o+dx,y-o+dy,v); }

  /* ═══ WERKZEUGE ═══ */
  let tool = $state('pencil'), penSize = $state(1), filled = $state(false);
  let textInput = $state('HELLO'), textScale = $state(1);
  let showGrid = $state(true), zoom = $state(6);
  let cursorX = $state(-1), cursorY = $state(-1);

  const drawTools = [
    {id:'pencil',icon:'fa-pen',label:'Stift',key:'P'},{id:'eraser',icon:'fa-eraser',label:'Radierer',key:'E'},
    {id:'line',icon:'fa-minus',label:'Linie',key:'L'},{id:'rect',icon:'fa-square',label:'Rechteck',key:'R'},
    {id:'circle',icon:'fa-circle',label:'Kreis',key:'C'},{id:'ellipse',icon:'fa-egg',label:'Ellipse',key:'O'},
    {id:'fill',icon:'fa-fill-drip',label:'Füllen',key:'F'},{id:'text',icon:'fa-font',label:'Text',key:'T'},
    {id:'move',icon:'fa-up-down-left-right',label:'Verschieben',key:'V'},
  ];

  /* ═══ WIDGETS ═══ */
  const widgets = [
    {id:'clock',cat:'zeit',label:'Uhr HH:MM',w:58,h:14,draw:(x,y,s)=>E.drawText(ap(),String(new Date().getHours()).padStart(2,'0')+':'+String(new Date().getMinutes()).padStart(2,'0'),x,y,2)},
    {id:'clock_s',cat:'zeit',label:'Uhr HH:MM:SS',w:48,h:7,draw:(x,y)=>E.drawText(ap(),'14:32:07',x,y)},
    {id:'clock_l',cat:'zeit',label:'Uhr Groß',w:90,h:21,draw:(x,y)=>E.drawText(ap(),'14:32',x,y,3)},
    {id:'date',cat:'zeit',label:'Datum',w:60,h:7,draw:(x,y)=>E.drawText(ap(),'02.04.2026',x,y)},
    {id:'cpu',cat:'sys',label:'CPU Temperatur',w:24,h:7,draw:(x,y)=>E.drawText(ap(),Math.round(s.stats?.cpu?.temp||0)+'°C',x,y)},
    {id:'ram',cat:'sys',label:'RAM Auslastung',w:54,h:7,draw:(x,y)=>E.drawText(ap(),'RAM '+(s.stats?.ram?.percent||0)+'%',x,y)},
    {id:'ip',cat:'sys',label:'IP-Adresse',w:60,h:7,draw:(x,y)=>E.drawText(ap(),s.stats?.network?.ip||'0.0.0.0',x,y)},
    {id:'uptime',cat:'sys',label:'Uptime',w:60,h:7,draw:(x,y)=>E.drawText(ap(),s.stats?.uptime?.formatted||'0:00',x,y)},
    {id:'label',cat:'deko',label:'Textfeld',w:48,h:7,draw:(x,y)=>E.drawText(ap(),'Text',x,y)},
    {id:'line_h',cat:'deko',label:'Linie',w:60,h:1,draw:(x,y)=>{for(let i=0;i<60;i++)sp(x+i,y,1);}},
    {id:'rect_w',cat:'deko',label:'Rahmen',w:40,h:20,draw:(x,y)=>E.drawRect(x,y,x+39,y+19,(px,py)=>sp(px,py,1),false)},
  ];
  function placeWidget(w) { addLayer(w.label); pushH(); w.draw(4,4); render(); s.toast(`${w.label} eingefügt`,'ok'); }

  /* ═══ CANVAS ═══ */
  let canvasEl = $state(null), previewEl = $state(null);
  function render() {
    const comp = E.composite(layers);
    if (canvasEl) E.renderCanvas(canvasEl.getContext('2d'), comp, zoom, showGrid);
    if (previewEl) E.renderPreview(previewEl.getContext('2d'), comp);
  }

  /* ═══ MAUS ═══ */
  let drawing=$state(false), sx=0, sy=0, lx=-1, ly=-1, snap=null, mvStart=null;
  function m2p(e) { const r=canvasEl.getBoundingClientRect(); return [Math.max(0,Math.min(W-1,Math.floor((e.clientX-r.left)/zoom))),Math.max(0,Math.min(H-1,Math.floor((e.clientY-r.top)/zoom)))]; }

  function onDown(e) {
    if (!canvasEl) return;
    const [x,y]=m2p(e); drawing=true; sx=x; sy=y; lx=x; ly=y;
    if (tool==='pencil'||tool==='eraser') { pushH(); plot(x,y); render(); }
    else if (tool==='fill') { pushH(); E.floodFill(ap(),x,y,gp(x,y)===1?0:1); render(); drawing=false; }
    else if (tool==='text') { pushH(); E.drawText(ap(),textInput,x,y,textScale); render(); drawing=false; }
    else if (tool==='move') { mvStart={x,y,snap:new Uint8Array(ap())}; }
    else { snap = new Uint8Array(ap()); }
  }
  function onMove(e) {
    if (!canvasEl) return;
    const [x,y]=m2p(e); cursorX=x; cursorY=y;
    if (!drawing) return;
    if (tool==='pencil'||tool==='eraser') { E.bresenhamLine(lx,ly,x,y,plot); lx=x; ly=y; render(); }
    else if (tool==='move'&&mvStart) {
      const layer=gl(activeLayer); if(!layer)return;
      const dx=x-mvStart.x,dy=y-mvStart.y; layer.pixels.fill(0);
      for(let py=0;py<H;py++)for(let px=0;px<W;px++)if(mvStart.snap[py*W+px]){const nx=px+dx,ny=py+dy;if(nx>=0&&nx<W&&ny>=0&&ny<H)layer.pixels[ny*W+nx]=1;}
      layers=[...layers]; render();
    } else if (snap) {
      gl(activeLayer).pixels=new Uint8Array(snap);
      const p=(px,py)=>sp(px,py,1);
      if(tool==='line')E.bresenhamLine(sx,sy,x,y,p);
      else if(tool==='rect')E.drawRect(sx,sy,x,y,p,filled);
      else if(tool==='circle')E.drawCircle(sx,sy,x,y,p,filled);
      else if(tool==='ellipse')E.drawEllipse(sx,sy,x,y,p,filled);
      render();
    }
  }
  function onUp(){if(!drawing)return;if(snap)pushH();if(tool==='move'&&mvStart){pushH();mvStart=null;}drawing=false;snap=null;}
  function clearLayer(){pushH();ap()?.fill(0);render();}
  function invertLayer(){pushH();const px=ap();if(px)for(let i=0;i<px.length;i++)px[i]=px[i]?0:1;render();}
  async function sendToOled(){s.toast('An OLED gesendet','ok');}

  /* ═══ PANEL D&D ═══ */
  let lpanels=$state(['preview','props','layers']), rpanels=$state(['tools','display','color']);
  let pdragId=$state(null), pdropSide=$state(null);
  function pDragStart(e,id){pdragId=id;e.dataTransfer.setData('application/x-oled-panel',id);e.dataTransfer.effectAllowed='move';}
  function pDragEnd(){pdragId=null;pdropSide=null;}
  function sDragOver(e,side){if(!e.dataTransfer.types.includes('application/x-oled-panel'))return;e.preventDefault();pdropSide=side;}
  function sDragLeave(e){if(!e.currentTarget.contains(e.relatedTarget))pdropSide=null;}
  function sDrop(e,side){e.preventDefault();const id=e.dataTransfer.getData('application/x-oled-panel');if(!id)return;lpanels=lpanels.filter(p=>p!==id);rpanels=rpanels.filter(p=>p!==id);if(side==='left')lpanels=[...lpanels,id];else rpanels=[...rpanels,id];pdragId=null;pdropSide=null;}

  function onKey(e){if(e.target.tagName==='INPUT'||e.target.tagName==='TEXTAREA')return;if(e.ctrlKey&&e.key==='z'){undo();e.preventDefault();}if(e.ctrlKey&&e.key==='y'){redo();e.preventDefault();}if(e.key==='g'){showGrid=!showGrid;render();}if(e.key==='+')zoom=Math.min(16,zoom+1);if(e.key==='-')zoom=Math.max(2,zoom-1);const t=drawTools.find(t=>t.key===e.key.toUpperCase());if(t&&!e.ctrlKey)tool=t.id;}

  /* Panel-Metadaten */
  const _pd = { tools:{icon:'pen',label:'Werkzeuge',c:false}, display:{icon:'eye',label:'Anzeige',c:true}, color:{icon:'palette',label:'Farbe',c:false}, preview:{icon:'display',label:'Vorschau',c:false}, props:{icon:'sliders',label:'Eigenschaften',c:true}, layers:{icon:'layer-group',label:'Ebenen',c:false} };
  function panelIcon(id) { return _pd[id]?.icon || 'circle'; }
  function panelLabel(id) { return _pd[id]?.label || id; }
  function panelCollapsible(id) { return _pd[id]?.c ?? true; }

  onMount(()=>{pushH();render();});
  $effect(()=>{zoom;showGrid;render();});
</script>

<svelte:window onkeydown={onKey} />

{#snippet panelContent(id)}
  {#if id==='tools'}
    <div class="tool-grid">{#each drawTools as t}<button class="tool-btn" class:active={tool===t.id} onclick={()=>tool=t.id} title="{t.label} ({t.key})"><i class="fa-solid {t.icon}"></i></button>{/each}</div>
    {#if tool==='pencil'||tool==='eraser'}<div class="pr"><span>Größe</span><input type="range" min="1" max="8" value={penSize} oninput={(e)=>penSize=+e.target.value}><span class="pv">{penSize}</span></div>{/if}
    {#if tool==='rect'||tool==='circle'||tool==='ellipse'}<div class="pr"><span>Gefüllt</span><button class="tog" class:on={filled} onclick={()=>filled=!filled}></button></div>{/if}
    {#if tool==='text'}<div class="pr"><span>Text</span><input type="text" class="ti" bind:value={textInput} maxlength="20"></div><div class="pr"><span>Größe</span><input type="range" min="1" max="3" value={textScale} oninput={(e)=>textScale=+e.target.value}><span class="pv">{textScale}×</span></div>{/if}
    <div class="ag"><button class="ab" onclick={undo}><i class="fa-solid fa-rotate-left"></i></button><button class="ab" onclick={redo}><i class="fa-solid fa-rotate-right"></i></button><button class="ab" onclick={clearLayer}><i class="fa-solid fa-trash-can"></i></button><button class="ab" onclick={invertLayer}><i class="fa-solid fa-circle-half-stroke"></i></button></div>
  {:else if id==='display'}
    <div class="pr"><span>Zoom</span><input type="range" min="2" max="16" value={zoom} oninput={(e)=>zoom=+e.target.value}><span class="pv">{zoom}×</span></div>
    <div class="pr"><span>Raster</span><button class="tog" class:on={showGrid} onclick={()=>{showGrid=!showGrid;}}></button></div>
  {:else if id==='color'}
    <div class="cp"><div class="cs white" class:active={tool!=='eraser'} onclick={()=>{if(tool==='eraser')tool='pencil';}} title="Weiß"></div><div class="cs black" class:active={tool==='eraser'} onclick={()=>tool='eraser'} title="Schwarz"></div></div>
  {:else if id==='preview'}
    <div class="pv-box"><div class="pv-bezel"><canvas bind:this={previewEl} width={W} height={H} class="pv-canvas"></canvas></div></div>
    <button class="send-btn" onclick={sendToOled}><i class="fa-solid fa-paper-plane"></i> An OLED senden</button>
  {:else if id==='props'}
    <div class="rr"><span>Position</span><span class="mono">{cursorX>=0?`${cursorX}, ${cursorY}`:'—'}</span></div>
    <div class="rr"><span>Ebene</span><span class="mono">{gl(activeLayer)?.name||'—'}</span></div>
    <div class="rr"><span>Pixel</span><span class="mono">{ap()?.reduce((a,v)=>a+v,0)||0}</span></div>
  {:else if id==='layers'}
    <div class="ll">{#each [...layers].reverse() as layer, ri}{@const idx=layers.length-1-ri}<div class="li" class:active={layer.id===activeLayer} class:drag-over={ldOver===idx} draggable="true" onclick={()=>activeLayer=layer.id} ondragstart={(e)=>ldStart(e,idx)} ondragover={(e)=>ldDragOver(e,idx)} ondrop={(e)=>ldDrop(e,idx)} ondragend={ldEnd}><span class="lh"><i class="fa-solid fa-grip-vertical"></i></span><button class="lv" onclick={(e)=>{e.stopPropagation();toggleVis(layer.id);render();}}><i class="fa-solid {layer.visible?'fa-eye':'fa-eye-slash'}"></i></button><span class="ln" contenteditable="false" ondblclick={(e)=>{e.target.contentEditable='true';e.target.focus();}} onblur={(e)=>{e.target.contentEditable='false';layers=layers.map(l=>l.id===layer.id?{...l,name:e.target.textContent}:l);}} onkeydown={(e)=>{if(e.key==='Enter'){e.preventDefault();e.target.blur();}}}>{layer.name}</span></div>{/each}</div>
    <div class="la"><button class="lab" onclick={()=>addLayer()}><i class="fa-solid fa-plus"></i></button><button class="lab" onclick={()=>dupLayer(activeLayer)}><i class="fa-solid fa-copy"></i></button><button class="lab" onclick={()=>rmLayer(activeLayer)}><i class="fa-solid fa-trash"></i></button></div>
  {/if}
{/snippet}

<div class="studio">
  <WidgetStrip {widgets} onPlace={placeWidget} />
  <div class="editor-main">
    <div class="side-panel" ondragover={(e)=>sDragOver(e,'left')} ondragleave={sDragLeave} ondrop={(e)=>sDrop(e,'left')} class:drop-target={pdropSide==='left'}>
      {#each lpanels as pid (pid)}
        <PanelWrapper id={pid} icon="fa-{panelIcon(pid)}" label={panelLabel(pid)} collapsible={panelCollapsible(pid)} onDragStart={pDragStart}>
          {@render panelContent(pid)}
        </PanelWrapper>
      {/each}
    </div>
    <div class="canvas-area">
      <div class="canvas-scroll"><canvas bind:this={canvasEl} width={W*zoom} height={H*zoom} onpointerdown={onDown} onpointermove={onMove} onpointerup={onUp} style="width:{W*zoom}px;height:{H*zoom}px"></canvas></div>
      <div class="status-bar"><span>{cursorX>=0?`${cursorX}, ${cursorY}`:''}</span><span>{zoom}×</span></div>
    </div>
    <div class="side-panel" ondragover={(e)=>sDragOver(e,'right')} ondragleave={sDragLeave} ondrop={(e)=>sDrop(e,'right')} class:drop-target={pdropSide==='right'}>
      {#each rpanels as pid (pid)}
        <PanelWrapper id={pid} icon="fa-{panelIcon(pid)}" label={panelLabel(pid)} collapsible={panelCollapsible(pid)} onDragStart={pDragStart}>
          {@render panelContent(pid)}
        </PanelWrapper>
      {/each}
    </div>
  </div>
</div>


<style>
  .studio { display: flex; flex-direction: column; height: 100%; overflow: hidden; }
  .editor-main { display: flex; flex: 1; min-height: 0; }

  .side-panel { width: 300px; flex-shrink: 0; background: var(--bg-base); padding: 4px; display: flex; flex-direction: column; gap: 4px; overflow-y: auto; }
  .side-panel:first-child { border-right: 1px solid var(--border); }
  .side-panel:last-child { border-left: 1px solid var(--border); }
  .drop-target { outline: 2px dashed var(--accent); outline-offset: -2px; background: rgba(0,180,255,0.04); }

  .canvas-area { flex: 1; display: flex; flex-direction: column; min-width: 0; background: #1a1a22; }
  .canvas-scroll { flex: 1; overflow: auto; display: flex; align-items: center; justify-content: center; }
  .canvas-scroll canvas { image-rendering: pixelated; touch-action: none; cursor: crosshair; box-shadow: 0 0 0 1px var(--border), 0 4px 20px rgba(0,0,0,0.4); }
  .status-bar { display: flex; gap: 16px; padding: 4px 12px; background: var(--bg-base); border-top: 1px solid var(--border); flex-shrink: 0; font: 500 var(--fs-xs) var(--mono); color: var(--text-muted); }

  /* Tool Grid */
  .tool-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 4px; margin-bottom: 8px; }
  .tool-btn { aspect-ratio: 1; border-radius: var(--radius-sm); border: 1px solid var(--border); background: var(--bg-surface); color: var(--text-muted); cursor: pointer; font-size: var(--fs-sm); display: flex; align-items: center; justify-content: center; transition: all 120ms; }
  .tool-btn:hover { background: rgba(255,255,255,0.04); color: var(--text-primary); }
  .tool-btn.active { color: var(--accent); background: rgba(0,180,255,0.1); border-color: var(--accent); }
  .ag { display: grid; grid-template-columns: repeat(4, 1fr); gap: 4px; margin-top: 6px; }
  .ab { height: 32px; border-radius: var(--radius-sm); border: 1px solid var(--border); background: var(--bg-elevated); color: var(--text-muted); cursor: pointer; font-size: var(--fs-xs); display: flex; align-items: center; justify-content: center; }
  .ab:hover { border-color: var(--accent); color: var(--accent); }

  /* Property Rows */
  .pr { display: flex; align-items: center; gap: 8px; font: 500 var(--fs-sm) var(--font); color: var(--text-secondary); }
  .pr span:first-child { width: 55px; flex-shrink: 0; }
  .pr input[type=range] { flex: 1; }
  .pv { font: 600 var(--fs-sm) var(--mono); color: var(--text-primary); min-width: 32px; text-align: right; }
  .ti { flex: 1; padding: 5px 8px; border: 1px solid var(--border); background: var(--bg-elevated); color: var(--text-primary); border-radius: var(--radius-sm); font: 500 var(--fs-sm) var(--mono); }
  .tog { width: 34px; height: 18px; border-radius: 9px; border: none; background: rgba(255,255,255,0.1); cursor: pointer; position: relative; transition: background 150ms; }
  .tog.on { background: var(--green); }
  .tog::after { content:''; position:absolute; top:2px; left:2px; width:14px; height:14px; border-radius:50%; background:#fff; transition:transform 150ms; }
  .tog.on::after { transform: translateX(16px); }

  /* Colors */
  .cp { display: flex; gap: 8px; }
  .cs { width: 32px; height: 32px; border-radius: var(--radius-sm); border: 2px solid var(--border); cursor: pointer; }
  .cs.white { background: #fff; } .cs.black { background: #000; }
  .cs.active { border-color: var(--accent); box-shadow: 0 0 8px rgba(0,180,255,0.3); }

  /* Preview */
  .pv-box { display: flex; justify-content: center; }
  .pv-bezel { background: #000; padding: 3px; border-radius: 4px; border: 2px solid #444; }
  .pv-canvas { display: block; width: 128px; height: 64px; image-rendering: pixelated; }
  .send-btn { width: 100%; padding: 8px; border-radius: var(--radius-sm); border: 1px solid var(--accent); background: var(--accent-dim); color: var(--accent); font: 500 var(--fs-sm) var(--font); cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 6px; }
  .send-btn:hover { background: var(--accent); color: #fff; }

  /* Properties */
  .rr { display: flex; justify-content: space-between; font: 500 var(--fs-sm) var(--font); color: var(--text-muted); padding: 3px 0; }
  .mono { font-family: var(--mono); color: var(--text-secondary); }

  /* Layers */
  .ll { display: flex; flex-direction: column; gap: 2px; }
  .li { display: flex; align-items: center; gap: 4px; padding: 5px 6px; border-radius: var(--radius-sm); cursor: pointer; font: 500 var(--fs-sm) var(--font); color: var(--text-muted); background: var(--bg-surface); border: 1px solid transparent; transition: all 120ms; }
  .li:hover { background: var(--bg-elevated); }
  .li.active { border-color: var(--accent); color: var(--accent); background: rgba(0,180,255,0.06); }
  .li.drag-over { border-color: var(--green); border-style: dashed; }
  .lh { color: var(--text-muted); cursor: grab; font-size: var(--fs-xs); padding: 0 2px; }
  .lv { background: none; border: none; color: inherit; cursor: pointer; font-size: var(--fs-sm); padding: 2px; }
  .ln { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .la { display: flex; gap: 3px; margin-top: 6px; }
  .lab { flex: 1; padding: 5px; border-radius: var(--radius-sm); border: 1px solid var(--border); background: var(--bg-elevated); color: var(--text-muted); cursor: pointer; font-size: var(--fs-sm); text-align: center; }
  .lab:hover { border-color: var(--accent); color: var(--accent); }

  @media (max-width: 900px) { .side-panel { width: 200px; } }
</style>
