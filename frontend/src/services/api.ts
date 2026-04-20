import axios, { AxiosInstance, AxiosError } from 'axios'
import { AuthTokens, User } from '@/types'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// Create Axios instance
const api: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Helper to get current token
const getToken = (): string | null => localStorage.getItem('access_token')

// ── Toast bridge ──────────────────────────────────────────
// The API service can't use React hooks directly, so we use
// a simple event-based bridge that the ToastProvider listens to.
type ToastEvent = {
  type: 'success' | 'error' | 'warning' | 'info'
  title: string
  description?: string
}

const toastListeners: Array<(event: ToastEvent) => void> = []

export function onApiToast(listener: (event: ToastEvent) => void) {
  toastListeners.push(listener)
  return () => {
    const idx = toastListeners.indexOf(listener)
    if (idx >= 0) toastListeners.splice(idx, 1)
  }
}

function emitToast(event: ToastEvent) {
  toastListeners.forEach(fn => fn(event))
}

// ── Session-expired bridge ────────────────────────────────
// Allows AuthContext to register its logout function so the
// API layer can trigger a reactive logout on 401 without
// using window.location (which causes hard page reloads).
let sessionExpiredCallback: (() => void) | null = null

export function onSessionExpired(callback: () => void) {
  sessionExpiredCallback = callback
  return () => { sessionExpiredCallback = null }
}

// Auth endpoints that should NOT have tokens injected
const AUTH_ENDPOINTS = ['/auth/register', '/auth/login']

function isAuthEndpoint(url?: string): boolean {
  if (!url) return false
  return AUTH_ENDPOINTS.some(ep => url.includes(ep))
}

// Request interceptor: Add JWT token to headers (skip auth endpoints)
api.interceptors.request.use(
  (config) => {
    const token = getToken()
    if (token && !isAuthEndpoint(config.url)) {
      config.headers.Authorization = `Bearer ${token}`
      // Also add token as query param for backend endpoints that expect it
      if (!config.params) config.params = {}
      if (!config.params.token) {
        config.params.token = token
      }
    }
    return config
  },
  (error) => Promise.reject(error)
)

// Response interceptor: Handle errors and token refresh
api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const status = error.response?.status
    const data = error.response?.data as Record<string, unknown> | undefined

    if (status === 401 && !isAuthEndpoint(error.config?.url)) {
      // Token expired or invalid — only handle for non-auth endpoints
      // (auth endpoints handle their own 401s via the AuthContext error state)
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      emitToast({ type: 'error', title: 'Session expired', description: 'Please log in again.' })
      // Trigger reactive logout via AuthContext (sets user=null),
      // which makes ProtectedRoute redirect to /login via React Router.
      // No window.location — no hard page reload.
      if (sessionExpiredCallback) sessionExpiredCallback()
    } else if (status === 403) {
      emitToast({ type: 'error', title: 'Access denied', description: 'You don\'t have permission for this action.' })
    } else if (status === 404) {
      emitToast({ type: 'warning', title: 'Not found', description: 'The requested resource was not found.' })
    } else if (status === 422) {
      const detail = data?.detail
      const msg = Array.isArray(detail) ? detail[0]?.msg : typeof detail === 'string' ? detail : 'Validation error'
      emitToast({ type: 'warning', title: 'Validation error', description: String(msg) })
    } else if (status && status >= 500) {
      emitToast({ type: 'error', title: 'Server error', description: 'Something went wrong. Please try again later.' })
    } else if (!error.response) {
      emitToast({ type: 'error', title: 'Network error', description: 'Could not reach the server. Check your connection.' })
    }

    return Promise.reject(error)
  }
)

/**
 * Authentication API calls
 */
export const authAPI = {
  login: async (email: string, password: string): Promise<{ user: User; tokens: AuthTokens }> => {
    const response = await api.post('/auth/login', { email, password })
    return response.data
  },

  register: async (email: string, username: string, password: string, full_name?: string) => {
    const response = await api.post('/auth/register', {
      email,
      username,
      password,
      full_name,
    })
    return response.data
  },

  verify: async (token: string): Promise<User> => {
    const response = await api.get('/auth/verify', {
      params: { token },
    })
    return response.data
  },

  logout: async (token: string) => {
    const response = await api.post('/auth/logout', {}, {
      params: { token },
    })
    return response.data
  },

  refresh: async (refresh_token: string): Promise<AuthTokens> => {
    const response = await api.post('/auth/refresh', {}, {
      params: { refresh_token },
    })
    return response.data
  },
}

/**
 * Knowledge/Search API calls
 */
export const knowledgeAPI = {
  search: async (query: string, top_k: number = 5, min_similarity: number = 0.3) => {
    const response = await api.post('/knowledge/search', {
      query,
      top_k,
      min_similarity,
    })
    return response.data
  },

  getSources: async () => {
    const response = await api.get('/knowledge/sources')
    return response.data
  },

  upload: async (file: File, sourceType: string = 'pdf') => {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('source_type', sourceType)

    const response = await api.post('/knowledge/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  },

  getGraph: async () => {
    const response = await api.get('/knowledge/graph')
    return response.data
  },
}

/**
 * AURA Chat API calls
 */
export const auraAPI = {
  sendMessage: async (message: string, context_window?: number, include_sources?: boolean) => {
    const response = await api.post('/aura/query', {
      message,
      context_window,
      include_sources,
    })
    return response.data
  },

  getConversationHistory: async () => {
    const response = await api.get('/aura/history')
    return response.data
  },

  getState: async () => {
    const response = await api.get('/aura/state')
    return response.data
  },
}

/**
 * Health API calls
 */
export const healthAPI = {
  health: async () => {
    const response = await api.get('/health')
    return response.data
  },

  status: async () => {
    const response = await api.get('/status')
    return response.data
  },

  version: async () => {
    const response = await api.get('/version')
    return response.data
  },
}

export default api
