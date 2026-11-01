import { formatTimestamp, useI18n } from './i18n';
import { useEffect, useState } from 'react';
import type { SubmitEvent } from 'react';
import { InterfaceError, request } from './api';
import type { Principal } from './api';

type Row = Record<string, unknown>;
function object(value: unknown): Row {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new InterfaceError('Invalid response');
  return value as Row;
}
function rows(value: unknown): Row[] {
  if (!Array.isArray(value)) throw new InterfaceError('Invalid list response');
  return value.map(object);
}
function pdfData(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result).split(',')[1]);
    reader.onerror = () => reject(new InterfaceError('Unable to read this PDF.'));
    reader.readAsDataURL(file);
  });
}

export default function Knowledge({ user }: { user: Principal }) {
  const { t, locale, timezone } = useI18n();
  const [enabled, setEnabled] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [jobs, setJobs] = useState<Row[]>([]);
  const [documents, setDocuments] = useState<Row[]>([]);
  const [review, setReview] = useState<Row | null>(null);
  const [answer, setAnswer] = useState('');
  const storageKey = `telecom-document-review:${user.user_id}`;

  useEffect(() => {
    let active = true;
    request('/api/capabilities').then(async value => {
      if (object(value).knowledge !== true || !active) return;
      setEnabled(true);
      const current = rows(await request('/api/knowledge/documents'));
      if (active) setDocuments(current);
      if (user.role === 'admin') {
        const items = rows(await request('/api/knowledge/jobs'));
        if (active) setJobs(items);
      }
    }).catch(() => { if (active) setError('Unable to load document access.'); });
    return () => { active = false; };
  }, [user.role]);

  async function refresh() {
    setDocuments(rows(await request('/api/knowledge/documents')));
    if (user.role === 'admin') setJobs(rows(await request('/api/knowledge/jobs')));
  }
  async function action(run: () => Promise<void>) {
    if (busy) return;
    setBusy(true); setError(''); setNotice('');
    try { await run(); }
    catch (reason) { setError(reason instanceof InterfaceError ? reason.key : 'Operation failed.'); }
    finally { setBusy(false); }
  }
  async function upload(event: SubmitEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    await action(async () => {
      const file = data.get('pdf');
      if (!(file instanceof File) || file.size < 1 || file.size > 5_000_000) {
        throw new InterfaceError('Choose a PDF no larger than 5 MB.');
      }
      const payload: Row = { pdf_base64: await pdfData(file), scanned: data.has('scanned') };
      for (const name of ['document_id', 'version_id', 'title']) payload[name] = String(data.get(name));
      for (const name of ['created_at', 'effective_from', 'expires_at', 'last_reviewed_at', 'review_due_at']) {
        payload[name] = new Date(String(data.get(name))).toISOString();
      }
      payload.language = String(data.get('language') || 'en');
      const original = String(data.get('translation_of') || '');
      if (original) payload.translation_of = original;
      const replacement = String(data.get('supersedes') || '');
      if (replacement) payload.supersedes = replacement;
      await request('/api/knowledge/upload', payload);
      form.reset(); setNotice('PDF queued. Start processing to extract and stage it.');
      await refresh();
    });
  }
  async function loadReview(id?: string) {
    const execution = id || sessionStorage.getItem(storageKey);
    if (!execution) throw new InterfaceError('No document review to restore.');
    setReview(object(await request('/api/knowledge/review-status', { execution_id: execution })));
  }

  if (!enabled) return null;
  const completed = review?.status === 'completed' ? object(review.result) : null;
  const pendingRequest = review?.status === 'suspended' ? object(review.request) : null;
  const metadata = pendingRequest ? object(pendingRequest.metadata) : null;
  return <section className="panel knowledge" aria-busy={busy}>
    <p className="eyebrow">{t("GOVERNED KNOWLEDGE")}</p><h2>{t("Technical procedures")}</h2>
    <p>{t("Current procedures for FiberBox, demo region, firmware 2.x. Sources must pass review before publication.")}</p>
    <form onSubmit={event => {
      event.preventDefault(); const query = String(new FormData(event.currentTarget).get('query'));
      void action(async () => { setAnswer(String(object(await request('/api/knowledge/search', { query })).text)); });
    }}>
      <label>{t("What do you need help with?")}<input name="query" required maxLength={2000} disabled={busy} /></label>
      <button disabled={busy}>{t("Find an approved procedure")}</button>
    </form>
    {answer && <p className="knowledge-answer" style={{ whiteSpace: 'pre-wrap' }}>{answer}</p>}
    <h3>{t("Published sources")}</h3>
    {documents.length === 0 ? <p>{t("No currently eligible sources.")}</p> : <ul>{documents.map(doc =>
      <li key={String(doc.version_key)}><a href={`/api/knowledge/source/${encodeURIComponent(String(doc.version_key))}`}>
        {String(doc.title)} — {t('version')} {String(doc.version_id)} (PDF, {String(doc.language || 'en')})</a></li>)}</ul>}
    {user.role === 'admin' && <>
      <details><summary>{t("Upload and curate a PDF")}</summary>
        <p>{t("Enter the source\u2019s actual dates. The registered owner reviews the source and metadata before publication.")}</p>
        <form onSubmit={event => { void upload(event); }}>
          <label>{t("PDF (up to 10 pages, 5 MB)")}<input name="pdf" type="file" accept="application/pdf" required disabled={busy} /></label>
          <label>{t('Source language')}<select name="language" defaultValue="en" disabled={busy}>
            <option value="en">{t('English')}</option><option value="pt">{t('Portuguese (Brazil)')}</option>
            <option value="es">{t('Spanish')}</option>
          </select></label>
          <label>{t('Translated from')}<select name="translation_of" defaultValue="" disabled={busy}>
            <option value="">{t('Original document (not a translation)')}</option>
            {documents.filter(doc => !doc.translation_of).map(doc => <option key={String(doc.version_key)} value={String(doc.version_key)}>
              {String(doc.document_id)} — {String(doc.version_id)} ({String(doc.language || 'en')})
            </option>)}
          </select></label>
          <label>{t("Document ID")}<input name="document_id" required maxLength={100} disabled={busy} /></label>
          <label>{t("Version")}<input name="version_id" required maxLength={100} disabled={busy} /></label>
          <label>{t("Title")}<input name="title" required maxLength={200} disabled={busy} /></label>
          {([['created_at', 'Source created'], ['effective_from', 'Effective from'], ['expires_at', 'Expires'],
            ['last_reviewed_at', 'Source last reviewed'], ['review_due_at', 'Next review due']] as const).map(([name, label]) =>
            <label key={name}>{t(label)}<input name={name} type="datetime-local" required disabled={busy} /></label>)}
          <label>{t("Replaces")}<select name="supersedes" disabled={busy}><option value="">{t("New document")}</option>
            {documents.map(doc => <option key={String(doc.version_key)} value={String(doc.version_key)}>
              {String(doc.document_id)} — {String(doc.version_id)}</option>)}</select></label>
          <label><input name="scanned" type="checkbox" disabled={busy} /> {t("Scanned PDF: use OCR")}</label>
          <button disabled={busy}>{t("Queue PDF")}</button>
        </form>
      </details>
      <h3>{t("Ingestion jobs")}</h3>
      <p>{t("Processing calls the embedding provider. One PDF runs at a time in this app.")}</p>
      <button disabled={busy} onClick={() => { void action(async () => {
        await request('/api/knowledge/process-next', {}); setNotice('Worker started. Refresh to check progress.');
      }); }}>{t("Process next PDF")}</button>{' '}
      <button className="secondary" disabled={busy} onClick={() => { void action(refresh); }}>{t("Refresh documents and jobs")}</button>
      <ul>{jobs.map(job => <li key={String(job._id)}>
        <strong>{String(job.document_id)} / {String(job.version_id)}</strong> — {t(String(job.status))}{' '}
        <a href={`/api/knowledge/preview/${encodeURIComponent(String(job._id))}`}>{t("Download original")}</a>{' '}
        {job.status === 'staged' && <button disabled={busy} onClick={() => { void action(async () => {
          const result = object(await request('/api/knowledge/request-review', { job_id: String(job._id) }));
          sessionStorage.setItem(storageKey, String(result.execution_id)); setReview(result);
        }); }}>{t("Owner: request publication review")}</button>}
      </li>)}</ul>
      <button className="secondary" disabled={busy} onClick={() => { void action(() => loadReview()); }}>{t("Restore / refresh my review")}</button>
      {metadata && <div><h3>{t("Review this exact publication")}</h3>
        <p>{String(metadata.title)} — {String(metadata.document_id)}, {t('version')} {String(metadata.version_id)}</p>
        <p>{t('Source language')}: {String(metadata.language || 'en')}</p>
        {typeof metadata.translation_of === 'string' && <p>{t('Translated from')}: {String(metadata.translation_of)}</p>}
        <p>{t("Effective:")} {formatTimestamp(metadata.effective_from, locale, timezone)}<br />{t("Expires:")} {formatTimestamp(metadata.expires_at, locale, timezone)}<br />{t("Review due:")} {formatTimestamp(metadata.review_due_at, locale, timezone)}</p>
        <details><summary>{t("All metadata covered by this approval")}</summary><dl>{Object.entries(metadata).map(([key, value]) =>
          <div key={key}><dt>{key.replaceAll('_', ' ')}</dt><dd>{Array.isArray(value) ? value.join(', ') : value == null ? t('None') : String(value)}</dd></div>)}</dl></details>
        <a href={`/api/knowledge/preview/${encodeURIComponent(String(pendingRequest?.job_id))}`}>{t("Read the original PDF")}</a>
        <p>{t("Approval confirms the source, ownership, validity, access and equipment applicability shown here.")}</p>
        {(['approve', 'reject'] as const).map(decision => <button key={decision} disabled={busy} onClick={() => {
          void action(async () => { setReview(object(await request('/api/knowledge/review', {
            execution_id: String(review?.execution_id), action_digest: String(review?.action_digest), decision,
          }))); });
        }}>{t(decision === 'approve' ? 'Approve publication' : 'Reject')}</button>)}
      </div>}
      {completed && <p>{t("Native review:")} {t(String(completed.status))}</p>}
      {completed?.status === 'approved' && <button disabled={busy} onClick={() => { void action(async () => {
        await request('/api/knowledge/publish', { execution_id: String(review?.execution_id) });
        setNotice('Document published. Search indexing may take a moment.'); await refresh();
      }); }}>{t("Publish approved version")}</button>}
    </>}
    {notice && <p role="status">{t(notice)}</p>}{error && <p role="alert">{t(error)}</p>}
  </section>;
}
