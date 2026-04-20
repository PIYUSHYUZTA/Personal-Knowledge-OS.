import { useEffect, useState, useCallback } from 'react'
import { useAuth } from '@/context/AuthContext'
import { User } from '@/types'
import { LogOut, Sun, Moon, Bell, Menu, Search, Command } from 'lucide-react'
import { motion } from 'framer-motion'

interface HeaderProps {
  user: User | null
  toggleMobileMenu: () => void
  onOpenCommandPalette?: () => void
}

export default function Header({ user, toggleMobileMenu, onOpenCommandPalette }: HeaderProps) {
  const { logout } = useAuth()
  const [isDark, setIsDark] = useState(false)
  const [hasScrolled, setHasScrolled] = useState(false)

  useEffect(() => {
    setIsDark(document.documentElement.classList.contains('dark'))
  }, [])

  // Scroll-aware header shadow
  useEffect(() => {
    const main = document.querySelector('main')
    if (!main) return
    const handler = () => setHasScrolled(main.scrollTop > 8)
    main.addEventListener('scroll', handler, { passive: true })
    return () => main.removeEventListener('scroll', handler)
  }, [])

  const toggleDarkMode = useCallback(() => {
    const root = document.documentElement
    if (root.classList.contains('dark')) {
      root.classList.remove('dark')
      setIsDark(false)
      localStorage.setItem('pkos-theme', 'light')
    } else {
      root.classList.add('dark')
      setIsDark(true)
      localStorage.setItem('pkos-theme', 'dark')
    }
  }, [])

  return (
    <header
      className={`h-14 glass-header px-4 md:px-6 flex justify-between items-center sticky top-0 z-30 transition-all duration-200 ${
        hasScrolled ? 'shadow-md border-border' : 'border-transparent'
      }`}
    >
      <div className="flex items-center gap-3 flex-1">
        <button
          onClick={toggleMobileMenu}
          className="md:hidden p-2 -ml-2 text-text-muted hover:text-primary transition-colors focus-ring rounded-lg cursor-pointer"
          aria-label="Toggle menu"
        >
          <Menu size={20} />
        </button>

        {/* ⌘K Search Trigger */}
        <button
          onClick={onOpenCommandPalette}
          className="hidden md:flex items-center gap-2 max-w-xs w-full h-9 bg-black/5 dark:bg-white/5 border border-transparent hover:border-border rounded-lg px-3 text-sm text-text-muted transition-all duration-fast cursor-pointer"
        >
          <Search size={15} className="shrink-0" />
          <span className="flex-1 text-left text-[13px]">Search knowledge...</span>
          <div className="flex items-center gap-1 opacity-60 shrink-0">
            <kbd className="text-[10px] font-mono bg-background border border-border px-1 py-0.5 rounded leading-none">
              <Command size={10} className="inline-block" />
            </kbd>
            <kbd className="text-[10px] font-mono bg-background border border-border px-1.5 py-0.5 rounded leading-none">
              K
            </kbd>
          </div>
        </button>
      </div>

      <div className="flex items-center gap-2 md:gap-3">
        {/* User Greeting */}
        <div className="hidden md:block text-right mr-1">
          <p className="text-xs font-medium text-text-muted">{user?.email?.split('@')[0] || 'User'}</p>
        </div>

        {/* Actions Group */}
        <div className="flex items-center gap-0.5">
          <button
            onClick={toggleDarkMode}
            className="p-2 text-text-muted hover:text-primary hover:bg-black/5 dark:hover:bg-white/5 rounded-lg transition-all focus-ring cursor-pointer"
            aria-label="Toggle dark mode"
          >
            <motion.div
              initial={false}
              animate={{ rotate: isDark ? 180 : 0 }}
              transition={{ duration: 0.3, ease: [0.23, 1, 0.32, 1] }}
            >
              {isDark ? <Sun size={17} /> : <Moon size={17} />}
            </motion.div>
          </button>

          <button
            className="p-2 text-text-muted hover:text-primary hover:bg-black/5 dark:hover:bg-white/5 rounded-lg transition-all focus-ring relative cursor-pointer"
            aria-label="Notifications"
          >
            <Bell size={17} />
            <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-secondary rounded-full border-2 border-surface" />
          </button>
        </div>

        <div className="w-px h-5 bg-border mx-0.5" />

        <button
          onClick={logout}
          className="flex items-center gap-2 px-2 md:px-3 py-1.5 text-sm font-medium text-text-muted hover:text-error hover:bg-error/10 rounded-lg transition-all focus-ring cursor-pointer"
        >
          <LogOut size={15} />
          <span className="hidden sm:inline">Log out</span>
        </button>
      </div>
    </header>
  )
}
