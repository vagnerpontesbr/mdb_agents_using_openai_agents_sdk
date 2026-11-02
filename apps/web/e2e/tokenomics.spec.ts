import { test, expect } from '@playwright/test';
import type { Page } from '@playwright/test';
import { fixture } from './tokenomics-fixture';

async function identity(page: Page, locale = 'en-US', role = 'admin') {
  const user = { user_id: 'synthetic-tokenomics', email: 'synthetic@example.test', role };
  await page.route('**/api/me', r => r.fulfill({ json: user }));
  await page.route('**/api/profile', r => r.fulfill({ json: { ...user, locale, timezone: 'UTC', display_name: 'Synthetic', revision: 0 } }));
  await page.route('**/api/capabilities', r => r.fulfill({ json: { journey: false, voice: false, knowledge: false } }));
}

test('all inventory sections, keyboard tabs, exact refreshes and preserved filters', async ({ page }) => {
  await identity(page);
  const requests: string[] = [];
  let focusReads = 0;
  await page.route('**/api/admin/tokenomics/dashboard?*', r => { requests.push(r.request().url()); return r.fulfill({ json: fixture.dashboard }); });
  await page.route('**/api/admin/tokenomics/focus-records?*', r => { focusReads++; return r.fulfill({ json: fixture.focus }); });
  await page.goto('/#/control-plane/tokenomics');
  await expect(page.getByRole('heading', { name: 'Observed tokens', exact: true })).toBeVisible();
  await expect(page.locator('.tok-card')).toHaveCount(6);
  expect(requests).toHaveLength(1); expect(focusReads).toBe(1);
  await expect(page.getByRole('heading', { name: 'Daily usage (UTC)' })).toBeVisible();
  await page.getByRole('combobox', { name: 'Period', exact: true }).selectOption('30d');
  await expect(page.getByRole('button', { name: 'Refresh usage' })).toBeEnabled();
  expect(requests).toHaveLength(2); expect(requests[1]).toContain('period=30d');
  await page.getByRole('tab', { name: 'Overview', exact: true }).focus();
  await page.keyboard.press('ArrowRight');
  await expect(page.getByRole('tab', { name: 'Breakdown' })).toBeFocused();
  for (const name of ['Context attribution', 'Token categories', 'Models', 'Agents', 'Business categories']) {
    await expect(page.getByRole('heading', { name, exact: true })).toBeVisible();
  }
  await expect(page.getByRole('listitem').filter({ hasText: 'Semantic memory' })).toBeVisible();
  await page.keyboard.press('End');
  await expect(page.getByRole('tab', { name: 'FOCUS', exact: true })).toBeFocused();
  await expect(page.getByText('Native invoice and SKU records are unavailable.')).toBeVisible();
  expect(requests).toHaveLength(2); expect(focusReads).toBe(2);
  await page.getByRole('button', { name: 'Refresh usage' }).click();
  await expect(page.getByText('Native invoice and SKU records are unavailable.')).toBeVisible();
  expect(requests).toHaveLength(3); expect(focusReads).toBe(3);
  await expect(page.getByRole('tab', { name: 'FOCUS', exact: true })).toHaveAttribute('aria-selected', 'true');
  await page.getByRole('link', { name: 'Support', exact: true }).click();
  await page.getByRole('link', { name: 'Tokenomics', exact: true }).click();
  await expect(page.getByRole('combobox', { name: 'Period', exact: true })).toHaveValue('30d');
  await expect(page.getByRole('tab', { name: 'FOCUS', exact: true })).toHaveAttribute('aria-selected', 'true');
  await page.getByText('Custom date range', { exact: true }).click();
  await expect(page.getByText('Historical date ranges are not supported by this source. Use a trailing period.')).toBeVisible();
});

test('zero bars, missing values and request errors never render misleading totals', async ({ page }) => {
  await identity(page);
  const data = structuredClone(fixture.dashboard);
  data.applications.rows[0].metric.value = '0';
  data.models.rows[0].metric.value = '0';
  let reads = 0;
  await page.route('**/api/admin/tokenomics/dashboard?*', r => { reads++; return r.fulfill({ json: data }); });
  await page.route('**/api/admin/tokenomics/focus-records?*', r => r.fulfill({ json: fixture.focus }));
  await page.goto('/#/control-plane/tokenomics');
  await expect(page.locator('.tok-track i[data-value="0"]')).toHaveCSS('width', '0px');
  await expect(page.locator('.tok-card').filter({ has: page.getByRole('heading', { name: 'Execution count' }) }).getByText('—', { exact: true })).toBeVisible();
  await page.route('**/api/admin/tokenomics/dashboard?*', r => { reads++; return r.fulfill({ status: 503, json: { code: 'tokenomics_auth_expired', error: 'PRIVATE_SENTINEL' } }); });
  await page.getByRole('button', { name: 'Refresh usage' }).click();
  await expect(page.getByRole('alert')).toHaveText('Engine session expired. An operator must refresh it.');
  await expect(page.locator('.tok-card')).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Profile', exact: false })).toBeVisible();
  expect(await page.content()).not.toContain('PRIVATE_SENTINEL');
  expect(reads).toBe(2);
});

