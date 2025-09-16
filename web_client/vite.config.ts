import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Uwaga: jeśli potrzebujesz, możesz dodać proxy do WS/HTTP.
// Domyślnie łączymy się bezpośrednio przez VITE_WS_URL.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true
  },
  envPrefix: 'VITE_'
})
