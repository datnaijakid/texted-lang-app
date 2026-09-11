import { useEffect, useRef, useState } from 'react'
import { api } from '../api'
import { Button } from '../components/ui'

export default function ConversationStage({ lessonId, scenarioTitle, onComplete }) {
  const [messages, setMessages] = useState([])
  const [conversationId, setConversationId] = useState(null)
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [aiTyping, setAiTyping] = useState(false)
  const [xpToast, setXpToast] = useState(null)
  const bottomRef = useRef(null)

  useEffect(() => {
    api.startConversation(lessonId).then((res) => {
      setConversationId(res.conversation_id)
      setMessages([{ sender: 'ai', content: res.opening_message }])
    })
  }, [lessonId])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, aiTyping])

  async function submit(e) {
    e.preventDefault()
    if (!input.trim() || sending || !conversationId) return
    const text = input
    setInput('')
    setMessages((m) => [...m, { sender: 'user', content: text }])
    setSending(true)
    setAiTyping(true)
    try {
      const res = await api.sendMessage(conversationId, text)
      setMessages((m) => [...m, { sender: 'ai', content: res.ai_message }])
      setXpToast(`+${res.xp_awarded} XP`)
      setTimeout(() => setXpToast(null), 1800)
      if (res.conversation_complete) {
        setTimeout(() => onComplete(), 1400)
      }
    } finally {
      setSending(false)
      setAiTyping(false)
    }
  }

  return (
    <div className="max-w-md mx-auto px-4 pt-6 pb-4 h-screen flex flex-col">
      {/* phone-style chat frame */}
      <div className="flex items-center gap-3 pb-3 border-b border-base-700 mb-3">
        <div className="w-9 h-9 rounded-full bg-gradient-to-br from-accent to-base-soft flex items-center justify-center font-bold text-base-950">
          C
        </div>
        <div>
          <div className="font-semibold text-white text-sm">Camille</div>
          <div className="text-base-600 text-xs">{scenarioTitle}</div>
        </div>
        {xpToast && (
          <div className="ml-auto text-accent text-xs font-bold bg-base-800 px-2 py-1 rounded-full animate-pop-in">
            {xpToast}
          </div>
        )}
      </div>

      <div className="flex-1 overflow-y-auto scrollbar-thin space-y-2 pb-3">
        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div
              className={`max-w-[75%] px-4 py-2.5 rounded-2xl text-sm animate-pop-in ${
                m.sender === 'user'
                  ? 'bg-bubble-me text-white rounded-br-sm'
                  : 'bg-bubble-them text-white rounded-bl-sm'
              }`}
            >
              {m.content}
            </div>
          </div>
        ))}
        {aiTyping && (
          <div className="flex justify-start">
            <div className="bg-bubble-them px-4 py-2.5 rounded-2xl rounded-bl-sm text-base-600 text-sm">
              <span className="inline-flex gap-1">
                <span className="animate-bounce">•</span>
                <span className="animate-bounce [animation-delay:0.1s]">•</span>
                <span className="animate-bounce [animation-delay:0.2s]">•</span>
              </span>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <form onSubmit={submit} className="flex gap-2 pt-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type a message…"
          disabled={sending}
          className="flex-1 bg-base-800 border border-base-700 rounded-full px-4 py-2.5 text-white placeholder-base-600 outline-none focus:border-accent transition-colors text-sm"
        />
        <Button type="submit" disabled={sending || !input.trim()} className="!px-4">
          →
        </Button>
      </form>
    </div>
  )
}
