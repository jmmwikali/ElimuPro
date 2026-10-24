import { useEffect, useRef, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import Login from './Login';
import Signup from './Signup';
import { MEDIA } from '../landing/Media';
import BrandLockup from '../components/BrandLockup';
import { BRAND } from '../config/brand';
import './authbook.css';

// One persistent "open book".
//   Login spread : [ welcome back | login form ]
//   Signup spread: [ signup form  | welcome to ElimuNova ]
// The login page is the front of a leaf hinged on the spine; its back is the signup page. Turning the leaf is a
// CSS transition + animation driven by the current route, so routing and auth logic are untouched.
// Below the book breakpoint (see authbook.css) the same markup renders as a single page with a simple crossfade.
const TURN_MS = 1100; // keep in sync with --dur in authbook.css
const WAITING = ['Results', 'Timetable', 'Fees', 'Announcements'];
const SIGNUP_STEPS = ['Create your account', 'Choose your school', 'Complete your application'];

const Arrow = ({ dir }) => (
  <svg viewBox="0 0 24 24" aria-hidden="true"><path d={dir === 'next' ? 'M5 12h14M13 6l6 6-6 6' : 'M19 12H5M11 6l-6 6 6 6'} /></svg>
);

// The two welcome pages carry different messages: "back" (login spread, left) and "new" (signup spread, right).
function Welcome({ side, active, mode }) {
  const isBack = mode === 'back';
  return (
    <aside className={`ab-base ab-${side}${active ? ' active' : ''}`} aria-label={isBack ? `Welcome back to ${BRAND.name}` : `Welcome to ${BRAND.name}`}>
      <div className="ab-scroll ab-welcome">
        <Link to="/" className="brand"><BrandLockup /></Link>
        {isBack ? (
          <div className="ab-wbody">
            <span className="ab-pill">Welcome back</span>
            <h2>Pick up right where you left off.</h2>
            <p>Your school workspace is just as you left it. Log in and carry on.</p>
            <img className="ab-photo" src={MEDIA.hero.poster} alt="" loading="lazy" decoding="async" onError={(e) => { e.currentTarget.style.display = 'none'; }} />
            <p className="ab-label">Waiting for you</p>
            <div className="ab-chips">{WAITING.map((r) => <span key={r}>{r}</span>)}</div>
          </div>
        ) : (
          <div className="ab-wbody">
            <span className="ab-pill is-new">Welcome to {BRAND.name}</span>
            <h2>Start something new.</h2>
            <p>Set up your account and begin your admission in one place.</p>
            <ol className="ab-steps">{SIGNUP_STEPS.map((s) => <li key={s}>{s}</li>)}</ol>
          </div>
        )}
        <Link className="ab-turn" to={isBack ? '/signup' : '/login'}>
          {!isBack && <Arrow dir="back" />}
          <span><span className="ab-turn-q">{isBack ? 'New here?' : 'Already have an account?'}</span> {isBack ? 'Create an account' : 'Log in'}</span>
          {isBack && <Arrow dir="next" />}
        </Link>
      </div>
    </aside>
  );
}

// Compact welcome shown on the single-page (phone) layout only; hidden when the book is open.
const MobileIntro = ({ mode }) => (
  <div className="ab-mintro">
    {mode === 'back'
      ? <><span className="ab-pill">Welcome back</span><p>Pick up right where you left off.</p></>
      : <><span className="ab-pill is-new">Welcome to {BRAND.name}</span><p>Start something new. Set up your account in two steps.</p></>}
  </div>
);

export default function AuthBook() {
  const isSignup = useLocation().pathname.startsWith('/signup');
  const [turning, setTurning] = useState(null); // 'fwd' (login -> signup) | 'back' | null
  const prev = useRef(isSignup);
  const book = useRef(null);
  const signupSeen = useRef(isSignup);
  if (isSignup) signupSeen.current = true; // mount Signup (and its school fetch) only once it is first needed

  useEffect(() => {
    if (prev.current === isSignup) return undefined;
    prev.current = isSignup;
    setTurning(isSignup ? 'fwd' : 'back');
    // move focus to the page that just became current so keyboard / screen-reader users land on it
    const h = book.current?.querySelector(isSignup ? '.ab-back h1' : '.ab-front h1');
    if (h) { h.setAttribute('tabindex', '-1'); h.focus({ preventScroll: true }); }
    const t = setTimeout(() => setTurning(null), TURN_MS + 150);
    return () => clearTimeout(t);
  }, [isSignup]);

  return (
    <div className="ab-stage">
      <main className="ab-book" ref={book} data-spread={isSignup ? 'signup' : 'login'} data-turning={turning ? 'true' : undefined} data-dir={turning || undefined} aria-busy={!!turning}>
        <div className="ab-cover" aria-hidden="true" />
        <Welcome side="l" active={!isSignup} mode="back" />
        <div className="ab-leaf">
          <section className={`ab-face ab-front${!isSignup ? ' active' : ''}`} aria-label="Log in">
            <div className="ab-scroll">
              <Link to="/" className="brand ab-mbrand"><BrandLockup /></Link>
              <MobileIntro mode="back" />
              <div className="ab-inner"><Login /></div>
            </div>
          </section>
          <section className={`ab-face ab-back${isSignup ? ' active' : ''}`} aria-label="Sign up">
            <div className="ab-scroll">
              <Link to="/" className="brand ab-mbrand"><BrandLockup /></Link>
              <MobileIntro mode="new" />
              <div className="ab-inner">{signupSeen.current && <Signup />}</div>
            </div>
          </section>
        </div>
        <Welcome side="r" active={isSignup} mode="new" />
        <div className="ab-spine" aria-hidden="true" />
      </main>
    </div>
  );
}