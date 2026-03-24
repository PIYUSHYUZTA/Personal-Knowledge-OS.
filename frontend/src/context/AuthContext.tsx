import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { User } from '@/types'
import { authAPI } from '@/services/api'

interface AuthContextType {
  user: User | null
  isLoading: boolean
  error: string | null
  isAuthenticated: boolean
  login: (email: string, password: string) => Promise<void>
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
      // After registration, automatically login
      await login(email, password)
    } catch (err: any) {
      setError(extractError(err, 'Registration failed'))
      throw err
    } finally {
      setIsLoading(false)
    }
  }

  const logout = () => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
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
