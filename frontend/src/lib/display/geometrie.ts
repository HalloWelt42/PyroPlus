/* Geometrie auf dem 128 mal 64 Pixel großen Display: Treffer, freie Stellen, Einrasten. */

import type { WidgetBox } from '$lib/api/types';

export const W = 128;
export const H = 64;

export function begrenze(wert: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, wert));
}

export function trifft(box: WidgetBox, x: number, y: number): boolean {
  return box.w > 0 && box.h > 0 && x >= box.x && x < box.x + box.w && y >= box.y && y < box.y + box.h;
}

/* Oberstes Widget zuerst: die Liste ist in Zeichenreihenfolge, also von hinten suchen. */
export function treffer(boxes: WidgetBox[], x: number, y: number): WidgetBox | null {
  for (let i = boxes.length - 1; i >= 0; i--) {
    if (trifft(boxes[i], x, y)) return boxes[i];
  }
  return null;
}

export function ueberlappt(a: { x: number; y: number; w: number; h: number }, b: WidgetBox): boolean {
  if (b.w === 0 || b.h === 0) return false;
  return a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h;
}

/* Erste freie Stelle für ein Widget der Größe w mal h; Abtastung in 2-Pixel-Schritten. */
export function freieStelle(boxes: WidgetBox[], w: number, h: number): { x: number; y: number } {
  const breite = Math.min(w, W), hoehe = Math.min(h, H);
  for (let y = 0; y + hoehe <= H; y += 2) {
    for (let x = 0; x + breite <= W; x += 2) {
      const kandidat = { x, y, w: breite, h: hoehe };
      if (!boxes.some((b) => ueberlappt(kandidat, b))) return { x, y };
    }
  }
  return { x: 0, y: 0 };
}

export function einrasten(wert: number, raster: number): number {
  return raster > 1 ? Math.round(wert / raster) * raster : wert;
}
