/* Display-Store: Bestand vom Backend plus der Entwurf, der gerade bearbeitet wird.
   Das Backend rendert jedes Bild; hier liegen nur Entwurf, Auswahl, Verlauf und
   das zuletzt gerenderte Bild mit den Rahmen der Widgets. */

import { api } from '$lib/api/client';
import type {
  Catalog, DisplayMode, DisplayModeInfo, GeocodeHit, OledBundle, OledSettingsPatch, OledState,
  Profile, Screen, SourceInfo, TemplateCatalog, WeatherLocationCreate, WeatherLocationState,
  Widget, WidgetBox, WidgetOpts, WidgetPreset,
} from '$lib/api/types';
import { freieStelle, W, H, begrenze } from '$lib/display/geometrie';
import { live } from './live.svelte';
import { ui } from './ui.svelte';

export type Speicherzustand = 'gespeichert' | 'wartet' | 'laeuft' | 'fehler';

const VERLAUF_MAX = 60;

function tief<T>(wert: T): T {
  return JSON.parse(JSON.stringify(wert)) as T;
}

function neueId(): string {
  return crypto.randomUUID().replace(/-/g, '');
}

export function leereOpts(): WidgetOpts {
  return {
    scaleX: 1, scaleY: null, prefix: '', suffix: '', decimals: null, thousands: false,
    invert: false, border: false, align: 'left', boxW: 0, width: null, height: null,
    radius: null, size: null, text: null, rotate: 0, locationId: null, bitmap: null,
  };
}

class OledStore {
  /* Bestand */
  zustand = $state<OledState | null>(null);
  screens = $state<Screen[]>([]);
  katalog = $state<Catalog | null>(null);
  vorlagen = $state<TemplateCatalog | null>(null);
  bausteine = $state<WidgetPreset[]>([]);
  profile = $state<Profile[]>([]);
  orte = $state<WeatherLocationState[]>([]);

  /* Entwurf */
  entwurf = $state<Screen | null>(null);
  auswahl = $state<string[]>([]);
  bild = $state<string | null>(null);
  boxen = $state<WidgetBox[]>([]);
  probe = $state<Widget | null>(null);
  probeBox = $state<WidgetBox | null>(null);
  simulate = $state<Record<string, number>>({});
  speicherzustand = $state<Speicherzustand>('gespeichert');
  vorschaubilder = $state<Record<string, string>>({});
  vorlagenbilder = $state<Record<string, string>>({});
  zeichnen = $state(false);
  geladen = $state(false);

  private verlauf: string[] = [];
  private verlaufIndex = -1;
  private renderTimer: ReturnType<typeof setTimeout> | null = null;
  private speicherTimer: ReturnType<typeof setTimeout> | null = null;
  private tickTimer: ReturnType<typeof setInterval> | null = null;
  private bekannteVersion = 0;
  private renderLaeuft = false;
  private renderErneut = false;

  /* Abgeleitet */
  get aktiverBildschirmId(): string | null { return this.zustand?.currentScreenId ?? live.oled?.currentScreenId ?? null; }
  get gewaehlte(): Widget[] {
    const e = this.entwurf;
    if (!e) return [];
    return e.widgets.filter((w) => this.auswahl.includes(w.id));
  }
  get erstesGewaehltes(): Widget | null { return this.gewaehlte[0] ?? null; }
  get kannRueckgaengig(): boolean { return this.verlaufIndex > 0; }
  get kannWiederholen(): boolean { return this.verlaufIndex < this.verlauf.length - 1; }

  quelle(id: string): SourceInfo | null {
    return this.katalog?.sources.find((s) => s.id === id) ?? null;
  }
  darstellung(id: DisplayMode): DisplayModeInfo | null {
    return this.katalog?.modes.find((m) => m.id === id) ?? null;
  }
  darstellungenFuer(quelle: SourceInfo | null): DisplayModeInfo[] {
    if (!this.katalog || !quelle) return [];
    return this.katalog.modes.filter((m) => m.forTypes.includes(quelle.valueType));
  }

  /* Laden */

