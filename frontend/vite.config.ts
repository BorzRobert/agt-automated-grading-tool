import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  base: '/agt-automated-grading-tool/',
  plugins: [react()],
})
