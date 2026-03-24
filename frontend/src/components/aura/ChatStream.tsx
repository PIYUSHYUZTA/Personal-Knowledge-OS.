import React, { useEffect, useRef, useState, useCallback } from 'react'
import { useAuth } from '@/context/AuthContext'

interface Message {
  id: string
  type: 'user' | 'assistant' | 'status' | 'sources' | 'error'
  content: string
  timestamp: Date
  sources?: Array<{ file_name: string; chunk_text: string; similarity: number }>
  confidence?: number
}

interface ChatStreamProps {
  token?: string
}

/**
 * Real-Time Chat Component with WebSocket Streaming
 *
 * Features:
 * - Token-by-token streaming of responses
 * - Auto-scroll to latest message
 * - Source attribution
 * - Connection status indicator
 * - Graceful reconnection
 */
const ChatStream: React.FC<ChatStreamProps> = ({ token }) => {
  useAuth()
  const [messages, setMessages] = useState<Message[]>([])
  const [inputValue, setInputValue] = useState('')
  const [isConnected, setIsConnected] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>()

  const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
  const WS_URL = API_URL.replace('http', 'ws')

  // Auto-scroll to latest message
  const scrollToBottom = useCallback(() => {
    setTimeout(() => {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }, 100)
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [messages, scrollToBottom])

  // Connect to WebSocket
  useEffect(() => {
    if (!token) return

    const connectWebSocket = () => {
      try {
        const ws = new WebSocket(`${WS_URL}/api/v1/stream/query?token=${token}`)

        ws.onopen = () => {
          console.log('WebSocket connected')
          setIsConnected(true)

          // Clear reconnect timeout
          if (reconnectTimeoutRef.current) {
            clearTimeout(reconnectTimeoutRef.current)
          }
        }

        ws.onmessage = (event) => {
          const data = JSON.parse(event.data)
          handleStreamMessage(data)
        }

        ws.onerror = (error) => {
          console.error('WebSocket error:', error)
          setIsConnected(false)
        }

        ws.onclose = () => {
          setIsConnected(false)

          // Attempt reconnection
          reconnectTimeoutRef.current = setTimeout(() => {
            console.log('Attempting WebSocket reconnection...')
            connectWebSocket()
          }, 3000)
        }

        wsRef.current = ws
      } catch (error) {
        console.error('Failed to connect WebSocket:', error)
        setIsConnected(false)
      }
    }

    connectWebSocket()

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
      if (wsRef.current) {
        wsRef.current.close()
      }
    }
  }, [token, WS_URL])

  // Handle streaming message
  const handleStreamMessage = (data: any) => {
    switch (data.type) {
      case 'status':
        addMessage({
          id: `status-${Date.now()}`,
          type: 'status',
          content: data.content,
          timestamp: new Date(),
        })
        break

      case 'token':
        // Append token to last assistant message
        setMessages((prev) => {
          const lastMsg = prev[prev.length - 1]
          if (lastMsg && lastMsg.type === 'assistant') {
            return [
              ...prev.slice(0, -1),
              { ...lastMsg, content: lastMsg.content + data.content },
            ]
          }
          return prev
        })
        scrollToBottom()
        break

      case 'sources':
        addMessage({
          id: `sources-${Date.now()}`,
          type: 'sources',
          content: `Retrieved ${data.content.length} sources`,
          timestamp: new Date(),
          sources: data.content,
        })
        break

      case 'complete':
        setIsLoading(false)
        setMessages((prev) => [
          ...prev,
          {
            id: `metadata-${Date.now()}`,
            type: 'status',
            content: `Response complete. Confidence: ${(data.confidence * 100).toFixed(0)}%`,
            timestamp: new Date(),
            confidence: data.confidence,
          },
        ])
        break

      case 'error':
        addMessage({
          id: `error-${Date.now()}`,
          type: 'error',
          content: data.content,
          timestamp: new Date(),
        })
        setIsLoading(false)
        break

      case 'response_start':
        // Create new assistant message for streaming
        addMessage({
          id: `assistant-${Date.now()}`,
          type: 'assistant',
          content: '',
          timestamp: new Date(),
        })
        break
    }
  }

  // Add message to chat
  const addMessage = (message: Message) => {
    setMessages((prev) => [...prev, message])
  }

  // Send query
  const handleSendMessage = useCallback(() => {
    if (!inputValue.trim() || !wsRef.current || !isConnected || isLoading) {
      return
    }

    // Add user message
    addMessage({
      id: `user-${Date.now()}`,
      type: 'user',
      content: inputValue,
      timestamp: new Date(),
    })

    // Send through WebSocket
    wsRef.current.send(
      JSON.stringify({
        message: inputValue,
        type: 'query',
      })
    )

    setInputValue('')
    setIsLoading(true)
    scrollToBottom()
  }, [inputValue, isConnected, isLoading, scrollToBottom])

  // Render individual message based on type
  const renderMessage = (msg: Message) => {
    switch (msg.type) {
      case 'user':
        return (
          <div key={msg.id} className="message message-user mb-4 flex justify-end">
            <div className="bg-blue-600 text-white rounded-lg px-4 py-2 max-w-xs">
              {msg.content}
            </div>
          </div>
        )

      case 'assistant':
        return (
          <div key={msg.id} className="message message-assistant mb-4 flex justify-start">
            <div className="bg-slate-200 dark:bg-slate-700 text-slate-900 dark:text-slate-50 rounded-lg px-4 py-2 max-w-2xl">
              <div className="text-sm whitespace-pre-wrap">{msg.content}</div>
            </div>
          </div>
        )

      case 'status':
        return (
          <div
            key={msg.id}
            className="message message-status mb-2 text-center text-sm text-slate-500"
          >
            {msg.content}
            {msg.confidence && (
              <span className="ml-2 text-green-600">
                ✓ {(msg.confidence * 100).toFixed(0)}%
              </span>
            )}
          </div>
        )

      case 'sources':
        return (
          <div key={msg.id} className="message message-sources mb-4 text-sm">
            <div className="bg-amber-50 dark:bg-amber-900 border-l-4 border-amber-400 p-3 rounded">
              <h4 className="font-semibold text-amber-900 dark:text-amber-100 mb-2">
                Sources ({msg.sources?.length || 0})
              </h4>
              <div className="space-y-1">
                {msg.sources?.map((source, i) => (
                  <div key={i} className="text-xs text-amber-800 dark:text-amber-100">
                    <strong>{source.file_name}</strong> ({(source.similarity * 100).toFixed(0)}%)
                  </div>
                ))}
              </div>
            </div>
          </div>
        )

      case 'error':
        return (
          <div key={msg.id} className="message message-error mb-4">
            <div className="bg-red-50 dark:bg-red-900 border-l-4 border-red-400 p-3 rounded text-red-800 dark:text-red-100 text-sm">
              ⚠️ {msg.content}
            </div>
          </div>
        )

      default:
        return null
    }
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="bg-slate-100 dark:bg-slate-900 border-b p-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold">Technical Reasoning Engine</h2>
          <div
            className={`w-3 h-3 rounded-full ${
              isConnected ? 'bg-green-500' : 'bg-red-500'
            }`}
            title={isConnected ? 'Connected' : 'Disconnected'}
          />
        </div>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-2">
        {messages.length === 0 ? (
          <div className="flex items-center justify-center h-full text-slate-500">
            <div className="text-center">
              <h3 className="text-lg font-semibold mb-2">Welcome to AURA</h3>
              <p>Ask any technical question about your knowledge base</p>
            </div>
          </div>
        ) : (
          <>
            {messages.map((msg) => renderMessage(msg))}
            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* Input Area */}
      <div className="border-t bg-slate-50 dark:bg-slate-900 p-4">
        <div className="flex gap-2">
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSendMessage()}
            placeholder="Ask a technical question..."
            disabled={!isConnected || isLoading}
            className="flex-1 px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
          />
          <button
            onClick={handleSendMessage}
            disabled={!isConnected || isLoading || !inputValue.trim()}
            className="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isLoading ? 'Thinking...' : 'Send'}
          </button>
        </div>

        {!isConnected && (
          <div className="text-sm text-red-600 mt-2">
            ⚠️ Connection lost. Reconnecting...
          </div>
        )}
      </div>
    </div>
  )
}

export default ChatStream
