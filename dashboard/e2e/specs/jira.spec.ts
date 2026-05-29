import { test, expect } from '@playwright/test';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const dashboardPath = path.resolve(__dirname, '../fixtures/test-dashboard.html');
const jiraPath = path.resolve(__dirname, '../fixtures/test-dashboard-jira.html');

test.describe('Jira Verified Bugs Features', () => {
  test('without jira: no verified bugs chart in team view', async ({ page }) => {
    await page.goto(`file://${dashboardPath}`);
    await expect(page.locator('[data-testid="chart-team-verified-bugs"]')).not.toBeVisible();
  });

  test('with jira: verified bugs chart visible in team view', async ({ page }) => {
    await page.goto(`file://${jiraPath}`);
    await expect(page.locator('[data-testid="chart-team-verified-bugs"]')).toBeVisible();
  });

  test('without jira: no verified bugs chart in detail view', async ({ page }) => {
    await page.goto(`file://${dashboardPath}`);
    await page.getByTestId('tab-overview').click();
    await expect(page.locator('[data-testid="chart-verified-bugs-trend"]')).not.toBeVisible();
  });

  test('with jira: verified bugs chart visible in detail view', async ({ page }) => {
    await page.goto(`file://${jiraPath}`);
    await page.getByTestId('tab-overview').click();
    await expect(page.locator('[data-testid="chart-verified-bugs-trend"]')).toBeVisible();
  });

  test('with jira: table includes bugs columns', async ({ page }) => {
    await page.goto(`file://${jiraPath}`);
    await page.getByTestId('tab-table').click();
    const table = page.getByTestId('main-table');
    await expect(table).toContainText('Bugs');
  });

  test('with jira: config tab shows Jira cloud', async ({ page }) => {
    await page.goto(`file://${jiraPath}`);
    await page.getByTestId('tab-config').click();
    const configTab = page.locator('[data-testid="tab-config"]').last();
    await expect(configTab).toContainText('Jira Cloud');
    await expect(configTab).toContainText('test.atlassian.net');
  });

  test('with jira: config tab shows Jira projects', async ({ page }) => {
    await page.goto(`file://${jiraPath}`);
    await page.getByTestId('tab-config').click();
    const configTab = page.locator('[data-testid="tab-config"]').last();
    await expect(configTab).toContainText('Jira Projects');
    await expect(configTab).toContainText('PROJ');
  });
});
