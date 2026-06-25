import { test, expect } from '@playwright/test';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const dashboardPath = path.resolve(__dirname, '../fixtures/test-dashboard.html');
const cycleTimePath = path.resolve(__dirname, '../fixtures/test-dashboard-cycle-time.html');

test.describe('Cycle Time Features', () => {
  test('without cycle time: no cycle time chart in team view', async ({ page }) => {
    await page.goto(`file://${dashboardPath}`);
    await expect(page.locator('[data-testid="chart-team-cycle-time"]')).not.toBeVisible();
  });

  test('with cycle time: cycle time chart visible in team view', async ({ page }) => {
    await page.goto(`file://${cycleTimePath}`);
    await expect(page.locator('[data-testid="chart-team-cycle-time"]')).toBeVisible();
  });

  test('without cycle time: no cycle time chart in detail view', async ({ page }) => {
    await page.goto(`file://${dashboardPath}`);
    await page.getByTestId('tab-overview').click();
    await expect(page.locator('[data-testid="chart-project-cycle-time"]')).not.toBeVisible();
  });

  test('with cycle time: project cycle time chart visible in detail view', async ({ page }) => {
    await page.goto(`file://${cycleTimePath}`);
    await page.getByTestId('tab-overview').click();
    await expect(page.locator('[data-testid="chart-project-cycle-time"]')).toBeVisible();
  });

  test('team chart does not grow on hover', async ({ page }) => {
    await page.goto(`file://${cycleTimePath}`);
    const chart = page.locator('[data-testid="chart-team-cycle-time"]');
    await expect(chart).toBeVisible();
    const before = await chart.boundingBox();
    const canvas = chart.locator('canvas');
    await canvas.hover({ position: { x: 100, y: 100 } });
    await page.waitForTimeout(1000);
    await canvas.hover({ position: { x: 150, y: 80 } });
    await page.waitForTimeout(1000);
    const after = await chart.boundingBox();
    expect(after!.height).toBe(before!.height);
  });
});
