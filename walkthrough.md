# Texted Production Hardening Walkthrough

## Summary of Accomplishments

Texted has been upgraded from an initial prototype to a hardened, production-ready MVP designed for deployment on **Vercel (Frontend)**, **FastAPI (Backend)**, **Neon (PostgreSQL)**, and **Stripe (Billing)**.

---

### 1. Database & Neon PostgreSQL Readiness
- **Database Engine & Pool**: Configured SQLAlchemy 2.0 with Neon serverless settings (`pool_pre_ping=True`, `pool_recycle=300`, `pool_size=10`, `max_overflow=20`), and automatic dialect normalization from `postgres://` to `postgresql://`.
- **Alembic Migrations**: Created a clean baseline migration (`60b14c524674_initial_production_schema.py`) that sets up all tables, foreign keys, and indexes from scratch on PostgreSQL or SQLite without depending on `create_all()`.
- **Performance Indexes**: Added targeted B-tree indexes across `users` (email, Stripe IDs), `conversations` (user_id, status, language_code), `messages` (conversation_id, created_at), `saved_words`, `daily_progress`, and verification/reset code lookup tables.

---

### 2. Authentication & Account Verification
- **Email Ownership Verification**:
  - Accounts are created with `email_verified=False`.
  - Cryptographically random 6-digit verification codes (`secrets.randbelow(900000) + 100000`).
  - Codes are stored as SHA-256 hashes (`code_hash`), with 10-minute expiry, max 5 failed attempts, and a 60-second cooldown between resends.
  - Integration with **EmailJS** REST API with safe fallback to console logging in development/test mode.
- **Secure Password Reset**:
  - Endpoint `POST /api/auth/forgot-password` generates single-use 6-digit reset codes (15-minute expiry).
  - Implements **account enumeration protection**: generic responses ensure non-existent accounts receive identical messaging.
  - Enforces password strength rules (8 to 72 bytes) and invalidates old sessions upon password change.
- **Session & Cookie Hardening**:
  - `HttpOnly`, `SameSite=Lax`, and configurable `Secure` cookies with fallback to `Authorization: Bearer <token>` for API clients.
  - `POST /api/auth/logout` clears session cookies.

---

### 3. Server-Enforced Stripe Paywall
- **No Client Spoofing**: Removed arbitrary `/api/usage/upgrade` endpoints. Pro status cannot be manipulated by client-side state.
- **Stripe Checkout**: `POST /api/billing/create-checkout-session` initializes server-authenticated sessions with metadata linking `user_id`.
- **Stripe Customer Portal**: `POST /api/billing/create-portal-session` allows active subscribers to manage payment methods and cancellations.
- **Authoritative Webhook Verification**: `POST /api/billing/webhook` strictly validates `stripe-signature` using `STRIPE_WEBHOOK_SECRET`. Idempotently processes `checkout.session.completed`, `customer.subscription.created`, `customer.subscription.updated`, `customer.subscription.deleted`, and `invoice.payment_failed`.

---

### 4. API Security & Rate Limiting
- **Production CORS**: Configured `CORSMiddleware` using `CORS_ORIGINS` from environment variables, eliminating wildcard headers with credentials.
- **Sliding-Window Rate Limiting**: Added `rate_limiter.py` protecting `/login` (10/min), `/register` (5/min), `/verify-email` (10/min), `/resend-verification` (3/min), `/forgot-password` (3/min), and `/reset-password` (5/min).
- **User Data Isolation**: Every conversation, message, and vocabulary query explicitly enforces `user_id == current_user.id`.
- **Health & Readiness Endpoints**: Added `GET /api/health` and `GET /api/ready` (with live DB connection verification).

---

### 5. Frontend & Vercel
- **Production Build**: Verified with `npm run build` in 1.12s.
- **Vercel Configuration**: Created `frontend/vercel.json` with SPA routing rewrites.
- **Verification UX**: Built `VerifyEmailScreen.jsx` with automatic 6-digit box focus, paste support, and cooldown timer.
- **Forgot Password UX**: Built into `AuthScreen.jsx` with step-by-step code and new password input.
- **Paywall UX**: Updated `UpgradeModal.jsx` to initiate Stripe Checkout and Customer Portal.

---

## Test Verification Results

All 15 automated unit and security tests passed cleanly:

```text
Ran 15 tests in 3.676s
OK
```
- `tests.test_dm_core`: 8/8 passed (onboarding, active conversation, messaging, corrections, persistence, free limits, Pro authorization, analytics).
- `tests.test_production_security`: 7/7 passed (unverified gates, code hashing, attempt limiting, password reset, enumeration protection, data isolation, webhook signature validation, health probes).
