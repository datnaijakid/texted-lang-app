import { useState } from 'react'
import { api } from '../api'

const LANGUAGES = [
  {
    code: 'es',
    name: 'Spanish',
    flag: '🇪🇸',
    partner: 'Sofia',
    handle: '@sofia_bcn',
    city: 'Barcelona',
    tagline: 'Warm & witty, loves indie music & coffee',
    avatarGradient: 'from-rose-500 to-amber-500',
    avatarLetter: 'S',
  },
  {
    code: 'fr',
    name: 'French',
    flag: '🇫🇷',
    partner: 'Camille',
    handle: '@camille_paris',
    city: 'Paris',
    tagline: 'Architecture student, cafe culture & art',
    avatarGradient: 'from-emerald-500 to-teal-500',
    avatarLetter: 'C',
  },
  {
    code: 'it',
    name: 'Italian',
    flag: '🇮🇹',
    partner: 'Marco',
    handle: '@marco_roma',
    city: 'Rome',
    tagline: 'Cinema fan & foodie, loves good vibes',
    avatarGradient: 'from-amber-500 to-orange-500',
    avatarLetter: 'M',
  },
  {
    code: 'de',
    name: 'German',
    flag: '🇩🇪',
    partner: 'Lukas',
    handle: '@lukas_berlin',
    city: 'Berlin',
    tagline: 'Tech designer & music lover, direct & chill',
    avatarGradient: 'from-blue-500 to-cyan-500',
    avatarLetter: 'L',
  },
  {
    code: 'ja',
    name: 'Japanese',
    flag: '🇯🇵',
    partner: 'Kenji',
    handle: '@kenji_tokyo',
    city: 'Tokyo',
    tagline: 'Animator & gamer, friendly casual chats',
    avatarGradient: 'from-purple-500 to-pink-500',
    avatarLetter: 'K',
  },
  {
    code: 'en',
    name: 'English',
    flag: '🇬🇧',
    partner: 'Emma',
    handle: '@emma_nyc',
    city: 'New York',
    tagline: 'Podcast creator, street food & travel',
    avatarGradient: 'from-indigo-500 to-purple-500',
    avatarLetter: 'E',
  },
]

const LEVELS = [
  {
    id: 'starter',
    title: 'Starter (Basics only)',
    desc: 'Know just a few words (hello, thanks, yes/no). Ultra-short sentences with hints.',
    icon: '🌱',
  },
  {
    id: 'beginner',
    title: 'Beginner',
    desc: 'Know everyday phrases & basic greetings. Building simple sentences.',
    icon: '🌿',
  },
  {
    id: 'intermediate',
    title: 'Intermediate',
    desc: 'Can carry simple chats, want more confidence & vocabulary.',
    icon: '🌲',
  },
  {
    id: 'advanced',
    title: 'Advanced',
    desc: 'Want native flow, slang & full conversational speed.',
    icon: '🔥',
  },
]

const GOALS = [
  { id: 'casual', label: 'Casual Chit-Chat', icon: '💬', desc: 'Everyday texting with friends' },
  { id: 'natural', label: 'Speak Naturally', icon: '🗣️', desc: 'Real slang & idioms, not textbooks' },
  { id: 'vocab', label: 'Expand Vocabulary', icon: '📚', desc: 'Learn fresh words in context' },
  { id: 'grammar', label: 'Grammar Polish', icon: '🎯', desc: 'Subtle corrections on mistakes' },
  { id: 'confidence', label: 'Overcome Anxiety', icon: '🚀', desc: 'Judgment-free safe practice' },
  { id: 'work', label: 'Work & Travel', icon: '✈️', desc: 'Practical conversations' },
]

