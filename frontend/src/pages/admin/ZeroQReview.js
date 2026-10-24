import { useState } from 'react';
import { useFetch } from '../../hooks/useFetch';
import { api, API_BASE } from '../../services/api';
import { Alert, Button, Empty, ErrorState, Field, Loading, Modal } from '../../components/ui';
import { fmtDate } from '../../utils/format';
import '../onboarding.css';

const DOC_TONE = { approved: 'green', passed_automated_checks: 'blue', human_review_required: 'warning', additional_information_required: '', rejected: 'red' };
const RES_TONE = { verified: 'green', awaiting_verification: 'warning', verification_in_progress: 'blue', additional_information_required: '', rejected: 'red', verification_failed: 'red' };
const CHECK_LABEL = { passed: 'Passed', failed: 'Failed', warning: 'Check this', info: 'Info' };

function Timeline({ items }) {
  return <ul className="ob-timeline">{items.map((h, i) => (
    <li key={i}>{h.to_label || h.to || h.action.replace(/_/g, ' ')}<small>{h.by} · {fmtDate(h.at)}{h.note ? ` · ${h.note}` : ''}</small></li>))}</ul>;
}

function DocumentDetail({ id, onClose, onChanged }) {
  const { data, loading, error, reload } = useFetch(`/zeroq/review/documents/${id}`);
  const [note, setNote] = useState('');
  const [msg, setMsg] = useState({});
  const [busy, setBusy] = useState(false);
  const act = async (action) => {
    setBusy(true); setMsg({});
    try { await api.post(`/zeroq/review/documents/${id}/action`, { action, note }); setNote(''); setMsg({ type: 'success', text: 'Recorded.' }); reload(); onChanged(); }
    catch (e) { setMsg({ type: 'error', text: e.message }); } finally { setBusy(false); }
  };
  const open = async () => {
    try { const r = await api.post(`/zeroq/review/documents/${id}/link`); window.location.assign(`${API_BASE}${r.data.path}`); }
    catch (e) { setMsg({ type: 'error', text: e.message }); }
  };
  return (
    <Modal wide title={data ? `${data.label}: ${data.student}` : 'Document'} onClose={onClose}>
      {loading && !data ? <Loading /> : error && !data ? <ErrorState error={error} onRetry={reload} /> : (
        <div className="stack">
          <div className="row between wrap"><span className="small muted">{data.application_reference} · version {data.version} · {data.file_name}</span>
            <span className="row" style={{ gap: '.4rem' }}>{data.escalated && <span className="badge red">Escalated</span>}<span className={`badge ${DOC_TONE[data.status] || ''}`}>{data.status_label}</span></span></div>
          {data.reasons.length > 0 && <Alert type="error">{data.reasons.join(' ')}</Alert>}
          <div><b>Recommended next step</b><div className="muted small">{data.verification.recommended_action}</div></div>
          <div><b>Automated checks that ran</b>
            {data.verification.checks.map((c) => <div className="ob-check" key={c.id}><span className={`badge ${c.status === 'passed' ? 'green' : c.status === 'failed' ? 'red' : c.status === 'warning' ? 'warning' : ''}`}>{CHECK_LABEL[c.status]}</span><span><b>{c.label}</b><br /><span className="muted">{c.detail}</span></span></div>)}</div>
          <div><b>Not checked automatically</b><div className="small muted">These need your judgment. Passing the checks above does not mean the document is genuine or complete.</div>
            <ul className="ob-reasons">{data.verification.not_performed.map((n) => <li key={n.id}>{n.label}</li>)}</ul></div>
          <div className="ob-actions"><Button variant="secondary" className="small" onClick={open}>Open the file</Button></div>
          {data.versions.length > 1 && <div className="small muted">Earlier versions: {data.versions.filter((v) => v.id !== data.id).map((v) => `v${v.version} (${v.status.replace(/_/g, ' ')})`).join(', ')}</div>}
          <div><b>History</b><Timeline items={data.history} /></div>
          <Alert type={msg.type}>{msg.text}</Alert>
          <Field as="textarea" label="Note to the student, or an internal note" name="doc-note" rows={3} value={note} onChange={(e) => setNote(e.target.value)} />
          <div className="ob-actions">
            <Button onClick={() => act('approve')} loading={busy}>Approve</Button>
            <Button variant="secondary" onClick={() => act('request_correction')} loading={busy} disabled={!note.trim()}>Request correction</Button>
            <Button variant="secondary" onClick={() => act('reject')} loading={busy} disabled={!note.trim()}>Reject</Button>
            <Button variant="secondary" onClick={() => act('escalate')} loading={busy} disabled={!note.trim()}>Escalate</Button>
            <Button variant="secondary" onClick={() => act('note')} loading={busy} disabled={!note.trim()}>Add note only</Button>
          </div>
          <div className="small muted">Correction, rejection, escalation and notes need a written reason. The student is told about corrections, rejections and approvals.</div>
        </div>
      )}
    </Modal>
  );
}

