import React, { useState, useCallback, useEffect } from 'react'
import { motion, useDragControls, AnimatePresence, useMotionValue } from 'framer-motion'
import { useDesktopStore, AppWindow } from '@/store/useDesktopStore'
import { X, Minus } from 'lucide-react'
// App Components
import KnowledgeVisualizer from '@/components/knowledge/KnowledgeVisualizer'
import AuraChat from '@/components/aura/AuraChat'
import FileUploader from '@/components/ingestion/FileUploader'
import CaffeineWidget from '@/components/desktop/CaffeineWidget'

// Anti-Gravity idle sway config per window (seeded randomness via id hash)
function getSwayConfig(id: string) {
    let hash = 0
    for (let i = 0; i < id.length; i++) hash = ((hash << 5) - hash) + id.charCodeAt(i)
    const seed = Math.abs(hash)
    return {
        duration: 6 + (seed % 4),        // 6-10s period
        yAmplitude: 2 + (seed % 3),       // 2-5px drift (subtle)
        delay: (seed % 3) * 0.8           // stagger start
    }
}

export default function Window({ window: win }: { window: AppWindow }) {
  const { closeWindow, focusWindow, toggleMinimize, updateWindowPosition, activeWindowId, zenMode } = useDesktopStore()
  const controls = useDragControls()
  const [isDragging, setIsDragging] = useState(false)
  
  const isActive = activeWindowId === win.id
  const sway = getSwayConfig(win.id)

  // ─── MOTION VALUES ─────────────────────────────────────────
  // Using useMotionValue for x/y gives Framer Motion direct
  // ownership of the position during drag, eliminating the
  // jitter caused by reading info.point (cursor coords ≠ element coords).
  const motionX = useMotionValue(win.position.x)
  const motionY = useMotionValue(win.position.y)

  // Sync store → motion values when position changes externally
  // (e.g. window opened at a new position, or restored from minimize).
  // Skip during drag to avoid fighting Framer Motion's internal state.
  useEffect(() => {
    if (!isDragging) {
      motionX.set(win.position.x)
      motionY.set(win.position.y)
    }
  }, [win.position.x, win.position.y, isDragging, motionX, motionY])
  
  // Zen Mode fading
  const opacityClass = zenMode ? (isActive ? 'opacity-100' : 'opacity-[0.15] pointer-events-none blur-[2px]') : 'opacity-100'

  const handleDragStart = useCallback(() => {
      setIsDragging(true)
  }, [])

  // ─── FIX: Read final position from motion values, not info.point ───
  // Previously used info.point which gives cursor viewport coordinates,
  // NOT the element's actual position → caused teleportation on drop.
  const handleDragEnd = useCallback(() => {
      setIsDragging(false)
      updateWindowPosition(win.id, { x: motionX.get(), y: motionY.get() })
  }, [win.id, updateWindowPosition, motionX, motionY])

  // Render Inner App Component
  const renderApp = () => {
      switch (win.appType) {
          case 'knowledge': return <KnowledgeVisualizer />
          case 'aura': return <AuraChat />
          case 'ingestion': return <div className="p-8 h-full overflow-auto"><FileUploader /></div>
          case 'settings': return <div className="p-8 text-[#A1A1AA] font-mono text-sm leading-relaxed"><p className="text-[#FF5722] mb-4 text-lg font-bold">⚙ SYSTEM SETTINGS</p><p className="text-[#52525B]">Configuration module pending deployment.</p></div>
          case 'caffeine': return <CaffeineWidget />
          default: return <div className="p-4">Unknown App</div>
      }
  }

  // ─── ARCHITECTURE ───────────────────────────────────────────────
  // OUTER motion.div = DRAG LAYER (handles position via motionX/motionY)
  // INNER motion.div = SWAY LAYER (handles idle floating animation)
  //
  // This separation prevents the drag system from fighting the
  // infinite y-keyframe loop that causes jitter/snap glitches.
  // ────────────────────────────────────────────────────────────────

  return (
    <AnimatePresence>
      {!win.isMinimized && (
        /* ── DRAG LAYER ─────────────────────────────────────────── */
        <motion.div
           initial={{ opacity: 0, scale: 0.9 }}
           animate={{ opacity: 1, scale: 1 }}
           exit={{ opacity: 0, scale: 0.9 }}
           transition={{ opacity: { duration: 0.3 }, scale: { duration: 0.3 } }}
           onPointerDown={() => focusWindow(win.id)}
           drag
           dragControls={controls}
           dragListener={false}
           dragMomentum={false}
           dragElastic={0}
           onDragStart={handleDragStart}
           onDragEnd={handleDragEnd}
           style={{ 
               zIndex: win.zIndex,
               width: win.size.width,
               height: win.size.height,
               x: motionX,
               y: motionY,
           }}
           className={`absolute pointer-events-auto ${opacityClass}`}
        >
          {/* ── SWAY LAYER ──────────────────────────────────────── */}
          <motion.div
             animate={isDragging 
               ? { y: 0 }
               : { y: [0, -sway.yAmplitude, 0] }
             }
             transition={isDragging 
               ? { type: 'tween', duration: 0.08 }
               : { 
                   y: { duration: sway.duration, repeat: Infinity, ease: 'easeInOut', delay: sway.delay },
                 }
             }
             className="w-full h-full flex flex-col rounded-xl border border-[#27272A]/70 shadow-[0_12px_48px_rgba(0,0,0,0.6)] overflow-hidden backdrop-blur-2xl bg-[#1A1B22]/80 transition-opacity duration-500"
          >
            {/* Smudged Texture Overlay */}
            <div className="absolute inset-0 opacity-[0.15] pointer-events-none bg-[url('data:image/svg+xml,%3Csvg viewBox=%220 0 200 200%22 xmlns=%22http://www.w3.org/2000/svg%22%3E%3Cfilter id=%22noise%22%3E%3CfeTurbulence type=%22fractalNoise%22 baseFrequency=%220.85%22 numOctaves=%223%22 stitchTiles=%22stitch%22/%3E%3C/filter%3E%3Crect width=%22100%25%22 height=%22100%25%22 filter=%22url(%23noise)%22/%3E%3C/svg%3E')]" />

            {/* Active window accent glow */}
            {isActive && (
               <div className="absolute top-0 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-[#FF5722]/50 to-transparent z-20" />
            )}

            {/* Title Bar - Drag Handle */}
            <div 
               className="h-10 flex-shrink-0 border-b border-[#27272A]/50 bg-[#0B0F19]/40 flex items-center justify-between px-3 relative z-10 cursor-grab active:cursor-grabbing hover:bg-[#0B0F19]/60 transition-colors"
               onPointerDown={(e) => controls.start(e)}
            >
               <div className="flex items-center gap-2">
                   <span className={`w-2 h-2 rounded-full transition-colors ${isActive ? 'bg-[#FF5722] shadow-[0_0_6px_rgba(255,87,34,0.6)]' : 'bg-[#27272A]'}`} />
                   <span className="text-xs font-mono text-[#A1A1AA] select-none tracking-wide">{win.title}</span>
               </div>
               <div className="flex items-center gap-1">
                   <button onClick={() => toggleMinimize(win.id)} className="p-1 hover:bg-[#27272A]/80 rounded text-[#A1A1AA] hover:text-[#ECECEF] transition-colors cursor-pointer">
                       <Minus size={12} />
                   </button>
                   <button onClick={() => closeWindow(win.id)} className="p-1 hover:bg-red-500/20 rounded text-[#A1A1AA] hover:text-red-400 transition-colors cursor-pointer lg:mr-0 mr-2">
                       <X size={12} />
                   </button>
               </div>
            </div>

            {/* Application Content */}
            <div className="flex-1 relative z-10 overflow-hidden">
               {renderApp()}
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
