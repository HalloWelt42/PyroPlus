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
  'I':'01110,00100,00100,00100,00100,00100,01110','J':'00111,00010,00010,00010,00010,10010,01100',
  'K':'10001,10010,10100,11000,10100,10010,10001','L':'10000,10000,10000,10000,10000,10000,11111',
  'M':'10001,11011,10101,10101,10001,10001,10001','N':'10001,11001,10101,10011,10001,10001,10001',
  'O':'01110,10001,10001,10001,10001,10001,01110','P':'11110,10001,10001,11110,10000,10000,10000',
  'Q':'01110,10001,10001,10001,10101,01110,00001','R':'11110,10001,10001,11110,10100,10010,10001',
  'S':'01110,10001,10000,01110,00001,10001,01110','T':'11111,00100,00100,00100,00100,00100,00100',
  'U':'10001,10001,10001,10001,10001,10001,01110','V':'10001,10001,10001,10001,01010,01010,00100',
  'W':'10001,10001,10001,10101,10101,11011,10001','X':'10001,01010,00100,00100,00100,01010,10001',
  'Y':'10001,01010,00100,00100,00100,00100,00100','Z':'11111,00001,00010,00100,01000,10000,11111',
  '0':'01110,10001,10011,10101,11001,10001,01110','1':'00100,01100,00100,00100,00100,00100,01110',
  '2':'01110,10001,00001,00010,00100,01000,11111','3':'01110,10001,00001,00110,00001,10001,01110',
  '4':'00010,00110,01010,10010,11111,00010,00010','5':'11111,10000,11110,00001,00001,10001,01110',
  '6':'00110,01000,10000,11110,10001,10001,01110','7':'11111,00001,00010,00100,01000,01000,01000',
  '8':'01110,10001,10001,01110,10001,10001,01110','9':'01110,10001,10001,01111,00001,00010,01100',
  ' ':'00000,00000,00000,00000,00000,00000,00000','.':'00000,00000,00000,00000,00000,00000,00100',
  ':':'00000,00100,00100,00000,00100,00100,00000','-':'00000,00000,00000,11111,00000,00000,00000',
  '/':'00001,00010,00010,00100,01000,01000,10000','\\':'10000,01000,01000,00100,00010,00010,00001',
  '_':'00000,00000,00000,00000,00000,00000,11111','+':'00000,00100,00100,11111,00100,00100,00000',
  '=':'00000,00000,11111,00000,11111,00000,00000','*':'00000,10101,01110,11111,01110,10101,00000',
  '#':'01010,01010,11111,01010,11111,01010,01010','@':'01110,10001,10111,10101,10110,10000,01110',
  '&':'01100,10010,01100,01001,10110,10010,01101','~':'00000,00000,01000,10101,00010,00000,00000',
  '^':'00100,01010,10001,00000,00000,00000,00000','|':'00100,00100,00100,00100,00100,00100,00100',
  '°':'01100,10010,01100,00000,00000,00000,00000',
  '!':'00100,00100,00100,00100,00100,00000,00100','?':'01110,10001,00001,00010,00100,00000,00100',
  ',':'00000,00000,00000,00000,00000,00100,01000',';':'00000,00100,00100,00000,00100,00100,01000',
  '(':'00010,00100,01000,01000,01000,00100,00010',')':'01000,00100,00010,00010,00010,00100,01000',
  '[':'01110,01000,01000,01000,01000,01000,01110',']':'01110,00010,00010,00010,00010,00010,01110',
  '{':'00110,01000,01000,10000,01000,01000,00110','}':'01100,00010,00010,00001,00010,00010,01100',
  '<':'00010,00100,01000,10000,01000,00100,00010','>':'01000,00100,00010,00001,00010,00100,01000',
  '%':'10001,00010,00010,00100,01000,01000,10001',
  "'": '00100,00100,01000,00000,00000,00000,00000','"':'01010,01010,10100,00000,00000,00000,00000',
  '`':'01000,00100,00010,00000,00000,00000,00000','$':'00100,01111,10100,01110,00101,11110,00100',
  // Kleinbuchstaben
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
  // Umlaute
  'Ä':'10001,00000,01110,10001,11111,10001,10001','Ö':'10001,00000,01110,10001,10001,10001,01110',
  'Ü':'10001,00000,10001,10001,10001,10001,01110','ä':'01010,00000,01110,00001,01111,10001,01111',
  'ö':'01010,00000,01110,10001,10001,10001,01110','ü':'01010,00000,10001,10001,10001,10011,01101',
  'ß':'01110,10001,10010,10100,10010,10001,10110',
  // Pfeile
  '\u2190':'00000,00100,01000,11111,01000,00100,00000', // ←
  '\u2191':'00000,00100,01110,10101,00100,00100,00000', // ↑
  '\u2192':'00000,00100,00010,11111,00010,00100,00000', // →
  '\u2193':'00000,00100,00100,10101,01110,00100,00000', // ↓
};

