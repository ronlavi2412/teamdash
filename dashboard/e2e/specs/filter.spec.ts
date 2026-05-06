import { test, expect } from '@playwright/test';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const dashboardPath = path.resolve(__dirname, '../fixtures/test-dashboard.html');

test.describe('Engineer Filter', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`file://${dashboardPath}`);
    await page.getByTestId('tab-overview').click();
  });

  test('shows All Engineers label by default', async ({ page }) => {
    await expect(page.getByTestId('filter-label')).toHaveText('All Engineers');
  });

  test('clicking filter button opens dropdown', async ({ page }) => {
    await page.getByTestId('engineer-filter-btn').click();
    await expect(page.getByTestId('filter-panel')).toBeVisible();
  });

  test('dropdown lists all engineers with checkboxes', async ({ page }) => {
    await page.getByTestId('engineer-filter-btn').click();
    await expect(page.locator('.filter-checkbox')).toHaveCount(2);
    await expect(page.locator('.filter-checkbox').first()).toContainText('Alice');
    await expect(page.locator('.filter-checkbox').last()).toContainText('Bob');
  });

  test('search filters the checkbox list', async ({ page }) => {
    await page.getByTestId('engineer-filter-btn').click();
    await page.getByTestId('engineer-search').fill('ali');
    const visible = page.locator('.filter-checkbox:not(.hidden)');
    await expect(visible).toHaveCount(1);
    await expect(visible.first()).toContainText('Alice');
  });

  test('unchecking an engineer updates filter label', async ({ page }) => {
    await page.getByTestId('engineer-filter-btn').click();
    await page.locator('#engineer-0').uncheck();
    await expect(page.getByTestId('filter-label')).toHaveText('Engineers');
    await expect(page.getByTestId('filter-count')).toHaveText('1');
  });

  test('Clear All updates label to No Engineers', async ({ page }) => {
    await page.getByTestId('engineer-filter-btn').click();
    await page.getByTestId('clear-all-btn').click();
    await expect(page.getByTestId('filter-label')).toHaveText('No Engineers');
  });

  test('Select All restores All Engineers label', async ({ page }) => {
    await page.getByTestId('engineer-filter-btn').click();
    await page.getByTestId('clear-all-btn').click();
    await page.getByTestId('select-all-btn').click();
    await expect(page.getByTestId('filter-label')).toHaveText('All Engineers');
  });

  test('clicking outside closes the dropdown', async ({ page }) => {
    await page.getByTestId('engineer-filter-btn').click();
    await expect(page.getByTestId('filter-panel')).toBeVisible();
    // Click on the page body outside the dropdown
    await page.locator('.container').click({ position: { x: 5, y: 5 } });
    await expect(page.getByTestId('filter-panel')).not.toBeVisible();
  });
});
