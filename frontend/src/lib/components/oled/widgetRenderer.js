/**
 * PyroPlus — Widget-Renderer
 * Zeichnet Widget-Instanzen (source + display + opts) in einen Pixel-Buffer.
 */

import * as E from './engine.js';
import { getSource, HISTORY_KEYS } from './catalog.js';

const W = E.W, H = E.H;

/**
 * Ein Widget in den Pixel-Buffer rendern.
 * @param {Uint8Array} px - Pixel-Buffer (128*64)
 * @param {object} widget - { source, display, x, y, opts, name }
 * @param {object} stats - s.stats
 * @param {object} weather - Wetterdaten
 * @param {object} history - { cpu:[], temp:[], ram:[], ... }
 */
export function renderWidget(px, widget, stats, weather, history) {
  const { source, display, x, y, opts = {} } = widget;
  const src = getSource(source);
  if (!src && !['linie_h','linie_v','rahmen_shape','block','section'].includes(display)) return;

  const rot = opts.rotate || 0;
  if (rot > 0) {
    // In Temp-Buffer zeichnen, dann rotiert kopieren
    const tmp = new Uint8Array(W * H);
    _renderInto(tmp, { ...widget, opts: { ...opts, rotate: 0 } }, stats, weather, history);
    const sz = getWidgetSize(widget);
    _copyRotated(tmp, px, x, y, sz.w, sz.h, rot);
    return;
  }
  _renderInto(px, widget, stats, weather, history);
}

function _copyRotated(src, dst, ox, oy, w, h, rot) {
  for (let iy = 0; iy < h && iy + oy < H; iy++) {
    for (let ix = 0; ix < w && ix + ox < W; ix++) {
      if (!src[(oy + iy) * W + (ox + ix)]) continue;
      let dx, dy;
      if (rot === 90)       { dx = ox + h - 1 - iy; dy = oy + ix; }
      else if (rot === 180) { dx = ox + w - 1 - ix;  dy = oy + h - 1 - iy; }
      else if (rot === 270) { dx = ox + iy;           dy = oy + w - 1 - ix; }
      else                  { dx = ox + ix;           dy = oy + iy; }
      if (dx >= 0 && dx < W && dy >= 0 && dy < H) dst[dy * W + dx] = 1;
    }
  }
}

