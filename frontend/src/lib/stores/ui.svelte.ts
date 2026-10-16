/* Oberflächenzustand: aktive Ansicht, Hinweise, Fenster, Editor-Bequemlichkeiten je Gerät. */

export type Ansicht = 'fan' | 'leds' | 'display';
export type Fenster = 'vorlagen' | 'wetterorte' | 'profile' | 'hilfe' | null;

export interface Hinweis { id: number; text: string; art: 'ok' | 'fehler' | 'info'; }

const ANSICHTEN: Ansicht[] = ['fan', 'leds', 'display'];

function lese<T>(schluessel: string, vorgabe: T): T {
  try {
    const roh = localStorage.getItem(schluessel);
    return roh === null ? vorgabe : (JSON.parse(roh) as T);
  } catch {
    return vorgabe;
  }
}

function schreibe(schluessel: string, wert: unknown): void {
  try { localStorage.setItem(schluessel, JSON.stringify(wert)); } catch { /* privater Modus */ }
}

/* Fensterbreiten: bis BREITE_TELEFON die Telefonansicht, bis BREITE_KNAPP schmale Seitenleiste */
export const BREITE_TELEFON = 1000;
export const BREITE_KNAPP = 1279;

class UiStore {
  ansicht = $state<Ansicht>('fan');
  hinweise = $state<Hinweis[]>([]);
  fenster = $state<Fenster>(null);
  hilfeAbschnitt = $state('erste-schritte');
  seitenleisteOffen = $state(lese('pp.seitenleiste', true));
  /* Unter BREITE_KNAPP ist die Leiste schmal und klappt nur vorübergehend schwebend auf */
  knapp = $state(false);
  schwebendOffen = $state(false);
  zoom = $state(lese('pp.zoom', 4));
  raster = $state(lese('pp.raster', true));
  einrasten = $state(lese('pp.einrasten', false));
  mobil = $state(false);
  frontendVersion = __APP_VERSION__;

  private naechsteId = 1;

  start(): void {
    const ausHash = location.hash.replace('#/', '') as Ansicht;
    if (ANSICHTEN.includes(ausHash)) this.ansicht = ausHash;
    window.addEventListener('hashchange', () => {
      const h = location.hash.replace('#/', '') as Ansicht;
      if (ANSICHTEN.includes(h) && h !== this.ansicht) this.ansicht = h;
    });
    const telefon = window.matchMedia(`(max-width: ${BREITE_TELEFON}px)`);
    this.mobil = telefon.matches;
    telefon.addEventListener('change', (e) => { this.mobil = e.matches; });
    const knapp = window.matchMedia(`(max-width: ${BREITE_KNAPP}px)`);
    this.knapp = knapp.matches;
    knapp.addEventListener('change', (e) => { this.knapp = e.matches; this.schwebendOffen = false; });
  }

  zeige(a: Ansicht): void {
    this.ansicht = a;
    location.hash = `#/${a}`;
  }

  toast(text: string, art: Hinweis['art'] = 'ok'): void {
    const id = this.naechsteId++;
    this.hinweise = [...this.hinweise, { id, text, art }];
    setTimeout(() => { this.hinweise = this.hinweise.filter((h) => h.id !== id); }, art === 'fehler' ? 6000 : 3000);
  }

  fehler(e: unknown, vorsatz = ''): void {
    const text = e instanceof Error ? e.message : String(e);
    this.toast(vorsatz ? `${vorsatz}: ${text}` : text, 'fehler');
  }

  oeffneHilfe(abschnitt?: string): void {
    if (abschnitt) this.hilfeAbschnitt = abschnitt;
    this.fenster = 'hilfe';
  }

  setzeZoom(z: number): void { this.zoom = z; schreibe('pp.zoom', z); }
  setzeRaster(an: boolean): void { this.raster = an; schreibe('pp.raster', an); }
  setzeEinrasten(an: boolean): void { this.einrasten = an; schreibe('pp.einrasten', an); }
  setzeSeitenleiste(offen: boolean): void {
    if (this.knapp) { this.schwebendOffen = offen; return; }
    this.seitenleisteOffen = offen; schreibe('pp.seitenleiste', offen);
  }
  /* Ob die Leiste gerade ausgeklappt gezeigt wird */
  get leisteOffen(): boolean { return this.knapp ? this.schwebendOffen : this.seitenleisteOffen; }
}

export const ui = new UiStore();
