<script lang="ts">
  import { onDestroy, onMount } from 'svelte';
  import { live } from '$lib/stores/live.svelte';
  import { ui } from '$lib/stores/ui.svelte';
  import { fassungVerfolgen } from '$lib/stores/fassung.svelte';
  import Seitenleiste from '$lib/Seitenleiste.svelte';
  import Hinweise from '$lib/bausteine/Hinweise.svelte';
  import FassungBand from '$lib/bausteine/FassungBand.svelte';
  import DisplayView from '$lib/display/DisplayView.svelte';
  import LuefterView from '$lib/luefter/LuefterView.svelte';
  import LedView from '$lib/leds/LedView.svelte';
  import MobilApp from '$lib/mobil/MobilApp.svelte';
  import HilfeFenster from '$lib/hilfe/HilfeFenster.svelte';

  onMount(() => { ui.start(); void live.start(); return fassungVerfolgen(); });
  onDestroy(() => live.stop());
</script>

<Hinweise />

{#if ui.mobil}
  <MobilApp />
{:else}
  <div class="app" class:eng={ui.knapp || !ui.seitenleisteOffen} class:schwebt={ui.knapp && ui.schwebendOffen}>
    <Seitenleiste />
    <div class="hauptbereich">
      <FassungBand />
      {#if ui.ansicht === 'display'}
        <DisplayView />
      {:else if ui.ansicht === 'fan'}
        <LuefterView />
      {:else}
        <LedView />
      {/if}
    </div>
  </div>
  {#if ui.fenster === 'hilfe' && ui.ansicht !== 'display'}
    <HilfeFenster onschliessen={() => (ui.fenster = null)} />
  {/if}
{/if}

<style>
  .app.eng { --sb: 64px; }
  /* Schmales Fenster: ausgeklappte Leiste liegt über dem Inhalt statt ihn zu verdrängen */
  .app.schwebt { grid-template-columns: minmax(0, 1fr); padding-left: 64px; box-sizing: border-box; }
  .app.schwebt :global(.sidebar) { position: fixed; z-index: 40; top: 0; left: 0; bottom: 0; width: 240px; box-shadow: 8px 0 32px rgba(0,0,0,0.6); }
</style>
