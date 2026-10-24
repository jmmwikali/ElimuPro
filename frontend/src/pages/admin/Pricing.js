import { useState } from 'react';
import { useFetch } from '../../hooks/useFetch';
import { api } from '../../services/api';
import { Alert, Button, ErrorState, Field, Loading } from '../../components/ui';
import { BRAND } from '../../config/brand';

const symbol = (cur) => (cur === 'KES' ? 'KSh' : cur);
const show = (v) => (v === null || v === undefined ? '' : String(v));

function PriceCard({ c, onSaved }) {
  const [active, setActive] = useState(c.is_active);
  const [amount, setAmount] = useState(show(c.amount));
  const [description, setDescription] = useState(c.description || '');
  const [tiers, setTiers] = useState(c.tiers.map((t) => ({ up_to: show(t.up_to_students), amount: show(t.amount) })));
  const [errs, setErrs] = useState({});
  const [msg, setMsg] = useState({});
  const [busy, setBusy] = useState(false);
  const tiered = c.tiers.length > 0;

  const setTier = (i, k, v) => setTiers(tiers.map((t, j) => (j === i ? { ...t, [k]: v } : t)));
  const addTier = () => setTiers([...tiers.slice(0, -1), { up_to: '', amount: '' }, tiers[tiers.length - 1]]);
  const removeTier = (i) => setTiers(tiers.filter((_, j) => j !== i));

  const save = async () => {
    setBusy(true); setErrs({}); setMsg({});
    const body = { is_active: active, description };
    if (tiered) {
      body.tiers = tiers.map((t, i) => ({
        up_to_students: i === tiers.length - 1 ? null : (t.up_to === '' ? null : Number(t.up_to)),
        amount: t.amount,
      }));
    } else {
      body.amount = amount;
    }
    try {
      await api.put(`/pricing/${c.key}`, body);
      setMsg({ type: 'success', text: 'Saved. New prices apply immediately.' });
      onSaved();
    } catch (e) {
      setErrs(e.errors || {});
      setMsg({ type: 'error', text: e.message });
    } finally { setBusy(false); }
  };

  return (
    <div className="card stack">
      <div className="row between wrap">
        <div><h2 style={{ margin: 0 }}>{c.name}</h2><div className="small muted">Billed {c.billing_label} · {symbol(c.currency)}</div></div>
        <label className="row" style={{ gap: '.5rem' }}>
          <input type="checkbox" checked={active} onChange={(e) => setActive(e.target.checked)} /> On sale
        </label>
      </div>
      {tiered ? (
        <div className="stack">
          {tiers.map((t, i) => {
            const last = i === tiers.length - 1;
            const floor = i === 0 ? 0 : Number(tiers[i - 1].up_to) || 0;
            return (
              <div key={i} className="row wrap" style={{ gap: '.75rem', alignItems: 'flex-end' }}>
                {last
                  ? <div className="grow small">Schools with more than <b>{floor.toLocaleString()}</b> students</div>
                  : <Field label={i === 0 ? 'Schools with up to (including)' : 'Up to (including)'} name={`${c.key}-up-${i}`} type="number" min="1" value={t.up_to} onChange={(e) => setTier(i, 'up_to', e.target.value)} />}
                <Field label={`Price (${symbol(c.currency)})`} name={`${c.key}-amt-${i}`} type="number" min="0" step="0.01" value={t.amount} onChange={(e) => setTier(i, 'amount', e.target.value)} />
                {!last && tiers.length > 2 && <Button variant="secondary" className="small" onClick={() => removeTier(i)}>Remove</Button>}
              </div>
            );
          })}
          {tiers.length < 6 && <div><Button variant="secondary" className="small" onClick={addTier}>Add a size band</Button></div>}
          <div className="small muted">A school with exactly the limit pays that band&apos;s price. The last band covers every larger school.</div>
          {errs.tiers && <div className="err" role="alert">{errs.tiers}</div>}
        </div>
      ) : (
        <Field label={`Price (${symbol(c.currency)})`} name={`${c.key}-amount`} type="number" min="0" step="0.01" value={amount} onChange={(e) => setAmount(e.target.value)} error={errs.amount} />
      )}
      <Field as="textarea" label="Internal note (optional)" name={`${c.key}-desc`} rows={2} maxLength={500} value={description} onChange={(e) => setDescription(e.target.value)} error={errs.description} />
      <Alert type={msg.type}>{msg.text}</Alert>
      <div className="row between wrap">
        <span className="small muted">{c.updated_at ? `Last changed ${new Date(c.updated_at).toLocaleString('en-KE')}` : 'Launch default, never edited'}</span>
        <Button onClick={save} loading={busy}>Save {c.name}</Button>
      </div>
    </div>
  );
}

export default function Pricing() {
  const { data, loading, error, reload } = useFetch('/pricing');
  if (loading && !data) return <Loading />;
  if (error && !data) return <ErrorState error={error} onRetry={reload} />;
  return (
    <div className="stack">
      <h1>Pricing</h1>
      <p className="muted">Prices for each {BRAND.name} component. Changes apply to new quotes and to what Apex AI tells customers. Every change is recorded in the audit log.</p>
      {data.map((c) => <PriceCard key={c.key} c={c} onSaved={reload} />)}
    </div>
  );
}
