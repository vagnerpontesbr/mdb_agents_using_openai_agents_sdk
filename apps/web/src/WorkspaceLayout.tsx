import { useEffect, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import type { Principal } from './api';
import Journey from './Journey';
import Knowledge from './Knowledge';
import Profile, { parseProfile } from './Profile';
import type { ProfileData } from './Profile';
import { request } from './api';
import type { Locale } from './catalogs';
import { useI18n } from './i18n';

const adminPages = ['overview', 'users', 'capabilities', 'integrations', 'tokenomics'];
const routeNow = () => location.hash.slice(1) || '/support';

export default function WorkspaceLayout({ user, account, busy, logout, feedback }: {
  user: Principal; account: ReactNode; feedback: ReactNode; busy: boolean; logout: () => void;
}) {
  const { t, locale, setLocale, setTimezone } = useI18n();
  const [profileData, setProfileData] = useState<ProfileData | null>(null);
  const [savingLocale, setSavingLocale] = useState(false);
  const [localeError, setLocaleError] = useState(false);
  const [profileError, setProfileError] = useState(false);
  const [reload, setReload] = useState(0);
  useEffect(() => {
    let active = true;
    request('/api/profile').then(value => {
      const data = parseProfile(value);
      if (data.user_id !== user.user_id) throw new Error('Profile identity mismatch');
      if (active) { setProfileData(data); setLocale(data.locale); setTimezone(data.timezone); setProfileError(false); }
    }).catch(() => { if (active) setProfileError(true); });
    return () => { active = false; };
  }, [user.user_id, reload, setLocale, setTimezone]);
  const [route, setRoute] = useState(routeNow);
  const [navigation, setNavigation] = useState(false);
  const [profile, setProfile] = useState(false);
  const profileButton = useRef<HTMLButtonElement>(null);
  const navigationButton = useRef<HTMLButtonElement>(null);
  const content = useRef<HTMLElement>(null);
  useEffect(() => {
    const change = () => {
      setRoute(routeNow()); setNavigation(false); setProfile(false);
      content.current?.focus();
    };
    window.addEventListener('hashchange', change);
    return () => window.removeEventListener('hashchange', change);
  }, []);
  const adminRoute = route.startsWith('/control-plane/');
  const adminPage = adminRoute ? route.slice('/control-plane/'.length) : '';
  const known = ['/support', '/knowledge', '/profile'].includes(route) || adminPages.includes(adminPage);
  function link(path: string, label: string) {
    return <a href={`#${path}`} aria-current={route === path ? 'page' : undefined}
      onClick={() => { setNavigation(false); setProfile(false); }}>{t(label)}</a>;
  }
  return <div className="workspace" onKeyDown={event => {
    if (event.key !== 'Escape') return;
    if (profile) { setProfile(false); profileButton.current?.focus(); }
    else if (navigation) { setNavigation(false); navigationButton.current?.focus(); }
  }}>
    <a className="skip-link" href="#workspace-content" onClick={event => {
      event.preventDefault(); content.current?.focus();
    }}>{t('Skip to content')}</a>
    <header className="workspace-header">
      <button className="nav-toggle" ref={navigationButton} aria-expanded={navigation}
        aria-controls="workspace-navigation" onClick={() => setNavigation(!navigation)}>{t('Navigation')}</button>
      <a className="brand" href="#/support">◒ Telecom<span> / {t('workspace')}</span></a>
      <div className="profile-disclosure">
        <button ref={profileButton} aria-expanded={profile} aria-controls="profile-links"
          onClick={() => setProfile(!profile)}>{t('Profile')} <span aria-hidden="true">▾</span></button>
        {profile && <div id="profile-links" className="profile-links">
          <strong>{profileData?.display_name || user.email}</strong><span className="role">{t(user.role)}</span>
          {link('/profile', 'My profile')}
          <label>{t('Language')}<select value={locale} disabled={!profileData || savingLocale} onChange={async event => {
            if (!profileData || savingLocale) return;
            const next = event.target.value as Locale;
            setSavingLocale(true); setLocaleError(false);
            try {
              const updated = parseProfile(await request('/api/profile', {
                display_name: profileData.display_name, timezone: profileData.timezone,
                locale: next, expected_revision: profileData.revision,
              }));
              setProfileData(updated); setLocale(updated.locale);
            } catch { setLocaleError(true); }
            finally { setSavingLocale(false); }
          }}><option value="en-US">English</option><option value="pt-BR">Português (Brasil)</option><option value="es-ES">Español</option></select></label>
          {localeError && <p role="alert">{t('Unable to save profile. Check the result before trying again.')}</p>}

          <button disabled={busy} onClick={logout}>{t('Sign out')}</button>
        </div>}
      </div>
    </header>
    <div className="workspace-body">
      <nav id="workspace-navigation" aria-label={t('Workspace')} className={navigation ? 'navigation open' : 'navigation'}>
        <p className="eyebrow">{t('WORKSPACE')}</p>
        {link('/support', 'Support')}{link('/knowledge', 'Knowledge')}
        {user.role === 'admin' && <><p className="eyebrow">{t('CONTROL PLANE')}</p>
          {adminPages.map(page => <div key={page}>{link(`/control-plane/${page}`, page[0].toUpperCase() + page.slice(1))}</div>)}
        </>}
      </nav>
      <main id="workspace-content" ref={content} tabIndex={-1} className="workspace-content">
        {feedback}
        <div hidden={route !== '/support'}><Journey user={user} active={route === '/support'} /></div>
        <div hidden={route !== '/knowledge'}><Knowledge user={user} /></div>
        {route === '/profile' && (profileData ? <Profile key={`${profileData.user_id}-${reload}`} data={profileData}
          saved={value => { setProfileData(value); setLocale(value.locale); setTimezone(value.timezone); }} reload={() => { setProfileData(null); setReload(value => value + 1); }} /> :
          <section className="panel"><h1>{t('My profile')}</h1><p role="status">{t(profileError ? 'Unable to load profile.' : 'Loading profile…')}</p>
            {profileError && <button onClick={() => setReload(value => value + 1)}>{t('Reload profile')}</button>}
          </section>)}
        {adminRoute && user.role !== 'admin' ? <section className="panel" role="alert"><h1>{t('Access denied')}</h1>
          <p>{t('This area requires an administrator.')}</p>{link('/support', 'Return to Support')}</section> :
          known && adminRoute && <section className="panel"><h1>{t(adminPage[0].toUpperCase() + adminPage.slice(1))}</h1>
            {adminPage === 'users' ? account : <p>{t('This view is coming soon.')}</p>}
          </section>}
        {!known && !(adminRoute && user.role !== 'admin') && <section className="panel"><h1>{t('Page not found')}</h1>
          {link('/support', 'Return to Support')}</section>}
      </main>
    </div>
  </div>;
}
