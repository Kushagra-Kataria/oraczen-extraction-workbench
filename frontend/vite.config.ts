import react from '@vitejs/plugin-react';
import { loadEnv } from 'vite';
import { defineConfig } from 'vitest/config';

export default defineConfig(({ mode }) => {
  // Both services read the example configuration from the repository root.
  const env = loadEnv(mode, '..', '');
  return {
    plugins: [react()],
    envDir: '..',
    test: {
      environment: 'jsdom',
      globals: true,
      setupFiles: ['./src/test/setup.ts'],
    },
    server: {
      port: 5173,
      strictPort: true,
      proxy: { '/api': env.BACKEND_URL || 'http://127.0.0.1:8000' },
    },
  };
});
