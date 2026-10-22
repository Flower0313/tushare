import react from '@vitejs/plugin-react'
import { visualizer } from 'rollup-plugin-visualizer'
import { defineConfig } from 'vitest/config'

const apiProxyTarget = process.env.TUSHARE_API_PROXY_TARGET ?? 'http://localhost:8000'

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
  test: {
    include: ['src/**/*.{test,spec}.{ts,tsx}'],
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '^/api(?:/|$)': apiProxyTarget,
    },
  },
}))
