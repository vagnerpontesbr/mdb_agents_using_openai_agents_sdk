import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  build: { assetsInlineLimit: 0 },
  server: {
    port: 5173,
    strictPort: true,
    // Browser and API use the same origin in development. Configure APP_ORIGIN
    // as http://127.0.0.1:5173 for this mode; do not trust forwarded identity.
    proxy: { '/api': 'http://127.0.0.1:8000', '/healthz': 'http://127.0.0.1:8000' },
  },
});
