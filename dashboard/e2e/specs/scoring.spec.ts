import { test, expect } from '@playwright/test';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const dashboardPath = path.resolve(__dirname, '../fixtures/test-dashboard.html');
const scoringPath = path.resolve(__dirname, '../fixtures/test-dashboard-scoring.html');

test.describe('Scoring Conditional Features', () => {
  test('without scoring: no complexity charts in team view', async ({ page }) => {
    await page.goto(`file://${dashboardPath}`);
    await expect(page.locator('[data-testid="chart-team-sp"]')).not.toBeVisible();
    await expect(page.locator('[data-testid="chart-team-review-sp"]')).not.toBeVisible();
  });

  test('with scoring: complexity charts visible in team view', async ({ page }) => {
    await page.goto(`file://${scoringPath}`);
    await expect(page.locator('[data-testid="chart-team-sp"]')).toBeVisible();
    await expect(page.locator('[data-testid="chart-team-review-sp"]')).toBeVisible();
  });

  test('without scoring: no complexity charts in detail view', async ({ page }) => {
    await page.goto(`file://${dashboardPath}`);
    await page.getByTestId('tab-overview').click();
    await expect(page.locator('[data-testid="chart-complexity-trend"]')).not.toBeVisible();
    await expect(page.locator('[data-testid="chart-review-complexity-trend"]')).not.toBeVisible();
  });

  test('with scoring: complexity charts visible in detail view', async ({ page }) => {
    await page.goto(`file://${scoringPath}`);
    await page.getByTestId('tab-overview').click();
    await expect(page.locator('[data-testid="chart-complexity-trend"]')).toBeVisible();
    await expect(page.locator('[data-testid="chart-review-complexity-trend"]')).toBeVisible();
  });

  test('with scoring: config tab shows scoring thresholds', async ({ page }) => {
    await page.goto(`file://${scoringPath}`);
    await page.getByTestId('tab-config').click();
    const configTab = page.locator('[data-testid="tab-config"]').last();
    await expect(configTab).toContainText('Scoring Configuration');
    await expect(configTab).toContainText('Complexity Points per Size');
    await expect(configTab).toContainText('Classification Thresholds');
  });

  test('without scoring: config tab has no scoring section', async ({ page }) => {
    await page.goto(`file://${dashboardPath}`);
    await page.getByTestId('tab-config').click();
    const configTab = page.locator('[data-testid="tab-config"]').last();
    await expect(configTab).not.toContainText('Scoring Configuration');
  });

  test('with scoring: table includes complexity columns', async ({ page }) => {
    await page.goto(`file://${scoringPath}`);
    await page.getByTestId('tab-table').click();
    const table = page.getByTestId('main-table');
    await expect(table).toContainText('Complexity');
  });
});
