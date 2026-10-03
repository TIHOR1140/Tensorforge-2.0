import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/health': 'http://localhost:8000',
      '/predict': 'http://localhost:8000',
      '/batch': 'http://localhost:8000'
    }
  }
});
