import { test, expect } from '@playwright/test';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const dashboardPath = path.resolve(__dirname, '../fixtures/test-dashboard.html');

test.describe('Responsive Layout', () => {
  test('desktop: chart grid has 2 columns', async ({ page }) => {
    await page.setViewportSize({ width: 1200, height: 800 });
    await page.goto(`file://${dashboardPath}`);

    const chartRow = page.locator('.chart-row').first();
    const style = await chartRow.evaluate(el => window.getComputedStyle(el).gridTemplateColumns);
    // Should have two columns
    const columns = style.split(' ').filter(s => s.trim());
    expect(columns.length).toBe(2);
  });

  test('mobile: chart grid collapses to 1 column', async ({ page }) => {
    await page.setViewportSize({ width: 600, height: 800 });
    await page.goto(`file://${dashboardPath}`);

    const chartRow = page.locator('.chart-row').first();
    const style = await chartRow.evaluate(el => window.getComputedStyle(el).gridTemplateColumns);
    const columns = style.split(' ').filter(s => s.trim());
    expect(columns.length).toBe(1);
  });

  test('table is scrollable on narrow viewport', async ({ page }) => {
    await page.setViewportSize({ width: 600, height: 800 });
    await page.goto(`file://${dashboardPath}`);
    await page.getByTestId('tab-table').click();
    const tableWrapper = page.locator('[data-testid="tab-table"] [style*="overflow"]');
    await expect(tableWrapper).toBeVisible();
  });
});