  async laden(): Promise<void> {
    try {
      const [zustand, katalog, bausteine, profile, orte] = await Promise.all([
        api.oled.state(), api.oled.catalog(), api.oled.presets(), api.oled.profiles(), api.oled.weatherLocations(),
      ]);
      this.zustand = zustand;
      this.screens = zustand.screens;
      this.bekannteVersion = zustand.screensVersion;
      this.katalog = katalog;
      this.bausteine = bausteine;
      this.profile = profile;
      this.orte = orte;
      this.geladen = true;
      if (!this.entwurf || !this.screens.some((s) => s.id === this.entwurf?.id)) {
        this.waehle(zustand.currentScreenId ?? this.screens[0]?.id ?? null);
      }
      void this.aktualisiereVorschaubilder();
    } catch (e) {
      ui.fehler(e, 'Display laden');
    }
  }

  async ladeKatalog(): Promise<void> {
    try { this.katalog = await api.oled.catalog(); } catch (e) { ui.fehler(e, 'Katalog'); }
  }

  aktivieren(): void {
    if (this.tickTimer) return;
    this.tickTimer = setInterval(() => {
      if (!this.entwurf) return;
      this.rendernBald(0);
      if (Date.now() % 5000 < 1000) void this.aktualisiereVorschaubilder();
    }, 1000);
  }

  deaktivieren(): void {
    if (this.tickTimer) clearInterval(this.tickTimer);
    this.tickTimer = null;
  }

  /* Abgleich mit dem Live-Zustand: Bildschirmliste nachladen, wenn sich die Version ändert. */
  async abgleich(version: number): Promise<void> {
    if (version === this.bekannteVersion) return;
    this.bekannteVersion = version;
    try {
      const zustand = await api.oled.state();
      this.zustand = zustand;
      this.screens = zustand.screens;
      if (this.entwurf && this.speicherzustand === 'gespeichert') {
        const server = this.screens.find((s) => s.id === this.entwurf?.id);
        if (!server) this.waehle(zustand.currentScreenId ?? this.screens[0]?.id ?? null);
        else if (JSON.stringify(server) !== JSON.stringify(this.entwurf)) {
          this.entwurf = tief(server);
          this.auswahl = this.auswahl.filter((id) => server.widgets.some((w) => w.id === id));
          this.rendernBald(0);
        }
      }
      void this.aktualisiereVorschaubilder();
    } catch { /* nächster Abgleich */ }
  }

  /* Bildschirmwahl */

  waehle(id: string | null): void {
    const screen = this.screens.find((s) => s.id === id) ?? null;
    this.entwurf = screen ? tief(screen) : null;
    this.auswahl = [];
    this.probe = null;
    this.probeBox = null;
    this.zeichnen = false;
    this.verlauf = this.entwurf ? [JSON.stringify(this.entwurf)] : [];
    this.verlaufIndex = this.verlauf.length - 1;
    this.speicherzustand = 'gespeichert';
    this.rendernBald(0);
  }

  async neuerBildschirm(): Promise<void> {
    try {
      const neu = await api.oled.addScreen({ name: `Bildschirm ${this.screens.length + 1}`, widgets: [] });
      await this.ladeBildschirme();
      this.waehle(neu.id);
      ui.toast('Neuer Bildschirm angelegt');
    } catch (e) { ui.fehler(e, 'Bildschirm anlegen'); }
  }

  async ausVorlage(vorlageId: string): Promise<void> {
    try {
      const neu = await api.oled.addTemplateScreen(vorlageId);
      await this.ladeBildschirme();
      this.waehle(neu.id);
      ui.toast(`"${neu.name}" eingefügt`);
    } catch (e) { ui.fehler(e, 'Vorlage einfügen'); }
  }

  async duplizieren(id: string): Promise<void> {
    try {
      const kopie = await api.oled.duplicateScreen(id);
      await this.ladeBildschirme();
      this.waehle(kopie.id);
      ui.toast('Bildschirm kopiert');
    } catch (e) { ui.fehler(e, 'Kopieren'); }
  }

  async loeschen(id: string): Promise<void> {
    try {
      await api.oled.deleteScreen(id);
      await this.ladeBildschirme();
      if (this.entwurf?.id === id) this.waehle(this.zustand?.currentScreenId ?? this.screens[0]?.id ?? null);
      ui.toast('Bildschirm gelöscht');
    } catch (e) { ui.fehler(e, 'Löschen'); }
  }

