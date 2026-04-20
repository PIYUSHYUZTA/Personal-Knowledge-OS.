import React, { useRef, useState } from 'react'
import { UploadCloud, File, X, CheckCircle2, Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import { motion, AnimatePresence } from 'framer-motion'
import { useDesktopStore } from '@/store/useDesktopStore'
import { useAura } from '@/context/AuraContext'

export default function FileUploader() {
  const [isDragging, setIsDragging] = useState(false)
  const [uploadedFiles, setUploadedFiles] = useState<{name: string, size: string, status: 'uploading'|'success'}[]>([])
  const fileInputRef = useRef<HTMLInputElement>(null)

  // ── Bridge to Zustand + AuraContext ─────────────────────────
  const { addUploadedFile, openWindow } = useDesktopStore()
  const { addSystemMessage } = useAura()

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }

  const handleDragLeave = () => {
    setIsDragging(false)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    const files = e.dataTransfer.files
    handleFiles(files)
  }

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (files) {
      handleFiles(files)
    }
  }

  const handleFiles = (files: FileList) => {
    // ── Step 1: Add files to local state with 'uploading' status ──
    const newFiles = Array.from(files).map(f => ({
      name: f.name,
      size: (f.size / 1024).toFixed(1) + ' KB',
      status: 'uploading' as const
    }))
    setUploadedFiles(prev => [...prev, ...newFiles])

    // ── Step 2: Simulate upload delay (1.5s), then mark success ──
    setTimeout(() => {
      setUploadedFiles(prev =>
        prev.map(f =>
          f.status === 'uploading' ? { ...f, status: 'success' as const } : f
        )
      )

      // ── Step 3: Register each file in Zustand for cross-component access ──
      Array.from(files).forEach(file => {
        addUploadedFile({ name: file.name, size: file.size })

        // ── Step 4: Inject system message into AURA chat ──
        addSystemMessage(
          `📄 **File received: ${file.name}** (${(file.size / 1024).toFixed(1)} KB)\n\n` +
          `Indexing content into knowledge graph... Processing complete.\n` +
          `You can now ask me questions about this document.`
        )
      })

      // ── Step 5: Auto-open the AURA chat window ──
      openWindow('aura', 'AURA Intelligence', 'aura')
    }, 1500)
  }

  const removeFile = (index: number) => {
    setUploadedFiles(prev => prev.filter((_, i) => i !== index))
  }

  return (
    <div className="w-full">
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={cn(
          "w-full border-2 border-dashed rounded-xl p-10 flex flex-col items-center justify-center transition-all duration-300 group cursor-pointer relative overflow-hidden",
          isDragging
            ? "border-[#FF5722] bg-[#FF5722]/5 scale-[1.02]"
            : "border-[#27272A] bg-[#1A1B22]/40 hover:bg-[#1A1B22]/60 hover:border-[#FF5722]/50"
        )}
        onClick={() => fileInputRef.current?.click()}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          onChange={handleFileSelect}
          className="hidden"
        />

        <div className={cn(
          "w-12 h-12 rounded-full flex items-center justify-center mb-4 transition-all duration-300",
          isDragging ? "bg-[#FF5722] text-white shadow-[0_0_20px_rgba(255,87,34,0.4)] scale-110" : "bg-[#27272A]/50 text-[#A1A1AA] group-hover:text-[#FF5722] group-hover:bg-[#FF5722]/10"
        )}>
          <UploadCloud size={24} />
        </div>

        <h3 className="text-sm font-medium text-[#ECECEF] mb-1">Click to upload or drag and drop</h3>
        <p className="text-xs text-[#71717A] text-center max-w-xs">
          PDF, Markdown, or TXT files (max. 10MB)
        </p>
      </div>

      {/* Uploaded Files List */}
      <AnimatePresence>
        {uploadedFiles.length > 0 && (
          <motion.div 
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="mt-6 space-y-3 relative z-10"
          >
            <h4 className="text-[11px] font-semibold text-[#71717A] uppercase tracking-wider">Uploaded Documents</h4>
            <div className="max-h-48 overflow-y-auto space-y-2 pr-2">
              <AnimatePresence>
                {uploadedFiles.map((f, i) => (
                  <motion.div 
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.1 }}
                    key={`${f.name}-${i}`}
                    className="flex items-center justify-between p-3 rounded-lg border border-[#27272A]/60 bg-[#1A1B22]/60 backdrop-blur-sm hover:border-[#27272A] transition-colors group"
                  >
                    <div className="flex items-center gap-3">
                      <div className={cn(
                        "w-8 h-8 rounded-md flex items-center justify-center",
                        f.status === 'uploading' ? "bg-[#FF5722]/10 text-[#FF5722]" : "bg-emerald-500/10 text-emerald-400"
                      )}>
                        {f.status === 'uploading' ? (
                          <Loader2 size={16} className="animate-spin" />
                        ) : (
                          <File size={16} />
                        )}
                      </div>
                      <div>
                        <p className="text-sm font-medium text-[#ECECEF] line-clamp-1">{f.name}</p>
                        <p className="text-[11px] text-[#71717A]">
                          {f.size} — {f.status === 'uploading' ? (
                            <span className="text-[#FF5722]">Uploading...</span>
                          ) : (
                            <span className="text-emerald-400">Indexed ✓</span>
                          )}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {f.status === 'success' && (
                        <CheckCircle2 size={16} className="text-emerald-400 opacity-0 group-hover:opacity-100 transition-opacity" />
                      )}
                      <button 
                        onClick={(e) => { e.stopPropagation(); removeFile(i) }}
                        className="p-1.5 rounded-md text-[#71717A] hover:text-red-400 hover:bg-red-500/10 transition-colors cursor-pointer"
                      >
                        <X size={14} />
                      </button>
                    </div>
                  </motion.div>
                ))}
              </AnimatePresence>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
