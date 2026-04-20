import React, { useState, useCallback, useEffect, useRef, useMemo } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { useDesktopStore, AppType } from '@/store/useDesktopStore'
import {
  Search, Network, MessageSquareText, Upload, Settings, Coffee,
  ArrowRight, Command, Zap, Keyboard
} from 'lucide-react'

// ═══════════════════════════════════════════════════════════════
// COMMAND PALETTE — The Hacker's Entrance
// CMD+K launcher with fuzzy search → openWindow integration.
// ═══════════════════════════════════════════════════════════════

interface LauncherItem {
  id: string
  label: string
  keywords: string[]       // fuzzy-match targets
  section: 'Apps' | 'Widgets' | 'System'
  icon: React.ReactNode
  shortcut?: string
  appType: AppType
  windowTitle: string
  defaultProps?: { size?: { width: number; height: number } }
}

const LAUNCHER_ITEMS: LauncherItem[] = [
  {
    id: 'knowledge',
    label: 'Knowledge Map',
    keywords: ['knowledge', 'map', 'graph', 'nodes', 'network', 'visualize'],
    section: 'Apps',
    icon: <Network size={16} />,
    shortcut: '⌘1',
    appType: 'knowledge',
    windowTitle: 'Knowledge Map',
  },
  {
    id: 'aura',
    label: 'AURA Chat',
    keywords: ['aura', 'chat', 'ai', 'assistant', 'intelligence', 'ask'],
    section: 'Apps',
    icon: <MessageSquareText size={16} />,
    shortcut: '⌘2',
    appType: 'aura',
    windowTitle: 'AURA Intelligence',
  },
  {
    id: 'ingestion',
    label: 'Upload / Ingest',
    keywords: ['upload', 'ingest', 'file', 'document', 'import', 'data'],
    section: 'Apps',
    icon: <Upload size={16} />,
    shortcut: '⌘3',
    appType: 'ingestion',
    windowTitle: 'Data Ingestion',
  },
  {
    id: 'settings',
    label: 'Settings',
    keywords: ['settings', 'config', 'preferences', 'system', 'options'],
    section: 'System',
    icon: <Settings size={16} />,
    appType: 'settings',
    windowTitle: 'System Settings',
  },
  {
    id: 'caffeine',
    label: 'Caffeine Tracker',
    keywords: ['caffeine', 'coffee', 'timer', 'focus', 'session', 'grind', 'survival'],
    section: 'Widgets',
    icon: <Coffee size={16} />,
    appType: 'caffeine',
    windowTitle: 'Caffeine Tracker',
    defaultProps: { size: { width: 320, height: 480 } },
  },
]

// Simple fuzzy match: check if all query chars exist in order within the target
function fuzzyMatch(query: string, target: string): { match: boolean; score: number } {
  const q = query.toLowerCase()
  const t = target.toLowerCase()

  // Exact substring match gets highest score
  if (t.includes(q)) return { match: true, score: 100 + (q.length / t.length) * 50 }

  // Fuzzy: all query chars in order
  let qi = 0
  let score = 0
  let lastIndex = -1
  for (let ti = 0; ti < t.length && qi < q.length; ti++) {
    if (t[ti] === q[qi]) {
      score += 10
      // Bonus for consecutive chars
      if (ti === lastIndex + 1) score += 5
      // Bonus for word-start match
      if (ti === 0 || t[ti - 1] === ' ') score += 8
      lastIndex = ti
      qi++
    }
  }

  return { match: qi === q.length, score }
}

function searchItems(query: string): LauncherItem[] {
  if (!query.trim()) return LAUNCHER_ITEMS

  const scored = LAUNCHER_ITEMS.map(item => {
    // Check label + all keywords
    const allTargets = [item.label, ...item.keywords]
    let bestScore = 0
    let matched = false

    for (const target of allTargets) {
      const result = fuzzyMatch(query, target)
      if (result.match && result.score > bestScore) {
        bestScore = result.score
        matched = true
      }
    }

    return { item, score: bestScore, matched }
  })
    .filter(r => r.matched)
    .sort((a, b) => b.score - a.score)

  return scored.map(r => r.item)
}

