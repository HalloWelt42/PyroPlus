<script>
  let { id, icon, label, collapsible = true, open = true, onDragStart, children } = $props();
  let isOpen = $state(open);
  const handleSvg = '<svg width="10" height="16" viewBox="0 0 10 16"><circle cx="3" cy="3" r="1.5" fill="currentColor"/><circle cx="7" cy="3" r="1.5" fill="currentColor"/><circle cx="3" cy="8" r="1.5" fill="currentColor"/><circle cx="7" cy="8" r="1.5" fill="currentColor"/><circle cx="3" cy="13" r="1.5" fill="currentColor"/><circle cx="7" cy="13" r="1.5" fill="currentColor"/></svg>';
</script>

<div class="pw" data-panel-id={id}>
  <div class="pw-bar">
    <div class="pw-handle" draggable="true" ondragstart={(e) => onDragStart?.(e, id)} title="Verschieben">{@html handleSvg}</div>
    <button class="pw-title" onclick={() => { if (collapsible) isOpen = !isOpen; }}>
      <i class="fa-solid {icon}"></i>
      <span>{label}</span>
      {#if collapsible}<i class="fa-solid fa-chevron-down pw-chev" class:rotated={!isOpen}></i>{/if}
    </button>
  </div>
  {#if isOpen || !collapsible}
    <div class="pw-body">{@render children()}</div>
  {/if}
</div>

<style>
  .pw { background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--radius); overflow: hidden; }
  .pw-bar { display: flex; align-items: stretch; background: var(--bg-elevated); user-select: none; flex-shrink: 0; width: 100%; }
  .pw-title { background: none; border: none; cursor: pointer; text-align: left; }
  .pw-handle { width: 28px; flex-shrink: 0; display: flex; align-items: center; justify-content: center; cursor: grab; color: var(--text-muted); position: relative; }
  .pw-handle::after { content:''; position:absolute; right:0; top:4px; bottom:4px; width:2px; border-radius:1px; background:var(--border); }
  .pw-handle:hover { background: rgba(0,232,138,0.08); color: var(--green); }
  .pw-handle:hover::after { background: var(--green); }
  .pw-title { flex:1; display:flex; align-items:center; gap:8px; padding:8px 10px; color:var(--text-secondary); font:600 var(--fs-sm) var(--font); text-transform:uppercase; letter-spacing:0.06em; }
  .pw-title i:first-child { color: var(--accent); }
  .pw-chev { font-size: var(--fs-xs); color: var(--text-muted); transition: transform 150ms; margin-left: auto; }
  .pw-chev.rotated { transform: rotate(-90deg); }
  .pw-body { padding: 10px; display: flex; flex-direction: column; gap: 8px; }
</style>
