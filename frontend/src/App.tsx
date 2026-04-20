import React, { useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from '@/context/AuthContext'
import { KnowledgeProvider } from '@/context/KnowledgeContext'
import { AuraProvider } from '@/context/AuraContext'
import { ToastProvider } from '@/components/ui/Toast'
import './index.css'

// Pages
import Dashboard from '@/components/dashboard/Dashboard'
import LoginPage from '@/pages/LoginPage'
import RegisterPage from '@/pages/RegisterPage'
import NotFoundPage from '@/pages/NotFoundPage'

import { useAuth } from '@/context/AuthContext'

// Protected Route — uses reactive auth context, not raw localStorage
const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated, isLoading } = useAuth()

  // While verifying the token on mount, show nothing (prevents flash)
  if (isLoading) return null

  return isAuthenticated ? <>{children}</> : <Navigate to="/login" />
}

function App() {
  // Theme initialization: localStorage → system preference → default dark
  useEffect(() => {
    const stored = localStorage.getItem('pkos-theme')
    const root = document.documentElement

    if (stored === 'light') {
      root.classList.remove('dark')
    } else if (stored === 'dark') {
      root.classList.add('dark')
    } else {
      // System preference fallback
      if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
        root.classList.add('dark')
      } else {
        root.classList.remove('dark')
      }
    }
  }, [])

  return (
    <BrowserRouter>
      <ToastProvider>
        <AuthProvider>
          <KnowledgeProvider>
            <AuraProvider>
              <Routes>
                <Route path="/login" element={<LoginPage />} />
                <Route path="/register" element={<RegisterPage />} />

                <Route
                  path="/"
                  element={
                    <ProtectedRoute>
                      <Dashboard />
                    </ProtectedRoute>
                  }
                />

                <Route path="*" element={<NotFoundPage />} />
              </Routes>
            </AuraProvider>
          </KnowledgeProvider>
        </AuthProvider>
      </ToastProvider>
    </BrowserRouter>
  )
}

export default App
