import { test, expect } from '@playwright/test';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const dashboardPath = path.resolve(__dirname, '../fixtures/test-dashboard.html');
const jiraPath = path.resolve(__dirname, '../fixtures/test-dashboard-jira.html');
const activityTypesPath = path.resolve(__dirname, '../fixtures/test-dashboard-activity-types.html');

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

test.describe('Activity Type Features', () => {
  test('without activity types: no activity type chart in team view', async ({ page }) => {
    await page.goto(`file://${dashboardPath}`);
    await expect(page.locator('[data-testid="chart-team-activity-types"]')).not.toBeVisible();
  });

  test('with activity types: chart visible in team view', async ({ page }) => {
    await page.goto(`file://${activityTypesPath}`);
    await expect(page.locator('[data-testid="chart-team-activity-types"]')).toBeVisible();
  });

  test('without activity types: no activity type chart in detail view', async ({ page }) => {
    await page.goto(`file://${dashboardPath}`);
    await page.getByTestId('tab-overview').click();
    await expect(page.locator('[data-testid="chart-activity-type-breakdown"]')).not.toBeVisible();
  });

  test('with activity types: chart visible in detail view', async ({ page }) => {
    await page.goto(`file://${activityTypesPath}`);
    await page.getByTestId('tab-overview').click();
    await expect(page.locator('[data-testid="chart-activity-type-breakdown"]')).toBeVisible();
  });

  test('detail chart does not grow on hover', async ({ page }) => {
    await page.goto(`file://${activityTypesPath}`);
    await page.getByTestId('tab-overview').click();
    const chart = page.locator('[data-testid="chart-activity-type-breakdown"]');
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

  test('team chart does not grow on hover', async ({ page }) => {
    await page.goto(`file://${activityTypesPath}`);
    const chart = page.locator('[data-testid="chart-team-activity-types"]');
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

  test('detail chart fits within chart-wrap container', async ({ page }) => {
    await page.goto(`file://${activityTypesPath}`);
    await page.getByTestId('tab-overview').click();
    const card = page.locator('[data-testid="chart-activity-type-breakdown"]');
    const wrap = card.locator('.chart-wrap');
    const canvas = card.locator('canvas');
    await expect(canvas).toBeVisible();
    const wrapBox = await wrap.boundingBox();
    const canvasBox = await canvas.boundingBox();
    expect(canvasBox!.y).toBeGreaterThanOrEqual(wrapBox!.y);
    expect(canvasBox!.y + canvasBox!.height).toBeLessThanOrEqual(wrapBox!.y + wrapBox!.height + 1);
  });
});
