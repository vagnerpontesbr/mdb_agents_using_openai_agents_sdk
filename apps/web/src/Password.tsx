import { useState } from 'react';
import { ApiError, request } from './api';
import { useI18n } from './i18n';

export default function Password() {
  const { t } = useI18n();
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  return <section className="password-editor" aria-label={t('Change password')}>
    <h2>{t('Change password')}</h2>
    <p>{t('Changing your password signs out all existing sessions. Sign in again afterward.')}</p>
    <form onSubmit={async event => {
      event.preventDefault(); if (busy) return;
      const form = event.currentTarget;
      const fields = new FormData(form);
      setBusy(true); setMessage('');
      try {
        await request('/api/profile/password', {
          current_password: String(fields.get('current_password') ?? ''),
          new_password: String(fields.get('new_password') ?? ''),
          confirmation: String(fields.get('confirmation') ?? ''),
        });
        window.dispatchEvent(new Event('telecom-password-changed'));
      } catch (error) {
        setMessage(error instanceof ApiError && error.status === 400 ? 'Check your current password and matching new passwords (8–128 characters).' :
          error instanceof ApiError && error.status === 429 ? 'Too many password attempts. Try again in 15 minutes.' :
          'Password change could not be confirmed. Sign in again to check before retrying.');
      } finally { form.reset(); setBusy(false); }
    }}>
      <label>{t('Current password')}<input name="current_password" type="password" autoComplete="current-password" required minLength={8} maxLength={128} disabled={busy} /></label>
      <label>{t('New password')}<input name="new_password" type="password" autoComplete="new-password" required minLength={8} maxLength={128} disabled={busy} /></label>
      <label>{t('Confirm new password')}<input name="confirmation" type="password" autoComplete="new-password" required minLength={8} maxLength={128} disabled={busy} /></label>
      <button disabled={busy}>{t(busy ? 'Working…' : 'Change password')}</button>
    </form>
    {message && <p role="alert">{t(message)}</p>}
  </section>;
}