function Documents({ onChanged }) {
  const [status, setStatus] = useState('needs_action');
  const [q, setQ] = useState('');
  const [openId, setOpenId] = useState(null);
  const list = useFetch(`/zeroq/review/documents?status=${status}${q ? `&q=${encodeURIComponent(q)}` : ''}`);
  return (
    <div className="stack">
      <div className="row wrap" style={{ gap: '.75rem' }}>
        <Field as="select" label="Show" name="doc-filter" value={status} onChange={(e) => setStatus(e.target.value)} options={[
          { value: 'needs_action', label: 'Needs a decision' }, { value: 'all', label: 'Everything' }, { value: 'additional_information_required', label: 'Waiting for a correction' },
          { value: 'approved', label: 'Approved' }, { value: 'rejected', label: 'Rejected' }]} />
        <Field label="Search student or reference" name="doc-search" value={q} onChange={(e) => setQ(e.target.value)} />
      </div>
      {list.loading && !list.data ? <Loading /> : list.error ? <ErrorState error={list.error} onRetry={list.reload} /> : list.data.length === 0 ? <div className="card"><Empty title="Nothing here" /></div> : (
        <div className="list">{list.data.map((d) => (
          <div key={d.id} className="list-row">
            <div className="grow"><b>{d.student}</b><div className="small muted">{d.label} · v{d.version} · {d.application_reference} · {fmtDate(d.uploaded_at)}</div>
              {d.reasons.length > 0 && <div className="small" style={{ color: 'var(--warning)' }}>{d.reasons[0]}</div>}</div>
            {d.escalated && <span className="badge red">Escalated</span>}
            <span className={`badge ${DOC_TONE[d.status] || ''}`}>{d.status_label}</span>
            <Button variant="secondary" className="small" onClick={() => setOpenId(d.id)}>Review</Button>
          </div>))}</div>
      )}
      {openId && <DocumentDetail id={openId} onClose={() => { setOpenId(null); list.reload(); }} onChanged={() => { list.reload(); onChanged(); }} />}
    </div>
  );
}

function ResultDetail({ id, onClose, onChanged }) {
  const { data, loading, error, reload } = useFetch(`/zeroq/review/results/${id}`);
  const [note, setNote] = useState('');
  const [basis, setBasis] = useState('');
  const [msg, setMsg] = useState({});
  const [busy, setBusy] = useState(false);
  const act = async (action) => {
    setBusy(true); setMsg({});
    try { await api.post(`/zeroq/review/results/${id}/action`, { action, note, basis }); setNote(''); setMsg({ type: 'success', text: 'Recorded.' }); reload(); onChanged(); }
    catch (e) { setMsg({ type: 'error', text: e.message }); } finally { setBusy(false); }
  };
  return (
    <Modal wide title={data ? `KJSEA ${data.assessment_year}: ${data.student}` : 'Results'} onClose={onClose}>
      {loading && !data ? <Loading /> : error && !data ? <ErrorState error={error} onRetry={reload} /> : (
        <div className="stack">
          <div className="row between wrap"><span className="small muted">Candidate number {data.candidate_number} · {data.student_phone}</span><span className={`badge ${RES_TONE[data.status] || ''}`}>{data.status_label}</span></div>
          {data.flags.map((f, i) => <Alert key={i} type="error">{f}</Alert>)}
          <div className="small muted">These are the results the student entered. Compare them with the results document or an official source before verifying.</div>
          <div className="table-wrap"><table><thead><tr><th>Subject</th><th>Result</th></tr></thead><tbody>{data.subjects.map((s, i) => <tr key={i}><td>{s.subject}</td><td>{s.result}</td></tr>)}</tbody></table></div>
          <div><b>History</b><Timeline items={data.history} /></div>
          <Alert type={msg.type}>{msg.text}</Alert>
          <Field as="textarea" label="Note to the student" name="res-note" rows={2} value={note} onChange={(e) => setNote(e.target.value)} />
          <Field label="What did you check these against? (required to verify)" name="res-basis" maxLength={200} value={basis} onChange={(e) => setBasis(e.target.value)} />
          <div className="ob-actions">
            <Button variant="secondary" onClick={() => act('start_review')} loading={busy}>Start review</Button>
            <Button onClick={() => act('verify')} loading={busy} disabled={!basis.trim()}>Verify</Button>
            <Button variant="secondary" onClick={() => act('request_info')} loading={busy} disabled={!note.trim()}>Ask for more information</Button>
            <Button variant="secondary" onClick={() => act('fail')} loading={busy} disabled={!note.trim()}>Could not verify</Button>
            <Button variant="secondary" onClick={() => act('reject')} loading={busy} disabled={!note.trim()}>Reject</Button>
          </div>
          <div className="small muted">Verifying records that you checked the results yourself. It tells the student their school checked them. It is not an official placement.</div>
        </div>
      )}
    </Modal>
  );
}

