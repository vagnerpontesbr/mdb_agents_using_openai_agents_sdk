import { useEffect, useRef, useState } from 'react';
import type { Principal } from './api';
import { request } from './api';
import { startRecording } from './recording';
import type { Recording } from './recording';

type Execution = {
  execution_id?: string; status: string; text?: string; outcome?: string;
  specialists?: string[]; action_digest?: string;
  action?: { plan_id: string; monthly_minor: number; proposal_id: string };
};

function execution(value: unknown): Execution {
  if (!value || typeof value !== 'object' || !('status' in value) || typeof value.status !== 'string') {
    throw new Error('Invalid execution response');
  }
  return value as Execution;
}

export default function Journey({ user }: { user: Principal }) {
  const [conversation, setConversation] = useState(() => {
    const key = `telecom-conversation-${user.user_id}`;
    const saved = sessionStorage.getItem(key);
    if (saved && /^[0-9a-f-]{36}$/.test(saved)) return saved;
    const id = crypto.randomUUID(); sessionStorage.setItem(key, id); return id;
  });
  const [available, setAvailable] = useState(false);
  const [voice, setVoice] = useState(false);
  const [draft, setDraft] = useState('');
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

  useEffect(() => {
    mounted.current = true;
    request('/api/capabilities').then(value => {
      const data = value as { journey: boolean; voice: boolean };
      if (!mounted.current) return;
      setAvailable(data.journey); setVoice(data.voice);
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
        body: JSON.stringify({ conversation_id: conversation, message: draft }),
        signal: AbortSignal.any([controller.signal, AbortSignal.timeout(150_000)]) });
      if (!response.ok || !response.body) throw new Error('Support request was not accepted.');
      setDraft('');
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
          if (kind === 'progress') setMessage(data.message);
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
    setRecoveryRequired(true); setCurrent(null); setHistory([]); setDraft('');
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
    setBusy(true);
    try {
      const pcm = await active.finish();
      const result = await request('/api/voice/transcribe', { pcm_base64: pcm }) as { text: string };
      setDraft(result.text); setMessage('Review the transcript, then choose Send.');
    } catch { setMessage('Speech could not be recognized. Try once more in a quiet room or use text.'); }
    finally { setBusy(false); }
  }

  async function record() {
    setBusy(true);
    try {
      const active = await startRecording(() => { void finishRecording(); });
      if (!mounted.current) { await active.cancel(); return; }
      capture.current = active;
      setRecording(true); setMessage('Recording — speak in English. Maximum 15 seconds.');
    } catch { setMessage('Microphone unavailable or permission denied. You can continue with text.'); }
    finally { setBusy(false); }
  }

  async function speak() {
    if (!current?.execution_id) return;
    setBusy(true);
    try {
      const response = await fetch('/api/voice/speak', { method: 'POST', credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ execution_id: current.execution_id }), signal: AbortSignal.timeout(120_000) });
      if (!response.ok) throw new Error();
      const blob = await response.blob();
      if (!mounted.current) return;
      audio.current?.pause(); if (audioUrl.current) URL.revokeObjectURL(audioUrl.current);
      audioUrl.current = URL.createObjectURL(blob);
      audio.current = new Audio(audioUrl.current); await audio.current.play();
    } catch { setMessage('Playback unavailable. The verified text remains visible.'); }
    finally { setBusy(false); }
  }

  const waiting = recoveryRequired || current && ['suspended', 'running', 'resuming', 'pending'].includes(current.status);
  return <section className="journey panel" aria-label="Support workspace">
    <p className="eyebrow">YOUR SUPPORT TEAM</p><h2>How can we help?</h2>
    <p className="muted">Financial · Technical · Sales</p>
    <div className="conversation" aria-live="polite">
      {history.map((item, index) => <article key={index}><strong>{item.role}</strong><p>{item.text}</p></article>)}
    </div>
    <p role="status" className="muted">{message}</p>
    {current?.status === 'suspended' && current.action && <div className="proposal">
      <h3>Confirm this simulation</h3>
      <p>Plan: <strong>{current.action.plan_id}</strong></p>
      <p>Monthly price: USD {(current.action.monthly_minor / 100).toFixed(2)}</p>
      <p>No live plan or charge will change. Only the original requester can approve.</p>
      <div className="actions"><button disabled={busy} onClick={() => { void review('approve'); }}>Approve simulation</button>
        <button className="secondary" disabled={busy} onClick={() => { void review('reject'); }}>Reject</button></div>
    </div>}
    {current && <div className="execution"><p>Execution: {current.status}</p>
      {current.specialists && <p>Consulted: {current.specialists.join(', ')}</p>}
      {current.text && <p className="result">{current.text}</p>}
      {voice && current.status === 'completed' && <div className="actions">
        <button disabled={busy} onClick={() => { void speak(); }}>Play response</button>
        <button className="secondary" onClick={() => audio.current?.pause()}>Stop playback</button>
      </div>}
    </div>}
    <label>Your message<textarea value={draft} maxLength={4000} rows={3}
      onChange={event => setDraft(event.target.value)} disabled={!available || busy || !!waiting || recording}
      placeholder="Read invoice demo-1 and check my slow connection." /></label>
    <div className="actions">
      <button disabled={!available || busy || !!waiting || recording || !draft.trim()} onClick={() => { void send(); }}>Send</button>
      {voice && !recording && <button className="secondary" disabled={!available || busy || !!waiting}
        onClick={() => { void record(); }}>Record voice</button>}
      {recording && <><button onClick={() => { void finishRecording(); }}>Finish recording</button>
        <button className="secondary" onClick={() => { void finishRecording(true); }}>Cancel recording</button></>}
      {busy && abort.current && <button className="secondary" onClick={() => abort.current?.abort()}>Stop waiting</button>}
      <button className="secondary" disabled={!available || busy || recording} onClick={() => { void latest(); }}>Check latest execution</button>
      <button className="secondary" disabled={!available || busy || recording || !!waiting}
        onClick={newConversation}>New conversation</button>
    </div>
    <p className="hint">Stopping playback or waiting does not cancel accepted remote work. No automatic resubmission.</p>
    <p className="hint">New conversations may recall selected earlier facts. Full chat history is not restored, and new memories may take time to become available.</p>
  </section>;
}
