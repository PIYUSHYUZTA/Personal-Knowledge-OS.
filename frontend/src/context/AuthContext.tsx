import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { User } from '@/types'
import { authAPI, onSessionExpired } from '@/services/api'

interface AuthContextType {
  user: User | null
  isLoading: boolean
  error: string | null
  isAuthenticated: boolean
  login: (email: string, password: string) => Promise<void>
  loginAsBiometric: () => void
  register: (email: string, username: string, password: string, full_name?: string) => Promise<void>
  logout: () => void
  clearError: () => void
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Check authentication on mount
  useEffect(() => {
    const token = localStorage.getItem('access_token')
    if (token) {
      // Mock biometric tokens bypass API verification (demo/presentation mode)
      if (token.startsWith('mock_biometric_')) {
        setUser({
          id: 'demo-user',
          email: 'operator@pkos.dev',
          username: 'Operator',
          full_name: 'PKOS Operator',
        } as User)
        setIsLoading(false)
        return
      }

      setIsLoading(true)
      authAPI
        .verify(token)
        .then((userData) => {
          setUser(userData)
          setError(null)
        })
        .catch(() => {
          setError('Session expired')
          localStorage.removeItem('access_token')
          localStorage.removeItem('refresh_token')
        })
        .finally(() => setIsLoading(false))
    }
  }, [])

  // Register logout as the session-expired handler so the API
  // layer's 401 interceptor can trigger a reactive redirect
  // via React Router instead of a hard window.location reload.
  useEffect(() => {
    return onSessionExpired(() => {
      setUser(null)
      setError(null)
    })
  }, [])

  const extractError = (err: any, defaultMsg: string) => {
    if (err.response?.data?.detail) {
      const detail = err.response.data.detail
      if (Array.isArray(detail)) {
        return detail[0].msg
      }
      return typeof detail === 'string' ? detail : defaultMsg
    }
    return defaultMsg
  }

  const login = async (email: string, password: string) => {
    setIsLoading(true)
    setError(null)
    try {
      const { user: userData, tokens } = await authAPI.login(email, password)
      setUser(userData)
      localStorage.setItem('access_token', tokens.access_token)
      if (tokens.refresh_token) {
        localStorage.setItem('refresh_token', tokens.refresh_token)
      }
    } catch (err: any) {
      setError(extractError(err, 'Login failed'))
      throw err
    } finally {
      setIsLoading(false)
    }
  }

  const register = async (email: string, username: string, password: string, full_name?: string) => {
    setIsLoading(true)
    setError(null)
    try {
      await authAPI.register(email, username, password, full_name)
      // After registration, automatically login (inline to avoid isLoading race)
      const { user: userData, tokens } = await authAPI.login(email, password)
      setUser(userData)
      localStorage.setItem('access_token', tokens.access_token)
      if (tokens.refresh_token) {
        localStorage.setItem('refresh_token', tokens.refresh_token)
      }
    } catch (err: any) {
      setError(extractError(err, 'Registration failed'))
      throw err
    } finally {
      setIsLoading(false)
    }
  }

  // ── Mock Biometric Login (Demo/Presentation Mode) ───────────
  // Directly sets user + token so ProtectedRoute passes immediately,
  // no API call needed. The boot sequence on LoginPage calls this
  // BEFORE navigating to '/'.
  const loginAsBiometric = () => {
    const mockToken = `mock_biometric_${Date.now()}_${Math.random().toString(36).slice(2)}`
    localStorage.setItem('access_token', mockToken)
    localStorage.setItem('pkos_auth_method', 'biometric')
    setUser({
      id: 'demo-user',
      email: 'operator@pkos.dev',
      username: 'Operator',
      full_name: 'PKOS Operator',
    } as User)
    setError(null)
  }

  const logout = () => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('pkos_auth_method')
    setUser(null)
    setError(null)
  }

  const clearError = () => setError(null)

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        error,
        isAuthenticated: !!user,
        login,
        loginAsBiometric,
        register,
        logout,
        clearError,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return context
}
