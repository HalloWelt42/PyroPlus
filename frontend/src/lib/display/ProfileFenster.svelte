<script lang="ts">
  import { oled } from '$lib/stores/oled.svelte';
  import { ui } from '$lib/stores/ui.svelte';
  import Fenster from '$lib/bausteine/Fenster.svelte';

  let { onschliessen }: { onschliessen: () => void } = $props();
  let neuerName = $state('');
  let loeschenId = $state<string | null>(null);
  let ersetzenBestaetigen = $state(false);
  let dateiErsetzen = false;
  let dateiEingabe = $state<HTMLInputElement | null>(null);
  const alt = $derived(oled.alteSicherung());

  function datum(iso: string): string { return new Date(iso).toLocaleDateString('de-DE'); }
  function importWaehlen(ersetzen: boolean): void {
    if (ersetzen && !ersetzenBestaetigen) { ersetzenBestaetigen = true; setTimeout(() => (ersetzenBestaetigen = false), 4000); return; }
    ersetzenBestaetigen = false;
    dateiErsetzen = ersetzen;
    dateiEingabe?.click();
  }
  async function dateiGewaehlt(e: Event): Promise<void> {
    const datei = (e.currentTarget as HTMLInputElement).files?.[0];
    if (datei) await oled.importieren(datei, dateiErsetzen);
    if (dateiEingabe) dateiEingabe.value = '';
  }
</script>

<Fenster titel="Profile und Sicherung" symbol="fa-box-archive" groesse="mittel" hilfe="profile" {onschliessen}>
  <div style="display:flex;flex-direction:column;gap:16px">
    <div class="gruppe">
      <div class="gruppe-titel"><i class="fa-solid fa-bookmark"></i>Profile<span class="badge badge-neutral" style="margin-left:auto">Zusammenstellungen aller Bildschirme</span></div>
      <p style="color:var(--text-secondary);font-size:var(--fs-sm)">Ein Profil sichert alle Bildschirme und das Wechselintervall unter einem Namen. Laden ersetzt die aktuellen Bildschirme.</p>
      {#if oled.profile.length}
        <div class="liste">
          {#each oled.profile as p (p.id)}
            <div class="eintrag">
              <div class="symbol"><i class="fa-solid fa-bookmark"></i></div>
              <div class="text"><div class="titel">{p.name}</div><div class="unter">{p.screens.length} {p.screens.length === 1 ? 'Bildschirm' : 'Bildschirme'} · Wechsel alle {p.rotationInterval} s · gesichert am {datum(p.created)}</div></div>
              <div class="aktionen">
                <button class="btn btn-klein btn-accent" title="Dieses Profil laden; die aktuellen Bildschirme werden ersetzt" onclick={() => oled.profilLaden(p.id)}><i class="fa-solid fa-download"></i>Laden</button>
                <button class="btn btn-klein" title="Aktuellen Stand unter diesem Namen neu sichern" onclick={() => oled.profilSichern(p.name)}><i class="fa-solid fa-floppy-disk"></i></button>
                <button class="btn btn-klein btn-symbol btn-gefahr" class:active={loeschenId === p.id} title={loeschenId === p.id ? 'Noch einmal klicken: löschen' : 'Profil löschen; die Bildschirme bleiben'}
                  onclick={() => { if (loeschenId === p.id) { void oled.profilLoeschen(p.id); loeschenId = null; } else { loeschenId = p.id; setTimeout(() => (loeschenId = null), 3000); } }}>
                  <i class="fa-solid {loeschenId === p.id ? 'fa-triangle-exclamation' : 'fa-trash-can'}"></i>
                </button>
              </div>
            </div>
          {/each}
        </div>
      {:else}
        <p style="color:var(--text-muted);font-size:var(--fs-sm)">Noch kein Profil gesichert.</p>
      {/if}
      <div class="feld-zeile">
        <input class="feld" placeholder="Neues Profil, z. B. Werkstatt" bind:value={neuerName} title="Name des neuen Profils" onkeydown={(e) => { if (e.key === 'Enter' && neuerName.trim()) { void oled.profilSichern(neuerName.trim()); neuerName = ''; } }}>
        <button class="btn btn-primary" disabled={!neuerName.trim()} title="Aktuellen Stand als neues Profil sichern" onclick={() => { void oled.profilSichern(neuerName.trim()); neuerName = ''; }}><i class="fa-solid fa-floppy-disk"></i>Sichern</button>
      </div>
    </div>

    <div class="gruppe">
      <div class="gruppe-titel"><i class="fa-solid fa-file-export"></i>Sicherung als Datei</div>
      <p style="color:var(--text-secondary);font-size:var(--fs-sm)">Der Export enthält Bildschirme, Bausteine, Profile und Wetterorte als eine Datei. Beim Import kannst du ergänzen oder alles ersetzen.</p>
      <div class="btn-reihe">
        <button class="btn" title="Alles als Datei herunterladen" onclick={() => oled.exportieren()}><i class="fa-solid fa-download"></i>Exportieren</button>
        <button class="btn" title="Datei wählen und Inhalte ergänzen" onclick={() => importWaehlen(false)}><i class="fa-solid fa-upload"></i>Importieren, ergänzen</button>
        <button class="btn btn-gefahr" title="Datei wählen und den gesamten Bestand ersetzen" onclick={() => importWaehlen(true)}><i class="fa-solid fa-triangle-exclamation"></i>{ersetzenBestaetigen ? 'Wirklich ersetzen?' : 'Importieren, ersetzen'}</button>
      </div>
      <input type="file" accept="application/json,.json" bind:this={dateiEingabe} onchange={dateiGewaehlt} style="display:none">
    </div>

    {#if alt}
      <div class="gruppe">
        <div class="gruppe-titel"><i class="fa-solid fa-clock-rotate-left"></i>Alte Sicherung aus diesem Browser</div>
        <p style="color:var(--text-secondary);font-size:var(--fs-sm)">Die frühere Version hat Bildschirme, Städte und Vorlagen im Browser gespeichert. Gefunden: <b style="color:var(--text-primary)">{alt.screens.length} Bildschirme, {alt.weatherCities.length} Städte, {alt.widgetPresets.length} Widget-Vorlagen, {alt.profiles.length} Profile</b>. Nach der Übernahme liegen sie sicher auf dem Pi.</p>
        <div class="btn-reihe">
          <button class="btn btn-accent" title="Gefundene Daten ins Backend übernehmen, vorhandene bleiben" onclick={() => oled.alteSicherungUebernehmen()}><i class="fa-solid fa-arrow-right-to-bracket"></i>Übernehmen</button>
          <button class="btn" title="Alte Browserdaten verwerfen; diese Meldung erscheint nicht mehr" onclick={() => { oled.alteSicherungVerwerfen(); ui.toast('Alte Browserdaten verworfen', 'info'); onschliessen(); }}>Verwerfen</button>
        </div>
      </div>
    {/if}
  </div>
  {#snippet fuss()}
    <div class="rechts"><button class="btn" onclick={onschliessen}>Schließen</button></div>
  {/snippet}
</Fenster>

<style>
  .btn:disabled { opacity: 0.45; cursor: default; }
</style>
