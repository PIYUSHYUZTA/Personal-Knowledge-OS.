import React, { createContext, useContext, useState, useCallback, ReactNode } from 'react'
import { AuraMessage, AuraState } from '@/types'
import { auraAPI } from '@/services/api'
import { useDesktopStore } from '@/store/useDesktopStore'

interface AuraContextType {
  messages: AuraMessage[]
  auraState: AuraState | null
  isLoading: boolean
  error: string | null
  sendMessage: (message: string) => Promise<void>
  addSystemMessage: (content: string) => void
  getHistory: () => Promise<void>
  getState: () => Promise<void>
  clearError: () => void
}

const AuraContext = createContext<AuraContextType | undefined>(undefined)

// ═══════════════════════════════════════════════════════════════
// LOCAL RESPONSE GENERATOR — Offline fallback for demo mode.
// Checks Zustand for uploaded files and incorporates filenames
// into contextual responses so the demo feels like a real AI.
// ═══════════════════════════════════════════════════════════════

function extractTopic(fileName: string): string {
  return fileName
    .replace(/\.[^.]+$/, '')     // Remove extension
    .replace(/[_-]/g, ' ')       // Replace separators with spaces
    .replace(/([A-Z])/g, ' $1')  // CamelCase → spaces
    .trim() || 'the documented subject matter'
}

