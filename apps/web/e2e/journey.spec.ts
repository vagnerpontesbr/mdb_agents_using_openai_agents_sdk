import { expect, test, type Cookie } from '@playwright/test';

// Reuse this suite's synthetic authenticated session; login behavior is tested
// separately, and repeated UI setup must not exhaust the real login limiter.
let cookies: Cookie[] = [];

// UI-only Engine doubles. Backend authorization has separate Python tests.
async function signIn(page: import('@playwright/test').Page) {
  await page.route('**/api/capabilities', route => route.fulfill({ json: { journey: true, voice: true } }));
  await page.route('**/api/journey/latest', route => route.fulfill({ json: { status: 'empty' } }));
  if (cookies.length) {
    await page.context().addCookies(cookies);
    await page.goto('/');
    await expect(page.getByLabel('Your message')).toBeEnabled();
    return;
  }
  await page.goto('/');
  await page.getByLabel('Email', { exact: true }).fill('admin@mongodb.com');
  await page.getByLabel('Password', { exact: true }).fill('synthetic-browser-only');
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await expect(page.getByLabel('Your message')).toBeEnabled();
  cookies = await page.context().cookies();
}

for (const decision of ['approve', 'reject']) {
  test(`mixed journey presents exact proposal and ${decision} result`, async ({ page }) => {
    await signIn(page);
    const pending = { execution_id: '00000000-0000-4000-8000-000000000001', status: 'suspended',
      action_digest: 'a'.repeat(64), action: { plan_id: 'fiber-500', monthly_minor: 8990, proposal_id: 'b'.repeat(64) } };
    await page.route('**/api/journey/chat', async route => {
      expect(route.request().postDataJSON().message).toContain('demo-1');
      await route.fulfill({ contentType: 'text/event-stream', body:
        'event: progress\ndata: {"message":"Consulting your support team"}\n\n' +
        `event: result\ndata: ${JSON.stringify(pending)}\n\n` });
    });
    await page.route('**/api/journey/review', async route => {
      expect(route.request().postDataJSON()).toEqual({ execution_id: pending.execution_id,
        action_digest: pending.action_digest, decision });
      await route.fulfill({ json: { execution_id: pending.execution_id, status: 'completed',
        specialists: ['financial', 'technical', 'sales'], text: decision === 'approve' ?
          'Simulation approved for fiber-500 at USD 89.90 per month. No live plan or charge was changed.' :
          'The plan-change simulation was rejected. No plan or charge changed.' } });
    });
    await page.getByLabel('Your message').fill('Read demo-1, check my connection and simulate fiber-500.');
    await page.getByRole('button', { name: 'Send', exact: true }).click();
    await expect(page.getByRole('heading', { name: 'Confirm this simulation' })).toBeVisible();
    await expect(page.getByText('Monthly price: USD 89.90')).toBeVisible();
    await expect(page.getByLabel('Your message')).toBeDisabled();
    if (decision === 'approve') await page.screenshot({ path: 'test-results/journey-proposal.png', fullPage: true });
    await page.getByRole('button', { name: decision === 'approve' ? 'Approve simulation' : 'Reject', exact: true }).click();
    await expect(page.locator('.result')).toContainText(decision === 'approve' ? 'Simulation approved' : 'was rejected');
    await expect(page.getByLabel('Your message')).toBeEnabled();
    await expect(page.getByText('Consulted: financial, technical, sales')).toBeVisible();
  });
}

test('uncertain request is not resubmitted; latest recovers its result', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await signIn(page);
  let calls = 0;
  await page.route('**/api/journey/chat', async route => {
    calls++; await route.fulfill({ contentType: 'text/event-stream',
      body: 'event: error\ndata: {"message":"uncertain"}\n\n' });
  });
  await page.route('**/api/journey/latest', route => route.fulfill({ json: {
    execution_id: '00000000-0000-4000-8000-000000000002', status: 'completed',
    text: 'Your synthetic invoice total is USD 79.90, due on 2026-12-01.', specialists: ['financial'],
  } }));
  await page.getByLabel('Your message').fill('Read demo-1');
  await page.getByRole('button', { name: 'Send', exact: true }).click();
  await expect(page.getByText('Outcome not confirmed. Check the latest execution before sending again.')).toBeVisible();
  expect(calls).toBe(1);
  await page.getByRole('button', { name: 'Check latest execution' }).click();
  await expect(page.locator('.result')).toContainText('USD 79.90');
  expect(calls).toBe(1);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: 'test-results/journey-mobile.png', fullPage: true });
});

test('denied microphone permission leaves text available without provider calls', async ({ page }) => {
  await page.addInitScript(() => {
    navigator.mediaDevices.getUserMedia = async () => { throw new DOMException('Denied', 'NotAllowedError'); };
  });
  await signIn(page);
  let speechCalls = 0;
  await page.route('**/api/voice/**', route => { speechCalls++; return route.abort(); });
  await page.getByRole('button', { name: 'Record voice' }).click();
  await expect(page.getByText('Microphone unavailable or permission denied. You can continue with text.')).toBeVisible();
  await expect(page.getByLabel('Your message')).toBeEnabled();
  expect(speechCalls).toBe(0);
});

