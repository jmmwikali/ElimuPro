import { Link } from 'react-router-dom';

const MODULES = [
  {
    to: '/student/zeroq',
    title: 'ZeroQ',
    desc: 'Queue, admission progress and your digital pass. Required before other features.',
    color: '#5b21b6',
  },
  {
    to: '/student/careergps',
    title: 'CareerGPS',
    desc: 'Explore careers, courses and guidance matched to your interests.',
    color: '#1d4ed8',
  },
];

export default function ModuleCards({ base = '/student' }) {
  const items = base === '/parent'
    ? [
        { to: '/parent/zeroq', title: 'ZeroQ', desc: 'View your children’s ZeroQ status and passes.', color: '#5b21b6' },
        { to: '/parent/careergps', title: 'CareerGPS', desc: 'See career interests for your children.', color: '#1d4ed8' },
      ]
    : MODULES;

  return (
    <section>
      <h2>Modules</h2>
      <div className="cards">
        {items.map((m) => (
          <Link key={m.to} to={m.to} className="card" style={{ textDecoration: 'none', color: 'inherit', borderTop: `4px solid ${m.color}` }}>
            <div className="label" style={{ color: m.color }}>{m.title}</div>
            <p className="small" style={{ margin: '.5rem 0 0' }}>{m.desc}</p>
            <div className="small" style={{ marginTop: '.75rem', color: m.color, fontWeight: 600 }}>Open →</div>
          </Link>
        ))}
      </div>
    </section>
  );
}
