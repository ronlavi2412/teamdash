import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './e2e/specs',
  use: {
    browserName: 'chromium',
  },
  projects: [
    { name: 'chromium', use: { browserName: 'chromium' } },
  ],
});
