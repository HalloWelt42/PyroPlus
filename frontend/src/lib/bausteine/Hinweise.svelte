<script lang="ts">
  import { ui } from '$lib/stores/ui.svelte';
</script>

<div class="hinweise">
  {#each ui.hinweise as h (h.id)}
    <div class="toast toast-{h.art}">
      <i class="fa-solid {h.art === 'fehler' ? 'fa-triangle-exclamation' : h.art === 'info' ? 'fa-circle-info' : 'fa-circle-check'}"></i>{h.text}
    </div>
  {/each}
</div>

<style>
  .hinweise { position: fixed; top: calc(16px + env(safe-area-inset-top, 0px)); right: 16px; z-index: 90; display: flex; flex-direction: column; gap: 8px; pointer-events: none; }
  .toast { position: static; }
  .toast-fehler { border-color: rgba(255,64,96,0.3); background: rgba(255,64,96,0.14); color: var(--red); }
  .toast-info { border-color: var(--border-accent); background: var(--accent-dim); color: var(--accent); }
</style>
