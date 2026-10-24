import { STATUS } from '../utils/format';

export const Spinner = () => <div className="spinner" role="status" aria-label="Loading" />;

export function Loading({ label }) {
  return <div><Spinner />{label && <p className="muted" style={{ textAlign: 'center' }}>{label}</p>}</div>;
}

export function ErrorState({ error, onRetry }) {
  return (
    <div className="alert error" role="alert">
      <strong>{error?.status === 403 ? 'Access denied' : 'Could not load this page'}</strong>
      <div>{error?.message || 'Something went wrong.'}</div>
      {onRetry && error?.status !== 403 && <button className="btn secondary small" style={{ marginTop: '.5rem' }} onClick={onRetry}>Try again</button>}
    </div>
  );
}

export const Empty = ({ title, children }) => (
  <div className="empty"><h3>{title}</h3>{children && <p>{children}</p>}</div>
);

export const Alert = ({ type = 'info', children }) => (children ? <div className={`alert ${type}`} role={type === 'error' ? 'alert' : 'status'}>{children}</div> : null);

export function Button({ loading, children, variant = '', block, ...rest }) {
  return (
    <button className={`btn ${variant} ${block ? 'block' : ''}`} disabled={loading || rest.disabled} {...rest}>
      {loading ? 'Please wait...' : children}
    </button>
  );
}

export function Field({ label, error, required, as = 'input', options, children, ...rest }) {
  const id = rest.name || label;
  const cls = `input ${error ? 'invalid' : ''}`;
  let control;
  if (as === 'select') {
    control = (
      <select id={id} className={cls} aria-invalid={!!error} {...rest}>
        <option value="">Select...</option>
        {(options || []).map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
    );
  } else if (as === 'textarea') {
    control = <textarea id={id} className={cls} aria-invalid={!!error} {...rest} />;
  } else {
    control = <input id={id} className={cls} aria-invalid={!!error} {...rest} />;
  }
  return (
    <label className="field" htmlFor={id}>
      <span>{label}{required && <b className="req" aria-hidden="true">*</b>}</span>
      {control}{children}
      {error && <div className="err" role="alert">{error}</div>}
    </label>
  );
}

export const StatusBadge = ({ status }) => {
  const [label, tone] = STATUS[status] || [status, ''];
  return <span className={`badge ${tone}`}>{label}</span>;
};

export function Modal({ title, onClose, children, wide }) {
  return (
    <div className="overlay" onClick={onClose} role="presentation">
      <div className={`modal${wide ? ' wide' : ''}`} role="dialog" aria-modal="true" aria-label={title} onClick={(e) => e.stopPropagation()}>
        <div className="row between"><h2>{title}</h2><button className="icon-btn" aria-label="Close" onClick={onClose}>✕</button></div>
        {children}
      </div>
    </div>
  );
}

export function Pager({ meta, onPage }) {
  if (!meta || meta.pages <= 1) return null;
  return (
    <div className="row between" style={{ marginTop: '.75rem' }}>
      <button className="btn secondary small" disabled={meta.page <= 1} onClick={() => onPage(meta.page - 1)}>Previous</button>
      <span className="muted small">Page {meta.page} of {meta.pages}</span>
      <button className="btn secondary small" disabled={meta.page >= meta.pages} onClick={() => onPage(meta.page + 1)}>Next</button>
    </div>
  );
}
