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
      '/ws': {
        target: 'http://localhost:8071',
        ws: true,
        changeOrigin: true,
        rewriteWsOrigin: true,
      },
    },
    // Vite HMR auf separatem Pfad, damit kein Konflikt mit /ws
    hmr: {
      path: '/__vite_hmr',
    },
  },
});
