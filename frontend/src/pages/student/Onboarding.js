import { useEffect, useState } from 'react';
import { useFetch } from '../../hooks/useFetch';
import { api, API_BASE } from '../../services/api';
import { Alert, Button, Empty, ErrorState, Field, Loading } from '../../components/ui';
import { fmtDate } from '../../utils/format';
import '../onboarding.css';

const STATE_TONE = { done: 'green', action: 'warning', waiting: 'blue', blocked: 'red', not_applicable: '' };
const STATE_LABEL = { done: 'Done', action: 'Your turn', waiting: 'With your school', blocked: 'Needs attention', not_applicable: 'Not required', not_started: 'Not started' };
const DOC_TONE = { approved: 'green', passed_automated_checks: 'blue', human_review_required: 'blue', uploaded: 'blue', processing: 'blue', additional_information_required: 'warning', rejected: 'red' };
const RESULT_TONE = { verified: 'green', additional_information_required: 'warning', rejected: 'red', verification_failed: 'red' };
const BLANK_ROW = { subject: '', result: '' };

function Progress({ data }) {
  return (
    <>
      <div className="card ob-next stack">
        <span className="small muted">NEXT STEP</span>
        <b>{data.next_action}</b>
        {data.latest_update && <span className="small muted">Latest update: {data.latest_update.title} · {fmtDate(data.latest_update.at)}</span>}
        <span className="small muted">{data.submission_date ? `Application submitted ${fmtDate(data.submission_date)}.` : 'Application not submitted yet.'} {data.deadline_note}</span>
      </div>
      <div className="ob-stages">
        {data.stages.map((s) => (
          <div key={s.key} className={`ob-stage ${s.state}`}>
            <b>{s.label}</b><span className={`badge ${STATE_TONE[s.state] || ''}`}>{STATE_LABEL[s.state] || s.state}</span><small>{s.detail}</small>
          </div>
        ))}
      </div>
    </>
  );
}

/* The status wording comes from the server so it can never claim more than has happened:
   a submission is "yours, not yet checked" until a school reviewer has verified it. */
function Results({ onChanged }) {
  const { data, loading, error, reload } = useFetch('/zeroq/my/results');
  const current = data && data.results[0];
  const [year, setYear] = useState(new Date().getFullYear());
  const [candidate, setCandidate] = useState('');
  const [rows, setRows] = useState([{ ...BLANK_ROW }]);
  const [errs, setErrs] = useState({});
  const [msg, setMsg] = useState({});
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!current) return;
    setYear(current.assessment_year); setCandidate(current.candidate_number || '');
    setRows(current.subjects.length ? current.subjects : [{ ...BLANK_ROW }]);
  }, [current]);

  const body = () => ({ assessment_year: Number(year), candidate_number: candidate, subjects: rows.filter((r) => r.subject.trim() || r.result.trim()) });
  const setRow = (i, k, v) => setRows(rows.map((r, j) => (j === i ? { ...r, [k]: v } : r)));
  const save = async (andSubmit) => {
    setBusy(true); setErrs({}); setMsg({});
    try {
      const saved = await api.put('/zeroq/my/results', body());
      if (andSubmit) { const done = await api.post(`/zeroq/my/results/${saved.data.id}/submit`); setMsg({ type: 'success', text: done.message }); } else setMsg({ type: 'success', text: 'Draft saved.' });
      reload(); onChanged();
    } catch (e) { setErrs(e.errors || {}); setMsg({ type: 'error', text: e.message }); } finally { setBusy(false); }
  };

  if (loading && !data) return <Loading />;
  if (error && !data) return <ErrorState error={error} onRetry={reload} />;
  const editable = !current || current.editable;
  return (
    <div className="card stack">
      <div className="row between wrap"><h2 style={{ margin: 0 }}>KJSEA results</h2>
        {current && <span className={`badge ${RESULT_TONE[current.status] || 'blue'}`}>{current.status_label}</span>}</div>
      <p className="muted small" style={{ margin: 0 }}>Enter your results exactly as they appear on your results document. Your school checks them; nothing here is an official placement.</p>
      {current && <Alert type={RESULT_TONE[current.status] === 'red' ? 'error' : 'info'}>{current.message}</Alert>}
      {current && current.review_note && <div className="ob-note"><b>From your school:</b> {current.review_note}</div>}
      <Alert type={msg.type}>{msg.text}</Alert>
      <div className="row wrap" style={{ gap: '.75rem' }}>
        <Field label="Year you sat the assessment" name="ob-year" type="number" required disabled={!editable || !!current} value={year} onChange={(e) => setYear(e.target.value)} error={errs.assessment_year} />
        <Field label="Assessment / candidate number" name="ob-candidate" required disabled={!editable} value={candidate} onChange={(e) => setCandidate(e.target.value)} error={errs.candidate_number} />
      </div>
      <div className="ob-subjects">
        {rows.map((r, i) => (
          <div key={i} className="ob-subject-row">
            <Field label={i === 0 ? 'Subject' : 'Subject '} name={`ob-subject-${i}`} disabled={!editable} value={r.subject} onChange={(e) => setRow(i, 'subject', e.target.value)} />
            <Field label={i === 0 ? 'Result' : 'Result '} name={`ob-result-${i}`} disabled={!editable} value={r.result} onChange={(e) => setRow(i, 'result', e.target.value)} />
            {editable && rows.length > 1 ? <Button variant="secondary" className="small" onClick={() => setRows(rows.filter((_, j) => j !== i))} aria-label={`Remove row ${i + 1}`}>✕</Button> : <span />}
          </div>
        ))}
        {errs.subjects && <div className="err" role="alert">{errs.subjects}</div>}
        {editable && rows.length < 20 && <div><Button variant="secondary" className="small" onClick={() => setRows([...rows, { ...BLANK_ROW }])}>Add a subject</Button></div>}
      </div>
      {editable && <div className="ob-actions"><Button variant="secondary" onClick={() => save(false)} loading={busy}>Save draft</Button><Button onClick={() => save(true)} loading={busy}>Submit to my school</Button></div>}
      {current && current.history.length > 1 && (
        <details><summary className="small muted">Status history</summary>
          <ul className="ob-timeline">{current.history.map((h, i) => <li key={i}>{h.to_label}<small>{h.by} · {fmtDate(h.at)}{h.note ? ` · ${h.note}` : ''}</small></li>)}</ul></details>
      )}
    </div>
  );
}

