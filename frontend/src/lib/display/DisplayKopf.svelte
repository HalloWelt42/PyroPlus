<script lang="ts">
  import { oled } from '$lib/stores/oled.svelte';
  import { live } from '$lib/stores/live.svelte';
  import { ui } from '$lib/stores/ui.svelte';
  import Segment from '$lib/bausteine/Segment.svelte';
  import Stufen from '$lib/bausteine/Stufen.svelte';
  import Regler from '$lib/bausteine/Regler.svelte';

  const zustand = $derived(oled.zustand);
  let helligkeit = $state<number | null>(null);
  const helligkeitAnzeige = $derived(helligkeit ?? zustand?.brightness ?? 0);
  const hardwareOk = $derived(!!(zustand?.hardware && live.verbunden));
</script>

<header class="kopf">
  <div class="kopf-zeile">
    <h1><i class="fa-solid fa-display"></i>Display</h1>
    {#if hardwareOk}
      <span class="chip-status" title="Das Display antwortet; Bilder kommen an"><i class="fa-solid fa-circle-check"></i>Verbunden</span>
    {:else}
      <span class="chip-status aus" title="Kein Display erreichbar; die Vorschau funktioniert trotzdem"><i class="fa-solid fa-plug-circle-xmark"></i>Kein Display</span>
    {/if}
    <div class="kopf-rechts">
      <button class="btn" title="Fertige Bildschirme einfügen und danach anpassen" onclick={() => (ui.fenster = 'vorlagen')}><i class="fa-solid fa-layer-group"></i>Vorlagen</button>
      <button class="btn" title="Zusammenstellungen sichern und wechseln, Export und Import" onclick={() => (ui.fenster = 'profile')}><i class="fa-solid fa-box-archive"></i>Profile</button>
      <button class="btn" title="Orte für die Wetterwerte verwalten" onclick={() => (ui.fenster = 'wetterorte')}><i class="fa-solid fa-cloud-sun"></i>Wetterorte</button>
      <button class="btn" style="width:44px;padding:0" title="Hilfe öffnen" onclick={() => ui.oeffneHilfe('display')}><i class="fa-solid fa-question"></i></button>
    </div>
  </div>
  <div class="kopf-zeile">
    <div class="kopf-gruppe">
      <span class="label">Betriebsart</span>
      <Segment wert={zustand?.mode ?? 'auto'} onwahl={(m) => oled.einstellungen({ mode: m as 'auto' | 'manual' | 'off' })} optionen={[
        { wert: 'auto', label: 'Rotation', symbol: 'fa-rotate', titel: 'Alle aktiven Bildschirme der Reihe nach anzeigen, jeweils für das eingestellte Intervall' },
        { wert: 'manual', label: 'Fest', symbol: 'fa-thumbtack', titel: 'Nur den gewählten Bildschirm anzeigen, ohne Wechsel' },
        { wert: 'off', label: 'Aus', symbol: 'fa-power-off', titel: 'Display dunkel schalten; die Bildschirme bleiben erhalten' },
      ]} />
    </div>
    <div class="kopf-gruppe">
      <span class="label">Wechsel alle</span>
      <Stufen wert={zustand?.rotationInterval ?? 10} min={1} max={3600} einheit=" s" titel="Anzeigedauer je Bildschirm bei Rotation, 1 bis 3600 Sekunden"
        onwahl={(v) => oled.einstellungen({ rotationInterval: v })} />
    </div>
    <div class="kopf-gruppe">
      <span class="label">Helligkeit</span>
      <Regler wert={helligkeitAnzeige} min={0} max={255} titel="Helligkeit des Displays von 0 bis 255; niedrige Werte schonen das Display"
        onwahl={(v) => (helligkeit = v)} onende={(v) => { helligkeit = null; void oled.einstellungen({ brightness: v }); }} />
    </div>
  </div>
</header>
