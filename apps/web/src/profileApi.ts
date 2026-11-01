import { locales } from './catalogs';
import type { Locale } from './catalogs';
export type ProfileData = { user_id: string; email: string; role: 'user' | 'admin'; display_name: string; timezone: string; locale: Locale; revision: number; has_avatar?: boolean };
export function parseProfile(value: unknown): ProfileData {
  const p = value as ProfileData;
  if (!p || typeof p.user_id !== 'string' || typeof p.email !== 'string' || !['user', 'admin'].includes(p.role)
    || typeof p.display_name !== 'string' || typeof p.timezone !== 'string' || !locales.includes(p.locale)
    || (p.has_avatar !== undefined && typeof p.has_avatar !== 'boolean')
    || !Number.isSafeInteger(p.revision) || p.revision < 0) throw new Error('Invalid profile');
  new Intl.DateTimeFormat('en-US', {timeZone:p.timezone});
  return p;
}
