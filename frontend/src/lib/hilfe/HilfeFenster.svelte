<script lang="ts">
  /* Freischwebendes, durchsuchbares Hilfefenster mit Sprungmarken. */
  import { ui } from '$lib/stores/ui.svelte';
  import Fenster from '$lib/bausteine/Fenster.svelte';
  import { ABSCHNITTE } from './inhalt';

  let { onschliessen }: { onschliessen: () => void } = $props();
  let suche = $state('');
  let textfeld = $state<HTMLDivElement | null>(null);

  const begriff = $derived(suche.trim().toLowerCase());
  const treffer = $derived(begriff ? ABSCHNITTE.filter((a) => a.html.toLowerCase().includes(begriff) || a.titel.toLowerCase().includes(begriff)) : ABSCHNITTE);

  function markiere(html: string): string {
    if (!begriff) return html;
    const muster = new RegExp(`(>[^<]*?)(${begriff.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
    return html.replace(muster, '$1<mark>$2</mark>');
  }

  $effect(() => {
    const ziel = ui.hilfeAbschnitt;
    const el = textfeld?.querySelector(`#hilfe-${ziel}`);
    el?.scrollIntoView({ block: 'start' });
  });
</script>

<Fenster titel="Hilfe" symbol="fa-question" groesse="schwebend" {onschliessen}>
  <div style="display:flex;flex-direction:column;gap:12px;height:100%">
    <div class="suche"><i class="fa-solid fa-magnifying-glass"></i><input class="feld" bind:value={suche} placeholder="Suchen ..." title="Volltextsuche in der Hilfe; Treffer werden hervorgehoben"></div>
    <div class="hilfe-inhalt">
      <nav>
        {#each treffer as a (a.id)}
          <a href="#hilfe-{a.id}" class:active={ui.hilfeAbschnitt === a.id} onclick={(e) => { e.preventDefault(); ui.hilfeAbschnitt = a.id; }}>{a.titel}</a>
        {/each}
      </nav>
      <div class="hilfe-text" bind:this={textfeld}>
        {#each treffer as a (a.id)}
          <section id="hilfe-{a.id}">{@html markiere(a.html)}</section>
        {/each}
        {#if treffer.length === 0}<p>Nichts gefunden.</p>{/if}
      </div>
    </div>
  </div>
</Fenster>

<style>
  section { margin-bottom: 26px; }
</style>
