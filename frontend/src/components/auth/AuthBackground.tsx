import React from 'react'

export default function AuthBackground() {
  return (
    <div className="absolute inset-0 z-[-1] overflow-hidden bg-[#050508]">
      {/* Immersive Video Layer */}
      <video
        autoPlay
        loop
        muted
        playsInline
        className="absolute inset-0 w-full h-full object-cover opacity-60 scale-105"
        style={{ filter: 'contrast(1.2) brightness(0.8) saturate(1.1)' }}
      >
        <source src="/background_new.mp4" type="video/mp4" />
        <source src="/mp4.mp4" type="video/mp4" />
        <source src="/mp4" type="video/mp4" />
        <source src="https://assets.mixkit.co/videos/preview/mixkit-abstract-neural-network-animation-9128-large.mp4" type="video/mp4" />
      </video>

      {/* 1. Perspective Grid Plane */}
      <div 
        className="absolute inset-0 pointer-events-none opacity-20"
        style={{
          perspective: '1000px',
          background: `
            linear-gradient(rgba(124, 77, 255, 0.1) 1px, transparent 1px),
            linear-gradient(90deg, rgba(124, 77, 255, 0.1) 1px, transparent 1px)
          `,
          backgroundSize: '100px 100px',
          transform: 'rotateX(60deg) translateY(20%) scale(2)',
          maskImage: 'linear-gradient(to bottom, transparent, black 40%, black 60%, transparent)',
          WebkitMaskImage: 'linear-gradient(to bottom, transparent, black 40%, black 60%, transparent)'
        }}
      />

      {/* 2. Distant Starfield (Large) */}
      <div className="absolute inset-0 pointer-events-none opacity-30 animate-slow-drift" 
        style={{
          backgroundImage: 'radial-gradient(1px 1px at 20px 30px, #fff, rgba(0,0,0,0)), radial-gradient(1px 1px at 40px 70px, #fff, rgba(0,0,0,0)), radial-gradient(2px 2px at 50px 160px, #fff, rgba(0,0,0,0)), radial-gradient(2px 2px at 90px 40px, #fff, rgba(0,0,0,0)), radial-gradient(1px 1px at 130px 80px, #fff, rgba(0,0,0,0)), radial-gradient(1px 1px at 160px 120px, #fff, rgba(0,0,0,0))',
          backgroundSize: '200px 200px'
        }}
      />

      {/* 3. Cinematic Overlays */}
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,transparent_20%,rgba(0,0,0,0.8)_100%)] pointer-events-none" />
      <div className="absolute inset-0 bg-primary/5 mix-blend-overlay pointer-events-none animate-pulse" style={{ animationDuration: '8s' }} />
      <div className="absolute inset-0 bg-[linear-gradient(rgba(18,16,16,0)_50%,rgba(0,0,0,0.1)_50%),linear-gradient(90deg,rgba(255,0,0,0.02),rgba(0,255,0,0.01),rgba(0,0,255,0.02))] bg-[length:100%_2px,3px_100%] pointer-events-none opacity-20" />
      <div className="absolute inset-0 bg-gradient-to-tr from-primary/10 via-transparent to-secondary/10 opacity-40 pointer-events-none blur-3xl animate-slow-drift" />
      <div className="absolute inset-0 opacity-[0.03] pointer-events-none bg-[url('data:image/svg+xml,%3Csvg viewBox=%220 0 200 200%22 xmlns=%22http://www.w3.org/2000/svg%22%3E%3Cfilter id=%22noise%22%3E%3CfeTurbulence type=%22fractalNoise%22 baseFrequency=%220.85%22 numOctaves=%224%22 stitchTiles=%22stitch%22/%3E%3C/filter%3E%3Crect width=%22100%25%22 height=%22100%25%22 filter=%22url(%23noise)%22/%3E%3C/svg%3E')]" />
    </div>
  )
}


