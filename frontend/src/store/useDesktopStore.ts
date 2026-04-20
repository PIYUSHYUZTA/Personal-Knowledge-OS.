import { create } from 'zustand'

export type AppType = 'knowledge' | 'aura' | 'ingestion' | 'settings' | 'caffeine'

export interface AppWindow {
  id: string
  title: string
  appType: AppType
  isOpen: boolean
  isMinimized: boolean
  zIndex: number
  position: { x: number; y: number }
  size: { width: number; height: number }
}

// ── Uploaded file record for Uploader → Chat bridge ──────────
export interface UploadedFileRecord {
  name: string
  size: number     // bytes
  addedAt: number  // Date.now() timestamp
}

interface DesktopStore {
  windows: AppWindow[]
  activeWindowId: string | null
  zenMode: boolean

  // ── Upload–Chat bridge state ───────────────────────────────
  uploadedFiles: UploadedFileRecord[]

  // Window actions
  toggleZenMode: () => void
  openWindow: (id: string, title: string, appType: AppType, defaultProps?: Partial<AppWindow>) => void
  closeWindow: (id: string) => void
  focusWindow: (id: string) => void
  toggleMinimize: (id: string) => void
  updateWindowPosition: (id: string, position: { x: number; y: number }) => void
  updateWindowSize: (id: string, size: { width: number; height: number }) => void

  // Upload bridge actions
  addUploadedFile: (file: { name: string; size: number }) => void
  clearUploadedFiles: () => void
}

let zIndexCounter = 100

export const useDesktopStore = create<DesktopStore>((set, get) => ({
  windows: [],
  activeWindowId: null,
  zenMode: false,
  uploadedFiles: [],

  toggleZenMode: () => set((state) => ({ zenMode: !state.zenMode })),

  openWindow: (id, title, appType, defaultProps) => {
    set((state) => {
      const existing = state.windows.find(w => w.id === id)
      if (existing) {
        // Bring to front and ensure open/unminimized
        const newZ = ++zIndexCounter
        return {
          windows: state.windows.map(w => 
            w.id === id ? { ...w, isOpen: true, isMinimized: false, zIndex: newZ } : w
          ),
          activeWindowId: id
        }
      }

      // Create new window
      const newWindow: AppWindow = {
        id,
        title,
        appType,
        isOpen: true,
        isMinimized: false,
        zIndex: ++zIndexCounter,
        position: defaultProps?.position || { x: 100 + state.windows.length * 40, y: 100 + state.windows.length * 40 },
        size: defaultProps?.size || { width: 800, height: 600 }
      }

      return {
        windows: [...state.windows, newWindow],
        activeWindowId: id
      }
    })
  },

  closeWindow: (id) => {
    set((state) => {
      const remaining = state.windows.filter(w => w.id !== id)
      const nextActive = remaining.length > 0 ? remaining.reduce((prev, curr) => (prev.zIndex > curr.zIndex ? prev : curr)).id : null
      return {
        windows: remaining,
        activeWindowId: state.activeWindowId === id ? nextActive : state.activeWindowId
      }
    })
  },

  focusWindow: (id) => {
    set((state) => {
      if (state.activeWindowId === id) return state
      const target = state.windows.find(w => w.id === id)
      if (!target || target.isMinimized) return state
      
      const newZ = ++zIndexCounter
      return {
        windows: state.windows.map(w => w.id === id ? { ...w, zIndex: newZ } : w),
        activeWindowId: id
      }
    })
  },

  toggleMinimize: (id) => {
    set((state) => {
      const win = state.windows.find(w => w.id === id)
      if (!win) return state
      
      const willMinimize = !win.isMinimized
      const newWindows = state.windows.map(w => w.id === id ? { ...w, isMinimized: willMinimize } : w)
      
      let nextActive = state.activeWindowId
      if (willMinimize && state.activeWindowId === id) {
        // give focus to highest zIndex non-minimized window
        const activeCandidates = newWindows.filter(w => !w.isMinimized)
        nextActive = activeCandidates.length > 0 ? activeCandidates.reduce((prev, curr) => (prev.zIndex > curr.zIndex ? prev : curr)).id : null
      } else if (!willMinimize) {
        nextActive = id
        // bring to front
        const newZ = ++zIndexCounter
        for(let i=0; i<newWindows.length; i++){
            if(newWindows[i].id === id) newWindows[i].zIndex = newZ;
        }
      }

      return { windows: newWindows, activeWindowId: nextActive }
    })
  },

  updateWindowPosition: (id, position) => {
    set((state) => ({
      windows: state.windows.map(w => w.id === id ? { ...w, position } : w)
    }))
  },

  updateWindowSize: (id, size) => {
    set((state) => ({
      windows: state.windows.map(w => w.id === id ? { ...w, size } : w)
    }))
  },

  // ── Upload bridge ──────────────────────────────────────────
  addUploadedFile: (file) => {
    set((state) => ({
      uploadedFiles: [...state.uploadedFiles, { ...file, addedAt: Date.now() }]
    }))
  },

  clearUploadedFiles: () => {
    set(() => ({ uploadedFiles: [] }))
  }
}))