interface CommandPaletteProps {
  isOpen: boolean
  onClose: () => void
  onNavigate?: (tab: string) => void  // legacy compat, unused
}

export default function CommandPalette({ isOpen, onClose }: CommandPaletteProps) {
  const [query, setQuery] = useState('')
  const [selectedIndex, setSelectedIndex] = useState(0)
  const inputRef = useRef<HTMLInputElement>(null)
  const listRef = useRef<HTMLDivElement>(null)
  const { openWindow } = useDesktopStore()

  const filteredItems = useMemo(() => searchItems(query), [query])

  // Group by section
  const sections = useMemo(() => {
    const groups: Record<string, LauncherItem[]> = {}
    for (const item of filteredItems) {
      if (!groups[item.section]) groups[item.section] = []
      groups[item.section].push(item)
    }
    return groups
  }, [filteredItems])

  // Execute a launcher item
  const executeItem = useCallback((item: LauncherItem) => {
    openWindow(item.id, item.windowTitle, item.appType, item.defaultProps)
    onClose()
  }, [openWindow, onClose])

  // Reset on query change
  useEffect(() => { setSelectedIndex(0) }, [query])

  // Focus input on open
  useEffect(() => {
    if (isOpen) {
      setQuery('')
      setSelectedIndex(0)
      setTimeout(() => inputRef.current?.focus(), 50)
    }
  }, [isOpen])

  // Scroll selected item into view
  useEffect(() => {
    if (!listRef.current) return
    const selected = listRef.current.querySelector('[data-selected="true"]')
    selected?.scrollIntoView({ block: 'nearest' })
  }, [selectedIndex])

  // Keyboard navigation
  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault()
        setSelectedIndex(prev => (prev + 1) % filteredItems.length)
        break
      case 'ArrowUp':
        e.preventDefault()
        setSelectedIndex(prev => (prev - 1 + filteredItems.length) % filteredItems.length)
        break
      case 'Enter':
        e.preventDefault()
        if (filteredItems[selectedIndex]) {
          executeItem(filteredItems[selectedIndex])
        }
        break
      case 'Escape':
        e.preventDefault()
        onClose()
        break
    }
  }, [filteredItems, selectedIndex, onClose, executeItem])

  // Global ⌘K toggle (close half)
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        if (isOpen) onClose()
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [isOpen, onClose])

  if (!isOpen) return null

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Void Overlay */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.12 }}
            className="fixed inset-0 bg-[#09090B]/70 backdrop-blur-sm z-[9999]"
            onClick={onClose}
          />

          {/* Smudged Glass Palette */}
          <motion.div
            initial={{ opacity: 0, scale: 0.92, y: -20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.92, y: -20 }}
            transition={{ duration: 0.18, ease: [0.23, 1, 0.32, 1] }}
            className="fixed top-[18%] left-1/2 -translate-x-1/2 w-full max-w-[540px] z-[10000]"
          >
            <div className="mx-4 rounded-2xl border border-[#27272A]/60 shadow-[0_24px_80px_rgba(0,0,0,0.8),0_0_1px_rgba(255,87,34,0.15)] overflow-hidden relative">

              {/* Smudged glass background */}
              <div className="absolute inset-0 bg-[#1A1B22]/90 backdrop-blur-2xl" />

              {/* Noise texture */}
              <div className="absolute inset-0 opacity-[0.12] pointer-events-none bg-[url('data:image/svg+xml,%3Csvg viewBox=%220 0 200 200%22 xmlns=%22http://www.w3.org/2000/svg%22%3E%3Cfilter id=%22noise%22%3E%3CfeTurbulence type=%22fractalNoise%22 baseFrequency=%220.85%22 numOctaves=%223%22 stitchTiles=%22stitch%22/%3E%3C/filter%3E%3Crect width=%22100%25%22 height=%22100%25%22 filter=%22url(%23noise)%22/%3E%3C/svg%3E')]" />

              {/* Top accent line */}
              <div className="absolute top-0 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-[#FF5722]/40 to-transparent z-20" />

              {/* Search Input */}
              <div className="relative z-10 flex items-center gap-3 px-5 py-4 border-b border-[#27272A]/40">
                <Search size={16} className="text-[#52525B] shrink-0" />
                <input
                  ref={inputRef}
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Launch an app..."
                  className="flex-1 bg-transparent text-sm text-[#ECECEF] placeholder:text-[#52525B] outline-none font-mono tracking-wide"
                  autoComplete="off"
                  spellCheck={false}
                />
                <kbd className="hidden sm:inline-flex items-center gap-0.5 px-2 py-1 text-[9px] font-mono font-medium text-[#52525B] bg-[#0B0F19]/60 border border-[#27272A]/50 rounded-md">
                  ESC
                </kbd>
              </div>

              {/* Results */}
              <div ref={listRef} className="relative z-10 max-h-[320px] overflow-y-auto py-2">
                {filteredItems.length === 0 ? (
                  <div className="px-5 py-10 text-center">
                    <Zap size={20} className="mx-auto text-[#3F3F46] mb-2" />
                    <p className="text-xs text-[#52525B] font-mono">
                      No matching apps found
                    </p>
                  </div>
                ) : (
                  Object.entries(sections).map(([section, sectionItems]) => (
                    <div key={section}>
                      <div className="px-5 py-1.5 text-[9px] font-bold text-[#3F3F46] uppercase tracking-[0.25em] font-mono">
                        {section}
                      </div>
                      {sectionItems.map((item) => {
                        const globalIdx = filteredItems.findIndex(fi => fi.id === item.id)
                        const isSelected = globalIdx === selectedIndex
                        return (
                          <button
                            key={item.id}
                            data-selected={isSelected}
                            onClick={() => executeItem(item)}
                            onMouseEnter={() => setSelectedIndex(globalIdx)}
                            className={`w-full flex items-center gap-3 px-5 py-2.5 text-sm transition-all duration-100 cursor-pointer font-mono ${
                              isSelected
                                ? 'bg-[#FF5722]/10 text-[#ECECEF]'
                                : 'text-[#A1A1AA] hover:bg-[#27272A]/30'
                            }`}
                          >
                            <span className={`shrink-0 transition-colors ${
                              isSelected ? 'text-[#FF5722]' : 'text-[#52525B]'
                            }`}>
                              {item.icon}
                            </span>
                            <span className="flex-1 text-left font-medium text-[13px] tracking-wide">
                              {item.label}
                            </span>
                            {item.shortcut && (
                              <kbd className="text-[9px] font-mono text-[#3F3F46] bg-[#0B0F19]/60 border border-[#27272A]/40 px-1.5 py-0.5 rounded">
                                {item.shortcut}
                              </kbd>
                            )}
                            {isSelected && (
                              <motion.div
                                initial={{ x: -4, opacity: 0 }}
                                animate={{ x: 0, opacity: 1 }}
                                transition={{ duration: 0.1 }}
                              >
                                <ArrowRight size={13} className="text-[#FF5722] shrink-0" />
                              </motion.div>
                            )}
                          </button>
                        )
                      })}
                    </div>
                  ))
                )}
              </div>

              {/* Footer */}
              <div className="relative z-10 flex items-center justify-between px-5 py-2.5 border-t border-[#27272A]/40 text-[9px] text-[#3F3F46] font-mono">
                <span className="flex items-center gap-2.5">
                  <span className="flex items-center gap-1">
                    <kbd className="px-1 py-0.5 bg-[#0B0F19]/60 border border-[#27272A]/40 rounded font-mono">↑</kbd>
                    <kbd className="px-1 py-0.5 bg-[#0B0F19]/60 border border-[#27272A]/40 rounded font-mono">↓</kbd>
                  </span>
                  <span className="tracking-wider">NAVIGATE</span>
                </span>
                <span className="flex items-center gap-2.5">
                  <kbd className="px-1 py-0.5 bg-[#0B0F19]/60 border border-[#27272A]/40 rounded font-mono">↵</kbd>
                  <span className="tracking-wider">LAUNCH</span>
                </span>
                <span className="flex items-center gap-1.5">
                  <Command size={10} />
                  <Keyboard size={10} />
                  <span className="tracking-wider">ANTI·GRAVITY OS</span>
                </span>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}
