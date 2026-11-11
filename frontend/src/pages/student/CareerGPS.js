import { useFetch } from '../../hooks/useFetch';
import { ErrorState, Loading } from '../../components/ui';

export default function StudentCareerGPS() {
  const { data: paths, loading, error, reload } = useFetch('/modules/careergps/paths');

  if (loading) return <Loading />;
  if (error) return <ErrorState error={error} onRetry={reload} />;

  return (
    <div className="stack">
      <h1>CareerGPS</h1>
      <p className="muted">Explore career paths that match your interests and academic strengths.</p>
      <div className="list">
        {(paths || []).length === 0 && <div className="empty">No career paths available yet. Check back soon.</div>}
        {(paths || []).map((p) => (
          <div key={p.id} className="list-row">
            <div className="grow">
              <b>{p.title}</b>
              <div className="small muted">{p.category}</div>
              <p style={{ margin: '.4rem 0 0', fontSize: '.95rem' }}>{p.description}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
