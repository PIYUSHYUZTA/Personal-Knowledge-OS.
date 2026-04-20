import React, { useState, useEffect, useRef, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Coffee, AlertTriangle, Zap, Timer } from 'lucide-react'

// ═══════════════════════════════════════════════════════════════
// CAFFEINE TRACKER — The Survival Widget
// Session intensity meter, grind timer, procrastination detection.
// ═══════════════════════════════════════════════════════════════

const IDLE_THRESHOLD_MS = 10 * 60 * 1000 // 10 minutes
const INTENSITY_DECAY_RATE = 0.003        // % per second of idle decay
const INTENSITY_BOOST = 8                 // boost per activity burst

function formatDuration(ms: number): string {
  const totalSec = Math.floor(ms / 1000)
  const h = Math.floor(totalSec / 3600)
  const m = Math.floor((totalSec % 3600) / 60)
  const s = totalSec % 60
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
}

// Status thresholds
function getStatus(intensity: number, isIdle: boolean) {
  if (isIdle) return { label: 'FOCUS DRIFT', color: '#EF4444', pulse: true }
  if (intensity > 80) return { label: 'OVERDRIVE', color: '#FF5722', pulse: false }
  if (intensity > 50) return { label: 'LOCKED IN', color: '#22C55E', pulse: false }
  if (intensity > 25) return { label: 'WARMING UP', color: '#F59E0B', pulse: false }
  return { label: 'COLD START', color: '#6B7280', pulse: false }
}

