<script>
  import { onMount, onDestroy, tick } from 'svelte';
  let { state: s } = $props();

  const S = 4; // 128×64 → 512×256

  /* ═══════════════════════════════════════════════════════
     1-BIT BITMAP FONT (5×7 Pixel)
     Jeder Char = 7 Zeilen à 5 Bits → Pixel an/aus
     ═══════════════════════════════════════════════════════ */
  const G = {
    '0':'01110,10001,10011,10101,11001,10001,01110',
    '1':'00100,01100,00100,00100,00100,00100,01110',
    '2':'01110,10001,00001,00010,00100,01000,11111',
    '3':'01110,10001,00001,00110,00001,10001,01110',
    '4':'00010,00110,01010,10010,11111,00010,00010',
    '5':'11111,10000,11110,00001,00001,10001,01110',
    '6':'00110,01000,10000,11110,10001,10001,01110',
    '7':'11111,00001,00010,00100,01000,01000,01000',
    '8':'01110,10001,10001,01110,10001,10001,01110',
    '9':'01110,10001,10001,01111,00001,00010,01100',
    'A':'01110,10001,10001,11111,10001,10001,10001',
    'B':'11110,10001,10001,11110,10001,10001,11110',
    'C':'01110,10001,10000,10000,10000,10001,01110',
    'D':'11110,10001,10001,10001,10001,10001,11110',
    'E':'11111,10000,10000,11110,10000,10000,11111',
    'F':'11111,10000,10000,11110,10000,10000,10000',
    'G':'01110,10001,10000,10111,10001,10001,01110',
    'H':'10001,10001,10001,11111,10001,10001,10001',
    'I':'01110,00100,00100,00100,00100,00100,01110',
    'J':'00001,00001,00001,00001,10001,10001,01110',
    'K':'10001,10010,10100,11000,10100,10010,10001',
    'L':'10000,10000,10000,10000,10000,10000,11111',
    'M':'10001,11011,10101,10101,10001,10001,10001',
    'N':'10001,11001,10101,10011,10001,10001,10001',
    'O':'01110,10001,10001,10001,10001,10001,01110',
    'P':'11110,10001,10001,11110,10000,10000,10000',
    'R':'11110,10001,10001,11110,10100,10010,10001',
    'S':'01110,10001,10000,01110,00001,10001,01110',
    'T':'11111,00100,00100,00100,00100,00100,00100',
    'U':'10001,10001,10001,10001,10001,10001,01110',
    'V':'10001,10001,10001,10001,01010,01010,00100',
    'W':'10001,10001,10001,10101,10101,11011,10001',
    'X':'10001,01010,00100,00100,00100,01010,10001',
    'Y':'10001,01010,00100,00100,00100,00100,00100',
    'Z':'11111,00001,00010,00100,01000,10000,11111',
    'a':'00000,00000,01110,00001,01111,10001,01111',
    'b':'10000,10000,11110,10001,10001,10001,11110',
    'c':'00000,00000,01110,10000,10000,10001,01110',
    'd':'00001,00001,01111,10001,10001,10001,01111',
    'e':'00000,00000,01110,10001,11111,10000,01110',
    'f':'00110,01000,01000,11100,01000,01000,01000',
    'g':'00000,00000,01111,10001,01111,00001,01110',
    'h':'10000,10000,11110,10001,10001,10001,10001',
    'i':'00100,00000,01100,00100,00100,00100,01110',
    'k':'10000,10001,10010,10100,11000,10100,10010',
    'l':'01100,00100,00100,00100,00100,00100,01110',
    'm':'00000,00000,11010,10101,10101,10001,10001',
    'n':'00000,00000,11110,10001,10001,10001,10001',
    'o':'00000,00000,01110,10001,10001,10001,01110',
    'p':'00000,00000,11110,10001,11110,10000,10000',
    'r':'00000,00000,10110,11001,10000,10000,10000',
    's':'00000,00000,01111,10000,01110,00001,11110',
    't':'01000,01000,11100,01000,01000,01001,00110',
    'u':'00000,00000,10001,10001,10001,10011,01101',
    'v':'00000,00000,10001,10001,01010,01010,00100',
    'w':'00000,00000,10001,10001,10101,10101,01010',
    'x':'00000,00000,10001,01010,00100,01010,10001',
    'y':'00000,00000,10001,01010,00100,01000,10000',
    ' ':'00000,00000,00000,00000,00000,00000,00000',
    '.':'00000,00000,00000,00000,00000,00000,00100',
    ',':'00000,00000,00000,00000,00000,00100,01000',
    ':':'00000,00100,00100,00000,00100,00100,00000',
    '/':'00001,00010,00010,00100,01000,01000,10000',
    '%':'10001,00010,00010,00100,01000,01000,10001',
    '°':'01100,10010,01100,00000,00000,00000,00000',
    '-':'00000,00000,00000,11111,00000,00000,00000',
    '↓':'00100,00100,00100,10101,01110,00100,00000',
    '↑':'00100,01110,10101,00100,00100,00100,00000',
    'Q':'01110,10001,10001,10001,10101,10010,01101',
    /* ── Deutsche Umlaute und Sonderzeichen ── */
    'Ä':'10001,00000,01110,10001,11111,10001,10001',
    'Ö':'10001,00000,01110,10001,10001,10001,01110',
    'Ü':'10001,00000,10001,10001,10001,10001,01110',
    'ä':'01010,00000,01110,00001,01111,10001,01111',
    'ö':'01010,00000,01110,10001,10001,10001,01110',
    'ü':'01010,00000,10001,10001,10001,10011,01101',
    'ß':'01110,10001,10010,10100,10010,10001,10110',
  };

  function drawText(ctx, str, x, y, scale = 1) {
    let cx = x;
    for (const ch of str) {
      const g = G[ch] || G[ch.toUpperCase()];
      if (!g) { cx += 4 * scale; continue; }
      const rows = g.split(',');
      rows.forEach((row, ry) => {
        for (let rx = 0; rx < row.length; rx++) {
          if (row[rx] === '1') ctx.fillRect(cx + rx * scale, y + ry * scale, scale, scale);
        }
      });
      cx += 6 * scale;
    }
  }

  /* ═══ PIXEL-ART ICONS ═══ */
  function drawThermo(ctx, x, y) {
    ctx.fillRect(x+2,y,2,5);
    ctx.fillRect(x+1,y+5,4,1); ctx.fillRect(x+1,y+6,4,1); ctx.fillRect(x+2,y+7,2,1);
  }
  function drawSun(ctx, x, y, s) {
    if (s <= 8) {
      ctx.fillRect(x+3,y,2,1); ctx.fillRect(x+3,y+7,2,1);
      ctx.fillRect(x,y+3,1,2); ctx.fillRect(x+7,y+3,1,2);
      ctx.fillRect(x+1,y+1,1,1); ctx.fillRect(x+6,y+1,1,1);
      ctx.fillRect(x+1,y+6,1,1); ctx.fillRect(x+6,y+6,1,1);
      ctx.fillRect(x+2,y+2,4,4);
    } else {
      ctx.fillRect(x+6,y,4,2); ctx.fillRect(x+6,y+14,4,2);
      ctx.fillRect(x,y+6,2,4); ctx.fillRect(x+14,y+6,2,4);
      ctx.fillRect(x+2,y+2,2,2); ctx.fillRect(x+12,y+2,2,2);
      ctx.fillRect(x+2,y+12,2,2); ctx.fillRect(x+12,y+12,2,2);
      ctx.fillRect(x+5,y+4,6,8); ctx.fillRect(x+4,y+5,8,6);
    }
  }
  function drawMoon(ctx, x, y, s) {
    if (s <= 8) {
      ctx.fillRect(x+2,y,3,1); ctx.fillRect(x+1,y+1,2,1); ctx.fillRect(x+1,y+2,1,1);
      ctx.fillRect(x+1,y+3,1,2); ctx.fillRect(x+1,y+5,2,1); ctx.fillRect(x+2,y+6,3,1);
      ctx.fillRect(x+4,y+5,1,1); ctx.fillRect(x+5,y+2,1,3);
    } else {
      ctx.fillRect(x+4,y,5,2); ctx.fillRect(x+2,y+2,3,2); ctx.fillRect(x+2,y+4,2,2);
      ctx.fillRect(x+2,y+6,2,4); ctx.fillRect(x+2,y+10,3,2);
      ctx.fillRect(x+4,y+12,5,2); ctx.fillRect(x+8,y+10,2,2);
      ctx.fillRect(x+9,y+4,2,6); ctx.fillRect(x+8,y+2,2,2);
    }
  }
  function drawBar(ctx, x, y, w, h, pct) {
    for (let i = 0; i < w; i++) { ctx.fillRect(x+i,y,1,1); ctx.fillRect(x+i,y+h-1,1,1); }
    for (let j = 0; j < h; j++) { ctx.fillRect(x,y+j,1,1); ctx.fillRect(x+w-1,y+j,1,1); }
    const fw = Math.round((w - 2) * Math.min(1, pct));
    for (let j = 1; j < h-1; j++) for (let i = 0; i < fw; i++) ctx.fillRect(x+1+i,y+j,1,1);
  }
  function threshold(ctx, w, h) {
    const d = ctx.getImageData(0, 0, w, h);
    const px = d.data;
    for (let i = 0; i < px.length; i += 4) {
      const on = px[i] > 80 || px[i+1] > 80 || px[i+2] > 80;
      px[i] = px[i+1] = px[i+2] = on ? 255 : 0; px[i+3] = 255;
    }
    ctx.putImageData(d, 0, 0);
  }

  /* ═══ ATOM CATALOG ═══ */
  const ATOMS = {
    clock:        { cat:'zeit',  label:'Uhr HH:MM',       w:58, h:18, font:'lg',  r:(c,x,y)=>{drawText(c,'14:32',x,y,2)} },
    clock_hms:    { cat:'zeit',  label:'Uhr HH:MM:SS',    w:48, h:10, font:'sm',  r:(c,x,y)=>{drawText(c,'14:32:07',x,y+1)} },
    clock_large:  { cat:'zeit',  label:'Uhr Groß',        w:96, h:26, font:'xl',  r:(c,x,y)=>{drawText(c,'14:32',x,y,3)} },
    date:         { cat:'zeit',  label:'Datum',            w:58, h:10, font:'sm',  r:(c,x,y)=>{drawText(c,'12.02.2026',x,y+1)} },
    weekday:      { cat:'zeit',  label:'Wochentag',        w:14, h:10, font:'sm',  r:(c,x,y)=>{drawText(c,'Do',x,y+1)} },
    datetime_full:{ cat:'zeit',  label:'Datum + Tag',      w:72, h:10, font:'sm',  r:(c,x,y)=>{drawText(c,'Do 12.02.2026',x,y+1)} },

    cpu_temp:     { cat:'sys',   label:'CPU Temp+%',       w:82, h:10, font:'sm',  r:(c,x,y)=>{drawThermo(c,x,y);drawText(c,'42C  CPU 12%',x+10,y+1)} },
    cpu_temp_only:{ cat:'sys',   label:'CPU °C',           w:30, h:10, font:'sm',  r:(c,x,y)=>{drawText(c,'42°C',x,y+1)} },
    cpu_pct:      { cat:'sys',   label:'CPU %',            w:40, h:10, font:'sm',  r:(c,x,y)=>{drawText(c,'CPU 12%',x,y+1)} },
    cpu_bar:      { cat:'sys',   label:'CPU Balken',       w:60, h:6,  font:'',    r:(c,x,y,w,h)=>{drawBar(c,x,y,w||60,h||6,0.12)} },
    ram_bar:      { cat:'sys',   label:'RAM Text',         w:82, h:10, font:'sm',  r:(c,x,y)=>{drawText(c,'RAM 4.2/16G 26%',x,y+1)} },
    ram_pct:      { cat:'sys',   label:'RAM %',            w:40, h:10, font:'sm',  r:(c,x,y)=>{drawText(c,'RAM 26%',x,y+1)} },
    ram_bar_gfx:  { cat:'sys',   label:'RAM Balken',       w:60, h:6,  font:'',    r:(c,x,y,w,h)=>{drawBar(c,x,y,w||60,h||6,0.26)} },
    disk:         { cat:'sys',   label:'Disk Text',        w:72, h:10, font:'sm',  r:(c,x,y)=>{drawText(c,'DSK 1842/3726G',x,y+1)} },
    disk_bar:     { cat:'sys',   label:'Disk Balken',      w:60, h:6,  font:'',    r:(c,x,y,w,h)=>{drawBar(c,x,y,w||60,h||6,0.49)} },
    docker:       { cat:'sys',   label:'Docker',           w:60, h:10, font:'sm',  r:(c,x,y)=>{drawText(c,'Docker: 8 up',x,y+1)} },
    ip:           { cat:'sys',   label:'IP-Adresse',       w:82, h:10, font:'sm',  r:(c,x,y)=>{drawText(c,'IP 10.0.0.1',x,y+1)} },
    uptime:       { cat:'sys',   label:'Uptime',           w:60, h:10, font:'sm',  r:(c,x,y)=>{drawText(c,'Up 3d 14:32',x,y+1)} },

    network:      { cat:'net',   label:'Netz Rx/Tx',       w:82, h:10, font:'sm',  r:(c,x,y)=>{drawText(c,'Rx142 Tx38 KB/s',x,y+1)} },
    net_rx:       { cat:'net',   label:'Download',          w:52, h:10, font:'sm',  r:(c,x,y)=>{drawText(c,'↓142KB/s',x,y+1)} },
    net_tx:       { cat:'net',   label:'Upload',            w:52, h:10, font:'sm',  r:(c,x,y)=>{drawText(c,'↑38KB/s',x,y+1)} },

    weather:      { cat:'wetter',label:'Wetter Mini',      w:72, h:10, font:'sm',  r:(c,x,y)=>{drawSun(c,x,y,8);drawText(c,'8°C Wolkig',x+10,y+1)} },
    w_temp:       { cat:'wetter',label:'Temperatur',       w:36, h:18, font:'lg',  r:(c,x,y)=>{drawText(c,'8°',x,y,2)} },
    w_temp_sm:    { cat:'wetter',label:'Temp Klein',       w:28, h:10, font:'sm',  r:(c,x,y)=>{drawText(c,'8°C',x,y+1)} },
    w_feels:      { cat:'wetter',label:'Gefühlt',          w:52, h:10, font:'sm',  r:(c,x,y)=>{drawText(c,'Gef.5°',x,y+1)} },
    w_icon:       { cat:'wetter',label:'Wetter-Icon',      w:16, h:16, font:'',    r:(c,x,y)=>{drawSun(c,x,y,16)} },
    w_icon_sm:    { cat:'wetter',label:'Icon Klein',       w:8,  h:8,  font:'',    r:(c,x,y)=>{drawSun(c,x,y,8)} },
    w_cond:       { cat:'wetter',label:'Beschreibung',     w:48, h:10, font:'sm',  r:(c,x,y)=>{drawText(c,'Wolkig',x,y+1)} },
    w_hum:        { cat:'wetter',label:'Feuchtigkeit',     w:32, h:10, font:'sm',  r:(c,x,y)=>{drawText(c,'78%',x,y+1)} },
    w_wind:       { cat:'wetter',label:'Wind',             w:48, h:10, font:'sm',  r:(c,x,y)=>{drawText(c,'12km/h',x,y+1)} },
    w_press:      { cat:'wetter',label:'Luftdruck',        w:52, h:10, font:'sm',  r:(c,x,y)=>{drawText(c,'1013hPa',x,y+1)} },
    w_sunrise:    { cat:'wetter',label:'Sonnenaufgang',    w:42, h:10, font:'sm',  r:(c,x,y)=>{drawSun(c,x,y,8);drawText(c,'07:14',x+10,y+1)} },
    w_sunset:     { cat:'wetter',label:'Sonnenuntergang',  w:42, h:10, font:'sm',  r:(c,x,y)=>{drawMoon(c,x,y,8);drawText(c,'17:42',x+10,y+1)} },
    w_uv:         { cat:'wetter',label:'UV-Index',         w:24, h:10, font:'sm',  r:(c,x,y)=>{drawText(c,'UV2',x,y+1)} },
    w_location:   { cat:'wetter',label:'Ort',              w:52, h:10, font:'sm',  r:(c,x,y)=>{drawText(c,'Stuttgart',x,y+1)} },

    label:        { cat:'deko',  label:'Text',             w:48, h:10, font:'sm',  r:(c,x,y)=>{drawText(c,'Mein Text',x,y+1)} },
    line_h:       { cat:'deko',  label:'Linie ─',          w:60, h:1,  font:'',    r:(c,x,y,w)=>{for(let i=0;i<(w||60);i++)c.fillRect(x+i,y,1,1)} },
    line_v:       { cat:'deko',  label:'Linie │',          w:1,  h:20, font:'',    r:(c,x,y,_,h)=>{for(let j=0;j<(h||20);j++)c.fillRect(x,y+j,1,1)} },
    rect:         { cat:'deko',  label:'Rahmen □',         w:40, h:20, font:'',    r:(c,x,y,w,h)=>{drawBar(c,x,y,w||40,h||20,0)} },
  };

  const CATS = [
    { id:'zeit',  name:'Zeit',     icon:'fa-clock' },
    { id:'sys',   name:'System',   icon:'fa-microchip' },
    { id:'net',   name:'Netzwerk', icon:'fa-network-wired' },
    { id:'wetter',name:'Wetter',   icon:'fa-cloud-sun' },
    { id:'deko',  name:'Deko',     icon:'fa-pen' },
  ];

  const PRESETS = {
    system: { name:'System', widgets:[
      {type:'clock',x:0,y:0,font:'lg'},{type:'cpu_temp',x:0,y:22,font:'sm'},
      {type:'ram_bar',x:0,y:34,font:'sm'},{type:'disk',x:0,y:46,font:'sm'},
      {type:'uptime',x:0,y:56,font:'sm'},
    ]},
    wetter: { name:'Wetter', widgets:[
      {type:'w_location',x:2,y:0,font:'sm'},{type:'clock_hms',x:78,y:0,font:'sm'},
      {type:'w_icon',x:2,y:14},{type:'w_temp',x:22,y:12,font:'lg'},
      {type:'w_cond',x:62,y:14,font:'sm'},{type:'w_feels',x:62,y:24,font:'sm'},
      {type:'line_h',x:0,y:36,w:128},{type:'w_hum',x:2,y:40,font:'sm'},
      {type:'w_wind',x:42,y:40,font:'sm'},{type:'w_press',x:2,y:52,font:'sm'},
      {type:'w_sunrise',x:62,y:40,font:'sm'},{type:'w_sunset',x:62,y:52,font:'sm'},
    ]},
    uhr: { name:'Uhr Groß', widgets:[
      {type:'clock_large',x:2,y:2},{type:'weekday',x:2,y:34,font:'md'},
      {type:'date',x:20,y:34,font:'md'},{type:'cpu_temp_only',x:2,y:52,font:'sm'},
      {type:'ram_pct',x:38,y:52,font:'sm'},{type:'uptime',x:76,y:52,font:'sm'},
    ]},
    netzwerk: { name:'Netzwerk', widgets:[
      {type:'ip',x:0,y:0,font:'sm'},{type:'net_rx',x:0,y:14,font:'md'},
      {type:'net_tx',x:0,y:28,font:'md'},{type:'docker',x:0,y:44,font:'sm'},
      {type:'uptime',x:0,y:54,font:'sm'},
    ]},
  };

  /* ═══ MINI-PREVIEW CACHE ═══ */
  const miniCache = {};
  function getMiniDataUrl(type) {
    if (miniCache[type]) return miniCache[type];
    const atom = ATOMS[type];
    if (!atom) return '';
    const c = document.createElement('canvas');
    c.width = 48; c.height = 24;
    const ctx = c.getContext('2d');
    ctx.imageSmoothingEnabled = false;
    ctx.fillStyle = '#fff';
    const sx = 48 / Math.max(atom.w, 16);
    const sy = 24 / Math.max(atom.h, 6);
    const sc = Math.min(sx, sy, 2);
    ctx.save();
    ctx.translate(Math.floor((48 - atom.w * sc) / 2), Math.floor((24 - atom.h * sc) / 2));
    ctx.scale(sc, sc);
    try { atom.r(ctx, 0, 0, atom.w, atom.h); } catch(e) {}
    ctx.restore();
    threshold(ctx, 48, 24);
    miniCache[type] = c.toDataURL();
    return miniCache[type];
  }

  /* ═══ STATE ═══ */
  let sel = $state(-1);
  let localWidgets = $state([]);
  let isDragging = $state(false);
  let saving = $state(false);
  let canvasEl = $state(null);
  let oledEl = $state(null);
  let dragOffX = 0, dragOffY = 0;
  let openCats = $state({ zeit:true, sys:true, net:false, wetter:true, deko:false });
  let showGrid = $state(true);
  let _commitTimer = 0;
  let _sliderTimers = {};

  /* ═══ SYNC: Store → Local ═══ */
  let _syncedIdx = -1;
  $effect(() => {
    const idx = s.oled?.current_screen ?? 0;
    const screens = s.oled?.screens;
    if (idx !== _syncedIdx && screens) {
      _syncedIdx = idx;
      const scr = screens[idx];
      localWidgets = scr?.widgets ? JSON.parse(JSON.stringify(scr.widgets)) : [];
      sel = -1;
      renderOLED();
    }
  });

  /* ═══ DERIVED ═══ */
  let screenIdx = $derived(s.oled?.current_screen ?? 0);
  let currentScreen = $derived((s.oled?.screens || [])[screenIdx] || {});
  let isEditable = $derived(currentScreen.type === 'system');
  let preview = $derived(s.oled?.preview || '');
  let selWidget = $derived(sel >= 0 && sel < localWidgets.length ? localWidgets[sel] : null);
  let selAtom = $derived(selWidget ? ATOMS[selWidget.type] : null);

  function atomsForCat(catId) {
    return Object.entries(ATOMS).filter(([_, a]) => a.cat === catId);
  }

  /* ═══ OLED CANVAS RENDERING ═══ */
  function renderOLED() {
    if (!oledEl) return;
    const ctx = oledEl.getContext('2d');
    ctx.imageSmoothingEnabled = false;
    ctx.clearRect(0, 0, 128, 64);
    ctx.fillStyle = '#fff';
    localWidgets.forEach(w => {
      const atom = ATOMS[w.type];
      if (!atom) return;
      try { atom.r(ctx, w.x, w.y, w.w || atom.w, w.h || atom.h); } catch(e) {}
    });
    threshold(ctx, 128, 64);
  }

  $effect(() => {
    const _ = JSON.stringify(localWidgets);
    renderOLED();
  });

  /* ═══ DEBOUNCE ═══ */
  function debouncedSlider(fn, ms, key) {
    clearTimeout(_sliderTimers[key]);
    _sliderTimers[key] = setTimeout(fn, ms);
  }

  /* ═══ WIDGET CRUD ═══ */
  function addWidget(type) {
    if (!isEditable) return;
    const atom = ATOMS[type];
    if (!atom) return;
    const w = { type, x: 4, y: 4 };
    if (atom.font) w.font = atom.font;
    if (type === 'label') w.text = 'Text';
    if (['line_h','cpu_bar','ram_bar_gfx','disk_bar'].includes(type)) { w.w = 60; w.h = 6; }
    if (type === 'line_v') { w.w = 1; w.h = 20; }
    if (type === 'rect') { w.w = 40; w.h = 20; }
    localWidgets = [...localWidgets, w];
    sel = localWidgets.length - 1;
    scheduleCommit();
  }

  function removeWidget() {
    if (sel < 0 || !isEditable) return;
    localWidgets = localWidgets.filter((_, i) => i !== sel);
    sel = -1;
    scheduleCommit();
  }

  /* ═══ DRAG ═══ */
  function onWidgetDown(e, idx) {
    if (!isEditable) return;
    e.stopPropagation(); e.preventDefault();
    sel = idx;
    isDragging = true;
    const rect = canvasEl.getBoundingClientRect();
    const ww = localWidgets[idx];
    dragOffX = e.clientX - rect.left - ww.x * S;
    dragOffY = e.clientY - rect.top - ww.y * S;
    window.addEventListener('pointermove', onDragMove);
    window.addEventListener('pointerup', onDragEnd);
  }

  function onDragMove(e) {
    if (!isDragging || sel < 0 || !canvasEl) return;
    const rect = canvasEl.getBoundingClientRect();
    const w = localWidgets[sel];
    const atom = ATOMS[w.type] || { w: 20, h: 10 };
    let nx = Math.round((e.clientX - rect.left - dragOffX) / S / 2) * 2;
    let ny = Math.round((e.clientY - rect.top - dragOffY) / S / 2) * 2;
    nx = Math.max(0, Math.min(128 - (w.w || atom.w || 10), nx));
    ny = Math.max(0, Math.min(64 - (w.h || atom.h || 10), ny));
    localWidgets[sel] = { ...w, x: nx, y: ny };
    localWidgets = [...localWidgets];
  }

  function onDragEnd() {
    window.removeEventListener('pointermove', onDragMove);
    window.removeEventListener('pointerup', onDragEnd);
    if (isDragging) { isDragging = false; scheduleCommit(); }
  }

  /* ═══ PROPERTY EDIT ═══ */
  function updateProp(key, val) {
    if (sel < 0 || !isEditable) return;
    localWidgets[sel] = { ...localWidgets[sel], [key]: val };
    localWidgets = [...localWidgets];
    scheduleCommit();
  }

  /* ═══ COMMIT (300ms Debounce) ═══ */
  function scheduleCommit() {
    clearTimeout(_commitTimer);
    _commitTimer = setTimeout(doCommit, 300);
  }

  async function doCommit() {
    saving = true;
    try {
      await s.updateOledScreen(screenIdx, {
        type: currentScreen.type || 'system',
        name: currentScreen.name || 'Screen',
        widgets: localWidgets,
      });
    } catch (e) { console.error('[OLEDStudio] Commit:', e); }
    saving = false;
  }

  /* ═══ SCREEN MANAGEMENT ═══ */
  async function addPresetScreen(key) {
    const p = PRESETS[key];
    if (!p) return;
    await s.addOledScreen({ type: 'system', name: p.name, widgets: JSON.parse(JSON.stringify(p.widgets)) });
  }

  async function addBlankScreen() {
    await s.addOledScreen({ type: 'system', name: `Screen ${(s.oled?.screens || []).length + 1}`, widgets: [] });
  }

  async function convertToSystem() {
    const scr = currentScreen;
    let widgets;
    if (scr.type === 'clock') widgets = PRESETS.uhr.widgets;
    else if (scr.type?.startsWith('weather')) widgets = PRESETS.wetter.widgets;
    else widgets = PRESETS.system.widgets;
    await s.updateOledScreen(screenIdx, {
      type: 'system', name: scr.name || 'System',
      widgets: JSON.parse(JSON.stringify(widgets)),
    });
    _syncedIdx = -1;
  }

  /* ═══ KEYBOARD ═══ */
  function onKeyDown(e) {
    const tag = e.target?.tagName;
    if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;
    if (sel < 0 || !isEditable) return;
    const w = localWidgets[sel];
    if (!w) return;
    if (e.key === 'Delete' || e.key === 'Backspace') { removeWidget(); e.preventDefault(); }
    else if (e.key === 'ArrowLeft')  { updateProp('x', Math.max(0, w.x - 2)); e.preventDefault(); }
    else if (e.key === 'ArrowRight') { updateProp('x', Math.min(126, w.x + 2)); e.preventDefault(); }
    else if (e.key === 'ArrowUp')    { updateProp('y', Math.max(0, w.y - 2)); e.preventDefault(); }
    else if (e.key === 'ArrowDown')  { updateProp('y', Math.min(62, w.y + 2)); e.preventDefault(); }
    else if (e.key === 'Escape') { sel = -1; e.preventDefault(); }
  }

  function onBrightness(e) { const v = +e.target.value; debouncedSlider(() => s.setOledBrightness(v), 150, 'br'); }
  function onRotation(e) { const v = +e.target.value; debouncedSlider(() => s.setOledRotation(v), 150, 'rot'); }

  function onCanvasClick(e) {
    if (e.target === canvasEl || e.target.tagName === 'CANVAS' || e.target.tagName === 'svg' || e.target.classList.contains('canvas-empty')) {
      sel = -1;
    }
  }

  onDestroy(() => {
    window.removeEventListener('pointermove', onDragMove);
    window.removeEventListener('pointerup', onDragEnd);
    clearTimeout(_commitTimer);
    Object.values(_sliderTimers).forEach(clearTimeout);
  });
