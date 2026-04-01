<script>
  import { onMount, onDestroy } from 'svelte';
  let { state: s } = $props();

  let simLeds = $state([{r:0,g:0,b:0},{r:0,g:0,b:0},{r:0,g:0,b:0},{r:0,g:0,b:0}]);
  let simFps = $state(0);
  let simSource = $state('—');
  let timerId = null;
  let step = 0;
  let frameCount = 0;
  let fpsTimer = 0;
  const N = 4;
  const catNames = { basis: 'Basis', advanced: 'Advanced', audio: 'Audio', party: 'Party', mood: 'Stimmung' };

  /* ── Farb-Hilfsfunktionen (identisch zum Backend hsv_to_rgb) ── */
  function hsv(h,sat,v) {
    h=((h%360)+360)%360;
    const c=v*sat, x=c*(1-Math.abs((h/60)%2-1)), m=v-c;
    let r,g,b;
    if(h<60){r=c;g=x;b=0;}else if(h<120){r=x;g=c;b=0;}else if(h<180){r=0;g=c;b=x;}
    else if(h<240){r=0;g=x;b=c;}else if(h<300){r=x;g=0;b=c;}else{r=c;g=0;b=x;}
    return{r:Math.round((r+m)*255),g:Math.round((g+m)*255),b:Math.round((b+m)*255)};
  }

  /* ── Adaptive FPS basierend auf Effekt ── */
  function getTargetFps(fx) {
    if (fx === 'off') return 2;
    if (['static','warm_white','gradient','temp_reactive','load_reactive'].includes(fx)) return 4;
    if (['breathing','night_light','sunset','forest','aurora','ocean','lava','neon'].includes(fx)) return 20;
    return 24;
  }

  /* ── Simulation (1:1 Backend-Formeln) ── */
  function tick() {
    const fx = s.leds?.effect||'off';
    const br = Math.pow((s.leds?.brightness||500)/1000, 0.6);
    const spd = Math.pow((s.leds?.speed||50)/100, 1.5);
    const c = s.leds?.color||{r:0,g:100,b:255};
    const c2 = s.leds?.color2||{r:255,g:0,b:0};
    const targetFps = getTargetFps(fx);

    /* Hardware-States bevorzugen (kommen via WebSocket) */
    const hw = s.leds?.led_states;
    if (hw && Array.isArray(hw) && hw.length === N && hw.some(l=>l.r||l.g||l.b) && fx !== 'off') {
      simLeds = hw.map(l => ({
        r: Math.round((l.r||0)*br),
        g: Math.round((l.g||0)*br),
        b: Math.round((l.b||0)*br)
      }));
      simSource = 'Live HW';
      countFps();
      scheduleTick(targetFps);
      return;
    }

    /* Lokale Simulation — Backend-identische Formeln */
    let L = Array.from({length:N}, ()=>({r:0,g:0,b:0}));
    simSource = fx === 'off' ? '—' : 'Simulation';

    if (fx === 'off') { /* schwarz */ }
    else if (fx === 'static') { L = L.map(() => ({...c})); }
    else if (fx === 'breathing') {
      const f = (Math.sin(step * 0.04 * spd) + 1) / 2;
      L = L.map(() => ({r:Math.round(c.r*f), g:Math.round(c.g*f), b:Math.round(c.b*f)}));
    }
    else if (fx === 'rainbow') {
      for (let i=0;i<N;i++) L[i] = hsv(((step*2*spd)+(i*90))%360, 1.0, 1.0);
    }
    else if (fx === 'gradient') {
      for (let i=0;i<N;i++) {
        const t=i/Math.max(1,N-1);
        const phase=Math.sin(step*0.03*spd)*0.3+0.7;
        L[i]={r:Math.round((c.r+(c2.r-c.r)*t)*phase),g:Math.round((c.g+(c2.g-c.g)*t)*phase),b:Math.round((c.b+(c2.b-c.b)*t)*phase)};
      }
    }
    else if (fx === 'candle') {
      for (let i=0;i<N;i++){const fl=0.6+Math.random()*0.4;L[i]={r:Math.round(255*fl),g:Math.round(120*fl),b:Math.round(20*fl*0.5)};}
    }
    else if (fx === 'lava') {
      const t=step*0.01*spd;
      for (let i=0;i<N;i++) L[i]=hsv(Math.abs((Math.sin(t+i*1.2)*30+Math.sin(t*0.7+i*0.8)*20)%360),0.9,0.5+Math.sin(t+i)*0.3);
    }
    else if (fx === 'aurora') {
      const t=step*0.015*spd;
      const pal=[{r:0,g:255,b:100},{r:0,g:180,b:255},{r:80,g:0,b:255},{r:0,g:255,b:180}];
      for (let i=0;i<N;i++){
        const idx=(Math.sin(t+i*0.8)+1)/2*(pal.length-1);const lo=Math.floor(idx),hi=Math.min(lo+1,pal.length-1),frac=idx-lo;
        const bright=0.4+Math.sin(t*1.3+i*2)*0.3;
        L[i]={r:Math.round((pal[lo].r+(pal[hi].r-pal[lo].r)*frac)*bright),g:Math.round((pal[lo].g+(pal[hi].g-pal[lo].g)*frac)*bright),b:Math.round((pal[lo].b+(pal[hi].b-pal[lo].b)*frac)*bright)};
      }
    }
    else if (fx === 'fire') {
      for (let i=0;i<N;i++){const h=120+Math.floor(Math.random()*136);L[i]={r:h,g:Math.max(0,h-100),b:Math.max(0,h-200)};}
    }
    else if (fx === 'ocean') {
      const t=step*0.02*spd;
      for (let i=0;i<N;i++){const w=Math.sin(t+i*1.5)*0.5+0.5;L[i]={r:0,g:Math.round(80*w),b:Math.round(180+75*w)};}
    }
    else if (fx === 'pulse') {
      const t=step*0.06*spd,pos=t%(N+2);
      for (let i=0;i<N;i++){const bright=Math.max(0,1-Math.abs(i-pos)*0.7);L[i]={r:Math.round(c.r*bright),g:Math.round(c.g*bright),b:Math.round(c.b*bright)};}
    }
    else if (fx === 'strobe') {
      const on=(step%Math.max(1,Math.floor(20/spd)))<Math.max(1,Math.floor(5/spd));
      L=L.map(()=>on?{...c}:{r:0,g:0,b:0});
    }
    else if (fx === 'police') {
      const phase=(Math.floor(step/Math.max(1,Math.floor(8/spd))))%4;
      if(phase===0){L[0]={r:255,g:0,b:0};L[1]={r:255,g:0,b:0};}
      else if(phase===2){L[2]={r:0,g:0,b:255};L[3]={r:0,g:0,b:255};}
    }
    else if (fx === 'disco') {
      if(step%Math.max(1,Math.floor(6/spd))===0) for(let i=0;i<N;i++) L[i]=hsv(Math.random()*360,1,1);
    }
    else if (fx === 'chase') {
      const pos=Math.floor(step/Math.max(1,Math.floor(4/spd)))%N;
      for(let i=0;i<N;i++) L[i]=i===pos?{...c}:{r:0,g:0,b:0};
    }
    else if (fx === 'sparkle') {
      for(let i=0;i<N;i++) L[i]=Math.random()<0.15*spd?{...c}:{r:Math.round(c.r*0.1),g:Math.round(c.g*0.1),b:Math.round(c.b*0.1)};
    }
    else if (fx === 'firework') {
      const cycle=Math.max(1,Math.floor(60/spd)),phase=step%cycle;
      if(phase===0) L=L.map(()=>({r:255,g:255,b:255}));
      else if(phase<cycle*0.3){const h=hsv(Math.random()*360,1,1);L=L.map(()=>({...h}));}
      else{const fade=Math.max(0,1-(phase-cycle*0.3)/(cycle*0.7));L=L.map(()=>({r:Math.round(c.r*fade),g:Math.round(c.g*fade),b:Math.round(c.b*fade)}));}
    }
    else if (fx === 'sunset') {
      const t=step*0.008*spd;
      const pal=[{r:255,g:60,b:0},{r:255,g:120,b:0},{r:255,g:80,b:50},{r:200,g:40,b:80}];
      for(let i=0;i<N;i++){const idx=(Math.sin(t+i*0.5)+1)/2*(pal.length-1),lo=Math.floor(idx),hi=Math.min(lo+1,pal.length-1),frac=idx-lo;
        L[i]={r:Math.round(pal[lo].r+(pal[hi].r-pal[lo].r)*frac),g:Math.round(pal[lo].g+(pal[hi].g-pal[lo].g)*frac),b:Math.round(pal[lo].b+(pal[hi].b-pal[lo].b)*frac)};}
    }
    else if (fx === 'forest') {
      const t=step*0.01*spd;
      for(let i=0;i<N;i++){const g=Math.round(80+Math.sin(t+i*1.5)*40);L[i]={r:Math.round(g*0.1),g:g,b:Math.round(g*0.2)};}
    }
    else if (fx === 'neon') {
      const t=step*0.02*spd;
      const nc=[{r:255,g:0,b:255},{r:0,g:255,b:255},{r:255,g:0,b:100},{r:100,g:0,b:255}];
      for(let i=0;i<N;i++){const ci=Math.floor((t+i*2)%nc.length),fl=0.7+Math.random()*0.3;
        L[i]={r:Math.round(nc[ci].r*fl),g:Math.round(nc[ci].g*fl),b:Math.round(nc[ci].b*fl)};}
    }
    else if (fx === 'warm_white') { L=L.map(()=>({r:255,g:180,b:100})); }
    else if (fx === 'night_light') {
      const v=0.05+Math.sin(step*0.01)*0.02;
      L=L.map(()=>({r:Math.round(255*v),g:Math.round(200*v),b:Math.round(120*v)}));
    }
    else if (fx === 'temp_reactive') {
      const temp=Math.max(30,Math.min(80,s.stats?.cpu?.temp||40)),ratio=(temp-30)/50;
      if(ratio<0.5)L=L.map(()=>({r:0,g:Math.round(255*ratio*2),b:Math.round(255*(1-ratio*2))}));
      else L=L.map(()=>({r:Math.round(255*(ratio-0.5)*2),g:Math.round(255*(1-(ratio-0.5)*2)),b:0}));
    }
    else if (fx === 'load_reactive') {
      const intensity=Math.min(100,s.stats?.cpu?.percent||10)/100;
      L=L.map(()=>({r:Math.round(c.r*intensity),g:Math.round(c.g*intensity),b:Math.round(c.b*intensity)}));
    }
    else { L=L.map(()=>({...c})); }

    simLeds = L.map(l => ({r:Math.round(l.r*br),g:Math.round(l.g*br),b:Math.round(l.b*br)}));
    step++;
    countFps();
    scheduleTick(targetFps);
  }

  function scheduleTick(fps) { if(timerId)clearTimeout(timerId); timerId=setTimeout(tick,Math.round(1000/fps)); }
  function countFps() { frameCount++; const now=performance.now(); if(now-fpsTimer>=1000){simFps=frameCount;frameCount=0;fpsTimer=now;} }

  onMount(() => { fpsTimer=performance.now(); tick(); });
  onDestroy(() => { if(timerId)clearTimeout(timerId); });

  function toHex(c){return c?'#'+[c.r,c.g,c.b].map(v=>(v||0).toString(16).padStart(2,'0')).join(''):'#0064ff';}
  function fromHex(h){return{r:parseInt(h.slice(1,3),16),g:parseInt(h.slice(3,5),16),b:parseInt(h.slice(5,7),16)};}
  function spdLabel(v){if(v<=5)return v+' (Minimal)';if(v<=20)return v+' (Sehr langsam)';if(v<=50)return v+' (Langsam)';if(v<=100)return v+' (Gemächlich)';if(v<=250)return v+' (Normal)';if(v<=500)return v+' (Schnell)';if(v<=750)return v+' (Sehr schnell)';return v+' (Ultra)';}
