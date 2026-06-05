import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: true, // 네트워크에 노출 (핸드폰 접속 가능)
    port: 5173,
  },
})
