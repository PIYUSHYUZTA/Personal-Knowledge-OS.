import React, { useEffect, useRef, useState, useCallback } from 'react'
import { useAuth } from '@/context/AuthContext'
import { Send, Sparkles, User, AlertTriangle, BookOpen, CheckCircle2 } from 'lucide-react'
import Badge from '@/components/ui/Badge'

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
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout>>()

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
          <div key={msg.id} className="mb-4 flex justify-end">
            <div className="flex items-start gap-3">
              <div className="bg-secondary text-white rounded-2xl rounded-tr-sm px-4 py-2.5 max-w-xs shadow-sm shadow-secondary/10">
                <p className="text-sm leading-relaxed">{msg.content}</p>
              </div>
              <div className="w-8 h-8 rounded-full border border-border bg-surface text-text-muted flex items-center justify-center shrink-0">
                <User size={14} />
              </div>
            </div>
          </div>
        )

      case 'assistant':
        return (
          <div key={msg.id} className="mb-4 flex justify-start">
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 rounded-lg bg-secondary text-white flex items-center justify-center shrink-0 shadow-glow-sm">
                <Sparkles size={14} />
              </div>
              <div className="bg-surface/80 backdrop-blur-sm border border-border/80 rounded-2xl rounded-tl-sm px-4 py-2.5 max-w-2xl shadow-sm">
                <div className="text-sm text-text-body whitespace-pre-wrap leading-relaxed">{msg.content}</div>
              </div>
            </div>
          </div>
        )

      case 'status':
        return (
          <div key={msg.id} className="mb-3 text-center">
            <span className="inline-flex items-center gap-2 text-xs text-text-muted bg-surface/60 border border-border/40 px-3 py-1.5 rounded-full">
              {msg.content}
              {msg.confidence && (
                <Badge variant="success" size="sm">
                  <CheckCircle2 size={10} className="mr-0.5" />
                  {(msg.confidence * 100).toFixed(0)}%
                </Badge>
              )}
            </span>
          </div>
        )

      case 'sources':
        return (
          <div key={msg.id} className="mb-4">
            <div className="bg-warning/5 border border-warning/20 rounded-xl p-4">
              <div className="flex items-center gap-2 mb-3">
                <BookOpen size={14} className="text-warning" />
                <h4 className="text-xs font-semibold text-primary uppercase tracking-wider">
                  Sources ({msg.sources?.length || 0})
                </h4>
              </div>
              <div className="space-y-1.5">
                {msg.sources?.map((source, i) => (
                  <div key={i} className="flex items-center justify-between text-xs">
                    <span className="font-medium text-text-body truncate mr-3">{source.file_name}</span>
                    <Badge variant="outline" size="sm">
                      {(source.similarity * 100).toFixed(0)}%
                    </Badge>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )

      case 'error':
        return (
          <div key={msg.id} className="mb-4">
            <div className="bg-error/5 border border-error/20 rounded-xl p-3 flex items-start gap-2">
              <AlertTriangle size={14} className="text-error shrink-0 mt-0.5" />
              <p className="text-sm text-error">{msg.content}</p>
            </div>
          </div>
        )

      default:
        return null
    }
  }

  return (
    <div className="flex flex-col h-full bg-background">
      {/* Header */}
      <div className="bg-surface border-b border-border px-5 py-3.5">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-base font-semibold text-primary tracking-tight">Technical Reasoning Engine</h2>
            <p className="text-[11px] text-text-muted mt-0.5">Real-time streaming analysis</p>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant={isConnected ? 'success' : 'error'} dot size="sm">
              {isConnected ? 'Connected' : 'Disconnected'}
            </Badge>
          </div>
        </div>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-5 space-y-2">
        {messages.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center max-w-sm">
              <div className="w-14 h-14 rounded-2xl bg-secondary/10 text-secondary flex items-center justify-center mx-auto mb-5 border border-secondary/20">
                <Sparkles size={24} />
              </div>
              <h3 className="text-base font-semibold text-primary mb-2 tracking-tight">Welcome to AURA</h3>
              <p className="text-sm text-text-muted leading-relaxed">Ask any technical question about your knowledge base</p>
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
      <div className="border-t border-border bg-surface p-4">
        <div className="flex gap-2">
          <input
            id="chatstream-input"
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSendMessage()}
            placeholder="Ask a technical question..."
            disabled={!isConnected || isLoading}
            className="flex-1 px-4 py-2.5 bg-background border border-border rounded-xl text-sm text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-secondary/20 focus:border-secondary disabled:opacity-50 disabled:cursor-not-allowed transition-all"
          />
          <button
            id="chatstream-send"
            onClick={handleSendMessage}
            disabled={!isConnected || isLoading || !inputValue.trim()}
            className="px-5 py-2.5 bg-secondary hover:bg-secondary/90 text-white text-sm font-medium rounded-xl disabled:opacity-50 disabled:cursor-not-allowed transition-all active:scale-[0.97] shadow-sm shadow-secondary/20 cursor-pointer"
          >
            {isLoading ? (
              <span className="flex items-center gap-2">
                <div className="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Thinking
              </span>
            ) : (
              <span className="flex items-center gap-2">
                <Send size={14} />
                Send
              </span>
            )}
          </button>
        </div>

        {!isConnected && (
          <div className="flex items-center gap-2 mt-2 text-xs text-error">
            <AlertTriangle size={12} />
            Connection lost. Reconnecting...
          </div>
        )}
      </div>
    </div>
  )
}

export default ChatStream