test('same-origin policy permits synthesized WAV playback', async ({ page }) => {
  const errors: string[] = [];
  page.on('console', entry => { if (entry.type() === 'error') errors.push(entry.text()); });
  await page.addInitScript(() => {
    const OriginalAudio = window.Audio;
    window.Audio = class extends OriginalAudio {
      constructor(src?: string) {
        super(src);
        this.addEventListener('playing', () => document.documentElement.setAttribute('data-audio-playing', 'true'));
      }
    };
    document.addEventListener('playing', () => document.documentElement.setAttribute('data-audio-playing', 'true'), true);
  });
  await signIn(page);
  await page.route('**/api/journey/latest', route => route.fulfill({ json: {
    execution_id: '00000000-0000-4000-8000-000000000003', status: 'completed', text: 'Synthetic invoice.', specialists: ['financial'],
  } }));
  const wav = Buffer.alloc(44 + 48000);
  wav.write('RIFF', 0); wav.writeUInt32LE(wav.length - 8, 4); wav.write('WAVEfmt ', 8);
  wav.writeUInt32LE(16, 16); wav.writeUInt16LE(1, 20); wav.writeUInt16LE(1, 22);
  wav.writeUInt32LE(24000, 24); wav.writeUInt32LE(48000, 28);
  wav.writeUInt16LE(2, 32); wav.writeUInt16LE(16, 34); wav.write('data', 36); wav.writeUInt32LE(48000, 40);
  for (let index = 0; index < 24000; index++) wav.writeInt16LE(Math.round(Math.sin(index * Math.PI * 440 / 12000) * 2000), 44 + index * 2);
  await page.route('**/api/voice/speak', route => route.fulfill({ contentType: 'audio/wav', body: wav }));
  await page.getByRole('button', { name: 'Check latest execution' }).click();
  await page.getByRole('button', { name: 'Play response', exact: true }).click();
  await expect(page.locator('html'), errors.join('\n')).toHaveAttribute('data-audio-playing', 'true');
  await page.getByRole('region', { name: 'Support workspace' }).screenshot({ path: 'test-results/voice-playback.png' });
});

test('reload restores pending review; new conversation changes only the opaque session', async ({ page }) => {
  await signIn(page);
  let conversation = '';
  await page.route('**/api/journey/chat', async route => {
    conversation = route.request().postDataJSON().conversation_id;
    await route.fulfill({ contentType: 'text/event-stream', body: 'event: error\ndata: {}\n\n' });
  });
  await page.getByLabel('Your message').fill('Simulate fiber-500');
  await page.getByRole('button', { name: 'Send', exact: true }).click();
  await expect(page.getByLabel('Your message')).toBeDisabled();
  const pending = { execution_id: '00000000-0000-4000-8000-000000000004', status: 'suspended',
    action_digest: 'a'.repeat(64), action: { plan_id: 'fiber-500', monthly_minor: 8990, proposal_id: 'b'.repeat(64) } };
  await page.route('**/api/journey/latest', route => route.fulfill({ json:
    route.request().postDataJSON().conversation_id === conversation ? pending : { status: 'empty' } }));
  await page.reload();
  await expect(page.getByRole('heading', { name: 'Confirm this simulation' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'New conversation', exact: true })).toBeDisabled();
  await page.getByRole('button', { name: 'Check latest execution' }).click();
  await page.route('**/api/journey/review', route => route.fulfill({ json: {
    execution_id: pending.execution_id, status: 'completed', text: 'Simulation rejected.', specialists: ['sales'],
  } }));
  await page.getByRole('button', { name: 'Reject', exact: true }).click();
  await page.getByRole('button', { name: 'New conversation', exact: true }).click();
  await expect(page.getByLabel('Your message')).toBeEnabled();
  await expect(page.locator('.result')).toHaveCount(0);
  const storage = await page.evaluate(() => ({ ...sessionStorage }));
  expect(Object.values(storage)).not.toContain(conversation);
  expect(JSON.stringify(storage)).not.toContain('fiber-500');
});

test('empty or previous result cannot clear an uncertain new invocation, even after reload', async ({ page }) => {
  await signIn(page);
  const previous = { execution_id: '00000000-0000-4000-8000-000000000005', status: 'completed', text: 'Previous result.' };
  await page.route('**/api/journey/latest', route => route.fulfill({ json: previous }));
  await page.getByRole('button', { name: 'Check latest execution' }).click();
  await expect(page.locator('.result')).toContainText('Previous result.');
  let calls = 0;
  await page.route('**/api/journey/chat', async route => {
    calls++;
    await route.fulfill({ contentType: 'text/event-stream', body: 'event: error\ndata: {}\n\n' });
  });
  await page.getByLabel('Your message').fill('Read demo-1');
  await page.getByRole('button', { name: 'Send', exact: true }).click();
  await expect(page.getByLabel('Your message')).toBeDisabled();
  await page.getByRole('button', { name: 'Check latest execution' }).click();
  await expect(page.getByText('The uncertain request has not been recovered. Check again before continuing.')).toBeVisible();
  await expect(page.getByLabel('Your message')).toBeDisabled();
  await page.route('**/api/journey/latest', route => route.fulfill({ json: { status: 'empty' } }));
  await page.reload();
  await expect(page.getByText('A previous request has an uncertain outcome. Check the latest execution before continuing.')).toBeVisible();
  await page.getByRole('button', { name: 'Check latest execution' }).click();
  await expect(page.getByLabel('Your message')).toBeDisabled();
  await expect(page.getByRole('button', { name: 'New conversation', exact: true })).toBeDisabled();
  expect(calls).toBe(1);
});
