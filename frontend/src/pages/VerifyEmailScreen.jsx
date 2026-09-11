import { useState, useEffect, useRef } from 'react'
import { api, setToken } from '../api'

export default function VerifyEmailScreen({ user, onVerified, onLogout }) {
  const [code, setCode] = useState(['', '', '', '', '', ''])
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)
  const [resendCooldown, setResendCooldown] = useState(60)
  const [resendStatus, setResendStatus] = useState(null)
  const inputsRef = useRef([])

  useEffect(() => {
    if (resendCooldown <= 0) return
    const interval = setInterval(() => {
      setResendCooldown((prev) => prev - 1)
    }, 1000)
    return () => clearInterval(interval)
  }, [resendCooldown])

  function maskEmail(email = '') {
    const [name, domain] = email.split('@')
    if (!domain) return email
    const maskedName = name.length > 2 ? `${name[0]}***${name[name.length - 1]}` : `${name[0]}***`
    return `${maskedName}@${domain}`
  }

  function handleDigitChange(index, value) {
    if (value.length > 1) {
      const digits = value.replace(/\D/g, '').slice(0, 6).split('')
      const nextCode = [...code]
      digits.forEach((d, i) => {
        if (index + i < 6) nextCode[index + i] = d
      })
      setCode(nextCode)
      const targetIndex = Math.min(index + digits.length, 5)
      inputsRef.current[targetIndex]?.focus()
      return
    }

    const val = value.replace(/\D/g, '')
    const nextCode = [...code]
    nextCode[index] = val
    setCode(nextCode)

    if (val && index < 5) {
      inputsRef.current[index + 1]?.focus()
    }
  }

  function handleKeyDown(index, e) {
    if (e.key === 'Backspace' && !code[index] && index > 0) {
      inputsRef.current[index - 1]?.focus()
    }
  }

  async function handleVerify(e) {
    if (e) e.preventDefault()
    const fullCode = code.join('')
    if (fullCode.length !== 6) {
      setError('Please enter all 6 digits.')
      return
    }

    setError(null)
    setLoading(true)
    try {
      const res = await api.verifyEmail(user.email, fullCode)
      if (res && res.access_token) {
        setToken(res.access_token)
      }
      onVerified()
    } catch (err) {
      setError(err.message || 'Invalid or expired verification code.')
    } finally {
      setLoading(false)
    }
  }

  async function handleResend() {
    if (resendCooldown > 0 || loading) return
    setError(null)
    setResendStatus('Sending new code…')
    try {
      await api.resendVerification(user.email)
      setResendStatus('A fresh verification code has been sent!')
      setResendCooldown(60)
      setCode(['', '', '', '', '', ''])
      inputsRef.current[0]?.focus()
    } catch (err) {
      setError(err.message || 'Failed to resend code.')
      setResendStatus(null)
    }
  }

  return (
    <div className="min-h-screen bg-[#09090b] flex flex-col items-center justify-center px-4 py-8">
      <div className="w-full max-w-sm space-y-6">
        <div className="bg-[#121215] border border-zinc-800 rounded-2xl p-6 shadow-xl space-y-5 text-center">
          <div className="w-12 h-12 mx-auto rounded-xl bg-zinc-800 text-zinc-300 flex items-center justify-center text-xl">
            ✉️
          </div>

          <div className="space-y-1">
            <h2 className="text-xl font-bold text-white tracking-tight">
              Verify your email
            </h2>
            <p className="text-xs text-zinc-400">
              We sent a 6-digit verification code to
            </p>
            <div className="text-sm font-semibold text-zinc-200 font-mono">
              {maskEmail(user?.email)}
            </div>
          </div>

          {error && (
            <div className="bg-red-500/10 border border-red-500/20 text-red-400 text-xs px-3.5 py-2.5 rounded-xl text-left">
              {error}
            </div>
          )}

          {resendStatus && !error && (
            <div className="bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs px-3.5 py-2.5 rounded-xl text-left">
              {resendStatus}
            </div>
          )}

          <form onSubmit={handleVerify} className="space-y-5">
            {/* 6-digit PIN input */}
            <div className="flex justify-center gap-2">
              {code.map((digit, idx) => (
                <input
                  key={idx}
                  ref={(el) => (inputsRef.current[idx] = el)}
                  type="text"
                  inputMode="numeric"
                  maxLength={6}
                  value={digit}
                  onChange={(e) => handleDigitChange(idx, e.target.value)}
                  onKeyDown={(e) => handleKeyDown(idx, e)}
                  autoFocus={idx === 0}
                  className="w-11 h-13 bg-[#09090b] border border-zinc-800 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 rounded-xl text-center text-xl font-bold text-white outline-none transition-colors"
                />
              ))}
            </div>

            <button
              type="submit"
              disabled={loading || code.join('').length !== 6}
              className="w-full py-2.5 bg-blue-600 hover:bg-blue-500 text-white font-semibold text-sm rounded-xl transition-colors active:scale-[0.99] disabled:opacity-50"
            >
              {loading ? 'Verifying…' : 'Verify email'}
            </button>
          </form>

          {/* Resend & Switch Account */}
          <div className="space-y-2 pt-2 text-xs text-zinc-400 border-t border-zinc-800">
            <div>
              Didn't receive the code?{' '}
              {resendCooldown > 0 ? (
                <span className="text-zinc-500">Resend in {resendCooldown}s</span>
              ) : (
                <button
                  type="button"
                  onClick={handleResend}
                  className="text-blue-400 hover:text-blue-300 font-medium"
                >
                  Resend code
                </button>
              )}
            </div>

            {onLogout && (
              <div>
                <button
                  type="button"
                  onClick={onLogout}
                  className="text-zinc-500 hover:text-zinc-400"
                >
                  Sign in with another account
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
