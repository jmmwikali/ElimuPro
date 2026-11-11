import { Link } from 'react-router-dom';
import { useFetch } from '../../hooks/useFetch';
import { Loading, ErrorState, Empty } from '../../components/ui';

export default function ParentCareerGPS() {
  const { data, loading, error, reload } = useFetch('/parent/dashboard');
  if (loading) return <Loading />;
  if (error) return <ErrorState error={error} onRetry={reload} />;

  return (
    <div className="stack">
      <h1>CareerGPS</h1>
      <p className="muted">CareerGPS helps your children explore careers and courses. It is an independent module with its own page.</p>
      {data.children.length === 0 ? (
        <Empty title="No children linked">Ask the school to link your account.</Empty>
      ) : (
        <div className="list">
          {data.children.map((c) => (
            <div key={c.id} className="card" style={{ marginBottom: '.75rem' }}>
              <b>{c.full_name}</b>
              <div className="small muted">{c.class}{c.stream ? ` ${c.stream}` : ''}</div>
              <div style={{ marginTop: '.75rem' }}>
                <Link to={`/parent/children/${c.id}`} className="small">View child →</Link>
              </div>
            </div>
          ))}
        </div>
      )}
      <Link to="/parent" className="small">← Back to children</Link>
    </div>
  );
}