</script>

<svelte:window onkeydown={onKeyDown} />

<div class="page">
  <!-- Header -->
  <div class="head">
    <div>
      <h1><i class="fa-solid fa-display"></i> OLED Studio</h1>
      <span class="sub">128×64 · SSD1306 · 1-Bit Monochrom</span>
    </div>
    <div class="head-controls">
      <div class="mode-btns">
        {#each [['auto','fa-rotate','Auto'],['manual','fa-hand','Manuell'],['off','fa-power-off','Aus']] as [m, icon, lbl]}
          <button class="mode-btn" class:active={s.oled?.mode===m} onclick={()=>s.setOledMode(m)}>
            <i class="fa-solid {icon}"></i> {lbl}
          </button>
        {/each}
      </div>
      <label class="slider-compact">
        <span class="slider-label"><i class="fa-solid fa-sun"></i> Hell.</span>
        <input type="range" min="0" max="255" value={s.oled?.brightness??200} oninput={onBrightness}>
        <span class="slider-val">{s.oled?.brightness??200}</span>
      </label>
      <label class="slider-compact">
        <span class="slider-label"><i class="fa-solid fa-arrows-rotate"></i> Rotation</span>
        <input type="range" min="3" max="60" value={s.oled?.rotation_interval??10} oninput={onRotation}>
        <span class="slider-val">{s.oled?.rotation_interval??10}s</span>
      </label>
    </div>
  </div>

  <!-- Screen-Tabs -->
  <div class="tabs">
    {#each s.oled?.screens || [] as scr, i}
      <button class="tab" class:active={i===screenIdx} onclick={()=>s.selectOledScreen(i)}>
        {scr.name || scr.type}
      </button>
    {/each}
    <button class="tab tab-add" onclick={addBlankScreen}><i class="fa-solid fa-plus"></i></button>
    {#if (s.oled?.screens||[]).length > 1}
      <button class="tab tab-del" onclick={()=>s.removeOledScreen(screenIdx)}><i class="fa-solid fa-trash-can"></i></button>
    {/if}
  </div>

  <!-- Editor -->
  <div class="editor">
    <!-- PALETTE -->
    <div class="palette">
      <div class="palette-title"><i class="fa-solid fa-puzzle-piece"></i> Widgets</div>
      {#each CATS as cat}
        <button class="cat-head" onclick={()=>{ openCats[cat.id] = !openCats[cat.id]; }}>
          <i class="fa-solid {openCats[cat.id]?'fa-chevron-down':'fa-chevron-right'}" style="width:12px;font-size:9px"></i>
          <i class="fa-solid {cat.icon}" style="width:16px;font-size:11px;color:var(--accent)"></i>
          {cat.name}
        </button>
        {#if openCats[cat.id]}
          <div class="cat-items">
            {#each atomsForCat(cat.id) as [type, atom]}
              <button class="atom-btn" onclick={()=>addWidget(type)} disabled={!isEditable}
                      title="{atom.label} ({atom.w}×{atom.h}px)">
                <div class="atom-mini">
                  <img src={getMiniDataUrl(type)} alt="" width="48" height="24" />
                </div>
                <div class="atom-info">
                  <span class="atom-name">{atom.label}</span>
                  <span class="atom-meta">{atom.w}×{atom.h}px</span>
                </div>
              </button>
            {/each}
          </div>
        {/if}
      {/each}
      <div class="palette-divider"></div>
      <div class="palette-title"><i class="fa-solid fa-layer-group"></i> Vorlagen</div>
      {#each Object.entries(PRESETS) as [key, p]}
        <button class="preset-btn" onclick={()=>addPresetScreen(key)}>
          <i class="fa-solid fa-plus" style="color:var(--accent)"></i>
          {p.name}
          <span class="preset-count">{p.widgets.length}w</span>
        </button>
      {/each}
    </div>

    <!-- CANVAS -->
    <div class="canvas-col">
      {#if !isEditable && currentScreen.type}
        <div class="convert-banner">
          <i class="fa-solid fa-circle-info"></i>
          <span>«{currentScreen.type}» — nicht widget-editierbar</span>
          <button class="btn btn-accent btn-sm" onclick={convertToSystem}>Konvertieren</button>
        </div>
      {/if}
      <div class="bezel">
        <div class="canvas" bind:this={canvasEl} onclick={onCanvasClick}
             style="width:{128*S}px;height:{64*S}px">
          {#if isEditable}
            <canvas bind:this={oledEl} class="oled" width="128" height="64"
                    style="width:{128*S}px;height:{64*S}px"></canvas>
          {:else if preview}
            <img src="data:image/png;base64,{preview}" alt="OLED" class="oled" />
          {:else}
            <div class="canvas-empty">Display aus</div>
          {/if}

          {#if showGrid && isEditable}
            <svg class="grid-overlay" viewBox="0 0 128 64" preserveAspectRatio="none">
              {#each Array(8) as _, i}<line x1={i*16} y1="0" x2={i*16} y2="64" stroke="rgba(0,180,255,0.08)" stroke-width="0.25"/>{/each}
              {#each Array(4) as _, i}<line x1="0" y1={i*16} x2="128" y2={i*16} stroke="rgba(0,180,255,0.08)" stroke-width="0.25"/>{/each}
            </svg>
          {/if}

          {#if isEditable}
            {#each localWidgets as w, i}
              {@const atom = ATOMS[w.type] || { w:20, h:10 }}
              <div class="widget-handle" class:selected={sel===i} class:dragging={isDragging&&sel===i}
                   style="left:{w.x*S}px;top:{w.y*S}px;width:{(w.w||atom.w)*S}px;height:{(w.h||atom.h)*S}px"
                   onpointerdown={(e)=>onWidgetDown(e,i)}>
                {#if sel===i}<span class="widget-label">{atom.label||w.type}</span>{/if}
              </div>
            {/each}
          {/if}
        </div>
      </div>
      <div class="canvas-bar">
        <label class="canvas-check"><input type="checkbox" bind:checked={showGrid}><span>Raster</span></label>
        <span class="canvas-info">{localWidgets.length} Widgets</span>
        {#if saving}<span class="canvas-saving"><i class="fa-solid fa-circle-notch fa-spin"></i></span>{/if}
        {#if selWidget}<span class="canvas-pos">({selWidget.x}, {selWidget.y})</span>{/if}
      </div>
    </div>

    <!-- PROPERTIES -->
    <div class="props">
      {#if selWidget && isEditable}
        <div class="prop-header">
          <span class="prop-title">{selAtom?.label||selWidget.type}</span>
          <button class="prop-delete" onclick={removeWidget}><i class="fa-solid fa-trash-can"></i></button>
        </div>
        <div class="prop-section">Position</div>
        <div class="prop-grid">
          <label class="prop-label">X<input type="number" min="0" max="127" value={selWidget.x}
            oninput={e=>updateProp('x',Math.max(0,Math.min(127,+e.target.value)))}></label>
          <label class="prop-label">Y<input type="number" min="0" max="63" value={selWidget.y}
            oninput={e=>updateProp('y',Math.max(0,Math.min(63,+e.target.value)))}></label>
        </div>
        {#if selAtom?.font}
          <div class="prop-section">Schrift</div>
          <div class="font-row">
            {#each [['sm','S'],['md','M'],['lg','L'],['xl','XL']] as [f,lbl]}
              <button class="font-btn" class:active={selWidget.font===f} onclick={()=>updateProp('font',f)}>{lbl}</button>
            {/each}
          </div>
        {/if}
        {#if ['line_h','cpu_bar','ram_bar_gfx','disk_bar','rect'].includes(selWidget.type)}
          <div class="prop-section">Breite</div>
          <input class="prop-input" type="number" min="4" max="128" value={selWidget.w||60}
            oninput={e=>updateProp('w',Math.max(4,Math.min(128,+e.target.value)))}>
        {/if}
        {#if ['line_v','rect'].includes(selWidget.type)}
          <div class="prop-section">Höhe</div>
          <input class="prop-input" type="number" min="2" max="64" value={selWidget.h||20}
            oninput={e=>updateProp('h',Math.max(2,Math.min(64,+e.target.value)))}>
        {/if}
        {#if selWidget.type==='label'}
          <div class="prop-section">Text</div>
          <input class="prop-input" type="text" value={selWidget.text||''} maxlength="20"
            oninput={e=>updateProp('text',e.target.value)}>
        {/if}

        <!-- LAYERS -->
        <div class="layers">
          <div class="layer-title"><i class="fa-solid fa-layer-group"></i> Layer ({localWidgets.length})</div>
          {#each localWidgets as lw, i}
            {@const la = ATOMS[lw.type] || {}}
            <button class="layer-item" class:selected={i===sel} onclick={()=>{sel=i}}>
              <span class="layer-dot"></span>
              <span class="layer-name">{la.label||lw.type}</span>
              <span class="layer-pos">{lw.x},{lw.y}</span>
            </button>
          {/each}
        </div>
        <div class="prop-keys"><i class="fa-solid fa-keyboard"></i> Pfeiltasten ±2px · Entf · Esc</div>

      {:else if !s.oled?.screens?.length}
        <div class="prop-empty"><i class="fa-solid fa-plus-circle"></i> Erstelle einen Screen oder wähle eine Vorlage.</div>
      {:else if !isEditable}
        <div class="prop-empty"><i class="fa-solid fa-arrows-rotate"></i> Konvertiere den Screen um Widgets frei zu platzieren.</div>
      {:else}
        <div class="prop-empty"><i class="fa-solid fa-hand-pointer"></i> Klicke ein Widget links oder auf der Leinwand.</div>
      {/if}
    </div>
  </div>
</div>

<style>
  .page { display: flex; flex-direction: column; gap: 12px; }

  /* Header */
  .head { display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 10px; }
  .head h1 { font-size: 20px; font-weight: 700; display: flex; align-items: center; gap: 8px; }
  .head h1 i { color: var(--accent); }
  .sub { color: var(--text-muted); font-size: 11px; font-family: var(--mono); }
  .head-controls { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
  .mode-btns { display: flex; gap: 2px; }
  .mode-btn { padding: 4px 10px; border: 1px solid var(--border); background: var(--bg-surface); color: var(--text-muted); border-radius: 6px; cursor: pointer; font: 600 11px var(--font); transition: all .15s; display: flex; align-items: center; gap: 4px; }
  .mode-btn.active { background: var(--accent); color: #fff; border-color: var(--accent); }
  .slider-compact { display: flex; align-items: center; gap: 5px; font-size: 11px; color: var(--text-secondary); }
  .slider-label { min-width: 60px; display: flex; align-items: center; gap: 4px; }
  .slider-label i { color: var(--accent); font-size: 10px; }
  .slider-val { min-width: 26px; text-align: right; font-family: var(--mono); font-size: 10px; color: var(--text-muted); }

  /* Tabs */
  .tabs { display: flex; gap: 3px; flex-wrap: wrap; padding-bottom: 6px; border-bottom: 1px solid var(--border); }
  .tab { padding: 5px 10px; border: 1px solid var(--border); background: var(--bg-surface); color: var(--text-muted); border-radius: 8px 8px 0 0; cursor: pointer; font: 500 11px var(--font); max-width: 100px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; transition: all .15s; }
  .tab.active { background: var(--accent-dim); color: var(--accent); border-color: var(--accent); border-bottom-color: transparent; }
  .tab-add { font-size: 12px; padding: 4px 14px; }
  .tab-del { font-size: 10px; padding: 5px 8px; opacity: .4; } .tab-del:hover { opacity: 1; }

  /* Editor Layout */
  .editor { display: grid; grid-template-columns: 200px 1fr 200px; gap: 14px; min-height: 300px; }
  @media (max-width: 900px) { .editor { grid-template-columns: 1fr; } .palette, .props { max-height: 200px; overflow-y: auto; } }

  /* Palette */
  .palette { overflow-y: auto; max-height: 520px; display: flex; flex-direction: column; gap: 1px; }
  .palette::-webkit-scrollbar { width: 3px; } .palette::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
  .palette-title { font: 700 10px var(--mono); text-transform: uppercase; letter-spacing: .8px; color: var(--text-muted); padding: 10px 6px 4px; display: flex; align-items: center; gap: 6px; }
  .palette-title i { color: var(--accent); font-size: 10px; }
  .cat-head { display: flex; align-items: center; gap: 4px; padding: 5px 6px; border: none; background: none; color: var(--text-secondary); cursor: pointer; font: 600 12px var(--font); width: 100%; text-align: left; }
  .cat-head:hover { color: var(--text-primary); }
  .cat-items { display: flex; flex-direction: column; gap: 2px; padding: 2px 0 4px 4px; }

  .atom-btn { display: flex; align-items: center; gap: 8px; padding: 5px 7px; border: 1px solid transparent; background: rgba(255,255,255,0.015); border-radius: 6px; cursor: pointer; width: 100%; text-align: left; transition: all .12s; font-family: var(--font); }
  .atom-btn:hover:not(:disabled) { border-color: var(--accent); background: var(--accent-dim); }
  .atom-btn:disabled { opacity: .2; cursor: not-allowed; }
  .atom-mini { width: 48px; height: 24px; background: #000; border: 1px solid #1a1a1a; border-radius: 3px; flex-shrink: 0; overflow: hidden; }
  .atom-mini img { display: block; width: 48px; height: 24px; image-rendering: pixelated; }
  .atom-info { display: flex; flex-direction: column; gap: 1px; flex: 1; min-width: 0; }
  .atom-name { font-size: 11px; font-weight: 500; color: var(--text-primary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .atom-meta { font: 10px var(--mono); color: var(--text-muted); }

  .palette-divider { height: 1px; background: var(--border); margin: 8px 0; }
  .preset-btn { display: flex; align-items: center; gap: 6px; width: 100%; padding: 5px 8px; border: 1px dashed var(--border); background: none; color: var(--text-secondary); border-radius: 6px; cursor: pointer; font: 500 11px var(--font); text-align: left; transition: all .12s; }
  .preset-btn:hover { border-color: var(--accent); color: var(--accent); }
  .preset-count { margin-left: auto; font: 10px var(--mono); color: var(--text-muted); background: var(--bg-surface); padding: 1px 5px; border-radius: 3px; }

  /* Canvas */
  .canvas-col { display: flex; flex-direction: column; align-items: center; gap: 8px; }
  .convert-banner { display: flex; align-items: center; gap: 8px; padding: 5px 10px; background: rgba(255,176,32,0.05); border: 1px solid rgba(255,176,32,0.12); border-radius: 6px; font-size: 11px; color: var(--text-secondary); width: 100%; }
  .convert-banner i { color: var(--amber); }
  .bezel { background: #050505; padding: 6px; border-radius: 8px; border: 2px solid #222; box-shadow: 0 4px 20px rgba(0,0,0,.5); }
  .canvas { position: relative; background: #000; overflow: hidden; cursor: crosshair; touch-action: none; }
  .oled { display: block; width: 100%; height: 100%; image-rendering: pixelated; pointer-events: none; }
  .canvas-empty { width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; color: #333; font-size: 11px; }
  .grid-overlay { position: absolute; inset: 0; width: 100%; height: 100%; pointer-events: none; }
  .widget-handle { position: absolute; border: 1px dashed rgba(0,180,255,.3); cursor: move; box-sizing: border-box; z-index: 2; transition: border-color .1s; }
  .widget-handle:hover { border-color: rgba(0,180,255,.6); background: rgba(0,180,255,.04); }
  .widget-handle.selected { border: 1.5px solid var(--accent) !important; background: rgba(0,180,255,.1); z-index: 3; }
  .widget-handle.dragging { border-style: solid !important; opacity: .8; }
  .widget-label { position: absolute; top: -12px; left: 0; font: 7px var(--mono); color: var(--accent); white-space: nowrap; pointer-events: none; background: rgba(0,0,0,.7); padding: 1px 3px; border-radius: 2px; }
  .canvas-bar { display: flex; gap: 10px; align-items: center; font: 10px var(--mono); color: var(--text-muted); width: 100%; }
  .canvas-check { display: flex; align-items: center; gap: 3px; cursor: pointer; font-size: 10px; }
  .canvas-saving { color: var(--accent); }
  .canvas-pos { margin-left: auto; color: var(--accent); }

  /* Properties */
  .props { display: flex; flex-direction: column; gap: 5px; padding: 10px; background: var(--bg-surface); border: 1px solid var(--border); border-radius: var(--radius); }
  .prop-header { display: flex; justify-content: space-between; align-items: center; padding-bottom: 5px; border-bottom: 1px solid var(--border); }
  .prop-title { font-size: 13px; font-weight: 700; }
  .prop-delete { background: none; border: none; cursor: pointer; font-size: 12px; padding: 2px 4px; opacity: .4; color: var(--text-muted); } .prop-delete:hover { opacity: 1; color: var(--red); }
  .prop-empty { font-size: 11px; color: var(--text-muted); padding: 10px 2px; line-height: 1.5; display: flex; align-items: flex-start; gap: 6px; }
  .prop-empty i { color: var(--accent); margin-top: 2px; }
  .prop-section { font: 700 9px var(--mono); text-transform: uppercase; letter-spacing: .4px; color: var(--text-muted); margin-top: 5px; }
  .prop-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 5px; }
  .prop-label { display: flex; flex-direction: column; gap: 2px; font: 10px var(--font); color: var(--text-secondary); }
  .prop-label input, .prop-input { padding: 4px 5px; border: 1px solid var(--border); background: var(--bg-elevated); color: var(--text-primary); border-radius: 4px; font: 11px var(--mono); width: 100%; box-sizing: border-box; }
  .prop-input { margin-top: 2px; }
  .font-row { display: flex; gap: 3px; }
  .font-btn { padding: 3px 8px; border: 1px solid var(--border); background: var(--bg-elevated); color: var(--text-muted); border-radius: 4px; cursor: pointer; font: 700 10px var(--mono); transition: all .1s; }
  .font-btn.active { background: var(--accent); color: #fff; border-color: var(--accent); }
  .prop-keys { font: 9px var(--mono); color: var(--text-muted); margin-top: 8px; opacity: .5; display: flex; align-items: center; gap: 4px; }

  /* Layers */
  .layers { margin-top: 8px; border-top: 1px solid var(--border); padding-top: 6px; display: flex; flex-direction: column; gap: 1px; }
  .layer-title { font: 700 9px var(--mono); text-transform: uppercase; letter-spacing: .4px; color: var(--text-muted); margin-bottom: 3px; display: flex; align-items: center; gap: 4px; }
  .layer-title i { font-size: 9px; color: var(--accent); }
  .layer-item { display: flex; align-items: center; gap: 4px; padding: 3px 5px; border: none; background: none; border-radius: 4px; cursor: pointer; font: 10px var(--mono); color: var(--text-muted); text-align: left; width: 100%; transition: all .1s; }
  .layer-item:hover { background: rgba(255,255,255,.03); }
  .layer-item.selected { background: var(--accent-dim); color: var(--accent); }
  .layer-dot { width: 5px; height: 5px; border-radius: 1px; background: var(--text-muted); flex-shrink: 0; }
  .layer-item.selected .layer-dot { background: var(--accent); }
  .layer-name { flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .layer-pos { color: var(--text-muted); font-size: 9px; }
</style>