  async umsortieren(ids: string[]): Promise<void> {
    try {
      this.screens = await api.oled.reorder(ids);
    } catch (e) { ui.fehler(e, 'Reihenfolge'); }
  }

  async anzeigen(id: string): Promise<void> {
    try {
      const s = await api.oled.activateScreen(id);
      if (this.zustand) this.zustand = { ...this.zustand, currentScreenId: s.currentScreenId };
      ui.toast('Wird auf dem Display gezeigt');
    } catch (e) { ui.fehler(e, 'Anzeigen'); }
  }

  async einstellungen(patch: OledSettingsPatch): Promise<void> {
    try {
      const s = await api.oled.patchSettings(patch);
      if (this.zustand) this.zustand = { ...this.zustand, mode: s.mode, brightness: s.brightness, rotationInterval: s.rotationInterval, currentScreenId: s.currentScreenId };
    } catch (e) { ui.fehler(e, 'Einstellungen'); }
  }

  async bildschirmEigenschaft(id: string, patch: Partial<Pick<Screen, 'name' | 'enabled' | 'duration'>>): Promise<void> {
    const screen = this.screens.find((s) => s.id === id);
    if (!screen) return;
    const neu = { ...tief(screen), ...patch };
    try {
      const gespeichert = await api.oled.updateScreen(id, neu);
      this.screens = this.screens.map((s) => (s.id === id ? gespeichert : s));
      if (this.entwurf?.id === id) this.entwurf = { ...this.entwurf, ...patch };
    } catch (e) { ui.fehler(e, 'Bildschirm ändern'); }
  }

  private async ladeBildschirme(): Promise<void> {
    const zustand = await api.oled.state();
    this.zustand = zustand;
    this.screens = zustand.screens;
    this.bekannteVersion = zustand.screensVersion;
    void this.aktualisiereVorschaubilder();
  }

  /* Entwurf ändern */

  aendere(fn: (s: Screen) => void, merken = true): void {
    if (!this.entwurf) return;
    const kopie = tief(this.entwurf);
    fn(kopie);
    this.entwurf = kopie;
    if (merken) this.merken();
    this.rendernBald(40);
    this.speichernBald();
  }

  merken(): void {
    if (!this.entwurf) return;
    const eintrag = JSON.stringify(this.entwurf);
    if (this.verlauf[this.verlaufIndex] === eintrag) return;
    this.verlauf = this.verlauf.slice(0, this.verlaufIndex + 1);
    this.verlauf.push(eintrag);
    if (this.verlauf.length > VERLAUF_MAX) this.verlauf.shift();
    this.verlaufIndex = this.verlauf.length - 1;
  }

  rueckgaengig(): void {
    if (!this.kannRueckgaengig) return;
    this.verlaufIndex -= 1;
    this.entwurf = JSON.parse(this.verlauf[this.verlaufIndex]) as Screen;
    this.auswahl = this.auswahl.filter((id) => this.entwurf?.widgets.some((w) => w.id === id));
    this.rendernBald(0);
    this.speichernBald();
  }

  wiederholen(): void {
    if (!this.kannWiederholen) return;
    this.verlaufIndex += 1;
    this.entwurf = JSON.parse(this.verlauf[this.verlaufIndex]) as Screen;
    this.rendernBald(0);
    this.speichernBald();
  }

  /* Widgets */

  widgetEinfuegen(widget: Widget, waehlen = true): void {
    const neu: Widget = { ...tief(widget), id: neueId() };
    if (neu.x === 0 && neu.y === 0 && this.probeBox) {
      const stelle = freieStelle(this.boxen, this.probeBox.w, this.probeBox.h);
      neu.x = stelle.x;
      neu.y = stelle.y;
    }
    this.aendere((s) => { s.widgets.push(neu); });
    if (waehlen) this.auswahl = [neu.id];
    this.zeichnen = neu.display === 'bitmap';
  }

  widgetAendern(id: string, patch: Partial<Widget>, merken = true): void {
    this.aendere((s) => {
      const w = s.widgets.find((x) => x.id === id);
      if (w) Object.assign(w, patch);
    }, merken);
  }

  optsAendern(ids: string[], patch: Partial<WidgetOpts>, merken = true): void {
    this.aendere((s) => {
      for (const w of s.widgets) if (ids.includes(w.id)) Object.assign(w.opts, patch);
    }, merken);
  }

