import { existsSync } from 'node:fs';
import { resolve } from 'node:path';
import type { NextConfig } from 'next';

// Support the shared root .env as well as Next's frontend-local environment files.
// Existing process variables take precedence. No server configuration is sent to clients.
const rootEnv = resolve(process.cwd(), '../.env');
if (existsSync(rootEnv)) process.loadEnvFile(rootEnv);

const backendUrl = (process.env.BACKEND_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');

const config: NextConfig = {
  async rewrites() {
    // The browser stays same-origin; FastAPI owns every API endpoint in both dev and production.
    return [{ source: '/api/:path*', destination: `${backendUrl}/api/:path*` }];
  },
};

export default config;
