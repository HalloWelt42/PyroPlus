<script lang="ts">
  /* Lüfterbereich: Gehäuselüfter (An/Aus nach Schwellwerten) und CPU-Lüfter (Kurve). */
  import { api } from '$lib/api/client';
  import type { CurvePoint } from '$lib/api/types';
  import { live } from '$lib/stores/live.svelte';
  import { ui } from '$lib/stores/ui.svelte';
  import Segment from '$lib/bausteine/Segment.svelte';
  import Regler from '$lib/bausteine/Regler.svelte';
  import Schalter from '$lib/bausteine/Schalter.svelte';

  const fan = $derived(live.fan);
  const echteTemp = $derived(fan?.current_temp ?? live.cpuTemp);
  const verlauf = $derived(live.stats?.history?.temp ?? []);
  const kurve = $derived(fan?.curve ?? []);
  const profil = $derived(fan?.profile ?? 'balanced');
  const modus = $derived(fan?.mode ?? 'auto');
  const sicherheit = $derived(fan?.safety_temp ?? 80);

  /* Simulation wirkt auf Lüfter und LEDs; ein Wert für beide Lüfter */
  let sim = $state<number | null>(null);
  let simTimer: ReturnType<typeof setTimeout> | null = null;
  const temp = $derived(sim ?? echteTemp);
  function simSetzen(v: number | null): void {
    sim = v;
    if (simTimer) clearTimeout(simTimer);
    simTimer = setTimeout(() => { if (v === null) void api.simulate.stop(); else void api.simulate.temp(v); }, 150);
  }

  function tempFarbe(t: number): string {
    if (t <= 25) return 'rgb(0,80,255)';
    if (t <= 35) { const f = (t - 25) / 10; return `rgb(${Math.round(200 * f)},${Math.round(80 + 175 * f)},${Math.round(255 * (1 - f))})`; }
    if (t <= 45) { const f = (t - 35) / 10; return `rgb(${Math.round(200 + 55 * f)},${Math.round(255 - 40 * f)},0)`; }
    if (t <= 55) { const f = (t - 45) / 10; return `rgb(255,${Math.round(215 - 115 * f)},0)`; }
    if (t <= 65) { const f = (t - 55) / 10; return `rgb(255,${Math.round(100 - 80 * f)},0)`; }
    return `rgb(255,${Math.round(20 * Math.max(0, 1 - (t - 65) / 10))},0)`;
  }
  const farbe = $derived(tempFarbe(temp));

  /* Gehäuselüfter: Schwellwerte lokal, Übernahme beim Loslassen */
  let ein = $state<number | null>(null);
  let aus = $state<number | null>(null);
  const einWert = $derived(ein ?? fan?.threshold_on ?? 55);
  const ausWert = $derived(aus ?? fan?.threshold_off ?? 48);
  const gehaeuseProfile: Record<string, { on: number; off: number; label: string; symbol: string }> = {
    silent: { on: 55, off: 48, label: 'Leise', symbol: 'fa-volume-xmark' },
    balanced: { on: 48, off: 42, label: 'Ausgewogen', symbol: 'fa-scale-balanced' },
    performance: { on: 42, off: 36, label: 'Leistung', symbol: 'fa-rocket' },
  };
  function gehaeuseProfil(name: string): void {
    const p = gehaeuseProfile[name];
    void live.setFanSettings({ threshold_on: p.on, threshold_off: p.off, case_profile: name });
  }
  function schwellenUebernehmen(): void {
    let on = einWert, off = ausWert;
    if (off >= on - 2) off = on - 3;
    void live.setFanSettings({ threshold_on: on, threshold_off: off, case_profile: 'custom' });
    ein = null; aus = null;
  }

  /* Temperaturdiagramm */
  const D = { w: 460, h: 260, pl: 44, pr: 66, pt: 20, pb: 28 };
  const DW = D.w - D.pl - D.pr, DH = D.h - D.pt - D.pb;
  const dMin = $derived(Math.min(30, ...verlauf) - 2);
  const dMax = $derived(Math.max(60, ...verlauf) + 2);
  const dy = (t: number) => D.pt + DH - ((t - dMin) / (dMax - dMin || 1)) * DH;
  const dx = (i: number, n: number) => D.pl + (i / Math.max(1, n - 1)) * DW;
  const ticks = $derived.by(() => { const t: number[] = []; for (let v = Math.ceil(dMin / 5) * 5; v <= dMax; v += 5) t.push(v); return t; });
  function pfad(arr: number[]): string {
    if (arr.length < 2) return '';
    return arr.map((v, i) => `${i ? 'L' : 'M'}${dx(i, arr.length).toFixed(1)},${dy(v).toFixed(1)}`).join(' ');
  }
  function flaeche(arr: number[]): string {
    const l = pfad(arr);
    return l ? `${l}L${dx(arr.length - 1, arr.length).toFixed(1)},${D.pt + DH}L${D.pl},${D.pt + DH}Z` : '';
  }

  /* Kurveneditor */
  const K = { w: 460, h: 260, pl: 44, pr: 16, pt: 24, pb: 28 };
  const KW = K.w - K.pl - K.pr, KH = K.h - K.pt - K.pb;
  const TMIN = 25, TMAX = 85;
  const kx = (t: number) => K.pl + ((t - TMIN) / (TMAX - TMIN)) * KW;
  const ky = (s: number) => K.pt + KH - (s / 100) * KH;
  const xk = (x: number) => Math.round(Math.max(TMIN, Math.min(TMAX, TMIN + ((x - K.pl) / KW) * (TMAX - TMIN))));
  const yk = (y: number) => Math.round(Math.max(0, Math.min(100, ((K.pt + KH - y) / KH) * 100)));
  const sortiert = $derived([...kurve].sort((a, b) => a.temp - b.temp));
  const kurvenPfad = $derived(sortiert.map((p, i) => `${i ? 'L' : 'M'}${kx(p.temp).toFixed(1)},${ky(p.speed).toFixed(1)}`).join(' '));
  const kurvenFlaeche = $derived(sortiert.length ? `${kurvenPfad}L${kx(sortiert[sortiert.length - 1].temp).toFixed(1)},${ky(0)}L${kx(sortiert[0].temp).toFixed(1)},${ky(0)}Z` : '');
  let kurveEl = $state<SVGSVGElement | null>(null);
  let ziehen = $state(-1);

  function punktStart(i: number, e: PointerEvent): void {
    if (profil !== 'custom') { ui.toast('Zum Verschieben erst "Eigene" wählen', 'info'); return; }
    e.preventDefault();
    ziehen = i;
    (e.currentTarget as SVGElement).setPointerCapture(e.pointerId);
  }
  function punktBewegen(e: PointerEvent): void {
    if (ziehen < 0 || !kuveEl()) return;
    const svg = kuveEl() as SVGSVGElement;
    const pt = svg.createSVGPoint();
    pt.x = e.clientX; pt.y = e.clientY;
    const p = pt.matrixTransform(svg.getScreenCTM()!.inverse());
    const punkte: CurvePoint[] = kurve.map((q, i) => (i === ziehen ? { temp: xk(p.x), speed: yk(p.y) } : q));
    live.setzeKurveLokal(punkte);
  }
  function punktEnde(): void {
    if (ziehen >= 0) void live.setFanCurve(kurve);
    ziehen = -1;
  }
  function kuveEl(): SVGSVGElement | null { return kurveEl; }
  async function punktHinzu(): Promise<void> {
    if (profil !== 'custom') await live.setFanProfile('custom');
    const p = [...(live.fan?.curve ?? [])];
    p.push({ temp: 50, speed: 50 });
    await live.setFanCurve(p);
  }
  function punktWeg(i: number): void {
    if (kurve.length <= 2) return;
    void live.setFanCurve(kurve.filter((_, k) => k !== i));
  }
  const profilLabels: Record<string, { label: string; symbol: string }> = {
    silent: { label: 'Leise', symbol: 'fa-volume-xmark' }, balanced: { label: 'Ausgewogen', symbol: 'fa-scale-balanced' },
    performance: { label: 'Leistung', symbol: 'fa-rocket' }, custom: { label: 'Eigene', symbol: 'fa-sliders' },
  };
  const drehung = $derived((fan?.current_rpm ?? 0) > 0 ? `${(3.0 - Math.min(2.6, ((fan?.current_rpm ?? 0) / 3500) * 2.6)).toFixed(1)}s` : '0s');
