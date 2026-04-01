import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';

export default defineConfig({
  plugins: [svelte()],
  server: {
    port: 5173,
    proxy: {
      '/api': { target: 'http://localhost:8071', changeOrigin: true },
      '/ws': { target: 'ws://localhost:8071', ws: true },
    }
  }
});
