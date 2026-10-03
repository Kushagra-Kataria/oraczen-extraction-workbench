import react from '@vitejs/plugin-react';
import { defineConfig, loadEnv } from 'vite';

export default defineConfig(({ mode }) => {
  // Both services read the example configuration from the repository root.
  const env = loadEnv(mode, '..', '');
  return {
    plugins: [react()],
    envDir: '..',
    server: {
      port: 5173,
      strictPort: true,
      proxy: { '/api': env.BACKEND_URL || 'http://127.0.0.1:8000' },
    },
  };
});
