import { LayoutDashboard, Network, MessageSquareText, X } from 'lucide-react';
import { cn } from '@/lib/utils';

interface SidebarProps {
  activeTab: string;
  setActiveTab: (tab: 'dashboard' | 'knowledge' | 'aura') => void;
  isOpen?: boolean;
  setIsOpen?: (open: boolean) => void;
}

export default function Sidebar({ activeTab, setActiveTab, isOpen, setIsOpen }: SidebarProps) {
  const tabs = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'knowledge', label: 'Knowledge Map', icon: Network },
    { id: 'aura', label: 'AURA Chat', icon: MessageSquareText },
  ];

  return (
    <>
      {/* Mobile Overlay */}
      {isOpen && (
        <div 
          className="fixed inset-0 bg-background/80 backdrop-blur-sm z-40 md:hidden animate-in fade-in"
          onClick={() => setIsOpen?.(false)}
        />
      )}

      <aside className={cn(
        "fixed md:relative top-0 left-0 h-full w-64 border-r border-border/50 bg-surface/80 backdrop-blur-2xl flex flex-col z-50 transition-transform duration-300 ease-in-out shadow-2xl md:shadow-none",
        isOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"
      )}>
        {/* Logo */}
        <div className="p-6 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-brand text-white flex items-center justify-center font-bold shadow-glow">
              PK
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight text-primary">PKOS</h1>
            </div>
          </div>
          <button 
            className="md:hidden p-2 text-muted hover:text-primary transition-colors focus-ring rounded-lg cursor-pointer"
            onClick={() => setIsOpen?.(false)}
          >
            <X size={20} />
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-4 py-2 space-y-1">
          <div className="text-xs font-semibold text-muted uppercase tracking-wider mb-4 px-2">Overview</div>
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={cn(
                  "w-full flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium transition-all duration-200 group relative cursor-pointer",
                  isActive 
                    ? "text-brand bg-brand/10" 
                    : "text-muted hover:text-primary hover:bg-subtle"
                )}
              >
                {isActive && (
                  <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-5 bg-brand rounded-r-full" />
                )}
                <Icon size={18} className={cn(
                  "transition-transform duration-200", 
                  isActive ? "text-brand" : "group-hover:text-primary group-hover:scale-110"
                )} />
                {tab.label}
              </button>
            );
          })}
        </nav>

        {/* Footer */}
        <div className="p-6 mt-auto">
          <div className="bg-subtle/50 border border-border/50 rounded-lg p-4 relative overflow-hidden group hover:border-brand/30 transition-colors">
            <div className="relative z-10">
              <p className="text-xs font-semibold text-primary mb-1">Early Access</p>
              <p className="text-[10px] text-muted leading-tight mb-3">You're on the v1.0.0-alpha block.</p>
              <button className="text-[10px] font-semibold text-brand hover:underline cursor-pointer">View Changelog</button>
            </div>
            <div className="absolute -top-4 -right-4 w-16 h-16 bg-brand opacity-10 blur-xl group-hover:opacity-20 transition-opacity duration-500 rounded-full"></div>
          </div>
        </div>
      </aside>
    </>
  );
}
