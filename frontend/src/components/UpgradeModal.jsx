import { useState } from 'react'
import { api } from '../api'

export default function UpgradeModal({ isOpen, onClose, currentTier, onTierChanged }) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const isPro = currentTier === 'pro'

  if (!isOpen) return null

  async function handleStartCheckout() {
    setLoading(true)
    setError(null)
    try {
      api.trackEvent('upgrade_clicked', { source: 'paywall_modal' })
      const res = await api.createCheckoutSession()
      if (res && res.checkout_url) {
        window.location.href = res.checkout_url
      } else {
        throw new Error('Could not initialize checkout. Please try again.')
      }
    } catch (err) {
      setError(err.message || 'Stripe Checkout is temporarily unavailable.')
      setLoading(false)
    }
  }

  async function handleOpenPortal() {
    setLoading(true)
    setError(null)
    try {
      const res = await api.createPortalSession()
      if (res && res.portal_url) {
        window.location.href = res.portal_url
      } else {
        throw new Error('Could not open billing portal.')
      }
    } catch (err) {
      setError(err.message || 'Unable to open billing portal.')
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="w-full max-w-md bg-[#121215] border border-zinc-800 rounded-2xl shadow-2xl overflow-hidden flex flex-col">
        {/* Modal Header */}
        <div className="p-6 border-b border-zinc-800 relative">
          <button
            onClick={onClose}
            className="absolute top-5 right-5 w-7 h-7 rounded-lg bg-zinc-800/80 hover:bg-zinc-700 flex items-center justify-center text-zinc-400 hover:text-white transition-colors text-xs"
          >
            ✕
          </button>
          <div className="inline-flex items-center px-2 py-0.5 rounded-md bg-blue-500/10 text-blue-400 text-xs font-semibold mb-2">
            PRO
          </div>
          <h2 className="text-xl font-bold text-white tracking-tight">
            Chat without limits
          </h2>
          <p className="text-xs text-zinc-400 mt-1">
            Keep your conversations going past the 20-message daily limit.
          </p>
        </div>

        {/* Benefits list */}
        <div className="p-6 space-y-5">
          <div className="space-y-3">
            {[
              {
                title: 'Unlimited Messages',
                desc: 'No daily limits or cutoffs on conversations.',
              },
              {
                title: 'All Language Partners',
                desc: 'Access Spanish, French, Italian, German, Japanese, and English personas.',
              },
              {
                title: 'Personalized Corrections',
                desc: 'In-character tips and natural texting alternatives.',
              },
              {
                title: 'Full Vocabulary Notebook',
                desc: 'Save words and phrases directly to your personal notebook.',
              },
            ].map((f, i) => (
              <div key={i} className="flex items-start gap-3">
                <div className="w-4 h-4 rounded-full bg-blue-500/20 text-blue-400 flex items-center justify-center text-[10px] font-bold mt-0.5 shrink-0">
                  ✓
                </div>
                <div>
                  <div className="text-sm font-medium text-white">{f.title}</div>
                  <div className="text-xs text-zinc-400 leading-relaxed">{f.desc}</div>
                </div>
              </div>
            ))}
          </div>

          {/* Pricing card */}
          <div className="p-4 rounded-xl bg-[#09090b] border border-zinc-800 flex items-center justify-between">
            <div>
              <div className="text-xs text-zinc-400">Monthly subscription</div>
              <div className="text-xl font-bold text-white">$9.99 <span className="text-xs font-normal text-zinc-400">/ month</span></div>
            </div>
            <div className="text-xs text-zinc-400 text-right">
              <div>Cancel anytime</div>
            </div>
          </div>

          {error && (
            <div className="bg-red-500/10 border border-red-500/20 text-red-400 text-xs px-3.5 py-2.5 rounded-xl">
              {error}
            </div>
          )}

          {/* Actions */}
          <div className="space-y-2 pt-1">
            {!isPro ? (
              <button
                onClick={handleStartCheckout}
                disabled={loading}
                className="w-full py-3 bg-white hover:bg-zinc-200 text-black font-semibold text-sm rounded-xl transition-colors active:scale-[0.99] disabled:opacity-50"
              >
                {loading ? 'Opening Stripe Checkout…' : 'Subscribe for $9.99/mo'}
              </button>
            ) : (
              <div className="space-y-2">
                <div className="text-center text-xs font-medium text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 py-2 rounded-xl">
                  ✓ Pro subscription is active
                </div>
                <button
                  onClick={handleOpenPortal}
                  disabled={loading}
                  className="w-full py-2.5 bg-zinc-800 hover:bg-zinc-700 text-zinc-200 rounded-xl text-xs font-semibold transition-colors"
                >
                  {loading ? 'Loading portal…' : 'Manage Subscription'}
                </button>
              </div>
            )}

            <button
              onClick={onClose}
              className="w-full py-2 text-xs text-zinc-500 hover:text-zinc-400 transition-colors"
            >
              Maybe later
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
