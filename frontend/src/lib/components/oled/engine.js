/**
 * PyroPlus OLED Pixel Engine — 128×64, 1-Bit
 * Reine Datenverarbeitung, kein Canvas/DOM.
 */

export const W = 128, H = 64;

/* ═══ Zeichenfunktionen ═══ */
export function bresenhamLine(x0, y0, x1, y1, plotFn) {
  const dx = Math.abs(x1 - x0), dy = Math.abs(y1 - y0);
  const sx = x0 < x1 ? 1 : -1, sy = y0 < y1 ? 1 : -1;
  let err = dx - dy;
  while (true) {
    plotFn(x0, y0);
    if (x0 === x1 && y0 === y1) break;
    const e2 = 2 * err;
    if (e2 > -dy) { err -= dy; x0 += sx; }
    if (e2 < dx) { err += dx; y0 += sy; }
  }
}

export function drawRect(x0, y0, x1, y1, plotFn, filled) {
  const a = Math.min(x0, x1), b = Math.min(y0, y1), c = Math.max(x0, x1), d = Math.max(y0, y1);
  if (filled) { for (let y = b; y <= d; y++) for (let x = a; x <= c; x++) plotFn(x, y); }
  else { for (let x = a; x <= c; x++) { plotFn(x, b); plotFn(x, d); } for (let y = b + 1; y < d; y++) { plotFn(a, y); plotFn(c, y); } }
}

export function drawCircle(cx, cy, x1, y1, plotFn, filled) {
  const r = Math.round(Math.sqrt((x1 - cx) ** 2 + (y1 - cy) ** 2));
  if (r === 0) { plotFn(cx, cy); return; }
  if (filled) {
    for (let y = -r; y <= r; y++) for (let x = -r; x <= r; x++) if (x * x + y * y <= r * r) plotFn(cx + x, cy + y);
  } else {
    let x = r, y = 0, d = 1 - r;
    while (x >= y) {
      plotFn(cx+x,cy+y); plotFn(cx-x,cy+y); plotFn(cx+x,cy-y); plotFn(cx-x,cy-y);
      plotFn(cx+y,cy+x); plotFn(cx-y,cy+x); plotFn(cx+y,cy-x); plotFn(cx-y,cy-x);
      y++; if (d <= 0) d += 2*y+1; else { x--; d += 2*(y-x)+1; }
    }
  }
}

export function drawEllipse(cx, cy, x1, y1, plotFn, filled) {
  const rx = Math.abs(x1 - cx), ry = Math.abs(y1 - cy);
  if (rx === 0 && ry === 0) { plotFn(cx, cy); return; }
  if (filled) {
    for (let y = -ry; y <= ry; y++) for (let x = -rx; x <= rx; x++)
      if (rx > 0 && ry > 0 && (x*x)/(rx*rx) + (y*y)/(ry*ry) <= 1) plotFn(cx+x, cy+y);
  } else {
    let x = 0, y = ry, d1 = ry*ry - rx*rx*ry + 0.25*rx*rx;
    while (2*ry*ry*x <= 2*rx*rx*y) {
      plotFn(cx+x,cy+y); plotFn(cx-x,cy+y); plotFn(cx+x,cy-y); plotFn(cx-x,cy-y);
      x++; if (d1 < 0) d1 += 2*ry*ry*x + ry*ry; else { y--; d1 += 2*ry*ry*x - 2*rx*rx*y + ry*ry; }
    }
    let d2 = ry*ry*(x+0.5)*(x+0.5) + rx*rx*(y-1)*(y-1) - rx*rx*ry*ry;
    while (y >= 0) {
      plotFn(cx+x,cy+y); plotFn(cx-x,cy+y); plotFn(cx+x,cy-y); plotFn(cx-x,cy-y);
      y--; if (d2 > 0) d2 -= 2*rx*rx*y + rx*rx; else { x++; d2 += 2*ry*ry*x - 2*rx*rx*y + rx*rx; }
    }
  }
}

