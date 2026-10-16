import { defineConfig } from '@playwright/test'

const soak = process.env.CARVUE_SOAK === '1'
const port = soak ? 5180 : 5173

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  workers: 1,
  timeout: 90_000,
  expect: { timeout: 12_000 },
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    baseURL: `http://127.0.0.1:${port}`,
    browserName: 'chromium',
    trace: soak ? 'off' : 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: ['chrome', 'msedge'].flatMap(channel => [
    { name: `${channel}-1280`, use: { channel, viewport: { width: 1280, height: 720 } } },
    { name: `${channel}-1920`, use: { channel, viewport: { width: 1920, height: 1080 } } },
  ]),
  webServer: {
    command: `${process.platform === 'win32' ? 'npm.cmd' : 'npm'} run dev -- --port ${port}`,
    url: `http://127.0.0.1:${port}`,
    reuseExistingServer: !soak,
    stdout: soak ? 'pipe' : 'ignore',
    timeout: 60_000,
  },
})
