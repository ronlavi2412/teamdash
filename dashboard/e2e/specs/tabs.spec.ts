import { test, expect } from '@playwright/test';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const dashboardPath = path.resolve(__dirname, '../fixtures/test-dashboard.html');

test.describe('Tab Navigation', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`file://${dashboardPath}`);
  });

  test('default tab is Overall Team View', async ({ page }) => {
    const teamTabBtn = page.locator('[data-testid="tab-bar"] [data-testid="tab-team"]');
    await expect(teamTabBtn).toHaveClass(/active/);
    // The team view content div is rendered
    await expect(page.locator('div[data-testid="tab-team"]')).toBeVisible();
  });

  test('clicking Detailed View tab switches content', async ({ page }) => {
    await page.getByTestId('tab-overview').click();
    await expect(page.getByTestId('tab-overview').first()).toHaveClass(/active/);
    await expect(page.locator('[data-testid="tab-overview"]').last()).toBeVisible();
  });

  test('clicking Full Table tab switches content', async ({ page }) => {
    await page.getByTestId('tab-table').click();
    await expect(page.getByTestId('tab-table').first()).toHaveClass(/active/);
    await expect(page.getByTestId('main-table')).toBeVisible();
  });

  test('clicking Configuration tab switches content', async ({ page }) => {
    await page.getByTestId('tab-config').click();
    await expect(page.getByTestId('tab-config').first()).toHaveClass(/active/);
    await expect(page.locator('[data-testid="tab-config"]').last()).toBeVisible();
  });

  test('only one tab content is visible at a time', async ({ page }) => {
    // Team is active by default
    await expect(page.locator('[data-testid="tab-team"]').last()).toBeVisible();
    await expect(page.locator('[data-testid="main-table"]')).not.toBeVisible();

    // Switch to table
    await page.getByTestId('tab-table').click();
    await expect(page.getByTestId('main-table')).toBeVisible();
    // Team view should no longer be visible (re-rendered away by React)
  });

  test('tab active state moves correctly', async ({ page }) => {
    const teamTabBtn = page.locator('[data-testid="tab-bar"] [data-testid="tab-team"]');
    const overviewTabBtn = page.locator('[data-testid="tab-bar"] [data-testid="tab-overview"]');

    await expect(teamTabBtn).toHaveClass(/active/);
    await expect(overviewTabBtn).not.toHaveClass(/active/);

    await overviewTabBtn.click();
    await expect(overviewTabBtn).toHaveClass(/active/);
    await expect(teamTabBtn).not.toHaveClass(/active/);
  });
});
