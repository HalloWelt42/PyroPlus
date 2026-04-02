<script>
  import { onMount, onDestroy } from 'svelte';
  let { state: s } = $props();

  /* ═══ TABS ═══ */
  let activeTab = $state('color');
  const tabs = [
    { id: 'temp', icon: 'fa-temperature-half', label: 'Temperatur' },
    { id: 'color', icon: 'fa-palette', label: 'Farben' },
    { id: 'anim', icon: 'fa-wand-magic-sparkles', label: 'Animationen' },
    { id: 'fun', icon: 'fa-champagne-glasses', label: 'Spielereien' },
  ];

  /* ═══ EFFEKT-KATEGORIEN ═══ */
  const tempEffects = ['temp_reactive', 'load_reactive'];
  const colorEffects = ['static', 'gradient', 'warm_white'];
  const animEffects = ['breathing', 'rainbow', 'candle', 'lava', 'aurora', 'fire', 'ocean', 'pulse', 'sunset', 'forest', 'neon', 'night_light'];
  const funEffects = ['strobe', 'police', 'disco', 'chase', 'sparkle', 'firework'];

  const effectLabels = {
    static: 'Statisch', gradient: 'Verlauf', warm_white: 'Warmweiß',
    breathing: 'Atmen', rainbow: 'Regenbogen', candle: 'Kerze', lava: 'Lava', aurora: 'Aurora',
    fire: 'Feuer', ocean: 'Ozean', pulse: 'Puls', sunset: 'Sonnenuntergang', forest: 'Wald',
    neon: 'Neon', night_light: 'Nachtlicht',
    strobe: 'Stroboskop', police: 'Polizei', disco: 'Disco', chase: 'Laufeffekt',
    sparkle: 'Funkeln', firework: 'Feuerwerk',
    temp_reactive: 'Temperatur-Reaktiv', load_reactive: 'Auslastung-Reaktiv',
  };

  /* ═══ FARB-HILFSFUNKTIONEN ═══ */
  function toHex(c) { return c ? '#' + [c.r, c.g, c.b].map(v => (v || 0).toString(16).padStart(2, '0')).join('') : '#0064ff'; }
  function fromHex(h) { return { r: parseInt(h.slice(1, 3), 16), g: parseInt(h.slice(3, 5), 16), b: parseInt(h.slice(5, 7), 16) }; }

  function spdLabel(v) { return v; }

  /* Aktiver Tab basierend auf aktuellem Effekt */
  function tabForEffect(fx) {
    if (tempEffects.includes(fx)) return 'temp';
    if (colorEffects.includes(fx)) return 'color';
    if (animEffects.includes(fx)) return 'anim';
    if (funEffects.includes(fx)) return 'fun';
    return 'color';
  }

  let _initialized = false;
  $effect(() => {
    if (!_initialized && s.leds?.effect) {
      activeTab = tabForEffect(s.leds.effect);
      _initialized = true;
    }
  });

  /* ═══════════════════════════════════════════════════════
     LOKALE LED-SIMULATION (~20 FPS, gleiche Formeln wie HW-Proxy)
     ═══════════════════════════════════════════════════════ */
  const N = 4;
  let simLeds = $state([{r:0,g:0,b:0},{r:0,g:0,b:0},{r:0,g:0,b:0},{r:0,g:0,b:0}]);
  let simFps = $state(0);
  let _rafId = 0;
  let _step = 0;
  let _frameCount = 0;
  let _fpsTime = 0;
  let _lastFrame = 0;
  const FRAME_MS = 1000 / 25; // 25 FPS wie Hardware-Proxy


  function hsv(h,sat,v) {
    h=((h%360)+360)%360;
    const c=v*sat, x=c*(1-Math.abs((h/60)%2-1)), m=v-c;
    let r,g,b;
    if(h<60){r=c;g=x;b=0;}else if(h<120){r=x;g=c;b=0;}else if(h<180){r=0;g=c;b=x;}
    else if(h<240){r=0;g=x;b=c;}else if(h<300){r=x;g=0;b=c;}else{r=c;g=0;b=x;}
    return{r:Math.round((r+m)*255),g:Math.round((g+m)*255),b:Math.round((b+m)*255)};
  }

  function simTick(now) {
    _rafId = requestAnimationFrame(simTick);
    if (now - _lastFrame < FRAME_MS) return;
    _lastFrame = now;

    const fx = s.leds?.effect || 'off';
    const br = Math.pow((s.leds?.brightness || 500) / 1000, 0.6);
    const spd = Math.pow((s.leds?.speed || 50) / 100, 1.5);
    const c = s.leds?.color || {r:0,g:100,b:255};
    const c2 = s.leds?.color2 || {r:255,g:0,b:0};
    const step = _step;

    // Hardware-States bevorzugen bei: reaktive Effekte, individuelle LEDs
    const hw = s.leds?.led_states;
    if (hw?.length === N && (tempEffects.includes(fx) || s.leds?.individual_mode)) {
      simLeds = hw.map(l => ({r:l.r||0, g:l.g||0, b:l.b||0}));
      s.setLedDisplay(simLeds, true);
      _step++; countFps(now); return;
    }

    let L = Array.from({length:N}, ()=>({r:0,g:0,b:0}));

    if (fx === 'off') { /* schwarz */ }
    else if (fx === 'static') { L = L.map(() => ({...c})); }
    else if (fx === 'breathing') {
      const f = (Math.sin(step*0.04*spd)+1)/2;
      L = L.map(()=>({r:Math.round(c.r*f),g:Math.round(c.g*f),b:Math.round(c.b*f)}));
    }
    else if (fx === 'rainbow') { for(let i=0;i<N;i++) L[i]=hsv(((step*2*spd)+(i*90))%360,1,1); }
    else if (fx === 'gradient') {
      for(let i=0;i<N;i++){const t=i/(N-1);const ph=Math.sin(step*0.03*spd)*0.3+0.7;L[i]={r:Math.round((c.r+(c2.r-c.r)*t)*ph),g:Math.round((c.g+(c2.g-c.g)*t)*ph),b:Math.round((c.b+(c2.b-c.b)*t)*ph)};}
    }
    else if (fx === 'candle') { for(let i=0;i<N;i++){const fl=0.6+Math.random()*0.4;L[i]={r:Math.round(255*fl),g:Math.round(120*fl),b:Math.round(20*fl*0.5)};} }
    else if (fx === 'lava') {
      const t=step*0.01*spd;
      for(let i=0;i<N;i++) L[i]=hsv(Math.abs((Math.sin(t+i*1.2)*30+Math.sin(t*0.7+i*0.8)*20)%360),0.9,0.5+Math.sin(t+i)*0.3);
    }
    else if (fx === 'aurora') {
      const t=step*0.015*spd;
      const pal=[{r:0,g:255,b:100},{r:0,g:180,b:255},{r:80,g:0,b:255},{r:0,g:255,b:180}];
      for(let i=0;i<N;i++){const idx=(Math.sin(t+i*0.8)+1)/2*(pal.length-1);const lo=Math.floor(idx),hi=Math.min(lo+1,pal.length-1),frac=idx-lo;const bright=0.4+Math.sin(t*1.3+i*2)*0.3;L[i]={r:Math.round((pal[lo].r+(pal[hi].r-pal[lo].r)*frac)*bright),g:Math.round((pal[lo].g+(pal[hi].g-pal[lo].g)*frac)*bright),b:Math.round((pal[lo].b+(pal[hi].b-pal[lo].b)*frac)*bright)};}
    }
    else if (fx === 'fire') { for(let i=0;i<N;i++){const h=120+Math.floor(Math.random()*136);L[i]={r:h,g:Math.max(0,h-100),b:Math.max(0,h-200)};} }
    else if (fx === 'ocean') { const t=step*0.02*spd; for(let i=0;i<N;i++){const w=Math.sin(t+i*1.5)*0.5+0.5;L[i]={r:0,g:Math.round(80*w),b:Math.round(180+75*w)};} }
    else if (fx === 'pulse') { const t=step*0.06*spd,pos=t%(N+2); for(let i=0;i<N;i++){const b2=Math.max(0,1-Math.abs(i-pos)*0.7);L[i]={r:Math.round(c.r*b2),g:Math.round(c.g*b2),b:Math.round(c.b*b2)};} }
    else if (fx === 'strobe') { const on=(step%Math.max(1,Math.floor(20/spd)))<Math.max(1,Math.floor(5/spd)); L=L.map(()=>on?{...c}:{r:0,g:0,b:0}); }
    else if (fx === 'police') { const ph=(Math.floor(step/Math.max(1,Math.floor(8/spd))))%4; if(ph===0){L[0]={r:255,g:0,b:0};L[1]={r:255,g:0,b:0};}else if(ph===2){L[2]={r:0,g:0,b:255};L[3]={r:0,g:0,b:255};} }
    else if (fx === 'disco') { if(step%Math.max(1,Math.floor(6/spd))===0) for(let i=0;i<N;i++) L[i]=hsv(Math.random()*360,1,1); }
    else if (fx === 'chase') { const pos=Math.floor(step/Math.max(1,Math.floor(4/spd)))%N; for(let i=0;i<N;i++) L[i]=i===pos?{...c}:{r:0,g:0,b:0}; }
    else if (fx === 'sparkle') { for(let i=0;i<N;i++) L[i]=Math.random()<0.15*spd?{...c}:{r:Math.round(c.r*0.1),g:Math.round(c.g*0.1),b:Math.round(c.b*0.1)}; }
    else if (fx === 'firework') { const cycle=Math.max(1,Math.floor(60/spd)),phase=step%cycle; if(phase===0)L=L.map(()=>({r:255,g:255,b:255}));else if(phase<cycle*0.3){const h=hsv(Math.random()*360,1,1);L=L.map(()=>({...h}));}else{const fade=Math.max(0,1-(phase-cycle*0.3)/(cycle*0.7));L=L.map(()=>({r:Math.round(c.r*fade),g:Math.round(c.g*fade),b:Math.round(c.b*fade)}));} }
    else if (fx === 'sunset') { const t=step*0.008*spd; const pal=[{r:255,g:60,b:0},{r:255,g:120,b:0},{r:255,g:80,b:50},{r:200,g:40,b:80}]; for(let i=0;i<N;i++){const idx=(Math.sin(t+i*0.5)+1)/2*(pal.length-1),lo=Math.floor(idx),hi=Math.min(lo+1,pal.length-1),frac=idx-lo;L[i]={r:Math.round(pal[lo].r+(pal[hi].r-pal[lo].r)*frac),g:Math.round(pal[lo].g+(pal[hi].g-pal[lo].g)*frac),b:Math.round(pal[lo].b+(pal[hi].b-pal[lo].b)*frac)};} }
    else if (fx === 'forest') { const t=step*0.01*spd; for(let i=0;i<N;i++){const g=Math.round(80+Math.sin(t+i*1.5)*40);L[i]={r:Math.round(g*0.1),g:g,b:Math.round(g*0.2)};} }
    else if (fx === 'neon') { const t=step*0.02*spd; const nc=[{r:255,g:0,b:255},{r:0,g:255,b:255},{r:255,g:0,b:100},{r:100,g:0,b:255}]; for(let i=0;i<N;i++){const ci=Math.floor((t+i*2)%nc.length),fl=0.7+Math.random()*0.3;L[i]={r:Math.round(nc[ci].r*fl),g:Math.round(nc[ci].g*fl),b:Math.round(nc[ci].b*fl)};} }
    else if (fx === 'warm_white') { L=L.map(()=>({r:255,g:180,b:100})); }
    else if (fx === 'night_light') { const v=0.05+Math.sin(step*0.01)*0.02; L=L.map(()=>({r:Math.round(255*v),g:Math.round(200*v),b:Math.round(120*v)})); }
    else { L=L.map(()=>({...c})); }

    simLeds = L.map(l => ({r:Math.round(l.r*br),g:Math.round(l.g*br),b:Math.round(l.b*br)}));
    s.setLedDisplay(simLeds, true);
    _step++;
    countFps(now);
  }

  function countFps(now) {
    _frameCount++;
    if (now - _fpsTime >= 1000) { simFps = _frameCount; _frameCount = 0; _fpsTime = now; }
  }

  onMount(() => { _fpsTime = performance.now(); _rafId = requestAnimationFrame(simTick); s.setSimActive(true); });
  onDestroy(() => { if (_rafId) cancelAnimationFrame(_rafId); s.setSimActive(false); });
