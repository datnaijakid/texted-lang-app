import { useEffect, useState } from 'react'
import { api, setToken } from '../api'

const LANGUAGES = [
  { code: 'es', name: 'Spanish', flag: '🇪🇸', partner: 'Sofia' },
  { code: 'fr', name: 'French', flag: '🇫🇷', partner: 'Camille' },
  { code: 'it', name: 'Italian', flag: '🇮🇹', partner: 'Marco' },
  { code: 'de', name: 'German', flag: '🇩🇪', partner: 'Lukas' },
  { code: 'ja', name: 'Japanese', flag: '🇯🇵', partner: 'Kenji' },
  { code: 'en', name: 'English', flag: '🇬🇧', partner: 'Emma' },
]

export default function ProfileDrawer({
  isOpen,
  onClose,
  user,
  onUserUpdated,
  onOpenUpgrade,
  onLanguageChanged,
  onLogout,
}) {
  const [tab, setTab] = useState('settings') // 'settings' | 'notebook'
  const [notebook, setNotebook] = useState([])
  const [loadingNotebook, setLoadingNotebook] = useState(false)
  const [saving, setSaving] = useState(false)

  const [level, setLevel] = useState(user?.proficiency_level || 'beginner')
  const [goal, setGoal] = useState(user?.learning_goal || 'casual')
  const [langCode, setLangCode] = useState(user?.learning_language_code || 'es')
  const [nativeLangCode, setNativeLangCode] = useState(user?.native_language_code || 'en')
  const [autoTranslate, setAutoTranslate] = useState(Boolean(user?.auto_translate))

  useEffect(() => {
    if (user) {
      setLevel(user.proficiency_level || 'beginner')
      setGoal(user.learning_goal || 'casual')
      setLangCode(user.learning_language_code || 'es')
      setNativeLangCode(user.native_language_code || 'en')
      setAutoTranslate(Boolean(user.auto_translate))
    }
  }, [user])

  useEffect(() => {
    if (tab === 'notebook' && isOpen) {
      setLoadingNotebook(true)
      api.getNotebook()
        .then(setNotebook)
        .catch(() => setNotebook([]))
        .finally(() => setLoadingNotebook(false))
    }
  }, [tab, isOpen])

  if (!isOpen) return null

  async function handleSaveSettings() {
    setSaving(true)
    try {
      const updated = await api.updateProfile({
        learning_language_code: langCode,
        native_language_code: nativeLangCode,
        proficiency_level: level,
        learning_goal: goal,
        auto_translate: autoTranslate,
      })
      onUserUpdated(updated)
      onLanguageChanged(langCode)
      onClose()
    } catch (err) {
      alert(err.message || 'Failed to update settings')
    } finally {
      setSaving(false)
    }
  }

  function handleLogout() {
    setToken(null)
    onLogout()
  }

  const isPro = (user?.subscription_tier || 'free').toLowerCase() === 'pro'

  return (
    <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex justify-end transition-opacity">
      <div className="w-full max-w-md bg-base-950 border-l border-base-800 h-full flex flex-col shadow-2xl animate-in slide-in-from-right duration-200">
        {/* Drawer Header */}
        <div className="px-5 py-4 border-b border-base-800 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="font-bold text-white text-base">Account & Settings</span>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-full bg-base-800 hover:bg-base-700 flex items-center justify-center text-slate-400 hover:text-white transition-colors"
          >
            ✕
          </button>
        </div>

        {/* Tab Toggle */}
        <div className="px-5 pt-4 pb-2">
          <div className="flex bg-base-900 border border-base-800 rounded-xl p-1">
            <button
              onClick={() => setTab('settings')}
              className={`flex-1 py-2 text-xs font-semibold rounded-lg transition-colors ${
                tab === 'settings' ? 'bg-base-800 text-white shadow' : 'text-slate-400 hover:text-white'
              }`}
            >
              ⚙️ Practice Settings
            </button>
            <button
              onClick={() => setTab('notebook')}
              className={`flex-1 py-2 text-xs font-semibold rounded-lg transition-colors ${
                tab === 'notebook' ? 'bg-base-800 text-white shadow' : 'text-slate-400 hover:text-white'
              }`}
            >
              📓 Saved Vocab ({notebook.length})
            </button>
          </div>
        </div>

        {/* Tab Content */}
        <div className="flex-1 overflow-y-auto px-5 py-3 space-y-5">
          {tab === 'settings' && (
            <>
              {/* User Subscription Status Card */}
              <div className="p-4 rounded-2xl bg-base-900 border border-base-800 flex items-center justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-bold text-white">
                      {isPro ? '⭐ Texted Pro Plan' : 'Free Plan'}
                    </span>
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                        isPro ? 'bg-amber-500/20 text-amber-300' : 'bg-slate-700 text-slate-300'
                      }`}
                    >
                      {isPro ? 'UNLIMITED' : `${20 - (user?.daily_messages_count || 0)}/20 msgs left`}
                    </span>
                  </div>
                  <div className="text-xs text-slate-400 mt-1">
                    {user?.email}
                  </div>
                </div>

                {!isPro && (
                  <button
                    onClick={() => {
                      onClose()
                      onOpenUpgrade()
                    }}
                    className="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold rounded-lg shadow-md transition-all active:scale-95"
                  >
                    Upgrade
                  </button>
                )}
              </div>

              {/* Language & Partner selection */}
              <div className="space-y-2">
                <label className="text-xs font-bold text-slate-400 uppercase tracking-wider block">
                  Target Language & Partner
                </label>
                <div className="grid grid-cols-2 gap-2">
                  {LANGUAGES.map((l) => (
                    <div
                      key={l.code}
                      onClick={() => setLangCode(l.code)}
                      className={`p-3 rounded-xl border cursor-pointer transition-all flex items-center gap-2.5 ${
                        langCode === l.code
                          ? 'border-blue-500 bg-blue-500/10 text-white'
                          : 'border-base-800 bg-base-900 text-slate-300 hover:border-base-700'
                      }`}
                    >
                      <span className="text-lg">{l.flag}</span>
                      <div className="min-w-0">
                        <div className="text-xs font-semibold truncate">{l.partner}</div>
                        <div className="text-[10px] text-slate-400 truncate">{l.name}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Difficulty Level */}
              <div className="space-y-2">
                <label className="text-xs font-bold text-slate-400 uppercase tracking-wider block">
                  Proficiency Level
                </label>
                <div className="grid grid-cols-2 gap-2">
                  {[
                    { id: 'starter', label: '🌱 Starter', desc: 'Basics only (Hello, Thanks)' },
                    { id: 'beginner', label: '🌿 Beginner', desc: 'Short everyday phrases' },
                    { id: 'intermediate', label: '🌲 Interm.', desc: 'Comfortable chatting' },
                    { id: 'advanced', label: '🔥 Adv.', desc: 'Native slang & speed' },
                  ].map((lvl) => (
                    <button
                      key={lvl.id}
                      type="button"
                      onClick={() => setLevel(lvl.id)}
                      className={`p-2.5 text-left rounded-xl border transition-all ${
                        level === lvl.id
                          ? 'border-blue-500 bg-blue-500/10 text-white font-semibold shadow-sm'
                          : 'border-base-800 bg-base-900 text-slate-400 hover:text-white'
                      }`}
                    >
                      <div className="text-xs font-bold text-slate-200">{lvl.label}</div>
                      <div className="text-[10px] text-slate-400 font-normal leading-tight mt-0.5">{lvl.desc}</div>
                    </button>
                  ))}
                </div>
              </div>

              {/* Learning Goal */}
              <div className="space-y-2">
                <label className="text-xs font-bold text-slate-400 uppercase tracking-wider block">
                  Learning Goal
                </label>
                <select
                  value={goal}
                  onChange={(e) => setGoal(e.target.value)}
                  className="w-full bg-base-900 border border-base-800 rounded-xl px-3 py-2.5 text-xs text-white outline-none focus:border-blue-500"
                >
                  <option value="casual">💬 Casual Chit-Chat</option>
                  <option value="natural">🗣️ Speak Naturally & Slang</option>
                  <option value="vocab">📚 Expand Vocabulary</option>
                  <option value="grammar">🎯 Grammar & Corrections</option>
                  <option value="confidence">🚀 Confidence & Fluency</option>
                  <option value="work">✈️ Work & Travel Conversations</option>
                </select>
              </div>

              {/* Translation Settings */}
              <div className="space-y-3 pt-2 border-t border-base-800/80">
                <label className="text-xs font-bold text-slate-400 uppercase tracking-wider block">
                  🌐 Translation Settings
                </label>

                <div>
                  <label className="text-[11px] text-slate-400 block mb-1">
                    Translate the other person's language to:
                  </label>
                  <select
                    value={nativeLangCode}
                    onChange={(e) => setNativeLangCode(e.target.value)}
                    className="w-full bg-base-900 border border-base-800 rounded-xl px-3 py-2.5 text-xs text-white outline-none focus:border-blue-500"
                  >
                    <option value="en">🇬🇧 English</option>
                    <option value="es">🇪🇸 Spanish (Español)</option>
                    <option value="fr">🇫🇷 French (Français)</option>
                    <option value="de">🇩🇪 German (Deutsch)</option>
                    <option value="it">🇮🇹 Italian (Italiano)</option>
                    <option value="pt">🇧🇷 Portuguese (Português)</option>
                    <option value="ja">🇯🇵 Japanese (日本語)</option>
                  </select>
                </div>

                <label className="flex items-start gap-3 p-3 bg-base-900 border border-base-800 rounded-xl cursor-pointer hover:border-base-700 transition-colors">
                  <input
                    type="checkbox"
                    checked={autoTranslate}
                    onChange={(e) => setAutoTranslate(e.target.checked)}
                    className="w-4 h-4 mt-0.5 rounded text-blue-600 focus:ring-blue-500 bg-base-950 border-base-700"
                  />
                  <div>
                    <div className="text-xs font-semibold text-white">Always show translations</div>
                    <div className="text-[11px] text-slate-400 leading-tight">
                      Automatically display English/chosen translations beneath their messages
                    </div>
                  </div>
                </label>
              </div>

              <div className="pt-2">
                <button
                  onClick={handleSaveSettings}
                  disabled={saving}
                  className="w-full py-2.5 bg-blue-600 hover:bg-blue-500 text-white font-semibold text-xs rounded-xl shadow-md transition-all active:scale-[0.98] disabled:opacity-50"
                >
                  {saving ? 'Saving changes…' : 'Apply Changes'}
                </button>
              </div>
            </>
          )}

          {tab === 'notebook' && (
            <div className="space-y-3">
              {loadingNotebook && (
                <div className="text-center text-xs text-slate-500 py-6">Loading saved vocabulary…</div>
              )}

              {!loadingNotebook && notebook.length === 0 && (
                <div className="text-center py-8 text-slate-500 space-y-2">
                  <div className="text-3xl">📓</div>
                  <div className="text-xs">No saved words yet.</div>
                  <div className="text-[11px] text-slate-600 max-w-xs mx-auto">
                    When your AI partner corrects or teaches you a word during chat, tap "Save" to keep it here!
                  </div>
                </div>
              )}

              {!loadingNotebook &&
                notebook.map((item, idx) => (
                  <div
                    key={idx}
                    className="p-3 bg-base-900 border border-base-800 rounded-xl space-y-1"
                  >
                    <div className="flex items-center justify-between">
                      <div className="font-bold text-sm text-white">{item.vocabulary.term}</div>
                      <span className="text-[10px] bg-base-800 text-slate-400 px-2 py-0.5 rounded-full capitalize">
                        {item.reason}
                      </span>
                    </div>
                    <div className="text-xs text-blue-400">{item.vocabulary.translation}</div>
                    {item.vocabulary.example_sentence && (
                      <div className="text-[11px] text-slate-400 italic pt-1">
                        "{item.vocabulary.example_sentence}"
                      </div>
                    )}
                  </div>
                ))}
            </div>
          )}
        </div>

        {/* Drawer Footer */}
        <div className="px-5 py-4 border-t border-base-800 flex items-center justify-between text-xs">
          <button
            onClick={handleLogout}
            className="text-red-400 hover:text-red-300 font-medium transition-colors"
          >
            Log out
          </button>
          <div className="text-slate-600 text-[11px]">Texted v0.2.0 · Instagram-DM MVP</div>
        </div>
      </div>
    </div>
  )
}
