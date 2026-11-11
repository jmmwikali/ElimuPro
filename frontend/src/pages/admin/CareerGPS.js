import { useState } from 'react';
import { useFetch } from '../../hooks/useFetch';
import { api } from '../../services/api';
import { Alert, Button, ErrorState, Field, Loading, Modal } from '../../components/ui';

export default function CareerGPS() {
  const { data: paths, loading, error, reload } = useFetch('/modules/careergps/paths');
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ title: '', description: '', category: '' });
  const [msg, setMsg] = useState('');

  const create = async () => {
    try {
      await api.post('/modules/careergps/paths', form);
      setOpen(false);
      setForm({ title: '', description: '', category: '' });
      setMsg('Career path added.');
      reload();
    } catch (e) {
      setMsg(e.message);
    }
  };

  if (loading) return <Loading />;
  if (error) return <ErrorState error={error} onRetry={reload} />;

  return (
    <div className="stack">
      <div className="row between">
        <h1>CareerGPS</h1>
        <Button onClick={() => setOpen(true)}>Add career path</Button>
      </div>
      <Alert type="success">{msg}</Alert>
      <p className="muted">Explore career paths, courses and guidance for students.</p>

      <div className="list">
        {(paths || []).length === 0 && <div className="empty">No career paths yet. Add the first one.</div>}
        {(paths || []).map((p) => (
          <div key={p.id} className="list-row">
            <div className="grow">
              <b>{p.title}</b>
              <div className="small muted">{p.category} · {p.description}</div>
            </div>
          </div>
        ))}
      </div>

      {open && (
        <Modal title="New career path" onClose={() => setOpen(false)}>
          <Alert type="error">{msg}</Alert>
          <Field label="Title" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
          <Field label="Category" value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} />
          <Field as="textarea" label="Description" rows={4} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
          <Button block onClick={create}>Create</Button>
        </Modal>
      )}
    </div>
  );
}
