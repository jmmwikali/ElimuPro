import { useState } from 'react';
import { MEDIA, Photo } from './Media';

const P = {
  user: 'M12 12a4 4 0 100-8 4 4 0 000 8zM4 20c0-4 4-6 8-6s8 2 8 6', book: 'M4 5h6a2 2 0 012 2v12a2 2 0 00-2-2H4zM20 5h-6a2 2 0 00-2 2v12a2 2 0 012-2h6z',
  card: 'M3 6h18v12H3zM3 10h18', chat: 'M21 12a8 8 0 01-11.5 7.2L4 20l1-4.5A8 8 0 1121 12z', bell: 'M6 16v-5a6 6 0 1112 0v5l2 2H4zM10 20a2 2 0 004 0',
  chart: 'M4 20V4M4 20h16M9 16v-5M14 16V8M19 16V7', db: 'M5 6c0-1.7 3.1-3 7-3s7 1.3 7 3-3.1 3-7 3-7-1.3-7-3zM5 6v12c0 1.7 3.1 3 7 3s7-1.3 7-3V6M5 12c0 1.7 3.1 3 7 3s7-1.3 7-3',
  trend: 'M3 17l6-6 4 4 8-8M15 7h6v6', clock: 'M12 21a9 9 0 100-18 9 9 0 000 18zM12 7v5l3 2', go: 'M9 6l6 6-6 6',
};
const Ic = ({ n }) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={P[n]} /></svg>;

const FEATURE_LOGOS = {
  careergps: ['careergps-logo.png', 'CareerGPS by ElimuPro'],
};
const FEATURES = [
  ['user', 'Admissions & student records', 'From first application to enrolment, keep every learner record complete and easy to find.'],
  ['book', 'Academics', 'Manage classes, streams, subjects, terms and results in one place.'],
  ['card', 'Fee management', 'Record school payments and keep balances and history up to date.'],
  ['chat', 'Parent communication', 'Share school updates and announcements with parents. Parent access is coming soon.'],
  ['bell', 'Results at a glance', 'See how classes and learners are performing, term by term.'],
  ['chart', 'Reports that stay ready', 'Give leadership accurate dashboards and reports without chasing spreadsheets.'],
  ['careergps', 'CareerGPS career guidance', 'Help every learner find their path. CareerGPS guides career and subject pathway choices that match their strengths and interests.'],
];
const STEPS = [
  ['Discover', "We map your school's people, processes and goals.", 'chat', 'A plan shaped around your school', 'A focused discovery session gives our team the context to recommend the right modules, migration plan and rollout timeline.', '60-minute discovery call'],
  ['Prepare', 'We organise your data, configure roles and train your team.', 'db', 'Your system, ready for real work', 'We securely prepare learner records, academic structures, fee balances and user access, then train each team in the work they do every day.', '2-4 week guided setup'],
  ['Go live', 'You launch with guided support and clear success checks.', 'trend', 'Momentum from your very first day', 'Launch week includes hands-on support, progress checks and practical help so staff can build confidence quickly.', 'Ongoing local support'],
];

export function Features() {
  return (
    <section className="lp-sec" id="features">
      <div className="lp-fhead">
        <div><p className="lp-eyebrow">Complete school operations</p><h2>Everything works better together</h2></div>
        <Photo item={MEDIA.features} />
      </div>
      <div className="lp-fgrid">
        {FEATURES.map(([i, t, d]) => {
          const logo = FEATURE_LOGOS[i];
          return (
            <div key={t} className={logo ? `lp-feature-${i}` : ''}>
              {logo ? <img className="lp-feature-logo" src={`${process.env.PUBLIC_URL || ''}/${logo[0]}`} alt={logo[1]} /> : <span className="lp-fic"><Ic n={i} /></span>}
              <div><h3>{t}</h3><p>{d}</p></div>
            </div>
          );
        })}
      </div>
    </section>
  );
}

export function Rollout() {
  const [s, setS] = useState(0);
  const [, , icon, head, text, meta] = STEPS[s];
  return (
    <section className="lp-sec white" id="how">
      <p className="lp-eyebrow center">A calm transition</p>
      <h2 className="center">From first call to confident rollout</h2>
      <div className="lp-roll">
        <div className="lp-steps">
          {STEPS.map(([t, d], i) => (
            <button key={t} type="button" className={i === s ? 'on' : ''} aria-pressed={i === s} onClick={() => setS(i)}>
              <b>0{i + 1}</b><span><strong>{t}</strong><small>{d}</small></span><Ic n="go" />
            </button>
          ))}
        </div>
        <div className="lp-rpanel" key={s} aria-live="polite">
          <Photo item={MEDIA.rollout[s]} className="lp-rphoto" />
          <span className="lp-ricon"><Ic n={icon} /></span>
          <p className="lp-eyebrow">Step {s + 1}</p>
          <h3>{head}</h3><p>{text}</p>
          <p className="lp-meta"><Ic n="clock" />{meta}</p>
        </div>
      </div>
    </section>
  );
}