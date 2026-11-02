import { expect, test } from '@playwright/test';

test('admin settings persist after reload; stale save requires explicit reload', async ({ page, baseURL }) => {
  await page.context().addCookies([{ name: 'telecom_session', value: 'c'.repeat(43), url: baseURL!, httpOnly: true, sameSite: 'Strict' }]);
  await page.goto('/#/control-plane/overview');
  await expect(page.getByLabel('Maximum message characters')).toBeEnabled();
  const settings = await page.evaluate(async () => (await fetch('/api/admin/control-plane')).json());
  await page.getByLabel('Maximum message characters').fill('2000');
  await page.getByLabel('Library cache age (seconds)').fill('60');
  await page.getByRole('button', { name: 'Save and apply', exact: true }).click();
  await expect(page.getByText('Settings saved. Subsequent operations use the new values.')).toBeVisible();
  await page.reload();
  await expect(page.getByLabel('Maximum message characters')).toHaveValue('2000');
  await expect(page.getByLabel('Library cache age (seconds)')).toHaveValue('60');
  await page.evaluate(async () => {
    const current = await (await fetch('/api/admin/control-plane')).json();
    await fetch('/api/admin/control-plane', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...current.values, expected_revision: current.revision, chat_max_chars: 1900 }) });
  });
  await page.getByRole('button', { name: 'Save and apply', exact: true }).click();
  await expect(page.getByText('Settings changed or save is uncertain. Reload before trying again.')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Save and apply', exact: true })).toBeDisabled();
  await page.getByRole('button', { name: 'Reload settings', exact: true }).click();
  await expect(page.getByLabel('Maximum message characters')).toHaveValue('1900');
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({ path: 'test-results/control-plane-mobile.png', fullPage: true });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.screenshot({ path: 'test-results/control-plane-desktop.png', fullPage: true });
  await page.getByLabel('Maximum message characters').focus();
  await page.keyboard.press('Tab');
  await expect(page.getByLabel('Maximum library query characters')).toBeFocused();
  // Restore shared fixture defaults using its current revision, not stale UI state.
  await page.evaluate(async original => {
    const current = await (await fetch('/api/admin/control-plane')).json();
    await fetch('/api/admin/control-plane', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...original.values, expected_revision: current.revision }) });
  }, settings);
});

test('unknown outcome does not retry settings write; unavailable data is explicit', async ({ page }) => {
  const user = { user_id: 'control-test', email: 'admin@example.test', role: 'admin' };
  await page.route('**/api/me', r => r.fulfill({ json: user }));
  await page.route('**/api/profile', r => r.fulfill({ json: { ...user, locale: 'en-US', timezone: 'UTC', display_name: 'Admin', revision: 0 } }));
  await page.route('**/api/capabilities', r => r.fulfill({ json: { journey: false, voice: false, knowledge: false } }));
  let writes = 0;
  await page.route('**/api/admin/control-plane', r => {
    if (r.request().method() === 'POST') { writes++; return r.abort(); }
    return r.fulfill({ json: { revision: 0, editable: true, source: 'application_database', observed_at: '2026-11-01T00:00:00Z',
      values: { chat_max_chars: 4000, knowledge_query_max_chars: 2000, library_cache_max_age_seconds: 900 } } });
  });
  await page.goto('/#/control-plane/overview');
  await page.getByRole('button', { name: 'Save and apply', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Save and apply', exact: true })).toBeDisabled();
  expect(writes).toBe(1);
  await page.route('**/api/admin/control-plane', r => r.fulfill({ status: 503, json: {} }));
  await page.getByRole('button', { name: 'Reload settings', exact: true }).click();
  await expect(page.getByText('Settings unavailable. Reload before continuing.')).toBeVisible();
  await expect(page.getByLabel('Maximum message characters')).toHaveCount(0);
});

for (const [locale, label, saved] of [
  ['pt-BR', 'Máximo de caracteres da mensagem', 'Salvar e aplicar'],
  ['es-ES', 'Máximo de caracteres del mensaje', 'Guardar y aplicar'],
]) {
  test(`localized Control Plane is usable at narrow width: ${locale}`, async ({ page }) => {
    const user = { user_id: 'control-locale', email: 'admin@example.test', role: 'admin' };
    await page.route('**/api/me', r => r.fulfill({ json: user }));
    await page.route('**/api/profile', r => r.fulfill({ json: { ...user, locale, timezone: 'UTC', display_name: 'Admin', revision: 0 } }));
    await page.route('**/api/capabilities', r => r.fulfill({ json: { journey: false, voice: false, knowledge: false } }));
    await page.route('**/api/admin/control-plane', r => r.fulfill({ json: {
      revision: 0, editable: true, source: 'code_defaults', observed_at: '2026-11-01T00:00:00Z',
      values: { chat_max_chars: 4000, knowledge_query_max_chars: 2000, library_cache_max_age_seconds: 900 },
    } }));
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto('/#/control-plane/overview');
    await expect(page.getByLabel(label)).toHaveValue('4000');
    await expect(page.getByRole('button', { name: saved, exact: true })).toBeEnabled();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.screenshot({ path: `test-results/control-plane-${locale}.png`, fullPage: true });
  });
}

test('definite admission rejection leaves the conversation editable without resubmission', async ({ page }) => {
  const user = { user_id: 'limit-test', email: 'user@example.test', role: 'user' };
  await page.route('**/api/me', r => r.fulfill({ json: user }));
  await page.route('**/api/profile', r => r.fulfill({ json: { ...user, locale: 'en-US', timezone: 'UTC', display_name: 'User', revision: 0 } }));
  await page.route('**/api/capabilities', r => r.fulfill({ json: { journey: true, voice: false, knowledge: false, chat_max_chars: 4000 } }));
  await page.route('**/api/journey/latest', r => r.fulfill({ json: { status: 'empty' } }));
  let calls = 0;
  await page.route('**/api/journey/chat', r => { calls++; return r.fulfill({ status: 400, json: {} }); });
  await page.goto('/');
  await page.getByLabel('Your message').fill('A message exceeding a newly reduced limit.');
  await page.getByRole('button', { name: 'Send', exact: true }).click();
  await expect(page.getByText('Request rejected. Shorten your message before sending again.')).toBeVisible();
  await expect(page.getByLabel('Your message')).toBeEnabled();
  await expect(page.getByRole('button', { name: 'Send', exact: true })).toBeEnabled();
  expect(calls).toBe(1);
});