function _renderInto(px, widget, stats, weather, history) {
  const { source, display, x, y, opts = {} } = widget;
  const src = getSource(source);

  const sx = opts.scaleX ?? 1;
  const sy = opts.scaleY ?? sx;
  const hasEx = opts.invert || opts.border || (opts.align && opts.align !== 'left');

  // Wert holen
  const val = src?.getValue ? String(src.getValue(stats, weather, opts)) : (opts.text ?? '');
  const rawPct = src?.getRaw ? src.getRaw(stats, weather, opts) : parseFloat(val) || 0;
  const fullText = (opts.prefix ?? '') + val + (opts.suffix ?? '');

  // Text-Rendering Hilfsfunktion
  function _drawTxt(text, tx, ty, tsx, tsy) {
    if (hasEx) {
      E.drawTextEx(px, text, tx, ty, tsx, tsy, {
        invert: !!opts.invert, border: !!opts.border,
        align: opts.align || 'left', boxW: opts.boxW || 0,
      });
    } else {
      E.drawText(px, text, tx, ty, tsx, tsy);
    }
  }

  switch (display) {
    // ─── Zahlen/Text in verschiedenen Groessen ───
    case 'zahl':
    case 'zahl_gross':
    case 'zahl_xl':
    case 'zahl_xxl':
    case 'zahl_breit':
    case 'zahl_hoch':
    case 'zahl_x3y1':
    case 'zahl_x1y3':
    case 'text':
    case 'text_gross':
    case 'text_xl': {
      _drawTxt(fullText, x, y, sx, sy);
      break;
    }

    // ─── Invertiert / Rahmen ───
    case 'text_invertiert':
    case 'text_inv_gross':
    case 'text_inv_xl': {
      E.drawTextEx(px, fullText, x, y, sx, sy, { invert: true, border: false, align: opts.align || 'left', boxW: opts.boxW || 0 });
      break;
    }
    case 'text_rahmen':
    case 'text_rahmen_gross': {
      E.drawTextEx(px, fullText, x, y, sx, sy, { invert: false, border: true, align: opts.align || 'left', boxW: opts.boxW || 0 });
      break;
    }

    // ─── Balken ───
    case 'balken':
    case 'balken_schmal':
    case 'balken_breit':
    case 'balken_hoch':
    case 'balken_voll': {
      E.drawBar(px, x, y, opts.width || 60, opts.height || 6, rawPct);
      break;
    }

    case 'balken_label': {
      const bw = opts.width || 50, bh = opts.height || 6;
      E.drawBar(px, x, y, bw, bh, rawPct);
      E.drawText(px, fullText || `${Math.round(rawPct)}%`, x + bw + 2, y, sx, sy);
      break;
    }

    case 'balken_label_in': {
      const bw = opts.width || 60, bh = opts.height || 8;
      E.drawBar(px, x, y, bw, bh, rawPct);
      const label = fullText || `${Math.round(rawPct)}%`;
      const lw = label.length * 6;
      E.drawText(px, label, x + Math.floor((bw - lw) / 2), y + 1, 1, 1);
      break;
    }

    // ─── Gauge ───
    case 'gauge':
    case 'gauge_gross':
    case 'gauge_xl': {
      E.drawGauge(px, rawPct, x, y, opts.radius || 12);
      break;
    }

    // ─── Sparkline ───
    case 'sparkline':
    case 'sparkline_gross':
    case 'sparkline_breit':
    case 'sparkline_voll': {
      const histKey = HISTORY_KEYS[source];
      const data = histKey && history ? (history[histKey] || []) : [];
      E.drawSparkline(px, data, x, y, opts.width || 60, opts.height || 20);
      break;
    }

    case 'laufschrift': {
      const text = opts.text || val || 'Laufschrift';
      const offset = Math.floor(Date.now() / 50) % (text.length * 6 * sx + W);
      E.drawMarquee(px, text, y, offset, sx);
      break;
    }

    // Layout-Elemente
    case 'linie_h': {
      for (let i = 0; i < (opts.width || 60); i++) {
        const px2 = x + i;
        if (px2 >= 0 && px2 < W && y >= 0 && y < H) px[y * W + px2] = 1;
      }
      break;
    }

    case 'linie_v': {
      for (let i = 0; i < (opts.height || 20); i++) {
        const py = y + i;
        if (x >= 0 && x < W && py >= 0 && py < H) px[py * W + x] = 1;
      }
      break;
    }

    case 'rahmen_shape': {
      const rw = opts.width || 40, rh = opts.height || 20;
      E.drawRect(x, y, x + rw - 1, y + rh - 1, (px2, py) => {
        if (px2 >= 0 && px2 < W && py >= 0 && py < H) px[py * W + px2] = 1;
      }, false);
      break;
    }

    case 'block': {
      const rw = opts.width || 40, rh = opts.height || 20;
      E.drawRect(x, y, x + rw - 1, y + rh - 1, (px2, py) => {
        if (px2 >= 0 && px2 < W && py >= 0 && py < H) px[py * W + px2] = 1;
      }, true);
      break;
    }

    case 'section': {
      E.drawSectionHeader(px, opts.text || 'Label', x, y, opts.width || 60);
      break;
    }

    // ─── Animiertes Lüftersymbol ───
    case 'fan_icon':
    case 'fan_icon_gross':
    case 'fan_icon_xl': {
      const sz = opts.size || (display === 'fan_icon_xl' ? 24 : display === 'fan_icon_gross' ? 16 : 8);
      const rpm = parseFloat(val) || 0;
      // Drehgeschwindigkeit proportional zur Drehzahl (0=still, 4000=schnell)
      const speed = Math.min(1, rpm / 3000);
      const frame = speed > 0.01 ? Math.floor(Date.now() / Math.max(80, 500 - speed * 420)) % 4 : 0;
      E.drawFanIcon(px, x, y, sz, frame);
      break;
    }

    case 'fan_icon_rpm': {
      const sz = opts.size || 16;
      const rpm = parseFloat(val) || 0;
      const speed = Math.min(1, rpm / 3000);
      const frame = speed > 0.01 ? Math.floor(Date.now() / Math.max(80, 500 - speed * 420)) % 4 : 0;
      E.drawFanIcon(px, x, y, sz, frame);
      // RPM-Text rechts neben dem Symbol
      const label = `${Math.round(rpm)}${opts.suffix || ''}`;
      E.drawText(px, label, x + sz + 2, y + Math.floor(sz / 2) - 3, sx, sy);
      break;
    }
  }
}

/**
 * Geschaetzte Groesse eines Widgets (fuer Selektion + Vorschau).
 */
export function getWidgetSize(widget) {
  const { display, opts = {}, source } = widget;
  const sx = opts.scaleX ?? 1;
  const sy = opts.scaleY ?? sx;
  const src = getSource(source);

  switch (display) {
    case 'zahl':
    case 'zahl_gross':
    case 'zahl_xl':
    case 'text': {
      const text = (opts.prefix ?? '') + (src?.label ?? opts.text ?? 'Text') + (opts.suffix ?? '');
      return { w: Math.max(text.length * 6 * sx, 6), h: 7 * sy };
    }
    case 'balken':       return { w: opts.width || 60, h: opts.height || 6 };
    case 'balken_label': return { w: (opts.width || 50) + 30, h: Math.max(opts.height || 6, 7) };
    case 'gauge':        return { w: (opts.radius || 12) * 2, h: (opts.radius || 12) + 4 };
    case 'sparkline':    return { w: opts.width || 60, h: opts.height || 20 };
    case 'laufschrift':  return { w: 128, h: 7 * sy };
    case 'linie_h':      return { w: opts.width || 60, h: 1 };
    case 'linie_v':      return { w: 1, h: opts.height || 20 };
    case 'rahmen':
    case 'block':        return { w: opts.width || 40, h: opts.height || 20 };
    case 'section':      return { w: opts.width || 60, h: 7 };
    case 'fan_icon':     return { w: opts.size || 8, h: opts.size || 8 };
    case 'fan_icon_gross': return { w: opts.size || 16, h: opts.size || 16 };
    case 'fan_icon_xl':  return { w: opts.size || 24, h: opts.size || 24 };
    case 'fan_icon_rpm': return { w: (opts.size || 16) + 40, h: opts.size || 16 };
    default:             return { w: 30, h: 7 };
  }
}
