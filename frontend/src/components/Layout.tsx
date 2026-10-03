import { Link, NavLink, Outlet } from 'react-router-dom';

export function Layout() {
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
          Mock provider · no key needed
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
