import React from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '@/context/AuthContext'
import { Loader2 } from 'lucide-react'

export default function LoginPage() {
  const navigate = useNavigate()
  const { login, isLoading, error } = useAuth()
  const [email, setEmail] = React.useState('')
  const [password, setPassword] = React.useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      await login(email, password)
      navigate('/')
    } catch (err) {
      // Error is handled by context
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background relative overflow-hidden">
      {/* Background Ornaments */}
      <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-brand/20 blur-[120px] rounded-full mix-blend-multiply dark:mix-blend-lighten pointer-events-none" />
      <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-accent/20 blur-[120px] rounded-full mix-blend-multiply dark:mix-blend-lighten pointer-events-none" />
      
      <div className="w-full max-w-md px-4 relative z-10 animate-in fade-in slide-in-from-bottom-8 duration-700">
        <div className="glass-card rounded-2xl p-10 flex flex-col items-center border border-border/50">
          <div className="w-12 h-12 rounded-xl bg-brand text-white flex items-center justify-center font-bold text-xl shadow-glow mb-6">
            PK
          </div>
          <h1 className="text-2xl font-bold text-primary mb-2 text-center tracking-tight">Welcome back</h1>
          <p className="text-sm text-muted mb-8 text-center">Sign in to your Personal Knowledge OS</p>

          {error && (
            <div className="w-full bg-red-500/10 border border-red-500/20 text-red-500 text-sm p-3 rounded-lg mb-6 flex items-center gap-2">
              <span className="shrink-0">⚠️</span> {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5 w-full">
            <div className="space-y-1.5">
              <label className="block text-xs font-medium text-primary">Email address</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-4 py-2.5 border border-border/50 rounded-xl bg-surface/50 text-primary placeholder:text-muted focus:ring-2 focus:ring-brand/50 focus:border-brand transition-all outline-none shadow-sm"
                placeholder="you@example.com"
                required
              />
            </div>

            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <label className="block text-xs font-medium text-primary">Password</label>
                <button type="button" className="text-xs font-medium text-brand hover:underline transition-all">Forgot?</button>
              </div>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-4 py-2.5 border border-border/50 rounded-xl bg-surface/50 text-primary placeholder:text-muted focus:ring-2 focus:ring-brand/50 focus:border-brand transition-all outline-none shadow-sm"
                placeholder="••••••••"
                required
              />
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full mt-2 bg-brand hover:bg-brand/90 text-white font-medium py-2.5 rounded-xl transition-all shadow-glow flex items-center justify-center gap-2 disabled:opacity-70 disabled:cursor-not-allowed hover:-translate-y-0.5 active:scale-95"
            >
              {isLoading && <Loader2 className="w-4 h-4 animate-spin" />}
              {isLoading ? 'Signing in...' : 'Sign in'}
            </button>
          </form>

          <p className="text-center text-sm text-muted mt-8">
            Don't have an account?{' '}
            <button
              onClick={() => navigate('/register')}
              className="text-brand hover:text-brand/80 font-medium transition-colors hover:underline cursor-pointer"
            >
              Request access
            </button>
          </p>
        </div>
      </div>
    </div>
  )
}
