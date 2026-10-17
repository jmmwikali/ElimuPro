import { useEffect, useRef, useState } from 'react';
import { BrowserQRCodeReader } from '@zxing/browser';
import { Link } from 'react-router-dom';
import { Alert, Button, Empty, ErrorState, Loading, Pager } from '../../components/ui';
import { useFetch } from '../../hooks/useFetch';
import { api } from '../../services/api';
import './zeroq.css';

function Stat({ label, value, tone }) {
  return <div className={`card stat zeroq-stat ${tone || ''}`}><div className="label">{label}</div><div className="value">{value ?? 0}</div></div>;
}

function localDate() {
  const today = new Date();
  return `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;
}

export function ZeroQDashboard() {
  const stats = useFetch('/zeroq/dashboard');
  const queue = useFetch(`/zeroq/queue?date=${localDate()}`);
  if (stats.loading || queue.loading) return <Loading label="Loading admissions overview" />;
  if (stats.error) return <ErrorState error={stats.error} onRetry={stats.reload} />;
  if (queue.error) return <ErrorState error={queue.error} onRetry={queue.reload} />;
  const d = stats.data;
  return (
    <div className="zeroq-page stack">
      <div className="row between wrap zeroq-heading"><div><span className="zeroq-kicker">ADMISSIONS OPERATIONS</span><h1>ZeroQ</h1><p>Today’s digital admission activity</p></div><div className="row wrap"><Link className="btn secondary" to="/admin/zeroq/queue">Arrival queue</Link><Link className="btn" to="/admin/zeroq/scanner">Open scanner</Link></div></div>
      <div className="zeroq-stats">
        <Stat label="Total applicants" value={d.total_applicants} />
        <Stat label="Pending admissions" value={d.pending_admissions} tone="warning" />
        <Stat label="Passes ready / checked in" value={d.verified} tone="blue" />
        <Stat label="Today's arrivals" value={d.today_arrivals} />
        <Stat label="QR scans today" value={d.qr_scans_today} tone="blue" />
        <Stat label="Completed" value={d.completed} tone="green" />
      </div>
      <section className="zeroq-section">
        <div className="row between wrap"><div><h2>Expected today</h2><p className="muted small">Students with an active ZeroQ pass for today.</p></div><Link to="/admin/zeroq/queue">View full queue</Link></div>
        {!queue.data.length ? <div className="card"><Empty title="No arrivals scheduled">Issued passes for today will appear here.</Empty></div> : (
          <div className="table-wrap"><table><thead><tr><th>Student</th><th>Admission</th><th>Class</th><th>Pass status</th><th>Reference</th></tr></thead><tbody>
            {queue.data.map((item) => <tr key={item.id}><td>{item.student.full_name}</td><td>{item.student.admission_number}</td><td>{item.student.class || '-'}</td><td><span className={`zeroq-status ${item.status}`}>{item.status.replace('_', ' ')}</span></td><td>{item.reference}</td></tr>)}
          </tbody></table></div>
        )}
      </section>
    </div>
  );
}

export function ZeroQQueue() {
  const [term, setTerm] = useState('');
  const [page, setPage] = useState(1);
  const path = `/zeroq/queue?date=${localDate()}&page=${page}${term ? `&q=${encodeURIComponent(term)}` : ''}`;
  const queue = useFetch(path);
  return (
    <div className="zeroq-page stack">
      <div className="row between wrap zeroq-heading"><div><span className="zeroq-kicker">ADMISSIONS OPERATIONS</span><h1>Today's arrivals</h1><p>Digital queue; no physical line required.</p></div><Link className="btn" to="/admin/zeroq/scanner">Open scanner</Link></div>
      <input className="input" value={term} onChange={(e) => { setTerm(e.target.value); setPage(1); }} placeholder="Search name, admission number, pass reference, or phone" aria-label="Search today's arrivals" />
      {queue.loading ? <Loading /> : queue.error ? <ErrorState error={queue.error} onRetry={queue.reload} /> : !queue.data.length ? <div className="card"><Empty title="No matching arrivals">Active passes expected today appear here.</Empty></div> : (
        <><div className="table-wrap"><table><thead><tr><th>Student</th><th>Admission</th><th>Class</th><th>Pass</th><th>Reference</th><th>Expected</th></tr></thead><tbody>
          {queue.data.map((item) => <tr key={item.id}><td>{item.student.full_name}</td><td>{item.student.admission_number}</td><td>{item.student.class || '-'}</td><td><span className={`zeroq-status ${item.status}`}>{item.status.replace('_', ' ')}</span></td><td>{item.reference}</td><td>{item.expected_on}</td></tr>)}
        </tbody></table></div><Pager meta={queue.meta} onPage={setPage} /></>
      )}
    </div>
  );
}

export function ZeroQScanner() {
  const videoRef = useRef(null);
  const controlsRef = useRef(null);
  const scanningRef = useRef(false);
  const [camera, setCamera] = useState('idle');
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => () => controlsRef.current?.stop(), []);

  const validate = async (qrValue) => {
    setBusy(true);
    setError('');
    setResult(null);
    try {
      const response = await api.post('/zeroq/scan', { qr_value: qrValue });
      setResult(response.data);
    } catch (e) {
      setError(e.status === 0
        ? 'Network unavailable. This scan is not verified. Reconnect and scan again.'
        : `${e.message} This scan is not verified.`);
    } finally {
      setBusy(false);
      scanningRef.current = false;
    }
  };

  const start = async () => {
    setError('');
    setResult(null);
    if (!navigator.mediaDevices?.getUserMedia) {
      setCamera('error');
      setError('Camera access is not available. Use a secure HTTPS page or localhost and check browser permissions.');
      return;
    }
    setCamera('starting');
    try {
      const reader = new BrowserQRCodeReader();
      controlsRef.current = await reader.decodeFromVideoDevice(undefined, videoRef.current, (decoded) => {
        if (!decoded || scanningRef.current) return;
        scanningRef.current = true;
        controlsRef.current?.stop();
        setCamera('idle');
        void validate(decoded.getText());
      });
      setCamera('active');
    } catch (e) {
      setCamera('error');
      if (e.name === 'NotAllowedError') setError('Camera permission was denied. Allow camera access in your browser settings and try again.');
      else if (e.name === 'NotFoundError') setError('No camera was found on this device.');
      else setError('The camera could not start. Check that it is not being used by another app.');
    }
  };

  const complete = async () => {
    if (!result?.valid || !result.pass?.id) return;
    setBusy(true);
    setError('');
    try {
      const response = await api.post(`/zeroq/${result.pass.id}/complete`, {});
      setResult({ ...result, status: 'completed', message: response.message });
    } catch (e) {
      setError(e.status === 0 ? 'Network unavailable. Admission was not completed.' : e.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="zeroq-page stack">
      <div className="zeroq-heading"><span className="zeroq-kicker">ADMISSIONS OPERATIONS</span><h1>QR scanner</h1><p>Scan a student’s ZeroQ admission pass to validate it with the school server.</p></div>
      {error && <Alert type="error">{error}</Alert>}
      <div className="zeroq-scanner">
        <video ref={videoRef} className={`zeroq-video ${camera === 'active' ? 'visible' : ''}`} muted playsInline />
        {camera !== 'active' && <div className="zeroq-camera-state"><div className="zeroq-camera-mark">ZQ</div><strong>{camera === 'starting' ? 'Starting camera…' : 'Camera is off'}</strong><span>Camera permission is requested only when you open the scanner.</span></div>}
        {camera === 'active' && <div className="zeroq-scan-frame" aria-hidden="true" />}
      </div>
      <div className="row wrap">{camera === 'active' ? <Button variant="secondary" onClick={() => { controlsRef.current?.stop(); setCamera('idle'); }}>Stop camera</Button> : <Button onClick={start} disabled={busy || camera === 'starting'}>{camera === 'starting' ? 'Starting camera…' : 'Open camera scanner'}</Button>}{busy && <span className="muted">Validating with school server…</span>}</div>
      {result && <section className={`zeroq-result ${result.valid ? 'verified' : 'rejected'}`} aria-live="polite">
        <div className="row between wrap"><div><span className="zeroq-kicker">SERVER VALIDATION</span><h2>{result.status === 'completed' ? 'Admission complete' : result.valid ? 'Pass verified' : `Pass ${result.status.replace('_', ' ')}`}</h2></div><span className={`zeroq-status ${result.valid ? 'verified' : result.status}`}>{result.status.replace('_', ' ')}</span></div>
        <p>{result.message}</p>
        {result.valid && <><div className="zeroq-verify-grid"><div><span>Student</span><strong>{result.student.full_name}</strong></div><div><span>Admission number</span><strong>{result.student.admission_number}</strong></div><div><span>Class</span><strong>{result.student.class || '-'}</strong></div><div><span>Institution</span><strong>{result.student.institution}</strong></div><div><span>Admission status</span><strong>{result.student.admission_status}</strong></div><div><span>Documents on file</span><strong>{result.student.document_count}</strong></div></div>
          {result.status === 'verified' && <Button onClick={complete} loading={busy}>Complete admission</Button>}
        </>}
      </section>}
      <p className="small muted">A scan is never shown as verified while offline. Keep the student at the verification point until the server response is visible.</p>
    </div>
  );
}