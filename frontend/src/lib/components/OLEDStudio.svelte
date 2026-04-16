<script>
  import { onMount, onDestroy } from 'svelte';
  import PanelWrapper from './oled/PanelWrapper.svelte';
  import * as E from './oled/engine.js';
  import { TABS, ALL_SOURCES, DATA_SOURCES, DISPLAY_MODES, getSource, getModesForType, getSourcesForTab, HISTORY_KEYS, defaultOpts, createWidget } from './oled/catalog.js';
  import { renderWidget, getWidgetSize } from './oled/widgetRenderer.js';
  let { state: s } = $props();
  const W = E.W, H = E.H;

  /* ═══ EDITOR-MODUS ═══ */
  let editorMode = $state('widget'); // 'widget' | 'raster'

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

  /* ═══ SCREEN-VERWALTUNG ═══ */
  let screens = $state([{ id: 0, name: 'Screen 1', widgets: [], layers: [{ id: 0, name: 'Hintergrund', pixels: Array.from(new Uint8Array(W*H)), visible: true }], thumbnail: '' }]);
  let activeScreen = $state(0);
  let rotation = $state(false);
  let rotationInterval = $state(10);
  let _screenId = 1;

  function saveCurrentScreen() {
    const idx = screens.findIndex(sc => sc.id === activeScreen);
    if (idx < 0) return;
    screens[idx].widgets = JSON.parse(JSON.stringify(placedWidgets));
    screens[idx].layers = layers.map(l => ({ ...l, pixels: Array.from(l.pixels) }));
    screens[idx].thumbnail = E.compositeToDataUrl(layers);
    screens = [...screens];
  }
  function addScreen() { saveCurrentScreen(); const id = _screenId++; screens = [...screens, { id, name: `Screen ${id+1}`, widgets: [], layers: [{ id: 0, name: 'Hintergrund', pixels: Array.from(new Uint8Array(W*H)), visible: true }], thumbnail: '' }]; switchScreen(id); }
  function removeScreen(id) { if (screens.length <= 1) return; screens = screens.filter(sc => sc.id !== id); if (activeScreen === id) switchScreen(screens[0].id); }
  function switchScreen(id) {
    saveCurrentScreen(); activeScreen = id;
    const sc = screens.find(sc => sc.id === id); if (!sc) return;
    placedWidgets = sc.widgets ? JSON.parse(JSON.stringify(sc.widgets)) : [];
    layers = sc.layers ? sc.layers.map(l => ({ ...l, pixels: new Uint8Array(l.pixels) })) : [{ id: 0, name: 'Hintergrund', pixels: new Uint8Array(W*H), visible: true }];
    activeLayer = layers[0]?.id || 0; _nid = Math.max(0, ...layers.map(l => l.id)) + 1;
    selectedWidget = -1; selectedWidgets = new Set(); renderAll();
  }
  function duplicateScreen() { saveCurrentScreen(); const src = screens.find(sc => sc.id === activeScreen); if (!src) return; const id = _screenId++; screens = [...screens, { id, name: src.name+' Kopie', widgets: JSON.parse(JSON.stringify(src.widgets)), layers: JSON.parse(JSON.stringify(src.layers)), thumbnail: src.thumbnail }]; switchScreen(id); }

  /* Screen D&D Reorder */
  let scDragFrom = $state(-1), scDragOver = $state(-1);
  function scDragStart(e, idx) { scDragFrom = idx; e.dataTransfer.effectAllowed = 'move'; }
  function scDragOverFn(e, idx) { e.preventDefault(); scDragOver = idx; }
  function scDrop(e, idx) { e.preventDefault(); scDragOver = -1; if (scDragFrom === idx) return; const arr = [...screens]; const [m] = arr.splice(scDragFrom, 1); arr.splice(idx, 0, m); screens = arr; scDragFrom = -1; }
  function scDragEnd() { scDragFrom = -1; scDragOver = -1; }

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
  let snapGrid = $state(0);
  function snapPos(v) { return snapGrid > 0 ? Math.round(v / snapGrid) * snapGrid : v; }

  const drawTools = [
    {id:'pencil',icon:'fa-pen',label:'Stift',key:'P'},{id:'eraser',icon:'fa-eraser',label:'Radierer',key:'E'},
    {id:'line',icon:'fa-minus',label:'Linie',key:'L'},{id:'rect',icon:'fa-square',label:'Rechteck',key:'R'},
    {id:'circle',icon:'fa-circle',label:'Kreis',key:'C'},{id:'ellipse',icon:'fa-egg',label:'Ellipse',key:'O'},
    {id:'fill',icon:'fa-fill-drip',label:'Fuellen',key:'F'},{id:'text',icon:'fa-font',label:'Text',key:'T'},
    {id:'move',icon:'fa-up-down-left-right',label:'Verschieben',key:'V'},
  ];

  /* ═══ WIDGETS (neues dynamisches System) ═══ */
  let placedWidgets = $state([]);
  let selectedWidget = $state(-1);
  let selectedWidgets = $state(new Set());
  let ctxMenu = $state(null);

  /* Sparkline History */
  const _hist = { cpu: [], temp: [], ram: [], fan_speed: [], net_rx: [], net_tx: [] };
  const HIST_LEN = 30;

  function placeNewWidget(sourceId, display, x = 4, y = 4) {
    const w = createWidget(sourceId, display, x, y);
    placedWidgets = [...placedWidgets, w];
    selectedWidget = placedWidgets.length - 1;
    selectedWidgets = new Set([selectedWidget]);
    tool = 'move';
    renderAll();
  }

  function removeWidget(idx) {
    placedWidgets = placedWidgets.filter((_, i) => i !== idx);
    if (selectedWidget >= placedWidgets.length) selectedWidget = placedWidgets.length - 1;
    selectedWidgets = new Set(); renderAll();
  }

  function updateWidgetOpt(idx, key, val) {
    placedWidgets[idx].opts[key] = val;
    placedWidgets = [...placedWidgets]; renderAll();
  }

  /* ═══ WIDGET-EDITOR STATE ═══ */
  let activeTab = $state('cpu');
  let configSource = $state(null);   // Datenquelle die gerade konfiguriert wird
  let configDisplay = $state(null);  // Gewaehlter Display-Modus

  function selectSource(src) {
    configSource = src;
    const modes = getModesForType(src.type);
    configDisplay = modes[0]?.id || 'zahl';
  }

  function addConfiguredWidget() {
    if (!configSource) return;
    placeNewWidget(configSource.id, configDisplay);
    s.toast(`${configSource.label} hinzugefuegt`, 'ok');
  }

  /* ═══ WETTER (Open-Meteo API + Ortssuche) ═══ */
  let weather = $state(null);
  let weatherLocation = $state(JSON.parse(localStorage.getItem('pp-weather-loc') || 'null') || { name: 'Zeitz', lat: 51.05, lon: 12.13 });
  let locationSearch = $state('');
  let locationResults = $state([]);

  async function fetchWeather() {
    if (!weatherLocation) return;
    try {
      const r = await fetch(`https://api.open-meteo.com/v1/forecast?latitude=${weatherLocation.lat}&longitude=${weatherLocation.lon}&current=temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code,surface_pressure&timezone=auto`);
      const d = await r.json();
      weather = { ...d.current, location: weatherLocation.name };
    } catch {}
  }
  async function searchLocation(q) {
    if (q.length < 2) { locationResults = []; return; }
    try {
      const r = await fetch(`https://geocoding-api.open-meteo.com/v1/search?name=${encodeURIComponent(q)}&count=5&language=de`);
      const d = await r.json();
      locationResults = (d.results || []).map(r => ({ name: r.name, country: r.country, admin: r.admin1, lat: r.latitude, lon: r.longitude }));
    } catch { locationResults = []; }
  }
  function selectLocation(loc) {
    weatherLocation = { name: loc.name, lat: loc.lat, lon: loc.lon };
    localStorage.setItem('pp-weather-loc', JSON.stringify(weatherLocation));
    locationSearch = ''; locationResults = [];
    fetchWeather(); s.toast(`Wetter-Ort: ${loc.name}`, 'ok');
  }
  let _searchTimer = 0;
  function onLocationInput(e) { locationSearch = e.target.value; clearTimeout(_searchTimer); _searchTimer = setTimeout(() => searchLocation(locationSearch), 300); }

  /* ═══ RENDERING ═══ */
  let canvasEl = $state(null), previewEl = $state(null);

  function renderAll() {
    // Widgets in Layer 0 rendern
    const px = layers[0].pixels; px.fill(0);
    for (const w of placedWidgets) {
      renderWidget(px, w, s.stats, weather, s.stats?.history || _hist);
    }
    layers = [...layers]; render(); autoSave();
  }

  function render() {
    const comp = E.composite(layers);
    if (canvasEl) {
      E.renderCanvas(canvasEl.getContext('2d'), comp, zoom, showGrid);
      const ctx = canvasEl.getContext('2d');
      const selSet = selectedWidgets.size > 0 ? selectedWidgets : (selectedWidget >= 0 ? new Set([selectedWidget]) : new Set());
      for (const idx of selSet) {
        const w = placedWidgets[idx]; if (!w) continue;
        const sz = getWidgetSize(w);
        ctx.strokeStyle = idx === selectedWidget ? 'rgba(0,180,255,0.7)' : 'rgba(0,232,138,0.5)';
        ctx.lineWidth = 1; ctx.setLineDash([4, 2]);
        ctx.strokeRect(w.x * zoom - 1, w.y * zoom - 1, sz.w * zoom + 2, sz.h * zoom + 2);
        ctx.setLineDash([]);
      }
    }
    if (previewEl) E.renderPreview(previewEl.getContext('2d'), comp);
  }

  /* Timer: Rendering 5fps, Stats 1x/s */
  let _renderTimer, _statsTimer;
  function startTimers() {
    _renderTimer = setInterval(() => { if (placedWidgets.length > 0) renderAll(); }, 200);
    _statsTimer = setInterval(() => {
      const st = s.stats;
      _hist.cpu.push(st?.cpu?.percent || 0); _hist.temp.push(st?.cpu?.temp || 0);
      _hist.ram.push(st?.ram?.percent || 0); _hist.fan_speed.push(st?.fan?.rpm || 0);
      _hist.net_rx.push(st?.network?.rx_bytes_sec || 0); _hist.net_tx.push(st?.network?.tx_bytes_sec || 0);
      for (const k of Object.keys(_hist)) if (_hist[k].length > HIST_LEN) _hist[k].shift();
    }, 1000);
  }
  function stopTimers() { clearInterval(_renderTimer); clearInterval(_statsTimer); }

  /* ═══ MAUS ═══ */
  let drawing=$state(false), sx=0, sy=0, lx=-1, ly=-1, snap=null, mvStart=null;
  function m2p(e) { const r=canvasEl.getBoundingClientRect(); return [Math.max(0,Math.min(W-1,Math.floor((e.clientX-r.left)/zoom))),Math.max(0,Math.min(H-1,Math.floor((e.clientY-r.top)/zoom)))]; }

  function hitTestWidget(x, y) {
    for (let i = placedWidgets.length - 1; i >= 0; i--) {
      const w = placedWidgets[i]; const sz = getWidgetSize(w);
      if (x >= w.x && x < w.x + sz.w && y >= w.y && y < w.y + sz.h) return i;
    }
    return -1;
  }

  let widgetDrag = null;
  function onDown(e) {
    if (!canvasEl) return; ctxMenu = null;
    const [x,y]=m2p(e);
    if (tool === 'move') {
      const hit = hitTestWidget(x, y);
      if (hit >= 0) {
        if (e.shiftKey) { const ns = new Set(selectedWidgets); if (ns.has(hit)) ns.delete(hit); else ns.add(hit); selectedWidgets = ns; selectedWidget = hit; render(); return; }
        selectedWidget = hit;
        if (!selectedWidgets.has(hit)) selectedWidgets = new Set([hit]);
        const origins = new Map(); for (const idx of selectedWidgets) origins.set(idx, { x: placedWidgets[idx].x, y: placedWidgets[idx].y });
        widgetDrag = { idx: hit, startX: x, startY: y, origX: placedWidgets[hit].x, origY: placedWidgets[hit].y, origins };
        drawing = true; render(); return;
      }
    }
    const hit2 = hitTestWidget(x, y); selectedWidget = hit2; selectedWidgets = hit2 >= 0 ? new Set([hit2]) : new Set(); render();
    drawing=true; sx=x; sy=y; lx=x; ly=y;
    if (tool==='pencil'||tool==='eraser') { pushH(); plot(x,y); render(); }
    else if (tool==='fill') { pushH(); E.floodFill(ap(),x,y,gp(x,y)===1?0:1); render(); drawing=false; }
    else if (tool==='text') { pushH(); E.drawText(ap(),textInput,x,y,textScale); render(); drawing=false; }
    else if (tool==='move') { mvStart={x,y,snap:new Uint8Array(ap())}; }
    else { snap = new Uint8Array(ap()); }
  }
  function onMove(e) {
    if (!canvasEl) return; const [x,y]=m2p(e); cursorX=x; cursorY=y;
    if (!drawing) return;
    if (widgetDrag) {
      const dx = x - widgetDrag.startX, dy = y - widgetDrag.startY;
      if (widgetDrag.origins && widgetDrag.origins.size > 1) {
        for (const [idx, orig] of widgetDrag.origins) { placedWidgets[idx].x = Math.max(0, Math.min(W-1, orig.x + dx)); placedWidgets[idx].y = Math.max(0, Math.min(H-1, orig.y + dy)); }
      } else { placedWidgets[widgetDrag.idx].x = Math.max(0, Math.min(W-1, widgetDrag.origX + dx)); placedWidgets[widgetDrag.idx].y = Math.max(0, Math.min(H-1, widgetDrag.origY + dy)); }
      placedWidgets = [...placedWidgets]; renderAll(); return;
    }
    if (tool==='pencil'||tool==='eraser') { E.bresenhamLine(lx,ly,x,y,plot); lx=x; ly=y; render(); }
    else if (tool==='move'&&mvStart) { const layer=gl(activeLayer); if(!layer)return; const dx=x-mvStart.x,dy=y-mvStart.y; layer.pixels.fill(0); for(let py=0;py<H;py++)for(let px=0;px<W;px++)if(mvStart.snap[py*W+px]){const nx=px+dx,ny=py+dy;if(nx>=0&&nx<W&&ny>=0&&ny<H)layer.pixels[ny*W+nx]=1;} layers=[...layers]; render(); }
    else if (snap) { gl(activeLayer).pixels=new Uint8Array(snap); const p=(px,py)=>sp(px,py,1); if(tool==='line')E.bresenhamLine(sx,sy,x,y,p); else if(tool==='rect')E.drawRect(sx,sy,x,y,p,filled); else if(tool==='circle')E.drawCircle(sx,sy,x,y,p,filled); else if(tool==='ellipse')E.drawEllipse(sx,sy,x,y,p,filled); render(); }
  }
  function onUp(){if(!drawing)return;if(widgetDrag){widgetDrag=null;drawing=false;return;}if(snap)pushH();if(tool==='move'&&mvStart){pushH();mvStart=null;}drawing=false;snap=null;}

  function onContext(e) { e.preventDefault(); if (!canvasEl) return; const [x,y]=m2p(e); const hit = hitTestWidget(x,y); if (hit>=0) { selectedWidget=hit; if(!selectedWidgets.has(hit))selectedWidgets=new Set([hit]); ctxMenu={x:e.clientX,y:e.clientY,widgetIdx:hit}; render(); } else ctxMenu=null; }
  function ctxAction(action) {
    const idx=ctxMenu?.widgetIdx; if(idx==null||idx<0){ctxMenu=null;return;}
    if(action==='dup'){const src=placedWidgets[idx];placedWidgets=[...placedWidgets,{...JSON.parse(JSON.stringify(src)),id:Date.now(),x:src.x+4,y:src.y+4}];selectedWidget=placedWidgets.length-1;selectedWidgets=new Set([selectedWidget]);renderAll();}
    else if(action==='del'){placedWidgets=placedWidgets.filter((_,i)=>i!==idx);selectedWidget=-1;selectedWidgets=new Set();renderAll();}
    else if(action==='front'){const[w]=placedWidgets.splice(idx,1);placedWidgets=[...placedWidgets,w];selectedWidget=placedWidgets.length-1;selectedWidgets=new Set([selectedWidget]);renderAll();}
    else if(action==='back'){const[w]=placedWidgets.splice(idx,1);placedWidgets=[w,...placedWidgets];selectedWidget=0;selectedWidgets=new Set([0]);renderAll();}
    ctxMenu=null;
  }

  function clearLayer(){pushH();ap()?.fill(0);render();}
  function invertLayer(){pushH();const px=ap();if(px)for(let i=0;i<px.length;i++)px[i]=px[i]?0:1;render();}

  /* ═══ KEYBOARD ═══ */
  function onKey(e) {
    if(e.target.tagName==='INPUT'||e.target.tagName==='TEXTAREA') return;
    if(e.ctrlKey&&e.key==='z'){undo();e.preventDefault();}
    if(e.ctrlKey&&e.key==='y'){redo();e.preventDefault();}
    if(e.ctrlKey&&e.key==='d'){ const indices=selectedWidgets.size>0?[...selectedWidgets]:(selectedWidget>=0?[selectedWidget]:[]); if(indices.length>0){const ns=new Set();for(const idx of indices){const src=placedWidgets[idx];placedWidgets=[...placedWidgets,{...JSON.parse(JSON.stringify(src)),id:Date.now()+Math.random(),x:src.x+4,y:src.y+4}];ns.add(placedWidgets.length-1);}selectedWidgets=ns;selectedWidget=[...ns][0];renderAll();e.preventDefault();return;} }
    if(e.ctrlKey&&e.key==='a'){selectedWidgets=new Set(placedWidgets.map((_,i)=>i));if(placedWidgets.length>0)selectedWidget=0;render();e.preventDefault();return;}
    if((e.key==='Delete'||e.key==='Backspace')){const indices=selectedWidgets.size>0?[...selectedWidgets].sort((a,b)=>b-a):(selectedWidget>=0?[selectedWidget]:[]);if(indices.length>0){for(const idx of indices)placedWidgets.splice(idx,1);placedWidgets=[...placedWidgets];selectedWidget=-1;selectedWidgets=new Set();renderAll();e.preventDefault();return;}}
    if(['ArrowUp','ArrowDown','ArrowLeft','ArrowRight'].includes(e.key)){const indices=selectedWidgets.size>0?[...selectedWidgets]:(selectedWidget>=0?[selectedWidget]:[]);if(indices.length>0){const step=e.shiftKey?(snapGrid||8):1;for(const idx of indices){const w=placedWidgets[idx];if(e.key==='ArrowLeft')w.x=Math.max(0,w.x-step);if(e.key==='ArrowRight')w.x=Math.min(W-1,w.x+step);if(e.key==='ArrowUp')w.y=Math.max(0,w.y-step);if(e.key==='ArrowDown')w.y=Math.min(H-1,w.y+step);if(snapGrid>0){w.x=snapPos(w.x);w.y=snapPos(w.y);}}placedWidgets=[...placedWidgets];renderAll();e.preventDefault();return;}}
    if(e.key==='g'){showGrid=!showGrid;render();}
    if(e.key==='+')zoom=Math.min(16,zoom+1);if(e.key==='-')zoom=Math.max(2,zoom-1);
    const t=drawTools.find(t=>t.key===e.key.toUpperCase());if(t&&!e.ctrlKey)tool=t.id;
  }

  /* ═══ SEND / LOAD ═══ */
  async function sendToOled() {
    saveCurrentScreen();
    try {
      const screenConfigs = screens.map(sc => ({
        type: 'system', name: sc.name,
        widgets: (sc.widgets || []).map(w => ({ source: w.source, display: w.display, x: w.x, y: w.y, name: w.name, opts: w.opts })),
      }));
      if (screenConfigs.length > 0) await s.updateOledScreen(0, screenConfigs[0]);
      for (let i = 1; i < screenConfigs.length; i++) await s.addOledScreen(screenConfigs[i]);
      const oledScreens = s.oled?.screens || [];
      while (oledScreens.length > screenConfigs.length && oledScreens.length > 1) { await s.removeOledScreen(oledScreens.length - 1); oledScreens.pop(); }
      if (rotation) { await s.setOledRotation(rotationInterval); await s.setOledMode('auto'); } else { await s.setOledMode('auto'); }
      s.toast(`${screenConfigs.length} Screen(s) gesendet`, 'ok');
    } catch (e) { s.toast('Fehler: ' + (e.message||e), 'err'); }
  }

  async function loadFromOled() {
    try {
      const backendScreens = s.oled?.screens;
      if (!backendScreens || backendScreens.length === 0) { s.toast('Keine Screens im Backend', 'info'); return; }
      const newScreens = backendScreens.map((bs, i) => ({
        id: i, name: bs.name || `Screen ${i+1}`,
        widgets: (bs.widgets || []).map(bw => ({ id: Date.now()+Math.random(), source: bw.source, display: bw.display, x: bw.x||0, y: bw.y||0, name: bw.name||'', opts: bw.opts||{} })),
        layers: [{ id: 0, name: 'Hintergrund', pixels: Array.from(new Uint8Array(W*H)), visible: true }], thumbnail: '',
      }));
      screens = newScreens; _screenId = screens.length; activeScreen = screens[0]?.id ?? 0;
      const sc = screens[0]; placedWidgets = sc.widgets ? JSON.parse(JSON.stringify(sc.widgets)) : [];
      layers = sc.layers.map(l => ({ ...l, pixels: new Uint8Array(l.pixels) })); activeLayer = 0; _nid = 1; selectedWidget = -1;
      renderAll(); s.toast(`${newScreens.length} Screen(s) geladen`, 'ok');
    } catch (e) { s.toast('Fehler: ' + (e.message||e), 'err'); }
  }

  async function exportScreens() { saveCurrentScreen(); const data = JSON.stringify({ screens, version: '2.0' }, null, 2); const blob = new Blob([data], { type: 'application/json' }); const url = URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url; a.download = `pyroplus-oled-${new Date().toISOString().slice(0,10)}.json`; a.click(); URL.revokeObjectURL(url); s.toast('Exportiert', 'ok'); }
  async function importScreens() { const input = document.createElement('input'); input.type = 'file'; input.accept = '.json'; input.onchange = async (e) => { try { const text = await e.target.files[0].text(); const data = JSON.parse(text); if (data.screens?.length > 0) { screens = data.screens.map((sc, i) => ({ ...sc, id: i, layers: sc.layers || [{ id: 0, name: 'Hintergrund', pixels: Array.from(new Uint8Array(W*H)), visible: true }] })); _screenId = screens.length; switchScreen(screens[0].id); s.toast(`${screens.length} Screen(s) importiert`, 'ok'); } } catch (err) { s.toast('Import-Fehler: ' + err.message, 'err'); } }; input.click(); }

  /* ═══ PROFILE ═══ */
  let profiles = $state(JSON.parse(localStorage.getItem('pp-oled-profiles') || '[]'));
  let activeProfile = $state('');
  let showProfileSave = $state(false), profileSaveName = $state('');
  function saveProfile(name) { if (!name) return; saveCurrentScreen(); const p = { name, created: new Date().toISOString(), screens: JSON.parse(JSON.stringify(screens)), rotation, rotationInterval }; profiles = [...profiles.filter(p => p.name !== name), p]; localStorage.setItem('pp-oled-profiles', JSON.stringify(profiles)); activeProfile = name; s.toast(`Profil "${name}" gespeichert`, 'ok'); }
  function loadProfile(p) { screens = p.screens.map((sc, i) => ({ ...sc, id: i })); _screenId = screens.length; rotation = p.rotation || false; rotationInterval = p.rotationInterval || 10; activeProfile = p.name; switchScreen(screens[0]?.id ?? 0); s.toast(`Profil "${p.name}" geladen`, 'ok'); }
  function deleteProfile(name) { profiles = profiles.filter(p => p.name !== name); localStorage.setItem('pp-oled-profiles', JSON.stringify(profiles)); if (activeProfile === name) activeProfile = ''; }

  /* ═══ PERSISTENZ ═══ */
  function saveState() { try { saveCurrentScreen(); localStorage.setItem('pp-oled-state', JSON.stringify({ screens: screens.map(sc => ({ ...sc, thumbnail: sc.thumbnail || '' })), activeScreen, rotation, rotationInterval, zoom, showGrid })); } catch {} }
  function loadState() { try { const raw = localStorage.getItem('pp-oled-state'); if (!raw) return; const data = JSON.parse(raw); if (data.screens?.length > 0) { screens = data.screens; _screenId = Math.max(0, ...screens.map(sc => sc.id)) + 1; } if (data.activeScreen !== undefined) activeScreen = data.activeScreen; if (data.rotation !== undefined) rotation = data.rotation; if (data.rotationInterval) rotationInterval = data.rotationInterval; if (data.zoom) zoom = data.zoom; if (data.showGrid !== undefined) showGrid = data.showGrid; const sc = screens.find(sc => sc.id === activeScreen) || screens[0]; if (sc) { placedWidgets = sc.widgets ? JSON.parse(JSON.stringify(sc.widgets)) : []; layers = sc.layers ? sc.layers.map(l => ({ ...l, pixels: new Uint8Array(l.pixels) })) : [{ id: 0, name: 'Hintergrund', pixels: new Uint8Array(W*H), visible: true }]; activeLayer = layers[0]?.id || 0; _nid = Math.max(0, ...layers.map(l => l.id)) + 1; } } catch {} }
  let _saveTimer = 0;
  function autoSave() { clearTimeout(_saveTimer); _saveTimer = setTimeout(saveState, 1000); }

  /* Canvas Drop */
  function onCanvasDrop(e) { const sid = e.dataTransfer.getData('application/x-widget-source'); const disp = e.dataTransfer.getData('application/x-widget-display'); if (!sid) return; e.preventDefault(); const rect = canvasEl.getBoundingClientRect(); const x = Math.max(0, Math.min(W-1, Math.floor((e.clientX - rect.left) / zoom))); const y = Math.max(0, Math.min(H-1, Math.floor((e.clientY - rect.top) / zoom))); placeNewWidget(sid, disp || 'zahl', snapGrid > 0 ? snapPos(x) : x, snapGrid > 0 ? snapPos(y) : y); }
  function onCanvasDragOver(e) { if (e.dataTransfer.types.includes('application/x-widget-source')) e.preventDefault(); }

  onMount(()=>{loadState();pushH();renderAll();startTimers();fetchWeather();setInterval(fetchWeather,300000);});
  onDestroy(()=>{stopTimers();saveState();});
  $effect(()=>{zoom;showGrid;render();autoSave();});
