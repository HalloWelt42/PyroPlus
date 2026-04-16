<script>
  import { onMount, onDestroy } from 'svelte';
  import PanelWrapper from './oled/PanelWrapper.svelte';
  import * as E from './oled/engine.js';
  import { TABS, getSource, getModesForType, getSourcesForTab, defaultOpts, createWidget, HISTORY_KEYS } from './oled/catalog.js';
  import { renderWidget as renderWidgetNew, getWidgetSize } from './oled/widgetRenderer.js';
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
  let showGrid = $state(true), zoom = $state(6), widgetZoom = $state(2);
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
  let weatherDaily = $state([]);
  let weatherHourly = $state([]);
  let weatherLocation = $state(JSON.parse(localStorage.getItem('pp-weather-loc') || 'null') || { name: 'Zeitz', lat: 51.05, lon: 12.13 });
  let locationSearch = $state('');
  let locationResults = $state([]);
  let showLocationSearch = $state(!weatherLocation.name);
  let _weatherFetchTime = 0;

  function _wmoDE(code) {
    if (code==null) return '--';
    if (code===0) return 'Klar';
    if (code<=3) return 'Bewölkt';
    if (code<=48) return 'Nebel';
    if (code<=55) return 'Nieseln';
    if (code<=57) return 'Gefrierender Niesel';
    if (code<=65) return 'Regen';
    if (code<=67) return 'Gefrierender Regen';
    if (code<=75) return 'Schneefall';
    if (code<=77) return 'Schneegriesel';
    if (code<=82) return 'Regenschauer';
    if (code<=86) return 'Schneeschauer';
    if (code<=95) return 'Gewitter';
    return 'Gewitter mit Hagel';
  }

  async function fetchWeather() {
    if (!weatherLocation) return;
    if (Date.now() - _weatherFetchTime < 600000) return; // 10 Min Cache
    _weatherFetchTime = Date.now();
    try {
      const params = [
        'current=temperature_2m,relative_humidity_2m,apparent_temperature,wind_speed_10m,wind_direction_10m,wind_gusts_10m,weather_code,cloud_cover,surface_pressure,pressure_msl,precipitation,is_day',
        'hourly=temperature_2m,relative_humidity_2m,apparent_temperature,precipitation_probability,weather_code,wind_speed_10m,uv_index,cloud_cover',
        'daily=weather_code,temperature_2m_max,temperature_2m_min,apparent_temperature_max,apparent_temperature_min,precipitation_sum,precipitation_probability_max,sunrise,sunset,daylight_duration,uv_index_max,wind_speed_10m_max,wind_gusts_10m_max,wind_direction_10m_dominant',
        'forecast_days=7',
        'timezone=auto',
      ].join('&');
      const r = await fetch(`https://api.open-meteo.com/v1/forecast?latitude=${weatherLocation.lat}&longitude=${weatherLocation.lon}&${params}`);
      const d = await r.json();
      const c = d.current || {};
      weather = {
        ...c,
        location: weatherLocation.name,
        condition_text: _wmoDE(c.weather_code),
        sunrise: '', sunset: '',
      };
      // Daily
      const dd = d.daily || {};
      const days = ['So','Mo','Di','Mi','Do','Fr','Sa'];
      weatherDaily = (dd.time || []).map((t, i) => {
        const dt = new Date(t + 'T12:00');
        return {
          date: t, tag: days[dt.getDay()],
          max: dd.temperature_2m_max?.[i], min: dd.temperature_2m_min?.[i],
          code: dd.weather_code?.[i], zustand: _wmoDE(dd.weather_code?.[i]),
          regen: dd.precipitation_sum?.[i], regenProb: dd.precipitation_probability_max?.[i],
          sunrise: (dd.sunrise?.[i]||'').slice(-5), sunset: (dd.sunset?.[i]||'').slice(-5),
          tageslicht: Math.round((dd.daylight_duration?.[i]||0)/3600*10)/10,
          uvMax: dd.uv_index_max?.[i], windMax: dd.wind_speed_10m_max?.[i],
          boeMax: dd.wind_gusts_10m_max?.[i], windDir: dd.wind_direction_10m_dominant?.[i],
          gefMax: dd.apparent_temperature_max?.[i], gefMin: dd.apparent_temperature_min?.[i],
        };
      });
      if (weatherDaily.length > 0) {
        weather.sunrise = weatherDaily[0].sunrise;
        weather.sunset = weatherDaily[0].sunset;
      }
      // Hourly (naechste 24h)
      const hh = d.hourly || {};
      const nowH = new Date().getHours();
      weatherHourly = (hh.time || []).slice(nowH, nowH + 24).map((t, i) => ({
        time: t, stunde: (t||'').slice(-5,-3)+'h',
        temp: hh.temperature_2m?.[nowH+i], feuchte: hh.relative_humidity_2m?.[nowH+i],
        gefuehlt: hh.apparent_temperature?.[nowH+i], regenProb: hh.precipitation_probability?.[nowH+i],
        code: hh.weather_code?.[nowH+i], zustand: _wmoDE(hh.weather_code?.[nowH+i]),
        wind: hh.wind_speed_10m?.[nowH+i], uv: hh.uv_index?.[nowH+i],
        wolken: hh.cloud_cover?.[nowH+i],
      }));
    } catch(e) { console.error('Wetter-Fetch:', e); }
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
    /* ─── Layout ─── */
    label:     { cat:'layout', label:'Textfeld',       w:48, h:7, props:{ scale:1, text:'Text' },
                 getText: (p) => p.text || 'Text' },
    marquee:   { cat:'layout', label:'Laufschrift',    w:128, h:7, props:{ scale:1, text:'Hallo Welt!' },
                 getText: (p) => p.text || 'Laufschrift' },
    line_h:    { cat:'layout', label:'Linie ─',        w:60, h:1, props:{ width:60 }, isShape: true,
                 draw: (px,x,y,p) => { for(let i=0;i<(p.width||60);i++) if(x+i>=0&&x+i<W) px[y*W+x+i]=1; }},
    line_v:    { cat:'layout', label:'Linie │',        w:1, h:20, props:{ height:20 }, isShape: true,
                 draw: (px,x,y,p) => { for(let i=0;i<(p.height||20);i++) if(y+i>=0&&y+i<H) px[(y+i)*W+x]=1; }},
    rect_o:    { cat:'layout', label:'Rahmen □',       w:40, h:20, props:{ width:40, height:20 }, isShape: true,
                 draw: (px,x,y,p) => E.drawRect(x,y,x+(p.width||40)-1,y+(p.height||20)-1,(px2,py)=>{if(px2>=0&&px2<W&&py>=0&&py<H)px[py*W+px2]=1;},false) },
    rect_f:    { cat:'layout', label:'Block ■',        w:40, h:20, props:{ width:40, height:20 }, isShape: true,
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
    section:   { cat:'layout', label:'── Header ──',   w:60, h:7, props:{ width:60, text:'CPU' }, isShape: true,
                 draw: (px,x,y,p) => E.drawSectionHeader(px, p.text||'Label', x, y, p.width||60) },
  };
  const widgetList = Object.entries(widgetTypes).map(([id,v])=>({id,...v}));

  /* ═══ HISTORY für Sparklines ═══ */
  const _hist = { cpu: [], temp: [], ram: [], fan_speed: [], net_rx: [], net_tx: [] };
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

  /* Getter fuer Widget-Optionen (opts bei neuen, props bei alten Widgets) */
  function wp(w) { return w.opts || w.props || {}; }

  function updateWidgetProp(idx, key, val) {
    const w = placedWidgets[idx];
    if (w.opts) w.opts[key] = val;
    else if (w.props) w.props[key] = val;
    placedWidgets = [...placedWidgets];
    renderWidgets();
  }

  /* ═══ WIDGET-EDITOR STATE (neues System) ═══ */
  let activeTab = $state('cpu');
  let configSource = $state(null);
  let configDisplay = $state(null);
  let configPreviewEl = $state(null);

  // Widget-Konfigurator: Eigene Bounding-Box + Optionen + Simulation
  let cfgBoxW = $state(60);   // Bounding-Box Breite
  let cfgBoxH = $state(16);   // Bounding-Box Hoehe
  let cfgOpts = $state({});   // Aktuelle Optionen
  let cfgSimVal = $state(null); // Simulierter Wert (null = Live)
  let cfgName = $state('');

  function selectSource(src) {
    configSource = src;
    const modes = getModesForType(src.type);
    configDisplay = modes[0]?.id || 'zahl';
    cfgOpts = { ...defaultOpts(configDisplay) };
    cfgName = src.label;
    cfgSimVal = null;
    _autoBoxSize();
  }

  function setConfigDisplay(mode) {
    configDisplay = mode;
    cfgOpts = { ...defaultOpts(mode) };
    _autoBoxSize();
  }

  function _autoBoxSize() {
    // Box automatisch an Display-Modus anpassen
    const o = cfgOpts;
    if (o.width) cfgBoxW = Math.min(128, o.width + 4);
    else if (o.radius) cfgBoxW = Math.min(128, o.radius * 2 + 4);
    else cfgBoxW = Math.min(128, Math.max(20, (cfgName?.length || 4) * 6 * (o.scaleX || 1) + 6));
    if (o.height) cfgBoxH = Math.min(64, o.height + 4);
    else if (o.radius) cfgBoxH = Math.min(64, o.radius + 6);
    else cfgBoxH = Math.min(64, 7 * (o.scaleY || o.scaleX || 1) + 4);
  }

  function renderConfigPreview() {
    if (!configPreviewEl || !configSource || !configDisplay) return;
    const bw = cfgBoxW, bh = cfgBoxH;
    configPreviewEl.width = bw;
    configPreviewEl.height = bh;
    const ctx = configPreviewEl.getContext('2d');
    ctx.imageSmoothingEnabled = false;
    // Schwarzer Hintergrund
    ctx.fillStyle = '#000';
    ctx.fillRect(0, 0, bw, bh);
    // Widget rendern in Buffer
    const buf = new Uint8Array(W * H);
    const tmpWidget = { source: configSource.id, display: configDisplay, x: 2, y: 2, opts: { ...cfgOpts } };
    // Simulierter Wert
    const simStats = cfgSimVal !== null ? _buildSimStats() : s.stats;
    renderWidgetNew(buf, tmpWidget, simStats, weather, s.stats?.history || _hist);
    // Pixel in Box-Bereich zeichnen
    ctx.fillStyle = '#fff';
    for (let y = 0; y < bh && y < H; y++)
      for (let x = 0; x < bw && x < W; x++)
        if (buf[y * W + x]) ctx.fillRect(x, y, 1, 1);
    // Box-Rand
    ctx.strokeStyle = '#444';
    ctx.lineWidth = 1;
    ctx.strokeRect(0.5, 0.5, bw - 1, bh - 1);
  }

  function _buildSimStats() {
    const base = JSON.parse(JSON.stringify(s.stats || {}));
    const v = cfgSimVal;
    const src = configSource?.id || '';
    const di = configSource?._diskIdx ?? 0;
    const totalRam = base.ram?.total_gb || 16;
    const totalDisk = base.disks?.[di]?.total_gb || 500;

    // CPU
    if (!base.cpu) base.cpu = {};
    if (src.startsWith('cpu.') || src === 'cpu.temp_pct') {
      base.cpu.temp = v; base.cpu.percent = v;
      base.cpu.temp_min = Math.round(v * 0.7);
      base.cpu.temp_max = Math.round(v * 1.2);
      base.cpu.cores = base.cpu.cores || 4;
    }
    // RAM
    if (!base.ram) base.ram = {};
    if (src.startsWith('ram.')) {
      base.ram.percent = v;
      base.ram.used_gb = v / 100 * totalRam;
      base.ram.total_gb = totalRam;
      base.ram.available_gb = totalRam - v / 100 * totalRam;
    }
    // Disk
    if (!base.disks) base.disks = [];
    while (base.disks.length <= di) base.disks.push({ label: `Disk ${base.disks.length}`, mount: '/', total_gb: 500 });
    if (src.startsWith('disk.')) {
      base.disks[di].percent = v;
      base.disks[di].used_gb = v / 100 * totalDisk;
      base.disks[di].available_gb = totalDisk - v / 100 * totalDisk;
      base.disks[di].total_gb = totalDisk;
    }
    // Fan
    if (!base.fan) base.fan = {};
    if (src.startsWith('fan.')) {
      base.fan.rpm = Math.round(v * 40);
      base.fan.current_duty = v;
      base.fan.level_name = v > 66 ? 'Voll' : v > 33 ? 'Mittel' : v > 0 ? 'Leise' : 'Aus';
      base.fan.case_on = v > 50;
    }
    // Net
    if (!base.network) base.network = {};
    if (src.startsWith('net.')) {
      base.network.rx_bytes_sec = Math.round(v * 10240);
      base.network.tx_bytes_sec = Math.round(v * 5120);
    }
    // Uptime
    if (!base.uptime) base.uptime = {};
    if (src.startsWith('zeit.uptime')) {
      const sec = Math.round(v * 864);
      const h = Math.floor(sec / 3600); const m = Math.floor((sec % 3600) / 60);
      base.uptime.seconds = sec;
      base.uptime.formatted = h > 24 ? `${Math.floor(h/24)}d ${h%24}h ${m}m` : `${h}h ${m}m`;
    }
    return base;
  }

  $effect(() => { if (configSource && configDisplay) { cfgBoxW; cfgBoxH; cfgOpts; cfgSimVal; setTimeout(renderConfigPreview, 30); } });

  function placeNewWidget(sourceId, displayMode, x = 4, y = 4) {
    const w = createWidget(sourceId, displayMode, x, y);
    w.opts = { ...w.opts, ...cfgOpts };
    w.name = cfgName || w.name;
    w.opts._boxW = cfgBoxW;
    w.opts._boxH = cfgBoxH;
    placedWidgets = [...placedWidgets, w];
    selectedWidget = placedWidgets.length - 1;
    tool = 'move';
    renderWidgets();
    s.toast(`${w.name} hinzugefuegt`, 'ok');
  }

  /* ═══ WIDGET-VORLAGEN (gespeicherte Widgets zum spaeter Einbauen) ═══ */
  let widgetPresets = $state(JSON.parse(localStorage.getItem('pp-widget-presets') || '[]'));

  function saveAsWidgetPreset() {
    if (!configSource) return;
    const preset = {
      id: Date.now() + Math.random(),
      source: configSource.id,
      display: configDisplay,
      name: cfgName || configSource.label,
      opts: { ...cfgOpts },
      boxW: cfgBoxW,
      boxH: cfgBoxH,
    };
    widgetPresets = [...widgetPresets, preset];
    localStorage.setItem('pp-widget-presets', JSON.stringify(widgetPresets));
    s.toast(`Widget "${preset.name}" gespeichert`, 'ok');
  }

  function deleteWidgetPreset(id) {
    widgetPresets = widgetPresets.filter(p => p.id !== id);
    localStorage.setItem('pp-widget-presets', JSON.stringify(widgetPresets));
  }

  /* Preset-Canvas rendern (Svelte Action) */
  function renderPresetCanvas(canvas, preset) {
    function draw() {
      if (!canvas) return;
      const bw = preset.boxW || 40, bh = preset.boxH || 12;
      canvas.width = bw; canvas.height = bh;
      const ctx = canvas.getContext('2d');
      ctx.imageSmoothingEnabled = false;
      ctx.fillStyle = '#000'; ctx.fillRect(0, 0, bw, bh);
      const buf = new Uint8Array(W * H);
      const w = { source: preset.source, display: preset.display, x: 1, y: 1, opts: preset.opts || {} };
      renderWidgetNew(buf, w, s.stats, weather, s.stats?.history || _hist);
      ctx.fillStyle = '#fff';
      for (let y = 0; y < bh && y < H; y++)
        for (let x = 0; x < bw && x < W; x++)
          if (buf[y * W + x]) ctx.fillRect(x, y, 1, 1);
    }
    draw();
    const iv = setInterval(draw, 1000);
    return { destroy() { clearInterval(iv); } };
  }

  function placePresetOnScreen(preset) {
    const w = {
      id: Date.now() + Math.random(),
      source: preset.source,
      display: preset.display,
      name: preset.name,
      x: 4, y: 4,
      opts: { ...preset.opts, _boxW: preset.boxW, _boxH: preset.boxH },
    };
    placedWidgets = [...placedWidgets, w];
    selectedWidget = placedWidgets.length - 1;
    tool = 'move';
    renderWidgets();
    s.toast(`"${preset.name}" platziert`, 'ok');
  }

  /* Alle Widgets in Layer 0 rendern — neues Format (source+display+opts) */
  function renderWidgets() {
    const px = layers[0].pixels;
    px.fill(0);
    for (const w of placedWidgets) {
      if (w.source) {
        // Neues Format
        renderWidgetNew(px, w, s.stats, weather, s.stats?.history || _hist);
      } else if (w.type) {
        // Altes Format (Abwaertskompatibilitaet)
        const wt = widgetTypes[w.type];
        if (!wt) continue;
        if (wt.isShape) {
          wt.draw(px, w.x, w.y, wp(w));
        } else {
          const text = wt.getText(wp(w));
          const sx = wp(w).scaleX ?? wp(w).scale ?? 1;
          const sy = wp(w).scaleY ?? wp(w).scale ?? 1;
          E.drawText(px, text, w.x, w.y, sx, sy);
        }
      }
    }
    layers = [...layers];
    render();
    autoSave();
  }

  /* Widget-Rendering 5fps, History + Previews 1x/s */
  let _renderTimer, _statsTimer;
  function startWidgetTimer() {
    // Rendering 5fps (200ms)
    _renderTimer = setInterval(() => {
      if (placedWidgets.length > 0) renderWidgets();
    }, 200);
    // History + Vorschau-Leiste nur 1x/s
    _statsTimer = setInterval(() => {
      _hist.cpu.push(s.stats?.cpu?.percent || 0);
      _hist.temp.push(s.stats?.cpu?.temp || 0);
      _hist.ram.push(s.stats?.ram?.percent || 0);
      if (_hist.cpu.length > HIST_LEN) _hist.cpu.shift();
      if (_hist.temp.length > HIST_LEN) _hist.temp.shift();
      if (_hist.ram.length > HIST_LEN) _hist.ram.shift();
      renderConfigPreview();
    }, 1000);
  }
  function stopWidgetTimer() { clearInterval(_renderTimer); clearInterval(_statsTimer); }

  /* ═══ CANVAS ═══ */
  let canvasEl = $state(null), previewEl = $state(null);
  function render() {
    const comp = E.composite(layers);
    if (canvasEl) {
      const z = editorMode === 'widget' ? widgetZoom : zoom;
      E.renderCanvas(canvasEl.getContext('2d'), comp, z, editorMode === 'raster' && showGrid);
      const ctx = canvasEl.getContext('2d');
      // Multi-Select Rahmen
      const selSet = selectedWidgets.size > 0 ? selectedWidgets : (selectedWidget >= 0 ? new Set([selectedWidget]) : new Set());
      for (const idx of selSet) {
        const w = placedWidgets[idx];
        if (!w) continue;
        const sz = w.source ? getWidgetSize(w) : _oldWidgetSize(w);
        ctx.strokeStyle = idx === selectedWidget ? 'rgba(0,180,255,0.7)' : 'rgba(0,232,138,0.5)';
        ctx.lineWidth = 1; ctx.setLineDash([4, 2]);
        ctx.strokeRect(w.x * z - 1, w.y * z - 1, sz.w * z + 2, sz.h * z + 2);
        ctx.setLineDash([]);
      }
    }
    if (previewEl) E.renderPreview(previewEl.getContext('2d'), comp);
  }

  /* ═══ MAUS ═══ */
  let drawing=$state(false), sx=0, sy=0, lx=-1, ly=-1, snap=null, mvStart=null;
  function m2p(e) { const r=canvasEl.getBoundingClientRect(); return [Math.max(0,Math.min(W-1,Math.floor((e.clientX-r.left)/zoom))),Math.max(0,Math.min(H-1,Math.floor((e.clientY-r.top)/zoom)))]; }

  /* Alte Widget-Groesse berechnen (Abwaertskompatibilitaet) */
  function _oldWidgetSize(w) {
    const wt = widgetTypes[w.type];
    if (!wt) return { w: 30, h: 7 };
    const p = wp(w);
    const ww = wt.isShape ? (p.width || wt.w) : wt.w * (p.scaleX ?? p.scale ?? 1);
    const wh = wt.isShape ? (p.height || wt.h) : wt.h * (p.scaleY ?? p.scale ?? 1);
    return { w: ww, h: wh };
  }

  function hitTestWidget(x, y) {
    for (let i = placedWidgets.length - 1; i >= 0; i--) {
      const w = placedWidgets[i];
      const sz = w.source ? getWidgetSize(w) : _oldWidgetSize(w);
      const ww = sz.w, wh = sz.h;
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
        widgets: (sc.widgets || []).map(w => {
          if (w.source) return { source: w.source, display: w.display, x: w.x, y: w.y, name: w.name, opts: w.opts };
          // Altes Format konvertieren
          const p = w.props || {};
          return { type: w.type, x: w.x, y: w.y, scaleX: p.scaleX ?? p.scale ?? 1, scaleY: p.scaleY ?? p.scale ?? 1, prefix: p.prefix, text: p.text, w: p.width, h: p.height, diskIdx: p.diskIdx, invert: p.invert||false, border: p.border||false, align: p.align||'left', boxW: p.boxW||0 };
        }),
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
        const widgets = (bs.widgets || []).map(bw => {
          if (bw.source) return { id: Date.now()+Math.random(), source: bw.source, display: bw.display, x: bw.x||0, y: bw.y||0, name: bw.name||'', opts: bw.opts||{} };
          return { id: Date.now()+Math.random(), type: bw.type, x: bw.x||0, y: bw.y||0, props: { scale: 1, ...bw } };
        });
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
  let lpanels=$state(['preview','props','layers']), rpanels=$state(['tools','display']);
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
  const _pd = { tools:{icon:'pen',label:'Werkzeuge',c:false}, display:{icon:'eye',label:'Anzeige',c:true}, preview:{icon:'display',label:'Vorschau',c:false}, props:{icon:'sliders',label:'Eigenschaften',c:true}, layers:{icon:'layer-group',label:'Ebenen',c:false}, weather:{icon:'cloud-sun',label:'Wetter-Ort',c:true} };

  /* Vorlagen entfernt — Profile ersetzen Vorlagen */
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

  onMount(()=>{loadState();pushH();renderWidgets();startWidgetTimer();fetchWeather();setInterval(fetchWeather,600000);});
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
      {@const wt = sw.type ? widgetTypes[sw.type] : null}
      <div class="rr"><span>Widget</span><span class="mono">{sw.name || wt?.label || sw.source || '?'}</span></div>
      <div class="rr"><span>Position</span><span class="mono">{sw.x}, {sw.y}</span></div>
      <div class="pr"><span>X</span><input type="range" min="0" max={W-1} value={sw.x} oninput={(e)=>{sw.x=+e.target.value;placedWidgets=[...placedWidgets];renderWidgets();}}><span class="pv">{sw.x}</span></div>
      <div class="pr"><span>Y</span><input type="range" min="0" max={H-1} value={sw.y} oninput={(e)=>{sw.y=+e.target.value;placedWidgets=[...placedWidgets];renderWidgets();}}><span class="pv">{sw.y}</span></div>
      {#if wp(sw).scale !== undefined || wp(sw).scaleX !== undefined}
        <div class="pr"><span>Breite</span><input type="range" min="1" max="8" value={wp(sw).scaleX??wp(sw).scale??1} oninput={(e)=>updateWidgetProp(selectedWidget,'scaleX',+e.target.value)}><span class="pv">{wp(sw).scaleX??wp(sw).scale??1}x</span></div>
        <div class="pr"><span>Hoehe</span><input type="range" min="1" max="8" value={wp(sw).scaleY??wp(sw).scaleX??wp(sw).scale??1} oninput={(e)=>updateWidgetProp(selectedWidget,'scaleY',+e.target.value)}><span class="pv">{wp(sw).scaleY??wp(sw).scaleX??wp(sw).scale??1}x</span></div>
      {/if}
      {#if wp(sw).text !== undefined}
        <div class="pr"><span>Text</span><input type="text" class="ti" value={wp(sw).text} oninput={(e)=>updateWidgetProp(selectedWidget,'text',e.target.value)}></div>
      {/if}
      {#if wp(sw).prefix !== undefined}
        <div class="pr"><span>Präfix</span><input type="text" class="ti" value={wp(sw).prefix} oninput={(e)=>updateWidgetProp(selectedWidget,'prefix',e.target.value)}></div>
      {/if}
      {#if wp(sw).tsep !== undefined}
        <div class="pr"><span>1.000er</span><button class="tog" class:on={wp(sw).tsep} onclick={()=>updateWidgetProp(selectedWidget,'tsep',!wp(sw).tsep)}></button></div>
      {/if}
      {#if wp(sw).diskIdx !== undefined}
        <div class="pr"><span>Disk</span><input type="range" min="0" max={Math.max(0,(s.stats?.disks?.length||1)-1)} value={wp(sw).diskIdx} oninput={(e)=>updateWidgetProp(selectedWidget,'diskIdx',+e.target.value)}><span class="pv">{s.stats?.disks?.[wp(sw).diskIdx]?.mount||'?'}</span></div>
      {/if}
      {#if wp(sw).width !== undefined}
        <div class="pr"><span>Breite</span><input type="range" min="4" max="128" value={wp(sw).width} oninput={(e)=>updateWidgetProp(selectedWidget,'width',+e.target.value)}><span class="pv">{wp(sw).width}</span></div>
      {/if}
      {#if wp(sw).height !== undefined}
        <div class="pr"><span>Höhe</span><input type="range" min="2" max="64" value={wp(sw).height} oninput={(e)=>updateWidgetProp(selectedWidget,'height',+e.target.value)}><span class="pv">{wp(sw).height}</span></div>
      {/if}
      {#if wp(sw).radius !== undefined}
        <div class="pr"><span>Radius</span><input type="range" min="6" max="30" value={wp(sw).radius} oninput={(e)=>updateWidgetProp(selectedWidget,'radius',+e.target.value)}><span class="pv">{wp(sw).radius}px</span></div>
      {/if}
      <!-- Erweiterte Darstellung -->
      <div class="rr" style="margin-top:6px;color:var(--text-muted);font-size:var(--fs-xs)"><i class="fa-solid fa-wand-magic-sparkles" style="color:var(--accent)"></i> Darstellung</div>
      <div class="pr"><span>Invertiert</span><button class="tog" class:on={wp(sw).invert} onclick={()=>updateWidgetProp(selectedWidget,'invert',!wp(sw).invert)}></button></div>
      <div class="pr"><span>Rahmen</span><button class="tog" class:on={wp(sw).border} onclick={()=>updateWidgetProp(selectedWidget,'border',!wp(sw).border)}></button></div>
      <!-- Streckung X/Y nachtraeglich -->
      <div class="pr"><span>Streck X</span><input type="range" min="1" max="6" value={wp(sw).scaleX??wp(sw).scale??1} oninput={(e)=>updateWidgetProp(selectedWidget,'scaleX',+e.target.value)}><span class="pv">{wp(sw).scaleX??wp(sw).scale??1}x</span></div>
      <div class="pr"><span>Streck Y</span><input type="range" min="1" max="6" value={wp(sw).scaleY??wp(sw).scaleX??wp(sw).scale??1} oninput={(e)=>updateWidgetProp(selectedWidget,'scaleY',+e.target.value)}><span class="pv">{wp(sw).scaleY??wp(sw).scaleX??wp(sw).scale??1}x</span></div>
      <!-- Rotation 90° -->
      <div class="pr"><span>Rotation</span>
        <div class="rot-btns">
          <button class="rot-btn" class:active={!wp(sw).rotate||wp(sw).rotate===0} onclick={()=>updateWidgetProp(selectedWidget,'rotate',0)}>0°</button>
          <button class="rot-btn" class:active={wp(sw).rotate===90} onclick={()=>updateWidgetProp(selectedWidget,'rotate',90)}>90°</button>
          <button class="rot-btn" class:active={wp(sw).rotate===180} onclick={()=>updateWidgetProp(selectedWidget,'rotate',180)}>180°</button>
          <button class="rot-btn" class:active={wp(sw).rotate===270} onclick={()=>updateWidgetProp(selectedWidget,'rotate',270)}>270°</button>
        </div>
      </div>
      {#if !wt?.isShape}
        <div class="pr"><span>Ausr.</span>
          <div class="align-btns">
            <button class="align-btn" class:active={!wp(sw).align||wp(sw).align==='left'} onclick={()=>updateWidgetProp(selectedWidget,'align','left')} title="Links"><i class="fa-solid fa-align-left"></i></button>
            <button class="align-btn" class:active={wp(sw).align==='center'} onclick={()=>updateWidgetProp(selectedWidget,'align','center')} title="Mitte"><i class="fa-solid fa-align-center"></i></button>
            <button class="align-btn" class:active={wp(sw).align==='right'} onclick={()=>updateWidgetProp(selectedWidget,'align','right')} title="Rechts"><i class="fa-solid fa-align-right"></i></button>
          </div>
        </div>
        {#if wp(sw).align && wp(sw).align !== 'left'}
          <div class="pr"><span>Box-B.</span><input type="range" min="0" max="128" value={wp(sw).boxW||0} oninput={(e)=>updateWidgetProp(selectedWidget,'boxW',+e.target.value)}><span class="pv">{wp(sw).boxW||0}</span></div>
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
  {:else if id==='widgets'}
    {#each ['zeit','cpu','ram','disk','net','sys','wetter','layout'] as cat}
      {@const items = widgetList.filter(w => w.cat === cat)}
      {#if items.length > 0}
        {@const catName = {zeit:'Zeit',cpu:'CPU',ram:'RAM',disk:'Festplatten',net:'Netzwerk',sys:'System',wetter:'Wetter',layout:'Layout'}[cat] || cat}
        <div class="wc-cat">{catName}</div>
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
      <!-- Modus-Umschalter + Profil-Leiste -->
      <div class="editor-bar">
        <div class="mode-switch">
          <button class:active={editorMode==='widget'} onclick={()=>editorMode='widget'}>Widget</button>
          <button class:active={editorMode==='raster'} onclick={()=>editorMode='raster'}>Raster</button>
        </div>
        <div class="pb-chips">
          {#each profiles as p}
            <button class="pb-chip" class:active={activeProfile===p.name} onclick={()=>loadProfile(p)}>{p.name}<span class="pb-del" onclick={(e)=>{e.stopPropagation();deleteProfile(p.name);}}>&times;</span></button>
          {/each}
        </div>
        {#if showProfileSave}<input class="pb-input" type="text" placeholder="Name..." bind:value={profileSaveName} onkeydown={(e)=>{if(e.key==='Enter'&&profileSaveName){saveProfile(profileSaveName);showProfileSave=false;profileSaveName='';}if(e.key==='Escape')showProfileSave=false;}} />{/if}
        <button class="pb-btn" onclick={()=>{if(showProfileSave&&profileSaveName){saveProfile(profileSaveName);showProfileSave=false;profileSaveName='';}else{showProfileSave=!showProfileSave;profileSaveName=activeProfile||'';}}} title="Profil speichern"><i class="fa-solid fa-floppy-disk"></i></button>
      </div>

      <!-- Top-Bar: Gespeicherte Widgets -->
      {#if widgetPresets.length > 0}
        <div class="preset-bar">
          {#each widgetPresets as pr}
            <div class="preset-item" onclick={()=>placePresetOnScreen(pr)} title="{pr.name} — Klick zum Platzieren">
              <canvas class="preset-canvas" use:renderPresetCanvas={pr} width={pr.boxW||40} height={pr.boxH||12} style="width:{(pr.boxW||40)*2}px;height:{(pr.boxH||12)*2}px"></canvas>
              <span class="preset-label">{pr.name}</span>
              <button class="preset-del" onclick={(e)=>{e.stopPropagation();deleteWidgetPreset(pr.id);}}>&times;</button>
            </div>
          {/each}
        </div>
      {/if}

      {#if editorMode === 'widget'}
        <!-- ═══ WIDGET-EDITOR: Golden Ratio Split ═══ -->
        <div class="widget-editor">
          <div class="we-canvas">
            <div class="canvas-scroll"><canvas bind:this={canvasEl} width={W*widgetZoom} height={H*widgetZoom} onpointerdown={onDown} onpointermove={onMove} onpointerup={onUp} oncontextmenu={onContext} style="width:{W*widgetZoom}px;height:{H*widgetZoom}px"></canvas></div>
          </div>
          <div class="we-browser">
            <div class="tab-bar">
              {#each TABS as tab}
                <button class="tab-btn" class:active={activeTab===tab.id} onclick={()=>{activeTab=tab.id;configSource=null;}}>{tab.label}</button>
              {/each}
            </div>
            <div class="tab-content">
              {#each getSourcesForTab(activeTab, s.stats) as src}
                {#if src.isHeader}
                  <div class="data-header">{src.label}</div>
                {:else}
                  {@const val = src.getValue ? src.getValue(s.stats, weather, {}) : '—'}
                  <button class="data-row" class:active={configSource?.id===src.id} onclick={()=>selectSource(src)}>
                    <span class="dk">{src.label}</span>
                    <span class="dv">{val}{src.unit ? ' '+src.unit : ''}</span>
                  </button>
                {/if}
              {/each}
              {#if activeTab === 'wetter'}
                <div class="we-loc">
                  <input type="text" class="ti" placeholder="Ort suchen..." value={locationSearch} oninput={onLocationInput}>
                  {#if locationResults.length > 0}
                    <div class="loc-results">{#each locationResults as loc}<button class="loc-item" onclick={()=>selectLocation(loc)}>{loc.name}{loc.country ? ', '+loc.country : ''}</button>{/each}</div>
                  {/if}
                </div>
              {/if}
              {#if configSource}
                <div class="conf-box">
                  <div class="conf-title">{configSource.label}</div>

                  <!-- Darstellungsmodus -->
                  <div class="conf-label">Darstellung</div>
                  <div class="mode-grid">
                    {#each getModesForType(configSource.type) as mode}
                      <button class="mode-btn" class:active={configDisplay===mode.id} onclick={()=>setConfigDisplay(mode.id)}>{mode.label}</button>
                    {/each}
                  </div>

                  <!-- Live-Vorschau in Bounding-Box -->
                  <div class="conf-label">Vorschau <span class="conf-dim">{cfgBoxW}×{cfgBoxH}px</span></div>
                  <div class="conf-preview">
                    <canvas bind:this={configPreviewEl} width={cfgBoxW} height={cfgBoxH} class="conf-canvas" style="width:{cfgBoxW*3}px;height:{cfgBoxH*3}px"></canvas>
                  </div>

                  <!-- Bounding-Box Größe -->
                  <div class="conf-label">Bounding-Box</div>
                  <div class="pr"><span>Breite</span><input type="range" min="8" max="128" bind:value={cfgBoxW}><span class="pv">{cfgBoxW}px</span></div>
                  <div class="pr"><span>Hoehe</span><input type="range" min="6" max="64" bind:value={cfgBoxH}><span class="pv">{cfgBoxH}px</span></div>

                  <!-- Optionen je nach Modus -->
                  {#if cfgOpts.scaleX !== undefined}
                    <div class="conf-label">Skalierung</div>
                    <div class="pr"><span>X</span><input type="range" min="1" max="6" bind:value={cfgOpts.scaleX}><span class="pv">{cfgOpts.scaleX}x</span></div>
                    <div class="pr"><span>Y</span><input type="range" min="1" max="6" value={cfgOpts.scaleY??cfgOpts.scaleX} oninput={(e)=>cfgOpts.scaleY=+e.target.value}><span class="pv">{cfgOpts.scaleY??cfgOpts.scaleX}x</span></div>
                  {/if}
                  {#if cfgOpts.prefix !== undefined}
                    <div class="pr"><span>Praefix</span><input type="text" class="ti" bind:value={cfgOpts.prefix}></div>
                  {/if}
                  {#if cfgOpts.suffix !== undefined}
                    <div class="pr"><span>Suffix</span><input type="text" class="ti" bind:value={cfgOpts.suffix}></div>
                  {/if}
                  {#if cfgOpts.text !== undefined}
                    <div class="pr"><span>Text</span><input type="text" class="ti" bind:value={cfgOpts.text}></div>
                  {/if}
                  {#if cfgOpts.width !== undefined}
                    <div class="pr"><span>Breite</span><input type="range" min="4" max="126" bind:value={cfgOpts.width}><span class="pv">{cfgOpts.width}</span></div>
                  {/if}
                  {#if cfgOpts.height !== undefined}
                    <div class="pr"><span>Hoehe</span><input type="range" min="2" max="62" bind:value={cfgOpts.height}><span class="pv">{cfgOpts.height}</span></div>
                  {/if}
                  {#if cfgOpts.radius !== undefined}
                    <div class="pr"><span>Radius</span><input type="range" min="6" max="30" bind:value={cfgOpts.radius}><span class="pv">{cfgOpts.radius}</span></div>
                  {/if}

                  <!-- Simulation -->
                  <div class="conf-label">Simulation</div>
                  <div class="pr">
                    <span>Wert</span>
                    {#if cfgSimVal !== null}
                      <input type="range" min="0" max="100" bind:value={cfgSimVal}>
                      <span class="pv">{cfgSimVal}</span>
                      <button class="sim-reset" onclick={()=>cfgSimVal=null}>Live</button>
                    {:else}
                      <button class="sim-start" onclick={()=>cfgSimVal=50}>Simulieren</button>
                    {/if}
                  </div>

                  <!-- Name -->
                  <div class="pr"><span>Name</span><input type="text" class="ti" bind:value={cfgName}></div>

                  <button class="add-btn" onclick={saveAsWidgetPreset}><i class="fa-solid fa-puzzle-piece"></i> Als Widget speichern</button>
                </div>
              {/if}
            </div>
          </div>
        </div>
      {:else}
        <!-- ═══ RASTER-EDITOR: Voller Canvas ═══ -->
        <div class="canvas-scroll"><canvas bind:this={canvasEl} width={W*zoom} height={H*zoom} onpointerdown={onDown} onpointermove={onMove} onpointerup={onUp} oncontextmenu={onContext} style="width:{W*zoom}px;height:{H*zoom}px"></canvas></div>
      {/if}
      {#if ctxMenu}
        <div class="ctx-menu" style="left:{ctxMenu.x}px;top:{ctxMenu.y}px">
          <button class="ctx-item" onclick={()=>ctxAction('dup')}><i class="fa-solid fa-copy"></i> Duplizieren</button>
          <button class="ctx-item" onclick={()=>ctxAction('front')}><i class="fa-solid fa-arrow-up"></i> Nach vorne</button>
          <button class="ctx-item" onclick={()=>ctxAction('back')}><i class="fa-solid fa-arrow-down"></i> Nach hinten</button>
          <div class="ctx-sep"></div>
          <button class="ctx-item ctx-del" onclick={()=>ctxAction('del')}><i class="fa-solid fa-trash-can"></i> Loeschen</button>
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
  .canvas-scroll { flex: 1; overflow: auto; display: flex; align-items: flex-start; justify-content: flex-start; padding: 20px; }

  /* Editor-Bar (Modus + Profile) */
  .editor-bar { display: flex; align-items: center; gap: 6px; padding: 4px 10px; border-bottom: 1px solid var(--border); background: var(--bg-base); flex-shrink: 0; }

  /* Preset-Bar (gespeicherte Widgets) */
  .preset-bar {
    display: flex; gap: 6px; overflow-x: auto; padding: 5px 10px;
    border-bottom: 1px solid var(--border); background: var(--bg-surface);
    flex-shrink: 0; align-items: flex-end; scrollbar-width: thin;
  }
  .preset-item {
    display: flex; flex-direction: column; align-items: center; gap: 2px;
    cursor: pointer; flex-shrink: 0; padding: 3px;
    border-radius: var(--radius-sm); border: 1px solid var(--border);
    background: var(--bg-elevated); position: relative;
    transition: border-color 120ms;
  }
  .preset-item:hover { border-color: var(--accent); }
  .preset-canvas {
    image-rendering: pixelated; image-rendering: crisp-edges;
    background: #000; border-radius: 2px; display: block;
  }
  .preset-label {
    font: 500 8px var(--font); color: var(--text-muted);
    max-width: 80px; overflow: hidden; text-overflow: ellipsis;
    white-space: nowrap; text-align: center; line-height: 1;
  }
  .preset-del {
    position: absolute; top: -4px; right: -4px;
    width: 14px; height: 14px; border-radius: 50%;
    border: 1px solid var(--border); background: var(--bg-elevated);
    color: var(--text-muted); cursor: pointer; font-size: 9px;
    display: none; align-items: center; justify-content: center; line-height: 1;
  }
  .preset-item:hover .preset-del { display: flex; }
  .preset-del:hover { color: var(--red); border-color: var(--red); }
  .mode-switch { display: flex; gap: 1px; background: var(--bg-surface); border-radius: var(--radius-sm); padding: 2px; flex-shrink: 0; }
  .mode-switch button { padding: 4px 12px; border: none; background: none; color: var(--text-muted); font: 600 var(--fs-xs) var(--font); cursor: pointer; border-radius: var(--radius-sm); }
  .mode-switch button.active { background: var(--accent); color: #fff; }
  .pb-chips { display: flex; gap: 3px; overflow-x: auto; flex: 1; }
  .pb-chip { display: flex; align-items: center; gap: 3px; padding: 2px 8px; border-radius: 10px; border: 1px solid var(--border); background: var(--bg-elevated); color: var(--text-muted); font: 500 9px var(--font); cursor: pointer; white-space: nowrap; flex-shrink: 0; }
  .pb-chip:hover { border-color: var(--accent); color: var(--accent); }
  .pb-chip.active { background: var(--accent-dim); border-color: var(--accent); color: var(--accent); }
  .pb-del { font-size: 10px; cursor: pointer; margin-left: 2px; }
  .pb-del:hover { color: var(--red); }
  .pb-input { width: 90px; padding: 2px 6px; border: 1px solid var(--accent); background: var(--bg-elevated); color: var(--text-primary); border-radius: 10px; font: 500 9px var(--mono); }
  .pb-btn { width: 24px; height: 24px; border-radius: 50%; border: 1px solid var(--border); background: none; color: var(--text-muted); cursor: pointer; font-size: 10px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
  .pb-btn:hover { border-color: var(--accent); color: var(--accent); }

  /* Widget-Editor (Golden Ratio) */
  .widget-editor { flex: 1; display: flex; overflow: hidden; }
  .we-canvas { flex-shrink: 0; overflow: auto; display: flex; align-items: flex-start; justify-content: flex-start; padding: 12px; }
  .we-browser { flex: 1; display: flex; flex-direction: column; border-left: 1px solid var(--border); background: var(--bg-base); overflow: hidden; }
  .tab-bar { display: flex; gap: 1px; border-bottom: 2px solid var(--border); flex-shrink: 0; overflow-x: auto; background: var(--bg-surface); }
  .tab-btn { padding: 7px 10px; border: none; background: none; color: var(--text-muted); font: 600 9px var(--font); cursor: pointer; border-bottom: 2px solid transparent; margin-bottom: -2px; white-space: nowrap; text-transform: uppercase; letter-spacing: 0.04em; }
  .tab-btn:hover { color: var(--text-primary); }
  .tab-btn.active { color: var(--accent); border-bottom-color: var(--accent); }
  .tab-content { flex: 1; overflow-y: auto; padding: 6px; display: flex; flex-direction: column; gap: 2px; }
  .data-row { display: flex; justify-content: space-between; align-items: center; padding: 6px 10px; border-radius: var(--radius-sm); border: 1px solid transparent; background: var(--bg-surface); cursor: pointer; text-align: left; width: 100%; }
  .data-row:hover { border-color: var(--accent); background: rgba(0,180,255,0.04); }
  .data-row.active { border-color: var(--accent); background: var(--accent-dim); }
  .dk { font: 500 var(--fs-sm) var(--font); color: var(--text-secondary); }
  .dv { font: 600 var(--fs-sm) var(--mono); color: var(--text-primary); }
  .data-header { font: 600 9px var(--font); color: var(--accent); padding: 6px 10px 2px; text-transform: uppercase; letter-spacing: 0.04em; }
  .we-loc { margin-top: 4px; }
  .conf-box { padding: 8px; border: 1px solid var(--border); border-radius: var(--radius); background: var(--bg-surface); margin-top: 6px; }
  .conf-title { font: 600 var(--fs-sm) var(--font); color: var(--text-primary); margin-bottom: 6px; }
  .mode-grid { display: flex; flex-wrap: wrap; gap: 3px; margin-bottom: 8px; }
  .mode-btn { padding: 4px 10px; border-radius: var(--radius-sm); border: 1px solid var(--border); background: var(--bg-elevated); color: var(--text-muted); font: 500 var(--fs-xs) var(--font); cursor: pointer; }
  .mode-btn:hover { border-color: var(--accent); color: var(--accent); }
  .mode-btn.active { background: var(--accent-dim); border-color: var(--accent); color: var(--accent); }
  .conf-label { font: 600 9px var(--font); text-transform: uppercase; letter-spacing: 0.06em; color: var(--text-muted); margin: 8px 0 3px; }
  .conf-dim { font: 500 9px var(--mono); color: var(--accent); margin-left: 6px; }
  .conf-preview { display: flex; justify-content: center; padding: 8px 0; background: #111; border-radius: var(--radius-sm); margin: 4px 0; }
  .conf-canvas {
    image-rendering: pixelated; image-rendering: crisp-edges;
    border: none; background: #000;
  }
  .sim-start, .sim-reset {
    padding: 2px 8px; border-radius: var(--radius-sm); border: 1px solid var(--border);
    background: var(--bg-elevated); color: var(--text-muted); font: 500 9px var(--font);
    cursor: pointer; flex-shrink: 0;
  }
  .sim-start:hover, .sim-reset:hover { border-color: var(--accent); color: var(--accent); }
  .sim-reset { border-color: var(--green); color: var(--green); }
  .add-btn { width: 100%; padding: 7px; border-radius: var(--radius-sm); border: 1px solid var(--accent); background: var(--accent-dim); color: var(--accent); font: 600 var(--fs-sm) var(--font); cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 6px; }
  .add-btn:hover { background: var(--accent); color: #fff; }
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
  .ti { flex: 1; min-width: 0; padding: 5px 8px; border: 1px solid var(--border); background: var(--bg-elevated); color: var(--text-primary); border-radius: var(--radius-sm); font: 500 var(--fs-sm) var(--mono); box-sizing: border-box; }
  .tog { width: 34px; height: 18px; border-radius: 9px; border: none; background: rgba(255,255,255,0.1); cursor: pointer; position: relative; transition: background 150ms; }
  .tog.on { background: var(--green); }
  .tog::after { content:''; position:absolute; top:2px; left:2px; width:14px; height:14px; border-radius:50%; background:#fff; transition:transform 150ms; }
  .tog.on::after { transform: translateX(16px); }

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
  .rot-btns { display: flex; gap: 2px; }
  .rot-btn { padding: 2px 8px; border-radius: var(--radius-sm); border: 1px solid var(--border); background: var(--bg-elevated); color: var(--text-muted); font: 500 9px var(--mono); cursor: pointer; }
  .rot-btn:hover { border-color: var(--accent); color: var(--accent); }
  .rot-btn.active { background: var(--accent-dim); border-color: var(--accent); color: var(--accent); }
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