  darstellungSetzen(ids: string[], modus: DisplayModeInfo): void {
    this.aendere((s) => {
      for (const w of s.widgets) {
        if (!ids.includes(w.id)) continue;
        const behalten = { prefix: w.opts.prefix, suffix: w.opts.suffix, decimals: w.opts.decimals, thousands: w.opts.thousands,
          text: w.opts.text, locationId: w.opts.locationId, rotate: w.opts.rotate };
        w.display = modus.id;
        w.opts = { ...leereOpts(), ...modus.defaults, ...behalten };
      }
    });
  }

  varianteAnwenden(ids: string[], opts: WidgetOpts, felder: string[]): void {
    const patch: Partial<WidgetOpts> = {};
    for (const feld of felder) {
      const wert = (opts as unknown as Record<string, unknown>)[feld];
      if (wert !== null && wert !== undefined) (patch as Record<string, unknown>)[feld] = wert;
    }
    this.optsAendern(ids, patch);
  }

  verschieben(ids: string[], dx: number, dy: number, merken = true): void {
    this.aendere((s) => {
      for (const w of s.widgets) {
        if (!ids.includes(w.id)) continue;
        w.x = begrenze(w.x + dx, 0, W - 1);
        w.y = begrenze(w.y + dy, 0, H - 1);
      }
    }, merken);
  }

  positionSetzen(ids: string[], pos: Map<string, { x: number; y: number }>, merken = true): void {
    this.aendere((s) => {
      for (const w of s.widgets) {
        const p = pos.get(w.id);
        if (p) { w.x = begrenze(p.x, 0, W - 1); w.y = begrenze(p.y, 0, H - 1); }
      }
    }, merken);
  }

  zentrieren(ids: string[]): void {
    this.aendere((s) => {
      for (const w of s.widgets) {
        if (!ids.includes(w.id)) continue;
        const box = this.boxen.find((b) => b.id === w.id);
        if (box && box.w > 0) w.x = begrenze(Math.round((W - box.w) / 2) + (w.x - box.x), 0, W - 1);
      }
    });
  }

  verteilen(ids: string[]): void {
    const boxen = ids.map((id) => this.boxen.find((b) => b.id === id)).filter((b): b is WidgetBox => !!b).sort((a, b) => a.x - b.x);
    if (boxen.length < 3) return;
    const gesamt = boxen.reduce((s, b) => s + b.w, 0);
    const luecke = Math.max(0, Math.floor((W - gesamt) / (boxen.length + 1)));
    let x = luecke;
    const pos = new Map<string, { x: number; y: number }>();
    for (const b of boxen) {
      const w = this.entwurf?.widgets.find((v) => v.id === b.id);
      if (w) pos.set(w.id, { x: x + (w.x - b.x), y: w.y });
      x += b.w + luecke;
    }
    this.positionSetzen(ids, pos);
  }

  buendig(ids: string[], kante: 'oben' | 'links'): void {
    const boxen = ids.map((id) => this.boxen.find((b) => b.id === id)).filter((b): b is WidgetBox => !!b);
    if (boxen.length < 2) return;
    const ziel = Math.min(...boxen.map((b) => (kante === 'oben' ? b.y : b.x)));
    const pos = new Map<string, { x: number; y: number }>();
    for (const b of boxen) {
      const w = this.entwurf?.widgets.find((v) => v.id === b.id);
      if (!w) continue;
      pos.set(w.id, kante === 'oben' ? { x: w.x, y: ziel + (w.y - b.y) } : { x: ziel + (w.x - b.x), y: w.y });
    }
    this.positionSetzen(ids, pos);
  }

  duplizierenWidgets(ids: string[]): void {
    const neueIds: string[] = [];
    this.aendere((s) => {
      for (const w of s.widgets.filter((x) => ids.includes(x.id))) {
        const kopie: Widget = { ...tief(w), id: neueId(), x: begrenze(w.x + 4, 0, W - 1), y: begrenze(w.y + 4, 0, H - 1) };
        s.widgets.push(kopie);
        neueIds.push(kopie.id);
      }
    });
    this.auswahl = neueIds;
  }