export default function CaffeineWidget() {
  const [sessionStart] = useState(Date.now())
  const [elapsed, setElapsed] = useState(0)
  const [intensity, setIntensity] = useState(15)
  const [lastActivity, setLastActivity] = useState(Date.now())
  const [isIdle, setIsIdle] = useState(false)
  const [activityBursts, setActivityBursts] = useState(0)
  const frameRef = useRef<number>(0)

  // Track keyboard/mouse activity globally
  const handleActivity = useCallback(() => {
    setLastActivity(Date.now())
    setIsIdle(false)
    setActivityBursts(prev => prev + 1)
  }, [])

  useEffect(() => {
    // Throttled listener — only react to bursts, not every keystroke
    let throttleTimer: ReturnType<typeof setTimeout> | null = null
    const throttledActivity = () => {
      if (!throttleTimer) {
        handleActivity()
        throttleTimer = setTimeout(() => { throttleTimer = null }, 2000)
      }
    }

    window.addEventListener('keydown', throttledActivity)
    window.addEventListener('mousemove', throttledActivity)
    window.addEventListener('click', throttledActivity)
    window.addEventListener('scroll', throttledActivity)

    return () => {
      window.removeEventListener('keydown', throttledActivity)
      window.removeEventListener('mousemove', throttledActivity)
      window.removeEventListener('click', throttledActivity)
      window.removeEventListener('scroll', throttledActivity)
      if (throttleTimer) clearTimeout(throttleTimer)
    }
  }, [handleActivity])

  // Main tick loop
  useEffect(() => {
    let prevBursts = activityBursts

    const tick = () => {
      const now = Date.now()
      setElapsed(now - sessionStart)

      // Idle detection
      const idleTime = now - lastActivity
      if (idleTime >= IDLE_THRESHOLD_MS) {
        setIsIdle(true)
      }

      // Intensity dynamics
      setIntensity(prev => {
        let next = prev
        // Decay when idle
        if (idleTime > 5000) {
          next -= INTENSITY_DECAY_RATE * (idleTime / 1000)
        }
        // Boost on activity bursts
        if (activityBursts > prevBursts) {
          next += INTENSITY_BOOST * (activityBursts - prevBursts) * 0.3
          prevBursts = activityBursts
        }
        return Math.max(0, Math.min(100, next))
      })

      frameRef.current = requestAnimationFrame(tick)
    }

    frameRef.current = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(frameRef.current)
  }, [sessionStart, lastActivity, activityBursts])

  const status = getStatus(intensity, isIdle)

  return (
    <div className="h-full flex flex-col p-4 gap-3 select-none font-mono text-[#A1A1AA] overflow-hidden relative">

      {/* Background pulse when idle */}
      <AnimatePresence>
        {isIdle && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: [0.05, 0.15, 0.05] }}
            exit={{ opacity: 0 }}
            transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
            className="absolute inset-0 bg-red-500 pointer-events-none rounded-xl z-0"
          />
        )}
      </AnimatePresence>

      {/* Header */}
      <div className="flex items-center justify-between relative z-10">
        <div className="flex items-center gap-2">
          <motion.div
            animate={isIdle ? { rotate: [0, -10, 10, -10, 0] } : { rotate: 0 }}
            transition={isIdle ? { duration: 0.5, repeat: Infinity, repeatDelay: 1 } : {}}
          >
            {isIdle ? (
              <AlertTriangle size={16} className="text-red-400" />
            ) : (
              <Coffee size={16} className="text-[#FF5722]" />
            )}
          </motion.div>
          <span className="text-[10px] uppercase tracking-[0.2em] text-[#52525B]">
            Session Vitals
          </span>
        </div>
        <motion.div
          animate={status.pulse ? { scale: [1, 1.15, 1], opacity: [1, 0.6, 1] } : {}}
          transition={status.pulse ? { duration: 1.2, repeat: Infinity } : {}}
          className="flex items-center gap-1.5"
        >
          <span
            className="w-1.5 h-1.5 rounded-full"
            style={{ backgroundColor: status.color, boxShadow: `0 0 8px ${status.color}80` }}
          />
          <span className="text-[9px] font-bold tracking-wider" style={{ color: status.color }}>
            {status.label}
          </span>
        </motion.div>
      </div>

      {/* Grind Timer */}
      <div className="relative z-10 bg-[#0B0F19]/60 rounded-lg p-3 border border-[#27272A]/40">
        <div className="flex items-center gap-2 mb-1">
          <Timer size={11} className="text-[#52525B]" />
          <span className="text-[8px] uppercase tracking-[0.25em] text-[#52525B]">
            Session Duration
          </span>
        </div>
        <div className="text-2xl font-bold tracking-[0.15em] text-[#ECECEF] tabular-nums">
          {formatDuration(elapsed)}
        </div>
      </div>

      {/* Intensity Meter */}
      <div className="relative z-10 flex-1 flex flex-col gap-1.5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5">
            <Zap size={11} className="text-[#FF5722]" />
            <span className="text-[8px] uppercase tracking-[0.25em] text-[#52525B]">
              Session Intensity
            </span>
          </div>
          <span className="text-[11px] font-bold tabular-nums" style={{ color: status.color }}>
            {Math.round(intensity)}%
          </span>
        </div>

        {/* Vertical bar meter */}
        <div className="flex-1 min-h-[60px] relative bg-[#0B0F19]/60 rounded-lg border border-[#27272A]/40 overflow-hidden">
          {/* Grid lines */}
          {[25, 50, 75].map(line => (
            <div
              key={line}
              className="absolute left-0 right-0 border-t border-[#27272A]/30"
              style={{ bottom: `${line}%` }}
            >
              <span className="absolute right-1 -top-2.5 text-[7px] text-[#3F3F46]">{line}</span>
            </div>
          ))}

          {/* Fill bar */}
          <motion.div
            className="absolute bottom-0 left-0 right-0"
            animate={{ height: `${intensity}%` }}
            transition={{ type: 'spring', damping: 20, stiffness: 100 }}
            style={{
              background: `linear-gradient(to top, ${status.color}30, ${status.color}90)`,
              boxShadow: `0 -4px 20px ${status.color}40`,
            }}
          >
            {/* Glow top edge */}
            <div
              className="absolute top-0 left-0 right-0 h-[2px]"
              style={{ background: status.color, boxShadow: `0 0 12px ${status.color}` }}
            />
          </motion.div>

          {/* Animated scan line */}
          <motion.div
            animate={{ y: ['0%', '100%', '0%'] }}
            transition={{ duration: 8, repeat: Infinity, ease: 'linear' }}
            className="absolute left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-[#FF5722]/20 to-transparent"
          />
        </div>
      </div>

      {/* Idle Warning Banner */}
      <AnimatePresence>
        {isIdle && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 10 }}
            className="relative z-10 bg-red-500/10 border border-red-500/30 rounded-lg p-2 text-center"
          >
            <motion.p
              animate={{ opacity: [1, 0.4, 1] }}
              transition={{ duration: 1.5, repeat: Infinity }}
              className="text-[9px] font-bold tracking-[0.2em] text-red-400 uppercase"
            >
              ⚠ Warning: Focus Drift Detected
            </motion.p>
            <p className="text-[8px] text-red-400/60 mt-0.5">
              No activity for {formatDuration(Date.now() - lastActivity)}
            </p>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Micro footer with activity count */}
      <div className="relative z-10 flex items-center justify-between text-[8px] text-[#3F3F46] pt-1 border-t border-[#27272A]/30">
        <span>BURSTS: {activityBursts}</span>
        <span className="flex items-center gap-1">
          <span className="w-1 h-1 rounded-full bg-[#FF5722] animate-pulse" />
          LIVE
        </span>
      </div>
    </div>
  )
}
