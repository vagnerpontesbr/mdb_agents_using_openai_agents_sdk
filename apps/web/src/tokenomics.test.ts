import { afterEach, expect, test, vi } from 'vitest';
import { fixture } from '../e2e/tokenomics-fixture';
import { parseDashboard, parseFocus, parseMetric, loadTokenomics } from './tokenomicsApi';
import { displayMetric } from './Tokenomics';
import { request } from './api';

afterEach(() => vi.unstubAllGlobals());
test('server contracts retain estimates, missing values and precision', () => {
  const view = parseDashboard(fixture.dashboard);
  expect(view.kpis.total_cost.value).toBe('0.000016');
  expect(view.kpis.execution_count.value).toBeNull();
  expect(parseFocus(fixture.focus).records).toEqual([]);
  expect(displayMetric(view.kpis.total_cost, 'pt-BR')).toContain('0,000016');
  expect(displayMetric({ ...view.kpis.total_cost, value: '0.000000001' }, 'en-US')).toContain('E-9');
  expect(displayMetric(view.kpis.execution_count, 'en-US')).toBe('—');
});
test('malformed, nonfinite and dishonest estimated responses fail closed', () => {
  for (const value of ['NaN', 'Infinity', 'text', '9007199254740992']) {
    expect(() => parseMetric({ ...fixture.dashboard.kpis.total_cost, value })).toThrow();
  }
  const d = structuredClone(fixture.dashboard);
  d.estimate!.price.source_url = 'https://untrusted.example/pricing';
  expect(() => parseDashboard(d)).toThrow();
  expect(() => parseDashboard({ ...fixture.dashboard, estimate: null })).toThrow();
  expect(() => parseDashboard({ ...fixture.dashboard, models: { status: 'available', rows: [] } })).toThrow();
});
test('FOCUS never relabels estimates as billed', () => {
  expect(() => parseFocus({ schema_version: 1, status: 'available', next_cursor: null, reason: null,
    records: [{ record_id: 'synthetic', provider: 'test', sku: 'test', consumed: fixture.dashboard.kpis.observed_tokens,
      billed_cost: fixture.dashboard.kpis.total_cost, estimated_cost: null }] })).toThrow();
});
test('each refresh uses exactly two distinct read endpoints and no mutations', async () => {
  const fetcher = vi.fn(async (path: string) => new Response(JSON.stringify(path.includes('focus-records') ? fixture.focus : fixture.dashboard)));
  vi.stubGlobal('fetch', fetcher);
  await loadTokenomics('30d');
  expect(fetcher).toHaveBeenCalledTimes(2);
  expect(fetcher.mock.calls.map(call => call[0]).sort()).toEqual([
    '/api/admin/tokenomics/dashboard?period=30d', '/api/admin/tokenomics/focus-records?period=30d&limit=100',
  ]);
});
test('Engine expiry is not an application sign-in failure and raw details stay hidden', async () => {
  const fetcher = vi.fn().mockResolvedValue(new Response(JSON.stringify({ code: 'tokenomics_auth_expired', error: 'PRIVATE' }), { status: 503 }));
  vi.stubGlobal('fetch', fetcher);
  await expect(request('/api/admin/tokenomics/dashboard')).rejects.toThrow('Engine session expired. An operator must refresh it.');
  expect(fetcher).toHaveBeenCalledTimes(1);
});
