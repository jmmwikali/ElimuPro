import { useState } from 'react';
import { useFetch } from '../../hooks/useFetch';
import { api } from '../../services/api';
import { Alert, Button, ErrorState, Loading } from '../../components/ui';

export default function StudentCareerGPS() {
  const { data: paths, loading, error, reload } = useFetch('/modules/careergps/paths');
  const [msg, setMsg] = useState('');

  const expressInterest = async (pathId) => {
    try {
      // In a full implementation this would use the logged-in student's id
      await api.post('/modules/careergps/interest', { career_path_id: pathId, interest_level: 4 });
      setMsg('Interest recorded. Your guidance counsellor can see this.');
    } catch (e) {
      setMsg(e.message || 'Could not save interest');
    }
  };

  if (loading) return <Loading />;
  if (error) return <ErrorState error={error} onRetry={reload} />;

  return (
    <div className="stack">
      <h1>CareerGPS</h1>
      <p className="muted">Explore career paths that match your interests and academic strengths.</p>
      <Alert type="success">{msg}</Alert>
      <div className="list">
        {(paths || []).length === 0 && <div className="empty">No career paths available yet. Check back soon.</div>}
        {(paths || []).map((p) => (
          <div key={p.id} className="list-row" style={{ alignItems: 'flex-start' }}>
            <div className="grow">
              <b>{p.title}</b>
              <div className="small muted">{p.category}</div>
              <p style={{ margin: '.4rem 0 0', fontSize: '.95rem' }}>{p.description}</p>
            </div>
            <Button variant="secondary" className="small" onClick={() => expressInterest(p.id)}>I'm interested</Button>
          </div>
        ))}
      </div>
    </div>
  );
}

