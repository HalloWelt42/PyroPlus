<script lang="ts">
  import { oled } from '$lib/stores/oled.svelte';
  import type { Widget } from '$lib/api/types';
  import Eigenschaften from './Eigenschaften.svelte';
  import Hinzufuegen from './Hinzufuegen.svelte';
  import Bausteine from './Bausteine.svelte';

  type Reiter = 'eigenschaften' | 'hinzufuegen' | 'bausteine';
  let reiter = $state<Reiter>('eigenschaften');
  let wechselFuer = $state<Widget | null>(null);
  let inhalt = $state<HTMLDivElement | null>(null);

  /* Aufruf bei Auswahl auf dem Display: dann sind die Eigenschaften gefragt. Einfügen aus Bausteinen
     oder Hinzufügen wählt zwar das neue Widget, der Reiter bleibt aber, damit die Liste stehen bleibt. */
  export function zeigeEigenschaften(): void { wechsle('eigenschaften'); }

  function wechsle(r: Reiter): void {
    reiter = r;
    if (inhalt) inhalt.scrollTop = 0;
    wechselFuer = null;
    if (r !== 'hinzufuegen') oled.setzeProbe(null);
  }
</script>

<section class="spalte spalte-rechts">
  <nav class="reiter">
    <button class:active={reiter === 'eigenschaften'} onclick={() => wechsle('eigenschaften')}><i class="fa-solid fa-sliders"></i>Eigenschaften</button>
    <button class:active={reiter === 'hinzufuegen'} onclick={() => wechsle('hinzufuegen')}><i class="fa-solid fa-plus"></i>Hinzufügen</button>
    <button class:active={reiter === 'bausteine'} onclick={() => wechsle('bausteine')}><i class="fa-solid fa-puzzle-piece"></i>Bausteine</button>
  </nav>
  <div class="spalte-inhalt" bind:this={inhalt}>
    {#if reiter === 'eigenschaften'}
      <Eigenschaften onhinzufuegen={() => wechsle('hinzufuegen')} onbausteine={() => wechsle('bausteine')}
        onquelleWechseln={(w) => { wechselFuer = w; reiter = 'hinzufuegen'; }} />
    {:else if reiter === 'hinzufuegen'}
      <Hinzufuegen {wechselFuer} onfertig={() => { wechselFuer = null; reiter = 'eigenschaften'; }} />
    {:else}
      <Bausteine />
    {/if}
  </div>
</section>
