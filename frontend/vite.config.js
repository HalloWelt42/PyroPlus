import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';

export default defineConfig({
  plugins: [svelte()],
  server: {
    port: 5173,
    proxy: {
      '/api': { target: 'http://192.168.178.49:8071', changeOrigin: true },
      '/ws': { target: 'ws://192.168.178.49:8071', ws: true },
    }
  }
});
