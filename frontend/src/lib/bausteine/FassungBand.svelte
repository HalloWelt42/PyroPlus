<script lang="ts">
  /* Band bei neuer Fassung auf dem Server: sagt, wann sie von selbst lädt (stores/fassung), der Knopf lädt sofort.
     Steht am Rechner über dem Hauptbereich und am Telefon oben in der eigenen Ansicht. */
  import { fassung, ruhig } from '$lib/stores/fassung.svelte';
</script>

{#if fassung.neu}
  <div class="fassung-band" role="status">
    <i class="fa-solid fa-rotate"></i>
    <span>
      <strong>Neue Fassung {fassung.neu} ist da.</strong>
      {ruhig()
        ? 'Beim nächsten Bereichswechsel oder wenn das Fenster wieder nach vorn kommt, lädt PyroPlus sie von selbst.'
        : 'Sie lädt von selbst, sobald der Entwurf gespeichert und kein Fenster mehr offen ist.'}
    </span>
    <button class="btn btn-primary btn-klein" title="Die Seite jetzt mit der neuen Fassung laden" onclick={() => location.reload()}><i class="fa-solid fa-rotate"></i>Jetzt neu laden</button>
  </div>
{/if}

<style>
  .fassung-band { display: flex; flex-wrap: wrap; align-items: center; gap: 10px 14px; padding: 10px 20px; flex-shrink: 0; background: var(--accent-dim); border-bottom: 1px solid var(--border-accent); color: var(--text-primary); font-size: var(--fs-sm); }
  .fassung-band > i { color: var(--accent); }
  .fassung-band > span { flex: 1 1 220px; min-width: 0; }
</style>
