import { expect, test } from '@playwright/test';
import { catalogs, type Locale } from '../src/catalogs';

for (const locale of ['en-US', 'pt-BR', 'es-ES'] as Locale[]) {
  test(`voice snapshot survives recording and transcription language switches: ${locale}`, async ({ page }) => {
    const t = (key: string) => catalogs[locale][key];
    const user = { user_id: 'voice-synthetic', email: 'voice@example.test', role: 'user' };
    let profile = { ...user, display_name: 'Voice Test', timezone: 'UTC', locale, revision: 0 };
    await page.route('**/api/me', r => r.fulfill({ json: user }));
    await page.route('**/api/profile', r => {
      if (r.request().method() === 'POST') profile = { ...profile, ...r.request().postDataJSON(), revision: profile.revision + 1 };
      return r.fulfill({ json: profile });
    });
    await page.route('**/api/capabilities', r => r.fulfill({ json: { journey: true, voice: true } }));
    await page.route('**/api/journey/latest', r => r.fulfill({ json: { status: 'empty' } }));
    // Browser transport/lifecycle double: no microphone, speech quality or provider claim.
    await page.addInitScript(() => {
      const stop = () => { document.documentElement.dataset.stops = String(Number(document.documentElement.dataset.stops ?? 0) + 1); };
      navigator.mediaDevices.getUserMedia = async () => {
        if (document.documentElement.dataset.denyMicrophone === 'true') throw new DOMException('Denied', 'NotAllowedError');
        return { getTracks: () => [{ stop }] } as unknown as MediaStream;
      };
      const node = () => ({ connect() {}, disconnect() {}, gain: { value: 0 } });
      window.AudioContext = class {
        sampleRate = 24000;
        audioWorklet = { addModule: async () => {} };
        destination = {};
        createMediaStreamSource = node;
        createGain = node;
        close = async () => {};
      } as unknown as typeof AudioContext;
      window.AudioWorkletNode = class {
        port = { onmessage: null };
        connect() {}
        disconnect() {}
      } as unknown as typeof AudioWorkletNode;
    });
    await page.goto('/');
    await expect(page.getByLabel(t('Your message'))).toBeEnabled();
    await page.evaluate(() => { document.documentElement.dataset.denyMicrophone = 'true'; });
    await page.getByRole('button', { name: t('Record voice'), exact: true }).click();
    await expect(page.getByText(t('Microphone unavailable or permission denied. You can continue with text.'))).toBeVisible();
    await expect(page.getByLabel(t('Your message'))).toBeEnabled();
    await page.evaluate(() => { document.documentElement.dataset.denyMicrophone = 'false'; });
    await page.getByLabel(t('Your message')).fill('Preserved draft');
    await page.getByRole('button', { name: t('Record voice'), exact: true }).click();
    await page.getByRole('button', { name: t('Cancel recording'), exact: true }).click();
    await expect(page.getByLabel(t('Your message'))).toHaveValue('Preserved draft');
    expect(await page.evaluate(() => document.documentElement.dataset.stops)).toBe('1');
    const conversation = await page.evaluate(() => sessionStorage.getItem('telecom-conversation-voice-synthetic'));
    await page.getByRole('button', { name: t('Record voice'), exact: true }).click();
    await expect(page.locator('.audio-language')).toContainText(t({ 'en-US': 'English', 'pt-BR': 'Portuguese (Brazil)', 'es-ES': 'Spanish' }[locale]));
    await page.getByRole('button', { name: t('Profile'), exact: true }).click();
    await page.getByRole('combobox', { name: t('Language'), exact: true }).selectOption('en-US');
    await page.keyboard.press('Escape');
    expect(await page.evaluate(() => document.documentElement.dataset.stops)).toBe('1');
    let release!: () => void;
    const held = new Promise<void>(resolve => { release = resolve; });
    let calls = 0;
    await page.route('**/api/voice/transcribe', async r => {
      calls++;
      expect(r.request().postDataJSON().locale).toBe(locale);
      await held;
      await r.fulfill({ json: { text: 'Synthetic transcript', locale } });
    });
    await page.getByRole('button', { name: 'Finish recording', exact: true }).click();
    await expect.poll(() => calls).toBe(1);
    await page.getByRole('button', { name: 'Profile', exact: true }).click();
    await page.getByRole('combobox', { name: 'Language', exact: true }).selectOption('es-ES');
    await page.keyboard.press('Escape');
    release();
    await expect(page.getByLabel('Tu mensaje')).toHaveValue('Synthetic transcript');
    await page.getByLabel('Tu mensaje').fill('Edited synthetic transcript');
    let chatCalls = 0;
    await page.route('**/api/journey/chat', r => {
      chatCalls++;
      expect(r.request().postDataJSON()).toEqual({ conversation_id: conversation, message: 'Edited synthetic transcript', audio_locale: locale });
      return r.fulfill({ contentType: 'text/event-stream', body: `event: result\ndata: ${JSON.stringify({ status: 'completed', text: 'Synthetic answer', locale })}\n\n` });
    });
    await page.getByRole('button', { name: 'Enviar', exact: true }).click();
    await expect(page.locator('.result')).toHaveAttribute('lang', locale);
    expect(chatCalls).toBe(1);
    expect(calls).toBe(1);
    await expect(page.locator('.audio-language')).toHaveCount(0);
    expect(await page.evaluate(() => document.documentElement.dataset.stops)).toBe('2');
    // A failed transcription cannot send a chat or erase a pre-existing draft.
    await page.getByLabel('Tu mensaje').fill('Keep after failure');
    await page.route('**/api/voice/transcribe', r => { calls++; return r.fulfill({ status: 503, json: {} }); });
    await page.getByRole('button', { name: catalogs['es-ES']['Record voice'], exact: true }).click();
    await page.getByRole('button', { name: catalogs['es-ES']['Finish recording'], exact: true }).click();
    await expect(page.getByText(catalogs['es-ES']['Speech could not be recognized. Try once more in a quiet room or use text.'])).toBeVisible();
    await expect(page.getByLabel('Tu mensaje')).toHaveValue('Keep after failure');
    expect(calls).toBe(2);
    expect(chatCalls).toBe(1);
  });
}

