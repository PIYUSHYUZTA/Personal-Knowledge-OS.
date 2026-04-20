import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '@/context/AuthContext'
import { Loader2, ArrowRight, Eye, EyeOff, ScanFace, TerminalSquare, AlertTriangle, ShieldCheck } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import { Turnstile } from '@marsidev/react-turnstile'
import AuthBackground from '@/components/auth/AuthBackground'

// ── Audio Feedback ───────────────────────────────────────────
const playBootSound = () => {
    try {
        const AudioContext = window.AudioContext || (window as any).webkitAudioContext;
        if (!AudioContext) return;
        const ctx = new AudioContext();
        
        // Mechanical click
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.type = 'square';
        osc.frequency.setValueAtTime(150, ctx.currentTime);
        osc.frequency.exponentialRampToValueAtTime(40, ctx.currentTime + 0.1);
        gain.gain.setValueAtTime(0.1, ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.1);
        osc.start(ctx.currentTime);
        osc.stop(ctx.currentTime + 0.1);

        // Digital Hum building up
        const humOsc = ctx.createOscillator();
        const humGain = ctx.createGain();
        humOsc.connect(humGain);
        humGain.connect(ctx.destination);
        humOsc.type = 'sawtooth';
        humOsc.frequency.setValueAtTime(50, ctx.currentTime);
        humGain.gain.setValueAtTime(0, ctx.currentTime);
        humGain.gain.linearRampToValueAtTime(0.08, ctx.currentTime + 0.5);
        humGain.gain.linearRampToValueAtTime(0, ctx.currentTime + 1.5);
        humOsc.start(ctx.currentTime);
        humOsc.stop(ctx.currentTime + 1.5);
    } catch(e) { /* ignore audio errors */ }
}

// Ascending confirmation tone (plays on biometric success)
const playVerifySound = () => {
    try {
        const AudioContext = window.AudioContext || (window as any).webkitAudioContext;
        if (!AudioContext) return;
        const ctx = new AudioContext();

        // Two-note ascending chime
        const osc1 = ctx.createOscillator();
        const gain1 = ctx.createGain();
        osc1.connect(gain1);
        gain1.connect(ctx.destination);
        osc1.type = 'sine';
        osc1.frequency.setValueAtTime(600, ctx.currentTime);
        gain1.gain.setValueAtTime(0.08, ctx.currentTime);
        gain1.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.25);
        osc1.start(ctx.currentTime);
        osc1.stop(ctx.currentTime + 0.25);

        const osc2 = ctx.createOscillator();
        const gain2 = ctx.createGain();
        osc2.connect(gain2);
        gain2.connect(ctx.destination);
        osc2.type = 'sine';
        osc2.frequency.setValueAtTime(900, ctx.currentTime + 0.15);
        gain2.gain.setValueAtTime(0, ctx.currentTime);
        gain2.gain.linearRampToValueAtTime(0.07, ctx.currentTime + 0.15);
        gain2.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.5);
        osc2.start(ctx.currentTime + 0.15);
        osc2.stop(ctx.currentTime + 0.5);
    } catch(e) { /* ignore audio errors */ }
}

const BOOT_SEQUENCE = [
  "[OK] Kernel Loaded",
  "[OK] Mounting Personal Knowledge Graph",
  "[OK] Bypassing Sleep Mode",
  "[OK] Focus Protocol: ENGAGED",
  "[!] Caffeine Levels: Critical but Stable"
]

// ── Biometric scan states ────────────────────────────────────
type BiometricState = 'idle' | 'scanning' | 'success' | 'error'

