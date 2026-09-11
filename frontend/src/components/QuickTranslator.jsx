import React, { useState, useEffect } from 'react'
import { api } from '../api'

const LANG_MAP = {
  en: { name: 'English', flag: '🇬🇧' },
  es: { name: 'Spanish', flag: '🇪🇸' },
  fr: { name: 'French', flag: '🇫🇷' },
  de: { name: 'German', flag: '🇩🇪' },
  it: { name: 'Italian', flag: '🇮🇹' },
  pt: { name: 'Portuguese', flag: '🇧🇷' },
  ja: { name: 'Japanese', flag: '🇯🇵' },
}

export default function QuickTranslator({
  isOpen,
  onClose,
  learningLangCode = 'fr',
  nativeLangCode = 'en',
  onInsertMessage,
  initialText = '',
}) {
  // Direction: 'to_native' (foreign -> native) or 'to_learning' (native -> foreign)
  const [direction, setDirection] = useState('to_native')
  const [inputText, setInputText] = useState(initialText || '')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [saved, setSaved] = useState(false)
  const [copied, setCopied] = useState(false)

  const learningLang = LANG_MAP[learningLangCode] || { name: 'Target Language', flag: '🌐' }
  const nativeLang = LANG_MAP[nativeLangCode] || { name: 'My Language', flag: '🇬🇧' }

  const sourceLang = direction === 'to_native' ? learningLang : nativeLang
  const targetLang = direction === 'to_native' ? nativeLang : learningLang
  const targetLangCode = direction === 'to_native' ? nativeLangCode : learningLangCode

  useEffect(() => {
    if (initialText) {
      setInputText(initialText)
      handleTranslate(initialText)
    }
  }, [initialText])

  async function handleTranslate(textToTranslate = inputText) {
    const query = textToTranslate.trim()
    if (!query) return

    setLoading(true)
    setError('')
    setSaved(false)
    setCopied(false)

    try {
      const res = await api.translateMessage(query, targetLangCode)
      setResult(res.translated_text)
    } catch (err) {
      setError(err.message || 'Failed to translate.')
    } finally {
      setLoading(false)
    }
  }

  function handleSwapDirection() {
    setDirection((prev) => (prev === 'to_native' ? 'to_learning' : 'to_native'))
    if (result) {
      setInputText(result)
      setResult(null)
    }
  }

  async function handleSaveToNotebook() {
    if (!result || !inputText) return
    try {
      const term = direction === 'to_native' ? inputText : result
      const translation = direction === 'to_native' ? result : inputText
      await api.saveCustomWord(term, translation, learningLangCode)
      setSaved(true)
      setTimeout(() => setSaved(false), 2500)
    } catch (err) {
      alert('Failed to save to notebook: ' + err.message)
    }
  }

  function handleCopy() {
    if (!result) return
    navigator.clipboard.writeText(result)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  function handleInsert() {
    if (!result) return
    onInsertMessage?.(result)
    onClose()
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4 animate-in fade-in duration-150">
      <div className="w-full max-w-lg bg-base-950 border border-base-800 rounded-3xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="px-5 py-4 border-b border-base-800 flex items-center justify-between bg-base-900/50">
          <div className="flex items-center gap-2">
            <span className="text-lg">🌐</span>
            <div>
              <h3 className="text-sm font-bold text-white">Translate Word or Sentence</h3>
              <p className="text-[11px] text-slate-400">Look up any phrase or prepare what to say</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-full bg-base-800 hover:bg-base-700 flex items-center justify-center text-slate-400 hover:text-white transition-colors"
          >
            ✕
          </button>
        </div>

        {/* Direction Switcher */}
        <div className="px-5 pt-4 pb-2">
          <div className="flex items-center justify-between bg-base-900 border border-base-800 rounded-2xl p-2">
            <div className="flex items-center gap-2 px-3 py-1.5 bg-base-950 rounded-xl text-xs font-semibold text-white">
              <span>{sourceLang.flag}</span>
              <span>{sourceLang.name}</span>
            </div>

            <button
              onClick={handleSwapDirection}
              type="button"
              title="Swap translation direction"
              className="w-8 h-8 rounded-full bg-base-800 hover:bg-blue-600 hover:text-white text-slate-300 flex items-center justify-center transition-all active:scale-90 text-sm font-bold"
            >
              ⇄
            </button>

            <div className="flex items-center gap-2 px-3 py-1.5 bg-base-950 rounded-xl text-xs font-semibold text-white">
              <span>{targetLang.flag}</span>
              <span>{targetLang.name}</span>
            </div>
          </div>
        </div>

        {/* Content Body */}
        <div className="p-5 space-y-4 overflow-y-auto flex-1">
          {/* Input Box */}
          <div className="space-y-1.5">
            <label className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block">
              Enter word or sentence ({sourceLang.name})
            </label>
            <div className="relative">
              <textarea
                rows={3}
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault()
                    handleTranslate()
                  }
                }}
                placeholder={
                  direction === 'to_native'
                    ? `e.g. "racontes", "Comment s'est passée ta journée ?"`
                    : `e.g. "How are you doing today?", "I want a coffee"`
                }
                className="w-full bg-base-900 border border-base-800 focus:border-blue-500 rounded-2xl p-3 text-sm text-white placeholder-slate-500 outline-none resize-none"
              />
              {inputText && (
                <button
                  type="button"
                  onClick={() => {
                    setInputText('')
                    setResult(null)
                  }}
                  className="absolute top-2 right-2 text-xs text-slate-400 hover:text-slate-200 bg-base-800 rounded-full w-5 h-5 flex items-center justify-center"
                >
                  ✕
                </button>
              )}
            </div>
          </div>

          {/* Action to trigger translation */}
          <button
            onClick={() => handleTranslate()}
            disabled={loading || !inputText.trim()}
            className="w-full py-2.5 bg-blue-600 hover:bg-blue-500 disabled:opacity-40 text-white text-xs font-bold rounded-xl transition-all shadow-md active:scale-[0.99] flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                <span>Translating...</span>
              </>
            ) : (
              <>
                <span>🌐 Translate to {targetLang.name}</span>
              </>
            )}
          </button>

          {/* Error notice */}
          {error && (
            <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs">
              {error}
            </div>
          )}

          {/* Result Card */}
          {result && (
            <div className="p-4 rounded-2xl bg-base-900 border border-blue-500/30 space-y-3 animate-pop-in">
              <div className="flex items-center justify-between text-[11px] text-slate-400">
                <span className="font-semibold text-blue-400 flex items-center gap-1.5">
                  <span>Translation ({targetLang.name})</span>
                </span>
                <span className="text-[10px] text-slate-500">Ready to use</span>
              </div>

              <div className="text-base font-medium text-white leading-relaxed bg-base-950 p-3 rounded-xl border border-base-800/80 select-text">
                {result}
              </div>

              {/* Action Buttons for Result */}
              <div className="flex flex-wrap items-center gap-2 pt-1">
                {direction === 'to_learning' && onInsertMessage && (
                  <button
                    type="button"
                    onClick={handleInsert}
                    className="flex-1 py-2 px-3 bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold rounded-xl flex items-center justify-center gap-1.5 active:scale-95 transition-colors"
                  >
                    <span>💬 Insert into chat</span>
                  </button>
                )}

                <button
                  type="button"
                  onClick={handleCopy}
                  className="py-2 px-3 bg-base-800 hover:bg-base-700 text-slate-200 text-xs font-semibold rounded-xl flex items-center justify-center gap-1.5 active:scale-95 transition-all"
                >
                  <span>{copied ? '✓ Copied!' : '📋 Copy'}</span>
                </button>

                <button
                  type="button"
                  onClick={handleSaveToNotebook}
                  className="py-2 px-3 bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/30 text-amber-300 text-xs font-semibold rounded-xl flex items-center justify-center gap-1.5 active:scale-95 transition-all"
                >
                  <span>{saved ? '✓ Saved!' : '📌 Save to Vocab'}</span>
                </button>
              </div>
            </div>
          )}

          {/* Quick Word & Phrase Suggestions */}
          <div className="pt-2 border-t border-base-800/60">
            <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-2">
              💡 Quick Practice Phrases
            </div>
            <div className="flex flex-wrap gap-1.5">
              {[
                direction === 'to_native'
                  ? ['racontes', 'truc sympa', "Comment s'est passée ta journée ?", 'Tu as prévu quoi pour ce soir ?', 'café', 'école']
                  : ['How was your day?', 'I had coffee', 'What are you doing tonight?', 'Nice to meet you', 'Tell me more']
              ][0].map((sample) => (
                <button
                  key={sample}
                  type="button"
                  onClick={() => {
                    setInputText(sample)
                    handleTranslate(sample)
                  }}
                  className="px-2.5 py-1 bg-base-900 hover:bg-base-800 border border-base-800 hover:border-slate-700 rounded-lg text-xs text-slate-300 transition-colors"
                >
                  {sample}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
