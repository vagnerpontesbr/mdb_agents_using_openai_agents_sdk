import { useState } from 'react';
import { ApiError, request } from './api';
import type { Locale } from './catalogs';
import { useI18n } from './i18n';
import AvatarEditor from './Avatar';
import { parseProfile } from './profileApi';
import type { ProfileData } from './profileApi';
export default function Profile({ data, saved, reload }: { data: ProfileData; saved: (value: ProfileData) => void; reload: () => void }) {
  const { t } = useI18n();
  const [name, setName] = useState(data.display_name);
  const [timezone, setTimezone] = useState(data.timezone);
  const [locale, setLocale] = useState(data.locale);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  return <section className="panel profile-panel"><h1>{t('My profile')}</h1><p>{data.email} · {t(data.role)}</p>
    <AvatarEditor data={data} saved={saved} />
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
    <p className="hint">{t('Password editing is coming in the next profile phase.')}</p>
  </section>;
}
