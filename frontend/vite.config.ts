// Vite config for the Quarter Roadmap Co-Pilot dashboard.
// - Dev server on :5173 proxies /api and /health to the FastAPI backend on :8080.
// - Production build outputs to submission_frontend/static/spa/ so FastAPI
//   serves the SPA alongside its JSON API from one origin (codelab 09 pattern).

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

const API_TARGET = 'http://127.0.0.1:8080'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      '/api': API_TARGET,
      '/health': API_TARGET,
    },
  },
  build: {
    outDir: '../submission_frontend/static/spa',
    emptyOutDir: true,
  },
})
