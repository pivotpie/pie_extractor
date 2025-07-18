import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  define: {
    'process.env': {}
  },
  server: {
    port: 8080,
    host: '0.0.0.0',
    strictPort: true,
    proxy: {
      // Proxy API requests to your backend
      '/api': {
        target: 'http://localhost:8002',
        changeOrigin: true,
        secure: false,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
      // Add Clerk proxy for development
      '/clerk': {
        target: 'https://clerk.your-app-name.lcl.dev',
        changeOrigin: true,
        secure: false,
        rewrite: (path) => path.replace(/^\/clerk/, '')
      }
    },
  },
  optimizeDeps: {
    esbuildOptions: {
      // Node.js global to browser globalThis
      define: {
        global: 'globalThis',
      },
    },
  },
});