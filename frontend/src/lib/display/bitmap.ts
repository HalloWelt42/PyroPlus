/* Pixelbilder: Packen und Entpacken (gleiches Format wie das Backend) und Zeichenoperationen.
   Zeilen aus 0 und 1; jede Zeile beginnt beim Packen an einer Bytegrenze. */

export type Bitmap = number[][];

export function neuesBitmap(breite: number, hoehe: number): Bitmap {
  return Array.from({ length: hoehe }, () => Array<number>(breite).fill(0));
}

export function packen(rows: Bitmap): string {
  const bytes: number[] = [];
  for (const zeile of rows) {
    let byte = 0;
    let bits = 0;
    for (const pixel of zeile) {
      byte = (byte << 1) | (pixel ? 1 : 0);
      bits += 1;
      if (bits === 8) { bytes.push(byte); byte = 0; bits = 0; }
    }
    if (bits) bytes.push(byte << (8 - bits));
  }
  let bin = '';
  for (const b of bytes) bin += String.fromCharCode(b);
  return btoa(bin);
}

export function entpacken(kodiert: string | null, breite: number, hoehe: number): Bitmap {
  let bytes: Uint8Array;
  try {
    const bin = atob(kodiert ?? '');
    bytes = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  } catch {
    bytes = new Uint8Array(0);
  }
  const breiteBytes = Math.ceil(breite / 8);
  const rows: Bitmap = [];
  for (let y = 0; y < hoehe; y++) {
    const zeile: number[] = [];
    for (let x = 0; x < breite; x++) {
      const index = y * breiteBytes + Math.floor(x / 8);
      const byte = index < bytes.length ? bytes[index] : 0;
      zeile.push((byte >> (7 - (x % 8))) & 1);
    }
    rows.push(zeile);
  }
  return rows;
}

export function kopie(rows: Bitmap): Bitmap {
  return rows.map((z) => [...z]);
}

export function setzePixel(rows: Bitmap, x: number, y: number, wert: 0 | 1, breite = 1): void {
  const o = Math.floor(breite / 2);
  for (let dy = 0; dy < breite; dy++) {
    for (let dx = 0; dx < breite; dx++) {
      const px = x - o + dx;
      const py = y - o + dy;
      if (py >= 0 && py < rows.length && px >= 0 && px < rows[0].length) rows[py][px] = wert;
    }
  }
}

export function linie(rows: Bitmap, x0: number, y0: number, x1: number, y1: number, wert: 0 | 1, breite = 1): void {
  const dx = Math.abs(x1 - x0);
  const dy = Math.abs(y1 - y0);
  const sx = x0 < x1 ? 1 : -1;
  const sy = y0 < y1 ? 1 : -1;
  let err = dx - dy;
  for (;;) {
    setzePixel(rows, x0, y0, wert, breite);
    if (x0 === x1 && y0 === y1) break;
    const e2 = 2 * err;
    if (e2 > -dy) { err -= dy; x0 += sx; }
    if (e2 < dx) { err += dx; y0 += sy; }
  }
}

export function rechteck(rows: Bitmap, x0: number, y0: number, x1: number, y1: number, wert: 0 | 1, gefuellt: boolean): void {
  const a = Math.min(x0, x1), b = Math.min(y0, y1), c = Math.max(x0, x1), d = Math.max(y0, y1);
  for (let y = b; y <= d; y++) {
    for (let x = a; x <= c; x++) {
      if (gefuellt || y === b || y === d || x === a || x === c) setzePixel(rows, x, y, wert);
    }
  }
}

export function ellipse(rows: Bitmap, x0: number, y0: number, x1: number, y1: number, wert: 0 | 1, gefuellt: boolean): void {
  const cx = (x0 + x1) / 2, cy = (y0 + y1) / 2;
  const rx = Math.abs(x1 - x0) / 2, ry = Math.abs(y1 - y0) / 2;
  if (rx < 0.5 && ry < 0.5) { setzePixel(rows, x0, y0, wert); return; }
  const a = Math.min(x0, x1), b = Math.min(y0, y1), c = Math.max(x0, x1), d = Math.max(y0, y1);
  for (let y = b; y <= d; y++) {
    for (let x = a; x <= c; x++) {
      const nx = rx > 0 ? (x - cx) / rx : 0;
      const ny = ry > 0 ? (y - cy) / ry : 0;
      const innen = nx * nx + ny * ny <= 1.0;
      if (!innen) continue;
      if (gefuellt) { setzePixel(rows, x, y, wert); continue; }
      const nx2 = rx > 1 ? (x - cx) / (rx - 1) : 2;
      const ny2 = ry > 1 ? (y - cy) / (ry - 1) : 2;
      if (nx2 * nx2 + ny2 * ny2 > 1.0) setzePixel(rows, x, y, wert);
    }
  }
}

