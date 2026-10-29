import { afterEach, expect, test, vi } from 'vitest';
import { ApiError, principal, request } from './api';

afterEach(() => vi.unstubAllGlobals());

test('rejects malformed identities and unrecognized roles', () => {
  for (const value of [null, {}, { user_id: '1', email: 'a', role: 'owner' }]) {
    expect(() => principal(value)).toThrow('Invalid server response');
  }
});

test('never exposes raw backend error details or retries a write', async () => {
  const fetcher = vi.fn().mockResolvedValue(new Response(JSON.stringify({ error: 'private-detail' }), { status: 503 }));
  vi.stubGlobal('fetch', fetcher);
  await expect(request('/api/users', { email: 'test@example.test' })).rejects.toThrow('Service unavailable');
  expect(fetcher).toHaveBeenCalledTimes(1);
});

test('preserves unauthorized status so the UI can discard a stale session', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('{}', { status: 401 })));
  await expect(request('/api/me')).rejects.toBeInstanceOf(ApiError);
});