export function drawBar(pixels, x, y, w, h, pct) {
  // Rahmen
  for (let i = 0; i < w; i++) { if (y >= 0 && y < H && x+i >= 0 && x+i < W) pixels[y * W + x + i] = 1; if (y+h-1 >= 0 && y+h-1 < H && x+i >= 0 && x+i < W) pixels[(y+h-1) * W + x + i] = 1; }
  for (let j = 0; j < h; j++) { if (x >= 0 && x < W && y+j >= 0 && y+j < H) pixels[(y+j) * W + x] = 1; if (x+w-1 >= 0 && x+w-1 < W && y+j >= 0 && y+j < H) pixels[(y+j) * W + x + w - 1] = 1; }
  // Füllung
  const fw = Math.round((w - 2) * Math.min(1, Math.max(0, pct / 100)));
  for (let j = 1; j < h - 1; j++) for (let i = 0; i < fw; i++) { const px = x+1+i, py = y+j; if (px >= 0 && px < W && py >= 0 && py < H) pixels[py * W + px] = 1; }
}

export function floodFill(pixels, startX, startY, fillVal) {
  if (startX < 0 || startX >= W || startY < 0 || startY >= H) return;
  const target = pixels[startY * W + startX];
  if (target === fillVal) return;
  const stack = [startY * W + startX];
  const visited = new Uint8Array(W * H);
  while (stack.length > 0) {
    const pi = stack.pop();
    if (visited[pi]) continue;
    visited[pi] = 1;
    if (pixels[pi] !== target) continue;
    pixels[pi] = fillVal;
    const x = pi % W, y = (pi - x) / W;
    if (x > 0) stack.push(pi - 1);
    if (x < W - 1) stack.push(pi + 1);
    if (y > 0) stack.push(pi - W);
    if (y < H - 1) stack.push(pi + W);
  }
}

/* ═══ 5×7 Bitmap-Font ═══ */
const FONT = {
  'A':'01110,10001,10001,11111,10001,10001,10001','B':'11110,10001,10001,11110,10001,10001,11110',
  'C':'01110,10001,10000,10000,10000,10001,01110','D':'11110,10001,10001,10001,10001,10001,11110',
  'E':'11111,10000,10000,11110,10000,10000,11111','F':'11111,10000,10000,11110,10000,10000,10000',
  'G':'01110,10001,10000,10111,10001,10001,01110','H':'10001,10001,10001,11111,10001,10001,10001',
  'I':'01110,00100,00100,00100,00100,00100,01110','L':'10000,10000,10000,10000,10000,10000,11111',
  'M':'10001,11011,10101,10101,10001,10001,10001','N':'10001,11001,10101,10011,10001,10001,10001',
  'O':'01110,10001,10001,10001,10001,10001,01110','P':'11110,10001,10001,11110,10000,10000,10000',
  'R':'11110,10001,10001,11110,10100,10010,10001','S':'01110,10001,10000,01110,00001,10001,01110',
  'T':'11111,00100,00100,00100,00100,00100,00100','U':'10001,10001,10001,10001,10001,10001,01110',
  'V':'10001,10001,10001,10001,01010,01010,00100','W':'10001,10001,10001,10101,10101,11011,10001',
  'X':'10001,01010,00100,00100,00100,01010,10001','Y':'10001,01010,00100,00100,00100,00100,00100',
  'Z':'11111,00001,00010,00100,01000,10000,11111',
  '0':'01110,10001,10011,10101,11001,10001,01110','1':'00100,01100,00100,00100,00100,00100,01110',
  '2':'01110,10001,00001,00010,00100,01000,11111','3':'01110,10001,00001,00110,00001,10001,01110',
  '4':'00010,00110,01010,10010,11111,00010,00010','5':'11111,10000,11110,00001,00001,10001,01110',
  '6':'00110,01000,10000,11110,10001,10001,01110','7':'11111,00001,00010,00100,01000,01000,01000',
  '8':'01110,10001,10001,01110,10001,10001,01110','9':'01110,10001,10001,01111,00001,00010,01100',
  ' ':'00000,00000,00000,00000,00000,00000,00000','.':'00000,00000,00000,00000,00000,00000,00100',
  ':':'00000,00100,00100,00000,00100,00100,00000','-':'00000,00000,00000,11111,00000,00000,00000',
  '°':'01100,10010,01100,00000,00000,00000,00000',
  'a':'00000,00000,01110,00001,01111,10001,01111','b':'10000,10000,11110,10001,10001,10001,11110',
  'c':'00000,00000,01110,10000,10000,10001,01110','d':'00001,00001,01111,10001,10001,10001,01111',
  'e':'00000,00000,01110,10001,11111,10000,01110','f':'00110,01000,01000,11100,01000,01000,01000',
  'g':'00000,00000,01111,10001,01111,00001,01110','h':'10000,10000,11110,10001,10001,10001,10001',
  'i':'00100,00000,01100,00100,00100,00100,01110','j':'00010,00000,00010,00010,00010,10010,01100',
  'k':'10000,10001,10010,10100,11000,10100,10010','l':'01100,00100,00100,00100,00100,00100,01110',
  'm':'00000,00000,11010,10101,10101,10001,10001','n':'00000,00000,11110,10001,10001,10001,10001',
  'o':'00000,00000,01110,10001,10001,10001,01110','p':'00000,00000,11110,10001,11110,10000,10000',
  'q':'00000,00000,01111,10001,01111,00001,00001','r':'00000,00000,10110,11001,10000,10000,10000',
  's':'00000,00000,01111,10000,01110,00001,11110','t':'01000,01000,11100,01000,01000,01001,00110',
  'u':'00000,00000,10001,10001,10001,10011,01101','v':'00000,00000,10001,10001,01010,01010,00100',
  'w':'00000,00000,10001,10001,10101,10101,01010','x':'00000,00000,10001,01010,00100,01010,10001',
  'y':'00000,00000,10001,01010,00100,01000,10000','z':'00000,00000,11111,00010,00100,01000,11111',
};

