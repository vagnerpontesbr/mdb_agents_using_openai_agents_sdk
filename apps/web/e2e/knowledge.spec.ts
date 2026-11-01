import { expect, test } from '@playwright/test';

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
  await expect(page.getByRole('link', { name: 'Synthetic optical procedure — version 1 (PDF)' })).toBeVisible();
});
