import { Link } from 'react-router-dom';
import { useFetch } from '../../hooks/useFetch';
import { ErrorState, Loading, Empty } from '../../components/ui';
import { fmtDate, greeting, initials, money } from '../../utils/format';

export default function Dashboard() {
  const { data: d, loading, error, reload } = useFetch('/students/me/dashboard');
  if (loading) return <Loading />;
  if (error) return <ErrorState error={error} onRetry={reload} />;
  const s = d.student;
  const r = d.latest_result;
  return (
    <div className="stack">
      <div className="greet card">
        <div className="avatar" style={{ width: 56, height: 56, fontSize: '1.2rem' }}>{initials(s.full_name)}</div>
        <div>
          <h1>{greeting()}, {s.first_name}</h1>
          <div className="muted small">{d.school.name}</div>
          <div className="small">{s.class}{s.stream ? ` ${s.stream}` : ''} · Adm No. <b>{s.admission_number}</b></div>
        </div>
      </div>

      <div className="cards">
        <div className="card stat"><div className="label">Fee balance</div><div className="value" style={{ color: d.fee_balance > 0 ? 'var(--red)' : 'var(--green)' }}>{money(d.fee_balance)}</div>
          <Link to="/student/fees" className="small">View fees</Link></div>
        <div className="card stat"><div className="label">Latest result</div>
          <div className="value">{r ? `${r.mean_grade} · ${r.mean}%` : '-'}</div>
          <Link to="/student/results" className="small">{r ? r.exam : 'No results yet'}</Link></div>
        <div className="card stat"><div className="label">Current term</div><div className="value" style={{ fontSize: '1.15rem' }}>{d.term ? `${d.term.name}, ${d.term.year}` : 'Not set'}</div>
          {d.term?.end_date && <span className="small muted">Closes {fmtDate(d.term.end_date)}</span>}</div>
        <div className="card stat"><div className="label">Next lesson</div>
          <div className="value" style={{ fontSize: '1.15rem' }}>{d.next_lesson ? d.next_lesson.title : 'None today'}</div>
          {d.next_lesson && <span className="small muted">{d.next_lesson.start_time} - {d.next_lesson.end_time}</span>}</div>
      </div>

      <section>
        <div className="row between"><h2>Announcements</h2><Link to="/student/announcements" className="small">See all</Link></div>
        {d.announcements.length === 0 ? <div className="card"><Empty title="No announcements">Messages from your school will appear here.</Empty></div> : (
          <div className="stack">{d.announcements.map((a) => (
            <div key={a.id} className={`card prio-${a.priority}`}><strong>{a.title}</strong><p className="small muted">{fmtDate(a.created_at)} · {a.author}</p><p>{a.content}</p></div>
          ))}</div>
        )}
      </section>
    </div>
  );
}
