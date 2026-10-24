import { useCallback, useEffect, useRef, useState } from 'react';
import { useFetch } from '../../hooks/useFetch';
import { api } from '../../services/api';
import { Alert, Button, Empty, ErrorState, Field, Loading, Modal, Pager } from '../../components/ui';
import { fmtDate, money } from '../../utils/format';
import { BRAND } from '../../config/brand';

const TONE = { paid: 'green', unpaid: 'warning', void: '' };
const POLL_MS = 5000;
const MAX_POLLS = 24; // about 2 minutes, then we stop asking and say so
const FAILED = { failed: 'The payment failed or was cancelled.', timeout: 'The prompt timed out before it was confirmed.', expired: 'The payment request expired.', amount_mismatch: `M-Pesa reported a different amount. Nothing was marked paid; please contact ${BRAND.name} support.` };

/* The invoice is only ever shown as paid because the SERVER says so (after Cyzora confirmed it),
   never because the prompt was sent or a screen said "success". */
function PayModal({ invoice, onClose, onChanged }) {
  const [phone, setPhone] = useState('');
  const [stage, setStage] = useState('form'); // form | waiting | paid | failed | slow
  const [msg, setMsg] = useState('');
  const [errs, setErrs] = useState({});
  const [busy, setBusy] = useState(false);
  const timer = useRef(null);
  const polls = useRef(0);

  const stop = () => { if (timer.current) { clearTimeout(timer.current); timer.current = null; } };
  useEffect(() => stop, []);

  const check = useCallback(async () => {
    try {
      const { data } = await api.post(`/billing/invoices/${invoice.id}/refresh`);
      if (data.status === 'paid') { setStage('paid'); onChanged(); return; }
      const state = data.attempt && data.attempt.status;
      if (FAILED[state]) { setMsg(FAILED[state]); setStage('failed'); onChanged(); return; }
    } catch (e) { /* keep waiting: a missed poll is harmless */ }
    polls.current += 1;
    if (polls.current >= MAX_POLLS) { setStage('slow'); return; }
    timer.current = setTimeout(check, POLL_MS);
  }, [invoice.id, onChanged]);

  const send = async () => {
    setBusy(true); setErrs({}); setMsg('');
    try {
      await api.post(`/billing/invoices/${invoice.id}/pay`, { phone });
      polls.current = 0; setStage('waiting'); timer.current = setTimeout(check, POLL_MS);
    } catch (e) { setErrs(e.errors || {}); setMsg(e.message); } finally { setBusy(false); }
  };

  return (
    <Modal title={`Pay ${invoice.number}`} onClose={() => { stop(); onClose(); }}>
      <p><b>{money(invoice.amount)}</b> for {invoice.description}</p>
      {stage === 'form' && (<>
        <Alert type="error">{msg}</Alert>
        <Field label="M-Pesa phone number" name="phone" type="tel" required placeholder="0712345678" value={phone} onChange={(e) => setPhone(e.target.value)} error={errs.phone} />
        <Button block onClick={send} loading={busy} disabled={!phone}>Send M-Pesa prompt</Button>
      </>)}
      {stage === 'waiting' && <Alert>Check your phone and enter your M-Pesa PIN. This page updates once M-Pesa confirms. Please keep it open.</Alert>}
      {stage === 'slow' && (<>
        <Alert>We have not heard back from M-Pesa yet. If you completed the payment, the invoice will update by itself once it is confirmed.</Alert>
        <Button block variant="secondary" onClick={() => { polls.current = 0; setStage('waiting'); check(); }}>Check again</Button>
      </>)}
      {stage === 'paid' && <Alert type="success">Payment confirmed. Thank you!</Alert>}
      {stage === 'failed' && (<><Alert type="error">{msg}</Alert><Button block onClick={() => { setStage('form'); setMsg(''); }}>Try again</Button></>)}
    </Modal>
  );
}

export default function Billing() {
  const [page, setPage] = useState(1);
  const { data, meta, loading, error, reload } = useFetch(`/billing/invoices?page=${page}`);
  const [paying, setPaying] = useState(null);
  const [note, setNote] = useState({});
  const check = async (inv) => {
    setNote({});
    try { await api.post(`/billing/invoices/${inv.id}/refresh`); reload(); } catch (e) { setNote({ type: 'error', text: e.message }); }
  };
  if (loading && !data) return <Loading />;
  if (error && !data) return <ErrorState error={error} onRetry={reload} />;
  return (
    <div className="stack">
      <h1>Billing</h1>
      <p className="muted">Invoices from {BRAND.name} for the components your school uses. Pay by M-Pesa; the invoice shows as paid once M-Pesa confirms it. This is separate from the school fees you collect from parents.</p>
      <Alert type={note.type}>{note.text}</Alert>
      {data.length === 0 ? <div className="card"><Empty title="No invoices yet" /></div> : (
        <><div className="list">{data.map((inv) => (
          <div key={inv.id} className="list-row">
            <div className="grow"><b>{inv.description}</b><div className="small muted">{inv.number} · issued {fmtDate(inv.created_at)}{inv.quantity > 1 ? ` · ${inv.quantity} × ${money(inv.unit_price)}` : ''}</div></div>
            <div className="right"><b>{money(inv.amount)}</b><div><span className={`badge ${TONE[inv.status] || ''}`}>{inv.status}</span></div></div>
            {inv.status === 'unpaid' && <>
              {inv.attempt && inv.attempt.status === 'pending' && <Button variant="secondary" className="small" onClick={() => check(inv)}>Check status</Button>}
              <Button className="small" onClick={() => setPaying(inv)}>Pay with M-Pesa</Button></>}
          </div>))}</div><Pager meta={meta} onPage={setPage} /></>
      )}
      {paying && <PayModal invoice={paying} onClose={() => { setPaying(null); reload(); }} onChanged={reload} />}
    </div>
  );
}
