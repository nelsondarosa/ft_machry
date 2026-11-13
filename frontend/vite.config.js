import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://localhost:5000',
      '/health': 'http://localhost:5000',
      '/docs': 'http://localhost:5000',
      '/openapi.yaml': 'http://localhost:5000',
    },
  },
})
