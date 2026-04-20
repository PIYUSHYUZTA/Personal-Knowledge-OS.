import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { ArrowLeft, Compass } from 'lucide-react'

export default function NotFoundPage() {
  const navigate = useNavigate()

  return (
    <div className="flex relative min-h-screen items-center justify-center bg-background overflow-hidden selection:bg-secondary/20 selection:text-secondary">
      {/* Floating orbs */}
      <div className="absolute top-[15%] left-[15%] w-[35%] h-[35%] bg-error/5 blur-[120px] rounded-full pointer-events-none animate-float" />
      <div className="absolute bottom-[15%] right-[15%] w-[35%] h-[35%] bg-secondary/8 blur-[120px] rounded-full pointer-events-none animate-float" style={{ animationDelay: '2s' }} />
      <div className="absolute top-[50%] left-[60%] w-[20%] h-[20%] bg-accent/6 blur-[80px] rounded-full pointer-events-none animate-float" style={{ animationDelay: '4s' }} />

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease: 'easeOut' }}
        className="w-full max-w-lg px-4 relative z-10 text-center flex flex-col items-center"
      >
        <div className="w-20 h-20 mb-8 rounded-2xl bg-black/5 dark:bg-white/5 flex items-center justify-center shadow-inner relative overflow-hidden">
          <div className="absolute inset-0 bg-secondary/10 opacity-50 backdrop-blur-3xl" />
          <Compass size={40} className="text-secondary relative z-10" strokeWidth={1.5} />
        </div>

        <motion.h1
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.5, delay: 0.1 }}
          className="text-[120px] font-bold leading-none tracking-tighter gradient-text"
        >
          404
        </motion.h1>

        <p className="text-lg text-text-muted mt-4 mb-10 max-w-sm mx-auto">
          The knowledge chunk you're looking for has drifted into the void.
        </p>

        <button
          id="not-found-go-home"
          onClick={() => navigate('/')}
          className="flex items-center gap-2 px-6 py-3 bg-secondary hover:bg-secondary/90 hover:scale-105 active:scale-95 text-white font-medium rounded-full transition-all duration-fast shadow-md shadow-secondary/20 group"
        >
          <ArrowLeft size={16} className="group-hover:-translate-x-1 transition-transform" />
          Return to Dashboard
        </button>
      </motion.div>
    </div>
  )
}
