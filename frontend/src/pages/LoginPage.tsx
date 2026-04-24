import React, { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '@/context/AuthContext'
import { motion, AnimatePresence } from 'framer-motion'
import AuthBackground from '@/components/auth/AuthBackground'
import { useSound } from '@/hooks/useSound'

export default function LoginPage() {
  const navigate = useNavigate()
  const { login, loginAsBiometric, isLoading, error } = useAuth()
  const { playClick, playScan, playSuccess, playError, playWoosh } = useSound()
  
  const [operatorId, setOperatorId] = useState('')
  const [accessKey, setAccessKey] = useState('')
  const [isBooting, setIsBooting] = useState(false)
  const [bootStage, setBootStage] = useState(-1)
  
  // Biometric States
  const [bioState, setBioState] = useState<'idle' | 'scanning' | 'success' | 'failed'>('idle')
  const [scanProgress, setScanProgress] = useState(0)
  const videoRef = useRef<HTMLVideoElement>(null)

  const BOOT_SEQUENCE = [
    "[OK] Kernel Loaded",
    "[OK] Mounting Personal Knowledge Graph",
    "[OK] Bypassing Sleep Mode",
    "[OK] Focus Protocol: ENGAGED",
    "[!] Caffeine Levels: Critical but Stable"
  ]

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      playClick()
      await login(operatorId, accessKey)
      triggerSystemBoot()
    } catch {
      playError()
      // Error handled by context
    }
  }

  const handleBiometricScan = async () => {
    setBioState('scanning')
    setScanProgress(0)

    // Try to access camera for realism
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user' } })
      if (videoRef.current) {
        videoRef.current.srcObject = stream
      }
    } catch (err) {
      console.warn("Camera access denied or unavailable for Face ID simulation.")
    }

    // Simulate intense scanning progress
    const interval = setInterval(() => {
      playScan()
      setScanProgress(prev => {
        if (prev >= 100) {
          clearInterval(interval)
          return 100
        }
        return prev + 2
      })
    }, 40)

    // Verification Logic
    setTimeout(() => {
      clearInterval(interval)
      setScanProgress(100)
      setBioState('success')
      playSuccess()
      
      // Stop camera
      if (videoRef.current?.srcObject) {
        (videoRef.current.srcObject as MediaStream).getTracks().forEach(track => track.stop())
      }

      setTimeout(() => {
        loginAsBiometric()
        triggerSystemBoot()
      }, 800)
    }, 2500)
  }

  const triggerSystemBoot = () => {
    playWoosh()
    setIsBooting(true)
  }

  useEffect(() => {
    if (!isBooting) return;
    const stepTime = 1200 / BOOT_SEQUENCE.length; 
    let step = 0;
    const interval = setInterval(() => {
      setBootStage(step);
      step++;
      if (step >= BOOT_SEQUENCE.length) {
        clearInterval(interval);
        setTimeout(() => {
          navigate('/');
        }, 600);
      }
    }, stepTime);
    return () => clearInterval(interval);
  }, [isBooting, navigate])

  return (
    <div className="bg-transparent text-on-surface h-screen w-screen overflow-hidden flex items-center justify-center relative font-body-md text-body-md selection:bg-primary-container/30 selection:text-primary">
      
      {/* Deep Space Background */}
      <AuthBackground />

      <AnimatePresence mode="wait">
        {bioState === 'scanning' ? (
          <motion.div 
            key="biometric-overlay"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-black/90 backdrop-blur-xl"
          >
            {/* Camera Viewfinder */}
            <div className="relative w-64 h-64 md:w-80 md:h-80 rounded-full border-2 border-primary/30 overflow-hidden shadow-[0_0_50px_rgba(124,77,255,0.3)]">
              <video 
                ref={videoRef} 
                autoPlay 
                playsInline 
                muted 
                className="w-full h-full object-cover grayscale brightness-75"
              />
              {/* Scan Line */}
              <motion.div 
                animate={{ top: ['0%', '100%', '0%'] }}
                transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                className="absolute left-0 right-0 h-1 bg-primary shadow-[0_0_15px_#7c4dff] z-10"
              />
              {/* Brackets */}
              <div className="absolute inset-8 border border-white/10 rounded-full pointer-events-none animate-pulse"></div>
            </div>

            <div className="mt-12 flex flex-col items-center gap-4">
              <h2 className="font-space-grotesk text-xl font-bold text-primary tracking-[0.4em] uppercase">Neural_Scan_Active</h2>
              <div className="w-64 h-1 bg-white/5 rounded-full overflow-hidden">
                <motion.div 
                  className="h-full bg-primary"
                  style={{ width: `${scanProgress}%` }}
                />
              </div>
              <p className="font-mono text-[10px] text-outline tabular-nums uppercase tracking-widest">
                Matching Biometric Signatures... {scanProgress}%
              </p>
            </div>
          </motion.div>
        ) : !isBooting ? (
          <motion.main 
            key="auth-panel"
            initial={{ opacity: 0, scale: 0.9, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 1.1, filter: "blur(20px)" }}
            transition={{ duration: 0.5, ease: [0.23, 1, 0.32, 1] }}
            className="relative z-10 w-full max-w-[420px] mx-6"
          >
            <div className="bg-surface/40 backdrop-blur-[40px] border border-white/10 rounded-2xl shadow-[0_32px_64px_rgba(0,0,0,0.5)] p-10 relative overflow-hidden">
              <div className="absolute inset-0 bg-gradient-to-b from-primary/5 to-transparent pointer-events-none"></div>
              
              <header className="mb-8 text-center relative z-10">
                <div className="flex justify-center mb-6">
                  <span className="material-symbols-outlined text-primary text-[40px] drop-shadow-[0_0_12px_rgba(205,189,255,0.5)]">memory</span>
                </div>
                <h1 className="font-space-grotesk text-3xl font-bold text-on-surface tracking-tight uppercase">PKOS_ENTRY</h1>
                <p className="font-inter text-[10px] uppercase font-bold text-primary/80 mt-2 tracking-[0.3em]">Awaiting Verification</p>
              </header>

              {error && (
                <motion.div 
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="mb-6 p-3 rounded-lg bg-error/10 border border-error/20 text-error text-[11px] font-bold text-center uppercase tracking-wider"
                >
                  {error}
                </motion.div>
              )}

              <form onSubmit={handleSubmit} className="flex flex-col gap-6 relative z-10">
                <div className="flex flex-col gap-2">
                  <label className="font-inter text-[10px] font-bold text-outline flex items-center gap-2 uppercase tracking-wider" htmlFor="operator-id">
                    <span className="material-symbols-outlined text-[16px]">badge</span>
                    OPERATOR ID
                  </label>
                  <input 
                    className="w-full bg-white/5 border-b-2 border-white/10 text-on-surface placeholder:text-outline/40 font-inter text-base p-4 rounded-t-lg focus:outline-none focus:border-primary focus:bg-white/10 transition-all" 
                    id="operator-id" 
                    placeholder="Enter Neural Designation" 
                    type="text"
                    value={operatorId}
                    onChange={(e) => setOperatorId(e.target.value)}
                    required
                  />
                </div>

                <div className="flex flex-col gap-2">
                  <div className="flex justify-between items-center">
                    <label className="font-inter text-[10px] font-bold text-outline flex items-center gap-2 uppercase tracking-wider" htmlFor="access-key">
                      <span className="material-symbols-outlined text-[16px]">key</span>
                      ACCESS KEY
                    </label>
                    <button 
                      type="button"
                      className="text-[9px] font-bold text-primary/60 hover:text-primary uppercase tracking-tighter transition-colors"
                      onClick={() => alert("Password recovery protocol initiated. Please contact system administrator.")}
                    >
                      Forgot Passphrase?
                    </button>
                  </div>
                  <input 
                    className="w-full bg-white/5 border-b-2 border-white/10 text-on-surface placeholder:text-outline/40 font-inter text-base p-4 rounded-t-lg focus:outline-none focus:border-primary focus:bg-white/10 transition-all" 
                    id="access-key" 
                    placeholder="••••••••••••" 
                    type="password"
                    value={accessKey}
                    onChange={(e) => setAccessKey(e.target.value)}
                    required
                  />
                </div>

                {/* Secondary Action */}
                <div className="flex justify-end mt-[-8px]">
                  <button 
                    onClick={handleBiometricScan}
                    className="font-inter text-[10px] font-bold text-secondary/70 hover:text-secondary transition-colors uppercase tracking-wider flex items-center gap-2" 
                    type="button"
                  >
                    <span className="material-symbols-outlined text-[14px]">face</span>
                    INITIALIZE BIOMETRIC OVERRIDE
                  </button>
                </div>

                {/* Primary Action */}
                <button 
                  disabled={isLoading}
                  className="mt-4 w-full bg-primary/10 border border-primary/50 hover:bg-primary/20 text-primary font-inter text-[10px] font-bold uppercase tracking-[0.2em] py-4 rounded-lg flex justify-center items-center gap-3 transition-all shadow-[0_0_15px_rgba(124,77,255,0.1)] hover:shadow-[0_0_25px_rgba(124,77,255,0.3)] disabled:opacity-50" 
                  type="submit"
                >
                  {isLoading ? "PROCESSING..." : "INITIALIZE UPLINK"}
                </button>
              </form>

              {/* NEW OPERATOR? REGISTER */}
              <div className="mt-8 pt-6 border-t border-white/5 flex flex-col items-center gap-4 relative z-10">
                <p className="font-inter text-[10px] text-outline uppercase tracking-widest">
                  New Operator? 
                  <button 
                    onClick={() => navigate('/register')}
                    className="ml-2 text-secondary hover:underline font-bold"
                  >
                    REQUEST CLEARANCE
                  </button>
                </p>
              </div>
            </div>
          </motion.main>
        ) : (
          <motion.div 
            key="boot-sequence"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex flex-col items-center justify-center font-mono space-y-4 z-50 p-10 max-w-2xl w-full"
          >
            {BOOT_SEQUENCE.map((line, idx) => (
              <motion.div
                key={idx}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: idx <= bootStage ? 1 : 0, x: idx <= bootStage ? 0 : -20 }}
                transition={{ duration: 0.1 }}
                className={`text-lg md:text-xl font-bold ${line.includes('[!]') ? 'text-primary' : 'text-white'}`}
              >
                {line}
              </motion.div>
            ))}
            <motion.div 
              animate={{ opacity: [1, 0, 1] }} 
              transition={{ repeat: Infinity, duration: 0.8 }}
              className="w-4 h-6 bg-primary mt-4"
            />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
