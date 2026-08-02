import path from 'node:path'

import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(import.meta.dirname, './src'),
    },
  },
  server: {
    // Binds all interfaces, not just localhost — required for the dev server
    // to be reachable through GitHub Codespaces' port forwarding (or any
    // other container/VM setup), same reasoning as Expo's web preview.
    host: true,
  },
})
