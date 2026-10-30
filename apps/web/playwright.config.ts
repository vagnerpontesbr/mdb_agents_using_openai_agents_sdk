import { defineConfig } from '@playwright/test';

const port = Number(process.env.TELECOM_TEST_PORT ?? '53181');
if (!Number.isInteger(port) || port < 1024 || port > 65535) throw new Error('Invalid test port');
const origin = `http://127.0.0.1:${port}`;

export default defineConfig({
  testDir: './e2e',
  workers: 1,
  retries: 0,
  use: { baseURL: origin, browserName: 'chromium' },
  webServer: {
    command: 'cd ../.. && uv run --frozen python -m tests.foundation.browser_server',
    url: `${origin}/healthz`,
    env: { TELECOM_TEST_PORT: String(port) },
    reuseExistingServer: false,
    timeout: 60_000,
  },
});
