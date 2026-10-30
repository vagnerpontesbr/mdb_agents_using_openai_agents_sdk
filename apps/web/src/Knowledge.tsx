import { useEffect, useState } from 'react';
import type { SubmitEvent } from 'react';
import { request } from './api';
import type { Principal } from './api';

type Row = Record<string, unknown>;
function object(value: unknown): Row {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('Invalid response');
  return value as Row;
}
function rows(value: unknown): Row[] {
  if (!Array.isArray(value)) throw new Error('Invalid list response');
  return value.map(object);
}
function pdfData(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result).split(',')[1]);
    reader.onerror = () => reject(new Error('Unable to read this PDF.'));
    reader.readAsDataURL(file);
  });
}

export default function Knowledge({ user }: { user: Principal }) {
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
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Operation failed.'); }
    finally { setBusy(false); }
  }
  async function upload(event: SubmitEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    await action(async () => {
      const file = data.get('pdf');
      if (!(file instanceof File) || file.size < 1 || file.size > 5_000_000) {
        throw new Error('Choose a PDF no larger than 5 MB.');
      }
      const payload: Row = { pdf_base64: await pdfData(file), scanned: data.has('scanned') };
      for (const name of ['document_id', 'version_id', 'title']) payload[name] = String(data.get(name));
      for (const name of ['created_at', 'effective_from', 'expires_at', 'last_reviewed_at', 'review_due_at']) {
        payload[name] = new Date(String(data.get(name))).toISOString();
      }
      const replacement = String(data.get('supersedes') || '');
      if (replacement) payload.supersedes = replacement;
      await request('/api/knowledge/upload', payload);
      form.reset(); setNotice('PDF queued. Start processing to extract and stage it.');
      await refresh();
    });
  }
  async function loadReview(id?: string) {
    const execution = id || sessionStorage.getItem(storageKey);
    if (!execution) throw new Error('No document review to restore.');
    setReview(object(await request('/api/knowledge/review-status', { execution_id: execution })));
  }

  if (!enabled) return null;
  const completed = review?.status === 'completed' ? object(review.result) : null;
  const pendingRequest = review?.status === 'suspended' ? object(review.request) : null;
  const metadata = pendingRequest ? object(pendingRequest.metadata) : null;
  return <section className="panel knowledge" aria-busy={busy}>
    <p className="eyebrow">GOVERNED KNOWLEDGE</p><h2>Technical procedures</h2>
    <p>Current procedures for FiberBox, demo region, firmware 2.x. Sources must pass review before publication.</p>
    <form onSubmit={event => {
      event.preventDefault(); const query = String(new FormData(event.currentTarget).get('query'));
      void action(async () => { setAnswer(String(object(await request('/api/knowledge/search', { query })).text)); });
    }}>
      <label>What do you need help with?<input name="query" required maxLength={2000} disabled={busy} /></label>
      <button disabled={busy}>Find an approved procedure</button>
    </form>
    {answer && <p className="knowledge-answer" style={{ whiteSpace: 'pre-wrap' }}>{answer}</p>}
    <h3>Published sources</h3>
    {documents.length === 0 ? <p>No currently eligible sources.</p> : <ul>{documents.map(doc =>
      <li key={String(doc.version_key)}><a href={`/api/knowledge/source/${encodeURIComponent(String(doc.version_key))}`}>
        {String(doc.title)} — version {String(doc.version_id)} (PDF)</a></li>)}</ul>}
    {user.role === 'admin' && <>
      <details><summary>Upload and curate a PDF</summary>
        <p>Enter the source’s actual dates. The registered owner reviews the source and metadata before publication.</p>
        <form onSubmit={event => { void upload(event); }}>
          <label>PDF (up to 10 pages, 5 MB)<input name="pdf" type="file" accept="application/pdf" required disabled={busy} /></label>
          <label>Document ID<input name="document_id" required maxLength={100} disabled={busy} /></label>
          <label>Version<input name="version_id" required maxLength={100} disabled={busy} /></label>
          <label>Title<input name="title" required maxLength={200} disabled={busy} /></label>
          {([['created_at', 'Source created'], ['effective_from', 'Effective from'], ['expires_at', 'Expires'],
            ['last_reviewed_at', 'Source last reviewed'], ['review_due_at', 'Next review due']] as const).map(([name, label]) =>
            <label key={name}>{label}<input name={name} type="datetime-local" required disabled={busy} /></label>)}
          <label>Replaces<select name="supersedes" disabled={busy}><option value="">New document</option>
            {documents.map(doc => <option key={String(doc.version_key)} value={String(doc.version_key)}>
              {String(doc.document_id)} — {String(doc.version_id)}</option>)}</select></label>
          <label><input name="scanned" type="checkbox" disabled={busy} /> Scanned PDF: use OCR</label>
          <button disabled={busy}>Queue PDF</button>
        </form>
      </details>
      <h3>Ingestion jobs</h3>
      <p>Processing calls the embedding provider. One PDF runs at a time in this app.</p>
      <button disabled={busy} onClick={() => { void action(async () => {
        await request('/api/knowledge/process-next', {}); setNotice('Worker started. Refresh to check progress.');
      }); }}>Process next PDF</button>{' '}
      <button className="secondary" disabled={busy} onClick={() => { void action(refresh); }}>Refresh documents and jobs</button>
      <ul>{jobs.map(job => <li key={String(job._id)}>
        <strong>{String(job.document_id)} / {String(job.version_id)}</strong> — {String(job.status)}{' '}
        <a href={`/api/knowledge/preview/${encodeURIComponent(String(job._id))}`}>Download original</a>{' '}
        {job.status === 'staged' && <button disabled={busy} onClick={() => { void action(async () => {
          const result = object(await request('/api/knowledge/request-review', { job_id: String(job._id) }));
          sessionStorage.setItem(storageKey, String(result.execution_id)); setReview(result);
        }); }}>Owner: request publication review</button>}
      </li>)}</ul>
      <button className="secondary" disabled={busy} onClick={() => { void action(() => loadReview()); }}>Restore / refresh my review</button>
      {metadata && <div><h3>Review this exact publication</h3>
        <p>{String(metadata.title)} — {String(metadata.document_id)}, version {String(metadata.version_id)}</p>
        <p>Effective: {String(metadata.effective_from)}<br />Expires: {String(metadata.expires_at)}<br />Review due: {String(metadata.review_due_at)}</p>
        <details><summary>All metadata covered by this approval</summary><dl>{Object.entries(metadata).map(([key, value]) =>
          <div key={key}><dt>{key.replaceAll('_', ' ')}</dt><dd>{Array.isArray(value) ? value.join(', ') : String(value ?? 'None')}</dd></div>)}</dl></details>
        <a href={`/api/knowledge/preview/${encodeURIComponent(String(pendingRequest?.job_id))}`}>Read the original PDF</a>
        <p>Approval confirms the source, ownership, validity, access and equipment applicability shown here.</p>
        {(['approve', 'reject'] as const).map(decision => <button key={decision} disabled={busy} onClick={() => {
          void action(async () => { setReview(object(await request('/api/knowledge/review', {
            execution_id: String(review?.execution_id), action_digest: String(review?.action_digest), decision,
          }))); });
        }}>{decision === 'approve' ? 'Approve publication' : 'Reject'}</button>)}
      </div>}
      {completed && <p>Native review: {String(completed.status)}</p>}
      {completed?.status === 'approved' && <button disabled={busy} onClick={() => { void action(async () => {
        await request('/api/knowledge/publish', { execution_id: String(review?.execution_id) });
        setNotice('Document published. Search indexing may take a moment.'); await refresh();
      }); }}>Publish approved version</button>}
    </>}
    {notice && <p role="status">{notice}</p>}{error && <p role="alert">{error}</p>}
  </section>;
}
