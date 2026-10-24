import { useState } from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import Icon from '../components/Icon';
import BrandLockup from '../components/BrandLockup';
import { BRAND } from '../config/brand';
import { initials } from '../utils/format';

/* One responsive shell, two navigation sets. Phones: bottom tab bar (student) or slide-in drawer (admin).
   Tablets/laptops: fixed sidebar. */
export default function AppShell({ nav, bottom, brandLabel }) {
  const { user, logout } = useAuth();
  const [open, setOpen] = useState(false);
  const navigate = useNavigate();
  const signOut = () => { logout(); navigate('/login'); };
  const plain = { background: 'none', border: 0, width: '100%', font: 'inherit', cursor: 'pointer' };

  const links = () => nav.map((n) => (
    <NavLink key={n.to} to={n.to} end={n.end} className={({ isActive }) => `navlink ${isActive ? 'active' : ''}`} onClick={() => setOpen(false)}>
      <Icon name={n.icon} /> {n.label}
    </NavLink>
  ));

  return (
    <div className="shell has-side">
      <aside className="sidenav" aria-label="Main navigation">
        <div className="brand" style={{ marginBottom: '1.25rem', color: "#fff" }}><BrandLockup /></div>
        {links()}
        <button className="navlink" style={{ ...plain, marginTop: '1rem' }} onClick={signOut}><Icon name="logout" /> Sign out</button>
      </aside>
      <div className="main-col">
        <header className="topbar">
          {!bottom && <button className="icon-btn menu" aria-label="Open menu" onClick={() => setOpen(true)}><Icon name="menu" /></button>}
          <div className="school">{user?.school?.name || brandLabel || BRAND.name}</div>
          <div className="avatar" style={{ width: 36, height: 36, fontSize: '.85rem' }} title={user?.full_name}>{initials(user?.full_name)}</div>
        </header>
        <main className="content"><Outlet /></main>
      </div>
      {bottom && (
        <nav className="bottomnav" aria-label="Main navigation">
          {bottom.map((n) => (
            <NavLink key={n.to} to={n.to} end={n.end} className={({ isActive }) => (isActive ? 'active' : '')}><Icon name={n.icon} />{n.label}</NavLink>
          ))}
        </nav>
      )}
      {open && (
        <>
          <div className="drawer-bg" onClick={() => setOpen(false)} />
          <aside className="drawer" aria-label="Menu">
            <div className="brand" style={{ marginBottom: '1rem' }}><BrandLockup /></div>
            {links()}
            <button className="navlink" style={plain} onClick={signOut}><Icon name="logout" /> Sign out</button>
          </aside>
        </>
      )}
    </div>
  );
}
