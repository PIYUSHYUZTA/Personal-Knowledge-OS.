import React, { useRef, useEffect } from 'react'
import { useAura } from '@/context/AuraContext'
import { Send, Sparkles, User, RefreshCw } from 'lucide-react'

export default function AuraChat() {
  const { messages, sendMessage, isLoading, auraState } = useAura()
  const [input, setInput] = React.useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSend = async () => {
    if (!input.trim() || isLoading) return
    const currentInput = input
    setInput('')
    await sendMessage(currentInput)
  }

  return (
    <div className="flex flex-col h-full bg-surface/30 backdrop-blur-xl">
      {/* Chat Messages */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center max-w-sm mx-auto animate-in fade-in zoom-in-95 duration-500">
            <div className="w-16 h-16 rounded-full bg-brand/10 text-brand flex items-center justify-center mb-6 ring-8 ring-brand/5">
              <Sparkles size={32} />
            </div>
            <h3 className="text-xl font-semibold text-primary mb-2">How can I help you?</h3>
            <p className="text-sm text-muted mb-6">
              I'm AURA, your personal AI. I have access to your full knowledge base.
            </p>
            <div className="px-4 py-2 border border-brand/20 bg-brand/5 text-brand rounded-full text-xs font-medium flex items-center gap-2">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-brand opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-brand"></span>
              </span>
              Mode: {auraState?.current_persona || 'Advisor'}
            </div>
          </div>
        ) : (
          messages.map((msg, idx) => (
            <div key={idx} className="space-y-6 animate-in fade-in slide-in-from-bottom-2">
              {/* User Message */}
              <div className="flex items-start gap-4 justify-end">
                <div className="bg-primary text-background rounded-2xl rounded-tr-sm px-5 py-3.5 max-w-[80%] shadow-sm">
                  <p className="text-sm leading-relaxed whitespace-pre-wrap">{msg.user_message}</p>
                </div>
                <div className="w-8 h-8 rounded-full bg-subtle text-muted flex items-center justify-center shrink-0">
                  <User size={16} />
                </div>
              </div>

              {/* AURA Response */}
              <div className="flex items-start gap-4">
                <div className="w-8 h-8 rounded-full bg-brand text-white flex items-center justify-center shrink-0 shadow-glow">
                  <Sparkles size={16} />
                </div>
                <div className="bg-surface border border-border/50 rounded-2xl rounded-tl-sm px-5 py-3.5 max-w-[80%] shadow-sm">
                  <p className="text-sm text-primary leading-relaxed whitespace-pre-wrap">{msg.aura_response}</p>
                  <div className="mt-3 flex items-center gap-2">
                    <span className="text-[10px] font-semibold text-muted uppercase tracking-wide bg-subtle px-2 py-0.5 rounded-full">
                      {msg.persona_used}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          ))
        )}
        {isLoading && (
          <div className="flex items-start gap-4 animate-in fade-in">
            <div className="w-8 h-8 rounded-full bg-brand/50 text-white flex items-center justify-center shrink-0 animate-pulse">
              <Sparkles size={16} />
            </div>
            <div className="bg-surface border border-border/50 rounded-2xl rounded-tl-sm px-5 py-4 max-w-[80%] shadow-sm flex gap-1">
              <div className="w-1.5 h-1.5 bg-brand rounded-full animate-bounce" style={{ animationDelay: '-0.3s' }}></div>
              <div className="w-1.5 h-1.5 bg-brand rounded-full animate-bounce" style={{ animationDelay: '-0.15s' }}></div>
              <div className="w-1.5 h-1.5 bg-brand rounded-full animate-bounce"></div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="p-4 bg-surface/50 border-t border-border/50 backdrop-blur-md">
        <div className="max-w-4xl mx-auto relative flex items-center">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSend()}
            placeholder="Ask AURA to query your knowledge..."
            className="w-full pl-5 pr-14 py-4 bg-background border border-border focus:border-brand rounded-2xl text-sm text-primary placeholder:text-muted focus:ring-4 focus:ring-brand/10 transition-all outline-none shadow-sm"
            disabled={isLoading}
          />
          <button
            onClick={handleSend}
            disabled={isLoading || !input.trim()}
            className="absolute right-2 p-2.5 bg-brand text-white rounded-xl hover:bg-brand/90 transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-glow"
          >
            {isLoading ? <RefreshCw size={18} className="animate-spin" /> : <Send size={18} />}
          </button>
        </div>
        <p className="text-center text-xs text-muted mt-3">
          AURA uses semantic search to answer based on your uploaded documents.
        </p>
      </div>
    </div>
  )
}
