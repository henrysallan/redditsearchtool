import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  base: '/',
  server: {
    proxy: {
      '/api': {
        target: process.env.VITE_API_URL || 'http://localhost:5001',
        changeOrigin: true
      }
    }
  },
  build: {
    outDir: 'dist'
  },
  define: {
    // Make environment variables available to the client
    'process.env.VITE_API_URL': JSON.stringify(process.env.VITE_API_URL)
  }
})