  entfernen(ids: string[]): void {
    this.aendere((s) => { s.widgets = s.widgets.filter((w) => !ids.includes(w.id)); });
    this.auswahl = [];
    this.zeichnen = false;
  }

  nachVorn(ids: string[]): void {
    this.aendere((s) => {
      const vorn = s.widgets.filter((w) => ids.includes(w.id));
      s.widgets = [...s.widgets.filter((w) => !ids.includes(w.id)), ...vorn];
    });
  }

  nachHinten(ids: string[]): void {
    this.aendere((s) => {
      const hinten = s.widgets.filter((w) => ids.includes(w.id));
      s.widgets = [...hinten, ...s.widgets.filter((w) => !ids.includes(w.id))];
    });
  }

  waehleWidget(id: string | null, erweitern = false): void {
    if (id === null) { this.auswahl = []; this.zeichnen = false; return; }
    if (erweitern) {
      this.auswahl = this.auswahl.includes(id) ? this.auswahl.filter((x) => x !== id) : [...this.auswahl, id];
    } else if (!this.auswahl.includes(id)) {
      this.auswahl = [id];
    }
    const w = this.entwurf?.widgets.find((x) => x.id === id);
    this.zeichnen = this.auswahl.length === 1 && w?.display === 'bitmap';
  }

  alleWaehlen(): void {
    this.auswahl = this.entwurf?.widgets.map((w) => w.id) ?? [];
    this.zeichnen = false;
  }

  /* Probe (Hinzufügen): wird im Bild mitgerendert, bis sie eingefügt oder verworfen wird. */

  setzeProbe(widget: Widget | null): void {
    this.probe = widget;
    if (!widget) this.probeBox = null;
    this.rendernBald(40);
  }

  probeEinfuegen(): void {
    if (!this.probe) return;
    const w = tief(this.probe);
    if (this.probeBox) { w.x = this.probeBox.x - (this.probeBox.x - w.x); }
    this.widgetEinfuegen(w);
    this.probe = null;
    this.probeBox = null;
    ui.toast(`"${w.name}" eingefügt`);
  }

  /* Rendern */

  rendernBald(verzoegerung: number): void {
    if (this.renderTimer) clearTimeout(this.renderTimer);
    this.renderTimer = setTimeout(() => void this.rendern(), verzoegerung);
  }

  async rendern(): Promise<void> {
    if (!this.entwurf) return;
    if (this.renderLaeuft) { this.renderErneut = true; return; }
    this.renderLaeuft = true;
    try {
      let screen = this.entwurf;
      if (this.probe) {
        const probe = tief(this.probe);
        if (this.probeBox === null) {
          const mass = await api.oled.render({ screen: { ...tief(this.entwurf), widgets: [{ ...probe, x: 0, y: 0 }] }, simulate: this.simulate });
          const box = mass.boxes[0];
          const stelle = freieStelle(this.boxen, box.w || 1, box.h || 1);
          probe.x = stelle.x;
          probe.y = stelle.y;
          this.probe = { ...this.probe, x: stelle.x, y: stelle.y };
        }
        screen = { ...tief(this.entwurf), widgets: [...this.entwurf.widgets, probe] };
      }
      const antwort = await api.oled.render({ screen, simulate: this.simulate });
      this.bild = antwort.imageBase64;
      if (this.probe) {
        this.boxen = antwort.boxes.slice(0, -1);
        this.probeBox = antwort.boxes[antwort.boxes.length - 1] ?? null;
      } else {
        this.boxen = antwort.boxes;
        this.probeBox = null;
      }
    } catch (e) {
      ui.fehler(e, 'Vorschau');
    } finally {
      this.renderLaeuft = false;
      if (this.renderErneut) { this.renderErneut = false; void this.rendern(); }
    }
  }

  async renderEinzeln(widget: Widget): Promise<{ bild: string; box: WidgetBox } | null> {
    try {
      const antwort = await api.oled.render({ screen: { id: 'probe', name: '', kind: 'widgets', widgets: [{ ...widget, x: 0, y: 0 }], locationId: null, enabled: true, duration: null }, simulate: this.simulate });
      return { bild: antwort.imageBase64, box: antwort.boxes[0] };
    } catch {
      return null;
    }
  }

