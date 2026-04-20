import React, { useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '@/context/AuthContext'
import { Loader2, ArrowRight } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import { cn } from '@/lib/utils'

function getPasswordStrength(password: string): { score: number; label: string; color: string } {
  let score = 0
  if (password.length >= 6) score++
  if (password.length >= 10) score++
  if (/[A-Z]/.test(password)) score++
  if (/[0-9]/.test(password)) score++
  if (/[^A-Za-z0-9]/.test(password)) score++

  if (score <= 1) return { score, label: 'Weak', color: 'bg-error' }
  if (score <= 2) return { score, label: 'Fair', color: 'bg-warning' }
  if (score <= 3) return { score, label: 'Good', color: 'bg-info' }
  return { score, label: 'Strong', color: 'bg-success' }
}

export default function RegisterPage() {
  const navigate = useNavigate()
  const { register, isLoading, error } = useAuth()
  const [formData, setFormData] = React.useState({
    email: '',
    username: '',
    password: '',
    full_name: '',
  })

  const passwordStrength = useMemo(() => getPasswordStrength(formData.password), [formData.password])

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
    } catch {
      // Error is handled by context
    }
  }

  return (
    <div className="flex relative min-h-screen items-center justify-center bg-background overflow-hidden selection:bg-secondary/20 selection:text-secondary py-12">
      {/* Background orbs */}
      <div className="absolute top-[-20%] right-[-10%] w-[50%] h-[50%] bg-secondary/8 blur-[120px] rounded-full pointer-events-none animate-float" />
      <div className="absolute bottom-[-20%] left-[-10%] w-[50%] h-[50%] bg-accent/8 blur-[120px] rounded-full pointer-events-none animate-float" style={{ animationDelay: '3s' }} />

      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 10 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        transition={{ duration: 0.5, ease: [0.23, 1, 0.32, 1] }}
        className="w-full max-w-[420px] px-4 relative z-10"
      >
        <div className="glass-panel rounded-2xl p-10 flex flex-col items-center border border-border/60 shadow-lg relative overflow-hidden backdrop-blur-2xl">
          {/* Gradient strip */}
          <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-accent/60 via-secondary/60 to-accent/60" />

          <div className="w-12 h-12 rounded-xl bg-primary text-surface flex items-center justify-center font-bold text-lg shadow-sm mb-6 relative group overflow-hidden">
            <span className="relative z-10">PK</span>
            <div className="absolute inset-0 bg-secondary/80 translate-y-full group-hover:translate-y-0 transition-transform duration-200" />
          </div>

          <h1 className="text-2xl font-semibold text-primary mb-1.5 text-center tracking-tight">Create your account</h1>
          <p className="text-sm text-text-muted mb-8 text-center px-4">Join PKOS and start building your brain.</p>

          <AnimatePresence>
            {error && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                className="w-full overflow-hidden"
              >
                <div className="bg-error/10 border border-error/20 text-error text-[13px] font-medium p-3 rounded-lg mb-6 flex items-start gap-2">
                  <span className="shrink-0 mt-0.5">⚠️</span>
                  <span>{error}</span>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          <form onSubmit={handleSubmit} className="space-y-4 w-full">
            <div className="space-y-1.5">
              <label className="block text-[10px] font-semibold text-text-muted uppercase tracking-wider">Email Address</label>
              <input
                id="register-email"
                type="email"
                name="email"
                value={formData.email}
                onChange={handleChange}
                className="w-full px-4 py-3 border border-border/80 rounded-xl bg-black/5 dark:bg-white/5 text-primary placeholder:text-text-muted/50 focus:ring-2 focus:ring-secondary/20 focus:border-secondary focus:bg-background transition-all outline-none shadow-sm text-sm"
                placeholder="you@example.com"
                required
              />
            </div>

            <div className="space-y-1.5">
              <label className="block text-[10px] font-semibold text-text-muted uppercase tracking-wider">Username</label>
              <input
                id="register-username"
                type="text"
                name="username"
                value={formData.username}
                onChange={handleChange}
                className="w-full px-4 py-3 border border-border/80 rounded-xl bg-black/5 dark:bg-white/5 text-primary placeholder:text-text-muted/50 focus:ring-2 focus:ring-secondary/20 focus:border-secondary focus:bg-background transition-all outline-none shadow-sm text-sm font-mono"
                placeholder="johndoe"
                required
              />
            </div>

            <div className="space-y-1.5">
              <label className="flex items-center justify-between text-[10px] font-semibold text-text-muted uppercase tracking-wider">
                <span>Full Name</span>
                <span className="opacity-60 lowercase font-medium tracking-normal">Optional</span>
              </label>
              <input
                id="register-fullname"
                type="text"
                name="full_name"
                value={formData.full_name}
                onChange={handleChange}
                className="w-full px-4 py-3 border border-border/80 rounded-xl bg-black/5 dark:bg-white/5 text-primary placeholder:text-text-muted/50 focus:ring-2 focus:ring-secondary/20 focus:border-secondary focus:bg-background transition-all outline-none shadow-sm text-sm"
                placeholder="John Doe"
              />
            </div>

            <div className="space-y-1.5">
              <label className="block text-[10px] font-semibold text-text-muted uppercase tracking-wider">Password</label>
              <input
                id="register-password"
                type="password"
                name="password"
                value={formData.password}
                onChange={handleChange}
                className="w-full px-4 py-3 border border-border/80 rounded-xl bg-black/5 dark:bg-white/5 text-primary placeholder:text-text-muted/50 focus:ring-2 focus:ring-secondary/20 focus:border-secondary focus:bg-background transition-all outline-none shadow-sm text-sm"
                placeholder="••••••••"
                required
              />
              {/* Password strength indicator */}
              {formData.password.length > 0 && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  className="pt-2 space-y-1.5"
                >
                  <div className="flex gap-1">
                    {[1, 2, 3, 4, 5].map((level) => (
                      <div
                        key={level}
                        className={cn(
                          'h-1 flex-1 rounded-full transition-colors duration-200',
                          level <= passwordStrength.score ? passwordStrength.color : 'bg-border'
                        )}
                      />
                    ))}
                  </div>
                  <p className="text-[10px] font-medium text-text-muted">
                    Password strength: <span className="text-primary">{passwordStrength.label}</span>
                  </p>
                </motion.div>
              )}
            </div>

            <button
              id="register-submit"
              type="submit"
              disabled={isLoading || !formData.email || !formData.username || !formData.password}
              className="w-full mt-6 bg-secondary text-white font-medium py-3 rounded-xl transition-all shadow-sm shadow-secondary/20 flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-secondary/90 active:scale-[0.98] group text-sm"
            >
              {isLoading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <>
                  Continue
                  <ArrowRight className="w-4 h-4 opacity-50 group-hover:translate-x-1 group-hover:opacity-100 transition-all" />
                </>
              )}
            </button>
          </form>

          <p className="text-center text-[13px] text-text-muted mt-8">
            Already have an account?{' '}
            <button
              onClick={() => navigate('/login')}
              className="text-secondary hover:text-secondary/80 font-semibold transition-colors cursor-pointer"
            >
              Log in
            </button>
          </p>
        </div>
      </motion.div>
    </div>
  )
}