export function drawText(pixels, str, sx, sy, scaleX = 1, scaleY) {
  if (scaleY === undefined) scaleY = scaleX;
  let cx = sx;
  for (const ch of str) {
    const g = FONT[ch] || FONT[ch.toUpperCase()];
    if (!g) { cx += 4 * scaleX; continue; }
    g.split(',').forEach((row, ry) => {
      for (let rx = 0; rx < row.length; rx++) {
        if (row[rx] === '1') {
          for (let dy = 0; dy < scaleY; dy++)
            for (let dx = 0; dx < scaleX; dx++) {
              const px = cx + rx * scaleX + dx, py = sy + ry * scaleY + dy;
              if (px >= 0 && px < W && py >= 0 && py < H) pixels[py * W + px] = 1;
            }
        }
      }
    });
    cx += 6 * scaleX;
  }
}

/* ═══ Erweitertes Text-Rendering (Invert, Border, Align) ═══ */
export function drawTextEx(pixels, str, sx, sy, scaleX = 1, scaleY, opts = {}) {
  if (scaleY === undefined) scaleY = scaleX;
  const { invert = false, border = false, align = 'left', boxW = 0 } = opts;
  const textW = Math.max(1, str.length * 6 * scaleX - scaleX);
  const textH = 7 * scaleY;
  const pad = (invert || border) ? 1 : 0;
  const totalW = (boxW > 0 ? boxW : textW) + pad * 2;
  const totalH = textH + pad * 2;

  // Ausrichtung
  let tx = sx + pad;
  if (boxW > 0 && align === 'center') tx = sx + pad + Math.floor((boxW - textW) / 2);
  else if (boxW > 0 && align === 'right') tx = sx + pad + boxW - textW;

  if (invert) {
    // Weißer Block
    for (let dy = 0; dy < totalH; dy++)
      for (let dx = 0; dx < totalW; dx++) {
        const px = sx + dx, py = sy + dy;
        if (px >= 0 && px < W && py >= 0 && py < H) pixels[py * W + px] = 1;
      }
    // Text schwarz (0) auf weißem Hintergrund
    drawTextVal(pixels, str, tx, sy + pad, scaleX, scaleY, 0);
  } else {
    drawText(pixels, str, tx, sy + pad, scaleX, scaleY);
  }

  // Rahmen (nur ohne Invert, weil Invert bereits einen Block hat)
  if (border && !invert) {
    for (let dx = 0; dx < totalW; dx++) {
      const px = sx + dx;
      if (px >= 0 && px < W) { if (sy >= 0 && sy < H) pixels[sy * W + px] = 1; if (sy+totalH-1 >= 0 && sy+totalH-1 < H) pixels[(sy+totalH-1) * W + px] = 1; }
    }
    for (let dy = 0; dy < totalH; dy++) {
      const py = sy + dy;
      if (py >= 0 && py < H) { if (sx >= 0 && sx < W) pixels[py * W + sx] = 1; if (sx+totalW-1 >= 0 && sx+totalW-1 < W) pixels[py * W + sx+totalW-1] = 1; }
    }
  }
}

function drawTextVal(pixels, str, sx, sy, scaleX, scaleY, val) {
  let cx = sx;
  for (const ch of str) {
    const g = FONT[ch] || FONT[ch.toUpperCase()];
    if (!g) { cx += 4 * scaleX; continue; }
    g.split(',').forEach((row, ry) => {
      for (let rx = 0; rx < row.length; rx++) {
        if (row[rx] === '1') {
          for (let dy = 0; dy < scaleY; dy++)
            for (let dx = 0; dx < scaleX; dx++) {
              const px = cx + rx * scaleX + dx, py = sy + ry * scaleY + dy;
              if (px >= 0 && px < W && py >= 0 && py < H) pixels[py * W + px] = val;
            }
        }
      }
    });
    cx += 6 * scaleX;
  }
}

