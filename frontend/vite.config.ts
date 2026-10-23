import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/auth': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/users': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/projects': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/tasks': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/goals': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/dashboard': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/documents': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/chat': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/memories': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/knowledge-graph': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/agents': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/actions': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/calendar': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
