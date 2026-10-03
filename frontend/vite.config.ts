import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

// Dev server (rule 20, docs/02_ARCHITECTURE.md §6): same-origin /api proxy to the backend (no CORS) and the
// Cloudflare quick-tunnel host for phones (Vite rejects unknown Host headers otherwise).
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    strictPort: true,
    allowedHosts: ['.trycloudflare.com'],
    proxy: {
      '/api': { target: 'http://localhost:8080', changeOrigin: false },
    },
  },
});
