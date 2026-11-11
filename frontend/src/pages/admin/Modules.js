import { useState } from 'react';
import { useFetch } from '../../hooks/useFetch';
import { api } from '../../services/api';
import { Alert, Button, ErrorState, Loading } from '../../components/ui';

export default function Modules() {
  const { data: modules, loading, error, reload } = useFetch('/modules');
  const { data: schools } = useFetch('/schools');
  const [selectedSchool, setSelectedSchool] = useState(null);
  const [schoolModules, setSchoolModules] = useState([]);
  const [msg, setMsg] = useState('');

  const loadSchoolModules = async (schoolId) => {
    setSelectedSchool(schoolId);
    try {
      const res = await api.get(`/modules/school/${schoolId}`);
      setSchoolModules(res);
    } catch (e) {
      setMsg(e.message);
    }
  };

  const toggle = async (code, currentlyEnabled) => {
    if (!selectedSchool) return;
    try {
      await api.put(`/modules/school/${selectedSchool}/${code}`, { is_enabled: !currentlyEnabled });
      setMsg('Module updated.');
      loadSchoolModules(selectedSchool);
    } catch (e) {
      setMsg(e.message);
    }
  };

  if (loading) return <Loading />;
  if (error) return <ErrorState error={error} onRetry={reload} />;

  return (
    <div className="stack">
      <h1>Module Management</h1>
      <Alert>{msg}</Alert>
      <p className="muted">Enable or disable ElimuNova modules for individual schools.</p>

      <div className="card">
        <h3>Select a school</h3>
        <div className="list">
          {(schools || []).map((s) => (
            <button
              key={s.id}
              className={`list-row ${selectedSchool === s.id ? 'active' : ''}`}
              style={{ textAlign: 'left', background: selectedSchool === s.id ? '#f4f4f8' : undefined }}
              onClick={() => loadSchoolModules(s.id)}
            >
              <div className="grow"><b>{s.name}</b></div>
            </button>
          ))}
        </div>
      </div>

      {selectedSchool && (
        <div className="card">
          <h3>Modules for selected school</h3>
          {(modules || []).map((m) => {
            const sm = schoolModules.find((x) => x.module_code === m.code);
            const enabled = sm ? sm.is_enabled : m.is_core;
            return (
              <div key={m.code} className="list-row">
                <div className="grow">
                  <b>{m.name}</b>
                  <div className="small muted">{m.description}</div>
                  {m.is_core && <span className="badge">Core</span>}
                </div>
                <Button
                  variant={enabled ? 'secondary' : ''}
                  className="small"
                  disabled={m.is_core}
                  onClick={() => toggle(m.code, enabled)}
                >
                  {enabled ? 'Enabled' : 'Disabled'}
                </Button>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
