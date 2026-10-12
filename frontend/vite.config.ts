import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { visualizer } from 'rollup-plugin-visualizer'

export default defineConfig(({ mode }) => ({
  plugins: [
    react(),
    mode === 'analyze' && visualizer({ filename: 'dist/bundle-stats.html', gzipSize: true, brotliSize: true }),
    mode === 'analyze' && visualizer({ filename: 'dist/bundle-stats.json', template: 'raw-data', gzipSize: true, brotliSize: true }),
  ].filter(Boolean),
  build: {
    // Route-level lazy loading reduced the entry chunk by roughly half. The remaining
    // shared Ant Design/React runtime is intentionally cached as one stable vendor chunk.
    chunkSizeWarningLimit: 700,
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '^/api(?:/|$)': 'http://localhost:8000',
    },
  },
}))
