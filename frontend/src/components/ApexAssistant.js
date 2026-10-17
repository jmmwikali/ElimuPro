import { useEffect, useRef, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { api } from '../services/api';
import './apex.css';

// Apex AI customer care. The server owns the Gemini key and the knowledge for each component;
// the widget only sends the chosen component, the message and the recent conversation.
const ROUTE_COMPONENT = [
  [/zeroq/i, 'zeroq_admissions'], [/fees|finance/i, 'financial_analytics'],
  [/results|classes/i, 'academic_analytics'], [/career/i, 'careergps'],
];
const FALLBACK = [{ id: 'general', name: 'ElimuPro (general)' }];
// Components with their own brand mark show it in the chat.
const PUBLIC = process.env.PUBLIC_URL || '';
const BRANDS = {
  careergps: { mark: `${PUBLIC}/careergps-mark.png`, logo: `${PUBLIC}/careergps-logo.png`, alt: 'CareerGPS by ElimuPro' },
};

const guessComponent = (path) => (ROUTE_COMPONENT.find(([re]) => re.test(path)) || [null, 'general'])[1];

export default function ApexAssistant() {
  const { pathname } = useLocation();
  const [open, setOpen] = useState(false);
  const [components, setComponents] = useState(FALLBACK);
  const [component, setComponent] = useState(() => guessComponent(pathname));
  const [threads, setThreads] = useState({}); // one conversation per component
  const [text, setText] = useState('');
  const [sending, setSending] = useState(false);
  const [error, setError] = useState('');
  const logRef = useRef(null);

  useEffect(() => {
    if (!open) return;
    api.get('/apex/components').then((r) => setComponents(r.data.components)).catch(() => {});
  }, [open]);
  useEffect(() => { if (!open) setComponent(guessComponent(pathname)); }, [pathname, open]);

  const messages = threads[component] || [];
  const current = components.find((c) => c.id === component) || FALLBACK[0];
  const brand = BRANDS[component];

  useEffect(() => { logRef.current?.scrollTo(0, logRef.current.scrollHeight); }, [messages.length, sending]);

  const send = async (e) => {
    e.preventDefault();
    const message = text.trim();
    if (!message || sending) return;
    const history = messages;
    setThreads((t) => ({ ...t, [component]: [...history, { role: 'user', text: message }] }));
    setText(''); setError(''); setSending(true);
    try {
      const res = await api.post('/apex/chat', { component, message, history });
      setThreads((t) => ({ ...t, [component]: [...(t[component] || []), { role: 'assistant', text: res.data.reply }] }));
    } catch (err) {
      setError(err.message);
    } finally { setSending(false); }
  };

  if (!open) {
    return (
      <button className="apex-launch" onClick={() => setOpen(true)} aria-label="Open Apex AI customer care">
        <span className="apex-dot" aria-hidden="true">A</span><span>Ask Apex AI</span>
      </button>
    );
  }

  return (
    <section className="apex-panel" role="dialog" aria-label="Apex AI customer care">
      <header className="apex-head">
        <div className="apex-title">
          {brand && <img className="apex-mark" src={brand.mark} alt="" />}
          <div><strong>Apex AI</strong><small>{brand ? `${current.name} customer care` : 'Customer care'}</small></div>
        </div>
        <button className="apex-close" onClick={() => setOpen(false)} aria-label="Close Apex AI">×</button>
      </header>
      <label className="apex-topic">
        <span>Help with</span>
        <select className="input" value={component} onChange={(e) => { setComponent(e.target.value); setError(''); }}>
          {components.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
      </label>
      <div className="apex-log" ref={logRef} aria-live="polite">
        {messages.length === 0 && brand && <img className="apex-logo" src={brand.logo} alt={brand.alt} />}
        {messages.length === 0 && (
          <p className="apex-msg assistant">Hi! I'm Apex AI. Ask me anything about {current.name}: pricing, how it works, or where to get help.</p>
        )}
        {messages.map((m, i) => <p key={i} className={`apex-msg ${m.role}`}>{m.text}</p>)}
        {sending && <p className="apex-msg assistant apex-typing">Apex is typing…</p>}
        {error && <p className="apex-error" role="alert">{error}</p>}
      </div>
      <form className="apex-form" onSubmit={send}>
        <input className="input" value={text} onChange={(e) => setText(e.target.value)} maxLength={1000}
               placeholder="Type your question…" aria-label="Your question" />
        <button className="btn small" disabled={sending || !text.trim()}>Send</button>
      </form>
      <p className="apex-note">Never share passwords, PINs or OTP codes. Apex AI cannot see or change your records.</p>
    </section>
  );
}
