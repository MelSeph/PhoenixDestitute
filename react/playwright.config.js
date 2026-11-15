import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests/browser',
  workers: 1,
  use: { baseURL: 'http://127.0.0.1:5173', channel: 'msedge', headless: true },
  webServer: [
    { command: 'python tests/django_server.py', url: 'http://127.0.0.1:8000/prototype/', reuseExistingServer: false },
    { command: 'npm run dev', url: 'http://127.0.0.1:5173', reuseExistingServer: false },
  ],
});
