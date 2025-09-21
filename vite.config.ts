import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  base: '/redditsearchtool/',
  server: {
    proxy: {
      '/api': 'http://localhost:5001'
    }
  },
  build: {
    outDir: 'dist'
  }
})