function Results({ onChanged }) {
  const [status, setStatus] = useState('needs_action');
  const [openId, setOpenId] = useState(null);
  const list = useFetch(`/zeroq/review/results?status=${status}`);
  return (
    <div className="stack">
      <Field as="select" label="Show" name="res-filter" value={status} onChange={(e) => setStatus(e.target.value)} options={[
        { value: 'needs_action', label: 'Needs a decision' }, { value: 'all', label: 'Everything' }, { value: 'verified', label: 'Verified' },
        { value: 'additional_information_required', label: 'Waiting for the student' }, { value: 'rejected', label: 'Rejected' }]} />
      {list.loading && !list.data ? <Loading /> : list.error ? <ErrorState error={list.error} onRetry={list.reload} /> : list.data.length === 0 ? <div className="card"><Empty title="Nothing here" /></div> : (
        <div className="list">{list.data.map((r) => (
          <div key={r.id} className="list-row">
            <div className="grow"><b>{r.student}</b><div className="small muted">KJSEA {r.assessment_year} · {r.candidate_number} · {r.subjects.length} subjects · submitted {fmtDate(r.submitted_at)}</div>
              {r.flags.length > 0 && <div className="small" style={{ color: 'var(--red)' }}>{r.flags[0]}</div>}</div>
            <span className={`badge ${RES_TONE[r.status] || ''}`}>{r.status_label}</span>
            <Button variant="secondary" className="small" onClick={() => setOpenId(r.id)}>Review</Button>
          </div>))}</div>
      )}
      {openId && <ResultDetail id={openId} onClose={() => { setOpenId(null); list.reload(); }} onChanged={() => { list.reload(); onChanged(); }} />}
    </div>
  );
}

function PassRules() {
  const { data, reload } = useFetch('/zeroq/settings');
  const [msg, setMsg] = useState({});
  const set = async (key, value) => {
    setMsg({});
    try { await api.patch('/zeroq/settings', { [key]: value }); reload(); setMsg({ type: 'success', text: 'Saved.' }); }
    catch (e) { setMsg({ type: 'error', text: e.message }); }
  };
  if (!data) return null;
  return (
    <div className="card stack">
      <h3 style={{ margin: 0 }}>When a student can get a ZeroQ pass</h3>
      <p className="muted small" style={{ margin: 0 }}>A pass is issued only after you have approved the admission and the checks below are met. Automated file checks never count: a person must verify or approve.</p>
      <Alert type={msg.type}>{msg.text}</Alert>
      <label className="row" style={{ gap: '.6rem', alignItems: 'flex-start' }}>
        <input type="checkbox" checked={data.require_verified_results} onChange={(e) => set('require_verified_results', e.target.checked)} />
        <span>KJSEA results verified by the school<br /><span className="small muted">Turn this off for grades whose students do not sit the KJSEA.</span></span>
      </label>
      <label className="row" style={{ gap: '.6rem', alignItems: 'flex-start' }}>
        <input type="checkbox" checked={data.require_approved_documents} onChange={(e) => set('require_approved_documents', e.target.checked)} />
        <span>Every required document approved<br /><span className="small muted">Only documents marked required below count. Optional ones never block a pass.</span></span>
      </label>
    </div>
  );
}