export default function LoginPage() {
  const navigate = useNavigate()
  // ── FIX: Destructure loginAsBiometric so biometric scan updates AuthContext state ──
  const { login, loginAsBiometric, isLoading, error } = useAuth()
  
  const [email, setEmail] = React.useState('')
  const [password, setPassword] = React.useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [capsLockActive, setCapsLockActive] = useState(false)
  const [captchaToken, setCaptchaToken] = useState<string | null>(null)
  const [greeting, setGreeting] = useState("Let's get this done.")
  const [logs, setLogs] = useState<string[]>([])
  
  // Boot Sequence States
  const [isBooting, setIsBooting] = useState(false)
  const [bootStage, setBootStage] = useState(-1)
  const [glitch, setGlitch] = useState(false)
  
  // Biometric Mock States
  const [bioState, setBioState] = useState<BiometricState>('idle')
  const [scanProgress, setScanProgress] = useState(0)

  // Time-Aware Greeting Logic
  useEffect(() => {
    const hour = new Date().getHours()
    if (hour < 5 || hour >= 23) setGreeting("Still awake? Let's get this done.")
    else if (hour >= 5 && hour < 12) setGreeting("Late start? Make it count.")
    else if (hour >= 12 && hour < 18) setGreeting("Afternoon grind. Stay focused.")
    else setGreeting("Evening push. Initializing focus mode.")
  }, [])

  // Terminal Micro-Logs Simulation
  useEffect(() => {
    if (isBooting) return;
    const startupLogs = [
        "[SYSTEM]: Diagnostics OK.",
        "[SYSTEM]: Establishing secure uplink...",
        "[SYSTEM]: Caffeine levels critical.",
        "[SYSTEM]: Initializing one-night-stand productivity mode."
    ]
    let currentLog = 0
    const interval = setInterval(() => {
        if (currentLog < startupLogs.length) {
            setLogs(prev => [...prev, startupLogs[currentLog]])
            currentLog++
        } else {
            clearInterval(interval)
        }
    }, 800)
    return () => clearInterval(interval)
  }, [isBooting])

  // Caps Lock Detector
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
        if (e.getModifierState && e.getModifierState('CapsLock')) {
            setCapsLockActive(true)
        } else {
            setCapsLockActive(false)
        }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])

  // Boot Sequence Orchestration
  useEffect(() => {
      if (!isBooting) return;
      
      playBootSound();
      
      const stepTime = 1200 / BOOT_SEQUENCE.length; 
      
      let step = 0;
      const interval = setInterval(() => {
          setBootStage(step);
          step++;
          if (step >= BOOT_SEQUENCE.length) {
              clearInterval(interval);
              setTimeout(() => {
                  setGlitch(true);
                  setTimeout(() => {
                      navigate('/');
                  }, 200);
              }, 400);
          }
      }, stepTime);

      return () => clearInterval(interval);
  }, [isBooting, navigate])

  const triggerSystemBoot = () => {
      setIsBooting(true)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!captchaToken) return 
    try {
      await login(email, password)
      triggerSystemBoot()
    } catch {
      // Error handled by context
    }
  }

  // ── Robust Mock WebAuthn / Biometric Flow ──────────────────────
  // FIXED: Now calls loginAsBiometric() from AuthContext instead of
  // writing localStorage directly. This sets BOTH the token AND the
  // user object in React state, so ProtectedRoute allows navigation.
  // ───────────────────────────────────────────────────────────────
  const handleBiometricScan = async () => {
      if (bioState === 'scanning') return;

      setBioState('scanning')
      setScanProgress(0)
      setLogs(prev => [...prev, "[BIOMETRIC]: Initializing FaceID / TouchID sensor..."])

      // Animate scan progress over 1.8 seconds
      const scanDuration = 1800
      const startTime = Date.now()
      
      const progressInterval = setInterval(() => {
          const elapsed = Date.now() - startTime
          const progress = Math.min((elapsed / scanDuration) * 100, 100)
          setScanProgress(progress)
          
          // Add log entries at specific progress milestones
          if (progress > 30 && progress < 32) {
            setLogs(prev => {
              if (prev[prev.length - 1]?.includes('Mapping')) return prev
              return [...prev, "[BIOMETRIC]: Mapping facial geometry..."]
            })
          }
          if (progress > 70 && progress < 72) {
            setLogs(prev => {
              if (prev[prev.length - 1]?.includes('Verifying')) return prev
              return [...prev, "[BIOMETRIC]: Verifying neural signature..."]
            })
          }
          
          if (progress >= 100) {
              clearInterval(progressInterval)
          }
      }, 30)

      // After scan completes, verify "biometric"
      setTimeout(() => {
          clearInterval(progressInterval)
          setScanProgress(100)
          
          playVerifySound()
          setLogs(prev => [...prev, "[BIOMETRIC]: ✓ Scan complete. Identity verified."])
          setBioState('success')

          // ── THE FIX: Call loginAsBiometric() from AuthContext ──
          // This sets user state reactively. Without this call,
          // ProtectedRoute sees user=null and blocks navigation.
          loginAsBiometric()

          // Brief pause to show success state, then boot
          setTimeout(() => {
              triggerSystemBoot()
          }, 600)
      }, scanDuration)
  }

  return (
    <div className={`flex relative min-h-screen items-center justify-center bg-[#0B0F19] text-[#ECECEF] overflow-hidden selection:bg-[#FF5722]/30 selection:text-[#FF5722] ${glitch ? 'invert' : ''}`}>
      
      {/* The Digital Void Background */}
      <AuthBackground />
      
      {/* Terminal Micro-Logs */}
      {!isBooting && (
          <div className="absolute top-6 left-6 font-mono text-[10px] sm:text-xs text-[#71717A] max-w-sm pointer-events-none z-0">
              <AnimatePresence>
                {logs.map((log, i) => (
                    <motion.div 
                       key={i} 
                       initial={{ opacity: 0, x: -10 }} 
                       animate={{ opacity: 1, x: 0 }} 
                       className="mb-1 flex items-center gap-2"
                    >
                       <TerminalSquare className="w-3 h-3 text-[#FF5722]/70" />
                       {log}
                    </motion.div>
                ))}
              </AnimatePresence>
          </div>
      )}

      {/* ═══════════════════════════════════════════════════════════
          APPLE-STYLE FaceID OVERLAY
          Full-screen overlay with viewfinder brackets, scan line,
          and radial pulse rings. Shows during scanning and success.
          ═══════════════════════════════════════════════════════════ */}
      <AnimatePresence>
        {bioState === 'scanning' && !isBooting && (
          <motion.div
            key="faceid-scan-overlay"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.3 }}
            className="fixed inset-0 z-50 flex flex-col items-center justify-center"
            style={{ backgroundColor: 'rgba(11, 15, 25, 0.88)' }}
          >
            {/* Radial pulse rings emanating outward */}
            {[0, 1, 2].map(i => (
              <motion.div
                key={`ring-${i}`}
                className="absolute rounded-full border border-[#FF5722]/15"
                style={{ width: 120, height: 120 }}
                animate={{ 
                  width: [120, 420], 
                  height: [120, 420], 
                  opacity: [0.5, 0] 
                }}
                transition={{
                  duration: 2.2,
                  repeat: Infinity,
                  delay: i * 0.7,
                  ease: 'easeOut'
                }}
              />
            ))}

            {/* Face viewfinder frame */}
            <div className="relative w-52 h-64 flex items-center justify-center">
              {/* Corner brackets — Apple FaceID style */}
              <div className="absolute top-0 left-0 w-10 h-10 border-t-2 border-l-2 border-[#FF5722]/70 rounded-tl-2xl" />
              <div className="absolute top-0 right-0 w-10 h-10 border-t-2 border-r-2 border-[#FF5722]/70 rounded-tr-2xl" />
              <div className="absolute bottom-0 left-0 w-10 h-10 border-b-2 border-l-2 border-[#FF5722]/70 rounded-bl-2xl" />
              <div className="absolute bottom-0 right-0 w-10 h-10 border-b-2 border-r-2 border-[#FF5722]/70 rounded-br-2xl" />

              {/* Horizontal scan line sweeping vertically */}
              <motion.div
                className="absolute left-2 right-2 h-[2px] bg-gradient-to-r from-transparent via-[#FF5722] to-transparent shadow-[0_0_12px_rgba(255,87,34,0.6)]"
                animate={{ top: ['8%', '88%', '8%'] }}
                transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
              />

              {/* Face icon within viewfinder */}
              <ScanFace className="w-14 h-14 text-[#FF5722]/30" />
            </div>

            {/* Status text + progress */}
            <motion.div 
              className="mt-10 flex flex-col items-center gap-2"
              animate={{ opacity: [1, 0.5, 1] }}
              transition={{ duration: 1.5, repeat: Infinity }}
            >
              <p className="text-[#FF5722] font-mono text-sm tracking-[0.25em] uppercase">
                Scanning Biometrics
              </p>
              <div className="w-48 h-[2px] bg-[#27272A] rounded-full overflow-hidden">
                <motion.div 
                  className="h-full bg-gradient-to-r from-[#FF5722] to-[#FF9800]"
                  style={{ width: `${scanProgress}%` }}
                />
              </div>
              <p className="text-[#52525B] font-mono text-xs tabular-nums">
                {Math.round(scanProgress)}%
              </p>
            </motion.div>
          </motion.div>
        )}

        {bioState === 'success' && !isBooting && (
          <motion.div
            key="faceid-success-overlay"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.25 }}
            className="fixed inset-0 z-50 flex flex-col items-center justify-center gap-6"
            style={{ backgroundColor: 'rgba(11, 15, 25, 0.92)' }}
          >
            <motion.div
              initial={{ scale: 0, rotate: -90 }}
              animate={{ scale: 1, rotate: 0 }}
              transition={{ type: 'spring', damping: 12, stiffness: 180 }}
            >
              <div className="w-20 h-20 rounded-full bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center shadow-[0_0_40px_rgba(52,211,153,0.2)]">
                <ShieldCheck className="w-10 h-10 text-emerald-400" />
              </div>
            </motion.div>
            <motion.p
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
              className="text-emerald-400 font-mono text-base tracking-[0.3em] uppercase"
            >
              Identity Verified
            </motion.p>
            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.4 }}
              className="text-[#52525B] font-mono text-xs"
            >
              Initializing session...
            </motion.p>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Main Glassmorphism Card */}
      <motion.div
        layout
        initial={{ opacity: 0, scale: 0.95, y: 10 }}
        animate={{ 
            opacity: 1, 
            scale: 1, 
            y: 0,
            width: isBooting ? '100vw' : '100%',
            height: isBooting ? '100vh' : 'auto',
            borderRadius: isBooting ? 0 : 16
        }}
        transition={{ duration: 0.6, ease: [0.23, 1, 0.32, 1] }}
        className={`px-4 relative z-10 w-full ${isBooting ? 'max-w-none flex items-center justify-center' : 'max-w-[440px]'}`}
      >
        <motion.div 
            layout
            className={`w-full flex flex-col items-center border shadow-[0_8px_32px_rgba(0,0,0,0.8)] relative overflow-hidden backdrop-blur-2xl bg-[#1A1B22]/70 ${isBooting ? 'h-full justify-center border-none' : 'rounded-2xl p-8 sm:p-10 border-[#27272A]/60'}`}
        >
          {/* Noise overlay for smudged look */}
          <div className="absolute inset-0 opacity-10 pointer-events-none bg-[url('data:image/svg+xml,%3Csvg viewBox=%220 0 200 200%22 xmlns=%22http://www.w3.org/2000/svg%22%3E%3Cfilter id=%22noise%22%3E%3CfeTurbulence type=%22fractalNoise%22 baseFrequency=%220.8%22 numOctaves=%224%22 stitchTiles=%22stitch%22/%3E%3C/filter%3E%3Crect width=%22100%25%22 height=%22100%25%22 filter=%22url(%23noise)%22/%3E%3C/svg%3E')]" />

          {/* Accent glow strip */}
          <motion.div layout className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-[#FF5722] to-transparent opacity-80" />

          <AnimatePresence mode="wait">
            {!isBooting ? (
              <motion.div 
                key="login-form"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
                transition={{ duration: 0.3 }}
                className="w-full flex flex-col items-center"
              >
                  {/* Header */}
                  <div className="w-12 h-12 rounded-xl border border-[#27272A] bg-[#09090B] flex items-center justify-center font-mono font-bold text-lg shadow-[0_0_15px_rgba(255,87,34,0.15)] mb-6 relative group overflow-hidden">
                    <span className="relative z-10 text-[#ECECEF]">OS</span>
                    <div className="absolute inset-0 bg-[#FF5722]/20 translate-y-full group-hover:translate-y-0 transition-transform duration-300" />
                  </div>

                  <h1 className="text-2xl font-semibold mb-1.5 text-center tracking-tight text-white">{greeting}</h1>
                  <p className="text-sm text-[#A1A1AA] mb-8 text-center px-4 font-mono">Authenticate to access session</p>

                  {error && (
                    <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        className="w-full overflow-hidden"
                    >
                        <div className="bg-red-500/10 border border-red-500/20 text-red-400 text-[13px] font-mono p-3 rounded-lg mb-6 flex items-start gap-2 backdrop-blur-md">
                        <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
                        <span>{error}</span>
                        </div>
                    </motion.div>
                  )}

                  {/* ── Biometric Authentication Button ─────────────── */}
                  <button 
                    type="button"
                    onClick={handleBiometricScan}
                    disabled={bioState === 'scanning' || bioState === 'success'}
                    className={`w-full mb-6 border text-[#ECECEF] font-medium py-3.5 rounded-xl transition-all flex items-center justify-center gap-3 shadow-sm group relative overflow-hidden ${
                      bioState === 'scanning' 
                        ? 'bg-[#0B0F19] border-[#FF5722]/40 cursor-wait' 
                        : bioState === 'success'
                        ? 'bg-emerald-500/10 border-emerald-500/40 cursor-default'
                        : 'bg-[#09090B] hover:bg-[#1A1B22] border-[#27272A] hover:border-[#FF5722]/50 cursor-pointer'
                    }`}
                  >
                    {/* Background gradient sweep */}
                    <div className="absolute inset-0 bg-gradient-to-r from-transparent via-[#FF5722]/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity rounded-xl pointer-events-none" />

                    {bioState === 'scanning' ? (
                      <>
                        <div className="relative w-5 h-5">
                          <motion.div
                            animate={{ rotate: 360 }}
                            transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                            className="absolute inset-0 rounded-full border-2 border-transparent border-t-[#FF5722] border-r-[#FF5722]/50"
                          />
                          <ScanFace className="w-3 h-3 absolute inset-0 m-auto text-[#FF5722]" />
                        </div>
                        <motion.span 
                          animate={{ opacity: [1, 0.5, 1] }}
                          transition={{ duration: 1.2, repeat: Infinity }}
                          className="text-sm font-mono tracking-wider text-[#FF5722]"
                        >
                          SCANNING...
                        </motion.span>
                      </>
                    ) : bioState === 'success' ? (
                      <>
                        <motion.div
                          initial={{ scale: 0 }}
                          animate={{ scale: 1 }}
                          transition={{ type: 'spring', damping: 10, stiffness: 200 }}
                        >
                          <ShieldCheck className="w-5 h-5 text-emerald-400" />
                        </motion.div>
                        <span className="text-sm font-mono tracking-wider text-emerald-400">IDENTITY VERIFIED</span>
                      </>
                    ) : (
                      <>
                        <ScanFace className="w-5 h-5 text-[#FF5722] group-hover:scale-110 transition-transform" />
                        <span className="text-sm font-mono tracking-wide">Initialize via FaceID / TouchID</span>
                      </>
                    )}
                  </button>

                  <div className="w-full flex items-center gap-4 mb-6">
                      <div className="flex-1 h-[1px] bg-[#27272A]" />
                      <span className="text-[10px] font-mono text-[#52525B] uppercase tracking-widest">or manual override</span>
                      <div className="flex-1 h-[1px] bg-[#27272A]" />
                  </div>

                  <form onSubmit={handleSubmit} className="space-y-4 w-full">
                    <div className="space-y-1.5 relative">
                      <label className="block text-[10px] font-mono text-[#A1A1AA] uppercase tracking-wider">Target Identity</label>
                      <input
                        id="login-email"
                        type="email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        className="w-full px-4 py-3 border border-[#27272A] rounded-xl bg-[#09090B]/50 text-[#ECECEF] placeholder:text-[#52525B] focus:ring-1 focus:ring-[#FF5722] focus:border-[#FF5722] transition-all outline-none text-sm font-mono backdrop-blur-sm"
                        placeholder="root@system.local"
                      />
                    </div>

                    <div className="space-y-1.5 relative">
                      <div className="flex items-center justify-between">
                        <label className="block text-[10px] font-mono text-[#A1A1AA] uppercase tracking-wider">Passphrase</label>
                      </div>
                      <div className="relative">
                        <input
                            id="login-password"
                            type={showPassword ? 'text' : 'password'}
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            className="w-full px-4 py-3 pr-10 border border-[#27272A] rounded-xl bg-[#09090B]/50 text-[#ECECEF] placeholder:text-[#52525B] focus:ring-1 focus:ring-[#FF5722] focus:border-[#FF5722] transition-all outline-none text-sm font-mono backdrop-blur-sm"
                            placeholder="••••••••"
                        />
                        <button 
                          type="button" 
                          onClick={() => setShowPassword(!showPassword)}
                          className="absolute right-3 top-1/2 -translate-y-1/2 text-[#71717A] hover:text-[#ECECEF] transition-colors"
                        >
                            {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                        </button>
                      </div>
                      
                      {/* Caps Lock Warning Tooltip */}
                      <AnimatePresence>
                        {capsLockActive && (
                            <motion.div 
                                initial={{ opacity: 0, y: -5 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -5 }}
                                className="absolute -top-8 right-0 bg-[#FF5722]/10 border border-[#FF5722]/30 text-[#FF5722] text-[10px] px-2 py-1 rounded backdrop-blur-md flex items-center gap-1 font-mono"
                            >
                                <AlertTriangle className="w-3 h-3" /> CAPS LOCK ON
                            </motion.div>
                        )}
                      </AnimatePresence>
                    </div>

                    {/* Turnstile Captcha */}
                    <div className="w-full flex justify-center py-2" style={{ colorScheme: 'dark' }}>
                        <Turnstile 
                          siteKey="1x00000000000000000000AA"
                          onSuccess={(token) => setCaptchaToken(token)}
                          options={{ theme: 'dark' }}
                        />
                    </div>

                    <button
                      id="login-submit"
                      type="submit"
                      disabled={isLoading || !email || !password || !captchaToken}
                      className="w-full mt-2 bg-[#FF5722] hover:bg-[#E64A19] text-white font-mono font-medium py-3 rounded-xl transition-all shadow-[0_0_15px_rgba(255,87,34,0.3)] flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed active:scale-[0.98] group text-sm tracking-widest"
                    >
                      {isLoading ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <>
                          INITIALIZE SESSION
                          <ArrowRight className="w-4 h-4 opacity-70 group-hover:translate-x-1 group-hover:opacity-100 transition-all" />
                        </>
                      )}
                    </button>
                  </form>

                  <p className="text-center text-[10px] uppercase font-mono text-[#52525B] mt-8">
                    Access strictly restricted. <br/>
                    <button
                      onClick={() => navigate('/register')}
                      className="text-[#FF5722] hover:text-[#FF5722]/80 font-bold transition-colors cursor-pointer mt-1"
                    >
                      Request Clearance
                    </button>
                  </p>
              </motion.div>
            ) : (
              <motion.div 
                 key="boot-sequence"
                 initial={{ opacity: 0 }}
                 animate={{ opacity: 1 }}
                 transition={{ delay: 0.3 }}
                 className="flex flex-col items-center justify-center font-mono space-y-4"
              >
                  {BOOT_SEQUENCE.map((line, idx) => (
                      <motion.div
                          key={idx}
                          initial={{ opacity: 0, y: 10 }}
                          animate={{ opacity: idx <= bootStage ? 1 : 0, y: idx <= bootStage ? 0 : 10 }}
                          transition={{ duration: 0.1 }}
                          className={`text-lg md:text-xl font-bold ${line.includes('[!]') ? 'text-[#FF5722]' : 'text-white'}`}
                      >
                          {line}
                      </motion.div>
                  ))}
                  <motion.div 
                     animate={{ opacity: [1, 0, 1] }} 
                     transition={{ repeat: Infinity, duration: 0.8 }}
                     className="w-4 h-6 bg-[#FF5722] mt-4"
                  />
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>
      </motion.div>
    </div>
  )
}
