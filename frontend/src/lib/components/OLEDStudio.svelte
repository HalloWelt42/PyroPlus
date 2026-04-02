<script>
  import { onMount, onDestroy } from 'svelte';
  import PanelWrapper from './oled/PanelWrapper.svelte';
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

  /* ═══ WETTER (Open-Meteo API + Ortssuche) ═══ */
  let weather = $state(null);
  let weatherLocation = $state(JSON.parse(localStorage.getItem('pp-weather-loc') || 'null') || { name: 'Zeitz', lat: 51.05, lon: 12.13 });
  let locationSearch = $state('');
  let locationResults = $state([]);
  let showLocationSearch = $state(!weatherLocation.name);

  async function fetchWeather() {
    if (!weatherLocation) return;
    try {
      const r = await fetch(`https://api.open-meteo.com/v1/forecast?latitude=${weatherLocation.lat}&longitude=${weatherLocation.lon}&current=temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code,surface_pressure&timezone=auto`);
      const d = await r.json();
      weather = d.current;
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
    locationSearch = '';
    locationResults = [];
    showLocationSearch = false;
    fetchWeather();
    s.toast(`Wetter-Ort: ${loc.name}`, 'ok');
  }

  let _searchTimer = 0;
  function onLocationInput(e) {
    locationSearch = e.target.value;
    clearTimeout(_searchTimer);
    _searchTimer = setTimeout(() => searchLocation(locationSearch), 300);
  }

  function weatherCodeToText(code) {
    if (code == null) return '—';
    if (code === 0) return 'Klar';
    if (code <= 3) return 'Bewölkt';
    if (code <= 49) return 'Nebel';
    if (code <= 59) return 'Nieselregen';
    if (code <= 69) return 'Regen';
    if (code <= 79) return 'Schnee';
    if (code <= 84) return 'Schauer';
    if (code <= 94) return 'Schneesch.';
    return 'Gewitter';
  }

  /* ═══ WIDGETS MIT LIVE-DATEN ═══ */
  const widgetTypes = {
    clock:     { cat:'zeit', label:'Uhr HH:MM',    w:58, h:14, props:{ scale:2, format:'HH:MM' },
                 getText: (p) => { const d=new Date(); return String(d.getHours()).padStart(2,'0')+':'+String(d.getMinutes()).padStart(2,'0'); }},
    clock_s:   { cat:'zeit', label:'Uhr HH:MM:SS', w:48, h:7, props:{ scale:1 },
                 getText: () => { const d=new Date(); return String(d.getHours()).padStart(2,'0')+':'+String(d.getMinutes()).padStart(2,'0')+':'+String(d.getSeconds()).padStart(2,'0'); }},
    clock_l:   { cat:'zeit', label:'Uhr Groß',     w:90, h:21, props:{ scale:3 },
                 getText: () => { const d=new Date(); return String(d.getHours()).padStart(2,'0')+':'+String(d.getMinutes()).padStart(2,'0'); }},
    date:      { cat:'zeit', label:'Datum',         w:60, h:7, props:{ scale:1 },
                 getText: () => new Date().toLocaleDateString('de-DE') },
    weekday:   { cat:'zeit', label:'Wochentag',     w:14, h:7, props:{ scale:1 },
                 getText: () => ['So','Mo','Di','Mi','Do','Fr','Sa'][new Date().getDay()] },
    /* ─── CPU ─── */
    cpu_temp:  { cat:'cpu',  label:'Temperatur °C',  w:24, h:7, props:{ scale:1, prefix:'' },
                 getText: (p) => (p.prefix||'')+Math.round(s.stats?.cpu?.temp||0)+'°' },
    cpu_pct:   { cat:'cpu',  label:'Auslastung %',   w:24, h:7, props:{ scale:1, prefix:'' },
                 getText: (p) => (p.prefix||'')+Math.round(s.stats?.cpu?.percent||0)+'%' },
    cpu_cores: { cat:'cpu',  label:'Kerne',          w:12, h:7, props:{ scale:1, prefix:'' },
                 getText: (p) => (p.prefix||'')+(s.stats?.cpu?.cores||4) },
    cpu_bar:   { cat:'cpu',  label:'Balken',         w:60, h:6, props:{ width:60, height:6 }, isShape: true,
                 draw: (px,x,y,p) => E.drawBar(px, x, y, p.width||60, p.height||6, s.stats?.cpu?.percent||0) },
    /* ─── RAM ─── */
    ram_used:  { cat:'ram',  label:'Benutzt',        w:24, h:7, props:{ scale:1, prefix:'' },
                 getText: (p) => (p.prefix||'')+(s.stats?.ram?.used_gb||0)+'G' },
    ram_total: { cat:'ram',  label:'Gesamt',         w:24, h:7, props:{ scale:1, prefix:'' },
                 getText: (p) => (p.prefix||'')+(s.stats?.ram?.total_gb||0)+'G' },
    ram_pct:   { cat:'ram',  label:'Prozent',        w:24, h:7, props:{ scale:1, prefix:'' },
                 getText: (p) => (p.prefix||'')+(s.stats?.ram?.percent||0)+'%' },
    ram_bar:   { cat:'ram',  label:'Balken',         w:60, h:6, props:{ width:60, height:6 }, isShape: true,
                 draw: (px,x,y,p) => E.drawBar(px, x, y, p.width||60, p.height||6, s.stats?.ram?.percent||0) },
    /* ─── Disk ─── */
    disk_name: { cat:'disk', label:'Name',           w:48, h:7, props:{ scale:1, prefix:'', diskIdx:0 },
                 getText: (p) => (p.prefix||'')+(s.stats?.disks?.[p.diskIdx||0]?.label||s.stats?.disks?.[p.diskIdx||0]?.mount||'?') },
    disk_used: { cat:'disk', label:'Benutzt',        w:36, h:7, props:{ scale:1, prefix:'', diskIdx:0 },
                 getText: (p) => { const d=s.stats?.disks?.[p.diskIdx||0]; return (p.prefix||'')+(d?Math.round(d.used_gb)+'G':'?'); }},
    disk_total:{ cat:'disk', label:'Gesamt',         w:36, h:7, props:{ scale:1, prefix:'', diskIdx:0 },
                 getText: (p) => { const d=s.stats?.disks?.[p.diskIdx||0]; return (p.prefix||'')+(d?Math.round(d.total_gb)+'G':'?'); }},
    disk_pct:  { cat:'disk', label:'Prozent',        w:24, h:7, props:{ scale:1, prefix:'', diskIdx:0 },
                 getText: (p) => (p.prefix||'')+(s.stats?.disks?.[p.diskIdx||0]?.percent||0)+'%' },
    disk_bar:  { cat:'disk', label:'Balken',         w:60, h:6, props:{ width:60, height:6, diskIdx:0 }, isShape: true,
                 draw: (px,x,y,p) => E.drawBar(px, x, y, p.width||60, p.height||6, s.stats?.disks?.[p.diskIdx||0]?.percent||0) },
    /* ─── Netzwerk ─── */
    net_ip:    { cat:'net',  label:'IP-Adresse',     w:60, h:7, props:{ scale:1, prefix:'' },
                 getText: (p) => (p.prefix||'')+(s.stats?.network?.ip||'0.0.0.0') },
    net_if:    { cat:'net',  label:'Interface',      w:36, h:7, props:{ scale:1, prefix:'' },
                 getText: (p) => (p.prefix||'')+(s.stats?.network?.interface||'?') },
    net_rx:    { cat:'net',  label:'Download',       w:48, h:7, props:{ scale:1, prefix:'' },
                 getText: (p) => { const b=s.stats?.network?.rx_bytes_sec||0; return (p.prefix||'')+(b>1048576?(b/1048576).toFixed(1)+'M':b>1024?Math.round(b/1024)+'K':b+'B')+'/s'; }},
    net_tx:    { cat:'net',  label:'Upload',         w:48, h:7, props:{ scale:1, prefix:'' },
                 getText: (p) => { const b=s.stats?.network?.tx_bytes_sec||0; return (p.prefix||'')+(b>1048576?(b/1048576).toFixed(1)+'M':b>1024?Math.round(b/1024)+'K':b+'B')+'/s'; }},
    /* ─── System ─── */
    uptime:    { cat:'sys',  label:'Uptime',         w:48, h:7, props:{ scale:1, prefix:'' },
                 getText: (p) => (p.prefix||'')+(s.stats?.uptime?.formatted||'0:00') },
    label:     { cat:'deko', label:'Textfeld',       w:48, h:7, props:{ scale:1, text:'Text' },
                 getText: (p) => p.text || 'Text' },
    line_h:    { cat:'deko', label:'Linie ─',        w:60, h:1, props:{ width:60 }, isShape: true,
                 draw: (px,x,y,p) => { for(let i=0;i<(p.width||60);i++) if(x+i>=0&&x+i<W) px[y*W+x+i]=1; }},
    line_v:    { cat:'deko', label:'Linie │',        w:1, h:20, props:{ height:20 }, isShape: true,
                 draw: (px,x,y,p) => { for(let i=0;i<(p.height||20);i++) if(y+i>=0&&y+i<H) px[(y+i)*W+x]=1; }},
    rect_o:    { cat:'deko', label:'Rahmen □',       w:40, h:20, props:{ width:40, height:20 }, isShape: true,
                 draw: (px,x,y,p) => E.drawRect(x,y,x+(p.width||40)-1,y+(p.height||20)-1,(px2,py)=>{if(px2>=0&&px2<W&&py>=0&&py<H)px[py*W+px2]=1;},false) },
    rect_f:    { cat:'deko', label:'Block ■',        w:40, h:20, props:{ width:40, height:20 }, isShape: true,
                 draw: (px,x,y,p) => E.drawRect(x,y,x+(p.width||40)-1,y+(p.height||20)-1,(px2,py)=>{if(px2>=0&&px2<W&&py>=0&&py<H)px[py*W+px2]=1;},true) },
  };
  const widgetList = Object.entries(widgetTypes).map(([id,v])=>({id,...v}));

  /* Platzierte Widgets — jedes hat Position, Typ, eigene Eigenschaften */
  let placedWidgets = $state([]);
  let selectedWidget = $state(-1);

  function placeWidget(w) {
    const wt = widgetTypes[w.id];
    placedWidgets = [...placedWidgets, {
      id: Date.now(),
      type: w.id,
      x: 4, y: 4,
      props: { ...wt.props },
    }];
    selectedWidget = placedWidgets.length - 1;
    tool = 'move';
    renderWidgets();
    s.toast(`${wt.label} eingefügt`, 'ok');
  }

  function removeWidget(idx) {
    placedWidgets = placedWidgets.filter((_, i) => i !== idx);
    if (selectedWidget >= placedWidgets.length) selectedWidget = placedWidgets.length - 1;
    renderWidgets();
  }

  function moveWidget(idx, dx, dy) {
    const w = placedWidgets[idx];
    w.x = Math.max(0, Math.min(W - 1, w.x + dx));
    w.y = Math.max(0, Math.min(H - 1, w.y + dy));
    placedWidgets = [...placedWidgets];
    renderWidgets();
  }

  function updateWidgetProp(idx, key, val) {
    placedWidgets[idx].props[key] = val;
    placedWidgets = [...placedWidgets];
    renderWidgets();
  }

  /* Alle Widgets in Layer 0 rendern */
  function renderWidgets() {
    const px = layers[0].pixels;
    px.fill(0);
    for (const w of placedWidgets) {
      const wt = widgetTypes[w.type];
      if (!wt) continue;
      if (wt.isShape) {
        wt.draw(px, w.x, w.y, w.props);
      } else {
        const text = wt.getText(w.props);
        E.drawText(px, text, w.x, w.y, w.props.scale || 1);
      }
    }
    layers = [...layers];
    render();
    autoSave();
  }

  /* Widget-Rendering alle Sekunde aktualisieren (für Uhr etc.) */
  let _widgetTimer;
  function startWidgetTimer() { _widgetTimer = setInterval(() => { if (placedWidgets.length > 0) renderWidgets(); }, 1000); }
  function stopWidgetTimer() { clearInterval(_widgetTimer); }

  /* ═══ CANVAS ═══ */
  let canvasEl = $state(null), previewEl = $state(null);
  function render() {
    const comp = E.composite(layers);
    if (canvasEl) {
      E.renderCanvas(canvasEl.getContext('2d'), comp, zoom, showGrid);
      // Widget-Rahmen zeichnen
      if (selectedWidget >= 0 && placedWidgets[selectedWidget]) {
        const ctx = canvasEl.getContext('2d');
        const w = placedWidgets[selectedWidget];
        const wt = widgetTypes[w.type];
        if (wt) {
          const ww = wt.isShape ? (w.props.width || wt.w) : wt.w * (w.props.scale || 1);
          const wh = wt.isShape ? (w.props.height || wt.h) : wt.h * (w.props.scale || 1);
          ctx.strokeStyle = 'rgba(0,180,255,0.7)';
          ctx.lineWidth = 1;
          ctx.setLineDash([4, 2]);
          ctx.strokeRect(w.x * zoom - 1, w.y * zoom - 1, ww * zoom + 2, wh * zoom + 2);
          ctx.setLineDash([]);
        }
      }
    }
    if (previewEl) E.renderPreview(previewEl.getContext('2d'), comp);
  }

  /* ═══ MAUS ═══ */
  let drawing=$state(false), sx=0, sy=0, lx=-1, ly=-1, snap=null, mvStart=null;
  function m2p(e) { const r=canvasEl.getBoundingClientRect(); return [Math.max(0,Math.min(W-1,Math.floor((e.clientX-r.left)/zoom))),Math.max(0,Math.min(H-1,Math.floor((e.clientY-r.top)/zoom)))]; }

  function hitTestWidget(x, y) {
    for (let i = placedWidgets.length - 1; i >= 0; i--) {
      const w = placedWidgets[i];
      const wt = widgetTypes[w.type];
      if (!wt) continue;
      const ww = wt.isShape ? (w.props.width || wt.w) : wt.w * (w.props.scale || 1);
      const wh = wt.isShape ? (w.props.height || wt.h) : wt.h * (w.props.scale || 1);
      if (x >= w.x && x < w.x + ww && y >= w.y && y < w.y + wh) return i;
    }
    return -1;
  }

  let widgetDrag = null;
  function onDown(e) {
    if (!canvasEl) return;
    const [x,y]=m2p(e);

    // Widget-Klick prüfen (im Move-Modus oder bei Rechtsklick)
    if (tool === 'move') {
      const hit = hitTestWidget(x, y);
      if (hit >= 0) {
        selectedWidget = hit;
        widgetDrag = { idx: hit, startX: x, startY: y, origX: placedWidgets[hit].x, origY: placedWidgets[hit].y };
        drawing = true;
        render();
        return;
      }
    }

    // Klick ohne Tool-Aktion = Widget abwählen
    selectedWidget = hitTestWidget(x, y);
    render();

    drawing=true; sx=x; sy=y; lx=x; ly=y;
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
    // Widget-Drag
    if (widgetDrag) {
      const dx = x - widgetDrag.startX, dy = y - widgetDrag.startY;
      placedWidgets[widgetDrag.idx].x = Math.max(0, Math.min(W-1, widgetDrag.origX + dx));
      placedWidgets[widgetDrag.idx].y = Math.max(0, Math.min(H-1, widgetDrag.origY + dy));
      placedWidgets = [...placedWidgets];
      renderWidgets();
      return;
    }
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
  function onUp(){if(!drawing)return;if(widgetDrag){widgetDrag=null;drawing=false;return;}if(snap)pushH();if(tool==='move'&&mvStart){pushH();mvStart=null;}drawing=false;snap=null;}
  function clearLayer(){pushH();ap()?.fill(0);render();}
  function invertLayer(){pushH();const px=ap();if(px)for(let i=0;i<px.length;i++)px[i]=px[i]?0:1;render();}
  async function sendToOled() {
    // Widgets als Screen-Konfiguration ans Backend senden
    const screenData = {
      type: 'system',
      name: 'Editor',
      widgets: placedWidgets.map(w => ({
        type: w.type,
        x: w.x,
        y: w.y,
        font: w.props.scale === 3 ? 'xl' : w.props.scale === 2 ? 'lg' : 'sm',
        ...(w.props.text !== undefined ? { text: w.props.text } : {}),
        ...(w.props.prefix !== undefined ? { prefix: w.props.prefix } : {}),
        ...(w.props.width !== undefined ? { w: w.props.width } : {}),
        ...(w.props.height !== undefined ? { h: w.props.height } : {}),
      })),
    };
    // Auch das gerenderte Bild als Pixel-Art senden (Fallback)
    const comp = E.composite(layers);
    const c = document.createElement('canvas');
    c.width = W; c.height = H;
    const ctx = c.getContext('2d');
    ctx.fillStyle = '#000'; ctx.fillRect(0, 0, W, H);
    ctx.fillStyle = '#fff';
    for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) if (comp[y * W + x]) ctx.fillRect(x, y, 1, 1);
    const base64 = c.toDataURL().split(',')[1];

    // An Backend senden
    try {
      await s.updateOledScreen(0, screenData);
      s.toast('An OLED gesendet', 'ok');
    } catch (e) {
      s.toast('Fehler: ' + e.message, 'err');
    }
  }

  /* ═══ PANEL D&D ═══ */
  let lpanels=$state(['preview','props','layers','widgets']), rpanels=$state(['tools','display','color','weather']);
  let pdragId=$state(null), pdropSide=$state(null);
  function pDragStart(e,id){pdragId=id;e.dataTransfer.setData('application/x-oled-panel',id);e.dataTransfer.effectAllowed='move';}
  function pDragEnd(){pdragId=null;pdropSide=null;}
  function sDragOver(e,side){if(!e.dataTransfer.types.includes('application/x-oled-panel'))return;e.preventDefault();pdropSide=side;}
  function sDragLeave(e){if(!e.currentTarget.contains(e.relatedTarget))pdropSide=null;}
  function sDrop(e,side){e.preventDefault();const id=e.dataTransfer.getData('application/x-oled-panel');if(!id)return;lpanels=lpanels.filter(p=>p!==id);rpanels=rpanels.filter(p=>p!==id);if(side==='left')lpanels=[...lpanels,id];else rpanels=[...rpanels,id];pdragId=null;pdropSide=null;}

  function onKey(e){if(e.target.tagName==='INPUT'||e.target.tagName==='TEXTAREA')return;if(e.ctrlKey&&e.key==='z'){undo();e.preventDefault();}if(e.ctrlKey&&e.key==='y'){redo();e.preventDefault();}if((e.key==='Delete'||e.key==='Backspace')&&selectedWidget>=0){removeWidget(selectedWidget);e.preventDefault();return;}if(e.key==='g'){showGrid=!showGrid;render();}if(e.key==='+')zoom=Math.min(16,zoom+1);if(e.key==='-')zoom=Math.max(2,zoom-1);const t=drawTools.find(t=>t.key===e.key.toUpperCase());if(t&&!e.ctrlKey)tool=t.id;}

  /* Panel-Metadaten */
  const _pd = { tools:{icon:'pen',label:'Werkzeuge',c:false}, display:{icon:'eye',label:'Anzeige',c:true}, color:{icon:'palette',label:'Farbe',c:false}, preview:{icon:'display',label:'Vorschau',c:false}, props:{icon:'sliders',label:'Eigenschaften',c:true}, layers:{icon:'layer-group',label:'Ebenen',c:false}, widgets:{icon:'puzzle-piece',label:'Widgets',c:true}, weather:{icon:'cloud-sun',label:'Wetter-Ort',c:true} };
  function panelIcon(id) { return _pd[id]?.icon || 'circle'; }
  function panelLabel(id) { return _pd[id]?.label || id; }
  function panelCollapsible(id) { return _pd[id]?.c ?? true; }

  /* ═══ PERSISTENZ (localStorage Auto-Save) ═══ */
  function saveState() {
    try {
      const data = {
        placedWidgets: placedWidgets.map(w => ({ type: w.type, x: w.x, y: w.y, props: w.props })),
        layers: layers.map(l => ({ id: l.id, name: l.name, visible: l.visible, pixels: Array.from(l.pixels) })),
        zoom, showGrid,
      };
      localStorage.setItem('pp-oled-state', JSON.stringify(data));
    } catch {}
  }

  function loadState() {
    try {
      const raw = localStorage.getItem('pp-oled-state');
      if (!raw) return;
      const data = JSON.parse(raw);
      if (data.placedWidgets) {
        placedWidgets = data.placedWidgets.map(w => ({ id: Date.now() + Math.random(), ...w }));
      }
      if (data.layers?.length > 0) {
        layers = data.layers.map(l => ({ ...l, pixels: new Uint8Array(l.pixels) }));
        activeLayer = layers[0].id;
        _nid = Math.max(...layers.map(l => l.id)) + 1;
      }
      if (data.zoom) zoom = data.zoom;
      if (data.showGrid !== undefined) showGrid = data.showGrid;
    } catch {}
  }

  let _saveTimer = 0;
  function autoSave() { clearTimeout(_saveTimer); _saveTimer = setTimeout(saveState, 1000); }

  onMount(()=>{loadState();pushH();renderWidgets();startWidgetTimer();fetchWeather();setInterval(fetchWeather,300000);});
  onDestroy(()=>{stopWidgetTimer();saveState();});
  $effect(()=>{zoom;showGrid;render();autoSave();});
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
    {#if selectedWidget >= 0 && placedWidgets[selectedWidget]}
      {@const sw = placedWidgets[selectedWidget]}
      {@const wt = widgetTypes[sw.type]}
      <div class="rr"><span>Widget</span><span class="mono">{wt?.label}</span></div>
      <div class="rr"><span>Position</span><span class="mono">{sw.x}, {sw.y}</span></div>
      <div class="pr"><span>X</span><input type="range" min="0" max={W-1} value={sw.x} oninput={(e)=>{sw.x=+e.target.value;placedWidgets=[...placedWidgets];renderWidgets();}}><span class="pv">{sw.x}</span></div>
      <div class="pr"><span>Y</span><input type="range" min="0" max={H-1} value={sw.y} oninput={(e)=>{sw.y=+e.target.value;placedWidgets=[...placedWidgets];renderWidgets();}}><span class="pv">{sw.y}</span></div>
      {#if sw.props.scale !== undefined}
        <div class="pr"><span>Größe</span><input type="range" min="1" max="5" value={sw.props.scale} oninput={(e)=>updateWidgetProp(selectedWidget,'scale',+e.target.value)}><span class="pv">{sw.props.scale}×</span></div>
      {/if}
      {#if sw.props.text !== undefined}
        <div class="pr"><span>Text</span><input type="text" class="ti" value={sw.props.text} oninput={(e)=>updateWidgetProp(selectedWidget,'text',e.target.value)}></div>
      {/if}
      {#if sw.props.prefix !== undefined}
        <div class="pr"><span>Präfix</span><input type="text" class="ti" value={sw.props.prefix} oninput={(e)=>updateWidgetProp(selectedWidget,'prefix',e.target.value)}></div>
      {/if}
      {#if sw.props.diskIdx !== undefined}
        <div class="pr"><span>Disk</span><input type="range" min="0" max={Math.max(0,(s.stats?.disks?.length||1)-1)} value={sw.props.diskIdx} oninput={(e)=>updateWidgetProp(selectedWidget,'diskIdx',+e.target.value)}><span class="pv">{s.stats?.disks?.[sw.props.diskIdx]?.mount||'?'}</span></div>
      {/if}
      {#if sw.props.width !== undefined}
        <div class="pr"><span>Breite</span><input type="range" min="4" max="128" value={sw.props.width} oninput={(e)=>updateWidgetProp(selectedWidget,'width',+e.target.value)}><span class="pv">{sw.props.width}</span></div>
      {/if}
      {#if sw.props.height !== undefined}
        <div class="pr"><span>Höhe</span><input type="range" min="2" max="64" value={sw.props.height} oninput={(e)=>updateWidgetProp(selectedWidget,'height',+e.target.value)}><span class="pv">{sw.props.height}</span></div>
      {/if}
      <button class="ab" style="width:100%;aspect-ratio:auto;height:28px;margin-top:6px" onclick={()=>removeWidget(selectedWidget)}><i class="fa-solid fa-trash-can"></i> Widget entfernen</button>
    {:else}
      <div class="rr"><span>Cursor</span><span class="mono">{cursorX>=0?`${cursorX}, ${cursorY}`:'—'}</span></div>
      <div class="rr"><span>Widgets</span><span class="mono">{placedWidgets.length}</span></div>
      <div class="rr" style="color:var(--text-muted);font-size:var(--fs-xs)">Klicke ein Widget auf dem Canvas zum Bearbeiten</div>
    {/if}
  {:else if id==='layers'}
    <div class="ll">{#each [...layers].reverse() as layer, ri}{@const idx=layers.length-1-ri}<div class="li" class:active={layer.id===activeLayer} class:drag-over={ldOver===idx} draggable="true" onclick={()=>activeLayer=layer.id} ondragstart={(e)=>ldStart(e,idx)} ondragover={(e)=>ldDragOver(e,idx)} ondrop={(e)=>ldDrop(e,idx)} ondragend={ldEnd}><span class="lh"><i class="fa-solid fa-grip-vertical"></i></span><button class="lv" onclick={(e)=>{e.stopPropagation();toggleVis(layer.id);render();}}><i class="fa-solid {layer.visible?'fa-eye':'fa-eye-slash'}"></i></button><span class="ln" contenteditable="false" ondblclick={(e)=>{e.target.contentEditable='true';e.target.focus();}} onblur={(e)=>{e.target.contentEditable='false';layers=layers.map(l=>l.id===layer.id?{...l,name:e.target.textContent}:l);}} onkeydown={(e)=>{if(e.key==='Enter'){e.preventDefault();e.target.blur();}}}>{layer.name}</span></div>{/each}</div>
    <div class="la"><button class="lab" onclick={()=>addLayer()}><i class="fa-solid fa-plus"></i></button><button class="lab" onclick={()=>dupLayer(activeLayer)}><i class="fa-solid fa-copy"></i></button><button class="lab" onclick={()=>rmLayer(activeLayer)}><i class="fa-solid fa-trash"></i></button></div>
  {:else if id==='weather'}
    <div class="rr"><span>Aktueller Ort</span><span class="mono">{weatherLocation?.name || '—'}</span></div>
    {#if weather}
      <div class="rr"><span>Temperatur</span><span class="mono">{weather.temperature_2m}°C</span></div>
      <div class="rr"><span>Feuchtigkeit</span><span class="mono">{weather.relative_humidity_2m}%</span></div>
      <div class="rr"><span>Wind</span><span class="mono">{weather.wind_speed_10m} km/h</span></div>
    {/if}
    <div class="loc-search">
      <input type="text" class="ti" placeholder="Ort suchen..." value={locationSearch} oninput={onLocationInput}>
      {#if locationResults.length > 0}
        <div class="loc-results">
          {#each locationResults as loc}
            <button class="loc-item" onclick={() => selectLocation(loc)}>
              <span class="loc-name">{loc.name}</span>
              <span class="loc-detail">{loc.admin || ''}{loc.country ? ', '+loc.country : ''}</span>
            </button>
          {/each}
        </div>
      {/if}
    </div>
  {:else if id==='widgets'}
    {#each ['zeit','cpu','ram','disk','net','sys','wetter','deko'] as cat}
      {@const items = widgetList.filter(w => w.cat === cat)}
      {#if items.length > 0}
        {@const catInfo = {zeit:['fa-clock','Zeit'],cpu:['fa-microchip','CPU'],ram:['fa-memory','RAM'],disk:['fa-hard-drive','Festplatten'],net:['fa-network-wired','Netzwerk'],sys:['fa-server','System'],wetter:['fa-cloud-sun','Wetter'],deko:['fa-pen','Dekoration']}[cat] || ['fa-circle',cat]}
        <div class="wc-cat"><i class="fa-solid {catInfo[0]}"></i> {catInfo[1]}</div>
        <div class="wc-grid">
          {#each items as w}
            <button class="wc-btn" onclick={() => placeWidget(w)} title="{w.label} ({w.w}×{w.h})">
              <span class="wc-name">{w.label}</span>
              <span class="wc-size">{w.w}×{w.h}</span>
            </button>
          {/each}
        </div>
      {/if}
    {/each}
  {/if}
{/snippet}

<div class="studio">
    <div class="side-panel" ondragover={(e)=>sDragOver(e,'left')} ondragleave={sDragLeave} ondrop={(e)=>sDrop(e,'left')} class:drop-target={pdropSide==='left'}>
      <div class="studio-header"><i class="fa-solid fa-display"></i> OLED Studio</div>
      {#each lpanels as pid (pid)}
        <PanelWrapper id={pid} icon="fa-{_pd[pid]?.icon||'circle'}" label={panelLabel(pid)} collapsible={panelCollapsible(pid)} onDragStart={pDragStart}>
          {@render panelContent(pid)}
        </PanelWrapper>
      {/each}
    </div>
    <div class="canvas-area">
      <div class="canvas-scroll"><canvas bind:this={canvasEl} width={W*zoom} height={H*zoom} onpointerdown={onDown} onpointermove={onMove} onpointerup={onUp} style="width:{W*zoom}px;height:{H*zoom}px"></canvas></div>
    </div>
    <div class="side-panel" ondragover={(e)=>sDragOver(e,'right')} ondragleave={sDragLeave} ondrop={(e)=>sDrop(e,'right')} class:drop-target={pdropSide==='right'}>
      {#each rpanels as pid (pid)}
        <PanelWrapper id={pid} icon="fa-{_pd[pid]?.icon||'circle'}" label={panelLabel(pid)} collapsible={panelCollapsible(pid)} onDragStart={pDragStart}>
          {@render panelContent(pid)}
        </PanelWrapper>
      {/each}
    </div>
</div>


<style>
  .studio { display: flex; height: 100%; overflow: hidden; }
  .studio-header { font: 700 var(--fs-xl) var(--font); color: var(--text-primary); padding: 10px 10px 6px; display: flex; align-items: center; gap: 10px; flex-shrink: 0; }
  .studio-header i { color: var(--accent); }

  .side-panel { width: 300px; flex-shrink: 0; background: var(--bg-base); padding: 4px; display: flex; flex-direction: column; gap: 4px; overflow-y: auto; }
  .side-panel:first-child { border-right: 1px solid var(--border); }
  .side-panel:last-child { border-left: 1px solid var(--border); }
  .drop-target { outline: 2px dashed var(--accent); outline-offset: -2px; background: rgba(0,180,255,0.04); }

  .canvas-area { flex: 1; display: flex; flex-direction: column; min-width: 0; background: #1a1a22; }
  .canvas-scroll { flex: 1; overflow: scroll; display: flex; align-items: flex-start; justify-content: flex-start; padding: 20px; }
  .canvas-scroll canvas { image-rendering: pixelated; touch-action: none; cursor: crosshair; box-shadow: 0 0 0 1px var(--border), 0 4px 20px rgba(0,0,0,0.4); flex-shrink: 0; }

  /* Tool Grid */
  .tool-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 3px; margin-bottom: 6px; }
  .tool-btn { height: 34px; border-radius: var(--radius-sm); border: 1px solid var(--border); background: var(--bg-surface); color: var(--text-muted); cursor: pointer; font-size: var(--fs-xs); display: flex; align-items: center; justify-content: center; transition: all 120ms; }
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

  /* Ortssuche */
  .loc-search { margin-top: 4px; }
  .loc-results { display: flex; flex-direction: column; gap: 2px; margin-top: 4px; max-height: 150px; overflow-y: auto; }
  .loc-item { display: flex; flex-direction: column; padding: 6px 8px; border-radius: var(--radius-sm); border: 1px solid var(--border); background: var(--bg-surface); cursor: pointer; text-align: left; font: 500 var(--fs-sm) var(--font); color: var(--text-secondary); transition: all 120ms; }
  .loc-item:hover { border-color: var(--accent); color: var(--accent); }
  .loc-name { font-weight: 600; }
  .loc-detail { font: 500 var(--fs-xs) var(--font); color: var(--text-muted); }

  /* Widgets */
  .wc-cat { font: 600 var(--fs-xs) var(--font); text-transform: uppercase; letter-spacing: 0.04em; color: var(--text-muted); display: flex; align-items: center; gap: 4px; margin-top: 4px; }
  .wc-cat i { color: var(--accent); }
  .wc-grid { display: flex; flex-direction: column; gap: 2px; }
  .wc-btn { display: flex; align-items: center; justify-content: space-between; padding: 6px 10px; border-radius: var(--radius-sm); border: 1px solid var(--border); background: var(--bg-surface); color: var(--text-secondary); font: 500 var(--fs-sm) var(--font); cursor: pointer; transition: all 120ms; text-align: left; width: 100%; }
  .wc-btn:hover { border-color: var(--accent); color: var(--accent); background: var(--accent-dim); }
  .wc-btn:active { background: var(--accent); color: #fff; }
  .wc-size { font: 500 var(--fs-xs) var(--mono); color: var(--text-muted); }

  @media (max-width: 900px) { .side-panel { width: 200px; } }
</style>
