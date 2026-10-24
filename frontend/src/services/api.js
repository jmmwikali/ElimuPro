// Centralised API client. The base URL comes from REACT_APP_API_URL (see .env.example).
const BASE = (process.env.REACT_APP_API_URL || 'http://localhost:5000/api/v1').replace(/\/$/, '');
export const API_BASE = BASE;
const TOKEN_KEY = 'elimupro_token'; // only the auth token is kept client-side; all data lives in the database

export class ApiError extends Error {
  constructor(message, status, errors) {
    super(message);
    this.status = status;
    this.errors = errors || {};
  }
}

export const tokenStore = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (t) => localStorage.setItem(TOKEN_KEY, t),
  clear: () => localStorage.removeItem(TOKEN_KEY),
};

async function request(path, { method = 'GET', body } = {}) {
  const isForm = typeof FormData !== 'undefined' && body instanceof FormData; // the browser sets the multipart boundary
  const headers = isForm ? {} : { 'Content-Type': 'application/json' };
  const token = tokenStore.get();
  if (token) headers.Authorization = `Bearer ${token}`;
  let res;
  try {
    res = await fetch(`${BASE}${path}`, { method, headers, body: body ? (isForm ? body : JSON.stringify(body)) : undefined });
  } catch (e) {
    throw new ApiError('Cannot reach the server. Check your internet connection and try again.', 0);
  }
  let json = null;
  try { json = await res.json(); } catch (e) { /* non-JSON error */ }
  if (!res.ok || !json || json.success === false) {
    if (res.status === 401 && token) window.dispatchEvent(new Event('elimupro:unauthorized'));
    throw new ApiError((json && json.message) || 'Something went wrong. Please try again.', res.status, json && json.errors);
  }
  return json;
}

export const api = {
  get: (p) => request(p),
  post: (p, body) => request(p, { method: 'POST', body: body || {} }),
  put: (p, body) => request(p, { method: 'PUT', body }),
  patch: (p, body) => request(p, { method: 'PATCH', body }),
  delete: (p) => request(p, { method: 'DELETE' }),
  upload: (p, form) => request(p, { method: 'POST', body: form }),
};
