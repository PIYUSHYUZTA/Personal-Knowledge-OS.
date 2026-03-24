import React, { useRef, useState } from 'react'
import { UploadCloud, File, X, CheckCircle2 } from 'lucide-react'
import { cn } from '@/lib/utils'

export default function FileUploader() {
  const [isDragging, setIsDragging] = useState(false)
  const [uploadedFiles, setUploadedFiles] = useState<{name: string, size: string, status: 'uploading'|'success'}[]>([])
  const fileInputRef = useRef<HTMLInputElement>(null)

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
    const newFiles = Array.from(files).map(f => ({
      name: f.name,
      size: (f.size / 1024).toFixed(1) + ' KB',
      status: 'success' as const
    }))
    setUploadedFiles(prev => [...prev, ...newFiles])
    
    // Simulate API logic
    Array.from(files).forEach((file) => {
      console.log('File selected:', file.name)
      // TODO: Upload file using knowledgeAPI.uploadFile
    })
  }

  return (
    <div className="w-full">
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={cn(
          "w-full border-2 border-dashed rounded-2xl p-10 flex flex-col items-center justify-center transition-all duration-300 group cursor-pointer",
          isDragging
            ? "border-brand bg-brand/5 scale-[1.02]"
            : "border-border/60 bg-surface/30 hover:bg-surface/60 hover:border-brand/50"
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
          "w-16 h-16 rounded-full flex items-center justify-center mb-4 transition-all duration-300",
          isDragging ? "bg-brand text-white shadow-glow scale-110" : "bg-subtle text-muted group-hover:text-brand group-hover:bg-brand/10"
        )}>
          <UploadCloud size={32} />
        </div>

        <h3 className="text-base font-semibold text-primary mb-1">Click to upload or drag and drop</h3>
        <p className="text-sm text-muted text-center max-w-xs">
          PDF, Markdown, or TXT files (max. 10MB)
        </p>
      </div>

      {/* Uploaded Files List */}
      {uploadedFiles.length > 0 && (
        <div className="mt-6 space-y-3">
          <h4 className="text-sm font-semibold text-primary">Uploaded Documents</h4>
          <div className="max-h-48 overflow-y-auto space-y-2 pr-2">
            {uploadedFiles.map((f, i) => (
              <div key={i} className="flex items-center justify-between p-3 rounded-xl border border-border/50 bg-surface/50 animate-in fade-in slide-in-from-bottom-2">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg bg-emerald-500/10 text-emerald-500 flex items-center justify-center">
                    <File size={16} />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-primary line-clamp-1">{f.name}</p>
                    <p className="text-xs text-muted">{f.size}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle2 size={18} className="text-emerald-500" />
                  <button className="p-1 rounded-md text-muted hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-950/30 transition-colors">
                    <X size={16} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
