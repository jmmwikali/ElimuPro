import { useLayoutEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import Logo from './Logo';
import { BRAND } from '../config/brand';
import { HeroMedia } from './Media';
gsap.registerPlugin(ScrollTrigger);

// All figures are illustrative sample data.
const ROLES = [
  { id: 'Admin', desc: 'Manage the school', head: 'Everything starts with control.', sub: 'Run admissions, learners, classes, fees and results from one dashboard.',
    feats: ['Student management', 'Admissions', 'Classes & streams', 'Teachers & subjects', 'Fees management', 'Results & reports'],
    ui: { t: 'Overview', stats: [['1,284', 'Students'], ['76', 'Teachers'], ['82%', 'Fees paid']], bars: true, h: 'Recent activity', rows: [['Admission approved', 'Form 1'], ['Fee recorded', 'KES 12,500'], ['Results published', 'Form 3']] } },
  { id: 'Teachers', desc: 'Teach and record results', head: 'Everything you need to teach.', sub: 'See your classes, learner records and results without chasing paper registers.',
    feats: ['Assigned classes', 'Subjects', 'Student records', 'Marks & results'],
    ui: { t: 'My classes', stats: [['2', 'Classes'], ['80', 'Learners']], h: 'Classes', rows: [['Form 3A · Mathematics', '42 students'], ['Form 2B · Computer Studies', '38 students']], h2: 'Recent results', rows2: [['Mathematics · Term 2', 'Posted']] } },
  { id: 'Parents', desc: 'Stay connected', head: "Stay connected to your child's school.", sub: 'Fee information, results and school updates in one place. Parent access is coming soon.',
    feats: ['Student information', 'Fee information', 'Academic results', 'School updates'], phone: true,
    ui: { t: 'Jane Wanjiku', stats: [['KES 12,500', 'Fees paid'], ['A-', 'Mathematics']], h: 'School updates', rows: [['Term 3 opening date', 'New'], ['Results available', 'New']] } },
  { id: 'Students', desc: 'Follow your school life', head: 'Your school life, in one place.', sub: 'Your profile, subjects, results and announcements, available on any phone.',
    feats: ['Personal profile', 'Classes & subjects', 'Academic results', 'Announcements'],
    ui: { t: 'Good morning, Brian', stats: [['3', 'Subjects'], ['A', 'Computer Studies']], h: 'My classes', rows: [['Mathematics', 'A-'], ['Computer Studies', 'A'], ['English', 'B+']] } },
];
const BARS = [40, 55, 38, 62, 48, 75, 66, 92];
const FINAL = [{ x: 0, y: -125 }, { x: -175, y: 0 }, { x: 175, y: 0 }, { x: 0, y: 125 }];

function Mock({ u, phone }) {
  return (
    <div className={`lp-mock${phone ? ' phone' : ''}`}>
      <b>{u.t}</b><span className="lp-tag">Sample data</span>
      <div className="lp-stats">{u.stats.map(([v, l]) => <div key={l}><b>{v}</b><small>{l}</small></div>)}</div>
      {u.bars && <div className="lp-bars" aria-hidden="true">{BARS.map((h, i) => <i key={i} className={i === 7 ? 'on' : ''} style={{ height: `${h}%` }} />)}</div>}
      {[[u.h, u.rows], [u.h2, u.rows2]].map(([h, rows]) => rows && <div key={h}><h4>{h}</h4>{rows.map(([a, b]) => <p key={a}><span>{a}</span><em>{b}</em></p>)}</div>)}
    </div>
  );
}

export default function Walkthrough({ signup }) {
  const ref = useRef(null);
  useLayoutEffect(() => {
    const root = ref.current, q = gsap.utils.selector(root), mm = gsap.matchMedia();
    mm.add('(min-width: 900px) and (prefers-reduced-motion: no-preference)', () => {
      root.classList.add('anim');
      const W = () => window.innerWidth, cards = q('.lp-rc'), panels = q('.lp-panel'), dots = q('.lp-dot');
      const pos = (k, a) => { const d = k - a; return { x: 0, y: d * 92 + (d > 0 ? 44 : d < 0 ? -44 : 0), scale: d === 0 ? 1 : 0.82, opacity: d === 0 ? 1 : 0.5, z: d === 0 ? 60 : -50, zIndex: 10 - Math.abs(d) }; };
      gsap.set(cards, { opacity: 0, scale: 0.8, z: -80, transformPerspective: 1200 });
      gsap.set(q('.lp-pk-move'), { rotateY: -10, rotateX: 4 });
      gsap.set(q('.lp-ly-b'), { x: 14, y: 14, z: -30 }); gsap.set(q('.lp-ly-m'), { x: 7, y: 7, z: -14 });
      gsap.set(dots, { opacity: 0.35 });
      gsap.to(q('.lp-pk-in'), { y: -10, duration: 3.2, yoyo: true, repeat: -1, ease: 'sine.inOut' });
      const tl = gsap.timeline({ defaults: { ease: 'none' }, scrollTrigger: { trigger: root, start: 'top top', end: '+=500%', pin: true, scrub: 0.6, anticipatePin: 1, invalidateOnRefresh: true } });
      const right = () => W() * 0.64 - 160;
      tl.to(q('.lp-hero-txt'), { autoAlpha: 0, x: 80, duration: 1.2, ease: 'power2.inOut' }, 0.3)
        .to(q('.lp-hero-media'), { opacity: 0.45, duration: 1.4, ease: 'power2.inOut' }, 0.3)
        .to(q('.lp-pk-move'), { x: right, rotateY: -22, rotateX: 6, scale: 1.1, duration: 2, ease: 'power2.inOut' }, 0.4)
        .to(q('.lp-cards'), { x: right, duration: 2, ease: 'power2.inOut' }, 0.4)
        .to(q('.lp-ly-f'), { z: 140, y: -26, duration: 1.6, ease: 'power2.out' }, 1)
        .to(q('.lp-ly-m'), { z: 80, y: 10, duration: 1.6, ease: 'power2.out' }, 1)
        .to(q('.lp-ly-b'), { z: 0, y: 36, duration: 1.6, ease: 'power2.out' }, 1);
      cards.forEach((c, k) => tl.to(c, { ...pos(k, 0), duration: 1.2, ease: 'power3.out' }, 1.8 + k * 0.12));
      tl.to(q('.lp-pk-move'), { opacity: 0, duration: 1 }, 2.8);
      const go = (a, t) => {
        cards.forEach((c, k) => tl.to(c, { ...pos(k, a), duration: 1, ease: 'power2.inOut' }, t));
        if (a > 0) tl.to(panels[a - 1], { opacity: 0, y: -24, duration: 0.7, ease: 'power2.in' }, t).to(dots[a - 1], { opacity: 0.35, scale: 1, duration: 0.3 }, t);
        tl.fromTo(panels[a], { opacity: 0, y: 24 }, { opacity: 1, y: 0, duration: 0.9, ease: 'power2.out' }, t + 0.3).to(dots[a], { opacity: 1, scale: 1.12, duration: 0.3 }, t);
      };
      [3.2, 5, 6.8, 8.6].forEach((t, a) => go(a, a ? t : 3.2));
      tl.to(panels[3], { opacity: 0, y: -24, duration: 0.7, ease: 'power2.in' }, 10.4).to(dots, { opacity: 0, duration: 0.4 }, 10.4)
        .to(q('.lp-cards'), { x: () => W() * 0.4 - 160, duration: 1.2, ease: 'power2.inOut' }, 10.4)
        .to(q('.lp-hub'), { opacity: 1, scale: 1, duration: 0.8 }, 10.9)
        .to(q('.lp-final-msg'), { opacity: 1, y: 0, duration: 0.8 }, 11.1);
      cards.forEach((c, k) => tl.to(c, { ...FINAL[k], scale: 0.6, opacity: 1, z: 0, zIndex: 10, duration: 1.1, ease: 'power2.inOut' }, 10.4));
      tl.to({}, { duration: 0.6 }, 12);
      return () => root.classList.remove('anim');
    });
    return () => mm.revert();
  }, []);

  // "Explore the system": scroll to the point where the package has opened and the Admin walkthrough is showing.
  const explore = (e) => {
    e.preventDefault();
    const st = ScrollTrigger.getAll().find((t) => t.trigger === ref.current);
    if (st) window.scrollTo({ top: st.start + (st.end - st.start) * 0.34, behavior: 'smooth' });
    else ref.current.querySelector('.lp-panel')?.scrollIntoView({ behavior: 'smooth' });
  };

  return (
    <section className="lp-wt" ref={ref} id="roles" aria-label={`${BRAND.name} walkthrough`}>
      <HeroMedia />
      <div className="lp-hero-txt">
        <p className="lp-pill">Built for Kenyan schools</p>
        <h1>The smarter way to manage your school.</h1>
        <p className="lp-lead">Bring admissions, student records, academics, fees and communication into one connected platform.</p>
        <div className="lp-cta"><Link className="lp-btn gold" to={signup}>Get started</Link><a className="lp-btn ghost" href="#roles" onClick={explore}>Explore the system</a></div>
      </div>
      <div className="lp-pk">
        <div className="lp-pk-move"><div className="lp-pk-in">
          <div className="lp-ly lp-ly-b" /><div className="lp-ly lp-ly-m" />
          <div className="lp-ly lp-ly-f"><Logo /><h2>One system.<br />Every role.</h2><p>{BRAND.name} connects the people and processes that run a school.</p>
            <div className="lp-chips">{ROLES.map((r) => <span key={r.id}>{r.id}</span>)}</div></div>
        </div></div>
      </div>
      <div className="lp-cards" aria-hidden="true">
        {ROLES.map((r) => <div className="lp-rc" key={r.id}><span className="lp-ic" /><b>{r.id}</b><small>{r.desc}</small></div>)}
        <div className="lp-hub"><span className="lp-logo-sq"><svg viewBox="0 0 24 24"><path d="M12 4 2 9l10 5 8-4v6h2V9L12 4zM6 13v4c0 1.5 3 3 6 3s6-1.5 6-3v-4l-6 3-6-3z" fill="#fff" /></svg></span></div>
      </div>
      <div className="lp-panels">
        {ROLES.map((r) => (
          <article className="lp-panel" key={r.id}>
            <div className="lp-ptop"><small>{r.id}</small><h2>{r.head}</h2><p>{r.sub}</p></div>
            <div className="lp-pbody"><Mock u={r.ui} phone={r.phone} /><ul>{r.feats.map((f) => <li key={f}><i />{f}</li>)}</ul></div>
          </article>
        ))}
      </div>
      <p className="lp-final-msg">Four roles. One connected system.</p>
      <div className="lp-dots" aria-hidden="true">{ROLES.map((r) => <span className="lp-dot" key={r.id}><i />{r.id}</span>)}</div>
    </section>
  );
}