<script>
  import { W, H, drawText, drawRect, composite, compositeToDataUrl } from './engine.js';
  let { widgets, onPlace } = $props();

  /* Mini-Vorschau für jedes Widget generieren */
  function widgetPreview(w) {
    const px = new Uint8Array(W * H);
    const tmpSet = (x, y, v) => { if (x >= 0 && x < W && y >= 0 && y < H) px[y * W + x] = v ? 1 : 0; };
    // Draw-Funktion auf temporären Buffer umleiten
    const oldPx = px;
    w.draw(2, 2, tmpSet);
    // Zu DataURL konvertieren (nur Widget-Bereich)
    const c = document.createElement('canvas');
    c.width = w.w + 4; c.height = w.h + 4;
    const ctx = c.getContext('2d');
    ctx.fillStyle = '#111'; ctx.fillRect(0, 0, c.width, c.height);
    ctx.fillStyle = '#fff';
    for (let y = 0; y < c.height && y < H; y++)
      for (let x = 0; x < c.width && x < W; x++)
        if (px[y * W + x]) ctx.fillRect(x, y, 1, 1);
    return c.toDataURL();
  }
</script>

<div class="widget-strip">
  <div class="strip-scroll">
    {#each widgets as w}
      <button class="widget-item" onclick={() => onPlace(w)} title="{w.label} ({w.w}×{w.h})">
        <span class="widget-label">{w.label}</span>
        <span class="widget-size">{w.w}×{w.h}</span>
      </button>
    {/each}
  </div>
</div>

<style>
  .widget-strip { flex-shrink: 0; background: var(--bg-base); border-bottom: 1px solid var(--border); padding: 6px 10px; }
  .strip-scroll { display: flex; gap: 6px; overflow-x: auto; align-items: center; }
  .widget-item {
    flex-shrink: 0; padding: 6px 12px; border-radius: var(--radius-sm);
    border: 1px dashed var(--border); background: var(--bg-card);
    color: var(--text-secondary); cursor: pointer;
    font: 500 var(--fs-sm) var(--font);
    display: flex; align-items: center; gap: 8px;
    transition: all 150ms; white-space: nowrap;
  }
  .widget-item:hover { border-color: var(--accent); color: var(--accent); border-style: solid; }
  .widget-size { font: 500 var(--fs-xs) var(--mono); color: var(--text-muted); }
</style>
