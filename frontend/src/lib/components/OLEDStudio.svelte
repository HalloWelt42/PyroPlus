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

  /* ═══ SCREEN-VERWALTUNG (mehrere Bilder/Displays) ═══ */
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

  function addScreen() {
    saveCurrentScreen();
    const id = _screenId++;
    screens = [...screens, { id, name: `Screen ${id + 1}`, widgets: [], layers: [{ id: 0, name: 'Hintergrund', pixels: Array.from(new Uint8Array(W*H)), visible: true }], thumbnail: '' }];
    switchScreen(id);
  }

  function removeScreen(id) {
    if (screens.length <= 1) return;
    screens = screens.filter(sc => sc.id !== id);
    if (activeScreen === id) switchScreen(screens[0].id);
  }

  function switchScreen(id) {
    saveCurrentScreen();
    activeScreen = id;
    const sc = screens.find(sc => sc.id === id);
    if (!sc) return;
    placedWidgets = sc.widgets ? JSON.parse(JSON.stringify(sc.widgets)) : [];
    layers = sc.layers ? sc.layers.map(l => ({ ...l, pixels: new Uint8Array(l.pixels) })) : [{ id: 0, name: 'Hintergrund', pixels: new Uint8Array(W*H), visible: true }];
    activeLayer = layers[0]?.id || 0;
    _nid = Math.max(0, ...layers.map(l => l.id)) + 1;
    selectedWidget = -1;
    renderWidgets();
  }

  function duplicateScreen() {
    saveCurrentScreen();
    const src = screens.find(sc => sc.id === activeScreen);
    if (!src) return;
    const id = _screenId++;
    screens = [...screens, { id, name: src.name + ' Kopie', widgets: JSON.parse(JSON.stringify(src.widgets)), layers: JSON.parse(JSON.stringify(src.layers)), thumbnail: src.thumbnail }];
    switchScreen(id);
  }

  /* Screen D&D Reorder */
  let scDragFrom = $state(-1), scDragOver = $state(-1);
  function scDragStart(e, idx) { scDragFrom = idx; e.dataTransfer.effectAllowed = 'move'; }
  function scDragOverFn(e, idx) { e.preventDefault(); scDragOver = idx; }
  function scDrop(e, idx) { e.preventDefault(); scDragOver = -1; if (scDragFrom === idx) return; const arr = [...screens]; const [m] = arr.splice(scDragFrom, 1); arr.splice(idx, 0, m); screens = arr; scDragFrom = -1; }
  function scDragEnd() { scDragFrom = -1; scDragOver = -1; }

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

  /* Zahl rechtsbündig mit führenden Leerzeichen */
  function pad(n, len=3) { const s = String(n); return s.length >= len ? s : ' '.repeat(len - s.length) + s; }
  /* Tausenderpunkt: 24214 → 24.214 */
  function tsd(n) { return Math.round(n).toLocaleString('de-DE'); }

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
                 getText: (p) => (p.prefix||'')+pad(Math.round(s.stats?.cpu?.temp||0))+'°' },
    cpu_pct:   { cat:'cpu',  label:'Auslastung %',   w:24, h:7, props:{ scale:1, prefix:'' },
                 getText: (p) => (p.prefix||'')+pad(Math.round(s.stats?.cpu?.percent||0))+'%' },
    cpu_cores: { cat:'cpu',  label:'Kerne',          w:12, h:7, props:{ scale:1, prefix:'' },
                 getText: (p) => (p.prefix||'')+(s.stats?.cpu?.cores||4) },
    cpu_bar:   { cat:'cpu',  label:'Balken',         w:60, h:6, props:{ width:60, height:6 }, isShape: true,
                 draw: (px,x,y,p) => E.drawBar(px, x, y, p.width||60, p.height||6, s.stats?.cpu?.percent||0) },
    /* ─── RAM ─── */
    ram_used:  { cat:'ram',  label:'Benutzt',        w:30, h:7, props:{ scale:1, prefix:'', tsep:true },
                 getText: (p) => (p.prefix||'')+(p.tsep?tsd(s.stats?.ram?.used_gb||0):Math.round(s.stats?.ram?.used_gb||0))+' G' },
    ram_total: { cat:'ram',  label:'Gesamt',         w:30, h:7, props:{ scale:1, prefix:'', tsep:true },
                 getText: (p) => (p.prefix||'')+(p.tsep?tsd(s.stats?.ram?.total_gb||0):Math.round(s.stats?.ram?.total_gb||0))+' G' },
    ram_pct:   { cat:'ram',  label:'Prozent',        w:24, h:7, props:{ scale:1, prefix:'' },
                 getText: (p) => (p.prefix||'')+pad(Math.round(s.stats?.ram?.percent||0))+'%' },
    ram_bar:   { cat:'ram',  label:'Balken',         w:60, h:6, props:{ width:60, height:6 }, isShape: true,
                 draw: (px,x,y,p) => E.drawBar(px, x, y, p.width||60, p.height||6, s.stats?.ram?.percent||0) },
    /* ─── Disk ─── */
    disk_name: { cat:'disk', label:'Name',           w:48, h:7, props:{ scale:1, prefix:'', diskIdx:0 },
                 getText: (p) => (p.prefix||'')+(s.stats?.disks?.[p.diskIdx||0]?.label||s.stats?.disks?.[p.diskIdx||0]?.mount||'?') },
    disk_used: { cat:'disk', label:'Benutzt',        w:48, h:7, props:{ scale:1, prefix:'', diskIdx:0, tsep:true },
                 getText: (p) => { const d=s.stats?.disks?.[p.diskIdx||0]; return (p.prefix||'')+(d?(p.tsep?tsd(d.used_gb):Math.round(d.used_gb))+' G':'?'); }},
    disk_total:{ cat:'disk', label:'Gesamt',         w:48, h:7, props:{ scale:1, prefix:'', diskIdx:0, tsep:true },
                 getText: (p) => { const d=s.stats?.disks?.[p.diskIdx||0]; return (p.prefix||'')+(d?(p.tsep?tsd(d.total_gb):Math.round(d.total_gb))+' G':'?'); }},
    disk_pct:  { cat:'disk', label:'Prozent',        w:30, h:7, props:{ scale:1, prefix:'', diskIdx:0 },
                 getText: (p) => (p.prefix||'')+pad(Math.round(s.stats?.disks?.[p.diskIdx||0]?.percent||0))+'%' },
    disk_bar:  { cat:'disk', label:'Balken',         w:60, h:6, props:{ width:60, height:6, diskIdx:0 }, isShape: true,
                 draw: (px,x,y,p) => E.drawBar(px, x, y, p.width||60, p.height||6, s.stats?.disks?.[p.diskIdx||0]?.percent||0) },
    /* ─── Netzwerk ─── */
    net_ip:    { cat:'net',  label:'IP-Adresse',     w:60, h:7, props:{ scale:1, prefix:'' },
                 getText: (p) => (p.prefix||'')+(s.stats?.network?.ip||'0.0.0.0') },
    net_if:    { cat:'net',  label:'Interface',      w:36, h:7, props:{ scale:1, prefix:'' },
                 getText: (p) => (p.prefix||'')+(s.stats?.network?.interface||'?') },
    net_rx:    { cat:'net',  label:'Download',       w:60, h:7, props:{ scale:1, prefix:'' },
                 getText: (p) => { const b=s.stats?.network?.rx_bytes_sec||0; return (p.prefix||'')+(b>1048576?(b/1048576).toFixed(1)+' MB/s':b>1024?Math.round(b/1024)+' KB/s':b+' B/s'); }},
    net_tx:    { cat:'net',  label:'Upload',         w:60, h:7, props:{ scale:1, prefix:'' },
                 getText: (p) => { const b=s.stats?.network?.tx_bytes_sec||0; return (p.prefix||'')+(b>1048576?(b/1048576).toFixed(1)+' MB/s':b>1024?Math.round(b/1024)+' KB/s':b+' B/s'); }},
    /* ─── System ─── */
    uptime:    { cat:'sys',  label:'Uptime',         w:48, h:7, props:{ scale:1, prefix:'' },
                 getText: (p) => (p.prefix||'')+(s.stats?.uptime?.formatted||'0:00') },
    /* ─── Deko Sprites ─── */
    snowman:   { cat:'deko', label:'Schneemann',     w:8, h:10, props:{ scale:1 }, isShape: true,
                 draw: (px,x,y,p) => E.drawSprite(px,'snowman',x,y,p.scale||1) },
    snowflake: { cat:'deko', label:'Schneeflocke',   w:8, h:8, props:{ scale:1 }, isShape: true,
                 draw: (px,x,y,p) => E.drawSprite(px,'snowflake',x,y,p.scale||1) },
    heart:     { cat:'deko', label:'Herz',           w:8, h:8, props:{ scale:1 }, isShape: true,
                 draw: (px,x,y,p) => E.drawSprite(px,'heart',x,y,p.scale||1) },
    star:      { cat:'deko', label:'Stern',          w:8, h:8, props:{ scale:1 }, isShape: true,
                 draw: (px,x,y,p) => E.drawSprite(px,'star',x,y,p.scale||1) },
    cat_spr:   { cat:'deko', label:'Katze',          w:8, h:8, props:{ scale:1 }, isShape: true,
                 draw: (px,x,y,p) => E.drawSprite(px,'cat',x,y,p.scale||1) },
    dog_spr:   { cat:'deko', label:'Hund',           w:8, h:8, props:{ scale:1 }, isShape: true,
                 draw: (px,x,y,p) => E.drawSprite(px,'dog',x,y,p.scale||1) },
    tree_spr:  { cat:'deko', label:'Tannenbaum',     w:8, h:8, props:{ scale:1 }, isShape: true,
                 draw: (px,x,y,p) => E.drawSprite(px,'tree',x,y,p.scale||1) },
    sun_spr:   { cat:'deko', label:'Sonne',          w:8, h:8, props:{ scale:1 }, isShape: true,
                 draw: (px,x,y,p) => E.drawSprite(px,'sun_deco',x,y,p.scale||1) },
    moon_spr:  { cat:'deko', label:'Mond',           w:8, h:8, props:{ scale:1 }, isShape: true,
                 draw: (px,x,y,p) => E.drawSprite(px,'moon_deco',x,y,p.scale||1) },
    music_spr: { cat:'deko', label:'Musik',          w:8, h:8, props:{ scale:1 }, isShape: true,
                 draw: (px,x,y,p) => E.drawSprite(px,'music',x,y,p.scale||1) },
    skull_spr: { cat:'deko', label:'Totenkopf',      w:8, h:8, props:{ scale:1 }, isShape: true,
                 draw: (px,x,y,p) => E.drawSprite(px,'skull',x,y,p.scale||1) },
    gift_spr:  { cat:'deko', label:'Geschenk',       w:8, h:8, props:{ scale:1 }, isShape: true,
                 draw: (px,x,y,p) => E.drawSprite(px,'gift',x,y,p.scale||1) },
    bell_spr:  { cat:'deko', label:'Glocke',         w:8, h:8, props:{ scale:1 }, isShape: true,
                 draw: (px,x,y,p) => E.drawSprite(px,'bell',x,y,p.scale||1) },
    /* ─── Text + Linien ─── */
    marquee:   { cat:'deko', label:'Laufschrift',    w:128, h:7, props:{ scale:1, text:'Hallo Welt!' },
                 getText: (p) => p.text || 'Laufschrift' },
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
    /* ─── Sparklines (Verlaufsgraph) ─── */
    spark_cpu: { cat:'cpu',  label:'CPU Verlauf',    w:60, h:20, props:{ width:60, height:20 }, isShape: true,
                 draw: (px,x,y,p) => E.drawSparkline(px, _hist.cpu, x, y, p.width||60, p.height||20) },
    spark_temp:{ cat:'cpu',  label:'Temp Verlauf',   w:60, h:20, props:{ width:60, height:20 }, isShape: true,
                 draw: (px,x,y,p) => E.drawSparkline(px, _hist.temp, x, y, p.width||60, p.height||20) },
    spark_ram: { cat:'ram',  label:'RAM Verlauf',    w:60, h:20, props:{ width:60, height:20 }, isShape: true,
                 draw: (px,x,y,p) => E.drawSparkline(px, _hist.ram, x, y, p.width||60, p.height||20) },
    /* ─── Gauges (Halbkreis) ─── */
    gauge_cpu: { cat:'cpu',  label:'CPU Gauge',      w:32, h:18, props:{ radius:12 }, isShape: true,
                 draw: (px,x,y,p) => E.drawGauge(px, s.stats?.cpu?.percent||0, x, y, p.radius||12) },
    gauge_ram: { cat:'ram',  label:'RAM Gauge',      w:32, h:18, props:{ radius:12 }, isShape: true,
                 draw: (px,x,y,p) => E.drawGauge(px, s.stats?.ram?.percent||0, x, y, p.radius||12) },
    gauge_disk:{ cat:'disk', label:'Disk Gauge',     w:32, h:18, props:{ radius:12, diskIdx:0 }, isShape: true,
                 draw: (px,x,y,p) => E.drawGauge(px, s.stats?.disks?.[p.diskIdx||0]?.percent||0, x, y, p.radius||12) },
    gauge_temp:{ cat:'cpu',  label:'Temp Gauge',     w:32, h:18, props:{ radius:12 }, isShape: true,
                 draw: (px,x,y,p) => E.drawGauge(px, Math.min(100,(s.stats?.cpu?.temp||0)/80*100), x, y, p.radius||12) },
    /* ─── Section Header ─── */
    section:   { cat:'deko', label:'── Header ──',   w:60, h:7, props:{ width:60, text:'CPU' }, isShape: true,
                 draw: (px,x,y,p) => E.drawSectionHeader(px, p.text||'Label', x, y, p.width||60) },
  };
  const widgetList = Object.entries(widgetTypes).map(([id,v])=>({id,...v}));

  /* ═══ HISTORY für Sparklines ═══ */
  const _hist = { cpu: [], temp: [], ram: [] };
  const HIST_LEN = 30;

  /* Platzierte Widgets — jedes hat Position, Typ, eigene Eigenschaften */
  let placedWidgets = $state([]);
  let selectedWidget = $state(-1);
  let selectedWidgets = $state(new Set()); // Multi-Select

  /* Kontextmenü */
  let ctxMenu = $state(null); // { x, y, widgetIdx }

  let snapGrid = $state(0); // 0=aus, 4/8/16=Rasterweite

  function snapPos(v) { return snapGrid > 0 ? Math.round(v / snapGrid) * snapGrid : v; }

  function placeWidget(w) {
    const wt = widgetTypes[w.id];
    placedWidgets = [...placedWidgets, {
      id: Date.now(),
      type: w.id,
      x: 4, y: 4,
      props: { ...wt.props, invert: false, border: false, align: 'left' },
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
        // Rahmen für Shapes
        if (w.props.border) {
          const bw = w.props.width || wt.w, bh = w.props.height || wt.h;
          E.drawRect(w.x-1,w.y-1,w.x+bw,w.y+bh,(px2,py)=>{if(px2>=0&&px2<W&&py>=0&&py<H)px[py*W+px2]=1;},false);
        }
      } else {
        const text = wt.getText(w.props);
        const sx = w.props.scaleX ?? w.props.scale ?? 1;
        const sy = w.props.scaleY ?? w.props.scale ?? 1;
        const hasEx = w.props.invert || w.props.border || (w.props.align && w.props.align !== 'left');
        if (hasEx) {
          E.drawTextEx(px, text, w.x, w.y, sx, sy, {
            invert: !!w.props.invert,
            border: !!w.props.border,
            align: w.props.align || 'left',
            boxW: w.props.boxW || 0,
          });
        } else {
          E.drawText(px, text, w.x, w.y, sx, sy);
        }
      }
    }
    layers = [...layers];
    render();
    autoSave();
  }

  /* Widget-Rendering alle Sekunde aktualisieren (für Uhr etc.) + History sammeln */
  let _widgetTimer;
  function startWidgetTimer() { _widgetTimer = setInterval(() => {
    // History für Sparklines sammeln
    _hist.cpu.push(s.stats?.cpu?.percent || 0);
    _hist.temp.push(s.stats?.cpu?.temp || 0);
    _hist.ram.push(s.stats?.ram?.percent || 0);
    if (_hist.cpu.length > HIST_LEN) _hist.cpu.shift();
    if (_hist.temp.length > HIST_LEN) _hist.temp.shift();
    if (_hist.ram.length > HIST_LEN) _hist.ram.shift();
    if (placedWidgets.length > 0) renderWidgets();
    renderAllPreviews();
  }, 1000); }
  function stopWidgetTimer() { clearInterval(_widgetTimer); }

  /* ═══ CANVAS ═══ */
  let canvasEl = $state(null), previewEl = $state(null);
  function render() {
    const comp = E.composite(layers);
    if (canvasEl) {
      E.renderCanvas(canvasEl.getContext('2d'), comp, zoom, showGrid);
      const ctx = canvasEl.getContext('2d');
      // Multi-Select Rahmen
      const selSet = selectedWidgets.size > 0 ? selectedWidgets : (selectedWidget >= 0 ? new Set([selectedWidget]) : new Set());
      for (const idx of selSet) {
        const w = placedWidgets[idx];
        if (!w) continue;
        const wt = widgetTypes[w.type];
        if (!wt) continue;
        const ww = wt.isShape ? (w.props.width || w.props.radius*2 || wt.w) : wt.w * (w.props.scaleX ?? w.props.scale ?? 1);
        const wh = wt.isShape ? (w.props.height || w.props.radius*2 || wt.h) : wt.h * (w.props.scaleY ?? w.props.scale ?? 1);
        ctx.strokeStyle = idx === selectedWidget ? 'rgba(0,180,255,0.7)' : 'rgba(0,232,138,0.5)';
        ctx.lineWidth = 1;
        ctx.setLineDash([4, 2]);
        ctx.strokeRect(w.x * zoom - 1, w.y * zoom - 1, ww * zoom + 2, wh * zoom + 2);
        ctx.setLineDash([]);
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
      const ww = wt.isShape ? (w.props.width || wt.w) : wt.w * (w.props.scaleX ?? w.props.scale ?? 1);
      const wh = wt.isShape ? (w.props.height || wt.h) : wt.h * (w.props.scaleY ?? w.props.scale ?? 1);
      if (x >= w.x && x < w.x + ww && y >= w.y && y < w.y + wh) return i;
    }
    return -1;
  }

  let widgetDrag = null;
  function onDown(e) {
    if (!canvasEl) return;
    ctxMenu = null; // Kontextmenü schließen
    const [x,y]=m2p(e);

    // Widget-Klick prüfen (im Move-Modus)
    if (tool === 'move') {
      const hit = hitTestWidget(x, y);
      if (hit >= 0) {
        // Shift+Klick = Multi-Select toggle
        if (e.shiftKey) {
          const ns = new Set(selectedWidgets);
          if (ns.has(hit)) ns.delete(hit); else ns.add(hit);
          selectedWidgets = ns;
          selectedWidget = hit;
          render();
          return;
        }
        selectedWidget = hit;
        if (!selectedWidgets.has(hit)) selectedWidgets = new Set([hit]);
        // Multi-Drag: Startpositionen aller selektierten Widgets merken
        const origins = new Map();
        for (const idx of selectedWidgets) origins.set(idx, { x: placedWidgets[idx].x, y: placedWidgets[idx].y });
        widgetDrag = { idx: hit, startX: x, startY: y, origX: placedWidgets[hit].x, origY: placedWidgets[hit].y, origins };
        drawing = true;
        render();
        return;
      }
    }

    // Klick ohne Shift = Einzel-Select oder abwählen
    const hit2 = hitTestWidget(x, y);
    selectedWidget = hit2;
    selectedWidgets = hit2 >= 0 ? new Set([hit2]) : new Set();
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
    // Widget-Drag (Multi oder Einzel)
    if (widgetDrag) {
      const dx = x - widgetDrag.startX, dy = y - widgetDrag.startY;
      if (widgetDrag.origins && widgetDrag.origins.size > 1) {
        // Multi-Drag
        for (const [idx, orig] of widgetDrag.origins) {
          placedWidgets[idx].x = Math.max(0, Math.min(W-1, orig.x + dx));
          placedWidgets[idx].y = Math.max(0, Math.min(H-1, orig.y + dy));
        }
      } else {
        placedWidgets[widgetDrag.idx].x = Math.max(0, Math.min(W-1, widgetDrag.origX + dx));
        placedWidgets[widgetDrag.idx].y = Math.max(0, Math.min(H-1, widgetDrag.origY + dy));
      }
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

  function onContext(e) {
    e.preventDefault();
    if (!canvasEl) return;
    const [x,y]=m2p(e);
    const hit = hitTestWidget(x, y);
    if (hit >= 0) {
      selectedWidget = hit;
      if (!selectedWidgets.has(hit)) selectedWidgets = new Set([hit]);
      ctxMenu = { x: e.clientX, y: e.clientY, widgetIdx: hit };
      render();
    } else {
      ctxMenu = null;
    }
  }

  function ctxAction(action) {
    const idx = ctxMenu?.widgetIdx;
    if (idx == null || idx < 0) { ctxMenu = null; return; }
    if (action === 'dup') {
      const src = placedWidgets[idx];
      placedWidgets = [...placedWidgets, { ...JSON.parse(JSON.stringify(src)), id: Date.now(), x: src.x+4, y: src.y+4 }];
      selectedWidget = placedWidgets.length - 1;
      selectedWidgets = new Set([selectedWidget]);
      renderWidgets();
    } else if (action === 'del') {
      placedWidgets = placedWidgets.filter((_, i) => i !== idx);
      selectedWidget = -1; selectedWidgets = new Set();
      renderWidgets();
    } else if (action === 'front') {
      const [w] = placedWidgets.splice(idx, 1);
      placedWidgets = [...placedWidgets, w];
      selectedWidget = placedWidgets.length - 1;
      selectedWidgets = new Set([selectedWidget]);
      renderWidgets();
    } else if (action === 'back') {
      const [w] = placedWidgets.splice(idx, 1);
      placedWidgets = [w, ...placedWidgets];
      selectedWidget = 0;
      selectedWidgets = new Set([0]);
      renderWidgets();
    }
    ctxMenu = null;
  }
  function clearLayer(){pushH();ap()?.fill(0);render();}
  function invertLayer(){pushH();const px=ap();if(px)for(let i=0;i<px.length;i++)px[i]=px[i]?0:1;render();}
  async function sendToOled() {
    saveCurrentScreen();
    try {
      // Alle Screens als Widget-Konfiguration ans Backend schicken
      // Backend rendert sie selbständig mit Live-Daten
      const screenConfigs = screens.map(sc => ({
        type: 'system',
        name: sc.name,
        widgets: (sc.widgets || []).map(w => ({
          type: w.type,
          x: w.x,
          y: w.y,
          scaleX: w.props?.scaleX ?? w.props?.scale ?? 1,
          scaleY: w.props?.scaleY ?? w.props?.scale ?? 1,
          prefix: w.props?.prefix,
          text: w.props?.text,
          w: w.props?.width,
          h: w.props?.height,
          scale: w.props?.scale,
          radius: w.props?.radius,
          diskIdx: w.props?.diskIdx,
          invert: w.props?.invert || false,
          border: w.props?.border || false,
          align: w.props?.align || 'left',
          boxW: w.props?.boxW || 0,
          tsep: w.props?.tsep || false,
        })),
      }));

      // Bestehende Screens löschen und neue setzen
      const oledScreens = s.oled?.screens || [];
      // Ersten Screen updaten
      if (screenConfigs.length > 0) {
        await s.updateOledScreen(0, screenConfigs[0]);
      }
      // Weitere Screens hinzufügen
      for (let i = 1; i < screenConfigs.length; i++) {
        await s.addOledScreen(screenConfigs[i]);
      }
      // Überzählige Backend-Screens löschen
      while (oledScreens.length > screenConfigs.length && oledScreens.length > 1) {
        await s.removeOledScreen(oledScreens.length - 1);
        oledScreens.pop();
      }

      // Rotation setzen
      if (rotation) {
        await s.setOledRotation(rotationInterval);
        await s.setOledMode('auto');
      } else {
        await s.setOledMode('auto');
      }

      s.toast(`${screenConfigs.length} Screen(s) an Backend gesendet`, 'ok');
    } catch (e) {
      s.toast('Fehler: ' + (e.message||e), 'err');
    }
  }

  async function loadFromOled() {
    try {
      // Widget-Konfigurationen vom Backend holen (nicht nur PNG!)
      const backendScreens = s.oled?.screens;
      if (!backendScreens || backendScreens.length === 0) {
        s.toast('Keine Screens im Backend', 'info');
        return;
      }

      // Backend-Screens in Editor-Format konvertieren
      const newScreens = backendScreens.map((bs, i) => {
        const widgets = (bs.widgets || []).map(bw => ({
          id: Date.now() + Math.random(),
          type: bw.type,
          x: bw.x || 0,
          y: bw.y || 0,
          props: {
            ...(widgetTypes[bw.type]?.props || {}),
            scaleX: bw.scaleX ?? bw.scale ?? (widgetTypes[bw.type]?.props?.scale ?? 1),
            scaleY: bw.scaleY ?? bw.scale ?? (widgetTypes[bw.type]?.props?.scale ?? 1),
            prefix: bw.prefix ?? widgetTypes[bw.type]?.props?.prefix,
            text: bw.text ?? widgetTypes[bw.type]?.props?.text,
            width: bw.w ?? widgetTypes[bw.type]?.props?.width,
            height: bw.h ?? widgetTypes[bw.type]?.props?.height,
            diskIdx: bw.diskIdx ?? widgetTypes[bw.type]?.props?.diskIdx,
            invert: bw.invert || false,
            border: bw.border || false,
            align: bw.align || 'left',
            boxW: bw.boxW || 0,
            tsep: bw.tsep || false,
          },
        }));
        return {
          id: i,
          name: bs.name || `Screen ${i + 1}`,
          widgets,
          layers: [{ id: 0, name: 'Hintergrund', pixels: Array.from(new Uint8Array(W*H)), visible: true }],
          thumbnail: '',
        };
      });

      screens = newScreens;
      _screenId = screens.length;
      activeScreen = screens[0]?.id ?? 0;
      const sc = screens[0];
      placedWidgets = sc.widgets ? JSON.parse(JSON.stringify(sc.widgets)) : [];
      layers = sc.layers.map(l => ({ ...l, pixels: new Uint8Array(l.pixels) }));
      activeLayer = 0;
      _nid = 1;
      selectedWidget = -1;
      renderWidgets();
      s.toast(`${newScreens.length} Screen(s) vom Backend geladen`, 'ok');
    } catch (e) {
      s.toast('Fehler: ' + (e.message||e), 'err');
    }
  }

  async function exportScreens() {
    saveCurrentScreen();
    const data = JSON.stringify({ screens, version: '1.0' }, null, 2);
    const blob = new Blob([data], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = `pyroplus-oled-${new Date().toISOString().slice(0,10)}.json`;
    a.click(); URL.revokeObjectURL(url);
    s.toast('Screens exportiert', 'ok');
  }

  async function importScreens() {
    const input = document.createElement('input');
    input.type = 'file'; input.accept = '.json';
    input.onchange = async (e) => {
      try {
        const text = await e.target.files[0].text();
        const data = JSON.parse(text);
        if (data.screens?.length > 0) {
          screens = data.screens.map((sc, i) => ({
            ...sc, id: i,
            layers: sc.layers || [{ id: 0, name: 'Hintergrund', pixels: Array.from(new Uint8Array(W*H)), visible: true }],
          }));
          _screenId = screens.length;
          switchScreen(screens[0].id);
          s.toast(`${screens.length} Screen(s) importiert`, 'ok');
        }
      } catch (err) { s.toast('Import-Fehler: ' + err.message, 'err'); }
    };
    input.click();
  }

  /* ═══ PANEL D&D ═══ */
  let lpanels=$state(['preview','props','layers','widgets','templates']), rpanels=$state(['tools','display','color','weather','clock']);
  let pdragId=$state(null), pdropSide=$state(null);
  function pDragStart(e,id){pdragId=id;e.dataTransfer.setData('application/x-oled-panel',id);e.dataTransfer.effectAllowed='move';}
  function pDragEnd(){pdragId=null;pdropSide=null;}
  function sDragOver(e,side){if(!e.dataTransfer.types.includes('application/x-oled-panel'))return;e.preventDefault();pdropSide=side;}
  function sDragLeave(e){if(!e.currentTarget.contains(e.relatedTarget))pdropSide=null;}
  function sDrop(e,side){e.preventDefault();const id=e.dataTransfer.getData('application/x-oled-panel');if(!id)return;lpanels=lpanels.filter(p=>p!==id);rpanels=rpanels.filter(p=>p!==id);if(side==='left')lpanels=[...lpanels,id];else rpanels=[...rpanels,id];pdragId=null;pdropSide=null;}

  function onKey(e){
    if(e.target.tagName==='INPUT'||e.target.tagName==='TEXTAREA')return;
    if(e.ctrlKey&&e.key==='z'){undo();e.preventDefault();}
    if(e.ctrlKey&&e.key==='y'){redo();e.preventDefault();}
    if(e.ctrlKey&&e.key==='d'){
      // Duplizieren (Multi oder Einzel)
      const indices = selectedWidgets.size > 0 ? [...selectedWidgets] : (selectedWidget >= 0 ? [selectedWidget] : []);
      if(indices.length > 0){
        const newSel = new Set();
        for(const idx of indices){
          const src=placedWidgets[idx];
          placedWidgets=[...placedWidgets,{...JSON.parse(JSON.stringify(src)),id:Date.now()+Math.random(),x:src.x+4,y:src.y+4}];
          newSel.add(placedWidgets.length-1);
        }
        selectedWidgets=newSel;selectedWidget=[...newSel][0];renderWidgets();e.preventDefault();return;
      }
    }
    if(e.ctrlKey&&e.key==='a'){
      // Alle selektieren
      selectedWidgets=new Set(placedWidgets.map((_,i)=>i));
      if(placedWidgets.length>0)selectedWidget=0;
      render();e.preventDefault();return;
    }
    if((e.key==='Delete'||e.key==='Backspace')){
      const indices = selectedWidgets.size > 0 ? [...selectedWidgets].sort((a,b)=>b-a) : (selectedWidget >= 0 ? [selectedWidget] : []);
      if(indices.length > 0){ for(const idx of indices) placedWidgets.splice(idx,1); placedWidgets=[...placedWidgets]; selectedWidget=-1; selectedWidgets=new Set(); renderWidgets(); e.preventDefault(); return; }
    }
    // Arrow-Key Nudge (Multi oder Einzel)
    if(['ArrowUp','ArrowDown','ArrowLeft','ArrowRight'].includes(e.key)){
      const indices = selectedWidgets.size > 0 ? [...selectedWidgets] : (selectedWidget >= 0 ? [selectedWidget] : []);
      if(indices.length > 0){
        const step=e.shiftKey?(snapGrid||8):1;
        for(const idx of indices){
          const w=placedWidgets[idx];
          if(e.key==='ArrowLeft')w.x=Math.max(0,w.x-step);
          if(e.key==='ArrowRight')w.x=Math.min(W-1,w.x+step);
          if(e.key==='ArrowUp')w.y=Math.max(0,w.y-step);
          if(e.key==='ArrowDown')w.y=Math.min(H-1,w.y+step);
          if(snapGrid>0){w.x=snapPos(w.x);w.y=snapPos(w.y);}
        }
        placedWidgets=[...placedWidgets];renderWidgets();e.preventDefault();return;
      }
    }
    if(e.key==='g'){showGrid=!showGrid;render();}
    if(e.key==='+')zoom=Math.min(16,zoom+1);
    if(e.key==='-')zoom=Math.max(2,zoom-1);
    const t=drawTools.find(t=>t.key===e.key.toUpperCase());if(t&&!e.ctrlKey)tool=t.id;
  }

  /* Panel-Metadaten */
  const _pd = { tools:{icon:'pen',label:'Werkzeuge',c:false}, display:{icon:'eye',label:'Anzeige',c:true}, color:{icon:'palette',label:'Farbe',c:false}, preview:{icon:'display',label:'Vorschau',c:false}, props:{icon:'sliders',label:'Eigenschaften',c:true}, layers:{icon:'layer-group',label:'Ebenen',c:false}, widgets:{icon:'puzzle-piece',label:'Widgets',c:true}, weather:{icon:'cloud-sun',label:'Wetter-Ort',c:true}, templates:{icon:'bookmark',label:'Vorlagen',c:true}, clock:{icon:'clock',label:'Uhr-Einst.',c:true} };

  /* Vordefinierte Vorlagen */
  const templates = [
    { name: 'Uhr + System', widgets: [
      {type:'clock',x:0,y:0,props:{scale:2}},
      {type:'weekday',x:0,y:18,props:{scale:1}},
      {type:'date',x:16,y:18,props:{scale:1}},
      {type:'cpu_temp',x:0,y:30,props:{scale:1,prefix:'CPU '}},
      {type:'ram_pct',x:0,y:40,props:{scale:1,prefix:'RAM '}},
      {type:'net_ip',x:0,y:50,props:{scale:1,prefix:''}},
    ]},
    { name: 'Wetter', widgets: [
      {type:'w_icon',x:2,y:2,props:{}},
      {type:'w_temp',x:14,y:0,props:{scale:2}},
      {type:'w_cond',x:2,y:20,props:{scale:1}},
      {type:'w_hum',x:2,y:30,props:{scale:1}},
      {type:'w_wind',x:2,y:40,props:{scale:1}},
      {type:'w_loc',x:2,y:54,props:{scale:1,text:''}},
      {type:'clock_s',x:76,y:2,props:{scale:1}},
    ]},
    { name: 'Große Uhr', widgets: [
      {type:'clock_l',x:4,y:4,props:{scale:3}},
      {type:'weekday',x:4,y:32,props:{scale:1}},
      {type:'date',x:20,y:32,props:{scale:1}},
      {type:'cpu_temp',x:4,y:50,props:{scale:1,prefix:''}},
      {type:'ram_pct',x:40,y:50,props:{scale:1,prefix:''}},
    ]},
    { name: 'System-Monitor', widgets: [
      {type:'cpu_temp',x:0,y:0,props:{scale:1,prefix:'CPU '}},
      {type:'cpu_bar',x:0,y:10,props:{width:60,height:6}},
      {type:'ram_pct',x:0,y:20,props:{scale:1,prefix:'RAM '}},
      {type:'ram_bar',x:0,y:30,props:{width:60,height:6}},
      {type:'disk_pct',x:0,y:40,props:{scale:1,prefix:'DSK ',diskIdx:0}},
      {type:'disk_bar',x:0,y:50,props:{width:60,height:6,diskIdx:0}},
      {type:'uptime',x:66,y:0,props:{scale:1,prefix:''}},
      {type:'net_ip',x:66,y:10,props:{scale:1,prefix:''}},
      {type:'net_rx',x:66,y:24,props:{scale:1,prefix:'Rx '}},
      {type:'net_tx',x:66,y:34,props:{scale:1,prefix:'Tx '}},
    ]},
    { name: 'Weihnachten', widgets: [
      {type:'tree_spr',x:2,y:2,props:{scale:2}},
      {type:'snowman',x:20,y:4,props:{scale:2}},
      {type:'snowflake',x:50,y:2,props:{scale:1}},
      {type:'snowflake',x:70,y:6,props:{scale:1}},
      {type:'snowflake',x:90,y:0,props:{scale:1}},
      {type:'snowflake',x:110,y:4,props:{scale:1}},
      {type:'gift_spr',x:40,y:14,props:{scale:1}},
      {type:'bell_spr',x:100,y:14,props:{scale:1}},
      {type:'label',x:2,y:34,props:{scale:2,text:'Frohe'}},
      {type:'label',x:2,y:50,props:{scale:2,text:'Weihnachten'}},
    ]},
    { name: 'Party', widgets: [
      {type:'music_spr',x:4,y:4,props:{scale:2}},
      {type:'star',x:30,y:2,props:{scale:1}},
      {type:'star',x:50,y:6,props:{scale:1}},
      {type:'star',x:70,y:0,props:{scale:1}},
      {type:'star',x:90,y:8,props:{scale:1}},
      {type:'heart',x:110,y:2,props:{scale:1}},
      {type:'label',x:24,y:20,props:{scale:3,text:'PARTY'}},
      {type:'clock_s',x:40,y:52,props:{scale:1}},
    ]},
    { name: 'Haustier', widgets: [
      {type:'cat_spr',x:10,y:10,props:{scale:3}},
      {type:'heart',x:50,y:4,props:{scale:1}},
      {type:'heart',x:60,y:8,props:{scale:1}},
      {type:'heart',x:70,y:4,props:{scale:1}},
      {type:'label',x:50,y:20,props:{scale:2,text:'Miau!'}},
      {type:'clock',x:0,y:50,props:{scale:1}},
    ]},
    { name: 'Minimal', widgets: [
      {type:'clock_l',x:16,y:8,props:{scale:3}},
      {type:'date',x:40,y:40,props:{scale:1}},
    ]},
    { name: 'Disk-Monitor', widgets: [
      {type:'disk_name',x:0,y:0,props:{scale:1,prefix:'',diskIdx:0}},
      {type:'disk_bar',x:0,y:10,props:{width:60,height:6,diskIdx:0}},
      {type:'disk_pct',x:64,y:0,props:{scale:1,prefix:'',diskIdx:0}},
      {type:'disk_name',x:0,y:20,props:{scale:1,prefix:'',diskIdx:1}},
      {type:'disk_bar',x:0,y:30,props:{width:60,height:6,diskIdx:1}},
      {type:'disk_pct',x:64,y:20,props:{scale:1,prefix:'',diskIdx:1}},
      {type:'disk_name',x:0,y:40,props:{scale:1,prefix:'',diskIdx:2}},
      {type:'disk_bar',x:0,y:50,props:{width:60,height:6,diskIdx:2}},
      {type:'disk_pct',x:64,y:40,props:{scale:1,prefix:'',diskIdx:2}},
    ]},
    { name: 'Netzwerk', widgets: [
      {type:'net_ip',x:0,y:0,props:{scale:2,prefix:''}},
      {type:'net_if',x:0,y:18,props:{scale:1,prefix:''}},
      {type:'net_rx',x:0,y:30,props:{scale:1,prefix:'DL '}},
      {type:'net_tx',x:0,y:40,props:{scale:1,prefix:'UL '}},
      {type:'uptime',x:0,y:54,props:{scale:1,prefix:'Up '}},
    ]},
    { name: 'Dashboard', widgets: [
      {type:'section',x:0,y:0,props:{width:62,text:'CPU'}},
      {type:'gauge_cpu',x:2,y:10,props:{radius:12}},
      {type:'cpu_temp',x:30,y:14,props:{scale:1,prefix:''}},
      {type:'section',x:66,y:0,props:{width:62,text:'RAM'}},
      {type:'gauge_ram',x:68,y:10,props:{radius:12}},
      {type:'ram_pct',x:96,y:14,props:{scale:1,prefix:''}},
      {type:'section',x:0,y:36,props:{width:128,text:'VERLAUF'}},
      {type:'spark_cpu',x:0,y:44,props:{width:62,height:18}},
      {type:'spark_ram',x:66,y:44,props:{width:62,height:18}},
    ]},
    { name: 'Gauges', widgets: [
      {type:'gauge_cpu',x:2,y:2,props:{radius:16}},
      {type:'label',x:2,y:36,props:{scale:1,text:'CPU'}},
      {type:'gauge_ram',x:42,y:2,props:{radius:16}},
      {type:'label',x:42,y:36,props:{scale:1,text:'RAM'}},
      {type:'gauge_disk',x:82,y:2,props:{radius:16,diskIdx:0}},
      {type:'label',x:82,y:36,props:{scale:1,text:'Disk'}},
      {type:'clock_s',x:36,y:54,props:{scale:1}},
    ]},
  ];

  function loadTemplate(t) {
    placedWidgets = t.widgets.map(w => ({ id: Date.now()+Math.random(), ...w }));
    selectedWidget = -1;
    tool = 'move';
    renderWidgets();
    s.toast(`Vorlage "${t.name}" geladen`, 'ok');
  }
  function panelIcon(id) { return _pd[id]?.icon || 'circle'; }
  function panelLabel(id) { return _pd[id]?.label || id; }
  function panelCollapsible(id) { return _pd[id]?.c ?? true; }

  /* ═══ PERSISTENZ (localStorage Auto-Save) ═══ */
  function saveState() {
    try {
      saveCurrentScreen();
      const data = {
        screens: screens.map(sc => ({ ...sc, thumbnail: sc.thumbnail || '' })),
        activeScreen, rotation, rotationInterval, zoom, showGrid,
      };
      localStorage.setItem('pp-oled-state', JSON.stringify(data));
    } catch {}
  }

  function loadState() {
    try {
      const raw = localStorage.getItem('pp-oled-state');
      if (!raw) return;
      const data = JSON.parse(raw);
      if (data.screens?.length > 0) {
        screens = data.screens;
        _screenId = Math.max(0, ...screens.map(sc => sc.id)) + 1;
      }
      if (data.activeScreen !== undefined) activeScreen = data.activeScreen;
      if (data.rotation !== undefined) rotation = data.rotation;
      if (data.rotationInterval) rotationInterval = data.rotationInterval;
      if (data.zoom) zoom = data.zoom;
      if (data.showGrid !== undefined) showGrid = data.showGrid;
      // Aktiven Screen laden
      const sc = screens.find(sc => sc.id === activeScreen) || screens[0];
      if (sc) {
        placedWidgets = sc.widgets ? JSON.parse(JSON.stringify(sc.widgets)) : [];
        layers = sc.layers ? sc.layers.map(l => ({ ...l, pixels: new Uint8Array(l.pixels) })) : [{ id: 0, name: 'Hintergrund', pixels: new Uint8Array(W*H), visible: true }];
        activeLayer = layers[0]?.id || 0;
        _nid = Math.max(0, ...layers.map(l => l.id)) + 1;
      }
    } catch {}
  }

  let _saveTimer = 0;
  function autoSave() { clearTimeout(_saveTimer); _saveTimer = setTimeout(saveState, 1000); }

  /* ═══ PROFIL-SYSTEM ═══ */
  let profiles = $state(JSON.parse(localStorage.getItem('pp-oled-profiles') || '[]'));
  let activeProfile = $state('');

  function saveProfile(name) {
    if (!name) return;
    saveCurrentScreen();
    const profile = {
      name, created: new Date().toISOString(),
      screens: JSON.parse(JSON.stringify(screens)),
      rotation, rotationInterval,
    };
    profiles = [...profiles.filter(p => p.name !== name), profile];
    localStorage.setItem('pp-oled-profiles', JSON.stringify(profiles));
    activeProfile = name;
    s.toast(`Profil "${name}" gespeichert`, 'ok');
  }

  function loadProfile(p) {
    screens = p.screens.map((sc, i) => ({ ...sc, id: i }));
    _screenId = screens.length;
    rotation = p.rotation || false;
    rotationInterval = p.rotationInterval || 10;
    activeProfile = p.name;
    switchScreen(screens[0]?.id ?? 0);
    s.toast(`Profil "${p.name}" geladen`, 'ok');
  }

  function deleteProfile(name) {
    profiles = profiles.filter(p => p.name !== name);
    localStorage.setItem('pp-oled-profiles', JSON.stringify(profiles));
    if (activeProfile === name) activeProfile = '';
    s.toast(`Profil "${name}" gelöscht`, 'ok');
  }

  let showProfileSave = $state(false);
  let profileSaveName = $state('');

  /* ═══ WIDGET-VORSCHAU-LEISTE ═══ */
  const PREV_W = 48, PREV_H = 24;
  let previewCanvases = $state({}); // id -> canvas element
  const catOrder = ['zeit','cpu','ram','disk','net','sys','wetter','deko'];
  const catMeta = {zeit:['fa-clock','Zeit'],cpu:['fa-microchip','CPU'],ram:['fa-memory','RAM'],disk:['fa-hard-drive','Disk'],net:['fa-network-wired','Netz'],sys:['fa-server','Sys'],wetter:['fa-cloud-sun','Wetter'],deko:['fa-pen','Deko']};

  function renderWidgetPreview(canvas, wId) {
    if (!canvas) return;
    const wt = widgetTypes[wId];
    if (!wt) return;
    const ctx = canvas.getContext('2d');
    ctx.imageSmoothingEnabled = false;
    ctx.fillStyle = '#000';
    ctx.fillRect(0, 0, PREV_W, PREV_H);
    // Mini-Buffer rendern
    const buf = new Uint8Array(W * H);
    const fakeProps = { ...wt.props, invert: false, border: false, align: 'left' };
    if (wt.isShape) {
      wt.draw(buf, 2, 2, fakeProps);
    } else {
      const text = wt.getText(fakeProps);
      const sx = fakeProps.scaleX ?? fakeProps.scale ?? 1;
      const sy = fakeProps.scaleY ?? fakeProps.scale ?? 1;
      E.drawText(buf, text, 2, 2, sx, sy);
    }
    // Buffer skaliert auf Preview-Canvas zeichnen
    ctx.fillStyle = '#fff';
    const scaleX = PREV_W / W, scaleY = PREV_H / H;
    // Direkt die relevanten Pixel zeichnen (nur oberer linker Bereich)
    for (let y = 0; y < H; y++) {
      for (let x = 0; x < W; x++) {
        if (buf[y * W + x]) {
          ctx.fillRect(Math.floor(x * scaleX), Math.floor(y * scaleY),
                       Math.max(1, Math.ceil(scaleX)), Math.max(1, Math.ceil(scaleY)));
        }
      }
    }
  }

  function renderAllPreviews() {
    for (const [id, canvas] of Object.entries(previewCanvases)) {
      renderWidgetPreview(canvas, id);
    }
  }

  function onPreviewDragStart(e, wId) {
    e.dataTransfer.setData('application/x-widget-id', wId);
    e.dataTransfer.effectAllowed = 'copy';
  }

  function onCanvasDrop(e) {
    const wId = e.dataTransfer.getData('application/x-widget-id');
    if (!wId || !widgetTypes[wId]) return;
    e.preventDefault();
    const rect = canvasEl.getBoundingClientRect();
    const x = Math.max(0, Math.min(W-1, Math.floor((e.clientX - rect.left) / zoom)));
    const y = Math.max(0, Math.min(H-1, Math.floor((e.clientY - rect.top) / zoom)));
    const wt = widgetTypes[wId];
    placedWidgets = [...placedWidgets, {
      id: Date.now(),
      type: wId,
      x: snapGrid > 0 ? snapPos(x) : x,
      y: snapGrid > 0 ? snapPos(y) : y,
      props: { ...wt.props, invert: false, border: false, align: 'left' },
    }];
    selectedWidget = placedWidgets.length - 1;
    selectedWidgets = new Set([selectedWidget]);
    tool = 'move';
    renderWidgets();
    s.toast(`${wt.label} eingefügt`, 'ok');
  }

  function onCanvasDragOver(e) {
    if (e.dataTransfer.types.includes('application/x-widget-id')) e.preventDefault();
  }

  onMount(()=>{loadState();pushH();renderWidgets();startWidgetTimer();fetchWeather();setInterval(fetchWeather,300000);
    // Previews nach kurzer Verzögerung rendern (Canvas muss gemountet sein)
    setTimeout(renderAllPreviews, 200);
  });
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
    <div class="pr"><span>Snap</span>
      <select class="ti" style="flex:1;padding:3px 6px" onchange={(e)=>snapGrid=+e.target.value}>
        <option value="0" selected={snapGrid===0}>Aus</option>
        <option value="4" selected={snapGrid===4}>4px</option>
        <option value="8" selected={snapGrid===8}>8px</option>
        <option value="16" selected={snapGrid===16}>16px</option>
      </select>
    </div>
  {:else if id==='color'}
    <div class="cp"><div class="cs white" class:active={tool!=='eraser'} onclick={()=>{if(tool==='eraser')tool='pencil';}} title="Weiß"></div><div class="cs black" class:active={tool==='eraser'} onclick={()=>tool='eraser'} title="Schwarz"></div></div>
  {:else if id==='preview'}
    <div class="pv-box"><div class="pv-bezel"><canvas bind:this={previewEl} width={W} height={H} class="pv-canvas"></canvas></div></div>
    <button class="send-btn" onclick={sendToOled}><i class="fa-solid fa-paper-plane"></i> An OLED senden ({screens.length})</button>
    <button class="send-btn sec" onclick={loadFromOled}><i class="fa-solid fa-download"></i> Vom Backend laden</button>
    <div class="btn-row">
      <button class="send-btn half" onclick={exportScreens}><i class="fa-solid fa-file-export"></i> Export</button>
      <button class="send-btn half" onclick={importScreens}><i class="fa-solid fa-file-import"></i> Import</button>
    </div>
  {:else if id==='props'}
    {#if selectedWidget >= 0 && placedWidgets[selectedWidget]}
      {@const sw = placedWidgets[selectedWidget]}
      {@const wt = widgetTypes[sw.type]}
      <div class="rr"><span>Widget</span><span class="mono">{wt?.label}</span></div>
      <div class="rr"><span>Position</span><span class="mono">{sw.x}, {sw.y}</span></div>
      <div class="pr"><span>X</span><input type="range" min="0" max={W-1} value={sw.x} oninput={(e)=>{sw.x=+e.target.value;placedWidgets=[...placedWidgets];renderWidgets();}}><span class="pv">{sw.x}</span></div>
      <div class="pr"><span>Y</span><input type="range" min="0" max={H-1} value={sw.y} oninput={(e)=>{sw.y=+e.target.value;placedWidgets=[...placedWidgets];renderWidgets();}}><span class="pv">{sw.y}</span></div>
      {#if sw.props.scale !== undefined}
        <div class="pr"><span>Breite</span><input type="range" min="1" max="8" value={sw.props.scaleX||sw.props.scale} oninput={(e)=>updateWidgetProp(selectedWidget,'scaleX',+e.target.value)}><span class="pv">{sw.props.scaleX||sw.props.scale}×</span></div>
        <div class="pr"><span>Höhe</span><input type="range" min="1" max="8" value={sw.props.scaleY||sw.props.scale} oninput={(e)=>updateWidgetProp(selectedWidget,'scaleY',+e.target.value)}><span class="pv">{sw.props.scaleY||sw.props.scale}×</span></div>
      {/if}
      {#if sw.props.text !== undefined}
        <div class="pr"><span>Text</span><input type="text" class="ti" value={sw.props.text} oninput={(e)=>updateWidgetProp(selectedWidget,'text',e.target.value)}></div>
      {/if}
      {#if sw.props.prefix !== undefined}
        <div class="pr"><span>Präfix</span><input type="text" class="ti" value={sw.props.prefix} oninput={(e)=>updateWidgetProp(selectedWidget,'prefix',e.target.value)}></div>
      {/if}
      {#if sw.props.tsep !== undefined}
        <div class="pr"><span>1.000er</span><button class="tog" class:on={sw.props.tsep} onclick={()=>updateWidgetProp(selectedWidget,'tsep',!sw.props.tsep)}></button></div>
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
      {#if sw.props.radius !== undefined}
        <div class="pr"><span>Radius</span><input type="range" min="6" max="30" value={sw.props.radius} oninput={(e)=>updateWidgetProp(selectedWidget,'radius',+e.target.value)}><span class="pv">{sw.props.radius}px</span></div>
      {/if}
      <!-- Erweiterte Darstellung -->
      <div class="rr" style="margin-top:6px;color:var(--text-muted);font-size:var(--fs-xs)"><i class="fa-solid fa-wand-magic-sparkles" style="color:var(--accent)"></i> Darstellung</div>
      <div class="pr"><span>Invertiert</span><button class="tog" class:on={sw.props.invert} onclick={()=>updateWidgetProp(selectedWidget,'invert',!sw.props.invert)}></button></div>
      <div class="pr"><span>Rahmen</span><button class="tog" class:on={sw.props.border} onclick={()=>updateWidgetProp(selectedWidget,'border',!sw.props.border)}></button></div>
      {#if !wt?.isShape}
        <div class="pr"><span>Ausr.</span>
          <div class="align-btns">
            <button class="align-btn" class:active={!sw.props.align||sw.props.align==='left'} onclick={()=>updateWidgetProp(selectedWidget,'align','left')} title="Links"><i class="fa-solid fa-align-left"></i></button>
            <button class="align-btn" class:active={sw.props.align==='center'} onclick={()=>updateWidgetProp(selectedWidget,'align','center')} title="Mitte"><i class="fa-solid fa-align-center"></i></button>
            <button class="align-btn" class:active={sw.props.align==='right'} onclick={()=>updateWidgetProp(selectedWidget,'align','right')} title="Rechts"><i class="fa-solid fa-align-right"></i></button>
          </div>
        </div>
        {#if sw.props.align && sw.props.align !== 'left'}
          <div class="pr"><span>Box-B.</span><input type="range" min="0" max="128" value={sw.props.boxW||0} oninput={(e)=>updateWidgetProp(selectedWidget,'boxW',+e.target.value)}><span class="pv">{sw.props.boxW||0}</span></div>
        {/if}
      {/if}
      <div class="prop-actions">
        <button class="ab" style="flex:1;height:28px" onclick={()=>{const src=placedWidgets[selectedWidget];placedWidgets=[...placedWidgets,{...JSON.parse(JSON.stringify(src)),id:Date.now(),x:src.x+4,y:src.y+4}];selectedWidget=placedWidgets.length-1;renderWidgets();}} title="Duplizieren"><i class="fa-solid fa-copy"></i></button>
        <button class="ab del" style="flex:1;height:28px" onclick={()=>removeWidget(selectedWidget)} title="Entfernen"><i class="fa-solid fa-trash-can"></i></button>
      </div>
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
  {:else if id==='templates'}
    {#each templates as t}
      <button class="wc-btn" onclick={() => loadTemplate(t)}><i class="fa-solid fa-download"></i> <span class="wc-name">{t.name}</span><span class="wc-size">{t.widgets.length} Widgets</span></button>
    {/each}
  {:else if id==='clock'}
    {@const cs = s.oled?.clock_settings || {}}
    <div class="pr"><span>Blinken</span><button class="tog" class:on={cs.blink!==false} onclick={()=>s.setClockSettings({blink:!(cs.blink!==false)})}></button></div>
    <div class="pr"><span>Sekunden</span><button class="tog" class:on={cs.seconds} onclick={()=>s.setClockSettings({seconds:!cs.seconds})}></button></div>
    <div class="pr"><span>Zehntel</span><button class="tog" class:on={cs.tenths} onclick={()=>s.setClockSettings({tenths:!cs.tenths})}></button></div>
    <div class="pr"><span>Datum</span><button class="tog" class:on={cs.date!==false} onclick={()=>s.setClockSettings({date:!(cs.date!==false)})}></button></div>
    <div class="pr"><span>Wochentag</span><button class="tog" class:on={cs.weekday!==false} onclick={()=>s.setClockSettings({weekday:!(cs.weekday!==false)})}></button></div>
    <div class="pr"><span>24h</span><button class="tog" class:on={cs.format_24h!==false} onclick={()=>s.setClockSettings({format_24h:!(cs.format_24h!==false)})}></button></div>
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
      <!-- Profil-Leiste -->
      <div class="profile-bar">
        <span class="pb-label"><i class="fa-solid fa-bookmark"></i></span>
        <div class="pb-chips">
          {#each profiles as p}
            <button class="pb-chip" class:active={activeProfile===p.name} onclick={()=>loadProfile(p)} title="Profil laden: {p.name}">
              {p.name}
              <span class="pb-del" onclick={(e)=>{e.stopPropagation();deleteProfile(p.name);}}><i class="fa-solid fa-xmark"></i></span>
            </button>
          {/each}
          {#if profiles.length === 0}<span class="pb-empty">Keine Profile</span>{/if}
        </div>
        {#if showProfileSave}
          <input class="pb-input" type="text" placeholder="Name..." bind:value={profileSaveName} onkeydown={(e)=>{if(e.key==='Enter'&&profileSaveName){saveProfile(profileSaveName);showProfileSave=false;profileSaveName='';}if(e.key==='Escape')showProfileSave=false;}} />
        {/if}
        <button class="pb-save" onclick={()=>{if(showProfileSave&&profileSaveName){saveProfile(profileSaveName);showProfileSave=false;profileSaveName='';}else{showProfileSave=!showProfileSave;profileSaveName=activeProfile||'';}}} title="Aktuelles Layout als Profil speichern"><i class="fa-solid fa-floppy-disk"></i></button>
      </div>
      <!-- Widget-Vorschau-Leiste -->
      <div class="widget-strip">
        {#each catOrder as cat}
          {@const items = widgetList.filter(w => w.cat === cat)}
          {#if items.length > 0}
            <div class="ws-group">
              <span class="ws-cat" title={catMeta[cat]?.[1]||cat}><i class="fa-solid {catMeta[cat]?.[0]||'fa-circle'}"></i></span>
              {#each items as w}
                <div class="ws-item" draggable="true" ondragstart={(e)=>onPreviewDragStart(e,w.id)} onclick={()=>placeWidget(w)} title="{w.label} ({w.w}×{w.h}) — Klick oder Drag">
                  <canvas bind:this={previewCanvases[w.id]} width={PREV_W} height={PREV_H} class="ws-canvas"></canvas>
                  <span class="ws-label">{w.label}</span>
                </div>
              {/each}
            </div>
          {/if}
        {/each}
      </div>
      <div class="canvas-scroll"><canvas bind:this={canvasEl} width={W*zoom} height={H*zoom} onpointerdown={onDown} onpointermove={onMove} onpointerup={onUp} oncontextmenu={onContext} ondrop={onCanvasDrop} ondragover={onCanvasDragOver} style="width:{W*zoom}px;height:{H*zoom}px"></canvas></div>
      {#if ctxMenu}
        <div class="ctx-menu" style="left:{ctxMenu.x}px;top:{ctxMenu.y}px">
          <button class="ctx-item" onclick={()=>ctxAction('dup')}><i class="fa-solid fa-copy"></i> Duplizieren</button>
          <button class="ctx-item" onclick={()=>ctxAction('front')}><i class="fa-solid fa-arrow-up"></i> Nach vorne</button>
          <button class="ctx-item" onclick={()=>ctxAction('back')}><i class="fa-solid fa-arrow-down"></i> Nach hinten</button>
          <div class="ctx-sep"></div>
          <button class="ctx-item ctx-del" onclick={()=>ctxAction('del')}><i class="fa-solid fa-trash-can"></i> Löschen</button>
        </div>
      {/if}
      <!-- Screen-Galerie unten -->
      <div class="screen-gallery">
        <div class="sg-strip">
          {#each screens as sc, i}
            <div class="sg-item" class:active={sc.id===activeScreen} class:drag-over={scDragOver===i}
              draggable="true" onclick={()=>switchScreen(sc.id)}
              ondragstart={(e)=>scDragStart(e,i)} ondragover={(e)=>scDragOverFn(e,i)}
              ondrop={(e)=>scDrop(e,i)} ondragend={scDragEnd}>
              <div class="sg-thumb">
                {#if sc.thumbnail}<img src={sc.thumbnail} alt={sc.name} />{:else}<div class="sg-empty"></div>{/if}
              </div>
              <span class="sg-name" contenteditable="false"
                ondblclick={(e)=>{e.stopPropagation();e.target.contentEditable='true';e.target.focus();}}
                onblur={(e)=>{e.target.contentEditable='false';const idx=screens.findIndex(s2=>s2.id===sc.id);if(idx>=0){screens[idx].name=e.target.textContent;screens=[...screens];}}}
                onkeydown={(e)=>{if(e.key==='Enter'){e.preventDefault();e.target.blur();}}}>{sc.name}</span>
              {#if screens.length > 1}
                <button class="sg-del" onclick={(e)=>{e.stopPropagation();removeScreen(sc.id);}}><i class="fa-solid fa-xmark"></i></button>
              {/if}
            </div>
          {/each}
          <button class="sg-add" onclick={addScreen}><i class="fa-solid fa-plus"></i></button>
          <button class="sg-dup" onclick={duplicateScreen} title="Aktiven Screen duplizieren"><i class="fa-solid fa-copy"></i></button>
        </div>
        <div class="sg-controls">
          <div class="sg-ctrl"><span>Rotation</span><button class="tog" class:on={rotation} onclick={()=>rotation=!rotation}></button></div>
          {#if rotation}
            <div class="sg-ctrl"><span>Intervall</span><input type="range" min="3" max="60" value={rotationInterval} oninput={(e)=>rotationInterval=+e.target.value}><span class="pv">{rotationInterval}s</span></div>
          {/if}
        </div>
      </div>
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

  /* Widget-Vorschau-Leiste */
  .widget-strip {
    display: flex; gap: 2px; overflow-x: auto; overflow-y: hidden;
    padding: 6px 8px; border-bottom: 1px solid var(--border);
    background: var(--bg-base); flex-shrink: 0; min-height: 62px;
    scrollbar-width: thin;
  }
  .ws-group {
    display: flex; align-items: center; gap: 3px;
    padding-right: 6px; border-right: 1px solid var(--border);
    flex-shrink: 0;
  }
  .ws-group:last-child { border-right: none; padding-right: 0; }
  .ws-cat {
    writing-mode: vertical-lr; text-orientation: mixed;
    font-size: 10px; color: var(--accent); padding: 0 2px;
    flex-shrink: 0; display: flex; align-items: center;
  }
  .ws-item {
    display: flex; flex-direction: column; align-items: center; gap: 2px;
    cursor: grab; flex-shrink: 0; padding: 2px;
    border-radius: var(--radius-sm); border: 1px solid transparent;
    transition: border-color 120ms;
  }
  .ws-item:hover { border-color: var(--accent); }
  .ws-item:active { cursor: grabbing; }
  .ws-canvas {
    width: 48px; height: 24px;
    image-rendering: pixelated;
    border-radius: 2px;
    border: 1px solid rgba(255,255,255,0.08);
    background: #000;
    pointer-events: none;
  }
  .ws-label {
    font: 500 9px var(--font); color: var(--text-muted);
    max-width: 52px; overflow: hidden; text-overflow: ellipsis;
    white-space: nowrap; text-align: center;
  }

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
  .ti { flex: 1; min-width: 0; padding: 5px 8px; border: 1px solid var(--border); background: var(--bg-elevated); color: var(--text-primary); border-radius: var(--radius-sm); font: 500 var(--fs-sm) var(--mono); box-sizing: border-box; }
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
  .send-btn.sec { margin-top: 4px; border-color: var(--green); color: var(--green); background: rgba(0,232,138,0.06); }
  .send-btn.sec:hover { background: var(--green); color: #000; }
  .send-btn.half { flex: 1; }
  .btn-row { display: flex; gap: 4px; margin-top: 4px; }

  /* Alignment Buttons */
  .align-btns { display: flex; gap: 2px; }
  .align-btn { width: 28px; height: 24px; border-radius: var(--radius-sm); border: 1px solid var(--border); background: var(--bg-surface); color: var(--text-muted); cursor: pointer; font-size: 11px; display: flex; align-items: center; justify-content: center; }
  .align-btn:hover { border-color: var(--accent); color: var(--accent); }
  .align-btn.active { background: rgba(0,180,255,0.1); border-color: var(--accent); color: var(--accent); }

  /* Prop Actions */
  .prop-actions { display: flex; gap: 4px; margin-top: 6px; }
  .ab.del { border-color: var(--red); color: var(--red); }
  .ab.del:hover { background: var(--red); color: #fff; }

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

  /* Screen-Galerie */
  .screen-gallery { flex-shrink: 0; border-top: 1px solid var(--border); background: var(--bg-base); padding: 8px; }
  .sg-strip { display: flex; gap: 8px; overflow-x: auto; align-items: flex-end; margin-bottom: 6px; }
  .sg-item { flex-shrink: 0; cursor: pointer; border: 2px solid var(--border); border-radius: var(--radius-sm); padding: 3px; position: relative; transition: border-color 150ms; }
  .sg-item.active { border-color: var(--accent); }
  .sg-item.drag-over { border-color: var(--green); border-style: dashed; }
  .sg-item:hover { border-color: var(--text-muted); }
  .sg-thumb { width: 128px; height: 64px; background: #000; border-radius: 2px; overflow: hidden; }
  .sg-thumb img { width: 128px; height: 64px; image-rendering: pixelated; display: block; }
  .sg-empty { width: 100%; height: 100%; }
  .sg-name { display: block; font: 500 var(--fs-xs) var(--font); color: var(--text-muted); text-align: center; margin-top: 2px; max-width: 128px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .sg-del { position: absolute; top: -4px; right: -4px; width: 16px; height: 16px; border-radius: 50%; border: none; background: var(--bg-elevated); color: var(--red); cursor: pointer; font-size: 8px; display: none; align-items: center; justify-content: center; }
  .sg-item:hover .sg-del { display: flex; }
  .sg-add, .sg-dup { width: 128px; height: 64px; flex-shrink: 0; border-radius: var(--radius-sm); border: 2px dashed var(--border); background: none; color: var(--text-muted); cursor: pointer; font-size: var(--fs-base); display: flex; align-items: center; justify-content: center; }
  .sg-add:hover, .sg-dup:hover { border-color: var(--accent); color: var(--accent); }
  .sg-controls { display: flex; gap: 12px; align-items: center; }
  .sg-ctrl { display: flex; align-items: center; gap: 6px; font: 500 var(--fs-xs) var(--font); color: var(--text-muted); }
  .sg-ctrl input { width: 80px; }

  /* Profil-Leiste */
  .profile-bar {
    display: flex; align-items: center; gap: 6px;
    padding: 6px 12px; border-bottom: 1px solid var(--border);
    background: var(--bg-surface); flex-shrink: 0; min-height: 36px;
  }
  .pb-label { color: var(--accent); font-size: var(--fs-sm); flex-shrink: 0; }
  .pb-chips { display: flex; gap: 4px; overflow-x: auto; flex: 1; }
  .pb-chip {
    display: flex; align-items: center; gap: 4px;
    padding: 3px 10px; border-radius: 12px;
    border: 1px solid var(--border); background: var(--bg-elevated);
    color: var(--text-secondary); font: 500 var(--fs-xs) var(--font);
    cursor: pointer; white-space: nowrap; flex-shrink: 0;
  }
  .pb-chip:hover { border-color: var(--accent); color: var(--accent); }
  .pb-chip.active { background: var(--accent-dim); border-color: var(--accent); color: var(--accent); }
  .pb-del { font-size: 9px; color: var(--text-muted); cursor: pointer; margin-left: 2px; }
  .pb-del:hover { color: var(--red); }
  .pb-empty { font: 500 var(--fs-xs) var(--font); color: var(--text-muted); }
  .pb-input {
    width: 120px; padding: 3px 8px; border: 1px solid var(--accent);
    background: var(--bg-elevated); color: var(--text-primary);
    border-radius: 12px; font: 500 var(--fs-xs) var(--mono); flex-shrink: 0;
  }
  .pb-save {
    width: 28px; height: 28px; border-radius: 50%;
    border: 1px solid var(--border); background: var(--bg-elevated);
    color: var(--text-muted); cursor: pointer; font-size: var(--fs-xs);
    display: flex; align-items: center; justify-content: center; flex-shrink: 0;
  }
  .pb-save:hover { border-color: var(--accent); color: var(--accent); }

  /* Kontextmenue */
  .ctx-menu {
    position: fixed; z-index: 100;
    background: var(--bg-elevated); border: 1px solid var(--border);
    border-radius: var(--radius); box-shadow: 0 8px 24px rgba(0,0,0,0.4);
    padding: 4px; min-width: 160px;
  }
  .ctx-item {
    display: flex; align-items: center; gap: 8px; width: 100%;
    padding: 7px 12px; border: none; background: none; border-radius: var(--radius-sm);
    color: var(--text-secondary); font: 500 var(--fs-sm) var(--font);
    cursor: pointer; text-align: left;
  }
  .ctx-item:hover { background: rgba(0,180,255,0.1); color: var(--accent); }
  .ctx-item i { width: 16px; text-align: center; font-size: var(--fs-xs); }
  .ctx-del:hover { background: rgba(255,60,60,0.1); color: var(--red); }
  .ctx-sep { height: 1px; background: var(--border); margin: 3px 8px; }

  @media (max-width: 900px) { .side-panel { width: 200px; } }
</style>
