import React from 'react'
import { useKnowledge } from '@/context/KnowledgeContext'
import Skeleton from '@/components/ui/Skeleton'
import { motion } from 'framer-motion'

export default function KnowledgeVisualizer() {
  const { isLoading } = useKnowledge()

  if (isLoading) {
    return (
      <div className="h-full flex flex-col items-center justify-center p-8 gap-4">
        <div className="w-full max-w-md space-y-4">
          <Skeleton variant="text" lines={1} width="60%" height="20px" />
          <Skeleton variant="text" lines={2} />
          <div className="grid grid-cols-3 gap-3 mt-6">
            <Skeleton variant="stat-card" className="h-24" />
            <Skeleton variant="stat-card" className="h-24" />
            <Skeleton variant="stat-card" className="h-24" />
          </div>
        </div>
        <p className="text-xs font-medium text-text-muted mt-4 uppercase tracking-wider">
          Loading knowledge graph...
        </p>
      </div>
    )
  }

  return (
    <div className="w-full h-full bg-transparent text-on-background font-inter overflow-hidden relative flex rounded-xl">
      {/* Graph Container (Simulated 3D Space) */}
      <div className="absolute inset-0 z-0">
        {/* Simulated Edges */}
        <div className="absolute top-1/2 left-1/3 w-64 h-[1px] edge-primary transform -rotate-12 origin-left opacity-60"></div>
        <div className="absolute top-1/2 left-1/3 w-48 h-[1px] edge-secondary transform rotate-45 origin-left opacity-40"></div>
        <div className="absolute top-1/3 left-2/3 w-56 h-[1px] edge-primary transform rotate-12 origin-left opacity-50"></div>
        <div className="absolute bottom-1/3 left-1/2 w-40 h-[1px] edge-secondary transform -rotate-30 origin-left opacity-40"></div>

        {/* Simulated Nodes */}
        {/* Central Hub Node */}
        <motion.div 
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ duration: 0.8, ease: "easeOut" }}
          className="absolute top-1/2 left-1/3 transform -translate-x-1/2 -translate-y-1/2 group cursor-pointer z-20"
        >
          <div className="w-16 h-16 rounded-full bg-primary/20 node-glow-primary transition-transform duration-300 group-hover:scale-125 relative flex items-center justify-center border border-primary/50">
            <span className="material-symbols-outlined text-primary text-[32px]">hub</span>
          </div>
          {/* Tooltip */}
          <div className="absolute top-full mt-4 left-1/2 -translate-x-1/2 opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none dashboard-v2-glass rounded-lg p-4 w-64 z-50 shadow-2xl">
            <h3 className="text-lg font-bold text-on-surface mb-1">Quantum Computing</h3>
            <p className="text-xs text-on-surface-variant">Central nexus for all research notes regarding quantum state manipulation.</p>
            <div className="mt-2 flex gap-2">
              <span className="px-2 py-1 rounded-full bg-white/5 text-on-surface text-[10px] font-bold border border-white/10 uppercase tracking-wider">Physics</span>
              <span className="px-2 py-1 rounded-full bg-white/5 text-on-surface text-[10px] font-bold border border-white/10 uppercase tracking-wider">Active</span>
            </div>
          </div>
        </motion.div>

        {/* Secondary Node 1 */}
        <motion.div 
          initial={{ scale: 0, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ delay: 0.3, duration: 0.6 }}
          className="absolute top-[30%] left-[50%] transform -translate-x-1/2 -translate-y-1/2 group cursor-pointer z-10"
        >
          <div className="w-12 h-12 rounded-full bg-secondary/20 node-glow-secondary transition-transform duration-300 group-hover:scale-125 relative flex items-center justify-center border border-secondary/50">
            <span className="material-symbols-outlined text-secondary text-[24px]">memory</span>
          </div>
        </motion.div>

        {/* Secondary Node 2 */}
        <motion.div 
          initial={{ scale: 0, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ delay: 0.4, duration: 0.6 }}
          className="absolute top-[65%] left-[45%] transform -translate-x-1/2 -translate-y-1/2 group cursor-pointer z-10"
        >
          <div className="w-10 h-10 rounded-full bg-secondary/20 node-glow-secondary transition-transform duration-300 group-hover:scale-125 relative flex items-center justify-center border border-secondary/50">
            <span className="material-symbols-outlined text-secondary text-[20px]">science</span>
          </div>
        </motion.div>

        {/* Tertiary Nodes (Background elements) */}
        <div className="absolute top-[40%] left-[20%] w-6 h-6 rounded-full bg-tertiary/20 node-glow-tertiary border border-tertiary/30 animate-pulse"></div>
        <div className="absolute top-[20%] left-[35%] w-8 h-8 rounded-full bg-tertiary/20 node-glow-tertiary border border-tertiary/30 animate-pulse delay-75"></div>
        <div className="absolute top-[75%] left-[25%] w-5 h-5 rounded-full bg-tertiary/20 node-glow-tertiary border border-tertiary/30 animate-pulse delay-150"></div>
      </div>

      {/* Floating Controls (Bottom Right) */}
      <div className="absolute bottom-6 right-6 flex flex-col gap-2 z-40">
        <button className="w-10 h-10 rounded-full dashboard-v2-glass flex items-center justify-center text-on-surface hover:bg-white/20 transition-colors shadow-lg">
          <span className="material-symbols-outlined text-[20px]">add</span>
        </button>
        <button className="w-10 h-10 rounded-full dashboard-v2-glass flex items-center justify-center text-on-surface hover:bg-white/20 transition-colors shadow-lg">
          <span className="material-symbols-outlined text-[20px]">remove</span>
        </button>
        <button className="w-10 h-10 rounded-full dashboard-v2-glass flex items-center justify-center text-on-surface hover:bg-white/20 transition-colors shadow-lg mt-2">
          <span className="material-symbols-outlined text-[20px]">refresh</span>
        </button>
      </div>

      {/* Status Overlay (Top Right) */}
      <div className="absolute top-6 right-6 z-40 dashboard-v2-glass rounded-full px-4 py-2 flex items-center gap-3">
        <div className="w-2 h-2 rounded-full bg-secondary animate-pulse shadow-[0_0_8px_rgba(0,227,253,0.8)]"></div>
        <span className="text-[10px] font-bold text-on-surface tracking-wider uppercase">System Synced</span>
        <span className="text-on-surface-variant/30 text-xs">|</span>
        <span className="text-[10px] font-bold text-primary tracking-wider uppercase">Deep Focus Mode</span>
      </div>
    </div>
  )
}