export default function OnboardingModal({ user, onComplete }) {
  const [step, setStep] = useState(1) // 1 -> 2 -> 3
  const [selectedLang, setSelectedLang] = useState(user?.learning_language_code || 'es')
  const [selectedLevel, setSelectedLevel] = useState(user?.proficiency_level || 'starter')
  const [selectedGoal, setSelectedGoal] = useState(user?.learning_goal || 'casual')
  const [displayName, setDisplayName] = useState(user?.display_name || '')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const activeLang = LANGUAGES.find((l) => l.code === selectedLang) || LANGUAGES[0]

  async function finishOnboarding() {
    setLoading(true)
    setError(null)
    try {
      await api.onboarding({
        learning_language_code: selectedLang,
        native_language_code: user?.native_language_code || 'en',
        proficiency_level: selectedLevel,
        learning_goal: selectedGoal,
        display_name: displayName.trim() || undefined,
      })
      api.trackEvent('onboarding_complete', {
        language: selectedLang,
        level: selectedLevel,
        goal: selectedGoal,
      })
      onComplete()
    } catch (err) {
      setError(err.message || 'Failed to finish onboarding')
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex items-center justify-center p-4">
      <div className="w-full max-w-lg bg-base-900 border border-base-700/80 rounded-3xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Top Header & Progress */}
        <div className="px-6 pt-6 pb-4 border-b border-base-800 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="font-bold text-white tracking-tight">Choose Your Language Partner</span>
          </div>
          <div className="flex items-center gap-1.5">
            {[1, 2, 3].map((s) => (
              <div
                key={s}
                className={`h-2 rounded-full transition-all duration-300 ${
                  s === step ? 'w-6 bg-blue-500' : s < step ? 'w-2 bg-blue-500/50' : 'w-2 bg-base-700'
                }`}
              />
            ))}
          </div>
        </div>

        {/* Modal Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {error && (
            <div className="bg-red-500/10 border border-red-500/30 text-red-400 text-xs px-3 py-2 rounded-xl">
              {error}
            </div>
          )}

          {/* STEP 1: Select Language & Meet Persona */}
          {step === 1 && (
            <div className="space-y-4">
              <div>
                <h2 className="text-xl font-bold text-white">Who do you want to text with?</h2>
                <p className="text-sm text-slate-400 mt-1">
                  Choose a language partner living in their home city.
                </p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                {LANGUAGES.map((l) => {
                  const isSelected = selectedLang === l.code
                  return (
                    <div
                      key={l.code}
                      onClick={() => setSelectedLang(l.code)}
                      className={`p-3.5 rounded-2xl border transition-all cursor-pointer flex items-center gap-3.5 ${
                        isSelected
                          ? 'border-blue-500 bg-blue-500/10 shadow-sm ring-1 ring-blue-500/50'
                          : 'border-base-700 bg-base-800/60 hover:bg-base-800 hover:border-base-600'
                      }`}
                    >
                      <div
                        className={`w-11 h-11 rounded-full bg-gradient-to-br ${l.avatarGradient} flex items-center justify-center font-bold text-white shadow-md text-base shrink-0`}
                      >
                        {l.avatarLetter}
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center justify-between font-semibold text-white text-sm">
                          <div className="flex items-center gap-1.5 truncate">
                            <span>{l.partner}</span>
                            <span className="text-xs text-zinc-400 font-normal">{l.handle}</span>
                          </div>
                          <span className="text-xs shrink-0 ml-1">{l.flag}</span>
                        </div>
                        <div className="text-xs text-blue-400 font-medium">{l.name} · {l.city}</div>
                        <div className="text-[11px] text-slate-400 truncate mt-0.5">{l.tagline}</div>
                      </div>
                    </div>
                  )
                })}
              </div>

              <div className="pt-2">
                <label className="text-xs font-semibold text-slate-400 block mb-1.5">
                  What should {activeLang.partner} call you?
                </label>
                <input
                  type="text"
                  placeholder="Your first name"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  className="w-full bg-base-800 border border-base-700 rounded-xl px-4 py-2.5 text-white placeholder-slate-500 outline-none focus:border-blue-500 text-sm transition-colors"
                />
              </div>
            </div>
          )}

          {/* STEP 2: Level Selection */}
          {step === 2 && (
            <div className="space-y-4">
              <div>
                <h2 className="text-xl font-bold text-white">What is your current level in {activeLang.name}?</h2>
                <p className="text-sm text-slate-400 mt-1">
                  {activeLang.partner} will automatically match your speed, vocabulary, and slang.
                </p>
              </div>

              <div className="space-y-3">
                {LEVELS.map((lvl) => {
                  const isSelected = selectedLevel === lvl.id
                  return (
                    <div
                      key={lvl.id}
                      onClick={() => setSelectedLevel(lvl.id)}
                      className={`p-4 rounded-2xl border transition-all cursor-pointer flex items-center justify-between ${
                        isSelected
                          ? 'border-blue-500 bg-blue-500/10 shadow-sm ring-1 ring-blue-500/50'
                          : 'border-base-700 bg-base-800/60 hover:bg-base-800 hover:border-base-600'
                      }`}
                    >
                      <div className="flex items-center gap-3.5">
                        <span className="text-2xl">{lvl.icon}</span>
                        <div>
                          <div className="font-semibold text-white text-sm">{lvl.title}</div>
                          <div className="text-xs text-slate-400 mt-0.5">{lvl.desc}</div>
                        </div>
                      </div>
                      <div
                        className={`w-5 h-5 rounded-full border flex items-center justify-center transition-colors ${
                          isSelected ? 'border-blue-500 bg-blue-500' : 'border-base-600'
                        }`}
                      >
                        {isSelected && <div className="w-2 h-2 rounded-full bg-white" />}
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          {/* STEP 3: Learning Goal */}
          {step === 3 && (
            <div className="space-y-4">
              <div>
                <h2 className="text-xl font-bold text-white">What's your main practice goal?</h2>
                <p className="text-sm text-slate-400 mt-1">
                  Tell {activeLang.partner} what to focus on during your chats.
                </p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                {GOALS.map((g) => {
                  const isSelected = selectedGoal === g.id
                  return (
                    <div
                      key={g.id}
                      onClick={() => setSelectedGoal(g.id)}
                      className={`p-3.5 rounded-2xl border transition-all cursor-pointer flex items-start gap-3 ${
                        isSelected
                          ? 'border-blue-500 bg-blue-500/10 shadow-sm ring-1 ring-blue-500/50'
                          : 'border-base-700 bg-base-800/60 hover:bg-base-800 hover:border-base-600'
                      }`}
                    >
                      <span className="text-xl shrink-0 mt-0.5">{g.icon}</span>
                      <div>
                        <div className="font-semibold text-white text-sm">{g.label}</div>
                        <div className="text-[11px] text-slate-400 mt-0.5 leading-tight">{g.desc}</div>
                      </div>
                    </div>
                  )
                })}
              </div>

              {/* Preview Bubble */}
              <div className="mt-4 p-4 rounded-2xl bg-base-800/50 border border-base-700/60">
                <div className="text-xs text-slate-400 font-medium mb-2">First message preview:</div>
                <div className="flex gap-2.5 items-start">
                  <div
                    className={`w-8 h-8 rounded-full bg-gradient-to-br ${activeLang.avatarGradient} flex items-center justify-center font-bold text-white text-xs shrink-0`}
                  >
                    {activeLang.avatarLetter}
                  </div>
                  <div className="bg-base-700/80 text-slate-200 text-xs px-3.5 py-2.5 rounded-2xl rounded-bl-xs leading-relaxed max-w-xs">
                    "Heyyy 👋 I'm {activeLang.partner}. I'm gonna help you practice {activeLang.name}, but don't worry — I'm not gonna make this feel like school 😂"
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer Controls */}
        <div className="px-6 py-4 border-t border-base-800 bg-base-900/90 flex items-center justify-between gap-3">
          {step > 1 ? (
            <button
              onClick={() => setStep(step - 1)}
              disabled={loading}
              className="px-4 py-2 text-sm font-semibold text-slate-400 hover:text-white transition-colors"
            >
              ← Back
            </button>
          ) : (
            <div />
          )}

          {step < 3 ? (
            <button
              onClick={() => setStep(step + 1)}
              className="px-6 py-2.5 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-sm font-semibold shadow-lg shadow-blue-500/20 transition-all active:scale-[0.98]"
            >
              Continue →
            </button>
          ) : (
            <button
              onClick={finishOnboarding}
              disabled={loading}
              className="px-6 py-2.5 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-sm font-semibold transition-colors active:scale-[0.99] disabled:opacity-50"
            >
              {loading ? 'Starting conversation…' : `Start Texting ${activeLang.partner} →`}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