</script>

<div class="layout">
  <div class="content">
    <!-- ═══ LINKS: LED-Vorschau + Steuerung ═══ -->
    <div class="panel">
      <div class="fan-header">
        <i class="fa-solid fa-lightbulb fan-icon"></i>
        <div>
          <div class="fan-title">LED-Steuerung</div>
          <div class="fan-sub">4× WS2812B · SPI · neopixel_spi</div>
        </div>
        <div class="fan-badge" class:on={s.ledsActive}>
          {s.leds?.effect || 'off'}
        </div>
      </div>

      <!-- LED-Visualisierung (lokale Simulation) -->
      <div class="led-preview">
        <div class="led-strip">
          {#each simLeds as led, i}
            <div class="led-mount">
              <div class="led-glow" style="background:radial-gradient(circle, rgba({led.r},{led.g},{led.b},0.5), transparent 70%)"></div>
              <div class="led-chip" style="background:rgb({led.r},{led.g},{led.b});box-shadow:0 0 12px rgba({led.r},{led.g},{led.b},0.6), 0 0 30px rgba({led.r},{led.g},{led.b},0.3)">
                <span class="led-num">{i + 1}</span>
              </div>
            </div>
          {/each}
        </div>
        <div class="led-fps">{simFps} FPS</div>
      </div>

      <!-- Globale Parameter -->
      <div class="param-section">
        <div class="ctrl">
          <div class="ctrl-row">
            <span><i class="fa-solid fa-sun"></i> Helligkeit</span>
            <input type="range" min="1" max="1000" value={s.leds?.brightness || 500} oninput={(e) => s.setLedBrightness(+e.target.value)}>
            <span class="ctrl-val">{s.leds?.brightness || 0}</span>
          </div>
          <div class="ctrl-row">
            <span><i class="fa-solid fa-gauge-high"></i> Geschwindigkeit</span>
            <input type="range" min="1" max="1000" value={s.leds?.speed || 50} oninput={(e) => s.setLedSpeed(+e.target.value)}>
            <span class="ctrl-val">{spdLabel(s.leds?.speed || 0)}</span>
          </div>
        </div>
      </div>

      <!-- Farben (nur bei passenden Effekten) -->
      {#if !tempEffects.includes(s.leds?.effect) && s.leds?.effect !== 'off'}
        <div class="color-section">
          <div class="color-row">
            <span class="color-label">Primärfarbe</span>
            <input type="color" value={toHex(s.leds?.color)} oninput={(e) => { const c = fromHex(e.target.value); s.setLedColor(c.r, c.g, c.b); }}>
            <div class="color-swatch" style="background:{toHex(s.leds?.color)}"></div>
            <span class="color-hex">{toHex(s.leds?.color)}</span>
          </div>
          <div class="color-row">
            <span class="color-label">Sekundärfarbe</span>
            <input type="color" value={toHex(s.leds?.color2)} oninput={(e) => { const c = fromHex(e.target.value); s.setLedColor2(c.r, c.g, c.b); }}>
            <div class="color-swatch" style="background:{toHex(s.leds?.color2)}"></div>
            <span class="color-hex">{toHex(s.leds?.color2)}</span>
          </div>
        </div>
      {/if}

      <!-- System-Info bei reaktiven Effekten -->
      {#if tempEffects.includes(s.leds?.effect)}
        <div class="reactive-info">
          <div class="reactive-chip"><i class="fa-solid fa-temperature-half"></i> {(s.stats?.cpu?.temp || 0).toFixed(1)}°C</div>
          <div class="reactive-chip"><i class="fa-solid fa-microchip"></i> {(s.stats?.cpu?.percent || 0).toFixed(0)}% CPU</div>
        </div>
      {/if}

      <!-- Ein/Aus -->
      <div class="power-section">
        <button class="power-btn" class:on={s.ledsActive} onclick={() => s.toggleLeds()}>
          <i class="fa-solid {s.ledsActive ? 'fa-toggle-on' : 'fa-toggle-off'}"></i>
          {s.ledsActive ? 'LEDs ausschalten' : 'LEDs einschalten'}
        </button>
      </div>
    </div>

    <!-- ═══ RECHTS: Effekt-Auswahl ═══ -->
    <div class="panel">
      <div class="fan-header">
        <i class="fa-solid fa-wand-magic-sparkles fan-icon"></i>
        <div>
          <div class="fan-title">Effekte</div>
          <div class="fan-sub">{effectLabels[s.leds?.effect] || s.leds?.effect || 'Aus'}</div>
        </div>
      </div>

      <!-- LED-Zuordnung (gleicher Schalter wie auf Lüfterseite) -->
      <div class="led-mode-switch">
        <span class="led-mode-label">LED-Farbe bestimmt durch</span>
        <div class="led-mode-btns">
          <button class="led-mode-btn" class:active={['temp_reactive','load_reactive'].includes(s.leds?.effect)} onclick={() => s.setLedEffect('temp_reactive')}>
            <i class="fa-solid fa-temperature-half"></i> Temperatur
          </button>
          <button class="led-mode-btn" class:active={!['temp_reactive','load_reactive'].includes(s.leds?.effect)} onclick={() => { if (['temp_reactive','load_reactive'].includes(s.leds?.effect)) s.setLedEffect('static'); }}>
            <i class="fa-solid fa-palette"></i> LED-Steuerung
          </button>
        </div>
      </div>

      {#if ['temp_reactive','load_reactive'].includes(s.leds?.effect)}
        <!-- Temperatur-Modus aktiv — keine Effekt-Auswahl nötig -->
        <div class="temp-mode-info">
          <div class="temp-mode-title"><i class="fa-solid fa-temperature-half"></i> Temperatur-Modus aktiv</div>
          <div class="temp-mode-desc">Die LED-Farben werden automatisch anhand der CPU-Temperatur berechnet. Um manuelle Effekte zu nutzen, wechsle zu "LED-Steuerung".</div>
          <div class="reactive-info">
            <div class="reactive-chip"><i class="fa-solid fa-temperature-half"></i> {(s.stats?.cpu?.temp || 0).toFixed(1)}°C</div>
            <div class="reactive-chip"><i class="fa-solid fa-microchip"></i> {(s.stats?.cpu?.percent || 0).toFixed(0)}% CPU</div>
          </div>
        </div>
      {:else}
        <!-- Themen-Tabs (nur bei manueller Steuerung) -->
        <div class="theme-tabs">
          {#each tabs.filter(t => t.id !== 'temp') as tab}
            <button class="theme-tab" class:active={activeTab === tab.id} onclick={() => activeTab = tab.id}>
              <i class="fa-solid {tab.icon}"></i>
              <span>{tab.label}</span>
            </button>
          {/each}
        </div>

      <!-- Effekt-Grid -->
      <div class="effect-area">
        {#if activeTab === 'temp'}
          <div class="effect-desc">LEDs reagieren auf Systemwerte. Farbe und Intensität werden automatisch berechnet.</div>
          <div class="effect-grid">
            {#each tempEffects as fx}
              <button class="effect-btn" class:active={s.leds?.effect === fx} onclick={() => s.setLedEffect(fx)}>
                <i class="fa-solid {fx === 'temp_reactive' ? 'fa-temperature-half' : 'fa-microchip'}"></i>
                <span>{effectLabels[fx]}</span>
              </button>
            {/each}
          </div>

        {:else if activeTab === 'color'}
          <div class="effect-desc">Feste Farben — über die Farbwähler links einstellbar.</div>
          <div class="effect-grid">
            {#each colorEffects as fx}
              <button class="effect-btn" class:active={s.leds?.effect === fx} onclick={() => s.setLedEffect(fx)}>
                <span>{effectLabels[fx]}</span>
              </button>
            {/each}
          </div>

          <!-- Individuelle LEDs -->
          {#if s.leds?.individual_mode !== undefined}
            <div class="individual-section">
              <div class="ctrl-row">
                <span>Individuelle LEDs</span>
                <button class="tog" class:on={s.leds?.individual_mode} onclick={() => s.setLedIndividual(!s.leds?.individual_mode)} aria-label="Individuell"></button>
              </div>
              {#if s.leds?.individual_mode}
                <div class="ind-grid">
                  {#each s.leds?.individual_colors || [] as ic, i}
                    <div class="ind-led">
                      <span class="ind-num">LED {i + 1}</span>
                      <input type="color" value={toHex(ic)} oninput={(e) => { const c = fromHex(e.target.value); s.setLedIndColor(i, c.r, c.g, c.b); }}>
                    </div>
                  {/each}
                </div>
              {/if}
            </div>
          {/if}

        {:else if activeTab === 'anim'}
          <div class="effect-desc">Animierte Lichteffekte — Geschwindigkeit über den Regler links steuerbar.</div>
          <div class="effect-grid">
            {#each animEffects as fx}
              <button class="effect-btn" class:active={s.leds?.effect === fx} onclick={() => s.setLedEffect(fx)}>
                <span>{effectLabels[fx]}</span>
              </button>
            {/each}
          </div>

        {:else if activeTab === 'fun'}
          <div class="effect-desc">Party- und Spaßeffekte.</div>
          <div class="effect-grid">
            {#each funEffects as fx}
              <button class="effect-btn" class:active={s.leds?.effect === fx} onclick={() => s.setLedEffect(fx)}>
                <span>{effectLabels[fx]}</span>
              </button>
            {/each}
          </div>
        {/if}
      </div>
      {/if}
    </div>
  </div>
</div>

<style>
  .layout { display: flex; flex-direction: column; height: 100%; }
  .content {
    display: grid; grid-template-columns: 1fr 1fr; gap: 12px;
    flex: 1; min-height: 0;
    grid-template-rows: 1fr;
  }
  .panel {
    background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--radius);
    padding: 14px; display: flex; flex-direction: column; gap: 12px; overflow-y: auto;
  }

  /* Header (gleich wie Lüfterseite) */
  .fan-header { display: flex; align-items: flex-start; gap: 10px; padding-bottom: 1em; }
  .fan-icon { font-size: var(--fs-xl); color: var(--accent); line-height: 1; margin-top: 2px; }
  .fan-title { font: 700 var(--fs-xl) var(--font); line-height: 1; }
  .fan-sub { font: 500 var(--fs-sm) var(--mono); color: var(--text-muted); }
  .fan-badge { margin-left: auto; padding: 6px 14px; border-radius: 99px; background: rgba(255,255,255,0.04); border: 1px solid var(--border); font: 500 var(--fs-sm) var(--mono); color: var(--text-muted); }
  .fan-badge.on { color: var(--green); border-color: rgba(0,232,138,0.2); background: rgba(0,232,138,0.06); }

  /* LED-Vorschau */
  .led-preview {
    background: #000; border-radius: var(--radius); border: 1px solid #222;
    padding: 20px; display: flex; justify-content: center;
  }
  .led-strip { display: flex; gap: 24px; }
  .led-mount { position: relative; width: 48px; height: 48px; display: flex; align-items: center; justify-content: center; }
  .led-glow { position: absolute; width: 80px; height: 80px; border-radius: 50%; top: 50%; left: 50%; transform: translate(-50%,-50%); pointer-events: none; }
  .led-chip { width: 28px; height: 28px; border-radius: 6px; border: 2px solid #555; display: flex; align-items: center; justify-content: center; position: relative; z-index: 1; }
  .led-num { font: 700 9px var(--mono); color: rgba(255,255,255,0.4); }
  .led-fps { font: 500 10px var(--mono); color: var(--text-muted); text-align: center; margin-top: 8px; }

  /* Steuerung */
  .ctrl { display: flex; flex-direction: column; gap: 8px; }
  .ctrl-row { display: flex; align-items: center; gap: 10px; font: 500 var(--fs-sm) var(--font); color: var(--text-secondary); }
  .ctrl-row span:first-child { min-width: 140px; display: flex; align-items: center; gap: 6px; white-space: nowrap; }
  .ctrl-row span:first-child i { color: var(--accent); }
  .ctrl-row input[type=range] { flex: 1; }
  .ctrl-val { font: 600 var(--fs-sm) var(--mono); color: var(--text-primary); background: var(--bg-deep); padding: 3px 10px; border-radius: var(--radius-sm); min-width: 60px; text-align: center; }

  /* Farben */
  .color-section { display: flex; flex-direction: column; gap: 10px; }
  .color-row { display: flex; align-items: center; gap: 12px; }
  .color-label { font: 500 var(--fs-sm) var(--font); color: var(--text-secondary); min-width: 120px; }
  .color-row input[type=color] { width: 48px; height: 36px; }
  .color-swatch { width: 36px; height: 36px; border-radius: var(--radius-sm); border: 1px solid var(--border); }
  .color-hex { font: 500 var(--fs-sm) var(--mono); color: var(--text-muted); }

  /* Reaktive Info */
  .reactive-info { display: flex; justify-content: center; gap: 12px; }
  .reactive-chip {
    display: flex; align-items: center; gap: 6px;
    padding: 6px 14px; border-radius: 99px;
    background: rgba(0,180,255,0.08); border: 1px solid var(--border-accent);
    font: 500 var(--fs-sm) var(--mono); color: var(--accent);
  }

  /* Ein/Aus */
  .power-section { margin-top: auto; }
  .power-btn {
    width: 100%; height: 42px; border-radius: var(--radius-sm);
    border: 1px solid var(--border); background: var(--bg-elevated);
    color: var(--text-muted); font: 500 var(--fs-sm) var(--font);
    cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 8px;
  }
  .power-btn.on { border-color: var(--green); color: var(--green); background: rgba(0,232,138,0.06); }

  /* Themen-Tabs */
  .theme-tabs { display: flex; gap: 6px; }
  .theme-tab {
    flex: 1; padding: 10px 8px; border-radius: var(--radius-sm);
    border: 1px solid var(--border); background: var(--bg-elevated);
    color: var(--text-muted); font: 500 var(--fs-sm) var(--font);
    cursor: pointer; display: flex; flex-direction: column; align-items: center; gap: 4px;
    transition: all 150ms;
  }
  .theme-tab i { font-size: var(--fs-lg); }
  .theme-tab:hover { border-color: var(--text-muted); }
  .theme-tab.active { background: var(--accent-dim); border-color: var(--accent); color: var(--accent); }

  /* Effekt-Bereich */
  .effect-area { flex: 1; display: flex; flex-direction: column; gap: 12px; }
  .effect-desc { font: 500 var(--fs-sm) var(--font); color: var(--text-muted); }
  .effect-grid { display: flex; flex-wrap: wrap; gap: 8px; }
  .effect-btn {
    padding: 10px 16px; border-radius: var(--radius-sm);
    border: 1px solid var(--border); background: var(--bg-elevated);
    color: var(--text-secondary); font: 500 var(--fs-sm) var(--font);
    cursor: pointer; display: flex; align-items: center; gap: 8px;
    transition: all 150ms;
  }
  .effect-btn:hover { border-color: var(--text-muted); }
  .effect-btn.active { background: var(--accent); color: #fff; border-color: var(--accent); }

  /* Individuelle LEDs */
  .individual-section { margin-top: 12px; padding-top: 12px; border-top: 1px solid var(--border); }
  .ind-grid { display: flex; gap: 16px; margin-top: 10px; }
  .ind-led { display: flex; flex-direction: column; align-items: center; gap: 6px; }
  .ind-num { font: 500 var(--fs-sm) var(--font); color: var(--text-muted); }

  /* Toggle */
  .tog { width: 36px; height: 20px; border-radius: 10px; border: none; background: rgba(255,255,255,0.1); cursor: pointer; position: relative; transition: background var(--tr); flex-shrink: 0; }
  .tog.on { background: var(--green); }
  .tog::after { content: ''; position: absolute; top: 2px; left: 2px; width: 16px; height: 16px; border-radius: 50%; background: #fff; transition: transform var(--tr); box-shadow: 0 1px 2px rgba(0,0,0,0.3); }
  .tog.on::after { transform: translateX(16px); }

  /* Temperatur-Modus Info */
  .temp-mode-info { flex: 1; display: flex; flex-direction: column; gap: 14px; justify-content: center; align-items: center; text-align: center; }
  .temp-mode-title { font: 600 var(--fs-lg) var(--font); color: var(--text-primary); display: flex; align-items: center; gap: 8px; }
  .temp-mode-title i { color: var(--accent); }
  .temp-mode-desc { font: 500 var(--fs-sm) var(--font); color: var(--text-muted); max-width: 400px; line-height: 1.5; }

  /* LED-Zuordnung */
  .led-mode-switch { display: flex; align-items: center; gap: 10px; }
  .led-mode-label { font: 500 var(--fs-sm) var(--font); color: var(--text-muted); white-space: nowrap; }
  .led-mode-btns { display: flex; gap: 4px; flex: 1; }
  .led-mode-btn {
    flex: 1; height: 34px; border-radius: var(--radius-sm);
    border: 1px solid var(--border); background: var(--bg-elevated);
    color: var(--text-muted); font: 500 var(--fs-xs) var(--font);
    cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 6px;
    transition: all 150ms;
  }
  .led-mode-btn:hover { border-color: var(--text-muted); }
  .led-mode-btn.active { background: var(--accent-dim); border-color: var(--accent); color: var(--accent); }

  @media (max-width: 900px) { .content { grid-template-columns: 1fr; } }
</style>
