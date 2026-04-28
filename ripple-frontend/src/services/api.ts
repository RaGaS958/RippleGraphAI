import axios from 'axios'

const BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8080/api/v1'

export const api = axios.create({ baseURL: BASE, timeout: 15_000 })

api.interceptors.request.use(cfg => {
  const token = localStorage.getItem('token')
  if (token) cfg.headers.Authorization = `Bearer ${token}`
  return cfg
})

api.interceptors.response.use(r => r, err => {
  const msg = err.response?.data?.detail ?? err.message
  return Promise.reject(new Error(msg))
})

// ── Auth ─────────────────────────────────────────────────────────────────────
export const authApi = {
  register: (email: string, password: string, name: string) =>
    api.post('/auth/register', { email, password, name }).then(r => r.data),
  login: (email: string, password: string) =>
    api.post('/auth/login', { email, password }).then(r => r.data),
  me: () => api.get('/auth/me').then(r => r.data),
}

// ── Graph ─────────────────────────────────────────────────────────────────────
export const graphApi = {
  get: () => api.get('/graph/').then(r => r.data),
}

// ── Suppliers ─────────────────────────────────────────────────────────────────
export const suppliersApi = {
  list: (tier?: string) => api.get('/suppliers/', { params: tier ? { tier } : {} }).then(r => r.data),
}

// ── Events ────────────────────────────────────────────────────────────────────
export const eventsApi = {
  listActive: () => api.get('/events/active').then(r => r.data),
  create: (data: {
    supplier_id: string; disruption_type: string; severity: number
    description: string; affected_capacity_pct: number
  }) => api.post('/events/', data).then(r => r.data),
  resolve: (id: string) => api.post(`/events/${id}/resolve`).then(r => r.data),
}

// ── Predictions ───────────────────────────────────────────────────────────────
export const predictionsApi = {
  summary: () => api.get('/predictions/summary').then(r => r.data),
  tierBreakdown: () => api.get('/predictions/tier-breakdown').then(r => r.data),
}
