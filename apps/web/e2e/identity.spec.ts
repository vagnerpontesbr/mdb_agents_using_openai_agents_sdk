import { expect, test } from '@playwright/test';

test('admin registers a user; reload and logout preserve session boundaries', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Sign in', exact: true })).toBeVisible();
  await page.screenshot({ path: 'test-results/sign-in-desktop.png', fullPage: true });
  await page.getByLabel('Email', { exact: true }).fill('admin@mongodb.com');
  await page.getByLabel('Password', { exact: true }).fill('synthetic-browser-only');
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await page.getByRole('link', { name: 'Users', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Create an account' })).toBeVisible();
  await page.screenshot({ path: 'test-results/admin-desktop.png', fullPage: true });
  await page.getByLabel('Email', { exact: true }).fill('member@example.test');
  await page.getByLabel('Password', { exact: true }).fill('synthetic-member-only');
  await page.getByRole('button', { name: 'Create account', exact: true }).click();
  await expect(page.getByRole('status').filter({ hasText: 'Account created for' }))
    .toHaveText('Account created for member@example.test.');
  await page.reload();
  await expect(page.getByRole('button', { name: 'Profile', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Profile', exact: true }).click();
  await page.getByRole('button', { name: 'Sign out', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Sign in', exact: true })).toBeVisible();
  await page.getByLabel('Email', { exact: true }).fill('member@example.test');
  await page.getByLabel('Password', { exact: true }).fill('synthetic-member-only');
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Profile', exact: true })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Create an account' })).toHaveCount(0);
  const denied = await page.evaluate(async () => (await fetch('/api/users', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: 'forbidden@example.test', password: 'synthetic-denied-only', role: 'admin' }),
  })).status);
  expect(denied).toBe(403);
  expect(await page.evaluate(() => Object.keys(localStorage))).toEqual([]);
  expect(await page.evaluate(() => document.cookie)).not.toContain('telecom_session');
  await page.getByRole('button', { name: 'Profile', exact: true }).click();
  await page.getByRole('button', { name: 'Sign out', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Sign in', exact: true })).toBeVisible();
  await page.reload();
  await expect(page.getByRole('heading', { name: 'Sign in', exact: true })).toBeVisible();
});

test('mobile layout keeps sign-in controls visible', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/');
  await expect(page.getByRole('button', { name: 'Sign in', exact: true })).toBeVisible();
  await page.screenshot({ path: 'test-results/sign-in-mobile.png', fullPage: true });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});
