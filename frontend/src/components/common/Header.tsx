import { useEffect, useState } from 'react';
import { useAuth } from '@/context/AuthContext';
import { User } from '@/types';
import { LogOut, Sun, Moon, Bell, Menu } from 'lucide-react';

interface HeaderProps {
  user: User | null;
  toggleMobileMenu: () => void;
}

export default function Header({ user, toggleMobileMenu }: HeaderProps) {
  const { logout } = useAuth();
  const [isDark, setIsDark] = useState(false);

  useEffect(() => {
    // Check initial user preference
    if (document.documentElement.classList.contains('dark')) {
      setIsDark(true);
    }
  }, []);

  const toggleDarkMode = () => {
    const root = document.documentElement;
    if (root.classList.contains('dark')) {
      root.classList.remove('dark');
      setIsDark(false);
      localStorage.setItem('theme', 'light');
    } else {
      root.classList.add('dark');
      setIsDark(true);
      localStorage.setItem('theme', 'dark');
    }
  };

  return (
    <header className="h-16 border-b border-border/50 bg-surface/50 backdrop-blur-md px-4 md:px-8 flex justify-between items-center sticky top-0 z-30">
      <div className="flex items-center gap-4">
        <button 
          onClick={toggleMobileMenu}
          className="md:hidden p-2 -ml-2 text-muted hover:text-primary transition-colors focus-ring rounded-lg"
          aria-label="Toggle menu"
        >
          <Menu size={24} />
        </button>
        <div>
          <h2 className="text-lg font-semibold text-primary hidden md:block">Good evening,</h2>
          <p className="text-xs text-muted mt-0.5">{user?.email}</p>
        </div>
      </div>

      <div className="flex items-center gap-2 md:gap-4">
        {/* Actions */}
        <div className="flex items-center gap-1 md:gap-2">
          <button 
            onClick={toggleDarkMode}
            className="p-2 text-muted hover:text-primary hover:bg-subtle rounded-full transition-colors focus-ring"
            aria-label="Toggle dark mode"
          >
            {isDark ? <Sun size={18} /> : <Moon size={18} />}
          </button>
          <button 
            className="p-2 text-muted hover:text-primary hover:bg-subtle rounded-full transition-colors focus-ring relative hidden sm:block"
            aria-label="Notifications"
          >
            <Bell size={18} />
            <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-brand rounded-full ring-2 ring-background"></span>
          </button>
        </div>

        <div className="w-px h-6 bg-border mx-1 md:mx-2" />

        <button
          onClick={logout}
          className="flex items-center gap-2 px-2 md:px-3 py-1.5 text-sm font-medium text-muted hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-950/30 rounded-md transition-colors focus-ring"
        >
          <LogOut size={16} />
          <span className="hidden sm:inline">Logout</span>
        </button>
      </div>
    </header>
  );
}
