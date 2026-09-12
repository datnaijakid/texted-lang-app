import { useEffect, useState } from 'react'
import { api, setToken } from './api'
import AuthScreen from './pages/AuthScreen'
import VerifyEmailScreen from './pages/VerifyEmailScreen'
import DirectMessageScreen from './pages/DirectMessageScreen'
import OnboardingModal from './pages/OnboardingModal'

export default function App() {
  const [user, setUser] = useState(null)
  const [checkedAuth, setCheckedAuth] = useState(false)

  function refreshUser() {
    return api.me()
      .then(setUser)
      .catch(() => setUser(null))
  }

  async function handleLogout() {
    try {
      await api.logout()
    } catch (_) {}
    setToken(null)
    setUser(null)
  }

  useEffect(() => {
    const timer = setTimeout(() => {
      setCheckedAuth(true)
    }, 2000)

    refreshUser().finally(() => {
      clearTimeout(timer)
      setCheckedAuth(true)
    })

    return () => clearTimeout(timer)
  }, [])

  if (!checkedAuth) {
    return (
      <div className="min-h-screen bg-[#09090b] flex flex-col items-center justify-center gap-3">
        <div className="w-12 h-12 rounded-2xl bg-blue-600 flex items-center justify-center text-white text-2xl shadow-lg animate-pulse">
          💬
        </div>
        <div className="w-5 h-5 rounded-full border-2 border-blue-500 border-t-transparent animate-spin mt-1" />
      </div>
    )
  }

  if (!user) {
    return <AuthScreen onAuthed={refreshUser} />
  }

  // Mandatory email verification gate
  if (!user.email_verified) {
    return (
      <VerifyEmailScreen
        user={user}
        onVerified={refreshUser}
        onLogout={handleLogout}
      />
    )
  }

  if (!user.onboarding_completed) {
    return (
      <OnboardingModal
        user={user}
        onComplete={refreshUser}
      />
    )
  }

  return (
    <DirectMessageScreen
      user={user}
      onUserUpdated={setUser}
      onLogout={handleLogout}
    />
  )
}
