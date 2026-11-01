import { expect, test } from '@playwright/test';

test('translation upload preserves declared language and original identity (UI doubles)', async ({ page }) => {
  const user = { user_id: 'knowledge-language', email: 'synthetic@example.test', role: 'admin' };
  const original = 'a'.repeat(64);
  await page.route('**/api/me', r => r.fulfill({ json: user }));
  await page.route('**/api/profile', r => r.fulfill({ json: {
    ...user, display_name: 'Synthetic owner', timezone: 'UTC', locale: 'en-US', revision: 0,
  } }));
  await page.route('**/api/capabilities', r => r.fulfill({ json: { journey: false, voice: false, knowledge: true } }));
  await page.route('**/api/knowledge/documents', r => r.fulfill({ json: [
    { version_key: original, document_id: 'ORIGINAL', version_id: '1', title: 'Original', language: 'en' },
    { version_key: 'b'.repeat(64), document_id: 'TRANSLATED', version_id: '1', title: 'Translation', language: 'es', translation_of: original },
  ] }));
  await page.route('**/api/knowledge/jobs', r => r.fulfill({ json: [] }));
  let uploaded: Record<string, unknown> | undefined;
  await page.route('**/api/knowledge/upload', async r => {
    uploaded = r.request().postDataJSON();
    await r.fulfill({ json: { status: 'queued' } });
  });
  await page.goto('/#/knowledge');
  await page.getByText('Upload and curate a PDF', { exact: true }).click();
  await expect(page.getByLabel('Translated from').locator('option')).toHaveCount(2);
  await page.getByLabel('PDF (up to 10 pages, 5 MB)').setInputFiles({
    name: 'synthetic.pdf', mimeType: 'application/pdf', buffer: Buffer.from('%PDF-1.4 synthetic upload transport fixture'),
  });
  await page.getByRole('combobox', { name: 'Source language', exact: true }).selectOption('pt');
  await page.getByLabel('Translated from').selectOption(original);
  await page.getByLabel('Document ID', { exact: true }).fill('ORIGINAL-PT');
  await page.getByLabel('Version', { exact: true }).fill('1');
  await page.getByLabel('Title', { exact: true }).fill('Procedimento sintético');
  for (const label of ['Source created', 'Effective from', 'Source last reviewed']) {
    await page.getByLabel(label, { exact: true }).fill('2026-11-01T10:00');
  }
  for (const label of ['Expires', 'Next review due']) {
    await page.getByLabel(label, { exact: true }).fill('2026-12-01T10:00');
  }
  await page.getByRole('button', { name: 'Queue PDF', exact: true }).click();
  await expect.poll(() => uploaded).toMatchObject({ language: 'pt', translation_of: original, document_id: 'ORIGINAL-PT' });
  await expect(page.getByRole('status')).toContainText('PDF queued.');
});

test('curation displays the exact native review before publication (UI doubles)', async ({ page }) => {
  let published = false;
  const id = '00000000-0000-4000-8000-000000000041';
  const metadata = { title: 'Synthetic optical procedure', document_id: 'SOP-ONT', version_id: '1',
    effective_from: '2026-10-01T00:00:00Z', expires_at: '2026-12-01T00:00:00Z',
    review_due_at: '2026-11-15T00:00:00Z', checksum: 'b'.repeat(64), acl: ['synthetic-support'] };
  const pending = { execution_id: id, status: 'suspended', action_digest: 'c'.repeat(64),
    request: { job_id: 'a'.repeat(64), metadata } };
  await page.route('**/api/capabilities', route => route.fulfill({ json: { journey: false, voice: false, knowledge: true } }));
  await page.route('**/api/knowledge/documents', route => route.fulfill({ json: published ? [
    { version_key: 'd'.repeat(64), title: metadata.title, document_id: 'SOP-ONT', version_id: '1' },
  ] : [] }));
  await page.route('**/api/knowledge/jobs', route => route.fulfill({ json: [
    { _id: 'a'.repeat(64), document_id: 'SOP-ONT', version_id: '1', status: 'staged', metadata },
  ] }));
  await page.route('**/api/knowledge/request-review', route => route.fulfill({ json: pending }));
  await page.route('**/api/knowledge/review', async route => {
    expect(route.request().postDataJSON()).toEqual({ execution_id: id, action_digest: 'c'.repeat(64), decision: 'approve' });
    await route.fulfill({ json: { execution_id: id, status: 'completed', result: { status: 'approved' } } });
  });
  await page.route('**/api/knowledge/publish', async route => {
    published = true;
    await route.fulfill({ json: { status: 'published', version_key: 'd'.repeat(64) } });
  });
  await page.goto('/');
  await page.getByLabel('Email', { exact: true }).fill('admin@mongodb.com');
  await page.getByLabel('Password', { exact: true }).fill('synthetic-browser-only');
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await page.getByRole('link', { name: 'Knowledge', exact: true }).click();
  await page.getByRole('button', { name: 'Owner: request publication review' }).click();
  await expect(page.getByRole('heading', { name: 'Review this exact publication' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Publish approved version' })).toHaveCount(0);
  await page.getByText('All metadata covered by this approval').click();
  await expect(page.getByText('b'.repeat(64), { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Approve publication', exact: true }).click();
  await page.getByRole('button', { name: 'Publish approved version' }).click();
  await expect(page.getByRole('link', { name: 'Synthetic optical procedure — version 1 (PDF, en)' })).toBeVisible();
});
