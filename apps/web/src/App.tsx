import { useEffect, useState } from 'react';
import type { SubmitEvent } from 'react';
import { ApiError, principal, request } from './api';
import type { Principal, Role } from './api';
import WorkspaceLayout from './WorkspaceLayout';

export default function App() {
  const [user, setUser] = useState<Principal | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  useEffect(() => {
    let active = true;
    request('/api/me').then(value => { if (active) setUser(principal(value)); })
      .catch((reason: unknown) => {
        if (active && !(reason instanceof ApiError && reason.status === 401)) {
          setError('Unable to check your session. Refresh to try again.');
        }
      }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    const expired = () => { setUser(null); setNotice(''); setError('Your session expired. Sign in again.'); };
    window.addEventListener('telecom-session-expired', expired);
    return () => window.removeEventListener('telecom-session-expired', expired);
  }, []);

  async function submit(event: SubmitEvent<HTMLFormElement>, register: boolean) {
    event.preventDefault();
    if (busy) return;
    const form = event.currentTarget;
    const fields = new FormData(form);
    const payload = {
      email: String(fields.get('email') ?? ''),
      password: String(fields.get('password') ?? ''),
      ...(register ? { role: String(fields.get('role') ?? 'user') as Role } : {}),
    };
    setBusy(true); setError(''); setNotice('');
    try {
      const result = principal(await request(register ? '/api/users' : '/api/login', payload));
      form.reset();
      if (register) setNotice(`Account created for ${result.email}.`);
      else setUser(result);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Request failed.');
      if (register && reason instanceof ApiError && reason.status === 401) setUser(null);
    } finally {
      // Passwords never enter persistent browser storage.
      const input = form.elements.namedItem('password');
      if (input instanceof HTMLInputElement) input.value = '';
      setBusy(false);
    }
  }

  async function logout() {
    setBusy(true); setError(''); setNotice('');
    try { await request('/api/logout', {}); setUser(null); }
    catch (reason) {
      if (reason instanceof ApiError && reason.status === 401) setUser(null);
      else setError('Sign-out could not be confirmed. Please try again.');
    } finally { setBusy(false); }
  }

  if (user) return <WorkspaceLayout key={user.user_id} user={user} busy={busy}
    logout={() => { void logout(); }} feedback={error && <p role="alert" className="feedback error">{error}</p>} account={<>
      <h2>Create an account</h2><p className="muted">Give a team member access to this demo.</p>
      <form onSubmit={event => { void submit(event, true); }}>
        <Credentials register disabled={busy} />
        <label>Role<select name="role" defaultValue="user" disabled={busy}>
          <option value="user">User</option><option value="admin">Administrator</option>
        </select></label>
        <button disabled={busy} type="submit">{busy ? 'Working…' : 'Create account'}</button>
      </form>
      {notice && <p role="status" className="feedback success">{notice}</p>}
    </>} />;

  return <div className="shell">
    <header><a className="brand" href="/" aria-label="Telecom workspace home">
      <span className="brand-mark" aria-hidden="true">◒</span> Telecom<span> / workspace</span>
    </a><span className="badge">Reference demo</span></header>
    <main>
      <section className="intro">
        <p className="eyebrow">CONNECTED SERVICE</p>
        <h1>A clear start.<br />A connected experience.</h1>
        <p className="lede">One workspace for your telecom support team.</p>
        <div className="scope-note"><span aria-hidden="true">01</span><div>
          <strong>Your workspace starts here</strong>
          <p>Sign in to access your account. Administrators can invite the team by creating user accounts.</p>
        </div></div>
        <p className="footnote">Independent reference asset inspired by MongoDB. Uses synthetic demo data.</p>
      </section>
      <section className="panel" aria-busy={busy || loading}>
        {loading ? <p role="status">Checking your session…</p> : <>
            <p className="eyebrow">YOUR WORKSPACE</p><h2>Sign in</h2>
            <p className="muted">Use the account provided by your administrator.</p>
            <form onSubmit={event => { void submit(event, false); }}>
              <Credentials register={false} disabled={busy} />
              <button disabled={busy} type="submit">{busy ? 'Signing in…' : 'Sign in'}</button>
            </form>
        </>}
        {error && <p className="feedback error" role="alert">{error}</p>}
        {notice && <p className="feedback success" role="status">{notice}</p>}
      </section>
    </main>
    <footer>Telecom reference asset <span>Private demo workspace</span></footer>
  </div>;
}

function Credentials({ register, disabled }: { register: boolean; disabled: boolean }) {
  return <>
    <label>Email<input name="email" type="email" autoComplete={register ? 'off' : 'username'}
      required maxLength={254} placeholder="you@example.com" disabled={disabled} /></label>
    <label>Password<input name="password" type="password" required minLength={8} maxLength={128}
      autoComplete={register ? 'new-password' : 'current-password'} disabled={disabled} /></label>
    {register && <p className="hint">Use 8–128 characters. Share credentials through your private demo channel.</p>}
  </>;
}
