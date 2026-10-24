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
        <div className="lp-actions"><Link className="lp-login" to={LOGIN}>Login</Link><Link className="lp-btn gold" to={SIGNUP}>Get started</Link></div>
      </nav>
      <main id="top"><Walkthrough signup={SIGNUP} /><Features /><Rollout /></main>
      <footer className="lp-footer">
        <div><span className="lp-logo"><Logo light /></span><p>{BRAND.tagline}</p></div>
        <div><h4>Platform</h4><p>Admissions</p><p>Students</p><p>Academics</p><p>Fees</p><p>Results</p><p>Reports</p></div>
        <div><h4>Access</h4><p><Link to={LOGIN}>School admin</Link></p><p><Link to={LOGIN}>Teacher</Link></p><p><Link to={SIGNUP}>Student</Link></p><p>Parent</p></div>
        <div><h4>Company</h4><p>About</p><p>Contact</p><p>Privacy</p><p>Terms</p></div>
      </footer>
    </div>
  );
}