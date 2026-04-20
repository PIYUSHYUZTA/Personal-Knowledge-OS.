import { useState, useEffect } from 'react'
import { LayoutDashboard, Network, MessageSquareText, X, Settings, HelpCircle, ChevronsLeft, ChevronsRight } from 'lucide-react'
import { cn } from '@/lib/utils'
import { motion, AnimatePresence } from 'framer-motion'
import Tooltip from '@/components/ui/Tooltip'

interface SidebarProps {
  activeTab: string
  setActiveTab: (tab: 'dashboard' | 'knowledge' | 'aura') => void
  isOpen?: boolean
  setIsOpen?: (open: boolean) => void
}

const SIDEBAR_COLLAPSED_KEY = 'pkos-sidebar-collapsed'

export default function Sidebar({ activeTab, setActiveTab, isOpen, setIsOpen }: SidebarProps) {
  const [isCollapsed, setIsCollapsed] = useState(() => {
    const stored = localStorage.getItem(SIDEBAR_COLLAPSED_KEY)
    return stored === 'true'
  })

  useEffect(() => {
    localStorage.setItem(SIDEBAR_COLLAPSED_KEY, String(isCollapsed))
  }, [isCollapsed])

  const mainTabs = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard, shortcut: '⌘1' },
    { id: 'knowledge', label: 'Knowledge Map', icon: Network, shortcut: '⌘2' },
    { id: 'aura', label: 'AURA Chat', icon: MessageSquareText, shortcut: '⌘3' },
  ]

  const secondaryTabs = [
    { id: 'settings', label: 'Settings', icon: Settings },
    { id: 'help', label: 'Help & Docs', icon: HelpCircle },
  ]

  // Keyboard shortcuts for tab switching
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (!(e.metaKey || e.ctrlKey)) return
      if (e.key === '1') { e.preventDefault(); setActiveTab('dashboard') }
      if (e.key === '2') { e.preventDefault(); setActiveTab('knowledge') }
      if (e.key === '3') { e.preventDefault(); setActiveTab('aura') }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [setActiveTab])

  const sidebarWidth = isCollapsed ? 'w-16' : 'w-[260px]'

  const renderNavItem = (tab: { id: string; label: string; icon: React.ComponentType<any>; shortcut?: string }, isActive: boolean, isMain: boolean) => {
    const Icon = tab.icon

    const button = (
      <button
        key={tab.id}
        onClick={() => {
          if (isMain) setActiveTab(tab.id as 'dashboard' | 'knowledge' | 'aura')
          setIsOpen?.(false)
        }}
        className={cn(
          'w-full flex items-center gap-3 rounded-lg text-sm font-medium transition-all duration-fast group relative cursor-pointer',
          isCollapsed ? 'px-0 py-2.5 justify-center' : 'px-3 py-2.5',
          isActive
            ? 'text-primary bg-secondary/10'
            : 'text-text-muted hover:text-primary hover:bg-black/5 dark:hover:bg-white/5'
        )}
        aria-label={tab.label}
      >
        <Icon
          size={18}
          strokeWidth={isActive ? 2.5 : 2}
          className={cn(
            'transition-colors duration-fast shrink-0',
            isActive ? 'text-secondary' : 'text-text-muted group-hover:text-primary'
          )}
        />
        {!isCollapsed && (
          <>
            <span className="flex-1 text-left">{tab.label}</span>
            {tab.shortcut && (
              <kbd className="text-[10px] font-mono text-text-muted/60 bg-black/5 dark:bg-white/5 px-1.5 py-0.5 rounded hidden lg:inline-block">
                {tab.shortcut}
              </kbd>
            )}
          </>
        )}
        {isActive && (
          <motion.div
            layoutId="activeTabIndicator"
            className="absolute left-0 w-[3px] h-5 bg-secondary rounded-r-full top-1/2 -translate-y-1/2"
            transition={{ type: 'spring', bounce: 0.2, duration: 0.4 }}
          />
        )}
      </button>
    )

    if (isCollapsed) {
      return (
        <Tooltip key={tab.id} content={tab.label} position="right">
          {button}
        </Tooltip>
      )
    }

    return button
  }

  return (
    <>
      {/* Mobile Overlay */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-background/80 backdrop-blur-sm z-40 md:hidden"
            onClick={() => setIsOpen?.(false)}
          />
        )}
      </AnimatePresence>

      <aside
        className={cn(
          'fixed md:relative top-0 left-0 h-full bg-surface border-r border-border flex flex-col z-50 transition-all duration-200 ease-in-out shadow-lg md:shadow-none',
          sidebarWidth,
          isOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'
        )}
      >
        {/* Logo Section */}
        <div className={cn(
          'h-14 flex items-center border-b border-border/50 shrink-0',
          isCollapsed ? 'justify-center px-2' : 'justify-between px-5'
        )}>
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-primary text-surface flex items-center justify-center font-bold text-xs shadow-sm relative overflow-hidden group shrink-0">
              <span className="relative z-10">PK</span>
              <div className="absolute inset-0 bg-secondary/80 translate-y-full group-hover:translate-y-0 transition-transform duration-200" />
            </div>
            {!isCollapsed && (
              <motion.h1
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                className="text-[17px] font-semibold tracking-tight text-primary"
              >
                PKOS
              </motion.h1>
            )}
          </div>
          <button
            className="md:hidden p-1.5 text-text-muted hover:text-primary transition-colors focus-ring rounded-md cursor-pointer"
            onClick={() => setIsOpen?.(false)}
            aria-label="Close sidebar"
          >
            <X size={18} />
          </button>
        </div>

        {/* Navigation */}
        <nav className={cn(
          'flex-1 py-5 space-y-6 overflow-y-auto',
          isCollapsed ? 'px-2' : 'px-3'
        )}>
          {/* Main Menu */}
          <div>
            {!isCollapsed && (
              <div className="px-3 mb-2 text-[10px] font-semibold text-text-muted uppercase tracking-wider">
                Overview
              </div>
            )}
            <div className="space-y-0.5">
              {mainTabs.map((tab) => renderNavItem(tab, activeTab === tab.id, true))}
            </div>
          </div>

          {/* Secondary Menu */}
          <div>
            {!isCollapsed && (
              <div className="px-3 mb-2 text-[10px] font-semibold text-text-muted uppercase tracking-wider">
                Preferences
              </div>
            )}
            <div className="space-y-0.5">
              {secondaryTabs.map((tab) => renderNavItem(tab, false, false))}
            </div>
          </div>
        </nav>

        {/* Collapse Toggle (desktop only) */}
        <div className="hidden md:flex items-center justify-center py-2 border-t border-border/50">
          <Tooltip content={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'} position="right">
            <button
              onClick={() => setIsCollapsed(!isCollapsed)}
              className="p-2 text-text-muted hover:text-primary hover:bg-black/5 dark:hover:bg-white/5 rounded-lg transition-all cursor-pointer"
              aria-label={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            >
              {isCollapsed ? <ChevronsRight size={16} /> : <ChevronsLeft size={16} />}
            </button>
          </Tooltip>
        </div>

        {/* Footer info widget */}
        {!isCollapsed && (
          <div className="p-3 border-t border-border/50">
            <div className="bg-black/5 dark:bg-white/5 rounded-lg p-3 relative overflow-hidden flex items-start gap-3">
              <div className="w-2 h-2 mt-1 rounded-full bg-success flex-shrink-0 relative">
                <div className="absolute inset-0 rounded-full bg-success animate-ping opacity-75" />
              </div>
              <div>
                <p className="text-[11px] font-semibold text-primary mb-0.5">System Online</p>
                <p className="text-[10px] text-text-muted leading-relaxed">
                  v1.0.0-alpha
                </p>
              </div>
            </div>
          </div>
        )}
      </aside>
    </>
  )
}
