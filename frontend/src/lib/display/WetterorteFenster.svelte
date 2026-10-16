<script lang="ts">
  import { onMount } from 'svelte';
  import { oled } from '$lib/stores/oled.svelte';
  import type { GeocodeHit } from '$lib/api/types';
  import Fenster from '$lib/bausteine/Fenster.svelte';

  let { onschliessen }: { onschliessen: () => void } = $props();
  let suche = $state('');
  let treffer = $state<GeocodeHit[]>([]);
  let sucheTimer: ReturnType<typeof setTimeout> | null = null;
  let loeschenId = $state<string | null>(null);

  onMount(() => { void oled.ladeOrte(); });

  function eingabe(): void {
    if (sucheTimer) clearTimeout(sucheTimer);
    if (suche.trim().length < 2) { treffer = []; return; }
    sucheTimer = setTimeout(async () => { treffer = await oled.ortSuchen(suche.trim()); }, 300);
  }
  async function hinzufuegen(t: GeocodeHit): Promise<void> {
    await oled.ortHinzufuegen({ name: t.name, lat: t.lat, lon: t.lon, country: t.country });
    suche = ''; treffer = [];
  }
  function alter(iso: string | null): string {
    if (!iso) return 'noch nicht geladen';
    const min = Math.round((Date.now() - new Date(iso).getTime()) / 60000);
    return min < 1 ? 'gerade geladen' : `vor ${min} Minuten geladen`;
  }
</script>

<Fenster titel="Wetterorte" symbol="fa-cloud-sun" groesse="mittel" hilfe="wetterorte" {onschliessen}>
  {#snippet kopf()}
    <span class="badge badge-neutral">{oled.orte.length} {oled.orte.length === 1 ? 'Ort' : 'Orte'}</span>
    <button class="btn btn-klein" style="margin-left:8px" title="Alle Orte jetzt neu laden" onclick={() => oled.ortAktualisieren()}><i class="fa-solid fa-rotate"></i>Alle laden</button>
  {/snippet}
  <div style="display:flex;flex-direction:column;gap:16px">
    <p style="color:var(--text-secondary);font-size:var(--fs-sm)">Wetter-Widgets zeigen den Vorgabeort, wenn im Widget kein anderer Ort gewählt ist. Die Werte werden alle 10 Minuten geladen.</p>
    {#if oled.orte.length === 0}
      <div class="leer" style="padding:10px"><div class="symbol"><i class="fa-solid fa-location-dot"></i></div><h3>Noch kein Ort</h3><p>Unten eine Stadt suchen und hinzufügen. Der erste Ort wird der Vorgabeort.</p></div>
    {/if}
    <div class="liste">
      {#each oled.orte as o (o.location.id)}
        <div class="eintrag">
          <div class="symbol"><i class="fa-solid {o.isDefault ? 'fa-house' : 'fa-location-dot'}"></i></div>
          <div class="text">
            <div class="titel">{o.location.name}
              {#if o.isDefault}<span class="badge badge-info">Vorgabe</span>{:else if o.ok}<span class="badge badge-ok">Geladen</span>{:else}<span class="badge badge-warn">Wird geladen</span>{/if}
            </div>
            <div class="unter">{o.summary ? `${o.summary} · ` : ''}{alter(o.fetchedAt)} · {o.location.lat.toFixed(2)}, {o.location.lon.toFixed(2)}{o.location.country ? ` · ${o.location.country}` : ''}</div>
          </div>
          <div class="aktionen">
            {#if !o.isDefault}<button class="btn btn-klein" title="Als Vorgabeort für alle Wetter-Widgets ohne eigenen Ort setzen" onclick={() => oled.ortVorgabe(o.location.id)}>Vorgabe</button>{/if}
            <button class="btn btn-klein btn-symbol" title="Diesen Ort jetzt neu laden" onclick={() => oled.ortAktualisieren(o.location.id)}><i class="fa-solid fa-rotate"></i></button>
            <button class="btn btn-klein btn-symbol btn-gefahr" class:active={loeschenId === o.location.id} title={loeschenId === o.location.id ? 'Noch einmal klicken: entfernen' : 'Ort entfernen; Widgets mit diesem Ort zeigen dann den Vorgabeort'}
              onclick={() => { if (loeschenId === o.location.id) { void oled.ortLoeschen(o.location.id); loeschenId = null; } else { loeschenId = o.location.id; setTimeout(() => (loeschenId = null), 3000); } }}>
              <i class="fa-solid {loeschenId === o.location.id ? 'fa-triangle-exclamation' : 'fa-trash-can'}"></i>
            </button>
          </div>
        </div>
      {/each}
    </div>
    <div class="gruppe">
      <div class="gruppe-titel"><i class="fa-solid fa-plus"></i>Ort hinzufügen</div>
      <div class="suche"><i class="fa-solid fa-magnifying-glass"></i><input class="feld" bind:value={suche} oninput={eingabe} placeholder="Stadt eingeben, mindestens zwei Buchstaben" title="Suche über die Ortsdatenbank des Wetterdienstes"></div>
      {#if treffer.length}
        <div class="treffer">
          {#each treffer as t (t.name + t.lat + t.lon)}
            <button onclick={() => hinzufuegen(t)}><span>{t.name}</span><span class="land">{[t.country, t.admin].filter(Boolean).join(', ')}</span></button>
          {/each}
        </div>
      {:else if suche.trim().length >= 2}
        <p style="color:var(--text-muted);font-size:var(--fs-sm)">Keine Treffer.</p>
      {/if}
    </div>
  </div>
  {#snippet fuss()}
    <span style="color:var(--text-muted);font-size:var(--fs-sm)">Quelle der Werte: freier Wetterdienst ohne Anmeldung.</span>
    <div class="rechts"><button class="btn" onclick={onschliessen}>Schließen</button></div>
  {/snippet}
</Fenster>
