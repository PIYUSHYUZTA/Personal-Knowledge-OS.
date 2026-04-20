import React, { useState, useEffect } from 'react'
import { useDesktopStore } from '@/store/useDesktopStore'
import { useAuth } from '@/context/AuthContext'
import { useApiToasts } from '@/hooks/useApiToasts'
import AuthBackground from '@/components/auth/AuthBackground'
import WindowManager from '@/components/desktop/WindowManager'
import CommandPalette from '@/components/ui/CommandPalette'
import { motion, AnimatePresence } from 'framer-motion'
import { Settings, Coffee, Network, MessageSquare, Plus } from 'lucide-react'

// Ghost Dock Component
function GhostDock() {
  const { openWindow } = useDesktopStore()
  return (
    <div className="fixed bottom-4 left-1/2 -translate-x-1/2 z-50 group px-10 pb-4">
      {/* Invisible hover area to trigger group hover */}
      <div className="absolute inset-0 top-[-40px]" />
      
      <div className="flex items-center gap-3 bg-[#1A1B22]/40 backdrop-blur-md border border-[#27272A]/50 rounded-2xl p-2 opacity-20 group-hover:opacity-100 transition-opacity duration-300 shadow-[0_8px_32px_rgba(0,0,0,0.8)]">
        
        <button 
          onClick={() => openWindow('knowledge', 'Knowledge Map', 'knowledge')}
          className="w-12 h-12 flex items-center justify-center rounded-xl hover:bg-[#27272A] text-[#A1A1AA] hover:text-[#FF5722] transition-colors group/btn relative cursor-pointer"
        >
          <Network size={20} />
          <span className="absolute -top-8 bg-[#0B0F19] text-[10px] px-2 py-1 rounded border border-[#27272A] opacity-0 group-hover/btn:opacity-100 font-mono text-[#ECECEF]">MAP</span>
        </button>

        <button 
          onClick={() => openWindow('aura', 'AURA Intelligence', 'aura')}
          className="w-12 h-12 flex items-center justify-center rounded-xl hover:bg-[#27272A] text-[#A1A1AA] hover:text-[#FF5722] transition-colors group/btn relative cursor-pointer"
        >
          <MessageSquare size={20} />
          <span className="absolute -top-8 bg-[#0B0F19] text-[10px] px-2 py-1 rounded border border-[#27272A] opacity-0 group-hover/btn:opacity-100 font-mono text-[#ECECEF]">AURA</span>
        </button>

        <button 
          onClick={() => openWindow('ingestion', 'Data Ingestion', 'ingestion')}
          className="w-12 h-12 flex items-center justify-center rounded-xl hover:bg-[#27272A] text-[#A1A1AA] hover:text-[#FF5722] transition-colors group/btn relative cursor-pointer"
        >
          <Plus size={20} />
          <span className="absolute -top-8 bg-[#0B0F19] text-[10px] px-2 py-1 rounded border border-[#27272A] opacity-0 group-hover/btn:opacity-100 font-mono text-[#ECECEF]">UPLOAD</span>
        </button>

        <div className="w-[1px] h-8 bg-[#27272A] mx-1" />

        <button 
          onClick={() => openWindow('caffeine', 'Caffeine Tracker', 'caffeine')}
          className="w-12 h-12 flex items-center justify-center rounded-xl hover:bg-[#27272A] text-[#A1A1AA] hover:text-[#FF5722] transition-colors group/btn relative cursor-pointer"
        >
          <Coffee size={20} />
          <span className="absolute -top-8 bg-[#0B0F19] text-[10px] px-2 py-1 rounded border border-[#27272A] opacity-0 group-hover/btn:opacity-100 font-mono text-[#ECECEF]">CAFFEINE</span>
        </button>

      </div>
    </div>
  )
}

export default function Dashboard() {
  const { user } = useAuth()
  useApiToasts() // Wire API toasts
  
  const { zenMode, toggleZenMode } = useDesktopStore()
  const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useState(false)

  // Global ⌘K and ⌘F listener
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      // CMD+K
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        setIsCommandPaletteOpen(prev => !prev)
      }
      
      // CMD+F (Zen Focus Mode)
      if ((e.metaKey || e.ctrlKey) && e.key === 'f') {
        e.preventDefault()
        toggleZenMode()
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [toggleZenMode])

  return (
    <div className="flex bg-[#09090B] min-h-screen text-[#A1A1AA] font-mono selection:bg-[#FF5722]/20 selection:text-[#FF5722] overflow-hidden relative">
      
      {/* Base Desktop Wallpaper (Digital Void) */}
      <AuthBackground />
      
      {/* Zen Mode Dimmer */}
      <AnimatePresence>
          {zenMode && (
              <motion.div 
                 initial={{ opacity: 0 }}
                 animate={{ opacity: 1 }}
                 exit={{ opacity: 0 }}
                 className="absolute inset-0 bg-[#0B0F19]/80 backdrop-blur-[2px] pointer-events-none z-[1]" 
              />
          )}
      </AnimatePresence>
      
      {/* Noise Texture over desktop */}
      <div className="absolute inset-0 bg-[url('data:image/svg+xml,%3Csvg viewBox=%220 0 200 200%22 xmlns=%22http://www.w3.org/2000/svg%22%3E%3Cfilter id=%22noise%22%3E%3CfeTurbulence type=%22fractalNoise%22 baseFrequency=%220.8%22 numOctaves=%224%22 stitchTiles=%22stitch%22/%3E%3C/filter%3E%3Crect width=%22100%25%22 height=%22100%25%22 filter=%22url(%23noise)%22/%3E%3C/svg%3E')] opacity-5 pointer-events-none mix-blend-overlay z-[2]" />

      {/* Primary OS Container */}
      <main className="flex-1 w-full h-full p-4 relative z-10 pointer-events-none">
         {/* Allow pointer events only on the windows themselves */}
         <div className="absolute inset-0 pointer-events-none">
            <WindowManager />
         </div>
      </main>

      {/* The Ghost Dock Backup */}
      <GhostDock />

      {/* Command Palette — CMD+K Hacker Launcher */}
      <CommandPalette
        isOpen={isCommandPaletteOpen}
        onClose={() => setIsCommandPaletteOpen(false)}
      />
    </div>
  )
}
