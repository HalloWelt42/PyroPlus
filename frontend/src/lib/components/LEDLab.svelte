<script>
  import { onMount, onDestroy } from 'svelte';
  let { state: s } = $props();

  /* ═══ TABS ═══ */
  let activeTab = $state('temp');
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

  function spdLabel(v) {
    if (v <= 20) return 'Sehr langsam';
    if (v <= 50) return 'Langsam';
    if (v <= 100) return 'Gemächlich';
    if (v <= 250) return 'Normal';
    if (v <= 500) return 'Schnell';
    if (v <= 750) return 'Sehr schnell';
    return 'Ultra';
  }

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

      <!-- LED-Visualisierung -->
      <div class="led-preview">
        <div class="led-strip">
          {#each s.ledColors as c, i}
            <div class="led-mount">
              <div class="led-glow" style="background:radial-gradient(circle, {c.glow}, transparent 70%)"></div>
              <div class="led-chip" style="background:{c.rgb};box-shadow:0 0 12px {c.glow}, 0 0 30px {c.glow}">
                <span class="led-num">{i + 1}</span>
              </div>
            </div>
          {/each}
        </div>
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
            <span class="color-hex">{toHex(s.leds?.color)}</span>
          </div>
          <div class="color-row">
            <span class="color-label">Sekundärfarbe</span>
            <input type="color" value={toHex(s.leds?.color2)} oninput={(e) => { const c = fromHex(e.target.value); s.setLedColor2(c.r, c.g, c.b); }}>
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

      <!-- Hinweis wenn Lüfter die LEDs steuert -->
      {#if ['temp_reactive', 'load_reactive'].includes(s.leds?.effect)}
        <div class="led-source-hint">
          <i class="fa-solid fa-fan"></i>
          <span>LEDs werden von der Lüftersteuerung bestimmt</span>
          <button class="led-source-btn" onclick={() => s.setLedEffect('static')}>LED-Steuerung übernehmen</button>
        </div>
      {/if}

      <!-- Themen-Tabs -->
      <div class="theme-tabs">
        {#each tabs as tab}
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

  /* Steuerung */
  .ctrl { display: flex; flex-direction: column; gap: 8px; }
  .ctrl-row { display: flex; align-items: center; gap: 10px; font: 500 var(--fs-sm) var(--font); color: var(--text-secondary); }
  .ctrl-row span:first-child { min-width: 140px; display: flex; align-items: center; gap: 6px; white-space: nowrap; }
  .ctrl-row span:first-child i { color: var(--accent); }
  .ctrl-row input[type=range] { flex: 1; }
  .ctrl-val { font: 600 var(--fs-sm) var(--mono); color: var(--text-primary); background: var(--bg-deep); padding: 3px 10px; border-radius: var(--radius-sm); min-width: 60px; text-align: center; }

  /* Farben */
  .color-section { display: flex; gap: 16px; }
  .color-row { display: flex; align-items: center; gap: 8px; flex: 1; }
  .color-label { font: 500 var(--fs-sm) var(--font); color: var(--text-secondary); min-width: 110px; }
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

  /* LED-Quelle Hinweis */
  .led-source-hint {
    display: flex; align-items: center; gap: 8px;
    padding: 8px 12px; border-radius: var(--radius-sm);
    background: rgba(255,176,32,0.06); border: 1px solid rgba(255,176,32,0.15);
    font: 500 var(--fs-sm) var(--font); color: var(--amber);
  }
  .led-source-hint i { font-size: var(--fs-sm); }
  .led-source-hint span { flex: 1; }
  .led-source-btn {
    padding: 4px 10px; border-radius: 99px; border: 1px solid var(--accent);
    background: var(--accent-dim); color: var(--accent);
    font: 500 var(--fs-xs) var(--font); cursor: pointer; white-space: nowrap;
  }

  @media (max-width: 900px) { .content { grid-template-columns: 1fr; } }
</style>
