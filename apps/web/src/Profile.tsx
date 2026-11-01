import { useState } from 'react';
import { ApiError, request } from './api';
import { locales } from './catalogs';
import type { Locale } from './catalogs';
import { useI18n } from './i18n';
export type ProfileData = { user_id: string; email: string; role: 'user' | 'admin'; display_name: string; timezone: string; locale: Locale; revision: number };
export function parseProfile(value: unknown): ProfileData {
  const p = value as ProfileData;
  if (!p || typeof p.user_id !== 'string' || typeof p.email !== 'string' || !['user', 'admin'].includes(p.role)
    || typeof p.display_name !== 'string' || typeof p.timezone !== 'string' || !locales.includes(p.locale)
    || !Number.isSafeInteger(p.revision) || p.revision < 0) throw new Error('Invalid profile');
  new Intl.DateTimeFormat('en-US', {timeZone:p.timezone});
  return p;
}
export default function Profile({ data, saved, reload }: { data: ProfileData; saved: (value: ProfileData) => void; reload: () => void }) {
  const { t } = useI18n();
  const [name, setName] = useState(data.display_name);
  const [timezone, setTimezone] = useState(data.timezone);
  const [locale, setLocale] = useState(data.locale);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  return <section className="panel"><h1>{t('My profile')}</h1><p>{data.email} · {t(data.role)}</p>
    <form onSubmit={async event => {
      event.preventDefault(); if (busy) return; setBusy(true); setMessage('');
      try {
        const value = parseProfile(await request('/api/profile', { display_name: name, timezone, locale, expected_revision: data.revision }));
        saved(value); setMessage('Profile saved.');
      } catch (error) {
        setMessage(error instanceof ApiError && error.status === 409 ? 'Profile changed. Reload before saving.' :
          error instanceof ApiError && error.status === 400 ? 'Check the name, timezone and language.' :
          'Unable to save profile. Check the result before trying again.');
      } finally { setBusy(false); }
    }}>
      <label>{t('Display name')}<input required maxLength={80} value={name} onChange={e => setName(e.target.value)} disabled={busy} /></label>
      <label>{t('Timezone')}<input required maxLength={100} value={timezone} onChange={e => setTimezone(e.target.value)} disabled={busy} list="timezones" /></label>
      <datalist id="timezones">{['UTC', ...Intl.supportedValuesOf('timeZone')].map(zone => <option key={zone} value={zone} />)}</datalist>
      <label>{t('Language')}<select value={locale} onChange={e => setLocale(e.target.value as Locale)} disabled={busy}>
        <option value="en-US">English</option><option value="pt-BR">Português (Brasil)</option><option value="es-ES">Español</option>
      </select></label>
      <button disabled={busy}>{t(busy ? 'Saving…' : 'Save profile')}</button>
      <button type="button" className="secondary" disabled={busy} onClick={reload}>{t('Reload profile')}</button>
    </form>
    {message && <p role="status">{t(message)}</p>}
    <p className="hint">{t('Photo and password editing are coming in the next profile phases.')}</p>
  </section>;
}
