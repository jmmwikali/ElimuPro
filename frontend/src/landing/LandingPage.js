import { Link } from 'react-router-dom';
import Logo from './Logo';
import { BRAND } from '../config/brand';
import Walkthrough from './Walkthrough';
import { Features, Rollout } from './Sections';
import './landing.css';

const LOGIN = '/login';   // existing route
const SIGNUP = '/signup'; // existing route

export default function LandingPage() {
  return (
    <div className="lp">
      <nav className="lp-nav" aria-label="Main">
        <a href="#top" aria-label={`${BRAND.name} home`}><Logo /></a>
        <div className="lp-links">
          {/* Anchors below #roles point to sections that will be built from the next screenshots */}
          <a href="#features">Features</a><a href="#roles">Roles</a><a href="#how">How it works</a>
        </div>
        <div className="lp-actions">
          <Link className="lp-icon-btn" to={LOGIN} aria-label="Login" title="Login">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"/><polyline points="10 17 15 12 10 7"/><line x1="15" y1="12" x2="3" y2="12"/></svg>
          </Link>
          <Link className="lp-icon-btn gold" to={SIGNUP} aria-label="Create account" title="Create account">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="8.5" cy="7" r="4"/><line x1="20" y1="8" x2="20" y2="14"/><line x1="23" y1="11" x2="17" y2="11"/></svg>
          </Link>
        </div>
      </nav>
      <main id="top"><Walkthrough signup={SIGNUP} /><Features /><Rollout /></main>
      <footer className="lp-footer">
        <div><span className="lp-logo"><Logo light /></span><p>{BRAND.tagline}</p></div>
        <div><h4>Platform</h4><p>Admissions</p><p>Students</p><p>Academics</p><p>Fees</p><p>Results</p><p>Reports</p></div>
        <div><h4>Access</h4><p><Link to={LOGIN}>School admin</Link></p><p><Link to={LOGIN}>Teacher</Link></p><p><Link to={SIGNUP}>Student</Link></p><p>Parent</p></div>
        <div><h4>Company</h4><p>Rose Seko Foundations</p><p>About</p><p>Contact</p><p>Privacy</p><p>Terms</p></div>
      </footer>
    </div>
  );
  }
