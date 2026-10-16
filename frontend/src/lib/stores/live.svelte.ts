/* Live-Zustand des Systems: Werte, Lüfter, LEDs und das Display, wie sie das Backend meldet.
   Der WebSocket ist der einzige Live-Kanal; Polling springt nur ein, wenn er getrennt ist.
   Alle Änderungen gehen an das Backend; die Antwort setzt den Zustand. Keine zweite Wahrheit. */

import { api, verbindeLive } from '$lib/api/client';
import type { EffectCatalog, FanFineSettings, FanState, LedState, OledLive, Rgb, Stats, SystemState, WsMessage, HwProxyHealth } from '$lib/api/types';
import { ui } from './ui.svelte';

const LEER_RGB: Rgb = { r: 0, g: 0, b: 0 };

class LiveStore {
  verbunden = $state(false);
  stats = $state<Stats | null>(null);
  fan = $state<FanState | null>(null);
  leds = $state<LedState | null>(null);
  oled = $state<OledLive | null>(null);
  hwProxy = $state<HwProxyHealth | null>(null);
  backendVersion = $state('');
  effekte = $state<EffectCatalog>({});

  private ws: { schliessen: () => void } | null = null;
  private pollTimer: ReturnType<typeof setInterval> | null = null;

  /* Abgeleitete Werte */
  get ledFarben(): Rgb[] {
    const zustand = this.leds?.led_states;
    if (zustand && zustand.length === 4) return zustand;
    return [LEER_RGB, LEER_RGB, LEER_RGB, LEER_RGB];
  }
  get ledsAn(): boolean { return !!this.leds && this.leds.effect !== 'off'; }
  get oledAn(): boolean { return !!this.oled && this.oled.mode !== 'off'; }
  get fanAn(): boolean { return !!this.fan && this.fan.mode !== 'off'; }
  get cpuTemp(): number { return this.stats?.cpu.temp ?? 0; }

  async start(): Promise<void> {
    await api.holeToken();
    await this.ladeGesamt();
    try { this.effekte = await api.leds.effects(); } catch { /* ohne Katalog weiter */ }
    this.ws = verbindeLive((m) => this.beiNachricht(m), (v) => this.setzeVerbindung(v));
    this.pollTimer = setInterval(() => { if (!this.verbunden) void this.ladeGesamt(); }, 2000);
  }

  stop(): void {
    this.ws?.schliessen();
    if (this.pollTimer) clearInterval(this.pollTimer);
  }

  private setzeVerbindung(v: boolean): void {
    this.verbunden = v;
  }

  private beiNachricht(m: WsMessage): void {
    if (m.type !== 'stats') return;
    this.verbunden = true;
    this.stats = m.data.stats;
    this.fan = m.data.fan;
    this.leds = m.data.leds;
    this.oled = m.data.oled;
  }

  async ladeGesamt(): Promise<void> {
    try {
      const s: SystemState = await api.system.state();
      this.stats = s.stats;
      this.fan = s.fan;
      this.leds = s.leds;
      this.oled = s.oled;
      this.hwProxy = s.hw_proxy;
      this.backendVersion = s.voll ?? s.version;
      this.verbunden = true;
    } catch {
      this.verbunden = false;
    }
  }

  /* Schnellzugriff */
  async toggleLeds(): Promise<void> {
    if (this.ledsAn) { await api.quick.ledsOff(); ui.toast('LEDs aus'); }
    else { await api.quick.ledsOn(); ui.toast('LEDs ein'); }
    await this.ladeGesamt();
  }
  async toggleOled(): Promise<void> {
    if (this.oledAn) { await api.quick.oledOff(); ui.toast('Display aus'); }
    else { await api.quick.oledOn(); ui.toast('Display ein'); }
    await this.ladeGesamt();
  }
  async toggleFan(): Promise<void> {
    if (this.fanAn) { await api.quick.fanOff(); ui.toast('Lüfter aus'); }
    else { await api.quick.fanAuto(); ui.toast('Lüfter auf Automatik'); }
    await this.ladeGesamt();
  }

  /* Lüfter */
  async setFanMode(m: FanState['mode']): Promise<void> { await api.fan.mode(m); await this.ladeFan(); }
  async setFanProfile(p: string): Promise<void> { this.fan = await api.fan.profile(p); }
  async setFanManualSpeed(s: number): Promise<void> {
    await api.fan.manualSpeed(s);
    if (this.fan) this.fan = { ...this.fan, manual_speed: s };
  }
  async setFanCurve(points: { temp: number; speed: number }[]): Promise<void> { this.fan = await api.fan.curve(points); }
  async setFanSettings(s: FanFineSettings): Promise<void> { this.fan = await api.fan.settings(s); }
  /* Lokale Vorschau während des Ziehens an der Kurve; der Server bestätigt beim Loslassen */
  setzeKurveLokal(points: { temp: number; speed: number }[]): void {
    if (this.fan) this.fan = { ...this.fan, curve: points };
  }
  private async ladeFan(): Promise<void> { this.fan = await api.fan.state(); }

  /* LEDs */
  async setLedEffect(n: string): Promise<void> { await api.leds.effect(n); await this.ladeLeds(); ui.toast(`LED-Effekt: ${this.effektName(n)}`); }
  async setLedColor(c: Rgb): Promise<void> { await api.leds.color(c); if (this.leds) this.leds = { ...this.leds, color: c }; }
  async setLedColor2(c: Rgb): Promise<void> { await api.leds.color2(c); if (this.leds) this.leds = { ...this.leds, color2: c }; }
  async setLedBrightness(v: number): Promise<void> { await api.leds.brightness(v); if (this.leds) this.leds = { ...this.leds, brightness: v }; }
  async setLedSpeed(v: number): Promise<void> { await api.leds.speed(v); if (this.leds) this.leds = { ...this.leds, speed: v }; }
  async setLedIndividual(on: boolean): Promise<void> { await api.leds.individualMode(on); await this.ladeLeds(); }
  async setLedIndColor(i: number, c: Rgb): Promise<void> {
    await api.leds.individualColor(i, c);
    if (this.leds) {
      const farben = [...this.leds.individual_colors];
      farben[i] = c;
      this.leds = { ...this.leds, individual_colors: farben };
    }
  }
  private async ladeLeds(): Promise<void> { this.leds = await api.leds.state(); }
  effektName(id: string): string {
    for (const liste of Object.values(this.effekte)) {
      const e = liste.find((x) => x.id === id);
      if (e) return e.name;
    }
    return id;
  }
}

export const live = new LiveStore();
