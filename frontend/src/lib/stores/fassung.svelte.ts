/* Neue Fassung auf dem Server: nie ein hartes Neuladen verlangen (Muster aus Orbit und Kellerwolke).
   Die Startseite kommt ohne Zwischenspeicher (frontend/nginx.conf), Skripte und Gestaltung tragen Prüfsummen im
   Namen. Meldet das Backend eine andere Fassung als die eingebaute, lädt die Seite von selbst neu: in den ersten
   Sekunden nach dem Start sofort, später beim nächsten Bereichswechsel oder wenn das Fenster wieder nach vorn kommt.
   Nie, solange ein Entwurf des Displays noch nicht gespeichert ist oder ein Fenster mit Eingaben offen steht; dann
   wartet sie bis danach. Dazwischen steht ein Band mit Knopf (bausteine/FassungBand.svelte). Je Serverfassung nur ein
   selbsttätiger Versuch (Merker in der Sitzung), damit ein hängender Zwischenspeicher keine Schleife auslöst.
   Im Entwicklungsserver ruht der Vergleich: dort hält Vite die Oberfläche selbst frisch, und die eingebaute Fassung
   stammt vom Start des Servers (der Commit-Hook zählt version.json hoch, ohne dass Vite das mitbekommt). */

import { api } from '$lib/api/client';
import { oled } from './oled.svelte';
import { ui } from './ui.svelte';

export const OBERFLAECHE_FASSUNG = __APP_VERSION__;
const MERKER = 'pyroplus.neu_geladen';
const START_FENSTER_MS = 10_000;
const PRUEFEN_MS = 60_000;

export const fassung = $state<{ neu: string | null }>({ neu: null });

export type Anlass = 'start' | 'takt' | 'ortswechsel' | 'sichtbar';

/* Nichts, was ein Neuladen abbrechen würde: Entwurf gespeichert, kein Fenster mit Eingaben offen (die Hilfe zählt nicht). */
export function ruhig(): boolean {
  return oled.speicherzustand === 'gespeichert' && (ui.fenster === null || ui.fenster === 'hilfe');
}

function erlaubt(neu: string): boolean {
  try {
    if (sessionStorage.getItem(MERKER) === neu) return false;
    sessionStorage.setItem(MERKER, neu);
  } catch {
    /* ohne Sitzungsspeicher kein Merker: dann lieber einmal laden als nie */
  }
  return true;
}

export function vielleichtNeuLaden(anlass: Anlass): void {
  const neu = fassung.neu;
  if (!neu || anlass === 'takt' || !ruhig()) return;
  if (anlass === 'start' && performance.now() > START_FENSTER_MS) return;
  if (erlaubt(neu)) location.reload();
}

async function fassungPruefen(anlass: Anlass): Promise<void> {
  try {
    const server = (await api.system.info()).voll;
    fassung.neu = server !== OBERFLAECHE_FASSUNG ? server : null;
  } catch {
    return; /* ohne Backend meldet das die Verbindungsanzeige */
  }
  vielleichtNeuLaden(anlass);
}

function sichtbar(): void {
  if (document.visibilityState === 'visible') void fassungPruefen('sichtbar');
}

function ortswechsel(): void {
  vielleichtNeuLaden('ortswechsel');
}

export function fassungVerfolgen(): () => void {
  if (import.meta.env.DEV) return () => {};
  void fassungPruefen('start');
  const takt = setInterval(() => void fassungPruefen('takt'), PRUEFEN_MS);
  document.addEventListener('visibilitychange', sichtbar);
  window.addEventListener('hashchange', ortswechsel);
  return () => {
    clearInterval(takt);
    document.removeEventListener('visibilitychange', sichtbar);
    window.removeEventListener('hashchange', ortswechsel);
  };
}
