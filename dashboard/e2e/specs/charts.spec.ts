import { test, expect } from '@playwright/test';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const dashboardPath = path.resolve(__dirname, '../fixtures/test-dashboard.html');
const scoringPath = path.resolve(__dirname, '../fixtures/test-dashboard-scoring.html');

test.describe('Chart Rendering', () => {
  test('team view renders chart canvases', async ({ page }) => {
    await page.goto(`file://${dashboardPath}`);
    // Team view has PRs, Reviews, and Merge Time charts
    const canvases = page.locator('[data-testid="tab-team"] canvas');
    await expect(canvases).toHaveCount(3);
  });

  test('team view renders 5 chart canvases with scoring', async ({ page }) => {
    await page.goto(`file://${scoringPath}`);
    const canvases = page.locator('[data-testid="tab-team"] canvas');
    await expect(canvases).toHaveCount(5);
  });

  test('detail view renders chart canvases', async ({ page }) => {
    await page.goto(`file://${dashboardPath}`);
    await page.getByTestId('tab-overview').click();
    const canvases = page.locator('[data-testid="tab-overview"] canvas');
    await expect(canvases).toHaveCount(3);
  });

  test('detail view renders 5 chart canvases with scoring', async ({ page }) => {
    await page.goto(`file://${scoringPath}`);
    await page.getByTestId('tab-overview').click();
    const canvases = page.locator('[data-testid="tab-overview"] canvas');
    await expect(canvases).toHaveCount(5);
  });

  test('chart canvases have non-zero dimensions', async ({ page }) => {
    await page.goto(`file://${dashboardPath}`);
    const canvas = page.locator('[data-testid="tab-team"] canvas').first();
    const box = await canvas.boundingBox();
    expect(box).not.toBeNull();
    expect(box!.width).toBeGreaterThan(0);
    expect(box!.height).toBeGreaterThan(0);
  });
});
