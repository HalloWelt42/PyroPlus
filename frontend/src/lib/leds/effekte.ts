/* Deutsche Beschriftungen und Gruppen der LED-Effekte. Angeboten wird nur, was das Backend kennt. */

export const EFFEKT_LABEL: Record<string, string> = {
  static: 'Eine Farbe', gradient: 'Verlauf', warm_white: 'Warmweiß',
  breathing: 'Atmen', rainbow: 'Regenbogen', candle: 'Kerze', lava: 'Lava', aurora: 'Polarlicht',
  fire: 'Feuer', ocean: 'Ozean', pulse: 'Puls', sunset: 'Sonnenuntergang', forest: 'Wald',
  neon: 'Neon', night_light: 'Nachtlicht',
  strobe: 'Stroboskop', police: 'Blaulicht', disco: 'Disco', chase: 'Lauflicht', sparkle: 'Funkeln', firework: 'Feuerwerk',
  temp_reactive: 'Temperatur', load_reactive: 'Auslastung',
};

export const EFFEKT_SYMBOL: Record<string, string> = {
  static: 'fa-circle', gradient: 'fa-droplet-slash', warm_white: 'fa-lightbulb', breathing: 'fa-lungs', rainbow: 'fa-rainbow',
  candle: 'fa-fire-flame-simple', lava: 'fa-mound', aurora: 'fa-wind', fire: 'fa-fire', ocean: 'fa-water', pulse: 'fa-heart-pulse',
  sunset: 'fa-sun', forest: 'fa-tree', neon: 'fa-bolt-lightning', night_light: 'fa-moon', strobe: 'fa-bolt', police: 'fa-car',
  disco: 'fa-music', chase: 'fa-person-running', sparkle: 'fa-star', firework: 'fa-wand-sparkles',
  temp_reactive: 'fa-temperature-half', load_reactive: 'fa-microchip',
};

export interface Gruppe { id: string; label: string; symbol: string; effekte: string[]; text: string; }

export const GRUPPEN: Gruppe[] = [
  { id: 'farben', label: 'Farben', symbol: 'fa-palette', effekte: ['static', 'gradient', 'warm_white'], text: 'Feste Farben, über die Palette einstellbar.' },
  { id: 'animationen', label: 'Animationen', symbol: 'fa-wand-magic-sparkles', effekte: ['breathing', 'rainbow', 'candle', 'lava', 'aurora', 'fire', 'ocean', 'pulse', 'sunset', 'forest', 'neon', 'night_light'], text: 'Bewegte Lichteffekte; das Tempo gilt für alle.' },
  { id: 'spielereien', label: 'Spielereien', symbol: 'fa-champagne-glasses', effekte: ['strobe', 'police', 'disco', 'chase', 'sparkle', 'firework'], text: 'Auffällige Effekte für besondere Momente.' },
];

export const REAKTIV = ['temp_reactive', 'load_reactive'];

export const PALETTE = [
  '#ff0000', '#ff4000', '#ff8000', '#ffc000', '#ffff00',
  '#80ff00', '#00ff00', '#00ff80', '#00ffff', '#0080ff',
  '#0000ff', '#4000ff', '#8000ff', '#ff00ff', '#ff0080',
  '#ffffff', '#ffd0a0', '#ffb060', '#ff8080', '#000000',
];

export function hex(c: { r: number; g: number; b: number } | undefined): string {
  if (!c) return '#0064ff';
  return '#' + [c.r, c.g, c.b].map((v) => (v || 0).toString(16).padStart(2, '0')).join('');
}

export function rgbAusHex(h: string): { r: number; g: number; b: number } {
  return { r: parseInt(h.slice(1, 3), 16), g: parseInt(h.slice(3, 5), 16), b: parseInt(h.slice(5, 7), 16) };
}

export function effektLabel(id: string, backendName?: string): string {
  return EFFEKT_LABEL[id] ?? backendName ?? id;
}
