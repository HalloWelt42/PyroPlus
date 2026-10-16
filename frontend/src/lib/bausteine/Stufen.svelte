<script lang="ts">
  /* Wert mit Minus und Plus; Schritt und Grenzen konfigurierbar. */
  let { wert, min, max, schritt = 1, einheit = '', titel = '', onwahl }: {
    wert: number; min: number; max: number; schritt?: number; einheit?: string; titel?: string; onwahl: (wert: number) => void;
  } = $props();
  const setze = (v: number) => onwahl(Math.max(min, Math.min(max, v)));
</script>

<div class="stufen" title={titel}>
  <button type="button" onclick={() => setze(wert - schritt)} aria-label="Weniger"><i class="fa-solid fa-minus"></i></button>
  <span class="wert">{wert}{einheit}</span>
  <button type="button" onclick={() => setze(wert + schritt)} aria-label="Mehr"><i class="fa-solid fa-plus"></i></button>
</div>