export function drawText(pixels, str, sx, sy, scale = 1) {
  let cx = sx;
  for (const ch of str) {
    const g = FONT[ch] || FONT[ch.toUpperCase()];
    if (!g) { cx += 4 * scale; continue; }
    g.split(',').forEach((row, ry) => {
      for (let rx = 0; rx < row.length; rx++) {
        if (row[rx] === '1') {
          for (let dy = 0; dy < scale; dy++)
            for (let dx = 0; dx < scale; dx++) {
              const px = cx + rx * scale + dx, py = sy + ry * scale + dy;
              if (px >= 0 && px < W && py >= 0 && py < H) pixels[py * W + px] = 1;
            }
        }
      }
    });
    cx += 6 * scale;
  }
}

/* ═══ Composite: Alle sichtbaren Layer zusammenrechnen ═══ */
export function composite(layers) {
  const result = new Uint8Array(W * H);
  for (const layer of layers) {
    if (!layer.visible) continue;
    for (let i = 0; i < W * H; i++) if (layer.pixels[i]) result[i] = 1;
  }
  return result;
}

/* ═══ Canvas-Rendering ═══ */
export function renderCanvas(ctx, comp, zoom, showGrid) {
  ctx.imageSmoothingEnabled = false;
  ctx.fillStyle = '#000';
  ctx.fillRect(0, 0, W * zoom, H * zoom);
  ctx.fillStyle = '#fff';
  for (let y = 0; y < H; y++)
    for (let x = 0; x < W; x++)
      if (comp[y * W + x]) ctx.fillRect(x * zoom, y * zoom, zoom, zoom);
  if (showGrid && zoom >= 4) {
    ctx.strokeStyle = 'rgba(255,255,255,0.12)';
    ctx.lineWidth = 0.5;
    for (let x = 0; x <= W; x++) { ctx.beginPath(); ctx.moveTo(x*zoom, 0); ctx.lineTo(x*zoom, H*zoom); ctx.stroke(); }
    for (let y = 0; y <= H; y++) { ctx.beginPath(); ctx.moveTo(0, y*zoom); ctx.lineTo(W*zoom, y*zoom); ctx.stroke(); }
  }
}

export function renderPreview(ctx, comp) {
  ctx.imageSmoothingEnabled = false;
  ctx.fillStyle = '#000';
  ctx.fillRect(0, 0, W, H);
  ctx.fillStyle = '#fff';
  for (let y = 0; y < H; y++)
    for (let x = 0; x < W; x++)
      if (comp[y * W + x]) ctx.fillRect(x, y, 1, 1);
}

/* ═══ Bild zu DataURL ═══ */
export function compositeToDataUrl(layers) {
  const comp = composite(layers);
  const c = document.createElement('canvas');
  c.width = W; c.height = H;
  const ctx = c.getContext('2d');
  ctx.fillStyle = '#000'; ctx.fillRect(0, 0, W, H);
  ctx.fillStyle = '#fff';
  for (let y = 0; y < H; y++)
    for (let x = 0; x < W; x++)
      if (comp[y * W + x]) ctx.fillRect(x, y, 1, 1);
  return c.toDataURL();
}
