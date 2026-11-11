import { Link } from 'react-router-dom';
import { useFetch } from '../../hooks/useFetch';
import { Empty, ErrorState, Loading } from '../../components/ui';
import ModuleCards from '../../components/ModuleCards';
import { fmtDate, greeting, initials, money } from '../../utils/format';

export default function ParentDashboard() {
  const { data: d, loading, error, reload } = useFetch('/parent/dashboard');
  if (loading) return <Loading />;
  if (error) return <ErrorState error={error} onRetry={reload} />;
  return (
    <div className="stack">
      <div>
        <h1>{greeting()}, {d.parent.first_name}</h1>
        <p className="muted">{d.school.name}{d.term ? ` · ${d.term.name}, ${d.term.year}` : ''}</p>
      </div>

      <ModuleCards base="/parent" />

      {d.children.length === 0 ? (
        <div className="card"><Empty title="No children linked yet">Ask the school office to link your account to your child's record.</Empty></div>
      ) : (<>
        <div className="card stat accent">
          <div className="label">Total fee balance this term</div>
          <div className="value" style={{ color: d.total_balance > 0 ? 'var(--red)' : 'var(--green)' }}>{money(d.total_balance)}</div>
          <span className="small muted">Across {d.children.length} child{d.children.length === 1 ? '' : 'ren'}</span>
        </div>
        <section>
          <h2>My children</h2>
          <div className="list">{d.children.map((c) => (
            <Link key={c.id} to={`/parent/children/${c.id}`} className="list-row" style={{ alignItems: 'flex-start' }}>
              <div className="avatar">{initials(c.full_name)}</div>
              <div className="grow"><b>{c.full_name}</b>
                <div className="small muted">{c.class}{c.stream ? ` ${c.stream}` : ''} · Adm No. {c.admission_number}</div>
                <div className="small" style={{ marginTop: 4 }}>
                  {c.latest_result ? <>Latest: <b>{c.latest_result.mean_grade}</b> ({c.latest_result.mean}%) in {c.latest_result.exam}</> : <span className="muted">No results yet</span>}
                </div></div>
              <div className="right"><div className="small muted">Balance</div><b style={{ color: c.fee_balance > 0 ? 'var(--red)' : 'var(--green)' }}>{money(c.fee_balance)}</b></div>
            </Link>))}</div>
        </section>
      </>)}

      <section>
        <div className="row between"><h2>School news</h2><Link to="/parent/announcements" className="small">See all</Link></div>
        {d.announcements.length === 0 ? <div className="card muted small">No announcements.</div> : d.announcements.map((a) => (
          <div key={a.id} className={`card prio-${a.priority}`} style={{ marginBottom: '.75rem' }}><strong>{a.title}</strong><p className="small muted">{fmtDate(a.created_at)} · {a.author}</p><p>{a.content}</p></div>))}
      </section>
    </div>
  );
}
