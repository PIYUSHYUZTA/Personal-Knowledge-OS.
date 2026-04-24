import React, { useState, useEffect } from 'react'
import { useDesktopStore } from '@/store/useDesktopStore'
import { useAuth } from '@/context/AuthContext'
import { useApiToasts } from '@/hooks/useApiToasts'
import WindowManager from '@/components/desktop/WindowManager'
import CommandPalette from '@/components/ui/CommandPalette'
import { motion, AnimatePresence } from 'framer-motion'
import AuthBackground from '@/components/auth/AuthBackground'
import { useSound } from '@/hooks/useSound'

export default function Dashboard() {
  const { user } = useAuth()
  useApiToasts()
  const { playClick, playWoosh } = useSound()
  
  const { zenMode, toggleZenMode, openWindow } = useDesktopStore()
  const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useState(false)

  // Global ⌘K and ⌘F listener
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        playWoosh()
        setIsCommandPaletteOpen(prev => !prev)
      }
      
      if ((e.metaKey || e.ctrlKey) && e.key === 'f') {
        e.preventDefault()
        toggleZenMode()
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [toggleZenMode])

  return (
    <div className="bg-transparent text-on-surface min-h-screen overflow-hidden flex font-inter relative selection:bg-primary/20 selection:text-primary">
      {/* Deep Space Background Effect */}
      <AuthBackground />

      {/* Zen Mode Dimmer */}
      <AnimatePresence>
        {zenMode && (
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 bg-black/60 backdrop-blur-[2px] pointer-events-none z-[40]" 
          />
        )}
      </AnimatePresence>

      {/* Navigation Drawer */}
      <nav className="fixed left-0 top-0 h-full w-[64px] border-r border-white/20 bg-white/10 backdrop-blur-xl shadow-[0_8px_32px_rgba(0,0,0,0.3)] flex flex-col items-center py-8 gap-6 z-50">
        <div className="text-transparent mb-8">
          <span className="material-symbols-outlined text-[32px] text-primary">hub</span>
        </div>
        
        <button 
          onClick={() => { playClick() }} // Home action
          className="flex flex-col items-center justify-center w-10 h-10 rounded-lg bg-primary/20 text-primary shadow-[0_0_15px_rgba(124,77,255,0.5)] transition-all duration-300 scale-95 active:opacity-80 group"
        >
          <span className="material-symbols-outlined text-[24px]" style={{ fontVariationSettings: "'FILL' 1" }}>home</span>
        </button>

        <button 
          onClick={() => { playClick(); openWindow('search', 'Omni Search', 'search'); }}
          className="flex flex-col items-center justify-center w-10 h-10 rounded-lg text-white/50 hover:text-white/80 hover:bg-white/5 hover:scale-105 transition-all duration-300 scale-95 active:opacity-80 group"
        >
          <span className="material-symbols-outlined text-[24px]">search</span>
        </button>

        <button 
          onClick={() => { playClick(); openWindow('knowledge', 'Knowledge Map', 'knowledge'); }}
          className="flex flex-col items-center justify-center w-10 h-10 rounded-lg text-white/50 hover:text-white/80 hover:bg-white/5 hover:scale-105 transition-all duration-300 scale-95 active:opacity-80 group"
        >
          <span className="material-symbols-outlined text-[24px]">schema</span>
        </button>

        <button 
          onClick={() => { playClick(); openWindow('digest', 'Weekly Digest', 'digest'); }}
          className="flex flex-col items-center justify-center w-10 h-10 rounded-lg text-white/50 hover:text-white/80 hover:bg-white/5 hover:scale-105 transition-all duration-300 scale-95 active:opacity-80 group"
        >
          <span className="material-symbols-outlined text-[24px]">auto_stories</span>
        </button>

        <button 
          onClick={() => { playClick(); openWindow('ingestion', 'Data Ingestion', 'ingestion'); }}
          className="flex flex-col items-center justify-center w-10 h-10 rounded-lg text-white/50 hover:text-white/80 hover:bg-white/5 hover:scale-105 transition-all duration-300 scale-95 active:opacity-80 group mt-auto"
        >
          <span className="material-symbols-outlined text-[24px]">upload</span>
        </button>

      </nav>

      {/* Main Content Canvas */}
      <main className="ml-[64px] flex-1 flex flex-col relative z-10 p-6 md:p-8 lg:p-10 h-screen overflow-hidden">
        
        {/* Top Bar: Search */}
        <header className="w-full flex justify-center mb-8 relative z-20">
          <div className="relative w-full max-w-2xl">
            <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
              <span className="material-symbols-outlined text-on-surface-variant">search</span>
            </div>
            <input 
              className="w-full dashboard-v2-glass rounded-full py-4 pl-12 pr-4 text-lg text-on-surface placeholder-on-surface-variant/50 focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all duration-300 glow-active bg-white/5 border-white/20" 
              placeholder="Query your knowledge base..." 
              type="text"
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                   openWindow('search', 'Omni Search', 'search');
                }
              }}
            />
          </div>
        </header>

        {/* Centerpiece: Knowledge Graph Visualization */}
        <section className="flex-1 relative flex items-center justify-center my-8 border border-white/5 rounded-xl bg-gradient-to-b from-transparent to-surface-container-lowest/50 overflow-hidden">
          
          {/* Simulated Graph Nodes */}
          <div className="absolute w-[600px] h-[600px] flex items-center justify-center opacity-80">
            {/* Center Node */}
            <div className="absolute w-24 h-24 rounded-full bg-primary/20 border border-primary/50 flex items-center justify-center node-glow z-20">
              <span className="material-symbols-outlined text-[48px] text-primary">psychology</span>
            </div>
            
            {/* Orbiting Nodes */}
            <div className="absolute w-full h-full border border-white/5 rounded-full animate-[spin_60s_linear_infinite]">
              <div className="absolute top-[10%] left-[20%] w-12 h-12 rounded-full bg-secondary/20 border border-secondary/50 flex items-center justify-center node-glow">
                <span className="material-symbols-outlined text-[24px] text-secondary">data_object</span>
              </div>
              <div className="absolute bottom-[20%] right-[10%] w-16 h-16 rounded-full bg-tertiary/20 border border-tertiary/50 flex items-center justify-center node-glow">
                <span className="material-symbols-outlined text-[32px] text-tertiary">description</span>
              </div>
              <div className="absolute top-[40%] right-[5%] w-10 h-10 rounded-full bg-primary-container/30 border border-primary-container/60 flex items-center justify-center node-glow">
                <span className="material-symbols-outlined text-[20px] text-primary-container">link</span>
              </div>
            </div>

            {/* Connecting Lines */}
            <svg className="absolute inset-0 w-full h-full z-10 pointer-events-none" viewBox="0 0 600 600">
              <path d="M300,300 L180,120" fill="none" stroke="rgba(205, 189, 255, 0.3)" strokeDasharray="4 4" strokeWidth="2"></path>
              <path d="M300,300 L480,420" fill="none" stroke="rgba(205, 189, 255, 0.3)" strokeDasharray="4 4" strokeWidth="2"></path>
              <path d="M300,300 L540,240" fill="none" stroke="rgba(205, 189, 255, 0.3)" strokeDasharray="4 4" strokeWidth="2"></path>
            </svg>
          </div>

          <div className="absolute bottom-6 right-6 flex gap-2">
            <span className="px-3 py-1 rounded-full dashboard-v2-glass text-xs font-bold text-secondary uppercase tracking-wider">System Online</span>
            <span className="px-3 py-1 rounded-full dashboard-v2-glass text-xs font-bold text-on-surface-variant uppercase tracking-wider">Nodes Active</span>
          </div>
        </section>

        {/* Bottom Stats Panel */}
        <footer className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-auto relative z-20">
          {/* Stat Card 1 */}
          <div className="dashboard-v2-glass rounded-xl p-6 flex flex-col justify-between hover:bg-white/10 transition-colors duration-300">
            <div className="flex items-center justify-between mb-2">
              <h3 className="font-space-grotesk text-lg text-on-surface-variant">Documents Indexed</h3>
              <span className="material-symbols-outlined text-primary/70">inventory_2</span>
            </div>
            <div className="flex items-baseline gap-2">
              <span className="font-space-grotesk text-4xl font-bold text-primary">12,408</span>
              <span className="text-sm text-secondary">+24 this week</span>
            </div>
          </div>

          {/* Stat Card 2 */}
          <div className="dashboard-v2-glass rounded-xl p-6 flex flex-col justify-between hover:bg-white/10 transition-colors duration-300">
            <div className="flex items-center justify-between mb-2">
              <h3 className="font-space-grotesk text-lg text-on-surface-variant">Topics Connected</h3>
              <span className="material-symbols-outlined text-secondary/70">share</span>
            </div>
            <div className="flex items-baseline gap-2">
              <span className="font-space-grotesk text-4xl font-bold text-secondary">843</span>
              <span className="text-sm text-primary">Strong network</span>
            </div>
          </div>

          {/* Stat Card 3 */}
          <div className="dashboard-v2-glass rounded-xl p-6 flex flex-col justify-between hover:bg-white/10 transition-colors duration-300">
            <div className="flex items-center justify-between mb-2">
              <h3 className="font-space-grotesk text-lg text-on-surface-variant">Last Search</h3>
              <span className="material-symbols-outlined text-tertiary/70">history</span>
            </div>
            <div className="flex flex-col">
              <span className="font-space-grotesk text-xl text-on-surface truncate">"Quantum computing implications"</span>
              <span className="text-sm text-on-surface-variant mt-1">2 hours ago</span>
            </div>
          </div>
        </footer>
      </main>

      {/* Global Window Layer */}
      <div className="fixed inset-0 pointer-events-none z-[45]">
        <WindowManager />
      </div>

      {/* Command Palette */}
      <CommandPalette
        isOpen={isCommandPaletteOpen}
        onClose={() => setIsCommandPaletteOpen(false)}
      />
    </div>
  )
}
