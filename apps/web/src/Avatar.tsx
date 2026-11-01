import { useState } from 'react';
import { ApiError, request } from './api';
import { useI18n } from './i18n';
import { parseProfile } from './profileApi';
import type { ProfileData } from './profileApi';

export function AvatarImage({ data }: { data: ProfileData }) {
  const { t } = useI18n();
  const [failed, setFailed] = useState(false);
  const initials = data.display_name.trim().split(/\s+/).slice(0, 2).map(word => Array.from(word)[0] ?? '').join('').toUpperCase() || '?';
  return data.has_avatar && !failed ? <img className="avatar-image" src={`/api/profile/avatar?v=${data.revision}`}
    alt={t('Your profile photo')} onError={() => setFailed(true)} /> :
    <span className="avatar-initials" role="img" aria-label={t('Profile initials')}>{initials}</span>;
}

export default function AvatarEditor({ data, saved }: { data: ProfileData; saved: (value: ProfileData) => void }) {
  const { t } = useI18n();
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  async function change(file?: File) {
    if (busy) return;
    if (file && (file.size < 1 || file.size > 2 * 1024 * 1024 || !['image/png', 'image/jpeg'].includes(file.type))) {
      setMessage('Choose a JPEG or PNG up to 2 MiB.'); return;
    }
    setBusy(true); setMessage('');
    try {
      let payload: Record<string, unknown> = {expected_revision: data.revision};
      if (file) {
        const encoded = await new Promise<string>((resolve, reject) => {
          const reader = new FileReader();
          reader.onload = () => resolve(String(reader.result).split(',')[1]);
          reader.onerror = () => reject(new Error('Photo read failed'));
          reader.readAsDataURL(file);
        });
        payload = {...payload, mime: file.type, content_base64: encoded};
      }
      saved(parseProfile(await request(file ? '/api/profile/avatar' : '/api/profile/avatar/remove', payload)));
      setMessage(file ? 'Photo saved.' : 'Photo removed.');
    } catch (error) {
      setMessage(error instanceof ApiError && error.status === 409 ? 'Profile changed. Reload before saving.' :
        error instanceof ApiError && [400, 413].includes(error.status) ? 'Choose a valid JPEG or PNG within the image limits.' :
        'Photo change could not be confirmed. Reload your profile before trying again.');
    } finally { setBusy(false); }
  }
  return <section aria-label={t('Profile photo')} className="avatar-editor" aria-busy={busy}>
    <h2>{t('Profile photo')}</h2>
    <AvatarImage key={`${data.user_id}-${data.revision}`} data={data} />
    <label>{t('Choose photo')}<input type="file" accept="image/jpeg,image/png" disabled={busy} onChange={event => {
      const file = event.currentTarget.files?.[0]; event.currentTarget.value = '';
      if (file) void change(file);
    }} /></label>
    <p>{t('JPEG or PNG up to 2 MiB, 4096 pixels per side and 4 million pixels. Metadata is removed.')}</p>
    {data.has_avatar && <button type="button" className="secondary" disabled={busy} onClick={() => { void change(); }}>{t('Remove photo')}</button>}
    {message && <p role="status">{t(message)}</p>}
  </section>;
}
