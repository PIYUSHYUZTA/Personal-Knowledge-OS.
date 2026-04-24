import React from 'react'

export default function SearchView() {
  return (
    <div className="h-full w-full bg-transparent text-on-surface flex flex-col overflow-hidden relative selection:bg-primary/30 selection:text-primary">
      {/* Search Content Container */}
      <div className="flex-1 overflow-y-auto relative z-10 p-6 md:p-8">
        
        {/* Search Header Section */}
        <div className="max-w-4xl mx-auto mt-8 mb-8 flex flex-col items-center">
          <h1 className="font-space-grotesk text-4xl font-bold text-on-surface mb-6 text-center">Omni Search</h1>
          
          {/* Large Search Bar */}
          <div className="w-full relative group">
            <span className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-on-surface-variant z-10">search</span>
            <input 
              className="w-full h-16 pl-14 pr-4 rounded-xl dashboard-v2-glass text-lg font-medium text-on-surface focus:outline-none focus:ring-2 focus:ring-primary/50 placeholder-on-surface-variant transition-all shadow-xl" 
              placeholder="Query your knowledge universe..." 
              type="text" 
              defaultValue="neural network architectures"
            />
            <div className="absolute right-4 top-1/2 -translate-y-1/2 flex gap-2">
              <span className="px-2 py-1 rounded bg-white/5 text-on-surface-variant font-bold text-[10px] border border-white/10 uppercase tracking-widest">⌘K</span>
            </div>
          </div>

          {/* Filters */}
          <div className="flex flex-wrap justify-center gap-2 mt-6">
            <button className="px-4 py-1.5 rounded-full bg-primary/20 text-primary border border-primary/50 text-xs font-bold flex items-center gap-2 shadow-[0_0_15px_rgba(124,77,255,0.3)]">
              <span className="material-symbols-outlined text-[16px]">sort</span>
              Relevance
            </button>
            <button className="px-4 py-1.5 rounded-full dashboard-v2-glass text-on-surface-variant text-xs font-bold flex items-center gap-2 hover:bg-white/10 transition-colors">
              <span className="material-symbols-outlined text-[16px]">picture_as_pdf</span>
              PDFs
            </button>
            <button className="px-4 py-1.5 rounded-full dashboard-v2-glass text-on-surface-variant text-xs font-bold flex items-center gap-2 hover:bg-white/10 transition-colors">
              <span className="material-symbols-outlined text-[16px]">markdown</span>
              Markdown
            </button>
            <button className="px-4 py-1.5 rounded-full dashboard-v2-glass text-on-surface-variant text-xs font-bold flex items-center gap-2 hover:bg-white/10 transition-colors">
              <span className="material-symbols-outlined text-[16px]">description</span>
              Text
            </button>
          </div>
        </div>

        {/* Results Grid */}
        <div className="max-w-4xl mx-auto flex flex-col gap-4 pb-12">
          
          {/* Result Card 1 */}
          <article className="dashboard-v2-glass p-4 rounded-xl flex gap-4 items-start group hover:bg-white/10 transition-all cursor-pointer">
            {/* Source Icon */}
            <div className="w-12 h-12 rounded-lg bg-secondary/10 flex items-center justify-center shrink-0 border border-secondary/20">
              <span className="material-symbols-outlined text-secondary font-bold">markdown</span>
            </div>
            
            {/* Content */}
            <div className="flex-1 min-w-0">
              <div className="flex justify-between items-start mb-1">
                <h2 className="text-xl font-bold text-on-surface truncate">Deep Learning Architectures 2024.md</h2>
                
                {/* Relevance Score Ring */}
                <div className="relative w-8 h-8 flex items-center justify-center shrink-0 ml-4">
                  <svg className="w-full h-full transform -rotate-90" viewBox="0 0 36 36">
                    <circle className="stroke-white/10" cx="18" cy="18" fill="none" r="16" strokeWidth="3"></circle>
                    <circle className="stroke-primary" cx="18" cy="18" fill="none" r="16" strokeDasharray="100 100" strokeDashoffset="5" strokeWidth="3"></circle>
                  </svg>
                  <span className="absolute text-[10px] font-bold text-primary">95</span>
                </div>
              </div>
              
              <p className="text-sm text-on-surface-variant line-clamp-2 mb-3">
                An overview of modern <span className="text-primary bg-primary/10 px-1 rounded">neural network architectures</span> including Transformers, Diffusion models, and State Space Models. The evolution from early CNNs...
              </p>
              
              <div className="flex flex-wrap gap-2">
                <span className="px-2 py-0.5 rounded-full bg-white/5 text-on-surface-variant text-[10px] font-bold uppercase tracking-wider">Machine Learning</span>
                <span className="px-2 py-0.5 rounded-full bg-white/5 text-on-surface-variant text-[10px] font-bold uppercase tracking-wider">Research</span>
                <span className="text-on-surface-variant/50 text-[10px] font-bold uppercase tracking-wider ml-auto flex items-center">Modified 2d ago</span>
              </div>
            </div>
          </article>

          {/* Result Card 2 */}
          <article className="dashboard-v2-glass p-4 rounded-xl flex gap-4 items-start group hover:bg-white/10 transition-all cursor-pointer">
            <div className="w-12 h-12 rounded-lg bg-error/10 flex items-center justify-center shrink-0 border border-error/20">
              <span className="material-symbols-outlined text-error font-bold">picture_as_pdf</span>
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex justify-between items-start mb-1">
                <h2 className="text-xl font-bold text-on-surface truncate">Attention is All You Need.pdf</h2>
                <div className="relative w-8 h-8 flex items-center justify-center shrink-0 ml-4">
                  <svg className="w-full h-full transform -rotate-90" viewBox="0 0 36 36">
                    <circle className="stroke-white/10" cx="18" cy="18" fill="none" r="16" strokeWidth="3"></circle>
                    <circle className="stroke-primary" cx="18" cy="18" fill="none" r="16" strokeDasharray="100 100" strokeDashoffset="18" strokeWidth="3"></circle>
                  </svg>
                  <span className="absolute text-[10px] font-bold text-primary">82</span>
                </div>
              </div>
              <p className="text-sm text-on-surface-variant line-clamp-2 mb-3">
                We propose a new simple <span className="text-primary bg-primary/10 px-1 rounded">network architecture</span>, the Transformer, based solely on attention mechanisms, dispensing with recurrence and convolutions entirely...
              </p>
              <div className="flex flex-wrap gap-2">
                <span className="px-2 py-0.5 rounded-full bg-white/5 text-on-surface-variant text-[10px] font-bold uppercase tracking-wider">Paper</span>
                <span className="px-2 py-0.5 rounded-full bg-white/5 text-on-surface-variant text-[10px] font-bold uppercase tracking-wider">Transformers</span>
                <span className="text-on-surface-variant/50 text-[10px] font-bold uppercase tracking-wider ml-auto flex items-center">Modified 1y ago</span>
              </div>
            </div>
          </article>

          {/* Result Card 3 */}
          <article className="dashboard-v2-glass p-4 rounded-xl flex gap-4 items-start group hover:bg-white/10 transition-all cursor-pointer">
            <div className="w-12 h-12 rounded-lg bg-white/5 flex items-center justify-center shrink-0 border border-white/10">
              <span className="material-symbols-outlined text-on-surface-variant">description</span>
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex justify-between items-start mb-1">
                <h2 className="text-xl font-bold text-on-surface truncate">Meeting Notes - AI Strategy.txt</h2>
                <div className="relative w-8 h-8 flex items-center justify-center shrink-0 ml-4">
                  <svg className="w-full h-full transform -rotate-90" viewBox="0 0 36 36">
                    <circle className="stroke-white/10" cx="18" cy="18" fill="none" r="16" strokeWidth="3"></circle>
                    <circle className="stroke-primary" cx="18" cy="18" fill="none" r="16" strokeDasharray="100 100" strokeDashoffset="35" strokeWidth="3"></circle>
                  </svg>
                  <span className="absolute text-[10px] font-bold text-primary">65</span>
                </div>
              </div>
              <p className="text-sm text-on-surface-variant line-clamp-2 mb-3">
                Discussed potential implementation of novel <span className="text-primary bg-primary/10 px-1 rounded">neural networks</span> for the upcoming product pipeline. Need to review current computational constraints...
              </p>
              <div className="flex flex-wrap gap-2">
                <span className="px-2 py-0.5 rounded-full bg-white/5 text-on-surface-variant text-[10px] font-bold uppercase tracking-wider">Notes</span>
                <span className="px-2 py-0.5 rounded-full bg-white/5 text-on-surface-variant text-[10px] font-bold uppercase tracking-wider">Work</span>
                <span className="text-on-surface-variant/50 text-[10px] font-bold uppercase tracking-wider ml-auto flex items-center">Modified 1w ago</span>
              </div>
            </div>
          </article>
          
        </div>
      </div>
    </div>
  )
}
