import React from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from '@/context/AuthContext'
import { KnowledgeProvider } from '@/context/KnowledgeContext'
import { AuraProvider } from '@/context/AuraContext'
import './index.css'

// Pages
import Dashboard from '@/components/dashboard/Dashboard'
import LoginPage from '@/pages/LoginPage'
import RegisterPage from '@/pages/RegisterPage'
import NotFoundPage from '@/pages/NotFoundPage'

// Protected Route
const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const isAuthenticated = localStorage.getItem('access_token')
  return isAuthenticated ? <>{children}</> : <Navigate to="/login" />
}

function App() {
  return (
    <BrowserRouter>
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
    </BrowserRouter>
  )
}

export default App
