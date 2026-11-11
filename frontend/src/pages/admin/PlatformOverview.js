import { useFetch } from '../../hooks/useFetch';
import { ErrorState, Loading } from '../../components/ui';

export default function PlatformOverview() {
  const { data: schools, loading: sLoading, error: sError } = useFetch('/schools');
  const { data: modules, loading: mLoading } = useFetch('/modules');

  if (sLoading || mLoading) return <Loading />;
  if (sError) return <ErrorState error={sError} />;

  const totalSchools = (schools || []).length;
  const activeSchools = (schools || []).filter((s) => s.is_active).length;
  const totalStudents = (schools || []).reduce((sum, s) => sum + (s.student_count || 0), 0);

  const cards = [
    { label: 'Registered Schools', value: totalSchools, sub: `${activeSchools} active` },
    { label: 'Total Students', value: totalStudents, sub: 'Across all schools' },
    { label: 'Active Modules', value: (modules || []).filter((m) => m.is_active).length, sub: 'Platform-wide' },
    { label: 'Platform Status', value: 'Operational', sub: 'All systems running' },
  ];

  return (
    <div className="stack">
      <h1>Platform Overview</h1>
      <p className="muted">Central command centre for the ElimuNova ecosystem.</p>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', marginTop: '1rem' }}>
        {cards.map((c) => (
          <div key={c.label} className="card" style={{ textAlign: 'center', padding: '1.5rem 1rem' }}>
            <div style={{ fontSize: '2rem', fontWeight: 700, color: '#1A1F36' }}>{c.value}</div>
            <div style={{ fontWeight: 600, marginTop: '.25rem' }}>{c.label}</div>
            <div className="small muted">{c.sub}</div>
          </div>
        ))}
      </div>

      <div className="card" style={{ marginTop: '1.5rem' }}>
        <h3>Recent schools</h3>
        <div className="list">
          {(schools || []).slice(0, 8).map((s) => (
            <div key={s.id} className="list-row">
              <div className="grow">
                <b>{s.name}</b>
                <div className="small muted">{s.county} · {s.student_count || 0} students</div>
              </div>
              <span className={`badge ${s.is_active ? 'green' : 'red'}`}>{s.is_active ? 'Active' : 'Inactive'}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