function DocRow({ item, onUploaded }) {
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState({});
  const cur = item.current;
  const pick = async (e) => {
    const file = e.target.files[0]; e.target.value = '';
    if (!file) return;
    setBusy(true); setMsg({});
    const form = new FormData(); form.append('doc_type', item.doc_type); form.append('file', file);
    try { await api.upload('/zeroq/my/documents', form); onUploaded(); }
    catch (err) { setMsg({ type: 'error', text: err.message }); } finally { setBusy(false); }
  };
  const open = async () => {
    try { const r = await api.post(`/zeroq/my/documents/${cur.id}/link`); window.location.assign(`${API_BASE}${r.data.path}`); }
    catch (err) { setMsg({ type: 'error', text: err.message }); }
  };
  const checks = cur && cur.verification ? cur.verification.checks.filter((c) => c.status === 'failed' || c.status === 'warning') : [];
  return (
    <div className="ob-doc">
      <div className="row between wrap">
        <div className="grow"><b>{item.label}</b> {item.required === false ? <span className="small muted">(optional)</span> : item.required ? <span className="small muted">(required)</span> : null}</div>
        {cur ? <span className={`badge ${DOC_TONE[cur.status] || ''}`}>{cur.status_label}</span> : <span className="badge warning">Not uploaded</span>}
      </div>
      {item.instructions && <div className="ob-guide">{item.instructions}</div>}
      {cur && <div className="small muted">{cur.file_name} · version {cur.version} · {fmtDate(cur.uploaded_at)} · {cur.message}</div>}
      {cur && cur.review_note && <div className="ob-note"><b>From your school:</b> {cur.review_note}</div>}
      {checks.length > 0 && <ul className="ob-reasons">{cur.verification.reasons.map((r, i) => <li key={i}>{r}</li>)}</ul>}
      <Alert type={msg.type}>{msg.text}</Alert>
      <div className="ob-actions">
        {(!cur || cur.can_replace) && <label className="btn small" style={{ cursor: busy ? 'wait' : 'pointer' }}>{busy ? 'Uploading...' : cur ? 'Upload a new version' : 'Upload'}
          <input type="file" hidden accept=".pdf,.jpg,.jpeg,.png,.webp,application/pdf,image/*" disabled={busy} onChange={pick} aria-label={`Upload ${item.label}`} /></label>}
        {cur && <Button variant="secondary" className="small" onClick={open}>Download my copy</Button>}
      </div>
    </div>
  );
}

function Documents({ onChanged }) {
  const { data, loading, error, reload } = useFetch('/zeroq/my/requirements');
  if (loading && !data) return <Loading />;
  if (error && !data) return <ErrorState error={error} onRetry={reload} />;
  const items = [...data.requirements, data.kjsea];
  return (
    <div className="card stack">
      <h2 style={{ margin: 0 }}>Documents</h2>
      {!data.configured && <Alert>Your school has not listed required documents in ZeroQ yet. You can still upload your KJSEA results slip.</Alert>}
      <p className="ob-guide" style={{ margin: 0 }}>Accepted: PDF, JPEG, PNG or WebP up to {data.max_mb} MB. If a form must be signed, print it, fill it in by hand with ink, sign where required, then scan or photograph every page clearly and upload it. We check that the file opens and is readable; a reviewer at your school decides whether it is accepted.</p>
      {items.map((it) => <DocRow key={it.doc_type} item={it} onUploaded={() => { reload(); onChanged(); }} />)}
    </div>
  );
}

function Notifications({ refreshKey }) {
  const { data, meta, reload } = useFetch(`/zeroq/my/notifications?per_page=8&k=${refreshKey}`);
  const markRead = async () => { await api.post('/zeroq/my/notifications/read'); reload(); };
  return (
    <div className="card stack">
      <div className="row between wrap"><h2 style={{ margin: 0 }}>Updates</h2>{meta && meta.unread > 0 && <Button variant="secondary" className="small" onClick={markRead}>Mark {meta.unread} as read</Button>}</div>
      {!data || data.length === 0 ? <Empty title="No updates yet" /> : (
        <ul className="ob-timeline">{data.map((n) => <li key={n.id}><b style={{ fontWeight: n.read ? 400 : 700 }}>{n.title}</b>{n.body && <span className="muted small"> {n.body}</span>}<small>{fmtDate(n.created_at)}</small></li>)}</ul>
      )}
    </div>
  );
}

export default function Onboarding() {
  const progress = useFetch('/zeroq/my/progress');
  const [tick, setTick] = useState(0);
  const changed = () => { progress.reload(); setTick((t) => t + 1); };
  if (progress.loading && !progress.data) return <Loading label="Loading your admission progress" />;
  if (progress.error && !progress.data) return <ErrorState error={progress.error} onRetry={progress.reload} />;
  return (
    <section className="stack">
      <div><span className="small muted">ZEROQ</span><h1>Admission progress</h1></div>
      <Progress data={progress.data} />
      <Results onChanged={changed} />
      <Documents onChanged={changed} />
      <Notifications refreshKey={tick} />
    </section>
  );
}
