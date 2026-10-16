import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';
import { fileURLToPath } from 'node:url';
import { readFileSync } from 'node:fs';

/* Die Version kommt ausschließlich aus version.json im Wurzelverzeichnis
   (im Docker-Bau liegt eine Kopie unter /version.json). */
function leseVersion(): string {
  for (const pfad of ['../version.json', '/version.json']) {
    try {
      const daten = JSON.parse(readFileSync(new URL(pfad, import.meta.url), 'utf-8'));
      return String(daten.voll ?? daten.version ?? '0.0.0');
    } catch {
      continue;
    }
  }
  return 'v0.0.0';
}

export default defineConfig({
  plugins: [svelte()],
  publicDir: 'static',
  define: { __APP_VERSION__: JSON.stringify(leseVersion()) },
  resolve: { alias: { $lib: fileURLToPath(new URL('./src/lib', import.meta.url)) } },
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '/api': { target: 'http://localhost:8071', changeOrigin: true },
      '/ws': { target: 'ws://localhost:8071', ws: true },
    },
  },
});
