import { useI18n } from './i18n';
import { locales } from './catalogs';
import type { Locale } from './catalogs';
import { useEffect, useRef, useState } from 'react';
import type { Principal } from './api';
import { request } from './api';
import { startRecording } from './recording';
import type { Recording } from './recording';

const languageNames: Record<Locale, string> = { 'en-US': 'English', 'pt-BR': 'Portuguese (Brazil)', 'es-ES': 'Spanish' };

type Execution = {
  locale?: Locale; execution_id?: string; status: string; text?: string; outcome?: string;
  specialists?: string[]; action_digest?: string;
  action?: { plan_id: string; monthly_minor: number; proposal_id: string };
};

function execution(value: unknown): Execution {
  if (!value || typeof value !== 'object' || !('status' in value) || typeof value.status !== 'string') {
    throw new Error('Invalid execution response');
  }
  if ('locale' in value && !locales.includes(value.locale as Locale)) {
    throw new Error('Invalid execution language');
  }
  return { ...value, locale: ('locale' in value ? value.locale : 'en-US') } as Execution;
}

export default function Journey({ user, active = true }: { user: Principal; active?: boolean }) {
  const { t, locale } = useI18n();
  const [conversation, setConversation] = useState(() => {
    const key = `telecom-conversation-${user.user_id}`;
    const saved = sessionStorage.getItem(key);
    if (saved && /^[0-9a-f-]{36}$/.test(saved)) return saved;
    const id = crypto.randomUUID(); sessionStorage.setItem(key, id); return id;
  });
  const [available, setAvailable] = useState(false);
  const [messageLimit, setMessageLimit] = useState(4000);
  const [voice, setVoice] = useState(false);
  const [draft, setDraft] = useState('');
  const [draftLocale, setDraftLocale] = useState<Locale | null>(null);
  const recordingLocale = useRef<Locale>('en-US');
  const playbackGeneration = useRef(0);
  const [busy, setBusy] = useState(false);
  const [recoveryRequired, setRecoveryRequired] = useState(true);
  const [message, setMessage] = useState('Checking support availability…');
  const [current, setCurrent] = useState<Execution | null>(null);
  const [history, setHistory] = useState<{ role: string; text: string }[]>([]);
  const [recording, setRecording] = useState(false);
  const capture = useRef<Recording | null>(null);
  const abort = useRef<AbortController | null>(null);
  const audio = useRef<HTMLAudioElement | null>(null);
  const audioUrl = useRef<string | null>(null);
  const polls = useRef(0);
  const mounted = useRef(true);
  const visible = useRef(active);
  useEffect(() => {
    visible.current = active;
    if (!active) {
      const recorder = capture.current; capture.current = null;
      void recorder?.cancel(); playbackGeneration.current++; audio.current?.pause();
      setRecording(false);
      if (recorder) setMessage('Recording discarded when leaving Support.');
    }
  }, [active]);

  useEffect(() => {
    mounted.current = true;
    request('/api/capabilities').then(value => {
      const data = value as { journey: boolean; voice: boolean; chat_max_chars?: number };
      if (!mounted.current) return;
      setAvailable(data.journey); setVoice(data.voice);
      if (Number.isInteger(data.chat_max_chars) && data.chat_max_chars! >= 100 && data.chat_max_chars! <= 4000) setMessageLimit(data.chat_max_chars!);
      setMessage(data.journey ? 'Ask about your invoice, connection or plans.' :
        'The support journey is not configured. Your account remains available.');
    }).catch(() => setMessage('Support availability could not be checked.'));
    return () => {
      mounted.current = false; abort.current?.abort();
      void capture.current?.cancel(); audio.current?.pause();
      if (audioUrl.current) URL.revokeObjectURL(audioUrl.current);
    };
  }, []);

  useEffect(() => {
    if (!available) return;
    let active = true;
    request('/api/journey/latest', { conversation_id: conversation }).then(value => {
      if (!active) return;
      const result = execution(value);
      const uncertain = sessionStorage.getItem(`telecom-uncertain-${conversation}`) !== null;
      setCurrent(result); polls.current = 0;
      setRecoveryRequired(uncertain);
      setMessage(uncertain ? 'A previous request has an uncertain outcome. Check the latest execution before continuing.' :
        result.status === 'empty' ? 'Ask about your invoice, connection or plans.' : 'Latest execution recovered.');
    }).catch(() => {
      if (active) setMessage('Could not recover the latest execution. Check again before continuing.');
    });
    return () => { active = false; };
  }, [available, conversation]);

  useEffect(() => {
    if (!current?.execution_id || !['running', 'resuming', 'pending'].includes(current.status)) return;
    if (polls.current >= 30) return;
    let active = true;
    const timer = setTimeout(() => {
      polls.current++;
      request('/api/journey/status', { execution_id: current.execution_id! })
        .then(value => { if (active) setCurrent(execution(value)); })
        .catch(() => { if (active) setMessage('Status unavailable. Use Check latest execution.'); });
    }, 2000);
    return () => { active = false; clearTimeout(timer); };
  }, [current]);

  async function send() {
    if (!draft.trim() || busy || recoveryRequired) return;
    sessionStorage.setItem(`telecom-uncertain-${conversation}`, current?.execution_id ?? 'none');
    setBusy(true); setMessage('Connecting to your support team…');
    setHistory(items => [...items.slice(-18), { role: 'You', text: draft }]);
    const controller = new AbortController(); abort.current = controller;
    try {
      const response = await fetch('/api/journey/chat', { method: 'POST', credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ conversation_id: conversation, message: draft,
          ...(draftLocale ? { audio_locale: draftLocale } : {}) }),
        signal: AbortSignal.any([controller.signal, AbortSignal.timeout(150_000)]) });
      if (response.status === 401) window.dispatchEvent(new Event('telecom-session-expired'));
      if ([400, 413].includes(response.status)) {
        sessionStorage.removeItem(`telecom-uncertain-${conversation}`);
        setMessage('Request rejected. Shorten your message before sending again.');
        return;
      }
      if (!response.ok || !response.body) throw new Error('Support request was not accepted.');
      setDraft(''); setDraftLocale(null);
      const reader = response.body.getReader(); const decoder = new TextDecoder();
      let buffer = ''; let complete = false;
      while (true) {
        const chunk = await reader.read();
        if (chunk.done) break;
        buffer += decoder.decode(chunk.value, { stream: true });
        if (buffer.length > 50000) throw new Error('Response exceeds the demo limit.');
        let boundary: number;
        while ((boundary = buffer.indexOf('\n\n')) >= 0) {
          const block = buffer.slice(0, boundary); buffer = buffer.slice(boundary + 2);
          const kind = block.split('\n').find(line => line.startsWith('event: '))?.slice(7);
          const data = JSON.parse(block.split('\n').find(line => line.startsWith('data: '))?.slice(6) ?? '{}');
          if (kind === 'error') throw new Error(data.message);
          if (kind === 'progress') setMessage('Consulting your support team');
          if (kind === 'result') {
            const result = execution(data); setCurrent(result); polls.current = 0;
            sessionStorage.removeItem(`telecom-uncertain-${conversation}`);
            if (result.text) setHistory(items => [...items.slice(-18), { role: 'Support', text: result.text! }]);
            setMessage(result.status === 'suspended' ? 'Review the exact proposal below.' : 'Execution received.');
            complete = true;
          }
        }
      }
      if (!complete) throw new Error('Execution response was interrupted.');
    } catch {
      setRecoveryRequired(true);
      setMessage('Outcome not confirmed. Check the latest execution before sending again.');
    } finally { setBusy(false); abort.current = null; }
  }

  async function latest() {
    setBusy(true);
    try {
      const result = execution(await request('/api/journey/latest', { conversation_id: conversation }));
      setCurrent(result); polls.current = 0;
      // An empty lookup does not prove that an in-flight invocation was rejected.
      const priorExecution = sessionStorage.getItem(`telecom-uncertain-${conversation}`);
      const unresolved = priorExecution !== null &&
        (result.status === 'empty' || result.execution_id === priorExecution);
      setRecoveryRequired(unresolved);
      if (!unresolved) sessionStorage.removeItem(`telecom-uncertain-${conversation}`);
      setMessage(unresolved ? 'The uncertain request has not been recovered. Check again before continuing.' :
        result.status === 'empty' ? 'No execution found for this conversation.' : 'Latest execution recovered.');
    }
    catch { setMessage('Could not recover the latest execution. Do not repeat an uncertain action.'); }
    finally { setBusy(false); }
  }

  function newConversation() {
    if (busy || recording || recoveryRequired || waiting) return;
    const id = crypto.randomUUID();
    sessionStorage.setItem(`telecom-conversation-${user.user_id}`, id);
    audio.current?.pause();
    setRecoveryRequired(true); setCurrent(null); setHistory([]); setDraft(''); setDraftLocale(null);
    setConversation(id);
  }

  async function review(decision: string) {
    if (!current?.execution_id || !current.action_digest || busy) return;
    setBusy(true);
    try {
      setCurrent(execution(await request('/api/journey/review', {
        execution_id: current.execution_id, action_digest: current.action_digest, decision,
      }))); polls.current = 0;
    } catch { setMessage('Review changed or could not be confirmed. Refresh the execution.'); }
    finally { setBusy(false); }
  }

  async function finishRecording(cancel = false) {
    const active = capture.current; capture.current = null; setRecording(false);
    if (!active) return;
    if (cancel) { await active.cancel(); setMessage('Recording discarded.'); return; }
    const capturedLocale = recordingLocale.current;
    setBusy(true);
    try {
      const pcm = await active.finish();
      const result = await request('/api/voice/transcribe', { pcm_base64: pcm, locale: capturedLocale }) as { text: string; locale: Locale };
      if (!mounted.current || !visible.current) return;
      if (result.locale !== capturedLocale || typeof result.text !== 'string') throw new Error('Invalid transcript');
      setDraft(result.text); setDraftLocale(capturedLocale); setMessage('Review the transcript, then choose Send.');
    } catch { setMessage('Speech could not be recognized. Try once more in a quiet room or use text.'); }
    finally { setBusy(false); }
  }

  async function record() {
    recordingLocale.current = locale;
    setBusy(true);
    try {
      const active = await startRecording(() => { void finishRecording(); });
      if (!mounted.current || !visible.current) { await active.cancel(); return; }
      capture.current = active;
      setRecording(true); setMessage('Recording. Maximum 15 seconds.');
    } catch { setMessage('Microphone unavailable or permission denied. You can continue with text.'); }
    finally { setBusy(false); }
  }

  async function speak() {
    if (!current?.execution_id) return;
    const generation = ++playbackGeneration.current;
    setBusy(true);
    try {
      const response = await fetch('/api/voice/speak', { method: 'POST', credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ execution_id: current.execution_id }), signal: AbortSignal.timeout(120_000) });
      if (response.status === 401) window.dispatchEvent(new Event('telecom-session-expired'));
      if (!response.ok) throw new Error();
      const blob = await response.blob();
      if (!mounted.current || !visible.current || generation !== playbackGeneration.current) return;
      audio.current?.pause(); if (audioUrl.current) URL.revokeObjectURL(audioUrl.current);
      audioUrl.current = URL.createObjectURL(blob);
      audio.current = new Audio(audioUrl.current); await audio.current.play();
    } catch { setMessage('Playback unavailable. The verified text remains visible.'); }
    finally { setBusy(false); }
  }

  const waiting = recoveryRequired || current && ['suspended', 'running', 'resuming', 'pending'].includes(current.status);
  return <section className="journey panel" aria-label={t("Support workspace")}>
    <p className="eyebrow">{t("YOUR SUPPORT TEAM")}</p><h2>{t("How can we help?")}</h2>
    <p className="muted">{t("Financial \u00b7 Technical \u00b7 Sales")}</p>
    <div className="conversation" aria-live="polite">
      {history.map((item, index) => <article key={index}><strong>{t(item.role)}</strong><p>{item.text}</p></article>)}
    </div>
    <p role="status" className="muted">{t(message)}</p>
    {current?.status === 'suspended' && current.action && <div className="proposal">
      <h3>{t("Confirm this simulation")}</h3>
      <p>{t("Plan:")} <strong>{current.action.plan_id}</strong></p>
      <p>{t("Monthly price: USD")} {new Intl.NumberFormat(current.locale ?? 'en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(current.action.monthly_minor / 100)}</p>
      <p>{t("No live plan or charge will change. Only the original requester can approve.")}</p>
      <div className="actions"><button disabled={busy} onClick={() => { void review('approve'); }}>{t("Approve simulation")}</button>
        <button className="secondary" disabled={busy} onClick={() => { void review('reject'); }}>{t("Reject")}</button></div>
    </div>}
    {current && <div className="execution"><p>{t("Execution:")} {t(current.status)}</p>
      {current.specialists && <p>{t("Consulted:")} {current.specialists.map(t).join(', ')}</p>}
      {current.text && <><p className="response-language">{t('Response language:')} {t(languageNames[current.locale ?? 'en-US'])}</p>
        <p className="result" lang={current.locale}>{current.text}</p></>}
      {voice && current.status === 'completed' && <div className="actions">
        <button disabled={busy} onClick={() => { void speak(); }}>{t("Play response")}</button>
        <button className="secondary" onClick={() => { playbackGeneration.current++; audio.current?.pause(); }}>{t("Stop playback")}</button>
      </div>}
    </div>}
    {(recording || draftLocale) && <p className="audio-language">{t("Audio language:")} {t(languageNames[recording ? recordingLocale.current : draftLocale!])}</p>}
    <label>{t("Your message")}<textarea value={draft} maxLength={messageLimit} rows={3}
      onChange={event => { setDraft(event.target.value); if (!event.target.value) setDraftLocale(null); }} disabled={!available || busy || !!waiting || recording}
      placeholder={t("Read invoice demo-1 and check my slow connection.")} /></label>
    <div className="actions">
      <button disabled={!available || busy || !!waiting || recording || !draft.trim()} onClick={() => { void send(); }}>{t("Send")}</button>
      {voice && !recording && <button className="secondary" disabled={!available || busy || !!waiting}
        onClick={() => { void record(); }}>{t("Record voice")}</button>}
      {recording && <><button onClick={() => { void finishRecording(); }}>{t("Finish recording")}</button>
        <button className="secondary" onClick={() => { void finishRecording(true); }}>{t("Cancel recording")}</button></>}
      {busy && abort.current && <button className="secondary" onClick={() => abort.current?.abort()}>{t("Stop waiting")}</button>}
      <button className="secondary" disabled={!available || busy || recording} onClick={() => { void latest(); }}>{t("Check latest execution")}</button>
      <button className="secondary" disabled={!available || busy || recording || !!waiting}
        onClick={newConversation}>{t("New conversation")}</button>
    </div>
    {voice && <p className="hint">{t("The spoken response is AI-generated.")}</p>}
    <p className="hint">{t("Leaving Support discards microphone recording and stops playback. Your conversation remains active.")}</p>
    <p className="hint">{t("Stopping playback or waiting does not cancel accepted remote work. No automatic resubmission.")}</p>
    <p className="hint">{t("New conversations may recall selected earlier facts. Full chat history is not restored, and new memories may take time to become available.")}</p>
  </section>;
}
