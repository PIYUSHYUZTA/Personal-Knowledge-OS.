import React, { createContext, useContext, useState, useCallback, useRef, useEffect } from 'react'
import { cn } from '@/lib/utils'
import { X, CheckCircle2, AlertTriangle, AlertCircle, Info } from 'lucide-react'
import { AnimatePresence, motion } from 'framer-motion'

type ToastType = 'success' | 'error' | 'warning' | 'info'

interface Toast {
  id: string
  type: ToastType
  title: string
  description?: string
  duration?: number
}

interface ToastContextType {
  addToast: (toast: Omit<Toast, 'id'>) => void
  removeToast: (id: string) => void
}

const ToastContext = createContext<ToastContextType | undefined>(undefined)

export function useToast() {
  const context = useContext(ToastContext)
  if (!context) {
    throw new Error('useToast must be used within ToastProvider')
  }
  return context
}

const icons: Record<ToastType, React.ReactNode> = {
  success: <CheckCircle2 size={18} />,
  error: <AlertCircle size={18} />,
  warning: <AlertTriangle size={18} />,
  info: <Info size={18} />,
}

const typeStyles: Record<ToastType, string> = {
  success: 'text-success border-success/20',
  error: 'text-error border-error/20',
  warning: 'text-warning border-warning/20',
  info: 'text-info border-info/20',
}

const progressStyles: Record<ToastType, string> = {
  success: 'bg-success',
  error: 'bg-error',
  warning: 'bg-warning',
  info: 'bg-info',
}

function ToastItem({ toast, onRemove }: { toast: Toast; onRemove: (id: string) => void }) {
  const duration = toast.duration || 5000
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    timerRef.current = setTimeout(() => {
      onRemove(toast.id)
    }, duration)
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current)
    }
  }, [toast.id, duration, onRemove])

  return (
    <motion.div
      layout
      initial={{ opacity: 0, x: 24, scale: 0.95 }}
      animate={{ opacity: 1, x: 0, scale: 1 }}
      exit={{ opacity: 0, x: 24, scale: 0.95 }}
      transition={{ duration: 0.2, ease: [0.23, 1, 0.32, 1] }}
      className={cn(
        'relative w-80 bg-surface border rounded-lg shadow-lg overflow-hidden backdrop-blur-xl',
        typeStyles[toast.type]
      )}
    >
      <div className="flex items-start gap-3 p-4">
        <span className="shrink-0 mt-0.5">{icons[toast.type]}</span>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-primary leading-tight">{toast.title}</p>
          {toast.description && (
            <p className="text-xs text-text-muted mt-1 leading-relaxed">{toast.description}</p>
          )}
        </div>
        <button
          onClick={() => onRemove(toast.id)}
          className="shrink-0 p-1 text-text-muted hover:text-primary transition-colors rounded-md cursor-pointer"
        >
          <X size={14} />
        </button>
      </div>
      {/* Progress bar */}
      <div className="h-0.5 w-full bg-border/30">
        <div
          className={cn('h-full', progressStyles[toast.type])}
          style={{ animation: `toast-progress ${duration}ms linear forwards` }}
        />
      </div>
    </motion.div>
  )
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])

  const addToast = useCallback((toast: Omit<Toast, 'id'>) => {
    const id = `toast-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
    setToasts(prev => {
      const next = [...prev, { ...toast, id }]
      // Stack max 3 toasts
      return next.slice(-3)
    })
  }, [])

  const removeToast = useCallback((id: string) => {
    setToasts(prev => prev.filter(t => t.id !== id))
  }, [])

  return (
    <ToastContext.Provider value={{ addToast, removeToast }}>
      {children}
      {/* Toast container */}
      <div className="fixed bottom-6 right-6 z-[9998] flex flex-col gap-2">
        <AnimatePresence mode="popLayout">
          {toasts.map(toast => (
            <ToastItem key={toast.id} toast={toast} onRemove={removeToast} />
          ))}
        </AnimatePresence>
      </div>
    </ToastContext.Provider>
  )
}
