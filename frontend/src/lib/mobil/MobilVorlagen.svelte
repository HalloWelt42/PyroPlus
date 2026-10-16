<script lang="ts">
  /* Vorlage einfügen mit Drücken und Halten; ein kurzes Tippen fügt nichts ein. */
  import { onMount } from 'svelte';
  import { oled } from '$lib/stores/oled.svelte';

  let { onzurueck }: { onzurueck: () => void } = $props();
  let kategorie = $state('Alle');
  let halten = $state<{ id: string; anteil: number } | null>(null);
  let timer: ReturnType<typeof setInterval> | null = null;
  const DAUER = 900;

  onMount(() => { void oled.ladeVorlagen(); });
  const kategorien = $derived(['Alle', ...(oled.vorlagen?.categories.filter((k) => oled.vorlagen?.screens.some((s) => s.category === k)) ?? [])]);
  const liste = $derived((oled.vorlagen?.screens ?? []).filter((t) => kategorie === 'Alle' || t.category === kategorie));

  function start(id: string, e: PointerEvent): void {
    e.preventDefault();
    const begonnen = Date.now();
    halten = { id, anteil: 0 };
    if (timer) clearInterval(timer);
    timer = setInterval(async () => {
      const anteil = Math.min(1, (Date.now() - begonnen) / DAUER);
      halten = { id, anteil };
      if (anteil >= 1) {
        ende();
        await oled.ausVorlage(id);
        onzurueck();
      }
    }, 40);
  }
  function ende(): void {
    if (timer) clearInterval(timer);
    timer = null;
    halten = null;
  }
</script>

<div class="mobil-kopf">
  <button class="btn btn-klein" style="width:44px;height:44px;padding:0" title="Zurück zum Display" onclick={onzurueck}><i class="fa-solid fa-arrow-left"></i></button>
  <h1>Vorlage einfügen</h1>
</div>
<div class="mobil-inhalt">
  <div class="chips">
    {#each kategorien as k (k)}<button class="chip" class:active={kategorie === k} onclick={() => (kategorie = k)}>{k}</button>{/each}
  </div>
  {#each liste as t (t.id)}
    <div class="mobil-karte" class:active={halten?.id === t.id}>
      {#if oled.vorlagenbilder[t.id]}<img src="data:image/png;base64,{oled.vorlagenbilder[t.id]}" alt="">{:else}<div style="width:128px;height:64px;background:#000"></div>{/if}
      <div class="text"><div class="name">{t.name}</div><div class="unter">{halten?.id === t.id ? `Halten ... ${Math.round(halten.anteil * 100)} %` : t.description}</div></div>
      <button class="btn halten" class:btn-primary={halten?.id === t.id} class:btn-accent={halten?.id !== t.id} title="Drücken und halten fügt die Vorlage ein"
        onpointerdown={(e) => start(t.id, e)} onpointerup={ende} onpointercancel={ende} onpointerleave={ende} oncontextmenu={(e) => e.preventDefault()}>
        {#if halten?.id === t.id}<span class="ring" style="background:conic-gradient(var(--green) 0 {halten.anteil * 100}%, rgba(255,255,255,0.14) {halten.anteil * 100}% 100%)"></span>{/if}
        <i class="fa-solid fa-plus"></i>
      </button>
    </div>
  {/each}
  <p class="hinweis">Drücken und halten, bis der Ring voll ist. Ein kurzes Tippen fügt nichts ein.</p>
</div>

<style>
  .hinweis { font-size: 15px; color: var(--text-muted); text-align: center; }
  .halten { touch-action: none; }
  .mobil-karte .unter { display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
</style>
