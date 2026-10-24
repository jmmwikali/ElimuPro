import { useEffect, useState } from 'react';
import { QRCodeSVG } from 'qrcode.react';
import { Alert, Button, ErrorState, Loading } from '../../components/ui';
import { api } from '../../services/api';
import { BRAND } from '../../config/brand';
import '../admin/zeroq.css';

function dateLabel(value) {
  if (!value) return 'Not set';
  return new Date(`${value}T00:00:00`).toLocaleDateString(undefined, {
    year: 'numeric', month: 'long', day: 'numeric',
  });
}

export default function ZeroQStudent() {
  const [record, setRecord] = useState(null);
  const [qrValue, setQrValue] = useState('');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [message, setMessage] = useState('');

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.get('/zeroq/my');
      setRecord(response.data);
      setQrValue('');
    } catch (e) {
      setError(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const issue = async () => {
    setBusy(true);
    setMessage('');
    try {
      const response = await api.post('/zeroq/my/pass', {});
      setRecord({ eligible: true, pass: response.data.pass });
      setQrValue(response.data.qr_value);
      setMessage(response.message || 'Your pass is ready. Keep the QR code private.');
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  };

  const revoke = async () => {
    setBusy(true);
    setMessage('');
    try {
      await api.post('/zeroq/my/pass/revoke', {});
      setQrValue('');
      await load();
      setMessage('Your pass has been revoked. Generate a new one when you are ready.');
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  };

  if (loading) return <Loading label="Loading your admission pass" />;
  if (error && !record) return <ErrorState error={error} onRetry={load} />;
  if (!record?.eligible) {
    return (
      <section className="zeroq-page stack">
        <div className="zeroq-heading"><span className="zeroq-kicker">{BRAND.name.toUpperCase()} ADMISSIONS</span><h1>ZeroQ</h1><p>No queue. No paperwork. Just scan.</p></div>
        <div className="card zeroq-empty"><h2>Your digital pass comes after approval</h2><p className="muted">Complete your application and wait for your school to approve your admission. Your pass will appear here when you are enrolled.</p></div>
      </section>
    );
  }

  const pass = record.pass;
  const qrIsValid = pass && pass.status === 'ready';

  return (
    <section className="zeroq-page stack">
      <div className="zeroq-heading"><span className="zeroq-kicker">{BRAND.name.toUpperCase()} ADMISSIONS</span><h1>ZeroQ</h1><p>No queue. No paperwork. Just scan.</p></div>
      {message && <Alert type="success">{message}</Alert>}
      {error && <Alert type="error">{error.message} Your pass has not been verified or changed unless the server confirms it.</Alert>}
      {!pass ? (
        <div className="card zeroq-empty"><h2>Your admission pass is ready to be issued</h2><p className="muted">Generate a secure QR pass to present when you arrive at school.</p><Button onClick={issue} loading={busy}>Generate admission pass</Button></div>
      ) : (
        <div className="zeroq-pass">
          <div className="zeroq-pass-top"><div><span className="zeroq-kicker">DIGITAL ADMISSION PASS</span><h2>{pass.student.full_name}</h2><p>{pass.student.class || 'Class to be confirmed'}</p></div><span className={`zeroq-status ${pass.status}`}>{pass.status.replace('_', ' ')}</span></div>
          <div className="zeroq-pass-body">
            <div className="zeroq-qr-frame">
              {qrValue && qrIsValid ? <QRCodeSVG value={qrValue} size={220} level="H" includeMargin /> : <div className="zeroq-qr-placeholder">{pass.status === 'checked_in' ? 'Already scanned' : pass.status === 'completed' ? 'Admission completed' : pass.status === 'revoked' ? 'Pass revoked' : 'Generate a fresh pass to display your QR'}</div>}
            </div>
            <div className="zeroq-pass-details">
              <div><span>Admission number</span><strong>{pass.student.admission_number}</strong></div>
              <div><span>Pass reference</span><strong>{pass.reference}</strong></div>
              <div><span>Expected arrival</span><strong>{dateLabel(pass.expected_on)}</strong></div>
              <div><span>Valid until</span><strong>{new Date(pass.expires_at).toLocaleString()}</strong></div>
            </div>
          </div>
          <div className="zeroq-pass-note">Present this pass to an admissions officer. The QR contains a secure reference, not your personal details.</div>
          <div className="row wrap zeroq-actions no-print">
            {['ready', 'expired', 'revoked'].includes(pass.status) && <Button onClick={issue} loading={busy}>{pass.status === 'ready' ? 'Regenerate pass' : 'Generate new pass'}</Button>}
            {pass.status === 'ready' && qrValue && <Button variant="secondary" onClick={revoke} loading={busy}>Revoke pass</Button>}
          </div>
        </div>
      )}
    </section>
  );
}