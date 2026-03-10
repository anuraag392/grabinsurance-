import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'
import { fileURLToPath } from 'url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      // '@data/mock_deals.json' → <root>/../data/mock_deals.json
      '@data': path.resolve(__dirname, '../data'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/get-insurance-quote': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
