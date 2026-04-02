<script>
  let { widgets, onPlace } = $props();
  const catIcons = { zeit: 'fa-clock', sys: 'fa-microchip', deko: 'fa-pen' };
</script>

<div class="ws">
  {#each ['zeit','sys','deko'] as cat}
    {@const items = widgets.filter(w => w.cat === cat)}
    {#if items.length > 0}
      <div class="ws-group">
        <span class="ws-cat"><i class="fa-solid {catIcons[cat]}"></i></span>
        {#each items as w}
          <button class="ws-item" onclick={() => onPlace(w)} title="{w.label} ({w.w}×{w.h})">
            {w.label}
          </button>
        {/each}
      </div>
    {/if}
  {/each}
</div>

<style>
  .ws { flex-shrink: 0; background: var(--bg-base); border-bottom: 1px solid var(--border); padding: 4px 8px; display: flex; gap: 4px; overflow-x: auto; align-items: center; }
  .ws-group { display: flex; gap: 3px; align-items: center; }
  .ws-cat { color: var(--accent); font-size: var(--fs-xs); padding: 0 4px; }
  .ws-item {
    padding: 4px 10px; border-radius: var(--radius-sm);
    border: 1px solid var(--border); background: var(--bg-card);
    color: var(--text-secondary); cursor: pointer;
    font: 500 var(--fs-xs) var(--font); white-space: nowrap;
    transition: all 120ms;
  }
  .ws-item:hover { border-color: var(--accent); color: var(--accent); }
</style>
