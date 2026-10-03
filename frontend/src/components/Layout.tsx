import { Link, NavLink, Outlet } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { api } from '../lib/api';

export function Layout() {
  const [provider, setProvider] = useState('Connecting…');
  useEffect(() => {
    const controller = new AbortController();
    api
      .health(controller.signal)
      .then((data) =>
        setProvider(data.provider === 'mock' ? 'Mock provider · no key needed' : 'Gemini provider'),
      )
      .catch(() => {
        if (!controller.signal.aborted) setProvider('Backend offline');
      });
    return () => controller.abort();
  }, []);
  return (
    <>
      <header className="app-header">
        <Link to="/" className="brand" aria-label="Extraction Workbench home">
          <span className="brand-mark" aria-hidden="true">
            ▤
          </span>
          <span>
            Extraction<span className="brand-light"> Workbench</span>
          </span>
        </Link>
        <nav aria-label="Main navigation">
          <NavLink to="/" end>
            Ticket inbox
          </NavLink>
        </nav>
        <span className="provider-tag">
          <span className="status-dot" />
          {provider}
        </span>
      </header>
      <main className="app-main">
        <Outlet />
      </main>
      <footer className="app-footer">
        Oraczen assignment · Human review keeps the final decision with you.
      </footer>
    </>
  );
}
