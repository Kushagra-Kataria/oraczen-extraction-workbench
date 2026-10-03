import react from '@vitejs/plugin-react';
import { defineConfig } from 'vitest/config';

// Vite is used only by the test runner; Next.js builds and serves the application.
export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
  },
});