  async aktualisiereVorschaubilder(): Promise<void> {
    for (const s of this.screens) {
      try {
        const antwort = await api.oled.render({ screen: s });
        this.vorschaubilder = { ...this.vorschaubilder, [s.id]: antwort.imageBase64 };
      } catch { /* nächstes Bild */ }
    }
  }

  /* Speichern */

  speichernBald(): void {
    this.speicherzustand = 'wartet';
    if (this.speicherTimer) clearTimeout(this.speicherTimer);
    this.speicherTimer = setTimeout(() => void this.speichern(), 600);
  }

  async speichern(): Promise<void> {
    if (!this.entwurf) return;
    const entwurf = tief(this.entwurf);
    this.speicherzustand = 'laeuft';
    try {
      const gespeichert = await api.oled.updateScreen(entwurf.id, entwurf);
      this.screens = this.screens.map((s) => (s.id === gespeichert.id ? gespeichert : s));
      this.bekannteVersion += 1;
      this.speicherzustand = JSON.stringify(entwurf) === JSON.stringify(this.entwurf) ? 'gespeichert' : 'wartet';
      if (this.speicherzustand === 'wartet') this.speichernBald();
    } catch (e) {
      this.speicherzustand = 'fehler';
      ui.fehler(e, 'Speichern');
    }
  }

  /* Vorlagen und Bausteine */

  async ladeVorlagen(): Promise<void> {
    if (this.vorlagen) return;
    try {
      this.vorlagen = await api.oled.templates();
      for (const t of this.vorlagen.screens) {
        try {
          const antwort = await api.oled.render({ screen: t.screen });
          this.vorlagenbilder = { ...this.vorlagenbilder, [t.id]: antwort.imageBase64 };
        } catch { /* nächste */ }
      }
    } catch (e) { ui.fehler(e, 'Vorlagen'); }
  }

  async bausteinEinfuegen(vorlageId: string): Promise<void> {
    try {
      const w = await api.oled.templateWidget(vorlageId);
      this.setzeProbe({ ...w, x: 0, y: 0 });
      await this.rendern();
      this.probeEinfuegen();
    } catch (e) { ui.fehler(e, 'Baustein'); }
  }

  async eigenenBausteinEinfuegen(preset: WidgetPreset): Promise<void> {
    const w: Widget = { id: neueId(), source: preset.source, display: preset.display, x: 0, y: 0, name: preset.name, opts: tief(preset.opts) };
    this.setzeProbe(w);
    await this.rendern();
    this.probeEinfuegen();
  }

  async alsBausteinSichern(widget: Widget, name: string): Promise<void> {
    try {
      const p = await api.oled.addPreset({ name, source: widget.source, display: widget.display, opts: tief(widget.opts) });
      this.bausteine = [...this.bausteine, p];
      ui.toast(`Baustein "${name}" gesichert`);
    } catch (e) { ui.fehler(e, 'Baustein sichern'); }
  }

  async bausteinLoeschen(id: string): Promise<void> {
    try {
      await api.oled.deletePreset(id);
      this.bausteine = this.bausteine.filter((p) => p.id !== id);
    } catch (e) { ui.fehler(e, 'Baustein löschen'); }
  }

  async bausteinUmbenennen(preset: WidgetPreset, name: string): Promise<void> {
    try {
      const neu = await api.oled.updatePreset(preset.id, { ...preset, name });
      this.bausteine = this.bausteine.map((p) => (p.id === neu.id ? neu : p));
    } catch (e) { ui.fehler(e, 'Baustein umbenennen'); }
  }

  /* Profile */

  async profilSichern(name: string): Promise<void> {
    try {
      await api.oled.saveProfile(name);
      this.profile = await api.oled.profiles();
      ui.toast(`Profil "${name}" gesichert`);
    } catch (e) { ui.fehler(e, 'Profil sichern'); }
  }

  async profilLaden(id: string): Promise<void> {
    try {
      await api.oled.applyProfile(id);
      await this.ladeBildschirme();
      this.waehle(this.zustand?.currentScreenId ?? this.screens[0]?.id ?? null);
      ui.toast('Profil geladen');
    } catch (e) { ui.fehler(e, 'Profil laden'); }
  }

