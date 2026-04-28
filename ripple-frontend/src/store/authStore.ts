import { create } from 'zustand'
import { authApi } from '../services/api'

interface User { user_id: string; email: string; name: string }

interface AuthState {
  user: User | null
  loading: boolean
  error: string | null
  login:    (email: string, password: string) => Promise<void>
  register: (email: string, password: string, name: string) => Promise<void>
  logout:   () => void
  restore:  () => Promise<void>
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null, loading: false, error: null,

  login: async (email, password) => {
    set({ loading: true, error: null })
    try {
      const data = await authApi.login(email, password)
      localStorage.setItem('token', data.access_token)
      set({ user: { user_id: data.user_id, email: data.email, name: data.name }, loading: false })
    } catch (e: any) {
      set({ error: e.message, loading: false })
      throw e
    }
  },

  register: async (email, password, name) => {
    set({ loading: true, error: null })
    try {
      const data = await authApi.register(email, password, name)
      localStorage.setItem('token', data.access_token)
      set({ user: { user_id: data.user_id, email: data.email, name: data.name }, loading: false })
    } catch (e: any) {
      set({ error: e.message, loading: false })
      throw e
    }
  },

  logout: () => {
    localStorage.removeItem('token')
    set({ user: null })
  },

  restore: async () => {
    const token = localStorage.getItem('token')
    if (!token) return
    try {
      const data = await authApi.me()
      set({ user: { user_id: data.user_id, email: data.email, name: data.name } })
    } catch {
      localStorage.removeItem('token')
    }
  },
}))
