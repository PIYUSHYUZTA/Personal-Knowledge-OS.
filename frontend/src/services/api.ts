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

// Request interceptor: Add JWT token to headers
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// Response interceptor: Handle errors and token refresh
api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    if (error.response?.status === 401) {
      // Token expired or invalid
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      window.location.href = '/login'
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

    const response = await api.post('/ingestion/upload', formData, {
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
