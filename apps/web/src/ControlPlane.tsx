import { useEffect, useState } from 'react';
import { request } from './api';
import { formatTimestamp, useI18n } from './i18n';

type Values = { chat_max_chars: number; knowledge_query_max_chars: number; library_cache_max_age_seconds: number };
type View = { revision: number; values: Values; editable: boolean; source: string; observed_at: string; capabilities?: Record<string, boolean> };
const fields: { key: keyof Values; label: string; min: number; max: number }[] = [
  { key: 'chat_max_chars', label: 'Maximum message characters', min: 100, max: 4000 },
  { key: 'knowledge_query_max_chars', label: 'Maximum library query characters', min: 100, max: 2000 },
  { key: 'library_cache_max_age_seconds', label: 'Library cache age (seconds)', min: 1, max: 900 },
];
function parse(value: unknown): View {
  if (!value || typeof value !== 'object') throw new Error();
  const data = value as View;
  if (!Number.isInteger(data.revision) || data.revision < 0 || typeof data.editable !== 'boolean' || !data.values ||
      fields.some(field => !Number.isInteger(data.values[field.key]) || data.values[field.key] < field.min || data.values[field.key] > field.max) ||
      !['application_database', 'code_defaults'].includes(data.source) || typeof data.observed_at !== 'string') throw new Error();
  return data;
}
export default function ControlPlane({ page }: { page: string }) {
  const { t, locale, timezone } = useI18n();
  const [data, setData] = useState<View | null>(null);
  const [draft, setDraft] = useState<Values | null>(null);
  const [busy, setBusy] = useState(false);
  const [uncertain, setUncertain] = useState(false);
  const [message, setMessage] = useState('Loading settings…');
  const [reload, setReload] = useState(0);
  useEffect(() => {
    let active = true;
    request('/api/admin/control-plane').then(value => {
      if (!active) return;
      const next = parse(value); setData(next); setDraft(next.values); setUncertain(false); setMessage('Settings loaded.');
    }).catch(() => { if (active) { setData(null); setMessage('Settings unavailable. Reload before continuing.'); } });
    return () => { active = false; };
  }, [reload]);
  async function save(event: React.FormEvent) {
    event.preventDefault();
    if (!data || !draft || busy || uncertain) return;
    setBusy(true);
    try {
      const next = parse(await request('/api/admin/control-plane', { ...draft, expected_revision: data.revision }));
      setData({ ...data, ...next }); setDraft(next.values); setMessage('Settings saved. Subsequent operations use the new values.');
    } catch { setUncertain(true); setMessage('Settings changed or save is uncertain. Reload before trying again.'); }
    finally { setBusy(false); }
  }
  return <div>
    <p role="status">{t(message)}</p>
    <button className="secondary" disabled={busy} onClick={() => { setData(null); setReload(x => x + 1); }}>{t('Reload settings')}</button>
    {data && <>
      <p>{t('Configuration source:')} {t(data.source)}</p>
      <p>{t('Revision:')} {data.revision}</p>
      <p>{t('Observed at:')} {formatTimestamp(data.observed_at, locale, timezone)}</p>
      <p>{t('Configuration is not a live health check.')}</p>
      {page === 'overview' && draft && <form onSubmit={event => { void save(event); }}>
        {fields.map(field => <label key={field.key}>{t(field.label)}<input type="number" required step={1} min={field.min} max={field.max}
          value={draft[field.key]} disabled={!data.editable || busy || uncertain}
          onChange={event => setDraft({ ...draft, [field.key]: Number(event.target.value) })} /></label>)}
        <p>{t('Library cache settings affect library searches only. Hosted Engine cache is read-only.')}</p>
        <p>{t('Saving affects subsequent operations. Active executions keep their settings.')}</p>
        {!data.editable && <p>{t('Editing requires configured application persistence.')}</p>}
        <button disabled={!data.editable || busy || uncertain}>{t('Save and apply')}</button>
      </form>}
      {page === 'capabilities' && <dl>{['journey', 'voice', 'knowledge', 'localized_turns'].map(key => <div key={key}>
        <dt>{t(key)}</dt><dd>{t(data.capabilities?.[key] ? 'Configured' : 'Not configured')}</dd></div>)}</dl>}
      {page === 'integrations' && <>
        <p>{t('Application data: OpenAI-SDK')}</p><p>{t('Managed memory owner: Agent Engine')}</p>
        <p>{t('Memory migration to mymemory is planned, not active.')}</p>
        <p>{t('Provider credentials, models and Engine policies are not editable here.')}</p>
      </>}
    </>}
  </div>;
}

export function UsersList() {
  const { t } = useI18n();
  const [rows, setRows] = useState<{ user_id: string; email: string; role: string }[]>([]);
  const [next, setNext] = useState<string | null>(null);
  const [cursor, setCursor] = useState<string | null>(null);
  const [reload, setReload] = useState(0);
  const [message, setMessage] = useState('Loading users…');
  useEffect(() => {
    let active = true;
    request('/api/users?limit=20' + (cursor ? '&after=' + encodeURIComponent(cursor) : '')).then(value => {
      if (!active) return;
      const data = value as { items: typeof rows; next_cursor: string | null };
      if (!Array.isArray(data.items) || data.items.length > 20 || data.items.some(row => typeof row.user_id !== 'string' || typeof row.email !== 'string' || !['admin', 'user'].includes(row.role)) ||
          !(data.next_cursor === null || typeof data.next_cursor === 'string')) throw new Error();
      setRows(data.items); setNext(data.next_cursor); setMessage(data.items.length ? '' : 'No users found.');
    }).catch(() => { if (active) { setRows([]); setNext(null); setMessage('Users unavailable.'); } });
    return () => { active = false; };
  }, [cursor, reload]);
  return <div><h2>{t('Registered users')}</h2><p role="status">{t(message)}</p>
    <button className="secondary" onClick={() => { setCursor(null); setReload(x => x + 1); }}>{t('Reload users')}</button>
    <ul>{rows.map(row => <li key={row.user_id}>{row.email} — {t(row.role)}</li>)}</ul>
    {next && <button onClick={() => setCursor(next)}>{t('Next page')}</button>}
  </div>;
}
