<script lang="ts">
  /* Regler mit Wertanzeige; onwahl beim Ziehen, onende beim Loslassen. */
  let { wert, min, max, schritt = 1, einheit = '', titel = '', onwahl, onende }: {
    wert: number; min: number; max: number; schritt?: number; einheit?: string; titel?: string;
    onwahl: (wert: number) => void; onende?: (wert: number) => void;
  } = $props();
</script>

<div class="regler" title={titel}>
  <input type="range" {min} {max} step={schritt} value={wert}
    oninput={(e) => onwahl(Number((e.currentTarget as HTMLInputElement).value))}
    onchange={(e) => onende?.(Number((e.currentTarget as HTMLInputElement).value))}>
  <span class="wert">{wert}{einheit}</span>
</div>
