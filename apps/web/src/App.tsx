import { useEffect, useState } from 'react';
import type { SubmitEvent } from 'react';
import { ApiError, InterfaceError, principal, request } from './api';
import type { Principal, Role } from './api';
import WorkspaceLayout from './WorkspaceLayout';
import { useI18n } from './i18n';
import type { Locale } from './catalogs';

export default function App() {
  const { locale, setLocale, t } = useI18n();
  const [user, setUser] = useState<Principal | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [passwordChanged, setPasswordChanged] = useState(false);

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
    const changed = () => { setUser(null); setNotice(''); setError(''); setPasswordChanged(true); };
    window.addEventListener('telecom-session-expired', expired);
    window.addEventListener('telecom-password-changed', changed);
    return () => {
      window.removeEventListener('telecom-session-expired', expired);
      window.removeEventListener('telecom-password-changed', changed);
    };
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
      if (register) setNotice(result.email);
      else { setUser(result); setPasswordChanged(false); }
    } catch (reason) {
      setError(reason instanceof InterfaceError ? reason.key : 'Request failed.');
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
    logout={() => { void logout(); }} feedback={error && <p role="alert" className="feedback error">{t(error)}</p>} account={<>
      <h2>{t("Create an account")}</h2><p className="muted">{t("Give a team member access to this demo.")}</p>
      <form onSubmit={event => { void submit(event, true); }}>
        <Credentials register disabled={busy} />
        <label>{t("Role")}<select name="role" defaultValue="user" disabled={busy}>
          <option value="user">{t("User")}</option><option value="admin">{t("Administrator")}</option>
        </select></label>
        <button disabled={busy} type="submit">{t(busy ? 'Working…' : 'Create account')}</button>
      </form>
      {notice && <p role="status" className="feedback success">{notice && t('Account created for {email}.').replace('{email}', notice)}</p>}
    </>} />;

  return <div className="shell">
    <header><a className="brand" href="/" aria-label="Telecom workspace home">
      <span className="brand-mark" aria-hidden="true">◒</span> Telecom<span> / {t('workspace')}</span>
    </a><span className="badge">{t("Reference demo")}</span></header>
    <label>{t('Language')}<select value={locale} onChange={event => setLocale(event.target.value as Locale)}>
      <option value="en-US">English</option><option value="pt-BR">Português (Brasil)</option><option value="es-ES">Español</option>
    </select></label>
    <main>
      <section className="intro">
        <p className="eyebrow">{t("CONNECTED SERVICE")}</p>
        <h1>{t("A clear start.")}<br />{t("A connected experience.")}</h1>
        <p className="lede">{t("One workspace for your telecom support team.")}</p>
        <div className="scope-note"><span aria-hidden="true">01</span><div>
          <strong>{t("Your workspace starts here")}</strong>
          <p>{t("Sign in to access your account. Administrators can invite the team by creating user accounts.")}</p>
        </div></div>
        <p className="footnote">{t("Independent reference asset inspired by MongoDB. Uses synthetic demo data.")}</p>
      </section>
      <section className="panel" aria-busy={busy || loading}>
        {loading ? <p role="status">{t("Checking your session\u2026")}</p> : <>
            <p className="eyebrow">{t("YOUR WORKSPACE")}</p><h2>{t("Sign in")}</h2>
            <p className="muted">{t("Use the account provided by your administrator.")}</p>
            <form onSubmit={event => { void submit(event, false); }}>
              <Credentials register={false} disabled={busy} />
              <button disabled={busy} type="submit">{t(busy ? 'Signing in…' : 'Sign in')}</button>
            </form>
        </>}
        {passwordChanged && <p className="feedback success" role="status">{t('Password changed. Sign in with your new password.')}</p>}
        {error && <p className="feedback error" role="alert">{t(error)}</p>}
        {notice && <p className="feedback success" role="status">{notice && t('Account created for {email}.').replace('{email}', notice)}</p>}
      </section>
    </main>
    <footer>{t("Telecom reference asset")} <span>{t("Private demo workspace")}</span></footer>
  </div>;
}

function Credentials({ register, disabled }: { register: boolean; disabled: boolean }) {
  const { t } = useI18n();
  return <>
    <label>{t("Email")}<input name="email" type="email" autoComplete={register ? 'off' : 'username'}
      required maxLength={254} placeholder="you@example.com" disabled={disabled} /></label>
    <label>{t("Password")}<input name="password" type="password" required minLength={8} maxLength={128}
      autoComplete={register ? 'new-password' : 'current-password'} disabled={disabled} /></label>
    {register && <p className="hint">{t("Use 8\u2013128 characters. Share credentials through your private demo channel.")}</p>}
  </>;
}