test('normal user cannot mount dashboard or read its endpoints', async ({ page }) => {
  await identity(page, 'en-US', 'user');
  let reads = 0;
  await page.route('**/api/admin/tokenomics/**', r => { reads++; return r.abort(); });
  await page.goto('/#/control-plane/tokenomics');
  await expect(page.getByRole('heading', { name: 'Access denied' })).toBeVisible();
  await expect(page.getByRole('link', { name: 'Tokenomics', exact: true })).toHaveCount(0);
  expect(reads).toBe(0);
});

for (const [locale, cost, breakdown] of [
  ['en-US', 'Estimated cost', 'Breakdown'], ['pt-BR', 'Custo estimado', 'Detalhamento'], ['es-ES', 'Costo estimado', 'Desglose'],
]) {
  test(`localized desktop/mobile/zoom layout and keyboard details: ${locale}`, async ({ page }) => {
    await identity(page, locale);
    await page.route('**/api/admin/tokenomics/dashboard?*', r => r.fulfill({ json: fixture.dashboard }));
    await page.route('**/api/admin/tokenomics/focus-records?*', r => r.fulfill({ json: fixture.focus }));
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto('/#/control-plane/tokenomics');
    await expect(page.getByRole('heading', { name: cost, exact: true })).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.screenshot({ path: `test-results/tokenomics-${locale}-mobile.png`, fullPage: true });
    const detail = page.locator('.tok-card summary').first();
    await detail.focus(); await page.keyboard.press('Enter');
    await expect(page.locator('.tok-card details').first()).toHaveAttribute('open', '');
    await page.getByRole('tab', { name: breakdown, exact: true }).click();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.screenshot({ path: `test-results/tokenomics-${locale}-breakdown.png`, fullPage: true });
    await page.setViewportSize({ width: 1440, height: 1000 });
    await page.getByRole('tab').first().click();
    await page.screenshot({ path: `test-results/tokenomics-${locale}-desktop.png`, fullPage: true });
    await page.evaluate(() => { document.documentElement.style.zoom = '2'; });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    expect(await page.locator('.tok-card strong').first().evaluate(element => { const range = document.createRange(); range.selectNodeContents(element); return range.getClientRects().length; })).toBe(1);
    await page.screenshot({ path: `test-results/tokenomics-${locale}-zoom.png`, fullPage: true });
  });
}

test('Tokenomics filters and locale changes preserve the active support execution', async ({ page }) => {
  await identity(page);
  const user = { user_id: 'synthetic-tokenomics', email: 'synthetic@example.test', role: 'admin' };
  await page.route('**/api/profile', r => r.fulfill({ json: {
    ...user, locale: r.request().method() === 'POST' ? r.request().postDataJSON().locale : 'en-US',
    timezone: 'UTC', display_name: 'Synthetic', revision: r.request().method() === 'POST' ? 1 : 0,
  } }));
  await page.route('**/api/capabilities', r => r.fulfill({ json: { journey: true, voice: false, knowledge: false } }));
  await page.route('**/api/journey/latest', r => r.fulfill({ json: { status: 'empty' } }));
  let calls = 0, reads = 0, conversation = '';
  let release!: () => void;
  const held = new Promise<void>(resolve => { release = resolve; });
  await page.route('**/api/journey/chat', async r => {
    calls++; conversation = r.request().postDataJSON().conversation_id;
    await held;
    await r.fulfill({ contentType: 'text/event-stream', body: 'event: result\ndata: {"status":"completed","text":"Original synthetic support result"}\n\n' });
  });
  await page.route('**/api/admin/tokenomics/dashboard?*', r => { reads++; return r.fulfill({ json: fixture.dashboard }); });
  await page.route('**/api/admin/tokenomics/focus-records?*', r => r.fulfill({ json: fixture.focus }));
  await page.goto('/#/support');
  await page.getByLabel('Your message').fill('Synthetic pending support request');
  await page.getByRole('button', { name: 'Send', exact: true }).click();
  await expect.poll(() => calls).toBe(1);
  await page.getByRole('link', { name: 'Tokenomics', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Observed tokens', exact: true })).toBeVisible();
  await page.getByRole('combobox', { name: 'Period', exact: true }).selectOption('90d');
  await expect(page.getByRole('button', { name: 'Refresh usage' })).toBeEnabled();
  await page.getByRole('button', { name: 'Profile', exact: true }).click();
  await page.getByRole('combobox', { name: 'Language', exact: true }).selectOption('pt-BR');
  await expect(page.getByRole('heading', { name: 'Custo estimado', exact: true })).toBeVisible();
  expect(reads).toBe(2); expect(calls).toBe(1);
  release();
  await page.getByRole('link', { name: 'Suporte', exact: true }).click();
  await expect(page.locator('.result')).toHaveText('Original synthetic support result');
  expect(await page.evaluate(() => sessionStorage.getItem('telecom-conversation-synthetic-tokenomics'))).toBe(conversation);
  expect(calls).toBe(1);
});
