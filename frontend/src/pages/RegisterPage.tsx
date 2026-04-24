import React, { useState, useEffect, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '@/context/AuthContext'
import { motion, AnimatePresence } from 'framer-motion'
import AuthBackground from '@/components/auth/AuthBackground'

function getPasswordStrength(password: string): { score: number; label: string; color: string } {
  let score = 0
  if (password.length >= 6) score++
  if (password.length >= 10) score++
  if (/[A-Z]/.test(password)) score++
  if (/[0-9]/.test(password)) score++
  if (/[^A-Za-z0-9]/.test(password)) score++

  if (score <= 1) return { score, label: 'Weak', color: 'bg-error' }
  if (score <= 2) return { score, label: 'Fair', color: 'bg-orange-500' }
  if (score <= 3) return { score, label: 'Good', color: 'bg-secondary' }
  return { score, label: 'Strong', color: 'bg-emerald-500' }
}

export default function RegisterPage() {
  const navigate = useNavigate()
  const { register, isLoading, error } = useAuth()
  
  const [formData, setFormData] = useState({
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
      // Redirect to login to verify
      navigate('/login')
    } catch {
      // Error is handled by context
    }
  }

  return (
    <div className="bg-transparent text-on-surface h-screen w-screen overflow-hidden flex items-center justify-center relative font-body-md text-body-md selection:bg-primary-container/30 selection:text-primary">
      
      {/* Deep Space Background */}
      <AuthBackground />

      <motion.main 
        initial={{ opacity: 0, scale: 0.95, y: 10 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="relative z-10 w-full max-w-[440px] mx-6"
      >
        <div className="bg-surface/40 backdrop-blur-[40px] border border-white/10 rounded-2xl shadow-[0_32px_64px_rgba(0,0,0,0.5)] p-8 relative overflow-hidden">
          <header className="mb-6 text-center">
            <div className="flex justify-center mb-4">
              <span className="material-symbols-outlined text-secondary text-[32px] drop-shadow-[0_0_8px_rgba(0,227,253,0.3)]">person_add</span>
            </div>
            <h1 className="font-space-grotesk text-2xl font-bold text-on-surface tracking-tight uppercase">Identity_Registration</h1>
            <p className="font-inter text-[9px] uppercase font-bold text-secondary/80 mt-1 tracking-[0.2em]">Enrolling New Operator</p>
          </header>

          {error && (
            <div className="mb-6 p-3 rounded-lg bg-error/10 border border-error/20 text-error text-[11px] font-bold text-center uppercase tracking-wider">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <div className="grid grid-cols-2 gap-4">
               <div className="flex flex-col gap-1.5">
                  <label className="font-inter text-[9px] font-bold text-outline uppercase tracking-wider">Full Name</label>
                  <input 
                    className="w-full bg-white/5 border-b border-white/10 text-on-surface placeholder:text-outline/40 font-inter text-sm p-3 rounded-t focus:outline-none focus:border-secondary transition-all" 
                    name="full_name"
                    placeholder="John Doe" 
                    type="text"
                    value={formData.full_name}
                    onChange={handleChange}
                  />
               </div>
               <div className="flex flex-col gap-1.5">
                  <label className="font-inter text-[9px] font-bold text-outline uppercase tracking-wider">Username</label>
                  <input 
                    className="w-full bg-white/5 border-b border-white/10 text-on-surface placeholder:text-outline/40 font-inter text-sm p-3 rounded-t focus:outline-none focus:border-secondary transition-all" 
                    name="username"
                    placeholder="johndoe" 
                    type="text"
                    value={formData.username}
                    onChange={handleChange}
                    required
                  />
               </div>
            </div>

            <div className="flex flex-col gap-1.5">
              <label className="font-inter text-[9px] font-bold text-outline uppercase tracking-wider">Neural Designation (Email)</label>
              <input 
                className="w-full bg-white/5 border-b border-white/10 text-on-surface placeholder:text-outline/40 font-inter text-sm p-3 rounded-t focus:outline-none focus:border-secondary transition-all" 
                name="email"
                placeholder="operator@nexus.local" 
                type="email"
                value={formData.email}
                onChange={handleChange}
                required
              />
            </div>

            <div className="flex flex-col gap-1.5">
              <label className="font-inter text-[9px] font-bold text-outline uppercase tracking-wider">Access Passphrase</label>
              <input 
                className="w-full bg-white/5 border-b border-white/10 text-on-surface placeholder:text-outline/40 font-inter text-sm p-3 rounded-t focus:outline-none focus:border-secondary transition-all" 
                name="password"
                placeholder="••••••••••••" 
                type="password"
                value={formData.password}
                onChange={handleChange}
                required
              />
              {formData.password.length > 0 && (
                <div className="flex items-center gap-2 mt-1">
                  <div className="flex-1 h-0.5 bg-white/10 rounded-full overflow-hidden">
                    <motion.div 
                      className={`h-full ${passwordStrength.color}`} 
                      initial={{ width: 0 }}
                      animate={{ width: `${(passwordStrength.score / 5) * 100}%` }}
                    />
                  </div>
                  <span className="text-[8px] font-bold uppercase text-outline">{passwordStrength.label}</span>
                </div>
              )}
            </div>

            <button 
              disabled={isLoading || !formData.email || !formData.password}
              className="mt-4 w-full bg-secondary/10 border border-secondary/50 hover:bg-secondary/20 text-secondary font-inter text-[10px] font-bold uppercase tracking-[0.2em] py-4 rounded-lg flex justify-center items-center gap-3 transition-all shadow-[0_0_15px_rgba(0,227,253,0.1)] hover:shadow-[0_0_25px_rgba(0,227,253,0.3)] disabled:opacity-50" 
              type="submit"
            >
              {isLoading ? "ENROLLING..." : "CREATE IDENTITY"}
            </button>
          </form>

          <footer className="mt-8 pt-6 border-t border-white/5 flex flex-col items-center gap-4">
            <p className="font-inter text-[10px] text-outline uppercase tracking-widest">
              Already Enrolled?
              <button 
                onClick={() => navigate('/login')}
                className="ml-2 text-primary hover:underline font-bold"
              >
                ACCESS UPLINK
              </button>
            </p>
          </footer>
        </div>
      </motion.main>
    </div>
  )
}