</script>

<div class="page">
  <div class="page-head"><h1>LED Lab</h1><p class="sub">4x WS2812B · SPI · neopixel_spi</p></div>

  <div class="card sim-card">
    <div class="strip-housing">
      {#each simLeds as led, i}
        <div class="led-mount">
          <div class="led-glow" style="background:radial-gradient(circle,rgba({led.r},{led.g},{led.b},0.4),transparent 70%)"></div>
          <div class="led-chip" style="background:rgb({led.r},{led.g},{led.b});box-shadow:0 0 12px rgba({led.r},{led.g},{led.b},0.6),0 0 32px rgba({led.r},{led.g},{led.b},0.25)">
            <span class="led-num">{i+1}</span>
          </div>
        </div>
      {/each}
    </div>
    <div class="strip-base"></div>
    <div class="sim-info">
      <span class="badge" class:badge-ok={s.ledsActive}>{s.leds?.effect||'off'}</span>
      <span class="sim-src">{simSource} · {simFps} FPS</span>
      <button class="btn" onclick={()=>s.toggleLeds()}>{s.ledsActive?'Ausschalten':'Einschalten'}</button>
    </div>
  </div>

  <div class="section"><div class="section-title">Steuerung</div>
    <div class="grid-3">
      <div class="card"><div class="card-header"><h3>Primärfarbe</h3></div>
        <div class="color-row"><input type="color" value={toHex(s.leds?.color)} oninput={(e)=>{const c=fromHex(e.target.value);s.setLedColor(c.r,c.g,c.b);}}><span class="color-hex">{toHex(s.leds?.color)}</span><div class="color-swatch" style="background:{toHex(s.leds?.color)}"></div></div>
      </div>
      <div class="card"><div class="card-header"><h3>Sekundärfarbe</h3></div>
        <div class="color-row"><input type="color" value={toHex(s.leds?.color2)} oninput={(e)=>{const c=fromHex(e.target.value);s.setLedColor2(c.r,c.g,c.b);}}><span class="color-hex">{toHex(s.leds?.color2)}</span><div class="color-swatch" style="background:{toHex(s.leds?.color2)}"></div></div>
      </div>
      <div class="card"><div class="card-header"><h3>Parameter</h3></div>
        <div class="slider-row"><label>Helligkeit</label><input type="range" min="1" max="1000" value={s.leds?.brightness||500} oninput={(e)=>s.setLedBrightness(+e.target.value)}><span class="slider-val">{s.leds?.brightness||0}</span></div>
        <div class="slider-row"><label>Speed</label><input type="range" min="1" max="1000" value={s.leds?.speed||50} oninput={(e)=>s.setLedSpeed(+e.target.value)}><span class="slider-val">{spdLabel(s.leds?.speed||0)}</span></div>
      </div>
    </div>
  </div>

  <div class="section"><div class="section-title">Effekte</div>
    {#each Object.entries(s.leds?.effects_by_category||{}) as [cat, effects]}
      <div class="effect-cat"><span class="cat-name">{catNames[cat]||cat}</span>
        <div class="effect-grid">
          {#each effects as fx}
            <button class="fx-btn" class:act={s.leds?.effect===fx} onclick={()=>s.setLedEffect(fx)}>{fx.replace(/_/g,' ')}</button>
          {/each}
        </div>
      </div>
    {/each}
  </div>

  {#if s.leds?.individual_mode !== undefined}
  <div class="section"><div class="section-title">Individuell</div>
    <div class="card">
      <label class="toggle-row"><input type="checkbox" checked={s.leds?.individual_mode} onchange={(e)=>s.setLedIndividual(e.target.checked)}><span>Individuelle LEDs</span></label>
      {#if s.leds?.individual_mode}
        <div class="individual-grid">
          {#each s.leds?.individual_colors||[] as ic, i}
            <div class="ind-led"><span class="ind-num">LED {i+1}</span><input type="color" value={toHex(ic)} oninput={(e)=>{const c=fromHex(e.target.value);s.setLedIndColor(i,c.r,c.g,c.b);}}></div>
          {/each}
        </div>
      {/if}
    </div>
  </div>
  {/if}
</div>

<style>
  .page{display:flex;flex-direction:column;gap:20px}
  .page-head h1{margin:0;font-size:1.3rem} .sub{color:var(--text-muted);font-size:.8rem;margin:2px 0 0}
  .section-title{font-size:.9rem;font-weight:600;margin-bottom:10px;color:var(--text-secondary)}
  .card{background:var(--bg-surface,#111827);border:1px solid var(--border);border-radius:12px;padding:16px}
  .card-header h3{margin:0 0 10px;font-size:.9rem}
  .grid-3{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px}
  .sim-card{padding:20px;text-align:center}
  .strip-housing{display:flex;justify-content:center;gap:24px;padding:24px 16px;background:linear-gradient(180deg,#0a0a0a,#1a1a1a);border-radius:10px;border:1px solid #333;position:relative}
  .led-mount{position:relative;width:44px;height:44px;display:flex;align-items:center;justify-content:center}
  .led-glow{position:absolute;width:80px;height:80px;border-radius:50%;top:50%;left:50%;transform:translate(-50%,-50%);pointer-events:none}
  .led-chip{width:28px;height:28px;border-radius:6px;border:2px solid #555;display:flex;align-items:center;justify-content:center;position:relative;z-index:1;transition:box-shadow .15s}
  .led-num{font-size:9px;color:rgba(255,255,255,0.5);font-weight:700}
  .strip-base{height:4px;background:linear-gradient(90deg,#222,#444,#222);border-radius:0 0 6px 6px;margin:0 20px}
  .sim-info{display:flex;align-items:center;justify-content:center;gap:12px;margin-top:12px;font-size:.8rem}
  .badge{padding:3px 10px;border-radius:20px;background:var(--bg-elevated);border:1px solid var(--border);font-size:.75rem}
  .badge-ok{border-color:var(--accent);color:var(--accent)}
  .sim-src{color:var(--text-muted);font-size:.7rem;font-family:var(--mono,monospace)}
  .btn{padding:5px 14px;border-radius:8px;background:var(--accent);color:#fff;border:none;cursor:pointer;font-size:.8rem}
  .color-row{display:flex;align-items:center;gap:8px}
  .color-row input[type=color]{width:40px;height:32px;border:none;cursor:pointer;background:none}
  .color-hex{font-family:var(--mono,monospace);font-size:.8rem;color:var(--text-muted)}
  .color-swatch{width:24px;height:24px;border-radius:6px;border:1px solid var(--border)}
  .slider-row{display:flex;align-items:center;gap:8px;margin:6px 0}
  .slider-row label{min-width:90px;font-size:.8rem;color:var(--text-secondary)}
  .slider-row input[type=range]{flex:1}
  .slider-val{min-width:70px;text-align:right;font-size:.75rem;font-family:var(--mono,monospace);color:var(--text-muted)}
  .effect-cat{margin-bottom:14px}
  .cat-name{font-size:.75rem;text-transform:uppercase;color:var(--text-muted);letter-spacing:.05em;margin-bottom:6px;display:block}
  .effect-grid{display:flex;flex-wrap:wrap;gap:6px}
  .fx-btn{padding:6px 12px;border-radius:8px;border:1px solid var(--border);background:var(--bg-surface,#111827);color:var(--text);cursor:pointer;font-size:.78rem;transition:all .15s;text-transform:capitalize}
  .fx-btn:hover{border-color:var(--accent)}
  .fx-btn.act{background:var(--accent);color:#fff;border-color:var(--accent)}
  .toggle-row{display:flex;align-items:center;gap:8px;cursor:pointer;font-size:.85rem}
  .individual-grid{display:flex;gap:12px;margin-top:12px;flex-wrap:wrap}
  .ind-led{display:flex;flex-direction:column;align-items:center;gap:4px}
  .ind-num{font-size:.7rem;color:var(--text-muted)}
</style>
