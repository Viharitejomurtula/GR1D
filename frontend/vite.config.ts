import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  // maplibre-gl v6 finds its worker next to its own module; pre-bundling would move it
  optimizeDeps: { exclude: ['maplibre-gl'] },
  // The page calls the API at /api (simulate.ts: VITE_API_URL ?? '/api'); in development forward that to the
  // FastAPI server scripts/dev.sh starts on :8080, dropping the prefix (/api/predict -> /predict).
  server: {
    proxy: {
      '/api': { target: 'http://127.0.0.1:8080', changeOrigin: true, rewrite: (path) => path.replace(/^\/api/, '') },
    },
  },
})
