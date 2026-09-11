import { useEffect, useRef, useState } from 'react'
import { api } from '../api'
import ProfileDrawer from '../components/ProfileDrawer'
import UpgradeModal from '../components/UpgradeModal'
import QuickTranslator from '../components/QuickTranslator'

const PERSONA_STYLES = {
  Sofia: { gradient: 'from-rose-500 to-amber-500', flag: '🇪🇸', letter: 'S' },
  Camille: { gradient: 'from-emerald-500 to-teal-500', flag: '🇫🇷', letter: 'C' },
  Marco: { gradient: 'from-amber-500 to-orange-500', flag: '🇮🇹', letter: 'M' },
  Lukas: { gradient: 'from-blue-500 to-cyan-500', flag: '🇩🇪', letter: 'L' },
  Kenji: { gradient: 'from-purple-500 to-pink-500', flag: '🇯🇵', letter: 'K' },
  Emma: { gradient: 'from-indigo-500 to-purple-500', flag: '🇬🇧', letter: 'E' },
}

const COMMON_EMOJIS = ['😂', '😭', '☕', '🙌', '🍕', '✨', '👍', '❤️', '🌮', '🔥']

export default function DirectMessageScreen({ user, onUserUpdated, onLogout }) {
  const [conversation, setConversation] = useState(null)
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [aiTyping, setAiTyping] = useState(false)
  const [expandedCorrectionId, setExpandedCorrectionId] = useState(null)
  const [showEmojiPicker, setShowEmojiPicker] = useState(false)
  const [translations, setTranslations] = useState({})
  const [suggestedReplies, setSuggestedReplies] = useState([])

  // Translator & Word/Sentence Selection State
  const [isTranslatorOpen, setIsTranslatorOpen] = useState(false)
  const [translatorInitialText, setTranslatorInitialText] = useState('')
  const [selectionPopup, setSelectionPopup] = useState(null)
  const selectionPopupRef = useRef(null)

  // Modals & Drawers
  const [isDrawerOpen, setIsDrawerOpen] = useState(false)
  const [isUpgradeOpen, setIsUpgradeOpen] = useState(false)
  const [usage, setUsage] = useState({
    tier: user?.subscription_tier || 'free',
    is_pro: (user?.subscription_tier || 'free') === 'pro',
    messages_today: user?.daily_messages_count || 0,
    daily_limit: 20,
    messages_remaining: 20,
    can_send: true,
  })

  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)

  const isPro = (user?.subscription_tier || 'free').toLowerCase() === 'pro'
  const partnerName = conversation?.persona_name || 'Sofia'
  const partnerStyle = PERSONA_STYLES[partnerName] || PERSONA_STYLES['Sofia']

  async function toggleTranslation(msgId, content, forceVisible = false) {
    const existing = translations[msgId]
    if (existing?.text) {
      setTranslations((prev) => ({
        ...prev,
        [msgId]: {
          ...prev[msgId],
          visible: forceVisible ? true : !prev[msgId].visible,
        },
      }))
      return
    }

    setTranslations((prev) => ({
      ...prev,
      [msgId]: { loading: true, visible: true, text: '' },
    }))

    try {
      const res = await api.translateMessage(content, user?.native_language_code || 'en')
      setTranslations((prev) => ({
        ...prev,
        [msgId]: {
          loading: false,
          visible: true,
          text: res.translated_text,
          targetName: res.target_language_name,
        },
      }))
    } catch (err) {
      console.error('Translation failed:', err)
      setTranslations((prev) => ({
        ...prev,
        [msgId]: {
          loading: false,
          visible: true,
          text: 'Translation unavailable.',
          targetName: '',
        },
      }))
    }
  }

  // Auto-translate if user setting is enabled
  useEffect(() => {
    if (user?.auto_translate && messages.length > 0) {
      messages.forEach((m) => {
        if (m.sender === 'ai' && !translations[m.id]?.text) {
          toggleTranslation(m.id, m.content, true)
        }
      })
    }
  }, [user?.auto_translate, messages])

  // Load conversation & usage on mount and whenever learning language or level changes
  useEffect(() => {
    loadConversation()
    loadUsage()
  }, [user?.learning_language_code, user?.proficiency_level])

  function loadConversation() {
    api.getActiveConversation()
      .then((data) => {
        setConversation(data)
        setMessages(data.messages || [])
        if (data.suggested_replies && data.suggested_replies.length > 0) {
          setSuggestedReplies(data.suggested_replies)
        }
      })
      .catch((err) => console.error('Failed to load conversation:', err))
  }

  function loadUsage() {
    api.getUsage()
      .then(setUsage)
      .catch((err) => console.error('Failed to load usage:', err))
  }

  // Smooth auto-scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, aiTyping])

  // Text selection handler for translating individual words or highlighted sentences
  function handleTextSelect() {
    const sel = window.getSelection()
    if (!sel || sel.isCollapsed) return

    const text = sel.toString().trim()
    if (text.length > 0 && text.length <= 350) {
      try {
        const range = sel.getRangeAt(0)
        const rect = range.getBoundingClientRect()
        const popupX = Math.min(Math.max(rect.left + rect.width / 2, 140), window.innerWidth - 140)
        const popupY = Math.max(rect.top - 8, 45)

        setSelectionPopup({
          text,
          x: popupX,
          y: popupY,
          translation: null,
          loading: false,
          saved: false,
        })
      } catch (_) {}
    }
  }

  async function handleTranslateSelection() {
    if (!selectionPopup?.text) return
    setSelectionPopup((prev) => ({ ...prev, loading: true }))
    try {
      const res = await api.translateMessage(selectionPopup.text, user?.native_language_code || 'en')
      setSelectionPopup((prev) => ({
        ...prev,
        loading: false,
        translation: res.translated_text,
        targetName: res.target_language_name,
      }))
    } catch (err) {
      setSelectionPopup((prev) => ({
        ...prev,
        loading: false,
        translation: 'Translation unavailable',
      }))
    }
  }

  async function handleSaveSelectionToVocab() {
    if (!selectionPopup?.text || !selectionPopup?.translation) return
    try {
      await api.saveCustomWord(selectionPopup.text, selectionPopup.translation, langCode)
      setSelectionPopup((prev) => ({ ...prev, saved: true }))
      setTimeout(() => {
        setSelectionPopup((prev) => (prev ? { ...prev, saved: false } : null))
      }, 2500)
    } catch (err) {
      alert('Could not save to notebook: ' + err.message)
    }
  }

  // Dismiss selection popup when clicking outside
  useEffect(() => {
    function handleClickOutside(e) {
      if (selectionPopupRef.current && !selectionPopupRef.current.contains(e.target)) {
        const sel = window.getSelection()
        if (!sel || sel.isCollapsed) {
          setSelectionPopup(null)
        }
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  async function handleSendMessage(textToSend) {
    const content = (textToSend || input).trim()
    if (!content || sending || !conversation) return

    // Free limit check client-side
    if (!isPro && usage.messages_remaining <= 0) {
      setIsUpgradeOpen(true)
      api.trackEvent('hit_limit', { source: 'client_gate' })
      return
    }

    setInput('')
    setShowEmojiPicker(false)

    // Optimistic user message
    const tempUserId = 'temp_' + Date.now()
    const optimisticMsg = {
      id: tempUserId,
      sender: 'user',
      content,
      created_at: new Date().toISOString(),
      feedback: null,
    }
    setMessages((prev) => [...prev, optimisticMsg])
    setSending(true)
    setAiTyping(true)

    try {
      const res = await api.sendChatMessage(conversation.conversation_id, content)

      // Replace user message with backend version if it has feedback/correction
      setMessages((prev) =>
        prev.map((m) =>
          m.id === tempUserId
            ? {
                ...m,
                id: res.user_message_id,
                feedback: res.correction ? JSON.stringify(res.correction) : null,
              }
            : m
        )
      )

      // Append AI reply
      const aiMsg = {
        id: res.ai_message_id,
        sender: 'ai',
        content: res.ai_message,
        created_at: new Date().toISOString(),
        feedback: null,
      }
      setMessages((prev) => [...prev, aiMsg])

      // Dynamically update 1-tap reply chips with options relevant to what the AI just said
      if (res.suggested_replies && res.suggested_replies.length > 0) {
        setSuggestedReplies(res.suggested_replies)
      }

      // Update usage state
      setUsage((prev) => ({
        ...prev,
        messages_today: prev.messages_today + 1,
        messages_remaining: res.messages_remaining,
        can_send: res.can_send,
        tier: res.subscription_tier,
      }))
    } catch (err) {
      if (err.status === 429) {
        setIsUpgradeOpen(true)
      } else {
        alert(err.message || 'Could not send message. Please try again.')
      }
    } finally {
      setSending(false)
      setAiTyping(false)
      inputRef.current?.focus()
    }
  }

  async function handleResetConversation() {
    if (!window.confirm(`Start a fresh chat topic with ${partnerName}?`)) return
    try {
      const fresh = await api.resetConversation()
      setConversation(fresh)
      setMessages(fresh.messages || [])
      if (fresh.suggested_replies && fresh.suggested_replies.length > 0) {
        setSuggestedReplies(fresh.suggested_replies)
      }
    } catch (err) {
      alert(err.message || 'Failed to reset conversation')
    }
  }

  function handleLanguageChange(newLang) {
    loadConversation()
  }

  function handleAddEmoji(emoji) {
    setInput((prev) => prev + emoji)
    inputRef.current?.focus()
  }

  const langCode = conversation?.language_code || user?.learning_language_code || 'es'
  const isStarter = (user?.proficiency_level || 'starter').toLowerCase() === 'starter'

  const starterChipsByLang = {
    es: isStarter
      ? [
          { label: 'Say your name 👋', text: '¡Hola! Me llamo Alex.' },
          { label: 'Say you are well 😊', text: '¡Muy bien, gracias! ¿Y tú?' },
          { label: 'Ask how they are', text: '¿Cómo estás hoy?' },
          { label: 'Yes, coffee! ☕', text: 'Sí, me gusta el café.' },
        ]
      : [
          { label: 'Say hello & how you are 👋', text: '¡Hola! ¿Cómo estás hoy?' },
          { label: 'Talk about coffee ☕', text: 'Hoy me tomé un café delicioso. ¿Te gusta el café?' },
          { label: 'Ask about music 🎵', text: '¿Qué música estás escuchando últimamente?' },
        ],
    fr: isStarter
      ? [
          { label: 'Say your name 👋', text: "Bonjour ! Je m'appelle Alex." },
          { label: 'Say you are well 😊', text: 'Ça va très bien, merci ! Et toi ?' },
          { label: 'Ask how they are', text: 'Comment ça va ?' },
          { label: 'Yes, coffee! ☕', text: "Oui, j'adore le café." },
        ]
      : [
          { label: 'Say hello & how you are 👋', text: 'Salut ! Comment ça va aujourd’hui ?' },
          { label: 'Talk about your day ☕', text: 'J’ai bu un super café ce matin. Tu as passé une bonne journée ?' },
          { label: 'Ask about Paris 🎨', text: 'Tu fais quoi de beau à Paris en ce moment ?' },
        ],
    it: isStarter
      ? [
          { label: 'Say your name 👋', text: 'Ciao! Mi chiamo Alex.' },
          { label: 'Say you are well 😊', text: 'Molto bene, grazie! E tu?' },
          { label: 'Ask how they are', text: 'Come stai?' },
        ]
      : [
          { label: 'Say hello 👋', text: 'Ciao! Come stai oggi?' },
          { label: 'Talk about food 🍕', text: 'Ho mangiato una pizza incredibile oggi. Ti piace cucinare?' },
          { label: 'Ask about Rome 🏛️', text: 'Cosa fai di bello a Rome ultimamente?' },
        ],
    de: isStarter
      ? [
          { label: 'Say your name 👋', text: 'Hallo! Ich heiße Alex.' },
          { label: 'Say you are well 😊', text: 'Sehr gut, danke! Und dir?' },
          { label: 'Ask how they are', text: 'Wie geht es dir?' },
        ]
      : [
          { label: 'Say hello 👋', text: 'Hey! Wie geht es dir heute?' },
          { label: 'Talk about coffee ☕', text: 'Ich habe heute einen tollen Kaffee getrunken. Wie war dein Tag?' },
          { label: 'Ask about music 🎵', text: 'Welche Musik hörst du gerade gerne?' },
        ],
    ja: isStarter
      ? [
          { label: 'Say your name 👋', text: 'こんにちは！アレックスです。' },
          { label: 'Say you are well 😊', text: '元気です！そっちはどう？' },
        ]
      : [
          { label: 'Say hello 👋', text: 'こんにちは！元気ですか？' },
          { label: 'Talk about food 🍜', text: '今日ラーメンを食べたよ。好きな食べ物は何？' },
          { label: 'Ask about Tokyo 🎮', text: '最近何か面白いゲームやアニメはある？' },
        ],
    en: [
      { label: 'Say hello 👋', text: 'Hey! How is your day going?' },
      { label: 'Talk about coffee ☕', text: 'I just had the best coffee. What are you up to today?' },
      { label: 'Ask about music 🎵', text: 'What kind of music have you been listening to lately?' },
    ],
  }
  const starterChips = starterChipsByLang[langCode] || starterChipsByLang['es']
  const activeChips = suggestedReplies.length > 0 ? suggestedReplies : starterChips

  return (
    <div className="h-screen w-full flex flex-col bg-base-950 text-slate-100 overflow-hidden font-sans">
      {/* ========================================================================= */}
      {/* 1. INSTAGRAM-DM HEADER */}
      {/* ========================================================================= */}
      <header className="h-16 px-4 border-b border-base-800/80 bg-base-950/95 backdrop-blur-md flex items-center justify-between z-30 shrink-0">
        <div className="flex items-center gap-3">
          {/* Partner Avatar with Online Indicator */}
          <div className="relative">
            <div
              className={`w-10 h-10 rounded-full bg-gradient-to-br ${partnerStyle.gradient} flex items-center justify-center font-bold text-white text-base shadow-md`}
            >
              {partnerStyle.letter}
            </div>
            <div className="absolute bottom-0 right-0 w-3 h-3 bg-emerald-500 rounded-full border-2 border-base-950 ring-1 ring-emerald-400/50" />
          </div>

          {/* Partner Name & Subtitle */}
          <div>
            <div className="flex items-center gap-1.5 font-bold text-white text-sm leading-tight">
              <span>{partnerName}</span>
              <span>{partnerStyle.flag}</span>
            </div>
            <div className="flex items-center gap-1.5 text-[11px] text-slate-400 mt-0.5">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
              <span>Active now</span>
              <span className="text-slate-600">·</span>
              <span className="capitalize">{user?.proficiency_level || 'Beginner'}</span>
            </div>
          </div>
        </div>

        {/* Right Header Actions */}
        <div className="flex items-center gap-2">
          {/* Quick Translator Tool Button */}
          <button
            onClick={() => {
              setTranslatorInitialText('')
              setIsTranslatorOpen(true)
            }}
            title="Translate a word or sentence"
            className="px-3 py-1.5 rounded-full bg-base-900 border border-base-800 hover:border-blue-500 text-slate-300 hover:text-white flex items-center gap-1.5 transition-all text-xs font-semibold active:scale-95 shadow-sm"
          >
            <span>🌐</span>
            <span className="hidden sm:inline">Translate</span>
          </button>

          {/* Topic Reset Button */}
          <button
            onClick={handleResetConversation}
            title="Start new conversation topic"
            className="w-9 h-9 rounded-full bg-base-900 border border-base-800 hover:border-base-700 text-slate-400 hover:text-white flex items-center justify-center transition-colors text-xs"
          >
            🔄
          </button>

          {/* Quota / Pro Badge */}
          <button
            onClick={() => setIsUpgradeOpen(true)}
            className={`px-3 py-1.5 rounded-full text-xs font-semibold flex items-center gap-1.5 transition-all active:scale-95 border ${
              isPro
                ? 'bg-amber-500/10 border-amber-500/30 text-amber-300 hover:bg-amber-500/20'
                : 'bg-base-900 border-base-800 text-slate-300 hover:border-blue-500'
            }`}
          >
            {isPro ? (
              <>
                <span>⭐</span>
                <span>Pro</span>
              </>
            ) : (
              <>
                <span className="w-2 h-2 rounded-full bg-blue-500" />
                <span>{usage.messages_remaining} left</span>
              </>
            )}
          </button>

          {/* Settings / Profile Drawer Toggle */}
          <button
            onClick={() => setIsDrawerOpen(true)}
            className="w-9 h-9 rounded-full bg-base-900 border border-base-800 hover:border-base-700 text-slate-300 hover:text-white flex items-center justify-center transition-colors text-sm"
          >
            ⚙️
          </button>
        </div>
      </header>

      {/* ========================================================================= */}
      {/* 2. CONVERSATION MESSAGES AREA */}
      {/* ========================================================================= */}
      <main
        onMouseUp={handleTextSelect}
        onTouchEnd={handleTextSelect}
        className="flex-1 overflow-y-auto px-4 py-4 space-y-3.5 scrollbar-thin select-text relative"
      >
        {/* Chat Intro Card */}
        <div className="text-center py-6 border-b border-base-900 max-w-sm mx-auto space-y-2">
          <div
            className={`w-16 h-16 rounded-full bg-gradient-to-br ${partnerStyle.gradient} mx-auto flex items-center justify-center text-white text-2xl font-black shadow-xl ring-4 ring-base-900`}
          >
            {partnerStyle.letter}
          </div>
          <div className="font-bold text-white text-base">
            {partnerName} {partnerStyle.flag}
          </div>
          <p className="text-xs text-slate-400 leading-relaxed">
            {conversation?.persona_bio || 'Your conversational partner. Text freely, learn naturally!'}
          </p>
          <div className="flex flex-wrap items-center justify-center gap-1.5 pt-1">
            <span className="text-[11px] text-blue-400 font-medium bg-blue-500/10 px-3 py-0.5 rounded-full border border-blue-500/20">
              Topic: {conversation?.topic || 'Casual Chat'}
            </span>
            <span className="text-[11px] text-slate-400 bg-base-900 px-3 py-0.5 rounded-full border border-base-800">
              💡 Highlight any word or sentence to translate
            </span>
          </div>
        </div>

        {/* Messages Loop */}
        {messages.map((m, idx) => {
          const isUser = m.sender === 'user'

          // Check if feedback has a subtle correction
          let correction = null
          if (m.feedback) {
            try {
              const parsed = JSON.parse(m.feedback)
              if (parsed && parsed.better) correction = parsed
            } catch (_) {}
          }

          const isExpanded = expandedCorrectionId === m.id

          return (
            <div key={m.id || idx} className={`flex flex-col ${isUser ? 'items-end' : 'items-start'}`}>
              <div className="flex items-end gap-2 max-w-[85%] sm:max-w-[75%]">
                {/* AI Avatar */}
                {!isUser && (
                  <div
                    className={`w-7 h-7 rounded-full bg-gradient-to-br ${partnerStyle.gradient} flex items-center justify-center font-bold text-white text-[11px] shadow shrink-0 mb-1`}
                  >
                    {partnerStyle.letter}
                  </div>
                )}

                {/* Message Bubble */}
                <div
                  className={`px-4 py-2.5 rounded-2xl text-[14px] leading-relaxed break-words whitespace-pre-wrap select-text cursor-text ${
                    isUser
                      ? 'bg-blue-600 text-white rounded-br-xs'
                      : 'bg-base-900 border border-base-800/90 text-slate-100 rounded-bl-xs shadow-sm'
                  }`}
                >
                  {m.content}
                </div>
              </div>

              {/* Timestamp & Status */}
              <div
                className={`text-[10px] text-slate-500 mt-1 px-1 flex items-center gap-1.5 ${
                  isUser ? 'text-right' : 'ml-9'
                }`}
              >
                <span>
                  {new Date(m.created_at || Date.now()).toLocaleTimeString([], {
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                </span>
                {isUser ? (
                  <span>· Delivered</span>
                ) : (
                  <>
                    <span>·</span>
                    <button
                      type="button"
                      onClick={() => toggleTranslation(m.id, m.content)}
                      className="text-[11px] font-semibold text-slate-400 hover:text-blue-400 transition-colors focus:outline-none"
                    >
                      {translations[m.id]?.loading
                        ? 'Translating...'
                        : translations[m.id]?.visible
                        ? 'Hide translation'
                        : 'See translation'}
                    </button>
                  </>
                )}
              </div>

              {/* Translation Box for AI partner messages */}
              {!isUser && translations[m.id]?.visible && (
                <div className="ml-9 mt-1.5 max-w-[85%] sm:max-w-[70%] animate-pop-in">
                  <div className="px-3.5 py-2 rounded-xl bg-base-900/90 border border-base-800/80 text-[13px] text-slate-300 leading-relaxed shadow-sm">
                    <div className="text-[10px] uppercase font-bold text-slate-500 mb-0.5 tracking-wider flex items-center gap-1">
                      <span>🌐</span>
                      <span>Translation {translations[m.id]?.targetName ? `(${translations[m.id]?.targetName})` : ''}</span>
                    </div>
                    {translations[m.id]?.loading ? (
                      <span className="text-slate-400 italic text-xs">Fetching translation...</span>
                    ) : (
                      <span>{translations[m.id]?.text}</span>
                    )}
                  </div>
                </div>
              )}

              {/* Subtle Correction Pill (Attached underneath user message) */}
              {correction && (
                <div className="mt-1.5 max-w-[85%] sm:max-w-[70%] text-left animate-pop-in">
                  <div
                    onClick={() => setExpandedCorrectionId(isExpanded ? null : m.id)}
                    className="cursor-pointer bg-base-900 border border-base-800 hover:border-base-700 rounded-xl px-3 py-1.5 flex items-center gap-2 text-xs transition-colors"
                  >
                    <span className="text-[10px] font-bold text-blue-400 bg-blue-500/10 px-1.5 py-0.5 rounded">TIP</span>
                    <span className="text-slate-300 font-medium">
                      Better: <span className="text-white font-semibold">"{correction.better}"</span>
                    </span>
                    <span className="text-[10px] text-slate-500 ml-auto">{isExpanded ? '▲' : '▼'}</span>
                  </div>

                  {/* Expanded Correction Details Card */}
                  {isExpanded && (
                    <div className="mt-1.5 p-3.5 bg-base-900 border border-base-800 rounded-xl text-xs space-y-2 shadow-lg">
                      <div className="flex items-center justify-between text-[11px] text-slate-400">
                        <span>Learning Note</span>
                        <span className="text-[10px] text-blue-400 font-semibold uppercase">Natural Phrasing</span>
                      </div>

                      <div className="grid grid-cols-2 gap-2 bg-base-950 p-2 rounded-xl">
                        <div>
                          <div className="text-[10px] text-slate-500">You said</div>
                          <div className="text-red-400 line-through text-xs font-mono">{correction.original}</div>
                        </div>
                        <div>
                          <div className="text-[10px] text-slate-500">Natural way</div>
                          <div className="text-emerald-400 font-semibold text-xs font-mono">{correction.better}</div>
                        </div>
                      </div>

                      <div className="text-slate-300 text-[12px] leading-relaxed">
                        {correction.explanation}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )
        })}

        {/* Typing Indicator */}
        {aiTyping && (
          <div className="flex items-end gap-2 max-w-[75%]">
            <div
              className={`w-7 h-7 rounded-full bg-gradient-to-br ${partnerStyle.gradient} flex items-center justify-center font-bold text-white text-[11px] shadow shrink-0 mb-1`}
            >
              {partnerStyle.letter}
            </div>
            <div className="bg-base-900 border border-base-800 px-4 py-3 rounded-2xl rounded-bl-xs text-slate-400 flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce [animation-delay:-0.3s]" />
              <span className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce [animation-delay:-0.15s]" />
              <span className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce" />
            </div>
          </div>
        )}

        {/* Floating Word & Sentence Translation Popover */}
        {selectionPopup && (
          <div
            ref={selectionPopupRef}
            style={{
              position: 'fixed',
              left: `${selectionPopup.x}px`,
              top: `${selectionPopup.y}px`,
              transform: 'translate(-50%, -100%)',
              zIndex: 60,
            }}
            className="animate-pop-in pointer-events-auto"
          >
            {!selectionPopup.translation ? (
              <div className="flex items-center gap-1.5 bg-slate-900/95 border border-slate-700/90 rounded-full p-1 shadow-2xl backdrop-blur-md">
                <button
                  type="button"
                  onClick={handleTranslateSelection}
                  disabled={selectionPopup.loading}
                  className="px-3 py-1 bg-blue-600 hover:bg-blue-500 text-white rounded-full text-xs font-semibold flex items-center gap-1.5 transition-all active:scale-95 shadow-md"
                >
                  <span>🌐</span>
                  <span>
                    {selectionPopup.loading
                      ? 'Translating...'
                      : `Translate "${selectionPopup.text.slice(0, 16)}${
                          selectionPopup.text.length > 16 ? '…' : ''
                        }"`}
                  </span>
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setTranslatorInitialText(selectionPopup.text)
                    setIsTranslatorOpen(true)
                    setSelectionPopup(null)
                  }}
                  title="Open in full translator"
                  className="px-2 py-1 text-slate-300 hover:text-white text-xs hover:bg-base-800 rounded-full transition-colors"
                >
                  🔍
                </button>
                <button
                  type="button"
                  onClick={() => setSelectionPopup(null)}
                  className="w-5 h-5 rounded-full flex items-center justify-center text-slate-400 hover:text-white text-xs hover:bg-base-800"
                >
                  ✕
                </button>
              </div>
            ) : (
              <div className="w-72 bg-base-950/95 border border-blue-500/40 rounded-2xl p-3 shadow-2xl space-y-2 backdrop-blur-md animate-pop-in">
                <div className="flex items-center justify-between text-[11px] text-slate-400">
                  <span className="font-bold text-blue-400 flex items-center gap-1">
                    <span>🌐</span>
                    <span>Translation {selectionPopup.targetName ? `(${selectionPopup.targetName})` : ''}</span>
                  </span>
                  <button
                    type="button"
                    onClick={() => setSelectionPopup(null)}
                    className="text-slate-400 hover:text-white text-xs"
                  >
                    ✕
                  </button>
                </div>

                <div className="text-xs text-slate-400 bg-base-900/90 px-2.5 py-1.5 rounded-lg italic">
                  "{selectionPopup.text}"
                </div>

                <div className="text-sm font-semibold text-white leading-snug">
                  {selectionPopup.translation}
                </div>

                <div className="flex items-center gap-2 pt-1 border-t border-base-800 text-xs">
                  <button
                    type="button"
                    onClick={() => {
                      navigator.clipboard.writeText(selectionPopup.translation)
                    }}
                    className="flex-1 py-1 bg-base-800 hover:bg-base-700 text-slate-200 rounded-lg font-medium transition-colors text-center"
                  >
                    📋 Copy
                  </button>
                  <button
                    type="button"
                    onClick={handleSaveSelectionToVocab}
                    className="flex-1 py-1 bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 border border-amber-500/30 rounded-lg font-medium transition-colors text-center"
                  >
                    {selectionPopup.saved ? '✓ Saved!' : '📌 Save'}
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setTranslatorInitialText(selectionPopup.text)
                      setIsTranslatorOpen(true)
                      setSelectionPopup(null)
                    }}
                    title="Open in full translator"
                    className="px-2 py-1 bg-base-800 hover:bg-base-700 text-slate-300 rounded-lg"
                  >
                    🔍
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        <div ref={messagesEndRef} />
      </main>

      {/* ========================================================================= */}
      {/* 3. DYNAMIC CONTEXTUAL 1-TAP REPLY CHIPS & EMOJI PICKER */}
      {/* ========================================================================= */}
      {activeChips.length > 0 && !sending && !aiTyping && (
        <div className="px-4 py-2 flex items-center gap-2 overflow-x-auto scrollbar-none shrink-0 bg-base-950/90 border-t border-base-800/40">
          <div className="flex items-center gap-1 text-[11px] font-semibold text-blue-400 shrink-0 select-none mr-1">
            <span className="text-xs">⚡</span>
            <span className="hidden sm:inline">1-Tap:</span>
          </div>
          {activeChips.map((chip, i) => (
            <button
              key={i}
              type="button"
              onClick={() => handleSendMessage(chip.text)}
              title={chip.translation ? `${chip.text} (${chip.translation})` : chip.text}
              className="group px-3 py-1.5 bg-base-900 hover:bg-blue-600/20 active:scale-95 border border-base-800 hover:border-blue-500/50 text-slate-200 hover:text-blue-200 rounded-full text-xs whitespace-nowrap transition-all shadow-sm flex items-center gap-1.5"
            >
              <span className="font-medium">{chip.label}</span>
              {chip.translation && (
                <span className="text-[10px] text-slate-400 group-hover:text-blue-300 transition-colors hidden md:inline">
                  · {chip.translation}
                </span>
              )}
            </button>
          ))}
        </div>
      )}

      {showEmojiPicker && (
        <div className="px-4 py-2 bg-base-900/90 border-t border-base-800 flex items-center gap-2 overflow-x-auto shrink-0 animate-pop-in">
          {COMMON_EMOJIS.map((emoji) => (
            <button
              key={emoji}
              onClick={() => handleAddEmoji(emoji)}
              className="text-lg hover:scale-125 transition-transform p-1"
            >
              {emoji}
            </button>
          ))}
        </div>
      )}

      {/* ========================================================================= */}
      {/* 4. INSTAGRAM-DM BOTTOM INPUT BAR */}
      {/* ========================================================================= */}
      <footer className="p-3 border-t border-base-800/80 bg-base-950 shrink-0">
        <form
          onSubmit={(e) => {
            e.preventDefault()
            handleSendMessage()
          }}
          className="flex items-center gap-2 max-w-3xl mx-auto"
        >
          {/* Emoji Toggle Button */}
          <button
            type="button"
            onClick={() => setShowEmojiPicker(!showEmojiPicker)}
            className="w-10 h-10 rounded-full bg-base-900 border border-base-800 hover:border-base-700 text-slate-400 hover:text-white flex items-center justify-center transition-colors text-base shrink-0"
          >
            😊
          </button>

          {/* Quick Translator Shortcut Button */}
          <button
            type="button"
            onClick={() => {
              setTranslatorInitialText(input)
              setIsTranslatorOpen(true)
            }}
            title="Translate a word or sentence"
            className="w-10 h-10 rounded-full bg-base-900 border border-base-800 hover:border-blue-500 text-slate-400 hover:text-blue-400 flex items-center justify-center transition-colors text-base shrink-0"
          >
            🌐
          </button>

          {/* Text Input Pill */}
          <div className="flex-1 relative flex items-center">
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={sending}
              placeholder={`Message ${partnerName} in ${partnerStyle.flag}...`}
              className="w-full bg-base-900 border border-base-800 hover:border-base-700 focus:border-blue-500 rounded-full px-5 py-2.5 text-sm text-white placeholder-slate-500 outline-none transition-all shadow-inner"
            />
          </div>

          {/* Send Button */}
          <button
            type="submit"
            disabled={sending || !input.trim()}
            className={`w-10 h-10 rounded-full flex items-center justify-center transition-all duration-150 shrink-0 ${
              input.trim()
                ? 'bg-blue-600 hover:bg-blue-500 text-white shadow-lg shadow-blue-500/25 active:scale-95'
                : 'bg-base-900 border border-base-800 text-slate-600 cursor-not-allowed'
            }`}
          >
            <svg
              className="w-4 h-4 translate-x-0.5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2.5}
                d="M5 12h14M12 5l7 7-7 7"
              />
            </svg>
          </button>
        </form>
      </footer>

      {/* ========================================================================= */}
      {/* 5. MODALS & DRAWERS */}
      {/* ========================================================================= */}
      <ProfileDrawer
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        user={user}
        onUserUpdated={onUserUpdated}
        onOpenUpgrade={() => setIsUpgradeOpen(true)}
        onLanguageChanged={handleLanguageChange}
        onLogout={onLogout}
      />

      <UpgradeModal
        isOpen={isUpgradeOpen}
        onClose={() => setIsUpgradeOpen(false)}
        currentTier={usage.tier}
        onTierChanged={(newTier) => {
          loadUsage()
          onUserUpdated({ ...user, subscription_tier: newTier })
        }}
      />

      <QuickTranslator
        isOpen={isTranslatorOpen}
        onClose={() => setIsTranslatorOpen(false)}
        learningLangCode={langCode}
        learningLangName={partnerStyle.name || partnerName}
        nativeLangCode={user?.native_language_code || 'en'}
        initialText={translatorInitialText}
        onInsertMessage={(text) => {
          setInput(text)
          inputRef.current?.focus()
        }}
      />
    </div>
  )
}
