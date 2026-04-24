import React, { useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useDesktopStore, AppWindow } from '@/store/useDesktopStore'
import { X } from 'lucide-react'
// App Components
import KnowledgeVisualizer from '@/components/knowledge/KnowledgeVisualizer'
import AuraChat from '@/components/aura/AuraChat'
import FileUploader from '@/components/ingestion/FileUploader'
import CaffeineWidget from '@/components/desktop/CaffeineWidget'
import WeeklyDigest from '@/components/digest/WeeklyDigest'
import SearchView from '@/components/knowledge/SearchView'

export default function Window({ window: win }: { window: AppWindow }) {
  const { closeWindow, focusWindow, activeWindowId } = useDesktopStore()
  
  const isActive = activeWindowId === win.id

  const renderApp = () => {
      switch(win.appType) {
          case 'knowledge': return <KnowledgeVisualizer />
          case 'aura': return <AuraChat />
          case 'ingestion': return <div className="p-8 h-full overflow-auto"><FileUploader /></div>
          case 'settings': return <div className="p-8 text-[#A1A1AA] font-mono text-sm leading-relaxed"><p className="text-[#FF5722] mb-4 text-lg font-bold">⚙ SYSTEM SETTINGS</p><p className="text-[#52525B]">Configuration module pending deployment.</p></div>
          case 'caffeine': return <CaffeineWidget />
          case 'digest': return <WeeklyDigest />
          case 'search': return <SearchView />
          default: return <div className="p-4">Unknown App</div>
      }
  }

  return (
    <motion.div
      initial={{ scale: 0.9, opacity: 0, y: 20 }}
      animate={{ scale: 1, opacity: 1, y: 0 }}
      exit={{ scale: 0.9, opacity: 0, y: 20 }}
      transition={{ type: 'spring', damping: 25, stiffness: 300 }}
      onPointerDown={() => focusWindow(win.id)}
      className={`absolute inset-0 flex items-center justify-center pointer-events-none z-[110] ${isActive ? '' : 'hidden'}`}
    >
      <div className="w-[95vw] h-[92vh] max-w-7xl bg-surface/40 backdrop-blur-[32px] rounded-3xl border border-white/10 shadow-[0_32px_64px_rgba(0,0,0,0.5)] overflow-hidden pointer-events-auto relative flex flex-col">
        
        {/* Immersive Header / Close Trigger */}
        <div className="absolute top-6 right-6 z-[120]">
          <button 
            onClick={(e) => {
              e.stopPropagation()
              closeWindow(win.id)
            }} 
            className="w-10 h-10 rounded-full bg-white/5 hover:bg-white/10 border border-white/10 flex items-center justify-center text-white/50 hover:text-white transition-all duration-300 hover:rotate-90"
          >
            <X size={20} />
          </button>
        </div>

        {/* Title Badge (Subtle) */}
        <div className="absolute top-8 left-8 pointer-events-none opacity-40">
          <div className="flex items-center gap-3">
            <div className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse" />
            <span className="font-space-grotesk text-[10px] uppercase tracking-[0.2em] font-bold text-on-surface">
              {win.title}
            </span>
          </div>
        </div>

        {/* Content Area */}
        <div className="flex-1 w-full h-full mt-12 overflow-hidden">
          {renderApp()}
        </div>
      </div>
    </motion.div>
  )
}