export function fuellen(rows: Bitmap, x: number, y: number, wert: 0 | 1): void {
  if (y < 0 || y >= rows.length || x < 0 || x >= rows[0].length) return;
  const ziel = rows[y][x];
  if (ziel === wert) return;
  const stapel: Array<[number, number]> = [[x, y]];
  while (stapel.length) {
    const [px, py] = stapel.pop() as [number, number];
    if (py < 0 || py >= rows.length || px < 0 || px >= rows[0].length) continue;
    if (rows[py][px] !== ziel) continue;
    rows[py][px] = wert;
    stapel.push([px + 1, py], [px - 1, py], [px, py + 1], [px, py - 1]);
  }
}

export function verschieben(rows: Bitmap, dx: number, dy: number): Bitmap {
  const neu = neuesBitmap(rows[0].length, rows.length);
  for (let y = 0; y < rows.length; y++) {
    for (let x = 0; x < rows[0].length; x++) {
      const nx = x + dx, ny = y + dy;
      if (ny >= 0 && ny < rows.length && nx >= 0 && nx < rows[0].length) neu[ny][nx] = rows[y][x];
    }
  }
  return neu;
}

export function umkehren(rows: Bitmap): Bitmap {
  return rows.map((z) => z.map((p) => (p ? 0 : 1)));
}

export function spiegeln(rows: Bitmap): Bitmap {
  return rows.map((z) => [...z].reverse());
}

export function leeren(rows: Bitmap): Bitmap {
  return neuesBitmap(rows[0].length, rows.length);
}

export function groesseAendern(rows: Bitmap, breite: number, hoehe: number): Bitmap {
  const neu = neuesBitmap(breite, hoehe);
  for (let y = 0; y < Math.min(hoehe, rows.length); y++) {
    for (let x = 0; x < Math.min(breite, rows[0].length); x++) neu[y][x] = rows[y][x];
  }
  return neu;
}

/* Auf den gezeichneten Inhalt zuschneiden; liefert Versatz, damit das Widget an Ort bleibt. */
export function zuschneiden(rows: Bitmap): { rows: Bitmap; dx: number; dy: number } | null {
  let x0 = Infinity, y0 = Infinity, x1 = -1, y1 = -1;
  rows.forEach((z, y) => z.forEach((p, x) => {
    if (!p) return;
    x0 = Math.min(x0, x); y0 = Math.min(y0, y); x1 = Math.max(x1, x); y1 = Math.max(y1, y);
  }));
  if (x1 < 0) return null;
  const neu = rows.slice(y0, y1 + 1).map((z) => z.slice(x0, x1 + 1));
  return { rows: neu, dx: x0, dy: y0 };
}

/* Pixel aus einem gerenderten PNG (Base64) lesen, zum Beispiel für das Textwerkzeug. */
export async function pixelAusPng(base64: string, breite: number, hoehe: number): Promise<Bitmap> {
  const bild = new Image();
  bild.src = `data:image/png;base64,${base64}`;
  await bild.decode();
  const leinwand = document.createElement('canvas');
  leinwand.width = breite;
  leinwand.height = hoehe;
  const ctx = leinwand.getContext('2d');
  if (!ctx) return neuesBitmap(breite, hoehe);
  ctx.drawImage(bild, 0, 0);
  const daten = ctx.getImageData(0, 0, breite, hoehe).data;
  const rows = neuesBitmap(breite, hoehe);
  for (let y = 0; y < hoehe; y++) {
    for (let x = 0; x < breite; x++) rows[y][x] = daten[(y * breite + x) * 4] > 127 ? 1 : 0;
  }
  return rows;
}