  async profilLoeschen(id: string): Promise<void> {
    try {
      await api.oled.deleteProfile(id);
      this.profile = this.profile.filter((p) => p.id !== id);
    } catch (e) { ui.fehler(e, 'Profil löschen'); }
  }

  /* Wetterorte */

  async ladeOrte(): Promise<void> {
    try { this.orte = await api.oled.weatherLocations(); } catch (e) { ui.fehler(e, 'Wetterorte'); }
  }

  async ortSuchen(q: string): Promise<GeocodeHit[]> {
    try { return await api.oled.searchLocation(q); } catch (e) { ui.fehler(e, 'Ortssuche'); return []; }
  }

  async ortHinzufuegen(ort: WeatherLocationCreate): Promise<void> {
    try {
      await api.oled.addLocation(ort);
      await this.ladeOrte();
      ui.toast(`${ort.name} hinzugefügt`);
      setTimeout(() => void this.ladeOrte(), 3000);
    } catch (e) { ui.fehler(e, 'Ort hinzufügen'); }
  }

  async ortLoeschen(id: string): Promise<void> {
    try { await api.oled.deleteLocation(id); await this.ladeOrte(); } catch (e) { ui.fehler(e, 'Ort entfernen'); }
  }

  async ortVorgabe(id: string): Promise<void> {
    try { await api.oled.defaultLocation(id); await this.ladeOrte(); this.rendernBald(0); } catch (e) { ui.fehler(e, 'Vorgabeort'); }
  }

  async ortAktualisieren(id?: string): Promise<void> {
    try { await api.oled.refreshWeather(id); await this.ladeOrte(); this.rendernBald(0); ui.toast('Wetter geladen'); } catch (e) { ui.fehler(e, 'Wetter laden'); }
  }

  /* Sicherung */

  async exportieren(): Promise<void> {
    try {
      const b = await api.oled.exportBundle();
      const blob = new Blob([JSON.stringify(b, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `pyroplus-display-${new Date().toISOString().slice(0, 10)}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) { ui.fehler(e, 'Export'); }
  }

  async importieren(datei: File, ersetzen: boolean): Promise<void> {
    try {
      const daten = JSON.parse(await datei.text()) as OledBundle;
      const ergebnis = await api.oled.importBundle(daten, ersetzen);
      await this.laden();
      ui.toast(`Importiert: ${ergebnis.screens} Bildschirme, ${ergebnis.presets} Bausteine, ${ergebnis.profiles} Profile, ${ergebnis.locations} Orte`);
    } catch (e) { ui.fehler(e, 'Import'); }
  }

  /* Alte Sicherung der früheren Oberfläche im Browser */
  alteSicherung(): { screens: unknown[]; widgetPresets: unknown[]; profiles: unknown[]; weatherCities: unknown[] } | null {
    try {
      const zustand = JSON.parse(localStorage.getItem('pp-oled-state') ?? 'null') as { screens?: unknown[] } | null;
      const presets = JSON.parse(localStorage.getItem('pp-widget-presets') ?? '[]') as unknown[];
      const profile = JSON.parse(localStorage.getItem('pp-oled-profiles') ?? '[]') as unknown[];
      const staedte = JSON.parse(localStorage.getItem('pp-weather-cities') ?? '[]') as unknown[];
      const screens = zustand?.screens ?? [];
      if (!screens.length && !presets.length && !profile.length && !staedte.length) return null;
      return { screens, widgetPresets: presets, profiles: profile, weatherCities: staedte };
    } catch {
      return null;
    }
  }

  async alteSicherungUebernehmen(): Promise<void> {
    const daten = this.alteSicherung();
    if (!daten) return;
    try {
      const ergebnis = await api.oled.importLegacy(daten, false);
      this.alteSicherungVerwerfen();
      await this.laden();
      ui.toast(`Übernommen: ${ergebnis.screens} Bildschirme, ${ergebnis.presets} Bausteine, ${ergebnis.profiles} Profile, ${ergebnis.locations} Orte`);
    } catch (e) { ui.fehler(e, 'Übernahme'); }
  }

  alteSicherungVerwerfen(): void {
    for (const k of ['pp-oled-state', 'pp-widget-presets', 'pp-oled-profiles', 'pp-weather-cities']) {
      try { localStorage.removeItem(k); } catch { /* egal */ }
    }
  }
}

export const oled = new OledStore();
