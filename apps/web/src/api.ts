export type Role = 'user' | 'admin';
export type Principal = { user_id: string; email: string; role: Role };

export class InterfaceError extends Error {
  constructor(public readonly key: string) { super(key); }
}

export class ApiError extends InterfaceError {
  constructor(public readonly status: number, message: string) { super(message); }
}

export function principal(value: unknown): Principal {
  if (typeof value !== 'object' || value === null) throw new Error('Invalid server response');
  const data = value as Record<string, unknown>;
  if (typeof data.user_id !== 'string' || typeof data.email !== 'string'
      || (data.role !== 'user' && data.role !== 'admin')) {
    throw new Error('Invalid server response');
  }
  return { user_id: data.user_id, email: data.email, role: data.role };
}

export async function request(path: string, data?: Record<string, unknown>): Promise<unknown> {
  let response: Response;
  try {
    response = await fetch(path, {
      method: data === undefined ? 'GET' : 'POST',
      credentials: 'same-origin',
      headers: data === undefined ? {} : { 'Content-Type': 'application/json' },
      body: data === undefined ? undefined : JSON.stringify(data),
      signal: AbortSignal.timeout(60_000),
    });
  } catch {
    // Never retry account writes automatically after an uncertain network outcome.
    throw new InterfaceError('Connection unavailable. Check your session before trying again.');
  }
  if (response.status === 401 && !['/api/login', '/api/me'].includes(path) && typeof window !== 'undefined') {
    window.dispatchEvent(new Event('telecom-session-expired'));
  }
  const result: unknown = await response.json();
  if (!response.ok) {
    const messages: Record<number, string> = {
      400: 'Check the email, password and role.',
      401: 'Sign in again or check your credentials.',
      403: 'You do not have permission to perform this action.',
      409: 'This email is already registered.',
      429: 'Too many sign-in attempts. Try again in one minute.',
      503: 'Service unavailable. Check the result before trying again.',
    };
    if (path.startsWith('/api/knowledge/')) {
      messages[400] = path === '/api/knowledge/search' ? 'Check the search query and its length.' : 'Check the PDF and document metadata.';
      messages[409] = 'The document or review changed. Refresh its status before trying again.';
      messages[413] = 'The PDF exceeds the 5 MB demo limit.';
    }
    throw new ApiError(response.status, messages[response.status] ?? 'Request failed.');
  }
  return result;
}
