<script lang="ts">
  import { oled } from '$lib/stores/oled.svelte';
  import { ui } from '$lib/stores/ui.svelte';
  import Schalter from '$lib/bausteine/Schalter.svelte';

  let ziehId = $state<string | null>(null);
  let ueberId = $state<string | null>(null);
  let umbenennenId = $state<string | null>(null);
  let umbenennenText = $state('');
  let loeschenId = $state<string | null>(null);
  let loeschenTimer: ReturnType<typeof setTimeout> | null = null;

  function bild(id: string): string | null {
    if (oled.entwurf?.id === id && oled.bild && !oled.probe) return oled.bild;
    return oled.vorschaubilder[id] ?? null;
  }

  function start(e: DragEvent, id: string): void {
    ziehId = id;
    e.dataTransfer?.setData('text/plain', id);
    if (e.dataTransfer) e.dataTransfer.effectAllowed = 'move';
  }
  function ueber(e: DragEvent, id: string): void { e.preventDefault(); ueberId = id; }
  function ablegen(e: DragEvent, zielId: string): void {
    e.preventDefault();
    if (!ziehId || ziehId === zielId) { ziehId = null; ueberId = null; return; }
    const ids = oled.screens.map((s) => s.id);
    const von = ids.indexOf(ziehId);
    const nach = ids.indexOf(zielId);
    ids.splice(von, 1);
    ids.splice(nach, 0, ziehId);
    void oled.umsortieren(ids);
    ziehId = null;
    ueberId = null;
  }

  function umbenennenStart(id: string, name: string): void { umbenennenId = id; umbenennenText = name; }
  function umbenennenEnde(): void {
    if (umbenennenId && umbenennenText.trim()) void oled.bildschirmEigenschaft(umbenennenId, { name: umbenennenText.trim() });
    umbenennenId = null;
  }

  function loeschenAnfragen(id: string): void {
    if (loeschenId === id) { void oled.loeschen(id); loeschenId = null; return; }
    loeschenId = id;
    if (loeschenTimer) clearTimeout(loeschenTimer);
    loeschenTimer = setTimeout(() => (loeschenId = null), 3000);
  }
</script>

<section class="spalte spalte-bildschirme">
  <div class="spalte-kopf"><span>Bildschirme</span><span class="badge badge-neutral">{oled.screens.length}</span></div>
  <div class="spalte-inhalt">
    {#each oled.screens as s (s.id)}
      {@const aktiv = oled.aktiverBildschirmId === s.id}
      {@const gewaehlt = oled.entwurf?.id === s.id}
      <div class="bs-karte" class:active={gewaehlt} class:ziel={aktiv} class:ueber={ueberId === s.id}
        role="button" tabindex="0" draggable="true"
        title={gewaehlt ? 'Wird gerade bearbeitet' : 'Klick zum Bearbeiten, ziehen zum Umsortieren'}
        onclick={() => { if (!gewaehlt) oled.waehle(s.id); }}
        onkeydown={(e) => { if (e.key === 'Enter') oled.waehle(s.id); }}
        ondragstart={(e) => start(e, s.id)} ondragover={(e) => ueber(e, s.id)} ondrop={(e) => ablegen(e, s.id)} ondragend={() => { ziehId = null; ueberId = null; }}>
        <div class="bs-bild">
          {#if bild(s.id)}<img src="data:image/png;base64,{bild(s.id)}" alt={s.name}>{:else}<div class="bs-leer"></div>{/if}
        </div>
        <div class="bs-zeile">
          <i class="fa-solid fa-grip-vertical bs-griff"></i>
          {#if umbenennenId === s.id}
            <!-- svelte-ignore a11y_autofocus -->
            <input class="feld bs-eingabe" bind:value={umbenennenText} autofocus onblur={umbenennenEnde}
              onkeydown={(e) => { if (e.key === 'Enter') umbenennenEnde(); if (e.key === 'Escape') umbenennenId = null; e.stopPropagation(); }}
              onclick={(e) => e.stopPropagation()}>
          {:else}
            <span class="bs-name" title="Doppelklick zum Umbenennen" ondblclick={(e) => { e.stopPropagation(); umbenennenStart(s.id, s.name); }}>{s.name || 'Ohne Namen'}</span>
          {/if}
          {#if oled.screens.length > 1}
            <button class="bs-x" class:warnung={loeschenId === s.id} title={loeschenId === s.id ? 'Noch einmal klicken: endgültig löschen' : 'Bildschirm löschen'}
              onclick={(e) => { e.stopPropagation(); loeschenAnfragen(s.id); }}>
              <i class="fa-solid {loeschenId === s.id ? 'fa-triangle-exclamation' : 'fa-xmark'}"></i>
            </button>
          {/if}
        </div>
        <div class="bs-meta">
          {#if aktiv}
            <span class="bs-marke"><i class="fa-solid fa-circle-dot"></i>Auf dem Display</span>
          {:else if !s.enabled}
            <span class="bs-marke aus">Nicht in Rotation</span>
          {:else}
            <span class="bs-marke aus">{s.duration ?? oled.zustand?.rotationInterval ?? 10} s</span>
          {/if}
          <Schalter an={s.enabled} klein titel="Nimmt an der Rotation teil" onwahl={(an) => oled.bildschirmEigenschaft(s.id, { enabled: an })} />
        </div>
      </div>
    {/each}
  </div>
  <div class="spalte-fuss">
    <button class="btn btn-accent btn-breit" title="Leeren Bildschirm anlegen" onclick={() => oled.neuerBildschirm()}><i class="fa-solid fa-plus"></i>Neuer Bildschirm</button>
    <div class="btn-reihe">
      <button class="btn btn-klein" title="Fertigen Bildschirm aus den Vorlagen einfügen" onclick={() => (ui.fenster = 'vorlagen')}><i class="fa-solid fa-layer-group"></i>Vorlage</button>
      <button class="btn btn-klein" title="Bearbeiteten Bildschirm kopieren" disabled={!oled.entwurf} onclick={() => { if (oled.entwurf) void oled.duplizieren(oled.entwurf.id); }}><i class="fa-solid fa-copy"></i>Kopie</button>
    </div>
  </div>
</section>

<style>
  .bs-karte.ueber { border-color: var(--accent); }
  .bs-leer { width: 192px; height: 96px; background: #000; }
  .bs-eingabe { height: 32px; padding: 0 8px; flex: 1; min-width: 0; }
  .bs-x { width: 28px; height: 28px; border-radius: 6px; color: var(--text-muted); display: inline-flex; align-items: center; justify-content: center; flex-shrink: 0; }
  .bs-x:hover { background: rgba(255,255,255,0.06); color: var(--text-primary); }
  .bs-x.warnung { background: var(--red-glow); color: var(--red); }
  .btn:disabled { opacity: 0.5; cursor: default; }
</style>