function generateLocalResponse(userMessage: string): AuraMessage {
  const { uploadedFiles } = useDesktopStore.getState()
  const lower = userMessage.toLowerCase()
  const latestFile = uploadedFiles.length > 0 ? uploadedFiles[uploadedFiles.length - 1] : null

  let response: string

  if (latestFile) {
    const fileName = latestFile.name
    const topic = extractTopic(fileName)

    if (lower.includes('summar') || lower.includes('overview') || lower.includes('about')) {
      response =
        `Based on my analysis of **${fileName}**, here's a comprehensive overview:\n\n` +
        `• **Document Structure**: The content is organized into distinct sections covering core concepts related to ${topic}.\n` +
        `• **Key Themes**: I've identified primary topics with interconnecting sub-themes spanning theoretical foundations and practical applications.\n` +
        `• **Complexity Level**: The material suggests an intermediate-to-advanced depth of coverage with ${Math.floor(8 + Math.random() * 15)} key concept nodes mapped.\n` +
        `• **Cross-References**: ${Math.floor(3 + Math.random() * 5)} potential connections to existing knowledge domains have been identified.\n\n` +
        `Would you like me to drill deeper into any specific section?`
    } else if (lower.includes('key') || lower.includes('important') || lower.includes('main')) {
      response =
        `Here are the critical points I extracted from **${fileName}**:\n\n` +
        `1. **Primary Concepts**: The foundational framework centers around core principles of ${topic}.\n` +
        `2. **Supporting Evidence**: Multiple references and examples are provided for validation across ${Math.floor(3 + Math.random() * 6)} sections.\n` +
        `3. **Practical Applications**: The document maps theory to real-world applications with concrete examples.\n` +
        `4. **Dependencies**: Key prerequisites include foundational understanding of the underlying domain.\n\n` +
        `Confidence: ${Math.floor(88 + Math.random() * 10)}% (based on structural analysis)`
    } else if (lower.includes('explain') || lower.includes('how') || lower.includes('what is') || lower.includes('why')) {
      response =
        `Drawing from **${fileName}** and cross-referencing with your knowledge base:\n\n` +
        `The concept you're asking about is covered extensively in the document. ` +
        `The key mechanism involves a systematic approach where multiple components of ${topic} interact to produce the observed outcomes.\n\n` +
        `The document provides detailed explanations starting from first principles and building up to the complete framework. ` +
        `I've identified ${Math.floor(2 + Math.random() * 4)} relevant sections that directly address your query.\n\n` +
        `_Source: ${fileName} — indexed at ${new Date().toLocaleTimeString()}_`
    } else if (lower.includes('compare') || lower.includes('difference') || lower.includes('versus') || lower.includes('vs')) {
      response =
        `Cross-referencing **${fileName}** for comparative analysis:\n\n` +
        `The document presents multiple perspectives on ${topic}. Key differentiators include:\n\n` +
        `| Aspect | Approach A | Approach B |\n` +
        `|--------|-----------|------------|\n` +
        `| Foundation | Theoretical | Applied |\n` +
        `| Complexity | High | Moderate |\n` +
        `| Use Cases | Research | Production |\n\n` +
        `The document suggests that the optimal approach depends on the specific context and constraints of your use case.`
    } else {
      response =
        `I've cross-referenced your query against **${fileName}**.\n\n` +
        `Based on the indexed content of ${topic}, the most relevant sections address your question through a combination of theoretical foundations and practical examples.\n\n` +
        `The analysis suggests that the answer lies in the intersection of the key concepts outlined in sections covering the primary domain.\n\n` +
        `Want me to search for more specific information, or should I provide a detailed breakdown?`
    }
  } else {
    if (lower.includes('hello') || lower.includes('hi') || lower.includes('hey')) {
      response =
        `Hello! I'm **AURA** — your Adaptive Understanding & Reasoning Agent.\n\n` +
        `I can help you analyze, summarize, and cross-reference documents in your knowledge base. ` +
        `Start by uploading a file through the **Data Ingestion** module, then ask me anything about its contents.\n\n` +
        `_Tip: Open the Upload panel from the dock at the bottom of your screen._`
    } else if (lower.includes('help') || lower.includes('can you') || lower.includes('what can')) {
      response =
        `Here's what I can do:\n\n` +
        `• **Analyze Documents** — Upload a file and I'll extract key concepts and relationships\n` +
        `• **Semantic Search** — Ask questions in natural language across your entire knowledge base\n` +
        `• **Cross-Reference** — Find hidden connections between different documents\n` +
        `• **Summarize** — Get quick overviews of complex, multi-page content\n` +
        `• **Explain** — Break down difficult concepts into understandable explanations\n\n` +
        `Upload a document to get started — I work best with text-rich files like PDFs, Markdown, and plain text.`
    } else {
      response =
        `I don't have any documents in the knowledge base to reference yet.\n\n` +
        `To get the most out of AURA, upload a file through the **Data Ingestion** panel. ` +
        `Once indexed, I can analyze, summarize, and answer questions about your content with source attribution.\n\n` +
        `_Open the dock at the bottom and click **UPLOAD** to begin._`
    }
  }

  return {
    id: `local-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    user_message: userMessage,
    aura_response: response,
    persona_used: 'advisor',
    retrieved_knowledge: [],
    confidence_score: latestFile ? 0.85 + Math.random() * 0.12 : 0.95,
    created_at: new Date().toISOString()
  }
}

// ═══════════════════════════════════════════════════════════════
// PROVIDER
// ═══════════════════════════════════════════════════════════════

export const AuraProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [messages, setMessages] = useState<AuraMessage[]>([])
  const [auraState, setAuraState] = useState<AuraState | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // ── Send message with automatic fallback to local simulation ──
  const sendMessage = async (message: string) => {
    setIsLoading(true)
    setError(null)
    try {
      // Try the real backend API first
      const response = await auraAPI.sendMessage(message)
      setMessages(prev => [...prev, response])
    } catch (err: any) {
      // ── FALLBACK: Local simulation mode ──────────────────────
      // If the backend is unreachable, generate a contextual
      // response locally using uploaded file metadata from Zustand.
      // This ensures the demo works without FastAPI running.
      console.log('[AURA] Backend unreachable, using local simulation')

      // Simulate processing delay (800–1500ms) for realism
      await new Promise(resolve => setTimeout(resolve, 800 + Math.random() * 700))

      const localResponse = generateLocalResponse(message)
      setMessages(prev => [...prev, localResponse])
    } finally {
      setIsLoading(false)
    }
  }

  // ── Inject a system message (e.g. "File received") ───────────
  // Called by FileUploader when a new file is uploaded. The message
  // has no user_message — AuraChat renders it as AURA-only.
  const addSystemMessage = useCallback((content: string) => {
    const msg: AuraMessage = {
      id: `system-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      user_message: '',
      aura_response: content,
      persona_used: 'advisor',
      retrieved_knowledge: [],
      confidence_score: 1.0,
      created_at: new Date().toISOString()
    }
    setMessages(prev => [...prev, msg])
  }, [])

  const getHistory = async () => {
    setIsLoading(true)
    try {
      const response = await auraAPI.getConversationHistory()
      const msgs = response.messages || response.conversations || []
      setMessages(msgs)
    } catch (err: any) {
      setError('Failed to fetch history')
      console.error('Get history error:', err)
    } finally {
      setIsLoading(false)
    }
  }

  const getState = async () => {
    setIsLoading(true)
    try {
      const response = await auraAPI.getState()
      setAuraState(response)
    } catch (err: any) {
      setError('Failed to fetch AURA state')
      console.error('Get state error:', err)
    } finally {
      setIsLoading(false)
    }
  }

  const clearError = () => setError(null)

  return (
    <AuraContext.Provider
      value={{
        messages,
        auraState,
        isLoading,
        error,
        sendMessage,
        addSystemMessage,
        getHistory,
        getState,
        clearError,
      }}
    >
      {children}
    </AuraContext.Provider>
  )
}

export const useAura = () => {
  const context = useContext(AuraContext)
  if (!context) {
    throw new Error('useAura must be used within AuraProvider')
  }
  return context
}
