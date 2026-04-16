<script>
  let { visible = $bindable(false) } = $props();
  let activeCrypto = $state(null);
  let copyFeedback = $state(null);

  const cryptos = [
    { id: 'btc', label: 'BITCOIN', symbol: 'BTC', icon: 'fa-brands fa-bitcoin', color: '#f7931a', address: 'bc1qnd599khdkv3v3npmj9ufxzf6h4fzanny2acwqr', qrUrl: 'https://api.qrserver.com/v1/create-qr-code/?size=150x150&data=bitcoin:bc1qnd599khdkv3v3npmj9ufxzf6h4fzanny2acwqr' },
    { id: 'doge', label: 'DOGECOIN', symbol: 'DOGE', icon: 'fa-solid fa-dog', color: '#c3a634', address: 'DL7tuiYCqm3xQjMDXChdxeQxqUGMACn1ZV', qrUrl: 'https://api.qrserver.com/v1/create-qr-code/?size=150x150&data=dogecoin:DL7tuiYCqm3xQjMDXChdxeQxqUGMACn1ZV' },
    { id: 'eth', label: 'ETHEREUM', symbol: 'ETH', icon: 'fa-brands fa-ethereum', color: '#627eea', address: '0x8A28fc47bFFFA03C8f685fa0836E2dBe1CA14F27', qrUrl: 'https://api.qrserver.com/v1/create-qr-code/?size=150x150&data=ethereum:0x8A28fc47bFFFA03C8f685fa0836E2dBe1CA14F27' },
  ];

  function close() { activeCrypto = null; visible = false; }
  function selectCrypto(id) { activeCrypto = activeCrypto === id ? null : id; }
  async function copyAddress(addr) {
    try { await navigator.clipboard.writeText(addr); copyFeedback = addr; setTimeout(() => copyFeedback = null, 2000); } catch {}
  }
</script>

