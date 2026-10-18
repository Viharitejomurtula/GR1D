import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  // maplibre-gl v6 finds its worker next to its own module; pre-bundling would move it
  optimizeDeps: { exclude: ['maplibre-gl'] },
})
