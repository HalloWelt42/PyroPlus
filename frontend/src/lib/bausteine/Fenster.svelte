<script lang="ts">
  import type { Snippet } from 'svelte';
  import { ui } from '$lib/stores/ui.svelte';
  /* Fenster über der Ansicht. groesse mitte = breit, mittel = schmal, schwebend = frei verschiebbar. */
  let { titel, symbol, groesse = 'mittel', hilfe = '', onschliessen, kopf, children, fuss }: {
    titel: string; symbol: string; groesse?: 'mitte' | 'mittel' | 'schwebend'; hilfe?: string;
    onschliessen: () => void; kopf?: Snippet; children: Snippet; fuss?: Snippet;
  } = $props();

  let links = $state<number | null>(null);
  let oben = $state<number | null>(null);
  let ziehen: { dx: number; dy: number } | null = null;

  function start(e: PointerEvent): void {
    if (groesse !== 'schwebend') return;
    const ziel = (e.currentTarget as HTMLElement).parentElement as HTMLElement;
    const r = ziel.getBoundingClientRect();
    links = r.left; oben = r.top;
    ziehen = { dx: e.clientX - r.left, dy: e.clientY - r.top };
    (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
  }
  function bewege(e: PointerEvent): void {
    if (!ziehen) return;
    links = Math.max(0, e.clientX - ziehen.dx);
    oben = Math.max(0, e.clientY - ziehen.dy);
  }
  function ende(): void { ziehen = null; }
  function taste(e: KeyboardEvent): void { if (e.key === 'Escape') onschliessen(); }
</script>

<svelte:window onkeydown={taste} />

{#if groesse !== 'schwebend'}
  <div class="schleier" onclick={onschliessen} role="presentation"></div>
{/if}
<div class="fenster {groesse}" style={links !== null ? `left:${links}px;top:${oben}px;right:auto;transform:none` : ''} role="dialog" aria-label={titel}>
  <div class="fenster-kopf" onpointerdown={start} onpointermove={bewege} onpointerup={ende}>
    <h2><i class="fa-solid {symbol}"></i>{titel}</h2>
    {#if kopf}{@render kopf()}{/if}
    <div class="rechts">
      {#if hilfe}
        <button class="btn btn-klein" style="width:36px;padding:0" title="Hilfe zu diesem Fenster" onclick={() => ui.oeffneHilfe(hilfe)}><i class="fa-solid fa-question"></i></button>
      {/if}
      <button class="btn btn-klein" style="width:36px;padding:0" title="Schließen" onclick={onschliessen}><i class="fa-solid fa-xmark"></i></button>
    </div>
  </div>
  <div class="fenster-inhalt">{@render children()}</div>
  {#if fuss}<div class="fenster-fuss">{@render fuss()}</div>{/if}
</div>
