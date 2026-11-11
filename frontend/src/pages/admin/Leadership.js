import { useState } from 'react';
import { useFetch } from '../../hooks/useFetch';
import { api } from '../../services/api';
import { Alert, Button, ErrorState, Field, Loading, Modal } from '../../components/ui';

export default function Leadership() {
  const { data, loading, error, reload } = useFetch('/modules/leadership');
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState({});
  const [msg, setMsg] = useState('');

  if (loading) return <Loading />;
  if (error) return <ErrorState error={error} onRetry={reload} />;

  const profile = data || {};
  const startEdit = () => {
    setForm({ ...profile });
    setEditing(true);
  };
  const save = async () => {
    try {
      await api.put('/modules/leadership', form);
      setEditing(false);
      setMsg('Leadership profile updated.');
      reload();
    } catch (e) {
      setMsg(e.message);
    }
  };

  return (
    <div className="stack">
      <div className="row between">
        <h1>Leadership & Vision</h1>
        <Button variant="secondary" onClick={startEdit}>Edit</Button>
      </div>
      <Alert type="success">{msg}</Alert>

      {!editing ? (
        <div className="card" style={{ maxWidth: 720, margin: '0 auto', textAlign: 'center', padding: '2.5rem 1.5rem' }}>
          {profile.photo_url && (
            <img
              src={profile.photo_url}
              alt={profile.name}
              style={{ width: 160, height: 160, objectFit: 'cover', borderRadius: '50%', marginBottom: '1.25rem', border: '4px solid #f0f0f0' }}
            />
          )}
          <h2 style={{ margin: '0 0 .25rem', fontSize: '1.75rem' }}>{profile.name}</h2>
          <div className="muted" style={{ marginBottom: '1.25rem', fontSize: '1.05rem' }}>{profile.designation}</div>
          <p style={{ lineHeight: 1.6, fontSize: '1.05rem', maxWidth: 560, margin: '0 auto' }}>
            {profile.acknowledgement}
          </p>
        </div>
      ) : (
        <Modal title="Edit Leadership Profile" onClose={() => setEditing(false)}>
          <Alert type="error">{msg}</Alert>
          <Field label="Name" value={form.name || ''} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          <Field label="Designation" value={form.designation || ''} onChange={(e) => setForm({ ...form, designation: e.target.value })} />
          <Field as="textarea" label="Acknowledgement" rows={5} value={form.acknowledgement || ''} onChange={(e) => setForm({ ...form, acknowledgement: e.target.value })} />
          <Field label="Photo URL" value={form.photo_url || ''} onChange={(e) => setForm({ ...form, photo_url: e.target.value })} />
          <div className="row" style={{ gap: '.5rem', marginTop: '1rem' }}>
            <Button onClick={save}>Save</Button>
            <Button variant="secondary" onClick={() => setEditing(false)}>Cancel</Button>
          </div>
        </Modal>
      )}
    </div>
  );
}
