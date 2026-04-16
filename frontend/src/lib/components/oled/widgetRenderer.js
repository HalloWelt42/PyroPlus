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
  if (!src && display !== 'linie_h' && display !== 'linie_v' && display !== 'rahmen' && display !== 'block' && display !== 'section') return;

  const sx = opts.scaleX ?? 1;
  const sy = opts.scaleY ?? sx;
  const hasEx = opts.invert || opts.border || (opts.align && opts.align !== 'left');

  // Wert holen
  const val = src?.getValue ? String(src.getValue(stats, weather, opts)) : (opts.text ?? '');
  const rawPct = src?.getRaw ? src.getRaw(stats, weather, opts) : parseFloat(val) || 0;
  const fullText = (opts.prefix ?? '') + val + (opts.suffix ?? '');

  switch (display) {
    case 'zahl':
    case 'zahl_gross':
    case 'zahl_xl':
    case 'text': {
      if (hasEx) {
        E.drawTextEx(px, fullText, x, y, sx, sy, {
          invert: !!opts.invert, border: !!opts.border,
          align: opts.align || 'left', boxW: opts.boxW || 0,
        });
      } else {
        E.drawText(px, fullText, x, y, sx, sy);
      }
      break;
    }

    case 'balken': {
      E.drawBar(px, x, y, opts.width || 60, opts.height || 6, rawPct);
      break;
    }

    case 'balken_label': {
      const bw = opts.width || 50, bh = opts.height || 6;
      E.drawBar(px, x, y, bw, bh, rawPct);
      E.drawText(px, fullText || `${Math.round(rawPct)}%`, x + bw + 2, y, sx, sy);
      break;
    }

    case 'gauge': {
      E.drawGauge(px, rawPct, x, y, opts.radius || 12);
      break;
    }

    case 'sparkline': {
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

    case 'rahmen': {
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
    default:             return { w: 30, h: 7 };
  }
}
