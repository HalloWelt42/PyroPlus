<script lang="ts">
  import { onDestroy, onMount } from 'svelte';
  import { live } from '$lib/stores/live.svelte';
  import { oled } from '$lib/stores/oled.svelte';
  import { ui } from '$lib/stores/ui.svelte';
  import Schalter from '$lib/bausteine/Schalter.svelte';

  let { onvorlagen }: { onvorlagen: () => void } = $props();
  let helligkeit = $state<number | null>(null);
  let wechsel = $state<number | null>(null);
  let bilderTimer: ReturnType<typeof setInterval> | null = null;

  onMount(() => {
    void oled.laden();
    bilderTimer = setInterval(() => void oled.aktualisiereVorschaubilder(), 5000);
  });
  onDestroy(() => { if (bilderTimer) clearInterval(bilderTimer); });
  $effect(() => { const v = live.oled?.screensVersion; if (v !== undefined && oled.geladen) void oled.abgleich(v); });

  const zustand = $derived(live.oled);
</script>

<div class="mobil-kopf">
  <h1><i class="fa-solid fa-display" style="color:var(--accent);margin-right:10px"></i>Display</h1>
  <span class="temp">{live.cpuTemp.toFixed(1)}°</span>
</div>
<div class="mobil-inhalt">
  <div class="mobil-schirm">
    {#if zustand?.preview && live.oledAn}<img src="data:image/png;base64,{zustand.preview}" alt="Das Display gerade">{:else}<div class="dunkel">Display aus</div>{/if}
  </div>
  <div class="mobil-abschnitt">Betriebsart</div>
  <div class="segment">
    <button class:active={zustand?.mode === 'auto'} onclick={() => oled.einstellungen({ mode: 'auto' })}><i class="fa-solid fa-rotate"></i>Rotation</button>
    <button class:active={zustand?.mode === 'manual'} onclick={() => oled.einstellungen({ mode: 'manual' })}><i class="fa-solid fa-thumbtack"></i>Fest</button>
    <button class:active={zustand?.mode === 'off'} onclick={() => oled.einstellungen({ mode: 'off' })}><i class="fa-solid fa-power-off"></i>Aus</button>
  </div>
  <div class="mobil-regler"><span class="label">Helligkeit</span><input type="range" min="0" max="255" value={helligkeit ?? zustand?.brightness ?? 0} oninput={(e) => (helligkeit = Number((e.currentTarget as HTMLInputElement).value))} onchange={(e) => { helligkeit = null; void oled.einstellungen({ brightness: Number((e.currentTarget as HTMLInputElement).value) }); }}><span class="wert">{helligkeit ?? zustand?.brightness ?? 0}</span></div>
  <div class="mobil-regler"><span class="label">Wechsel</span><input type="range" min="1" max="120" value={wechsel ?? zustand?.rotationInterval ?? 10} oninput={(e) => (wechsel = Number((e.currentTarget as HTMLInputElement).value))} onchange={(e) => { wechsel = null; void oled.einstellungen({ rotationInterval: Number((e.currentTarget as HTMLInputElement).value) }); }}><span class="wert">{wechsel ?? zustand?.rotationInterval ?? 10} s</span></div>

  <div class="mobil-abschnitt">Bildschirme</div>
  {#each oled.screens as s (s.id)}
    {@const aktiv = zustand?.currentScreenId === s.id}
    <div class="mobil-karte" class:active={aktiv}>
      {#if oled.vorschaubilder[s.id]}<img src="data:image/png;base64,{oled.vorschaubilder[s.id]}" alt="">{:else}<div style="width:128px;height:64px;background:#000"></div>{/if}
      <div class="text"><div class="name">{s.name || 'Ohne Namen'}</div><div class="unter">{aktiv ? 'Auf dem Display' : s.enabled ? `${s.duration ?? zustand?.rotationInterval ?? 10} s` : 'Nicht in Rotation'}</div></div>
      {#if aktiv}
        <Schalter an={s.enabled} klein titel="In der Rotation" onwahl={(an) => oled.bildschirmEigenschaft(s.id, { enabled: an })} />
      {:else}
        <button class="btn btn-accent" title="Jetzt anzeigen" onclick={() => oled.anzeigen(s.id)}><i class="fa-solid fa-eye"></i></button>
      {/if}
    </div>
  {/each}
  <button class="btn btn-breit" style="height:48px" title="Fertigen Bildschirm aus den Vorlagen einfügen" onclick={onvorlagen}><i class="fa-solid fa-layer-group"></i>Vorlage einfügen</button>
  <p class="hinweis">Widgets bearbeiten geht am Rechner. Hier siehst du das Display, schaltest um und wählst Bildschirme.</p>
  <p class="hinweis klein">{ui.frontendVersion} · {live.backendVersion || '?'}</p>
</div>

<style>
  .dunkel { width: 100%; max-width: 384px; aspect-ratio: 2 / 1; display: flex; align-items: center; justify-content: center; color: var(--text-muted); font-size: 16px; }
  .hinweis { font-size: 15px; color: var(--text-muted); text-align: center; }
  .hinweis.klein { font-size: 13px; }
</style>
