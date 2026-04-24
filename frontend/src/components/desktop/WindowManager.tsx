import React, { useEffect } from 'react'
import { useDesktopStore } from '@/store/useDesktopStore'
import Window from './Window'
import { motion, AnimatePresence } from 'framer-motion'

export default function WindowManager() {
  const { windows, activeWindowId, closeWindow } = useDesktopStore()
  
  // Close active window on Escape
  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && activeWindowId) {
        closeWindow(activeWindowId)
      }
    }
    window.addEventListener('keydown', handleEsc)
    return () => window.removeEventListener('keydown', handleEsc)
  }, [activeWindowId, closeWindow])

  const openWindows = windows.filter(w => w.isOpen && !w.isMinimized)
  const hasActiveApp = openWindows.length > 0

  return (
    <AnimatePresence>
      {hasActiveApp && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center pointer-events-none">
          {/* Immersive Backdrop Overlay */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => activeWindowId && closeWindow(activeWindowId)}
            className="absolute inset-0 bg-black/70 backdrop-blur-[10px] pointer-events-auto cursor-pointer"
          />
          
          {/* App Portals */}
          <div className="relative w-full h-full flex items-center justify-center pointer-events-none">
            {openWindows.map((win) => (
              <Window key={win.id} window={win} />
            ))}
          </div>
        </div>
      )}
    </AnimatePresence>
  )
}
