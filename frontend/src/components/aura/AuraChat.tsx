import React, { useRef, useEffect } from 'react'
import { useAura } from '@/context/AuraContext'
import { Send, Sparkles, User, RefreshCw } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import Badge from '@/components/ui/Badge'

export default function AuraChat() {
  const { messages, sendMessage, isLoading, auraState } = useAura()
  const [input, setInput] = React.useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages, isLoading])

  const handleSend = async () => {
    if (!input.trim() || isLoading) return
    const currentInput = input
    setInput('')
    await sendMessage(currentInput)
  }

  return (
    <div className="flex flex-col h-full bg-transparent relative z-10 w-full">
      {/* Chat Messages Area */}
      <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-6">
        <AnimatePresence>
          {messages.length === 0 ? (
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.9 }}
              className="h-full flex flex-col items-center justify-center text-center max-w-sm mx-auto"
            >
              <div className="w-14 h-14 rounded-2xl bg-[#FF5722]/10 text-[#FF5722] flex items-center justify-center mb-6 border border-[#FF5722]/20 animate-pulse-glow">
                <Sparkles size={28} />
              </div>
              <h3 className="text-lg font-semibold text-[#ECECEF] mb-2 tracking-tight">How can I help you today?</h3>
              <p className="text-sm text-[#A1A1AA] mb-6 leading-relaxed">
                I'm AURA, your personal AI. Ask me to query, summarize, or cross-reference any data in your knowledge base.
              </p>
              <Badge variant="default" dot>
                Mode: {auraState?.current_persona || 'Advisor'}
              </Badge>
            </motion.div>
          ) : (
            messages.map((msg, idx) => (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: idx * 0.03 }}
                key={msg.id || idx}
                className="space-y-4"
              >
                {/* ── User Message (skip for system messages where user_message is empty) ── */}
                {msg.user_message && (
                  <div className="flex items-start gap-3 justify-end">
                    <div className="bg-[#FF5722] text-white rounded-2xl rounded-tr-sm px-4 py-3 max-w-[85%] shadow-sm shadow-[#FF5722]/10">
                      <p className="text-sm leading-relaxed whitespace-pre-wrap">{msg.user_message}</p>
                    </div>
                    <div className="w-8 h-8 rounded-full border border-[#27272A] bg-[#1A1B22] text-[#A1A1AA] flex items-center justify-center shrink-0 shadow-sm">
                      <User size={14} />
                    </div>
                  </div>
                )}

                {/* ── AURA Response ── */}
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 rounded-lg bg-[#FF5722] text-white flex items-center justify-center shrink-0 shadow-[0_0_10px_rgba(255,87,34,0.3)]">
                    <Sparkles size={14} />
                  </div>
                  <div className="bg-[#1A1B22]/80 backdrop-blur-sm border border-[#27272A]/80 rounded-2xl rounded-tl-sm px-4 py-3 max-w-[85%] shadow-sm">
                    <p className="text-sm text-[#ECECEF] leading-relaxed whitespace-pre-wrap">{msg.aura_response}</p>
                    {msg.user_message && (
                      <div className="mt-3 flex items-center gap-2">
                        <Badge variant="outline" size="sm">
                          {msg.persona_used}
                        </Badge>
                        {msg.confidence_score > 0 && msg.confidence_score < 1 && (
                          <span className="text-[10px] font-mono text-[#52525B]">
                            {Math.round(msg.confidence_score * 100)}% confidence
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              </motion.div>
            ))
          )}

          {isLoading && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex items-start gap-3"
            >
              <div className="w-8 h-8 rounded-lg bg-[#FF5722]/50 text-white flex items-center justify-center shrink-0 animate-pulse">
                <Sparkles size={14} />
              </div>
              <div className="bg-[#1A1B22]/80 border border-[#27272A]/50 rounded-2xl rounded-tl-sm px-4 py-3.5 shadow-sm flex gap-1.5 items-center justify-center">
                <div className="w-1.5 h-1.5 bg-[#FF5722] rounded-full animate-bounce" style={{ animationDelay: '-0.3s' }} />
                <div className="w-1.5 h-1.5 bg-[#FF5722] rounded-full animate-bounce" style={{ animationDelay: '-0.15s' }} />
                <div className="w-1.5 h-1.5 bg-[#FF5722] rounded-full animate-bounce" />
              </div>
            </motion.div>
          )}
        </AnimatePresence>
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="p-4 bg-[#0B0F19]/80 border-t border-[#27272A]/50 backdrop-blur-xl">
        <div className="max-w-3xl mx-auto relative flex items-center group">
          <input
            id="aura-chat-input"
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            placeholder="Ask AURA to query your knowledge..."
            className="w-full pl-4 pr-12 py-3 bg-[#1A1B22] border border-[#27272A] focus:border-[#FF5722]/50 hover:border-[#27272A]/80 rounded-xl text-sm text-[#ECECEF] placeholder:text-[#52525B] focus:ring-4 focus:ring-[#FF5722]/10 transition-all outline-none shadow-sm cursor-text font-mono"
            disabled={isLoading}
          />
          <button
            id="aura-chat-send"
            onClick={handleSend}
            disabled={isLoading || !input.trim()}
            className="absolute right-1.5 p-2 bg-[#FF5722] text-white rounded-lg hover:bg-[#E64A19] hover:scale-105 active:scale-95 transition-all disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100 shadow-sm cursor-pointer"
          >
            {isLoading ? <RefreshCw size={16} className="animate-spin" /> : <Send size={16} />}
          </button>
        </div>
        <p className="text-center text-[10px] text-[#52525B] mt-2 uppercase tracking-wide font-medium font-mono">
          AURA Semantic Search Engine
        </p>
      </div>
    </div>
  )
}
