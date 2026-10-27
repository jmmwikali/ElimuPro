import { useEffect, useRef, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { BRAND } from '../config/brand';
import './apex.css';

// Apex AI customer care. The server owns the Gemini key and the knowledge for each component;
// the widget only sends the chosen component, the message and the recent conversation.
const ROUTE_COMPONENT = [
  [/zeroq/i, 'zeroq_admissions'], [/fees|finance/i, 'financial_analytics'],
  [/results|classes/i, 'academic_analytics'], [/career/i, 'careergps'],
];
const FALLBACK = [{ id: 'general', name: `${BRAND.name} (general)` }];
// Components with their own brand mark show it in the chat.
const PUBLIC = process.env.PUBLIC_URL || '';
const BRANDS = {
  careergps: { mark: `${PUBLIC}/careergps-mark.png`, logo: `${PUBLIC}/careergps-logo.png`, alt: 'CareerGPS by ElimuNova' },
};

// Starter questions per role. Each one is answerable from what Apex AI knows, so a tap never ends in "I don't know".
const ADMIN_STARTERS = ['How does ZeroQ admissions work?', 'How do I review student applications?', 'What do the components cost?'];
const STARTERS = {
  student: ['Where can I see my results?', 'How does my ZeroQ admission pass work?', 'How do I pay school fees?'],
  parent: ["Where can I see my child's information?", 'How do I pay school fees?', 'I forgot my password'],
  teacher: ['How do I enter exam results?', 'Which sections can I use?', 'I forgot my password'],
  class_teacher: ['How do I enter exam results?', 'Which sections can I use?', 'I forgot my password'],
  school_admin: ADMIN_STARTERS, principal: ADMIN_STARTERS, deputy_principal: ADMIN_STARTERS,
  bursar: ['How are fee payments verified?', 'What does Financial Analytics cost?', 'I forgot my password'],
  super_admin: ['What are the current component prices?', 'What does Apex AI Pro cost?'],
  visitor: [`What is ${BRAND.name}?`, 'How do I sign up as a student?', 'What can my school buy?'],
};

const guessComponent = (path) => (ROUTE_COMPONENT.find(([re]) => re.test(path)) || [null, 'general'])[1];

export default function ApexAssistant() {
  const { pathname } = useLocation();
  const { user } = useAuth() || {};
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

  const sendMessage = async (raw) => {
    const message = raw.trim();
    if (!message || sending) return;
    const history = messages;
    setThreads((t) => ({ ...t, [component]: [...history, { role: 'user', text: message }] }));
    setText(''); setError(''); setSending(true);
    try {
      // `page` lets Apex AI tailor its answer to the screen the user is on; the server only accepts known pages.
      const res = await api.post('/apex/chat', { component, message, history, page: pathname });
      setThreads((t) => ({ ...t, [component]: [...(t[component] || []), { role: 'assistant', text: res.data.reply }] }));
    } catch (err) {
      setError(err.message);
    } finally { setSending(false); }
  };
  const send = (e) => { e.preventDefault(); sendMessage(text); };
  const firstName = (user?.first_name || '').trim().split(/\s+/)[0];
  const starters = STARTERS[user?.role] || STARTERS.visitor;

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
          <p className="apex-msg assistant">
            {firstName ? `Hi ${firstName}! ` : 'Hi! '}I'm Apex AI. Ask me anything about {current.name}, or tap a question below.
          </p>
        )}
        {messages.length === 0 && (
          <div className="apex-chips">
            {starters.map((q) => (
              <button key={q} type="button" className="apex-chip" disabled={sending} onClick={() => sendMessage(q)}>{q}</button>
            ))}
          </div>
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