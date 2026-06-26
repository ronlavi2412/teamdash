import { test, expect } from '@playwright/test';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const dashboardPath = path.resolve(__dirname, '../fixtures/test-dashboard.html');

test.describe('Full Table', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`file://${dashboardPath}`);
    await page.getByTestId('tab-table').click();
  });

  test('displays all engineer names', async ({ page }) => {
    const table = page.getByTestId('main-table');
    await expect(table).toContainText('Alice');
    await expect(table).toContainText('Bob');
  });

  test('displays quarter labels in headers', async ({ page }) => {
    const table = page.getByTestId('main-table');
    await expect(table).toContainText("Q4'24");
    await expect(table).toContainText("Q1'25");
  });

  test('clicking header sorts descending then ascending', async ({ page }) => {
    const headers = page.locator('[data-testid="main-table"] th');
    const firstNumHeader = headers.nth(1);

    // Click to sort descending
    await firstNumHeader.click();
    const arrow = firstNumHeader.locator('.sort-arrow');
    await expect(arrow).toHaveText('▼');

    // Click again to sort ascending
    await firstNumHeader.click();
    await expect(arrow).toHaveText('▲');
  });

  test('numeric sort works correctly', async ({ page }) => {
    const headers = page.locator('[data-testid="main-table"] th');
    // Sort by first PRs+MRs column (descending)
    await headers.nth(1).click();

    const firstCell = page.locator('[data-testid="main-table"] tbody tr:first-child td:first-child');
    // Alice should be first (higher PRs+MRs)
    await expect(firstCell).toContainText('Alice');
  });

  test('growth column is present', async ({ page }) => {
    const table = page.getByTestId('main-table');
    await expect(table).toContainText('Growth');
  });
});
