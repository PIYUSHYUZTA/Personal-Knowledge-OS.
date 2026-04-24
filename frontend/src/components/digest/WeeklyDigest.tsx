import React from 'react'

export default function WeeklyDigest() {
  return (
    <div className="h-full w-full bg-transparent text-on-background flex flex-col overflow-hidden relative selection:bg-primary/30 selection:text-primary">
      {/* Atmospheric Background Layers (Scoped to the window) */}
      <div className="absolute inset-0 z-0 pointer-events-none overflow-hidden">
        {/* Morning Gradient Overlay */}
        <div className="absolute top-[-20%] left-[-10%] w-[70%] h-[70%] bg-tertiary/10 rounded-full blur-[120px] mix-blend-screen"></div>
        <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] bg-primary/10 rounded-full blur-[100px]"></div>
      </div>

      {/* Main Content Canvas */}
      <div className="flex-1 relative z-10 flex flex-col p-6 md:p-8 gap-6 overflow-y-auto">
        {/* Header Section */}
        <header className="flex flex-col gap-2 mb-4">
          <div className="flex items-center gap-2 text-tertiary">
            <span className="material-symbols-outlined icon-fill text-[18px]">routine</span>
            <span className="font-space-grotesk text-xs tracking-widest uppercase font-bold">Morning Briefing</span>
          </div>
          <h1 className="font-space-grotesk text-4xl font-bold text-on-surface">Weekly Digest</h1>
          <p className="text-lg text-on-surface-variant max-w-2xl">
            Your synthesized intelligence for the week. We've surfaced emerging patterns and connections across your knowledge base.
          </p>
        </header>

        {/* Bento Grid Layout */}
        <div className="grid grid-cols-1 md:grid-cols-12 gap-6 auto-rows-min">
          
          {/* Card 1: Top Topics (Spans 8 cols) */}
          <section className="col-span-1 md:col-span-8 rounded-xl backdrop-blur-[20px] bg-white/5 border border-white/10 p-6 relative overflow-hidden flex flex-col gap-4 shadow-xl">
            {/* Morning Glow Accent */}
            <div className="absolute top-0 right-0 w-[300px] h-[300px] bg-gradient-to-bl from-tertiary/10 to-transparent blur-3xl pointer-events-none"></div>
            
            <header className="flex items-center justify-between border-b border-white/10 pb-2 z-10">
              <h2 className="text-xl font-bold text-on-surface flex items-center gap-2">
                <span className="material-symbols-outlined text-tertiary">trending_up</span>
                Top Topics This Week
              </h2>
              <span className="text-[10px] uppercase tracking-wider text-outline bg-white/5 px-2 py-1 rounded-full border border-white/10">High Engagement</span>
            </header>

            <div className="flex flex-col gap-3 z-10">
              {/* Topic Item 1 */}
              <div className="flex items-center justify-between p-4 rounded-lg bg-white/5 hover:bg-white/10 transition-colors border border-transparent hover:border-white/5 cursor-pointer">
                <div className="flex items-center gap-4">
                  <div className="w-10 h-10 rounded-full bg-primary/10 border border-primary/20 flex items-center justify-center text-primary shadow-lg">
                    <span className="material-symbols-outlined">psychology</span>
                  </div>
                  <div className="flex flex-col">
                    <span className="text-lg font-bold text-on-surface">Cognitive Architecture</span>
                    <span className="text-sm text-on-surface-variant">14 new nodes added · 3 connections</span>
                  </div>
                </div>
                {/* Sparkline Mockup */}
                <div className="w-24 h-8 flex items-end gap-1 opacity-70">
                  <div className="w-2 h-3 bg-tertiary/40 rounded-t-sm"></div>
                  <div className="w-2 h-5 bg-tertiary/60 rounded-t-sm"></div>
                  <div className="w-2 h-4 bg-tertiary/50 rounded-t-sm"></div>
                  <div className="w-2 h-7 bg-tertiary/80 rounded-t-sm"></div>
                  <div className="w-2 h-6 bg-tertiary/70 rounded-t-sm"></div>
                  <div className="w-2 h-8 bg-tertiary rounded-t-sm shadow-md"></div>
                </div>
              </div>

              {/* Topic Item 2 */}
              <div className="flex items-center justify-between p-4 rounded-lg bg-white/5 hover:bg-white/10 transition-colors border border-transparent hover:border-white/5 cursor-pointer">
                <div className="flex items-center gap-4">
                  <div className="w-10 h-10 rounded-full bg-secondary/10 border border-secondary/20 flex items-center justify-center text-secondary shadow-lg">
                    <span className="material-symbols-outlined">eco</span>
                  </div>
                  <div className="flex flex-col">
                    <span className="text-lg font-bold text-on-surface">Sustainable Systems</span>
                    <span className="text-sm text-on-surface-variant">8 new nodes added · 1 connection</span>
                  </div>
                </div>
                {/* Sparkline Mockup */}
                <div className="w-24 h-8 flex items-end gap-1 opacity-70">
                  <div className="w-2 h-2 bg-secondary/40 rounded-t-sm"></div>
                  <div className="w-2 h-3 bg-secondary/50 rounded-t-sm"></div>
                  <div className="w-2 h-2 bg-secondary/40 rounded-t-sm"></div>
                  <div className="w-2 h-5 bg-secondary/70 rounded-t-sm"></div>
                  <div className="w-2 h-4 bg-secondary/60 rounded-t-sm"></div>
                  <div className="w-2 h-6 bg-secondary rounded-t-sm shadow-md"></div>
                </div>
              </div>
            </div>
          </section>

          {/* Card 2: New Connections (Spans 4 cols) */}
          <section className="col-span-1 md:col-span-4 rounded-xl backdrop-blur-[20px] bg-white/5 border border-white/10 p-6 relative overflow-hidden flex flex-col gap-4 shadow-xl">
            <div className="absolute bottom-0 left-0 w-[200px] h-[200px] bg-gradient-to-tr from-primary/10 to-transparent blur-3xl pointer-events-none"></div>
            
            <header className="flex items-center justify-between border-b border-white/10 pb-2 z-10">
              <h2 className="text-xl font-bold text-on-surface flex items-center gap-2">
                <span className="material-symbols-outlined text-primary">hub</span>
                New Connections
              </h2>
            </header>

            <div className="flex-1 flex flex-col justify-center gap-6 z-10 py-4">
              <div className="flex flex-col gap-2 relative">
                {/* Connecting Line */}
                <div className="absolute left-[19px] top-6 bottom-6 w-px border-l border-dashed border-primary/30"></div>
                {/* Node 1 */}
                <div className="flex items-center gap-2 bg-white/5 border border-white/10 rounded-full px-3 py-1 w-max self-start shadow-sm z-10">
                  <div className="w-2 h-2 rounded-full bg-tertiary animate-pulse"></div>
                  <span className="text-xs font-bold text-on-surface">Game Theory</span>
                </div>
                {/* Middle connector icon */}
                <div className="w-10 h-6 flex items-center justify-center text-primary/60 z-10 ml-2">
                  <span className="material-symbols-outlined text-[16px]">swap_vert</span>
                </div>
                {/* Node 2 */}
                <div className="flex items-center gap-2 bg-white/5 border border-white/10 rounded-full px-3 py-1 w-max self-start ml-8 shadow-sm z-10">
                  <div className="w-2 h-2 rounded-full bg-secondary"></div>
                  <span className="text-xs font-bold text-on-surface">Market Dynamics</span>
                </div>
              </div>
            </div>
            
            <button className="w-full py-2 mt-auto bg-white/5 hover:bg-white/10 border border-white/10 rounded-md text-xs font-bold text-on-surface transition-colors">
              Explore Graph
            </button>
          </section>

          {/* Card 3: Time to Revisit (Spans 12 cols) */}
          <section className="col-span-1 md:col-span-12 rounded-xl backdrop-blur-[20px] bg-white/5 border border-white/10 p-6 relative overflow-hidden flex flex-col gap-4 shadow-xl">
            <header className="flex items-center justify-between border-b border-white/10 pb-2 z-10">
              <h2 className="text-xl font-bold text-on-surface flex items-center gap-2">
                <span className="material-symbols-outlined text-outline">history</span>
                Time to Revisit
              </h2>
              <span className="text-xs text-outline">Based on Spaced Repetition</span>
            </header>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 z-10">
              {/* Document Card 1 */}
              <div className="bg-white/5 border border-white/5 rounded-lg p-4 flex flex-col gap-2 hover:bg-white/10 hover:border-white/10 transition-all cursor-pointer group">
                <div className="flex justify-between items-start">
                  <span className="text-[10px] font-bold px-2 py-1 rounded bg-tertiary/10 text-tertiary border border-tertiary/20 uppercase tracking-wider">Philosophy</span>
                  <span className="material-symbols-outlined text-outline text-[18px] group-hover:text-primary transition-colors">arrow_outward</span>
                </div>
                <h3 className="text-lg font-bold text-on-surface leading-tight mt-1">Meditations on First Philosophy</h3>
                <p className="text-sm text-on-surface-variant line-clamp-2">Descartes' foundational work on epistemology and the nature of the mind...</p>
                <div className="mt-auto pt-2 flex items-center gap-1 text-outline text-[10px] uppercase font-bold tracking-wider">
                  <span className="material-symbols-outlined text-[14px]">calendar_today</span>
                  Last opened 45 days ago
                </div>
              </div>

              {/* Document Card 2 */}
              <div className="bg-white/5 border border-white/5 rounded-lg p-4 flex flex-col gap-2 hover:bg-white/10 hover:border-white/10 transition-all cursor-pointer group">
                <div className="flex justify-between items-start">
                  <span className="text-[10px] font-bold px-2 py-1 rounded bg-secondary/10 text-secondary border border-secondary/20 uppercase tracking-wider">Design</span>
                  <span className="material-symbols-outlined text-outline text-[18px] group-hover:text-primary transition-colors">arrow_outward</span>
                </div>
                <h3 className="text-lg font-bold text-on-surface leading-tight mt-1">The Humane Interface</h3>
                <p className="text-sm text-on-surface-variant line-clamp-2">Jef Raskin's critique of modern GUIs and proposals for efficiency...</p>
                <div className="mt-auto pt-2 flex items-center gap-1 text-outline text-[10px] uppercase font-bold tracking-wider">
                  <span className="material-symbols-outlined text-[14px]">calendar_today</span>
                  Last opened 60 days ago
                </div>
              </div>

              {/* Document Card 3 */}
              <div className="bg-white/5 border border-white/5 rounded-lg p-4 flex flex-col gap-2 hover:bg-white/10 hover:border-white/10 transition-all cursor-pointer group">
                <div className="flex justify-between items-start">
                  <span className="text-[10px] font-bold px-2 py-1 rounded bg-primary/10 text-primary border border-primary/20 uppercase tracking-wider">Physics</span>
                  <span className="material-symbols-outlined text-outline text-[18px] group-hover:text-primary transition-colors">arrow_outward</span>
                </div>
                <h3 className="text-lg font-bold text-on-surface leading-tight mt-1">Quantum Entanglement Basics</h3>
                <p className="text-sm text-on-surface-variant line-clamp-2">Notes on non-local interactions and Bell's theorem implications...</p>
                <div className="mt-auto pt-2 flex items-center gap-1 text-outline text-[10px] uppercase font-bold tracking-wider">
                  <span className="material-symbols-outlined text-[14px]">calendar_today</span>
                  Last opened 90+ days ago
                </div>
              </div>
            </div>
          </section>
        </div>
      </div>
    </div>
  )
}
