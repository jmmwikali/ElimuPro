import { useState } from 'react';
import { useFetch } from '../../hooks/useFetch';
import { api } from '../../services/api';
import { Alert, Button, Empty, ErrorState, Field, Loading, Modal, Pager } from '../../components/ui';
import { fmtDate, money } from '../../utils/format';

const TONE = { paid: 'green', unpaid: 'warning', void: '' };
const WITH_QUANTITY = ['per_admission', 'per_transfer', 'per_student_year'];
const BLANK = { school_id: '', component_key: '', quantity: '1', reference: '' };

export default function Invoices() {
  const [page, setPage] = useState(1);
  const list = useFetch(`/billing/invoices?page=${page}`);
  const schools = useFetch('/schools');
  const prices = useFetch('/pricing');
  const [open, setOpen] = useState(false);
  const [f, setF] = useState(BLANK);
  const [errs, setErrs] = useState({});
  const [msg, setMsg] = useState({});
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });

  // Apex AI Pro is priced in USD, which M-Pesa cannot take, so only KES components can be invoiced.
  const components = (prices.data || []).filter((c) => c.currency === 'KES' && c.is_active);
  const chosen = components.find((c) => c.key === f.component_key);
  const needsQty = chosen && WITH_QUANTITY.includes(chosen.billing_unit);

  const create = async () => {
    setBusy(true); setErrs({}); setMsg({});
    try {
      await api.post('/billing/invoices', { school_id: Number(f.school_id), component_key: f.component_key, quantity: needsQty ? Number(f.quantity) : 1, reference: f.reference });
      setOpen(false); setF(BLANK); setMsg({ type: 'success', text: 'Invoice issued.' }); list.reload();
    } catch (e) { setErrs(e.errors || {}); setMsg({ type: 'error', text: e.message }); } finally { setBusy(false); }
  };
  const act = async (inv, what) => {
    setMsg({});
    try { await api.post(`/billing/invoices/${inv.id}/${what}`); list.reload(); } catch (e) { setMsg({ type: 'error', text: e.message }); }
  };

  if (list.loading && !list.data) return <Loading />;
  if (list.error && !list.data) return <ErrorState error={list.error} onRetry={list.reload} />;
  return (
    <div className="stack">
      <div className="row between wrap"><h1>Invoices</h1><Button onClick={() => { setMsg({}); setOpen(true); }}>Issue invoice</Button></div>
      <Alert type={open ? undefined : msg.type}>{open ? '' : msg.text}</Alert>
      {list.data.length === 0 ? <div className="card"><Empty title="No invoices yet" /></div> : (
        <><div className="list">{list.data.map((inv) => (
          <div key={inv.id} className="list-row">
            <div className="grow"><b>{inv.school}</b><div className="small muted">{inv.description} · {inv.number} · {fmtDate(inv.created_at)}</div></div>
            <div className="right"><b>{money(inv.amount)}</b><div><span className={`badge ${TONE[inv.status] || ''}`}>{inv.status}</span></div></div>
            {inv.status === 'unpaid' && <>
              {inv.attempt && inv.attempt.status === 'pending' && <Button variant="secondary" className="small" onClick={() => act(inv, 'refresh')}>Check status</Button>}
              <Button variant="secondary" className="small" onClick={() => act(inv, 'void')}>Void</Button></>}
          </div>))}</div><Pager meta={list.meta} onPage={setPage} /></>
      )}
      {open && (
        <Modal title="Issue invoice" onClose={() => setOpen(false)}>
          <Alert type="error">{msg.type === 'error' ? msg.text : ''}</Alert>
          <Field as="select" label="School" name="school_id" required value={f.school_id} onChange={set('school_id')} error={errs.school_id}
            options={(schools.data || []).map((s) => ({ value: s.id, label: s.name }))} />
          <Field as="select" label="Component" name="component_key" required value={f.component_key} onChange={set('component_key')} error={errs.component_key}
            options={components.map((c) => ({ value: c.key, label: c.name }))} />
          {needsQty && <Field label={`Quantity (${chosen.billing_label})`} name="quantity" type="number" min="1" step="1" required value={f.quantity} onChange={set('quantity')} error={errs.quantity} />}
          <Field label="Billing period or batch (e.g. Term 2 2026)" name="reference" required maxLength={60} value={f.reference} onChange={set('reference')} error={errs.reference} />
          <p className="small muted">The price is set from the Pricing page when you issue the invoice, based on the school&apos;s current number of active students. A school cannot be invoiced twice for the same component and period.</p>
          <Button block onClick={create} loading={busy} disabled={!f.school_id || !f.component_key || !f.reference}>Issue invoice</Button>
        </Modal>
      )}
    </div>
  );
}
