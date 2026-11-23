import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// Mesmo esquema do TaskFlow do professor: em desenvolvimento o Vite
// repassa /api para o Flask (localhost:5000), entao nao ha problema de CORS.
export default defineConfig({
  plugins: [vue()],
  build: {
    // o mermaid (diagrama do banco no painel admin) e grande, mas so carrega naquela aba
    chunkSizeWarningLimit: 2000
  },
  test: {
    environment: 'node',
    include: ['src/**/*.test.js']
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true
      }
    }
  }
})
