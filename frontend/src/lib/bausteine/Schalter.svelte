<script lang="ts">
  let { an, klein = false, titel = '', onwahl }: { an: boolean; klein?: boolean; titel?: string; onwahl: (an: boolean) => void } = $props();
</script>

<button type="button" class="schalter" class:on={an} class:klein title={titel} role="switch" aria-checked={an} onclick={() => onwahl(!an)}></button>
