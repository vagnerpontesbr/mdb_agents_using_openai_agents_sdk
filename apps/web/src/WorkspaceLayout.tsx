import { useEffect, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import type { Principal } from './api';
import Journey from './Journey';
import Knowledge from './Knowledge';

const adminPages = ['overview', 'users', 'capabilities', 'integrations', 'tokenomics'];
const routeNow = () => location.hash.slice(1) || '/support';

export default function WorkspaceLayout({ user, account, busy, logout, feedback }: {
  user: Principal; account: ReactNode; feedback: ReactNode; busy: boolean; logout: () => void;
}) {
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
      onClick={() => { setNavigation(false); setProfile(false); }}>{label}</a>;
  }
  return <div className="workspace" onKeyDown={event => {
    if (event.key !== 'Escape') return;
    if (profile) { setProfile(false); profileButton.current?.focus(); }
    else if (navigation) { setNavigation(false); navigationButton.current?.focus(); }
  }}>
    <a className="skip-link" href="#workspace-content" onClick={event => {
      event.preventDefault(); content.current?.focus();
    }}>Skip to content</a>
    <header className="workspace-header">
      <button className="nav-toggle" ref={navigationButton} aria-expanded={navigation}
        aria-controls="workspace-navigation" onClick={() => setNavigation(!navigation)}>Navigation</button>
      <a className="brand" href="#/support">◒ Telecom<span> / workspace</span></a>
      <div className="profile-disclosure">
        <button ref={profileButton} aria-expanded={profile} aria-controls="profile-links"
          onClick={() => setProfile(!profile)}>Profile <span aria-hidden="true">▾</span></button>
        {profile && <div id="profile-links" className="profile-links">
          <strong>{user.email}</strong><span className="role">{user.role}</span>
          {link('/profile', 'My profile')}
          <button disabled={busy} onClick={logout}>Sign out</button>
        </div>}
      </div>
    </header>
    <div className="workspace-body">
      <nav id="workspace-navigation" aria-label="Workspace" className={navigation ? 'navigation open' : 'navigation'}>
        <p className="eyebrow">WORKSPACE</p>
        {link('/support', 'Support')}{link('/knowledge', 'Knowledge')}
        {user.role === 'admin' && <><p className="eyebrow">CONTROL PLANE</p>
          {adminPages.map(page => <div key={page}>{link(`/control-plane/${page}`, page[0].toUpperCase() + page.slice(1))}</div>)}
        </>}
      </nav>
      <main id="workspace-content" ref={content} tabIndex={-1} className="workspace-content">
        {feedback}
        <div hidden={route !== '/support'}><Journey user={user} active={route === '/support'} /></div>
        <div hidden={route !== '/knowledge'}><Knowledge user={user} /></div>
        {route === '/profile' && <section className="panel"><h1>My profile</h1>
          <p>Profile preferences, photo and password editing are planned for the next profile phase.</p>
          <div className="account"><strong>{user.email}</strong><span className="role">{user.role}</span></div>
          <button disabled={busy} onClick={logout}>Sign out</button>
        </section>}
        {adminRoute && user.role !== 'admin' ? <section className="panel" role="alert"><h1>Access denied</h1>
          <p>This area requires an administrator.</p>{link('/support', 'Return to Support')}</section> :
          known && adminRoute && <section className="panel"><h1>{adminPage[0].toUpperCase() + adminPage.slice(1)}</h1>
            {adminPage === 'users' ? account : <p>This view is coming soon.</p>}
          </section>}
        {!known && !(adminRoute && user.role !== 'admin') && <section className="panel"><h1>Page not found</h1>
          {link('/support', 'Return to Support')}</section>}
      </main>
    </div>
  </div>;
}
