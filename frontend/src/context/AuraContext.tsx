import React, { createContext, useContext, useState, ReactNode } from 'react'
import { AuraMessage, AuraState } from '@/types'
import { auraAPI } from '@/services/api'

interface AuraContextType {
  messages: AuraMessage[]
  auraState: AuraState | null
  isLoading: boolean
  error: string | null
  sendMessage: (message: string) => Promise<void>
  getHistory: () => Promise<void>
  getState: () => Promise<void>
  clearError: () => void
}

const AuraContext = createContext<AuraContextType | undefined>(undefined)

export const AuraProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [messages,setMessages] = useState<AuraMessage[]>([])
  const [auraState, setAuraState] = useState<AuraState | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const sendMessage = async (message: string) => {
    setIsLoading(true)
    setError(null)
    try {
      const response = await auraAPI.sendMessage(message)
      setMessages([...messages, response])
    } catch (err: any) {
      setError('Failed to send message')
      console.error('Send message error:', err)
    } finally {
      setIsLoading(false)
    }
  }

  const getHistory = async () => {
    setIsLoading(true)
    try {
      const response = await auraAPI.getConversationHistory()
      setMessages(response.messages || [])
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
