import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  base: './',
  server: { port: 5173, strictPort: true, watch: { ignored: ['**/artifacts/**', '**/assets/source/**', '**/tools/**'] } },
  optimizeDeps: {
    entries: ['index.html'],
    // Keep source mappings without embedding third-party source text in every response.
    rolldownOptions: { output: { sourcemapExcludeSources: true } },
  },
  test: { include: ['src/**/*.test.ts'] },
  build: { rollupOptions: { output: { manualChunks: (id) => id.includes('/node_modules/three/') ? 'three' : undefined } } },
})