</script>

<div class="main">
  <header class="kopf">
    <div class="kopf-zeile">
      <h1><i class="fa-solid fa-fan"></i>Lüfter</h1>
      <span class="chip-status" class:aus={!fan?.available}><i class="fa-solid {fan?.available ? 'fa-circle-check' : 'fa-plug-circle-xmark'}"></i>{fan?.available ? 'Lüfter erreichbar' : 'Keine Lüftersteuerung'}</span>
      <span class="chip-status neutral" style="color:{farbe}" title="Temperatur, die die Regelung gerade sieht"><i class="fa-solid fa-temperature-half"></i>{temp.toFixed(1)} °C{sim !== null ? ' simuliert' : ''}</span>
      <div class="kopf-rechts">
        <div class="kopf-gruppe sim" title="Angenommene Temperatur statt der echten; Lüfter und LEDs reagieren wie im Ernstfall">
          <span class="label">Simulation</span>
          <Schalter an={sim !== null} onwahl={(an) => simSetzen(an ? 45 : null)} />
          {#if sim !== null}<Regler wert={sim} min={20} max={85} einheit=" °C" onwahl={(v) => simSetzen(v)} />{/if}
        </div>
        <button class="btn" style="width:44px;padding:0" title="Hilfe zum Lüfter" onclick={() => ui.oeffneHilfe('luefter')}><i class="fa-solid fa-question"></i></button>
      </div>
    </div>
  </header>

  <div class="inhalt">
    <section class="panel">
      <div class="panel-kopf">
        <i class="fa-solid fa-hard-drive"></i>
        <div><div class="titel">Gehäuselüfter</div><div class="unter">Schaltet nach Schwellwerten ein und aus</div></div>
        <span class="badge" class:badge-ok={fan?.case_on} class:badge-neutral={!fan?.case_on}><i class="fa-solid fa-fan" class:dreht={fan?.case_on} style="animation-duration:0.5s"></i>{fan?.case_on ? 'Läuft' : 'Aus'}</span>
      </div>
      <div class="chips">
        {#each Object.entries(gehaeuseProfile) as [k, p] (k)}
          <button class="chip" class:active={fan?.case_profile === k} title="Ein ab {p.on} °C, aus unter {p.off} °C" onclick={() => gehaeuseProfil(k)}><i class="fa-solid {p.symbol}"></i>{p.label}</button>
        {/each}
        <button class="chip" class:active={fan?.case_profile === 'custom'} title="Eigene Schwellwerte über die Regler"><i class="fa-solid fa-sliders"></i>Eigene</button>
      </div>
      <div class="diagramm">
        <svg viewBox="0 0 {D.w} {D.h}">
          <defs><linearGradient id="tempflaeche" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color={farbe} stop-opacity="0.18" /><stop offset="100%" stop-color={farbe} stop-opacity="0.02" /></linearGradient></defs>
          {#each ticks as t (t)}<line x1={D.pl} y1={dy(t)} x2={D.pl + DW} y2={dy(t)} class="gitter" /><text x={D.pl - 6} y={dy(t) + 4} text-anchor="end" class="achse">{t}°</text>{/each}
          <line x1={D.pl} y1={dy(einWert)} x2={D.pl + DW} y2={dy(einWert)} class="schwelle ein" /><text x={D.pl + DW + 6} y={dy(einWert) + 4} class="achse ein">{einWert}° Ein</text>
          <line x1={D.pl} y1={dy(ausWert)} x2={D.pl + DW} y2={dy(ausWert)} class="schwelle aus" /><text x={D.pl + DW + 6} y={dy(ausWert) + 4} class="achse aus">{ausWert}° Aus</text>
          {#if verlauf.length > 2}
            {#each [60, 30, 0] as vor (vor)}<text x={dx(Math.max(0, verlauf.length - 1 - vor), verlauf.length)} y={D.pt + DH + 20} text-anchor="middle" class="achse">{vor === 0 ? 'jetzt' : `-${vor} s`}</text>{/each}
            <path d={flaeche(verlauf)} fill="url(#tempflaeche)" />
            <path d={pfad(verlauf)} fill="none" stroke={farbe} stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" />
            <circle cx={dx(verlauf.length - 1, verlauf.length)} cy={dy(verlauf[verlauf.length - 1])} r="5" fill={farbe} stroke="var(--bg-card)" stroke-width="2" />
          {/if}
          {#if sim !== null}<line x1={D.pl} y1={dy(sim)} x2={D.pl + DW} y2={dy(sim)} class="simlinie" /><text x={D.pl + DW + 6} y={dy(sim) + 4} class="achse sim">{sim.toFixed(0)}°</text>{/if}
        </svg>
      </div>
      <div class="zeile"><span class="label"><i class="fa-solid fa-arrow-up" style="color:var(--red)"></i> Einschalten</span><Regler wert={einWert} min={35} max={75} einheit=" °C" titel="Ab dieser Temperatur schaltet der Gehäuselüfter ein" onwahl={(v) => (ein = v)} onende={schwellenUebernehmen} /></div>
      <div class="zeile"><span class="label"><i class="fa-solid fa-arrow-down" style="color:var(--green)"></i> Ausschalten</span><Regler wert={ausWert} min={30} max={70} einheit=" °C" titel="Unter dieser Temperatur schaltet er wieder aus; mindestens 3 Grad unter Einschalten" onwahl={(v) => (aus = v)} onende={schwellenUebernehmen} /></div>
    </section>

    <section class="panel">
      <div class="panel-kopf">
        <i class="fa-solid fa-microchip"></i>
        <div><div class="titel">CPU-Lüfter</div><div class="unter">Stufenlos nach Temperaturkurve</div></div>
        <span class="badge" class:badge-ok={(fan?.current_rpm ?? 0) > 0} class:badge-neutral={!(fan?.current_rpm ?? 0)}><i class="fa-solid fa-fan" class:dreht={(fan?.current_rpm ?? 0) > 0} style="animation-duration:{drehung}"></i>{(fan?.current_rpm ?? 0) > 0 ? `${fan?.current_rpm} RPM · ${Math.round(fan?.current_duty ?? 0)} %` : 'Steht'}</span>
      </div>
      <div class="chips">
        {#each fan?.profiles ?? [] as p (p)}
          <button class="chip" class:active={profil === p} title={p === 'custom' ? 'Eigene Kurve: Punkte ziehen, hinzufügen, Doppelklick entfernt' : 'Fertige Kurve'} onclick={() => live.setFanProfile(p)}><i class="fa-solid {profilLabels[p]?.symbol ?? 'fa-circle'}"></i>{profilLabels[p]?.label ?? p}</button>
        {/each}
      </div>
      <div class="diagramm">
        <svg bind:this={kurveEl} viewBox="0 0 {K.w} {K.h}" onpointermove={punktBewegen} onpointerup={punktEnde}>
          <defs><linearGradient id="kurvenflaeche" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="var(--accent)" stop-opacity="0.2" /><stop offset="100%" stop-color="var(--accent)" stop-opacity="0" /></linearGradient></defs>
          {#each [0, 25, 50, 75, 100] as s (s)}<line x1={K.pl} y1={ky(s)} x2={K.pl + KW} y2={ky(s)} class="gitter" /><text x={K.pl - 6} y={ky(s) + 4} text-anchor="end" class="achse">{s}%</text>{/each}
          {#each [30, 40, 50, 60, 70, 80] as t (t)}<line x1={kx(t)} y1={K.pt} x2={kx(t)} y2={K.pt + KH} class="gitter" /><text x={kx(t)} y={K.pt + KH + 20} text-anchor="middle" class="achse">{t}°</text>{/each}
          <line x1={kx(sicherheit)} y1={K.pt} x2={kx(sicherheit)} y2={K.pt + KH} class="schwelle ein" /><text x={kx(sicherheit) - 6} y={K.pt + KH - 8} text-anchor="end" class="achse ein">Notfall ab {sicherheit}°</text>
          {#if temp > TMIN}<line x1={kx(Math.min(TMAX, temp))} y1={K.pt} x2={kx(Math.min(TMAX, temp))} y2={K.pt + KH} stroke={farbe} stroke-width="1.5" stroke-dasharray="6 4" opacity="0.7" /><text x={kx(Math.min(TMAX, temp))} y={K.pt - 8} text-anchor="middle" class="achse jetzt">{temp.toFixed(1)}°</text>{/if}
          <path d={kurvenFlaeche} fill="url(#kurvenflaeche)" />
          <path d={kurvenPfad} fill="none" stroke="var(--accent)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" />
          {#each kurve as p, i (i)}
            <circle cx={kx(p.temp)} cy={ky(p.speed)} r={ziehen === i ? 10 : 7} class="punkt" class:frei={profil === 'custom'} onpointerdown={(e) => punktStart(i, e)} ondblclick={() => punktWeg(i)} role="button" tabindex="-1" />
            <text x={kx(p.temp)} y={ky(p.speed) - 13} text-anchor="middle" class="achse punkttext">{p.temp}° / {p.speed} %</text>
          {/each}
        </svg>
      </div>
      {#if profil === 'custom'}
        <div class="chips">
          <button class="chip" title="Punkt bei 50 Grad und 50 Prozent hinzufügen, dann ziehen" onclick={punktHinzu}><i class="fa-solid fa-plus"></i>Punkt</button>
          {#each sortiert as p (p.temp + '-' + p.speed)}
            <span class="chip">{p.temp}° → {p.speed} %{#if kurve.length > 2}<button class="x" title="Punkt entfernen" onclick={() => punktWeg(kurve.indexOf(p))}><i class="fa-solid fa-xmark"></i></button>{/if}</span>
          {/each}
        </div>
      {/if}
      <div class="zeile"><span class="label">Betriebsart</span>
        <Segment wert={modus} onwahl={(m) => live.setFanMode(m as 'auto' | 'manual' | 'off')} optionen={[
          { wert: 'auto', label: 'Automatik', symbol: 'fa-wand-magic-sparkles', titel: 'Leistung nach der Kurve' },
          { wert: 'manual', label: 'Manuell', symbol: 'fa-hand', titel: 'Feste Leistung über den Regler' },
          { wert: 'off', label: 'Aus', symbol: 'fa-power-off', titel: 'Lüfter aus; ab 80 Grad läuft er trotzdem' },
        ]} />
      </div>
      {#if modus === 'manual'}
        <div class="zeile"><span class="label">Leistung</span><Regler wert={fan?.manual_speed ?? 50} min={0} max={100} schritt={5} einheit=" %" titel="Feste Lüfterleistung" onwahl={(v) => live.setFanManualSpeed(v)} /></div>
      {/if}
      <div class="zeile"><span class="label">Hysterese</span><Regler wert={fan?.hysteresis ?? 3} min={1} max={10} schritt={0.5} einheit=" °C" titel="Der Lüfter regelt erst herunter, wenn die Temperatur um diesen Wert gefallen ist; verhindert Pendeln" onwahl={() => {}} onende={(v) => live.setFanSettings({ hysteresis: v })} /></div>
    </section>
  </div>
</div>

<style>
  .inhalt { flex: 1; min-height: 0; overflow-y: auto; overflow-x: clip; padding: 16px 20px; display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 16px; align-content: start; }
  .panel { background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--radius); padding: 16px; display: flex; flex-direction: column; gap: 12px; min-width: 0; }
  .panel-kopf { display: flex; align-items: center; gap: 12px; }
  .panel-kopf > i { font-size: 26px; color: var(--accent); }
  .panel-kopf .titel { font-size: var(--fs-lg); font-weight: 700; line-height: 1.1; }
  .panel-kopf .unter { font-size: var(--fs-xs); color: var(--text-muted); }
  .panel-kopf .badge { margin-left: auto; font-size: var(--fs-sm); padding: 6px 12px; }
  .diagramm { background: var(--bg-deep); border-radius: var(--radius-sm); padding: 6px; }
  .diagramm svg { width: 100%; height: auto; display: block; touch-action: none; }
  .gitter { stroke: rgba(255,255,255,0.06); }
  .achse { font: 500 13px var(--mono); fill: var(--text-muted); }
  .achse.ein { fill: var(--red); } .achse.aus { fill: var(--green); } .achse.sim { fill: var(--amber); } .achse.jetzt { fill: var(--text-primary); font-weight: 600; }
  .punkttext { font-size: 12px; }
  .schwelle { stroke-width: 1; stroke-dasharray: 5 3; opacity: 0.7; } .schwelle.ein { stroke: var(--red); } .schwelle.aus { stroke: var(--green); }
  .simlinie { stroke: var(--amber); stroke-width: 1.5; stroke-dasharray: 3 3; }
  .punkt { fill: var(--accent); stroke: var(--bg-card); stroke-width: 3; }
  .punkt.frei { cursor: grab; }
  .zeile { grid-template-columns: 130px minmax(0, 1fr); }
  .zeile .label { display: flex; align-items: center; gap: 6px; }
  .kopf-gruppe.sim { gap: 12px; }
  .chip .x { margin-left: 4px; width: 20px; height: 20px; display: inline-flex; align-items: center; justify-content: center; border-radius: 50%; color: var(--text-muted); }
  .chip .x:hover { color: var(--red); }
  .chip-status.neutral { background: rgba(255,255,255,0.06); }
  .dreht { animation: drehen 1s linear infinite; }
  @keyframes drehen { to { transform: rotate(360deg); } }
  @media (max-width: 1100px) { .inhalt { grid-template-columns: minmax(0, 1fr); } }
</style>
