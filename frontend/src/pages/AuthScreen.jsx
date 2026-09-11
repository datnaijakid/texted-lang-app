import { useState } from 'react'
import { api, setToken } from '../api'

export default function AuthScreen({ onAuthed }) {
  const [mode, setMode] = useState('login') // 'login' | 'register' | 'forgot' | 'reset'
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [resetCode, setResetCode] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [error, setError] = useState(null)
  const [info, setInfo] = useState(null)
  const [loading, setLoading] = useState(false)

  async function submit(e) {
    e.preventDefault()
    setError(null)
    setInfo(null)
    setLoading(true)
    try {
      if (mode === 'register') {
        const res = await api.register({
          email,
          password,
          display_name: displayName.trim() || undefined,
          native_language_code: 'en',
          learning_language_code: 'es',
        })
        setToken(res.access_token)
        onAuthed()
      } else if (mode === 'login') {
        const res = await api.login(email, password)
        setToken(res.access_token)
        onAuthed()
      } else if (mode === 'forgot') {
        const res = await api.forgotPassword(email)
        setInfo(res.message || 'Reset code sent! Check your inbox.')
        setMode('reset')
      } else if (mode === 'reset') {
        const res = await api.resetPassword(email, resetCode.trim(), newPassword)
        if (res && res.access_token) {
          setToken(res.access_token)
          onAuthed()
        } else {
          setInfo('Password reset successful! You can now log in.')
          setMode('login')
          setPassword('')
        }
      }
    } catch (err) {
      setError(err.message || 'Authentication request failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-[#09090b] flex flex-col items-center justify-center px-4 py-8">
      <div className="w-full max-w-sm space-y-6">
        {/* Brand Header */}
        <div className="text-center space-y-2">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-2xl bg-blue-600 text-white text-xl font-bold mb-1 shadow-sm">
            💬
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight">
            Texted<span className="text-blue-500">.</span>
          </h1>
          <p className="text-sm text-zinc-400 max-w-xs mx-auto">
            Practice a new language by texting a native-speaking friend.
          </p>
        </div>

        {/* Auth Card */}
        <div className="bg-[#121215] border border-zinc-800 rounded-2xl p-6 shadow-xl space-y-5">
          {/* Mode Switcher */}
          {mode !== 'forgot' && mode !== 'reset' && (
            <div className="flex bg-[#09090b] border border-zinc-800 rounded-xl p-1">
              <button
                type="button"
                onClick={() => {
                  setMode('login')
                  setError(null)
                  setInfo(null)
                }}
                className={`flex-1 py-2 rounded-lg text-xs font-semibold transition-colors ${
                  mode === 'login'
                    ? 'bg-zinc-800 text-white shadow-sm'
                    : 'text-zinc-400 hover:text-white'
                }`}
              >
                Log in
              </button>
              <button
                type="button"
                onClick={() => {
                  setMode('register')
                  setError(null)
                  setInfo(null)
                }}
                className={`flex-1 py-2 rounded-lg text-xs font-semibold transition-colors ${
                  mode === 'register'
                    ? 'bg-zinc-800 text-white shadow-sm'
                    : 'text-zinc-400 hover:text-white'
                }`}
              >
                Sign up
              </button>
            </div>
          )}

          {mode === 'forgot' && (
            <div className="text-center space-y-1">
              <h2 className="text-base font-semibold text-white">Reset your password</h2>
              <p className="text-xs text-zinc-400">Enter your email and we'll send a 6-digit reset code.</p>
            </div>
          )}

          {mode === 'reset' && (
            <div className="text-center space-y-1">
              <h2 className="text-base font-semibold text-white">Enter Reset Code</h2>
              <p className="text-xs text-zinc-400">Enter the 6-digit code and your new password.</p>
            </div>
          )}

          {info && (
            <div className="bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs px-3.5 py-2.5 rounded-xl">
              {info}
            </div>
          )}

          {error && (
            <div className="bg-red-500/10 border border-red-500/20 text-red-400 text-xs px-3.5 py-2.5 rounded-xl">
              {error}
            </div>
          )}

          <form onSubmit={submit} className="space-y-3.5">
            {mode === 'register' && (
              <div>
                <label className="text-xs font-medium text-zinc-400 block mb-1">Your Name</label>
                <input
                  type="text"
                  placeholder="e.g. Alex"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  className="w-full bg-[#09090b] border border-zinc-800 focus:border-blue-500 rounded-xl px-3.5 py-2.5 text-white placeholder-zinc-600 outline-none text-sm transition-colors"
                />
              </div>
            )}

            <div>
              <label className="text-xs font-medium text-zinc-400 block mb-1">Email</label>
              <input
                type="email"
                required
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                disabled={mode === 'reset'}
                className="w-full bg-[#09090b] border border-zinc-800 focus:border-blue-500 rounded-xl px-3.5 py-2.5 text-white placeholder-zinc-600 outline-none text-sm transition-colors disabled:opacity-50"
              />
            </div>

            {(mode === 'login' || mode === 'register') && (
              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="text-xs font-medium text-zinc-400">Password</label>
                  {mode === 'login' && (
                    <button
                      type="button"
                      onClick={() => {
                        setMode('forgot')
                        setError(null)
                        setInfo(null)
                      }}
                      className="text-xs text-blue-400 hover:text-blue-300 transition-colors"
                    >
                      Forgot password?
                    </button>
                  )}
                </div>
                <input
                  type="password"
                  required
                  minLength={8}
                  placeholder="At least 8 characters"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full bg-[#09090b] border border-zinc-800 focus:border-blue-500 rounded-xl px-3.5 py-2.5 text-white placeholder-zinc-600 outline-none text-sm transition-colors"
                />
              </div>
            )}

            {mode === 'reset' && (
              <>
                <div>
                  <label className="text-xs font-medium text-zinc-400 block mb-1">6-Digit Reset Code</label>
                  <input
                    type="text"
                    required
                    maxLength={6}
                    placeholder="123456"
                    value={resetCode}
                    onChange={(e) => setResetCode(e.target.value)}
                    className="w-full bg-[#09090b] border border-zinc-800 focus:border-blue-500 rounded-xl px-3.5 py-2.5 text-white placeholder-zinc-600 outline-none text-sm font-mono tracking-widest text-center transition-colors"
                  />
                </div>
                <div>
                  <label className="text-xs font-medium text-zinc-400 block mb-1">New Password</label>
                  <input
                    type="password"
                    required
                    minLength={8}
                    placeholder="At least 8 characters"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    className="w-full bg-[#09090b] border border-zinc-800 focus:border-blue-500 rounded-xl px-3.5 py-2.5 text-white placeholder-zinc-600 outline-none text-sm transition-colors"
                  />
                </div>
              </>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full mt-2 py-2.5 bg-blue-600 hover:bg-blue-500 text-white font-semibold text-sm rounded-xl transition-colors active:scale-[0.99] disabled:opacity-50"
            >
              {loading
                ? 'Please wait…'
                : mode === 'login'
                ? 'Log in'
                : mode === 'register'
                ? 'Create account'
                : mode === 'forgot'
                ? 'Send reset code'
                : 'Set new password'}
            </button>

            {(mode === 'forgot' || mode === 'reset') && (
              <button
                type="button"
                onClick={() => {
                  setMode('login')
                  setError(null)
                  setInfo(null)
                }}
                className="w-full text-xs text-zinc-400 hover:text-white pt-2 transition-colors"
              >
                ← Back to login
              </button>
            )}
          </form>
        </div>

        {/* Clean Footer */}
        <div className="text-center text-xs text-zinc-500">
          Instagram-style messaging for language learning
        </div>
      </div>
    </div>
  )
}