{#if visible}
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div class="overlay" onclick={(e) => { if (e.target === e.currentTarget) close(); }} onkeydown={(e) => { if (e.key === 'Escape') close(); }}>
    <div class="panel">
      <button class="x" onclick={close}><i class="fa-solid fa-xmark"></i></button>

      <div class="heart-icon"><i class="fa-solid fa-heart"></i></div>
      <h2>PyroPlus unterstützen</h2>
      <p class="desc">PyroPlus ist ein nicht-kommerzielles Open-Source-Projekt. Wenn es dir gefällt und du die Entwicklung unterstützen möchtest, freue ich mich über eine kleine Aufmerksamkeit.</p>

      <a href="https://ko-fi.com/HalloWelt42" target="_blank" rel="noopener" class="kofi">
        <i class="fa-solid fa-mug-hot"></i> Unterstütze mich auf Ko-fi
      </a>

      <div class="sep"><span class="sep-line"></span><span class="sep-text">ODER PER KRYPTOWÄHRUNG</span><span class="sep-line"></span></div>

      <div class="coins">
        {#each cryptos as c}
          <button class="coin" class:active={activeCrypto===c.id} onclick={()=>selectCrypto(c.id)}>
            <div class="coin-icon" style="color:{c.color}"><i class={c.icon}></i></div>
            <span class="coin-name">{c.symbol}</span>
          </button>
        {/each}
      </div>

      {#each cryptos as c}
        {#if activeCrypto === c.id}
          <div class="detail">
            <img class="qr-img" src={c.qrUrl} alt="{c.symbol} QR Code" width="120" height="120" />
            <span class="detail-label">{c.label}</span>
            <code class="detail-addr">{c.address}</code>
            <button class="copy" onclick={()=>copyAddress(c.address)}>
              <i class="fa-solid {copyFeedback===c.address?'fa-check':'fa-copy'}"></i>
              {copyFeedback===c.address?'Kopiert':'Adresse kopieren'}
            </button>
          </div>
        {/if}
      {/each}

      <div class="foot"><i class="fa-solid fa-heart"></i> Vielen Dank für deine Unterstützung!</div>
    </div>
  </div>
{/if}

<style>
  .overlay { position: fixed; inset: 0; z-index: 1000; display: flex; align-items: center; justify-content: center; background: rgba(0,0,0,0.6); backdrop-filter: blur(4px); animation: fadeIn 0.2s ease; }
  @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
  .panel { position: relative; display: flex; flex-direction: column; align-items: center; gap: 1.2rem; padding: 2rem; max-width: 480px; width: 90vw; max-height: 90vh; overflow-y: auto; background: var(--bg-base); border: 1px solid var(--border); border-radius: 12px; box-shadow: 0 24px 48px rgba(0,0,0,0.4); animation: slideUp 0.25s ease; }
  @keyframes slideUp { from { opacity: 0; transform: translateY(16px); } to { opacity: 1; transform: translateY(0); } }
  .x { position: absolute; top: 10px; right: 10px; width: 28px; height: 28px; display: flex; align-items: center; justify-content: center; background: none; border: 1px solid transparent; border-radius: 6px; color: var(--text-muted); cursor: pointer; }
  .x:hover { background: rgba(255,255,255,0.05); color: var(--text-primary); border-color: var(--border); }
  .heart-icon { width: 48px; height: 48px; border-radius: 50%; background: rgba(204,34,68,0.1); border: 1px solid rgba(204,34,68,0.3); display: flex; align-items: center; justify-content: center; font-size: 20px; color: #cc2244; animation: pulse 2s infinite; }
  @keyframes pulse { 0%,100% { transform: scale(1); } 50% { transform: scale(1.08); } }
  h2 { font: 700 var(--fs-lg) var(--font); color: var(--text-primary); margin: 0; }
  .desc { font: 400 var(--fs-sm) var(--font); color: var(--text-muted); text-align: center; line-height: 1.7; margin: 0; max-width: 400px; }
  .kofi { display: flex; align-items: center; gap: 8px; padding: 10px 24px; background: var(--accent); border: none; border-radius: 999px; color: #fff; font: 700 var(--fs-sm) var(--font); text-decoration: none; cursor: pointer; transition: all 0.15s; }
  .kofi:hover { filter: brightness(1.15); transform: translateY(-1px); }
  .kofi i { font-size: 16px; }
  .sep { display: flex; align-items: center; gap: 10px; width: 100%; }
  .sep-line { flex: 1; height: 1px; background: var(--border); }
  .sep-text { font: 700 9px var(--font); letter-spacing: 1.5px; color: var(--text-muted); white-space: nowrap; }
  .coins { display: flex; gap: 10px; }
  .coin { display: flex; flex-direction: column; align-items: center; gap: 6px; padding: 12px 20px; background: var(--bg-surface); border: 1px solid var(--border); border-radius: 8px; cursor: pointer; transition: all 0.15s; }
  .coin:hover { background: var(--bg-elevated); transform: translateY(-2px); }
  .coin.active { border-color: var(--accent); }
  .coin-icon { font-size: 20px; }
  .coin-name { font: 700 10px var(--mono); color: var(--text-secondary); }
  .qr-img { border-radius: 6px; background: #fff; padding: 6px; }
  .detail { display: flex; flex-direction: column; align-items: center; gap: 8px; padding: 12px; background: var(--bg-surface); border: 1px solid var(--border); border-radius: 8px; width: 100%; }
  .detail-label { font: 700 9px var(--font); letter-spacing: 1px; color: var(--text-muted); }
  .detail-addr { font: 400 10px var(--mono); color: var(--text-primary); word-break: break-all; text-align: center; padding: 6px; background: var(--bg-elevated); border-radius: 4px; }
  .copy { display: flex; align-items: center; gap: 6px; padding: 6px 14px; background: none; border: 1px solid var(--border); border-radius: 6px; color: var(--text-muted); font: 600 10px var(--font); cursor: pointer; }
  .copy:hover { border-color: var(--accent); color: var(--accent); }
  .foot { font: 500 var(--fs-xs) var(--font); color: var(--text-muted); display: flex; align-items: center; gap: 6px; }
  .foot i { color: #cc2244; }
</style>
