import { useState } from 'react'
import { useAuth } from '@/context/AuthContext'
import { useKnowledge } from '@/context/KnowledgeContext'
import Sidebar from '@/components/common/Sidebar'
import Header from '@/components/common/Header'
import KnowledgeVisualizer from '@/components/knowledge/KnowledgeVisualizer'
import AuraChat from '@/components/aura/AuraChat'
import FileUploader from '@/components/ingestion/FileUploader'
import { Database, FolderHeart, Activity } from 'lucide-react'

export default function Dashboard() {
  const { user } = useAuth()
  const { sources } = useKnowledge()
  const [activeTab, setActiveTab] = useState<'dashboard' | 'knowledge' | 'aura'>('dashboard')
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false)

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      {/* Sidebar */}
      <Sidebar 
        activeTab={activeTab} 
        setActiveTab={(tab) => {
          setActiveTab(tab)
          setIsMobileMenuOpen(false)
        }} 
        isOpen={isMobileMenuOpen}
        setIsOpen={setIsMobileMenuOpen}
      />

      {/* Main Content */}
      <div className="flex-1 flex flex-col relative overflow-hidden">
        {/* Header */}
        <Header 
          user={user} 
          toggleMobileMenu={() => setIsMobileMenuOpen(!isMobileMenuOpen)} 
        />

        {/* Content */}
        <main className="flex-1 overflow-auto p-4 md:p-8 relative">
          {activeTab === 'dashboard' && (
            <div className="max-w-6xl mx-auto space-y-6 md:space-y-8 animate-in fade-in zoom-in-95 duration-500">
              
              {/* Stat Cards - Bento Grid Style */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 md:gap-6">
                <div className="glass-card rounded-2xl p-6 group">
                  <div className="flex items-start justify-between mb-4">
                    <div className="p-3 bg-brand/10 text-brand rounded-xl">
                      <FolderHeart size={20} />
                    </div>
                  </div>
                  <h3 className="text-sm font-medium text-muted">Knowledge Sources</h3>
                  <div className="mt-2 flex items-baseline gap-2">
                    <p className="text-3xl font-bold tracking-tight text-primary">{sources.length}</p>
                  </div>
                </div>

                <div className="glass-card rounded-2xl p-6 group">
                  <div className="flex items-start justify-between mb-4">
                    <div className="p-3 bg-amber-500/10 text-amber-500 rounded-xl">
                      <Database size={20} />
                    </div>
                  </div>
                  <h3 className="text-sm font-medium text-muted">Total Chunks</h3>
                  <div className="mt-2 flex items-baseline gap-2">
                    <p className="text-3xl font-bold tracking-tight text-primary">
                      {sources.reduce((sum, s) => sum + s.chunks_count, 0)}
                    </p>
                  </div>
                </div>

                <div className="glass-card rounded-2xl p-6 group">
                  <div className="flex items-start justify-between mb-4">
                    <div className="p-3 bg-emerald-500/10 text-emerald-500 rounded-xl">
                      <Activity size={20} />
                    </div>
                  </div>
                  <h3 className="text-sm font-medium text-muted">System Status</h3>
                  <div className="mt-2 flex items-baseline gap-2">
                    <p className="text-3xl font-bold tracking-tight text-primary">Active</p>
                    <span className="text-xs font-medium text-emerald-500 bg-emerald-500/10 px-2 py-0.5 rounded-full ring-1 ring-emerald-500/20 z-10">Optimal</span>
                  </div>
                </div>
              </div>

              {/* Upload Section */}
              <div className="glass-card rounded-2xl p-6 md:p-8 relative overflow-hidden">
                <div className="absolute top-0 right-0 w-64 h-64 bg-brand/5 blur-[100px] rounded-full pointer-events-none" />
                <div className="relative z-10">
                  <h2 className="text-xl font-semibold mb-1 text-primary">Ingest Knowledge</h2>
                  <p className="text-sm text-muted mb-6">Upload documents or connect data sources to expand PKOS.</p>
                  <FileUploader />
                </div>
              </div>
            </div>
          )}

          {activeTab === 'knowledge' && (
            <div className="h-full animate-in fade-in zoom-in-95 duration-500 flex flex-col">
              <div className="mb-4 md:mb-6 flex-shrink-0">
                <h2 className="text-xl font-semibold text-primary">Knowledge Graph</h2>
                <p className="text-sm text-muted">Visualize the semantic relationships in your brain.</p>
              </div>
              <div className="flex-1 glass-card rounded-2xl p-2 overflow-hidden relative border border-border/60">
                <KnowledgeVisualizer />
              </div>
            </div>
          )}

          {activeTab === 'aura' && (
            <div className="h-full flex flex-col max-w-5xl mx-auto animate-in fade-in zoom-in-95 duration-500">
               <div className="mb-4 md:mb-6 flex items-center justify-between flex-shrink-0">
                <div>
                  <h2 className="text-xl font-semibold text-primary">AURA Intelligence</h2>
                  <p className="text-sm text-muted">Your personal AI companion across all knowledge.</p>
                </div>
              </div>
              <div className="flex-1 glass-card rounded-2xl border border-border/60 overflow-hidden flex flex-col relative z-20">
                <AuraChat />
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  )
}
