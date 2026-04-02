import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';

export default defineConfig({
  plugins: [svelte()],
  publicDir: 'static',
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8071',
        changeOrigin: true,
      },
      // WebSocket läuft NICHT über Vite-Proxy.
      // Frontend verbindet direkt auf Port 8071 (siehe client.js).
    },
  },
});
