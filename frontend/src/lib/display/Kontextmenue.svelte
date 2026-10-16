<script lang="ts">
  import { oled } from '$lib/stores/oled.svelte';
  import { ui } from '$lib/stores/ui.svelte';

  let { x, y, onschliessen }: { x: number; y: number; onschliessen: () => void } = $props();
  const ids = $derived(oled.auswahl);
  const mehrere = $derived(ids.length > 1);
  let sichernName = $state('');
  let sichern = $state(false);

  function tu(fn: () => void): void { fn(); onschliessen(); }
  function bausteinSichern(): void {
    const w = oled.gewaehlte[0];
    if (!w || !sichernName.trim()) return;
    void oled.alsBausteinSichern(w, sichernName.trim());
    onschliessen();
  }
</script>

<svelte:window onclick={(e) => { if (!(e.target as HTMLElement).closest('.kontext')) onschliessen(); }} />

<div class="kontext" style="left:{x}px;top:{y}px" role="menu">
  <button onclick={() => tu(() => oled.duplizierenWidgets(ids))}><i class="fa-solid fa-copy"></i>Kopieren{mehrere ? ` (${ids.length} Widgets)` : ''}</button>
  <button onclick={() => tu(() => oled.zentrieren(ids))}><i class="fa-solid fa-align-center"></i>Waagerecht zentrieren</button>
  {#if ids.length > 2}
    <button onclick={() => tu(() => oled.verteilen(ids))}><i class="fa-solid fa-arrows-left-right"></i>Gleichmäßig verteilen</button>
  {/if}
  {#if mehrere}
    <button onclick={() => tu(() => oled.buendig(ids, 'oben'))}><i class="fa-solid fa-arrow-up-short-wide"></i>Oben bündig</button>
    <button onclick={() => tu(() => oled.buendig(ids, 'links'))}><i class="fa-solid fa-align-left"></i>Links bündig</button>
  {/if}
  <div class="trenner"></div>
  <button onclick={() => tu(() => oled.nachVorn(ids))}><i class="fa-solid fa-arrow-up"></i>Nach vorn</button>
  <button onclick={() => tu(() => oled.nachHinten(ids))}><i class="fa-solid fa-arrow-down"></i>Nach hinten</button>
  <div class="trenner"></div>
  {#if !mehrere}
    {#if sichern}
      <div class="sichern">
        <!-- svelte-ignore a11y_autofocus -->
        <input class="feld" placeholder="Name des Bausteins" bind:value={sichernName} autofocus onkeydown={(e) => { if (e.key === 'Enter') bausteinSichern(); }}>
        <button class="btn btn-klein btn-primary" onclick={bausteinSichern}>Sichern</button>
      </div>
    {:else}
      <button onclick={() => { sichern = true; sichernName = oled.gewaehlte[0]?.name ?? ''; }}><i class="fa-solid fa-puzzle-piece"></i>Als Baustein sichern</button>
    {/if}
    {#if oled.gewaehlte[0]?.display === 'bitmap'}
      <button onclick={() => tu(() => { oled.zeichnen = true; })}><i class="fa-solid fa-paintbrush"></i>Zeichnen</button>
    {/if}
  {/if}
  <button class="gefahr" onclick={() => tu(() => { oled.entfernen(ids); ui.toast(mehrere ? 'Widgets entfernt' : 'Widget entfernt'); })}><i class="fa-solid fa-trash-can"></i>Löschen</button>
</div>

<style>
  .sichern { display: flex; gap: 6px; padding: 6px; }
  .sichern .feld { height: 36px; }
</style>
