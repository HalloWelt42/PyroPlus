<script lang="ts">
  /* Segmentwahl: genau eine Option aktiv. */
  interface Option { wert: string; label: string; symbol?: string; titel?: string; gesperrt?: boolean; }
  let { optionen, wert, klein = false, titel = '', onwahl }: {
    optionen: Option[]; wert: string; klein?: boolean; titel?: string; onwahl: (wert: string) => void;
  } = $props();
</script>

<div class="segment" class:klein title={titel}>
  {#each optionen as o (o.wert)}
    <button type="button" class:active={o.wert === wert} title={o.titel ?? ''} disabled={o.gesperrt} onclick={() => onwahl(o.wert)}>
      {#if o.symbol}<i class="fa-solid {o.symbol}"></i>{/if}{o.label}
    </button>
  {/each}
</div>