</script>

<svelte:window onkeydown={onKey} />

<div class="studio">
  <!-- ═══ LINKE SEITE: Canvas + Vorschau ═══ -->
  <div class="left-col">
    <div class="left-header">
      <span class="studio-title">OLED Studio</span>
      <div class="mode-switch">
        <button class:active={editorMode==='widget'} onclick={()=>editorMode='widget'}>Widget</button>
        <button class:active={editorMode==='raster'} onclick={()=>editorMode='raster'}>Raster</button>
      </div>
    </div>

    <!-- Profil-Leiste -->
    <div class="profile-bar">
      <div class="pb-chips">
        {#each profiles as p}
          <button class="pb-chip" class:active={activeProfile===p.name} onclick={()=>loadProfile(p)}>{p.name}<span class="pb-del" onclick={(e)=>{e.stopPropagation();deleteProfile(p.name);}}>&times;</span></button>
        {/each}
      </div>
      {#if showProfileSave}<input class="pb-input" type="text" placeholder="Name..." bind:value={profileSaveName} onkeydown={(e)=>{if(e.key==='Enter'&&profileSaveName){saveProfile(profileSaveName);showProfileSave=false;profileSaveName='';}if(e.key==='Escape')showProfileSave=false;}} />{/if}
      <button class="pb-btn" onclick={()=>{if(showProfileSave&&profileSaveName){saveProfile(profileSaveName);showProfileSave=false;profileSaveName='';}else{showProfileSave=!showProfileSave;profileSaveName=activeProfile||'';}}} title="Profil speichern"><i class="fa-solid fa-floppy-disk"></i></button>
    </div>

    <!-- Canvas -->
    <div class="canvas-wrap">
      <div class="canvas-scroll">
        <canvas bind:this={canvasEl} width={W*zoom} height={H*zoom} onpointerdown={onDown} onpointermove={onMove} onpointerup={onUp} oncontextmenu={onContext} ondrop={onCanvasDrop} ondragover={onCanvasDragOver} style="width:{W*zoom}px;height:{H*zoom}px"></canvas>
      </div>
      {#if ctxMenu}
        <div class="ctx-menu" style="left:{ctxMenu.x}px;top:{ctxMenu.y}px">
          <button class="ctx-item" onclick={()=>ctxAction('dup')}><i class="fa-solid fa-copy"></i> Duplizieren</button>
          <button class="ctx-item" onclick={()=>ctxAction('front')}><i class="fa-solid fa-arrow-up"></i> Nach vorne</button>
          <button class="ctx-item" onclick={()=>ctxAction('back')}><i class="fa-solid fa-arrow-down"></i> Nach hinten</button>
          <div class="ctx-sep"></div>
          <button class="ctx-item ctx-del" onclick={()=>ctxAction('del')}><i class="fa-solid fa-trash-can"></i> Loeschen</button>
        </div>
      {/if}
    </div>

    <!-- Vorschau + Aktionen -->
    <div class="left-bottom">
      <div class="pv-bezel"><canvas bind:this={previewEl} width={W} height={H} class="pv-canvas"></canvas></div>
      <div class="left-actions">
        <button class="act-btn primary" onclick={sendToOled}><i class="fa-solid fa-paper-plane"></i> Senden</button>
        <button class="act-btn" onclick={loadFromOled}><i class="fa-solid fa-download"></i> Laden</button>
        <button class="act-btn" onclick={exportScreens}><i class="fa-solid fa-file-export"></i></button>
        <button class="act-btn" onclick={importScreens}><i class="fa-solid fa-file-import"></i></button>
      </div>
    </div>

    <!-- Screen-Galerie -->
    <div class="screen-gallery">
      <div class="sg-strip">
        {#each screens as sc, i}
          <div class="sg-item" class:active={sc.id===activeScreen} draggable="true" onclick={()=>switchScreen(sc.id)} ondragstart={(e)=>scDragStart(e,i)} ondragover={(e)=>scDragOverFn(e,i)} ondrop={(e)=>scDrop(e,i)} ondragend={scDragEnd}>
            <div class="sg-thumb">{#if sc.thumbnail}<img src={sc.thumbnail} alt="" />{/if}</div>
            <span class="sg-name" contenteditable="false" ondblclick={(e)=>{e.stopPropagation();e.target.contentEditable='true';e.target.focus();}} onblur={(e)=>{e.target.contentEditable='false';const idx=screens.findIndex(s2=>s2.id===sc.id);if(idx>=0){screens[idx].name=e.target.textContent;screens=[...screens];}}} onkeydown={(e)=>{if(e.key==='Enter'){e.preventDefault();e.target.blur();}}}>{sc.name}</span>
            {#if screens.length > 1}<button class="sg-del" onclick={(e)=>{e.stopPropagation();removeScreen(sc.id);}}><i class="fa-solid fa-xmark"></i></button>{/if}
          </div>
        {/each}
        <button class="sg-add" onclick={addScreen}>+</button>
      </div>
      <div class="sg-ctrl-row">
        <span>Rotation</span><button class="tog sm" class:on={rotation} onclick={()=>rotation=!rotation}></button>
        {#if rotation}<input type="range" min="3" max="60" value={rotationInterval} oninput={(e)=>rotationInterval=+e.target.value}><span class="mono">{rotationInterval}s</span>{/if}
      </div>
    </div>
  </div>

  <!-- ═══ RECHTE SEITE: Tab-Browser ═══ -->
  <div class="right-col">
    {#if editorMode === 'widget'}
      <!-- Tab-Leiste -->
      <div class="tab-bar">
        {#each TABS as tab}
          <button class="tab-btn" class:active={activeTab===tab.id} onclick={()=>{activeTab=tab.id;configSource=null;}}>{tab.label}</button>
        {/each}
      </div>

      <div class="tab-content">
        <!-- Live Key:Value Tabelle -->
        <div class="data-table">
          {#each getSourcesForTab(activeTab) as src}
            {@const val = src.getValue ? src.getValue(s.stats, weather, {}) : '—'}
            <button class="data-row" class:active={configSource?.id===src.id} onclick={()=>selectSource(src)}>
              <span class="dk">{src.label}</span>
              <span class="dv">{val}{src.unit ? ' '+src.unit : ''}</span>
            </button>
          {/each}

          <!-- Wetter-Ortssuche im Wetter-Tab -->
          {#if activeTab === 'wetter'}
            <div class="wetter-loc">
              <div class="data-row static"><span class="dk">Ort</span><span class="dv">{weatherLocation?.name || '—'}</span></div>
              <input type="text" class="loc-input" placeholder="Ort suchen..." value={locationSearch} oninput={onLocationInput}>
              {#if locationResults.length > 0}
                <div class="loc-results">{#each locationResults as loc}<button class="loc-item" onclick={()=>selectLocation(loc)}>{loc.name}{loc.country ? ', '+loc.country : ''}</button>{/each}</div>
              {/if}
            </div>
          {/if}

          <!-- Disk-Index Auswahl im Disk-Tab -->
          {#if activeTab === 'disk' && s.stats?.disks?.length > 1}
            <div class="disk-sel">
              {#each s.stats.disks as d, i}
                <button class="disk-btn" class:active={configSource?.opts?.diskIdx===i} onclick={()=>{/* diskIdx wird im Konfigurator gesetzt */}}>{d.label || d.mount}</button>
              {/each}
            </div>
          {/if}
        </div>

        <!-- Konfigurator (wenn Quelle gewaehlt) -->
        {#if configSource}
          <div class="configurator">
            <div class="conf-title">{configSource.label}</div>

            <!-- Display-Modus waehlen -->
            <div class="conf-section">Darstellung</div>
            <div class="mode-grid">
              {#each getModesForType(configSource.type) as mode}
                <button class="mode-btn" class:active={configDisplay===mode.id} onclick={()=>configDisplay=mode.id}>{mode.label}</button>
              {/each}
            </div>

            <button class="add-widget-btn" onclick={addConfiguredWidget}><i class="fa-solid fa-plus"></i> Zum Canvas</button>
          </div>
        {/if}

        <!-- Selektiertes Widget bearbeiten -->
        {#if selectedWidget >= 0 && placedWidgets[selectedWidget]}
          {@const sw = placedWidgets[selectedWidget]}
          <div class="widget-props">
            <div class="conf-section">Selektiert: {sw.name || sw.source}</div>
            <div class="pr"><span>X</span><input type="range" min="0" max={W-1} value={sw.x} oninput={(e)=>{sw.x=+e.target.value;placedWidgets=[...placedWidgets];renderAll();}}><span class="pv">{sw.x}</span></div>
            <div class="pr"><span>Y</span><input type="range" min="0" max={H-1} value={sw.y} oninput={(e)=>{sw.y=+e.target.value;placedWidgets=[...placedWidgets];renderAll();}}><span class="pv">{sw.y}</span></div>
            {#if sw.opts.scaleX !== undefined}
              <div class="pr"><span>Breite</span><input type="range" min="1" max="8" value={sw.opts.scaleX} oninput={(e)=>updateWidgetOpt(selectedWidget,'scaleX',+e.target.value)}><span class="pv">{sw.opts.scaleX}x</span></div>
              <div class="pr"><span>Hoehe</span><input type="range" min="1" max="8" value={sw.opts.scaleY??sw.opts.scaleX} oninput={(e)=>updateWidgetOpt(selectedWidget,'scaleY',+e.target.value)}><span class="pv">{sw.opts.scaleY??sw.opts.scaleX}x</span></div>
            {/if}
            {#if sw.opts.prefix !== undefined}<div class="pr"><span>Praefix</span><input type="text" class="ti" value={sw.opts.prefix} oninput={(e)=>updateWidgetOpt(selectedWidget,'prefix',e.target.value)}></div>{/if}
            {#if sw.opts.suffix !== undefined}<div class="pr"><span>Suffix</span><input type="text" class="ti" value={sw.opts.suffix} oninput={(e)=>updateWidgetOpt(selectedWidget,'suffix',e.target.value)}></div>{/if}
            {#if sw.opts.text !== undefined}<div class="pr"><span>Text</span><input type="text" class="ti" value={sw.opts.text} oninput={(e)=>updateWidgetOpt(selectedWidget,'text',e.target.value)}></div>{/if}
            {#if sw.opts.width !== undefined}<div class="pr"><span>Breite</span><input type="range" min="4" max="128" value={sw.opts.width} oninput={(e)=>updateWidgetOpt(selectedWidget,'width',+e.target.value)}><span class="pv">{sw.opts.width}</span></div>{/if}
            {#if sw.opts.height !== undefined}<div class="pr"><span>Hoehe</span><input type="range" min="2" max="64" value={sw.opts.height} oninput={(e)=>updateWidgetOpt(selectedWidget,'height',+e.target.value)}><span class="pv">{sw.opts.height}</span></div>{/if}
            {#if sw.opts.radius !== undefined}<div class="pr"><span>Radius</span><input type="range" min="6" max="30" value={sw.opts.radius} oninput={(e)=>updateWidgetOpt(selectedWidget,'radius',+e.target.value)}><span class="pv">{sw.opts.radius}</span></div>{/if}
            {#if sw.opts.diskIdx !== undefined}<div class="pr"><span>Disk</span><input type="range" min="0" max={Math.max(0,(s.stats?.disks?.length||1)-1)} value={sw.opts.diskIdx} oninput={(e)=>updateWidgetOpt(selectedWidget,'diskIdx',+e.target.value)}><span class="pv">{s.stats?.disks?.[sw.opts.diskIdx]?.mount||'?'}</span></div>{/if}
            <div class="pr"><span>Invertiert</span><button class="tog sm" class:on={sw.opts.invert} onclick={()=>updateWidgetOpt(selectedWidget,'invert',!sw.opts.invert)}></button></div>
            <div class="pr"><span>Rahmen</span><button class="tog sm" class:on={sw.opts.border} onclick={()=>updateWidgetOpt(selectedWidget,'border',!sw.opts.border)}></button></div>
            <div class="prop-actions">
              <button class="act-btn" onclick={()=>{const src=placedWidgets[selectedWidget];placedWidgets=[...placedWidgets,{...JSON.parse(JSON.stringify(src)),id:Date.now(),x:src.x+4,y:src.y+4}];selectedWidget=placedWidgets.length-1;selectedWidgets=new Set([selectedWidget]);renderAll();}}><i class="fa-solid fa-copy"></i></button>
              <button class="act-btn del" onclick={()=>removeWidget(selectedWidget)}><i class="fa-solid fa-trash-can"></i></button>
            </div>
          </div>
        {/if}
      </div>

    {:else}
      <!-- ═══ RASTER-EDITOR ═══ -->
      <div class="raster-tools">
        <div class="conf-section">Werkzeuge</div>
        <div class="tool-grid">{#each drawTools as t}<button class="tool-btn" class:active={tool===t.id} onclick={()=>tool=t.id} title="{t.label} ({t.key})"><i class="fa-solid {t.icon}"></i></button>{/each}</div>
        {#if tool==='pencil'||tool==='eraser'}<div class="pr"><span>Groesse</span><input type="range" min="1" max="8" value={penSize} oninput={(e)=>penSize=+e.target.value}><span class="pv">{penSize}</span></div>{/if}
        {#if tool==='rect'||tool==='circle'||tool==='ellipse'}<div class="pr"><span>Gefuellt</span><button class="tog sm" class:on={filled} onclick={()=>filled=!filled}></button></div>{/if}
        {#if tool==='text'}<div class="pr"><span>Text</span><input type="text" class="ti" bind:value={textInput} maxlength="20"></div><div class="pr"><span>Groesse</span><input type="range" min="1" max="3" value={textScale} oninput={(e)=>textScale=+e.target.value}><span class="pv">{textScale}x</span></div>{/if}
        <div class="ag"><button class="ab" onclick={undo}><i class="fa-solid fa-rotate-left"></i></button><button class="ab" onclick={redo}><i class="fa-solid fa-rotate-right"></i></button><button class="ab" onclick={clearLayer}><i class="fa-solid fa-trash-can"></i></button><button class="ab" onclick={invertLayer}><i class="fa-solid fa-circle-half-stroke"></i></button></div>

        <div class="conf-section">Anzeige</div>
        <div class="pr"><span>Zoom</span><input type="range" min="2" max="16" value={zoom} oninput={(e)=>zoom=+e.target.value}><span class="pv">{zoom}x</span></div>
        <div class="pr"><span>Raster</span><button class="tog sm" class:on={showGrid} onclick={()=>showGrid=!showGrid}></button></div>
        <div class="pr"><span>Snap</span><select class="ti" onchange={(e)=>snapGrid=+e.target.value}><option value="0">Aus</option><option value="4">4px</option><option value="8">8px</option><option value="16">16px</option></select></div>

        <div class="conf-section">Ebenen</div>
        <div class="layer-list">{#each [...layers].reverse() as layer}{@const idx=layers.indexOf(layer)}<div class="layer-item" class:active={layer.id===activeLayer} onclick={()=>activeLayer=layer.id}><button class="lv" onclick={(e)=>{e.stopPropagation();toggleVis(layer.id);render();}}><i class="fa-solid {layer.visible?'fa-eye':'fa-eye-slash'}"></i></button><span>{layer.name}</span></div>{/each}</div>
        <div class="ag"><button class="ab" onclick={()=>addLayer()}>+</button><button class="ab" onclick={()=>dupLayer(activeLayer)}><i class="fa-solid fa-copy"></i></button><button class="ab" onclick={()=>rmLayer(activeLayer)}><i class="fa-solid fa-trash"></i></button></div>

        <div class="rr"><span>Cursor</span><span class="mono">{cursorX>=0?`${cursorX}, ${cursorY}`:'—'}</span></div>
      </div>
    {/if}
  </div>
</div>

<style>
  .studio { display: flex; height: 100%; overflow: hidden; }

  /* ═══ LINKE SPALTE (golden ratio ~38%) ═══ */
  .left-col { width: 38.2%; flex-shrink: 0; display: flex; flex-direction: column; border-right: 1px solid var(--border); background: #1a1a22; overflow: hidden; }
  .left-header { display: flex; align-items: center; justify-content: space-between; padding: 8px 12px; border-bottom: 1px solid var(--border); background: var(--bg-base); flex-shrink: 0; }
  .studio-title { font: 700 var(--fs-lg) var(--font); color: var(--text-primary); }
  .mode-switch { display: flex; gap: 2px; background: var(--bg-surface); border-radius: var(--radius-sm); padding: 2px; }
  .mode-switch button { padding: 4px 12px; border: none; background: none; color: var(--text-muted); font: 500 var(--fs-xs) var(--font); cursor: pointer; border-radius: var(--radius-sm); }
  .mode-switch button.active { background: var(--accent); color: #fff; }

  .profile-bar { display: flex; align-items: center; gap: 4px; padding: 4px 8px; border-bottom: 1px solid var(--border); background: var(--bg-base); flex-shrink: 0; min-height: 28px; }
  .pb-chips { display: flex; gap: 3px; overflow-x: auto; flex: 1; }
  .pb-chip { display: flex; align-items: center; gap: 3px; padding: 2px 8px; border-radius: 10px; border: 1px solid var(--border); background: var(--bg-elevated); color: var(--text-muted); font: 500 9px var(--font); cursor: pointer; white-space: nowrap; flex-shrink: 0; }
  .pb-chip:hover { border-color: var(--accent); color: var(--accent); }
  .pb-chip.active { background: var(--accent-dim); border-color: var(--accent); color: var(--accent); }
  .pb-del { font-size: 10px; cursor: pointer; margin-left: 2px; }
  .pb-del:hover { color: var(--red); }
  .pb-input { width: 90px; padding: 2px 6px; border: 1px solid var(--accent); background: var(--bg-elevated); color: var(--text-primary); border-radius: 10px; font: 500 9px var(--mono); }
  .pb-btn { width: 24px; height: 24px; border-radius: 50%; border: 1px solid var(--border); background: none; color: var(--text-muted); cursor: pointer; font-size: 10px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
  .pb-btn:hover { border-color: var(--accent); color: var(--accent); }

  .canvas-wrap { flex: 1; overflow: hidden; position: relative; }
  .canvas-scroll { width: 100%; height: 100%; overflow: auto; display: flex; align-items: flex-start; justify-content: flex-start; padding: 12px; }
  .canvas-scroll canvas { image-rendering: pixelated; touch-action: none; cursor: crosshair; box-shadow: 0 0 0 1px var(--border); flex-shrink: 0; }

  .left-bottom { display: flex; align-items: center; gap: 8px; padding: 6px 10px; border-top: 1px solid var(--border); background: var(--bg-base); flex-shrink: 0; }
  .pv-bezel { background: #000; padding: 2px; border-radius: 3px; border: 1px solid #444; flex-shrink: 0; }
  .pv-canvas { display: block; width: 128px; height: 64px; image-rendering: pixelated; }
  .left-actions { display: flex; gap: 3px; flex-wrap: wrap; }
  .act-btn { padding: 5px 10px; border-radius: var(--radius-sm); border: 1px solid var(--border); background: var(--bg-elevated); color: var(--text-muted); font: 500 var(--fs-xs) var(--font); cursor: pointer; display: flex; align-items: center; gap: 4px; }
  .act-btn:hover { border-color: var(--accent); color: var(--accent); }
  .act-btn.primary { border-color: var(--accent); color: var(--accent); background: var(--accent-dim); }
  .act-btn.primary:hover { background: var(--accent); color: #fff; }
  .act-btn.del { border-color: var(--red); color: var(--red); }

  .screen-gallery { flex-shrink: 0; border-top: 1px solid var(--border); background: var(--bg-base); padding: 6px 8px; }
  .sg-strip { display: flex; gap: 6px; overflow-x: auto; margin-bottom: 4px; }
  .sg-item { flex-shrink: 0; cursor: pointer; border: 2px solid var(--border); border-radius: var(--radius-sm); padding: 2px; position: relative; }
  .sg-item.active { border-color: var(--accent); }
  .sg-thumb { width: 96px; height: 48px; background: #000; border-radius: 2px; overflow: hidden; }
  .sg-thumb img { width: 96px; height: 48px; image-rendering: pixelated; display: block; }
  .sg-name { display: block; font: 500 8px var(--font); color: var(--text-muted); text-align: center; max-width: 96px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .sg-del { position: absolute; top: -4px; right: -4px; width: 14px; height: 14px; border-radius: 50%; border: none; background: var(--bg-elevated); color: var(--red); cursor: pointer; font-size: 8px; display: none; align-items: center; justify-content: center; }
  .sg-item:hover .sg-del { display: flex; }
  .sg-add { width: 48px; height: 48px; flex-shrink: 0; border-radius: var(--radius-sm); border: 2px dashed var(--border); background: none; color: var(--text-muted); cursor: pointer; font-size: var(--fs-base); }
  .sg-add:hover { border-color: var(--accent); color: var(--accent); }
  .sg-ctrl-row { display: flex; align-items: center; gap: 8px; font: 500 var(--fs-xs) var(--font); color: var(--text-muted); }
  .sg-ctrl-row input { width: 70px; }

  /* ═══ RECHTE SPALTE (~61.8%) ═══ */
  .right-col { flex: 1; display: flex; flex-direction: column; overflow: hidden; background: var(--bg-base); }

  .tab-bar { display: flex; gap: 1px; border-bottom: 2px solid var(--border); flex-shrink: 0; overflow-x: auto; background: var(--bg-surface); }
  .tab-btn { padding: 8px 14px; border: none; background: none; color: var(--text-muted); font: 600 var(--fs-xs) var(--font); cursor: pointer; border-bottom: 2px solid transparent; margin-bottom: -2px; white-space: nowrap; text-transform: uppercase; letter-spacing: 0.04em; }
  .tab-btn:hover { color: var(--text-primary); }
  .tab-btn.active { color: var(--accent); border-bottom-color: var(--accent); }

  .tab-content { flex: 1; overflow-y: auto; padding: 8px; display: flex; flex-direction: column; gap: 8px; }

  .data-table { display: flex; flex-direction: column; gap: 2px; }
  .data-row { display: flex; justify-content: space-between; align-items: center; padding: 7px 10px; border-radius: var(--radius-sm); border: 1px solid transparent; background: var(--bg-surface); cursor: pointer; text-align: left; width: 100%; }
  .data-row:hover { border-color: var(--accent); background: rgba(0,180,255,0.04); }
  .data-row.active { border-color: var(--accent); background: var(--accent-dim); }
  .data-row.static { cursor: default; }
  .dk { font: 500 var(--fs-sm) var(--font); color: var(--text-secondary); }
  .dv { font: 600 var(--fs-sm) var(--mono); color: var(--text-primary); }

  .wetter-loc { margin-top: 4px; }
  .loc-input { width: 100%; padding: 6px 10px; border: 1px solid var(--border); background: var(--bg-elevated); color: var(--text-primary); border-radius: var(--radius-sm); font: 500 var(--fs-sm) var(--font); margin-top: 4px; box-sizing: border-box; }
  .loc-results { display: flex; flex-direction: column; gap: 2px; margin-top: 4px; }
  .loc-item { padding: 6px 10px; border-radius: var(--radius-sm); border: 1px solid var(--border); background: var(--bg-surface); cursor: pointer; text-align: left; font: 500 var(--fs-sm) var(--font); color: var(--text-secondary); width: 100%; }
  .loc-item:hover { border-color: var(--accent); color: var(--accent); }

  .configurator { padding: 8px; border: 1px solid var(--border); border-radius: var(--radius); background: var(--bg-surface); }
  .conf-title { font: 600 var(--fs-base) var(--font); color: var(--text-primary); margin-bottom: 6px; }
  .conf-section { font: 600 var(--fs-xs) var(--font); text-transform: uppercase; letter-spacing: 0.06em; color: var(--text-muted); margin: 8px 0 4px; }
  .mode-grid { display: flex; flex-wrap: wrap; gap: 3px; margin-bottom: 8px; }
  .mode-btn { padding: 5px 10px; border-radius: var(--radius-sm); border: 1px solid var(--border); background: var(--bg-elevated); color: var(--text-muted); font: 500 var(--fs-xs) var(--font); cursor: pointer; }
  .mode-btn:hover { border-color: var(--accent); color: var(--accent); }
  .mode-btn.active { background: var(--accent-dim); border-color: var(--accent); color: var(--accent); }
  .add-widget-btn { width: 100%; padding: 8px; border-radius: var(--radius-sm); border: 1px solid var(--accent); background: var(--accent-dim); color: var(--accent); font: 600 var(--fs-sm) var(--font); cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 6px; }
  .add-widget-btn:hover { background: var(--accent); color: #fff; }

  .widget-props { padding: 8px; border: 1px solid var(--border); border-radius: var(--radius); background: var(--bg-surface); }
  .prop-actions { display: flex; gap: 4px; margin-top: 6px; }

  /* Raster-Editor rechte Seite */
  .raster-tools { padding: 10px; overflow-y: auto; }
  .tool-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 3px; margin-bottom: 6px; }
  .tool-btn { height: 32px; border-radius: var(--radius-sm); border: 1px solid var(--border); background: var(--bg-surface); color: var(--text-muted); cursor: pointer; font-size: var(--fs-xs); display: flex; align-items: center; justify-content: center; }
  .tool-btn:hover { color: var(--text-primary); }
  .tool-btn.active { color: var(--accent); background: rgba(0,180,255,0.1); border-color: var(--accent); }
  .ag { display: grid; grid-template-columns: repeat(4, 1fr); gap: 3px; margin: 6px 0; }
  .ab { height: 28px; border-radius: var(--radius-sm); border: 1px solid var(--border); background: var(--bg-elevated); color: var(--text-muted); cursor: pointer; font-size: var(--fs-xs); display: flex; align-items: center; justify-content: center; }
  .ab:hover { border-color: var(--accent); color: var(--accent); }
  .layer-list { display: flex; flex-direction: column; gap: 2px; }
  .layer-item { display: flex; align-items: center; gap: 6px; padding: 4px 6px; border-radius: var(--radius-sm); cursor: pointer; font: 500 var(--fs-sm) var(--font); color: var(--text-muted); background: var(--bg-surface); border: 1px solid transparent; }
  .layer-item.active { border-color: var(--accent); color: var(--accent); }
  .lv { background: none; border: none; color: inherit; cursor: pointer; font-size: var(--fs-sm); padding: 2px; }

  /* Shared */
  .pr { display: flex; align-items: center; gap: 6px; font: 500 var(--fs-sm) var(--font); color: var(--text-secondary); margin: 2px 0; }
  .pr span:first-child { width: 50px; flex-shrink: 0; font-size: var(--fs-xs); }
  .pr input[type=range] { flex: 1; }
  .pv { font: 600 var(--fs-xs) var(--mono); color: var(--text-primary); min-width: 28px; text-align: right; }
  .rr { display: flex; justify-content: space-between; font: 500 var(--fs-xs) var(--font); color: var(--text-muted); padding: 2px 0; }
  .mono { font-family: var(--mono); color: var(--text-secondary); }
  .ti { flex: 1; min-width: 0; padding: 4px 8px; border: 1px solid var(--border); background: var(--bg-elevated); color: var(--text-primary); border-radius: var(--radius-sm); font: 500 var(--fs-sm) var(--mono); box-sizing: border-box; }
  .tog { width: 34px; height: 18px; border-radius: 9px; border: none; background: rgba(255,255,255,0.1); cursor: pointer; position: relative; transition: background 150ms; }
  .tog.sm { width: 28px; height: 14px; border-radius: 7px; }
  .tog.on { background: var(--green); }
  .tog::after { content:''; position:absolute; top:2px; left:2px; width:14px; height:14px; border-radius:50%; background:#fff; transition:transform 150ms; }
  .tog.sm::after { width:10px; height:10px; }
  .tog.on::after { transform: translateX(16px); }
  .tog.sm.on::after { transform: translateX(14px); }

  .ctx-menu { position: fixed; z-index: 100; background: var(--bg-elevated); border: 1px solid var(--border); border-radius: var(--radius); box-shadow: 0 8px 24px rgba(0,0,0,0.4); padding: 4px; min-width: 150px; }
  .ctx-item { display: flex; align-items: center; gap: 8px; width: 100%; padding: 6px 10px; border: none; background: none; border-radius: var(--radius-sm); color: var(--text-secondary); font: 500 var(--fs-sm) var(--font); cursor: pointer; text-align: left; }
  .ctx-item:hover { background: rgba(0,180,255,0.1); color: var(--accent); }
  .ctx-del:hover { background: rgba(255,60,60,0.1); color: var(--red); }
  .ctx-sep { height: 1px; background: var(--border); margin: 3px 8px; }

  @media (max-width: 900px) {
    .studio { flex-direction: column; }
    .left-col { width: 100%; height: 50%; }
    .right-col { height: 50%; }
  }
</style>
