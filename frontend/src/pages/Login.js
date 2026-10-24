import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth, homeFor } from '../context/AuthContext';
import { Alert, Button, Field } from '../components/ui';
import { BRAND } from '../config/brand';

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ email: '', password: '' });
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    if (!form.email || !form.password) return setError('Enter your email and password');
    setBusy(true); setError('');
    try {
      const user = await login(form.email.trim(), form.password);
      navigate(homeFor(user), { replace: true });
    } catch (err) { setError(err.message); } finally { setBusy(false); }
  };

  return (
    <>
    <h1>Welcome back</h1>
    <p className="muted">Log in to your {BRAND.name} account.</p>
    <Alert type="error">{error}</Alert>
    <form onSubmit={submit} noValidate>
      <Field label="Email" name="email" type="email" autoComplete="username" required value={form.email} onChange={set('email')} />
      <Field label="Password" name="password" type="password" autoComplete="current-password" required value={form.password} onChange={set('password')} />
      <Button block loading={busy} type="submit">Log in</Button>
    </form>
    <p className="small muted" style={{ marginTop: '1rem' }}>New student? <Link to="/signup">Create an account and apply</Link></p>
    </>
  );
}