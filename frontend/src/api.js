const BASE_URL = import.meta.env.VITE_API_URL !== undefined
  ? import.meta.env.VITE_API_URL
  : (import.meta.env.PROD ? '' : 'http://localhost:8000')

function getToken() {
  return localStorage.getItem('texted_token')
}

export function setToken(token) {
  if (token) localStorage.setItem('texted_token', token)
  else localStorage.removeItem('texted_token')
}

async function request(path, { method = 'GET', body, form } = {}) {
  const headers = {}
  const token = getToken()
  if (token) headers['Authorization'] = `Bearer ${token}`

  let payload
  if (form) {
    payload = new URLSearchParams(form)
    headers['Content-Type'] = 'application/x-www-form-urlencoded'
  } else if (body) {
    payload = JSON.stringify(body)
    headers['Content-Type'] = 'application/json'
  }

  const res = await fetch(`${BASE_URL}${path}`, {
    method,
    headers,
    body: payload,
    credentials: 'include', // Automatically send and receive HttpOnly session cookies
  })

  if (!res.ok) {
    let detail = 'Something went wrong'
    try {
      const data = await res.json()
      detail = data.detail || detail
    } catch (_) {}
    const err = new Error(detail)
    err.status = res.status
    throw err
  }

  if (res.status === 204) return null
  return res.json()
}

export const api = {
  // Authentication & Verification
  register: (payload) => request('/api/auth/register', { method: 'POST', body: payload }),
  login: (email, password) =>
    request('/api/auth/login', { method: 'POST', form: { username: email, password } }),
  logout: () => request('/api/auth/logout', { method: 'POST' }),
  verifyEmail: (email, code) =>
    request('/api/auth/verify-email', { method: 'POST', body: { email, code } }),
  resendVerification: (email) =>
    request('/api/auth/resend-verification', { method: 'POST', body: { email } }),
  forgotPassword: (email) =>
    request('/api/auth/forgot-password', { method: 'POST', body: { email } }),
  resetPassword: (email, code, new_password) =>
    request('/api/auth/reset-password', { method: 'POST', body: { email, code, new_password } }),
  me: () => request('/api/auth/me'),
  onboarding: (payload) => request('/api/auth/onboarding', { method: 'POST', body: payload }),
  updateProfile: (payload) => request('/api/auth/profile', { method: 'PUT', body: payload }),

  // Stripe Payments & Billing
  createCheckoutSession: (priceId = null) =>
    request('/api/billing/create-checkout-session', { method: 'POST', body: { price_id: priceId } }),
  createPortalSession: () =>
    request('/api/billing/create-portal-session', { method: 'POST' }),

  // DM Conversation Core
  getActiveConversation: () => request('/api/conversations/active'),
  sendChatMessage: (conversationId, content) =>
    request(`/api/conversations/${conversationId}/chat`, {
      method: 'POST',
      body: { content },
    }),
  resetConversation: () => request('/api/conversations/reset', { method: 'POST' }),
  translateMessage: (text, targetLanguageCode) =>
    request('/api/conversations/translate', {
      method: 'POST',
      body: { text, target_language_code: targetLanguageCode },
    }),

  // Usage & Subscription
  getUsage: () => request('/api/usage'),

  // Analytics
  trackEvent: (eventName, properties = {}) =>
    request('/api/analytics/event', { method: 'POST', body: { event_name: eventName, properties } }).catch(() => {}),

  // Vocabulary Notebook
  getNotebook: () => request('/api/vocabulary/notebook'),
  saveFavoriteWord: (vocabularyId) =>
    request(`/api/vocabulary/notebook/${vocabularyId}/favorite`, { method: 'POST' }),
  saveCustomWord: (term, translation, languageCode) =>
    request('/api/vocabulary/save-custom', {
      method: 'POST',
      body: { term, translation, language_code: languageCode },
    }),

  // Progress
  getProgress: () => request('/api/progress'),
}