function Requirements() {
  const list = useFetch('/zeroq/requirements');
  const [f, setF] = useState({ doc_type: '', label: '', instructions: '', required: true });
  const [errs, setErrs] = useState({});
  const [msg, setMsg] = useState({});
  const add = async () => {
    setErrs({}); setMsg({});
    try { await api.post('/zeroq/requirements', f); setF({ doc_type: '', label: '', instructions: '', required: true }); list.reload(); }
    catch (e) { setErrs(e.errors || {}); setMsg({ type: 'error', text: e.message }); }
  };
  const patch = async (r, body) => { setMsg({}); try { await api.patch(`/zeroq/requirements/${r.id}`, body); list.reload(); } catch (e) { setMsg({ type: 'error', text: e.message }); } };
  return (
    <div className="stack">
      <PassRules />
      <p className="muted small" style={{ margin: 0 }}>The documents your students are asked to upload. Use the official forms your school issues; ZeroQ does not supply forms.</p>
      <Alert type={msg.type}>{msg.text}</Alert>
      {list.loading && !list.data ? <Loading /> : list.error ? <ErrorState error={list.error} onRetry={list.reload} /> : list.data.length === 0 ? <div className="card"><Empty title="No documents listed yet" /></div> : (
        <div className="list">{list.data.map((r) => (
          <div key={r.id} className="list-row">
            <div className="grow"><b>{r.label}</b><div className="small muted">{r.doc_type}{r.instructions ? ` · ${r.instructions}` : ''}</div></div>
            <span className={`badge ${r.is_active ? 'green' : ''}`}>{r.is_active ? (r.required ? 'Required' : 'Optional') : 'Hidden'}</span>
            <Button variant="secondary" className="small" onClick={() => patch(r, { required: !r.required })}>{r.required ? 'Make optional' : 'Make required'}</Button>
            <Button variant="secondary" className="small" onClick={() => patch(r, { is_active: !r.is_active })}>{r.is_active ? 'Hide' : 'Show'}</Button>
          </div>))}</div>
      )}
      <div className="card stack">
        <h3 style={{ margin: 0 }}>Add a document</h3>
        <Field label="Name students see" name="req-label" value={f.label} onChange={(e) => setF({ ...f, label: e.target.value })} error={errs.label} />
        <Field label="Short code (lowercase letters, numbers, underscores)" name="req-code" value={f.doc_type} onChange={(e) => setF({ ...f, doc_type: e.target.value })} error={errs.doc_type} />
        <Field as="textarea" label="Instructions for the student (optional)" name="req-instructions" rows={2} value={f.instructions} onChange={(e) => setF({ ...f, instructions: e.target.value })} error={errs.instructions} />
        <label className="row" style={{ gap: '.5rem' }}><input type="checkbox" checked={f.required} onChange={(e) => setF({ ...f, required: e.target.checked })} /> Required for admission</label>
        <div><Button onClick={add} disabled={!f.label.trim() || !f.doc_type.trim()}>Add document</Button></div>
      </div>
    </div>
  );
}

export default function ZeroQReview() {
  const summary = useFetch('/zeroq/review/summary');
  const [tab, setTab] = useState('documents');
  const s = summary.data;
  return (
    <section className="stack">
      <div><span className="small muted">ZEROQ</span><h1>Document and results review</h1></div>
      {s && (
        <div className="ob-tiles">
          <div><b>{s.documents.human_review_required}</b><span>Documents flagged for a person</span></div>
          <div><b>{s.documents.passed_automated_checks}</b><span>Passed checks, awaiting approval</span></div>
          <div><b>{s.documents.corrections_outstanding}</b><span>Corrections outstanding</span></div>
          <div><b>{s.results.awaiting_verification + s.results.verification_in_progress}</b><span>Results to verify</span></div>
        </div>
      )}
      <div className="ob-tabs" role="tablist">
        {[['documents', 'Documents'], ['results', 'KJSEA results'], ['requirements', 'Required documents']].map(([k, label]) => (
          <button key={k} role="tab" aria-selected={tab === k} className={tab === k ? 'on' : ''} onClick={() => setTab(k)}>{label}</button>))}
      </div>
      {tab === 'documents' && <Documents onChanged={summary.reload} />}
      {tab === 'results' && <Results onChanged={summary.reload} />}
      {tab === 'requirements' && <Requirements />}
    </section>
  );
}
