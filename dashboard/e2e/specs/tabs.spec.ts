import { test, expect } from '@playwright/test';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const dashboardPath = path.resolve(__dirname, '../fixtures/test-dashboard.html');
const summaryDashboardPath = path.resolve(__dirname, '../fixtures/test-dashboard-with-summaries.html');

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

  test('hides Summaries when none are available', async ({ page }) => {
    await expect(page.getByTestId('tab-summaries')).toHaveCount(0);
  });

  test('Team Summary compares quarters and preserves engineer navigation', async ({ page }) => {
    await page.goto(`file://${summaryDashboardPath}`);
    await page.getByTestId('tab-summaries').click();
    const teamButton = page.getByRole('button', { name: 'Team Summary', exact: true });
    const output = page.locator('.summary-list li').filter({ hasText: 'PRs/MRs:' });
    await expect(teamButton).toHaveAttribute('aria-pressed', 'true');
    await expect(output).toContainText('15 → 20 (33.3% increase)');
    await page.getByRole('button', { name: 'Alice', exact: true }).click();
    await expect(page.locator('.summary-content h3')).toContainText('Alice');
    await expect(teamButton).toHaveAttribute('aria-pressed', 'false');
    await teamButton.click();
    await expect(output).toContainText('15 → 20 (33.3% increase)');
  });

  test('Team Summary distinguishes a zero baseline from missing cycle-time data', async ({ page }) => {
    await page.goto(`file://${summaryDashboardPath}`);
    await page.evaluate(() => {
      if (!('__DASHBOARD_DATA__' in window)) throw new Error('Missing fixture data');
      const data = window.__DASHBOARD_DATA__;
      if (!data || typeof data !== 'object' || !('quarters' in data) || !Array.isArray(data.quarters)) {
        throw new Error('Missing fixture quarters');
      }
      const previous = data.quarters[0];
      if (!previous || !Array.isArray(previous.gh_prs) || !Array.isArray(previous.gl_mrs)) {
        throw new Error('Missing fixture contributions');
      }
      previous.gh_prs.fill(0);
      previous.gl_mrs.fill(0);
    });
    await page.getByTestId('tab-summaries').click();
    await expect(page.locator('.summary-list li').filter({ hasText: 'PRs/MRs:' }))
      .toContainText('0 → 20 (no percentage comparison from a zero baseline)');
    await expect(page.locator('.summary-list li').filter({ hasText: 'Story median, all projects:' }))
      .toContainText('not available → not available (insufficient data for comparison)');
    await expect(page.locator('.summary-content')).not.toContainText('Infinity');
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