/* ═══ Wetter-Icons (8×8 Pixel) ═══ */
const WEATHER_ICONS = {
  sun: [
    '00010000','00100100','00011000','01111110','01111110','00011000','00100100','00010000'
  ],
  cloud: [
    '00000000','00111000','01111100','11111110','11111110','01111100','00000000','00000000'
  ],
  rain: [
    '00111000','01111100','11111110','11111110','00000000','01010100','10101010','01010100'
  ],
  snow: [
    '00111000','01111100','11111110','00000000','01010100','00101000','01010100','10001010'
  ],
  thunder: [
    '00111000','01111100','11111110','00011000','00110000','00010000','00100000','00010000'
  ],
  fog: [
    '00000000','11111110','00000000','01111100','00000000','11111110','00000000','01111100'
  ],
  partly: [
    '00100000','01010000','00111000','01111100','11111110','11111110','01111100','00000000'
  ],
};

export function drawWeatherIcon(pixels, x, y, code) {
  let icon = 'sun';
  if (code == null) icon = 'sun';
  else if (code === 0) icon = 'sun';
  else if (code <= 3) icon = 'partly';
  else if (code <= 49) icon = 'fog';
  else if (code <= 69) icon = 'rain';
  else if (code <= 79) icon = 'snow';
  else if (code <= 84) icon = 'rain';
  else icon = 'thunder';

  const rows = WEATHER_ICONS[icon] || WEATHER_ICONS.sun;
  for (let ry = 0; ry < rows.length; ry++) {
    for (let rx = 0; rx < rows[ry].length; rx++) {
      if (rows[ry][rx] === '1') {
        const px = x + rx, py = y + ry;
        if (px >= 0 && px < W && py >= 0 && py < H) pixels[py * W + px] = 1;
      }
    }
  }
}

/* ═══ Pixel-Art Sprites (8×8) ═══ */
const SPRITES = {
  snowman: [
    '00111000','01000100','01010100','01000100','00111000',
    '01111110','00111100','01111110','01011010','00100100',
  ],
  snowflake: [
    '00010000','01010100','00111000','11111110','00111000',
    '01010100','00010000','00000000',
  ],
  heart: [
    '01101100','11111110','11111110','11111110','01111100',
    '00111000','00010000','00000000',
  ],
  star: [
    '00010000','00010000','01111100','00111000','01101100',
    '01000100','00000000','00000000',
  ],
  cat: [
    '01000010','11100111','10011001','10111101','10100101',
    '10111101','01111110','00100100',
  ],
  dog: [
    '01100000','10010000','11111100','10010010','11111110',
    '10010010','10010010','01001100',
  ],
  tree: [
    '00010000','00111000','01111100','11111110','00111000',
    '01111100','11111110','00010000',
  ],
  sun_deco: [
    '00010000','01010100','00111000','11101110','00111000',
    '01010100','00010000','00000000',
  ],
  moon_deco: [
    '00111000','01111100','01110000','11100000','11100000',
    '01110000','01111100','00111000',
  ],
  music: [
    '00011100','00010010','00010010','00010010','01110010',
    '11111010','01110100','00001000',
  ],
  skull: [
    '01111110','11111111','10100101','11111111','01100110',
    '01111110','00111100','00000000',
  ],
  gift: [
    '00111000','01111100','11111110','01010100','01111100',
    '01010100','01111100','00000000',
  ],
  bell: [
    '00010000','00111000','01000100','01000100','01111100',
    '11111110','00010000','00000000',
  ],
};

export function drawSprite(pixels, name, x, y, scale = 1) {
  const rows = SPRITES[name];
  if (!rows) return;
  for (let ry = 0; ry < rows.length; ry++) {
    for (let rx = 0; rx < rows[ry].length; rx++) {
      if (rows[ry][rx] === '1') {
        for (let dy = 0; dy < scale; dy++)
          for (let dx = 0; dx < scale; dx++) {
            const px = x + rx * scale + dx, py = y + ry * scale + dy;
            if (px >= 0 && px < W && py >= 0 && py < H) pixels[py * W + px] = 1;
          }
      }
    }
  }
}