test('stop playback prevents a pending speech response from starting later', async ({ page }) => {
  const user = { user_id: 'voice-stop', email: 'voice@example.test', role: 'user' };
  await page.route('**/api/me', r => r.fulfill({ json: user }));
  await page.route('**/api/profile', r => r.fulfill({ json: { ...user, display_name: 'Voice', timezone: 'UTC', locale: 'en-US', revision: 0 } }));
  await page.route('**/api/capabilities', r => r.fulfill({ json: { journey: true, voice: true } }));
  await page.route('**/api/journey/latest', r => r.fulfill({ json: {
    status: 'completed', execution_id: '00000000-0000-4000-8000-000000000008', text: 'Synthetic', locale: 'pt-BR',
  } }));
  await page.addInitScript(() => {
    HTMLMediaElement.prototype.play = async () => { document.documentElement.dataset.played = 'true'; };
  });
  let release!: () => void;
  const held = new Promise<void>(resolve => { release = resolve; });
  let calls = 0;
  await page.route('**/api/voice/speak', async r => {
    calls++;
    expect(r.request().postDataJSON()).toEqual({ execution_id: '00000000-0000-4000-8000-000000000008' });
    await held;
    await r.fulfill({ contentType: 'audio/wav', body: Buffer.from('lifecycle double') });
  });
  await page.goto('/');
  await page.getByRole('button', { name: 'Play response', exact: true }).click();
  await expect.poll(() => calls).toBe(1);
  await page.getByRole('button', { name: 'Stop playback', exact: true }).click();
  release();
  await expect(page.getByRole('button', { name: 'Play response', exact: true })).toBeEnabled();
  expect(await page.evaluate(() => document.documentElement.dataset.played)).toBeUndefined();
  expect(calls).toBe(1);
});
