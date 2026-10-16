<script lang="ts">
  import { onDestroy, onMount } from 'svelte';
  import { live } from '$lib/stores/live.svelte';
  import { ui } from '$lib/stores/ui.svelte';
  import Seitenleiste from '$lib/Seitenleiste.svelte';
  import Hinweise from '$lib/bausteine/Hinweise.svelte';
  import DisplayView from '$lib/display/DisplayView.svelte';
  import LuefterView from '$lib/luefter/LuefterView.svelte';
  import LedView from '$lib/leds/LedView.svelte';
  import MobilApp from '$lib/mobil/MobilApp.svelte';
  import HilfeFenster from '$lib/hilfe/HilfeFenster.svelte';

  onMount(() => { ui.start(); void live.start(); });
  onDestroy(() => live.stop());
</script>

<Hinweise />

{#if ui.mobil}
  <MobilApp />
{:else}
  <div class="app" class:eng={!ui.seitenleisteOffen}>
    <Seitenleiste />
    {#if ui.ansicht === 'display'}
      <DisplayView />
    {:else if ui.ansicht === 'fan'}
      <LuefterView />
    {:else}
      <LedView />
    {/if}
  </div>
  {#if ui.fenster === 'hilfe' && ui.ansicht !== 'display'}
    <HilfeFenster onschliessen={() => (ui.fenster = null)} />
  {/if}
{/if}

<style>
  .app.eng { --sb: 64px; }
</style>
