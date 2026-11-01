import { expect, test, type Page } from '@playwright/test';

async function workspace(page: Page, role: 'user' | 'admin' = 'admin', route = '/support') {
  await page.route('**/api/me', r => r.fulfill({ json: { user_id: `synthetic-${role}`, email: `${role}@example.test`, role } }));
  await page.route('**/api/capabilities', r => r.fulfill({ json: { journey: true, voice: true, knowledge: false } }));
  await page.route('**/api/journey/latest', r => r.fulfill({ json: { status: 'empty' } }));
  await page.goto(`/#${route}`);
}

test('navigation preserves the draft, conversation and an in-flight request without resubmission', async ({ page }) => {
  await workspace(page);
  const draft = page.getByLabel('Your message');
  await expect(draft).toBeEnabled();
  await draft.fill('Synthetic connection question');
  const conversation = await page.evaluate(() => sessionStorage.getItem('telecom-conversation-synthetic-admin'));
  await page.getByRole('link', { name: 'Overview', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Overview', exact: true })).toBeVisible();
  await page.goBack();
  await expect(draft).toHaveValue('Synthetic connection question');
  let calls = 0;
  let release!: () => void;
  const held = new Promise<void>(resolve => { release = resolve; });
  await page.route('**/api/journey/chat', async r => {
    calls++;
    expect(r.request().postDataJSON().conversation_id).toBe(conversation);
    await held;
    await r.fulfill({ contentType: 'text/event-stream', body: 'event: result\ndata: {"status":"completed","text":"Synthetic verified result"}\n\n' });
  });
  await page.getByRole('button', { name: 'Send', exact: true }).click();
  await expect.poll(() => calls).toBe(1);
  await page.getByRole('link', { name: 'Overview', exact: true }).click();
  release();
  await page.getByRole('link', { name: 'Support', exact: true }).click();
  await expect(page.locator('.result')).toHaveText('Synthetic verified result');
  expect(calls).toBe(1);
  expect(await page.evaluate(() => sessionStorage.getItem('telecom-conversation-synthetic-admin'))).toBe(conversation);
});

test('deep links, reload, forward and unknown routes work; user cannot enter admin views', async ({ page }) => {
  await workspace(page, 'user', '/profile');
  await expect(page.getByRole('heading', { name: 'My profile' })).toBeVisible();
  await page.reload();
  await expect(page.getByRole('heading', { name: 'My profile' })).toBeVisible();
  await expect(page.getByRole('link', { name: 'Users', exact: true })).toHaveCount(0);
  await page.goto('/#/control-plane/users');
  await expect(page.getByRole('heading', { name: 'Access denied' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Create an account' })).toHaveCount(0);
  await page.getByRole('link', { name: 'Return to Support' }).click();
  await page.goBack();
  await expect(page.getByRole('heading', { name: 'Access denied' })).toBeVisible();
  await page.goForward();
  await expect(page.getByLabel('Your message')).toBeVisible();
  await page.goto('/#/missing');
  await expect(page.getByRole('heading', { name: 'Page not found' })).toBeVisible();
});

test('profile keyboard dismissal, mobile navigation and narrow layouts remain usable', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 1000 });
  await workspace(page);
  await expect(page.getByLabel('Your message')).toBeEnabled();
  const profile = page.getByRole('button', { name: 'Profile', exact: true });
  await profile.focus(); await page.keyboard.press('Enter');
  await expect(page.getByRole('link', { name: 'My profile' })).toBeVisible();
  await page.keyboard.press('Escape'); await expect(profile).toBeFocused();
  await page.screenshot({ path: 'test-results/workspace-desktop.png', fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  const nav = page.getByRole('button', { name: 'Navigation', exact: true });
  await nav.click();
  await page.getByRole('link', { name: 'Tokenomics', exact: true }).click();
  await expect(nav).toHaveAttribute('aria-expanded', 'false');
  await expect(page.getByRole('heading', { name: 'Tokenomics' })).toBeVisible();
  await nav.click(); await page.keyboard.press('Escape'); await expect(nav).toBeFocused();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: 'test-results/workspace-mobile.png', fullPage: true });
  await page.setViewportSize({ width: 720, height: 500 }); // Narrow reflow check
  await nav.click();
  await page.getByRole('link', { name: 'Support', exact: true }).click();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.evaluate(() => { document.documentElement.style.zoom = '2'; });
  await expect(page.getByLabel('Your message')).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: 'test-results/workspace-200-percent.png', fullPage: true });
});

test('expired authenticated request removes workspace and active user state', async ({ page }) => {
  await workspace(page);
  await expect(page.getByLabel('Your message')).toBeEnabled();
  await page.route('**/api/journey/latest', r => r.fulfill({ status: 401, json: { detail: 'unauthorized' } }));
  await page.getByRole('button', { name: 'Check latest execution' }).click();
  await expect(page.getByRole('heading', { name: 'Sign in', exact: true })).toBeVisible();
  await expect(page.getByRole('navigation', { name: 'Workspace' })).toHaveCount(0);
  await expect(page.getByRole('alert')).toContainText('session expired');
});

test('pending approval keeps its exact action across navigation; late audio never starts offscreen', async ({ page }) => {
  await workspace(page);
  const pending = { execution_id: '00000000-0000-4000-8000-000000000009', status: 'suspended',
    action_digest: 'c'.repeat(64), action: { plan_id: 'fiber-500', monthly_minor: 8990, proposal_id: 'd'.repeat(64) } };
  await page.route('**/api/journey/chat', r => r.fulfill({ contentType: 'text/event-stream',
    body: `event: result\ndata: ${JSON.stringify(pending)}\n\n` }));
  await expect(page.getByLabel('Your message')).toBeEnabled();
  await page.getByLabel('Your message').fill('Synthetic plan request');
  await page.getByRole('button', { name: 'Send', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Confirm this simulation' })).toBeVisible();
  await page.getByRole('link', { name: 'Overview', exact: true }).click();
  await page.getByRole('link', { name: 'Support', exact: true }).click();
  await expect(page.getByText('Monthly price: USD 89.90')).toBeVisible();
  await page.route('**/api/journey/review', r => {
    expect(r.request().postDataJSON()).toEqual({ execution_id: pending.execution_id, action_digest: pending.action_digest, decision: 'reject' });
    return r.fulfill({ json: { execution_id: pending.execution_id, status: 'completed', text: 'Synthetic rejection' } });
  });
  await page.getByRole('button', { name: 'Reject', exact: true }).click();
  let release!: () => void;
  const held = new Promise<void>(resolve => { release = resolve; });
  let requested = false;
  await page.route('**/api/voice/speak', async r => {
    requested = true; await held;
    await r.fulfill({ contentType: 'audio/wav', body: Buffer.from('synthetic-invalid-audio') });
  });
  await page.evaluate(() => {
    HTMLMediaElement.prototype.play = function () { throw new Error('Offscreen audio must not play'); };
  });
  await page.getByRole('button', { name: 'Play response' }).click();
  await expect.poll(() => requested).toBe(true);
  await page.getByRole('link', { name: 'Overview', exact: true }).click();
  const response = page.waitForResponse('**/api/voice/speak');
  release(); await response;
  // Wait for the hidden journey to finish handling the body, before returning.
  await expect(page.getByRole('button', { name: 'Play response', includeHidden: true })).toBeEnabled();
  await page.getByRole('link', { name: 'Support', exact: true }).click();
  await expect(page.getByText('Playback unavailable.', { exact: false })).toHaveCount(0);
  await expect(page.locator('.result')).toHaveText('Synthetic rejection');
});
