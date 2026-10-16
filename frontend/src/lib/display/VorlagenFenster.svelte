<script lang="ts">
  import { onMount } from 'svelte';
  import { oled } from '$lib/stores/oled.svelte';
  import Fenster from '$lib/bausteine/Fenster.svelte';

  let { onschliessen }: { onschliessen: () => void } = $props();
  let kategorie = $state('Alle');
  let gewaehlt = $state<string | null>(null);

  onMount(() => { void oled.ladeVorlagen(); });
  const kategorien = $derived(['Alle', ...(oled.vorlagen?.categories.filter((k) => oled.vorlagen?.screens.some((s) => s.category === k)) ?? [])]);
  const liste = $derived((oled.vorlagen?.screens ?? []).filter((t) => kategorie === 'Alle' || t.category === kategorie));
  const gewaehlteVorlage = $derived(liste.find((t) => t.id === gewaehlt) ?? null);

  async function einfuegen(): Promise<void> {
    if (!gewaehlt) return;
    await oled.ausVorlage(gewaehlt);
    onschliessen();
  }
</script>

<Fenster titel="Bildschirmvorlagen" symbol="fa-layer-group" groesse="mitte" hilfe="vorlagen" {onschliessen}>
  {#snippet kopf()}<span class="badge badge-neutral">{oled.vorlagen?.screens.length ?? 0} fertige Bildschirme</span>{/snippet}
  <div class="kategorien">
    {#each kategorien as k (k)}<button class="chip" class:active={kategorie === k} onclick={() => (kategorie = k)}>{k}</button>{/each}
  </div>
  {#if !oled.vorlagen}
    <p style="color:var(--text-muted)">Vorlagen werden geladen ...</p>
  {:else}
    <div class="vorlagen">
      {#each liste as t (t.id)}
        <button class="vorlage" class:active={gewaehlt === t.id} onclick={() => (gewaehlt = t.id)} ondblclick={einfuegen}>
          <div class="bild">{#if oled.vorlagenbilder[t.id]}<img src="data:image/png;base64,{oled.vorlagenbilder[t.id]}" alt={t.name}>{:else}<div style="width:256px;height:128px"></div>{/if}</div>
          <span class="name">{t.name}</span>
          <span class="text">{t.description}</span>
        </button>
      {/each}
    </div>
  {/if}
  {#snippet fuss()}
    <span style="color:var(--text-muted);font-size:var(--fs-sm)">
      {#if gewaehlteVorlage}Gewählt: <b style="color:var(--text-primary)">{gewaehlteVorlage.name}</b>. Wird als eigener Bildschirm eingefügt und ist danach frei bearbeitbar.{:else}Eine Vorlage wählen; Doppelklick fügt sofort ein.{/if}
    </span>
    <div class="rechts">
      <button class="btn" onclick={onschliessen}>Abbrechen</button>
      <button class="btn btn-primary" disabled={!gewaehlt} onclick={einfuegen}><i class="fa-solid fa-plus"></i>Als Bildschirm einfügen</button>
    </div>
  {/snippet}
</Fenster>

<style>
  .btn:disabled { opacity: 0.45; cursor: default; }
</style>
