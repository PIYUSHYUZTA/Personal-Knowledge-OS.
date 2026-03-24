import React from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '@/context/AuthContext'
import { Loader2, ArrowRight } from 'lucide-react'

export default function RegisterPage() {
  const navigate = useNavigate()
  const { register, isLoading, error } = useAuth()
  const [formData, setFormData] = React.useState({
    email: '',
    username: '',
    password: '',
    full_name: '',
  })

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    })
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      await register(formData.email, formData.username, formData.password, formData.full_name)
      navigate('/')
    } catch (err) {
      // Error is handled by context
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background relative overflow-hidden">
      {/* Background Ornaments */}
      <div className="absolute top-[-10%] right-[-10%] w-[40%] h-[40%] bg-brand/20 blur-[120px] rounded-full mix-blend-multiply dark:mix-blend-lighten pointer-events-none" />
      <div className="absolute bottom-[-10%] left-[-10%] w-[40%] h-[40%] bg-accent/20 blur-[120px] rounded-full mix-blend-multiply dark:mix-blend-lighten pointer-events-none" />
      
      <div className="w-full max-w-md px-4 relative z-10 py-12 animate-in fade-in slide-in-from-bottom-8 duration-700">
        <div className="glass-card rounded-2xl p-10 flex flex-col items-center border border-border/50">
          <div className="w-12 h-12 rounded-xl bg-brand text-white flex items-center justify-center font-bold text-xl shadow-glow mb-6">
            PK
          </div>
          <h1 className="text-2xl font-bold text-primary mb-2 text-center tracking-tight">Create your account</h1>
          <p className="text-sm text-muted mb-8 text-center">Join PKOS and organize your mind.</p>

          {error && (
            <div className="w-full bg-red-500/10 border border-red-500/20 text-red-500 text-sm p-3 rounded-lg mb-6 flex items-center gap-2">
              <span className="shrink-0">⚠️</span> {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4 w-full">
            <div className="space-y-1.5">
              <label className="block text-xs font-medium text-primary">Email address</label>
              <input
                type="email"
                name="email"
                value={formData.email}
                onChange={handleChange}
                className="w-full px-4 py-2.5 border border-border/50 rounded-xl bg-surface/50 text-primary placeholder:text-muted focus:ring-2 focus:ring-brand/50 focus:border-brand transition-all outline-none shadow-sm"
                placeholder="you@example.com"
                required
              />
            </div>

            <div className="space-y-1.5">
              <label className="block text-xs font-medium text-primary">Username</label>
              <input
                type="text"
                name="username"
                value={formData.username}
                onChange={handleChange}
                className="w-full px-4 py-2.5 border border-border/50 rounded-xl bg-surface/50 text-primary placeholder:text-muted focus:ring-2 focus:ring-brand/50 focus:border-brand transition-all outline-none shadow-sm"
                placeholder="johndoe"
                required
              />
            </div>

            <div className="space-y-1.5">
              <label className="block text-xs font-medium text-primary flex justify-between">
                <span>Full Name</span>
                <span className="text-muted/70 font-normal">Optional</span>
              </label>
              <input
                type="text"
                name="full_name"
                value={formData.full_name}
                onChange={handleChange}
                className="w-full px-4 py-2.5 border border-border/50 rounded-xl bg-surface/50 text-primary placeholder:text-muted focus:ring-2 focus:ring-brand/50 focus:border-brand transition-all outline-none shadow-sm"
                placeholder="John Doe"
              />
            </div>

            <div className="space-y-1.5">
              <label className="block text-xs font-medium text-primary">Password</label>
              <input
                type="password"
                name="password"
                value={formData.password}
                onChange={handleChange}
                className="w-full px-4 py-2.5 border border-border/50 rounded-xl bg-surface/50 text-primary placeholder:text-muted focus:ring-2 focus:ring-brand/50 focus:border-brand transition-all outline-none shadow-sm"
                placeholder="••••••••"
                required
              />
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full mt-4 bg-brand hover:bg-brand/90 text-white font-medium py-2.5 rounded-xl transition-all shadow-glow flex items-center justify-center gap-2 disabled:opacity-70 disabled:cursor-not-allowed hover:-translate-y-0.5 active:scale-95 group"
            >
              {isLoading && <Loader2 className="w-4 h-4 animate-spin" />}
              {isLoading ? 'Creating account...' : 'Continue'}
              {!isLoading && <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />}
            </button>
          </form>

          <p className="text-center text-sm text-muted mt-8">
            Already have an account?{' '}
            <button
              onClick={() => navigate('/login')}
              className="text-brand hover:text-brand/80 font-medium transition-colors hover:underline cursor-pointer"
            >
              Log in
            </button>
          </p>
        </div>
      </div>
    </div>
  )
}
