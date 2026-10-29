export type Role = 'user' | 'admin';
export type Principal = { user_id: string; email: string; role: Role };

export class ApiError extends Error {
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

export async function request(path: string, data?: Record<string, string>): Promise<unknown> {
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
    throw new Error('Connection unavailable. Check your session before trying again.');
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
    throw new ApiError(response.status, messages[response.status] ?? 'Request failed.');
  }
  return result;
}