export const SPRITE_NAMES = Object.keys(SPRITES);

/* ═══ Laufschrift ═══ */
export function drawMarquee(pixels, text, y, offset, scale = 1) {
  const totalW = text.length * 6 * scale;
  const x = W - (offset % (totalW + W));
  drawText(pixels, text, x, y, scale);
}

/* ═══ Sparkline (Mini-Verlaufsgraph) ═══ */
export function drawSparkline(pixels, values, x, y, w, h) {
  if (!values || values.length < 2) return;
  const max = Math.max(...values, 1);
  const min = Math.min(...values, 0);
  const range = max - min || 1;
  const step = w / (values.length - 1);
  // Rahmen
  for (let i = 0; i < w; i++) { if (x+i>=0&&x+i<W) { if(y>=0&&y<H) pixels[y*W+x+i]=1; if(y+h-1>=0&&y+h-1<H) pixels[(y+h-1)*W+x+i]=1; } }
  for (let j = 0; j < h; j++) { if (y+j>=0&&y+j<H) { if(x>=0&&x<W) pixels[(y+j)*W+x]=1; if(x+w-1>=0&&x+w-1<W) pixels[(y+j)*W+x+w-1]=1; } }
  // Linie zeichnen
  for (let i = 0; i < values.length - 1; i++) {
    const x0 = Math.round(x + 1 + i * step);
    const y0 = Math.round(y + h - 2 - ((values[i] - min) / range) * (h - 3));
    const x1 = Math.round(x + 1 + (i + 1) * step);
    const y1 = Math.round(y + h - 2 - ((values[i + 1] - min) / range) * (h - 3));
    bresenhamLine(x0, y0, x1, y1, (px, py) => {
      if (px >= x+1 && px < x+w-1 && py >= y+1 && py < y+h-1) pixels[py * W + px] = 1;
    });
  }
}

/* ═══ Gauge (Halbkreis-Fortschritt) ═══ */
export function drawGauge(pixels, pct, x, y, r) {
  const cx = x + r, cy = y + r;
  const clamped = Math.max(0, Math.min(100, pct));
  // Halbkreis-Outline (180°)
  for (let a = 180; a <= 360; a += 2) {
    const rad = a * Math.PI / 180;
    const px = Math.round(cx + r * Math.cos(rad));
    const py = Math.round(cy + r * Math.sin(rad));
    if (px >= 0 && px < W && py >= 0 && py < H) pixels[py * W + px] = 1;
  }
  // Gefüllter Bogen bis pct
  const endAngle = 180 + (clamped / 100) * 180;
  for (let a = 180; a <= endAngle; a += 1) {
    const rad = a * Math.PI / 180;
    for (let ri = r - 2; ri <= r; ri++) {
      const px = Math.round(cx + ri * Math.cos(rad));
      const py = Math.round(cy + ri * Math.sin(rad));
      if (px >= 0 && px < W && py >= 0 && py < H) pixels[py * W + px] = 1;
    }
  }
  // Wert zentriert unter dem Gauge
  const text = `${Math.round(clamped)}%`;
  const tw = text.length * 6;
  drawText(pixels, text, cx - Math.floor(tw / 2), cy - 3, 1);
}

/* ═══ Section Header (── LABEL ──) ═══ */
export function drawSectionHeader(pixels, text, x, y, w) {
  const tw = text.length * 6;
  const lineL = Math.max(0, Math.floor((w - tw - 4) / 2));
  const lineR = Math.max(0, w - tw - 4 - lineL);
  // Linke Linie
  for (let i = 0; i < lineL; i++) { const px = x+i; if(px>=0&&px<W&&y+3>=0&&y+3<H) pixels[(y+3)*W+px]=1; }
  // Text
  drawText(pixels, text, x + lineL + 2, y, 1);
  // Rechte Linie
  for (let i = 0; i < lineR; i++) { const px = x+lineL+2+tw+2+i; if(px>=0&&px<W&&y+3>=0&&y+3<H) pixels[(y+3)*W+px]=1; }
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
