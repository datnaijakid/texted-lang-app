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
    refreshUser().finally(() => setCheckedAuth(true))
  }, [])

  if (!checkedAuth) {
    return (
      <div className="min-h-screen bg-[#09090b] flex items-center justify-center">
        <div className="w-8 h-8 rounded-full border-2 border-blue-500 border-t-transparent animate-spin" />
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
