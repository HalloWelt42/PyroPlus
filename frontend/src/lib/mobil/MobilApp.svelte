<script lang="ts">
  /* Eigenständige Telefonansicht: sehen, umschalten, wählen. Bearbeiten bleibt am Rechner. */
  import { ui } from '$lib/stores/ui.svelte';
  import { live } from '$lib/stores/live.svelte';
  import MobilDisplay from './MobilDisplay.svelte';
  import MobilVorlagen from './MobilVorlagen.svelte';
  import MobilLuefter from './MobilLuefter.svelte';
  import MobilLeds from './MobilLeds.svelte';
  import FassungBand from '$lib/bausteine/FassungBand.svelte';

  let seite = $state<'display' | 'vorlagen'>('display');
</script>

<div class="mobil">
  <FassungBand />
  {#if ui.ansicht === 'display'}
    {#if seite === 'vorlagen'}
      <MobilVorlagen onzurueck={() => (seite = 'display')} />
    {:else}
      <MobilDisplay onvorlagen={() => (seite = 'vorlagen')} />
    {/if}
  {:else if ui.ansicht === 'fan'}
    <MobilLuefter />
  {:else}
    <MobilLeds />
  {/if}
  <nav class="mobil-fuss">
    <button class:active={ui.ansicht === 'fan'} onclick={() => ui.zeige('fan')}><i class="fa-solid fa-fan"></i>Lüfter</button>
    <button class:active={ui.ansicht === 'leds'} onclick={() => ui.zeige('leds')}><i class="fa-solid fa-lightbulb"></i>LEDs</button>
    <button class:active={ui.ansicht === 'display'} onclick={() => { ui.zeige('display'); seite = 'display'; }}><i class="fa-solid fa-display"></i>Display</button>
  </nav>
  {#if !live.verbunden}<div class="getrennt"><i class="fa-solid fa-plug-circle-xmark"></i>Keine Verbindung zum Backend</div>{/if}
</div>

<style>
  .getrennt { position: fixed; left: 50%; bottom: 96px; transform: translateX(-50%); padding: 8px 14px; border-radius: 99px; background: var(--red-glow); color: var(--red); font-size: 15px; display: flex; gap: 8px; align-items: center; }
</style>
