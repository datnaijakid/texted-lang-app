# Texted — Learn a Language by Texting an AI Friend

An AI friend you text with to build real conversational language skills. Designed to feel like **Instagram DMs** rather than a rigid classroom app.

> **Open app → receive a message → reply naturally → AI responds → AI corrects/teaches you → continue conversation.**

---

## Production Architecture

```text
                 ┌─────────────────────────────┐
                 │           Vercel            │
                 │   React 18 + Vite 5 (SPA)   │
                 └──────────────┬──────────────┘
                                │ HTTPS + HttpOnly Cookies
                                ↓
                 ┌─────────────────────────────┐
                 │       FastAPI Backend       │
                 │   (Render / Railway / Fly)  │
                 └──────────────┬──────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        ↓                       ↓                       ↓
┌──────────────┐        ┌──────────────┐        ┌──────────────┐
│     Neon     │        │    Stripe    │        │ LLM Provider │
│  PostgreSQL  │        │   Billing    │        │ OpenAI/Anth. │
└──────────────┘        └──────────────┘        └──────────────┘
                                │
                        ┌──────────────┐
                        │   EmailJS    │
                        │ Verification │
                        └──────────────┘
```

- **Frontend**: React 18, Vite 5, Tailwind CSS, Lucide icons deployed to **Vercel** with SPA rewrites (`vercel.json`).
- **Backend**: Python 3.11+, FastAPI, SQLAlchemy 2.0 with Neon PostgreSQL connection pooling, Alembic migrations, secure HttpOnly cookie sessions, and sliding-window rate limiting.
- **Database**: **Neon PostgreSQL** serverless database with connection recycling (`pool_recycle=300`, `pool_pre_ping=True`, `pool_size=10`).
- **Authentication**: Bcrypt password hashing (8–72 char enforcement), secure random 6-digit email ownership verification, password reset tokens hashed at rest (SHA-256), and account enumeration protection.
- **Payments & Paywall**: Real server-authoritative **Stripe Checkout** and **Stripe Billing Portal** with cryptographically verified webhook signatures (`stripe-signature`). Pro status is enforced strictly server-side.
- **Email Delivery**: **EmailJS** REST API integration with automatic fallback to local debug logging in development/test mode.

---

## Core Flow & Security Architecture

```text
User visits site → Sign up (email + password)
       ↓
Account created in unverified state (email_verified = False)
       ↓
Server generates secure random 6-digit code (hashed at rest with SHA-256, 10 min expiry)
       ↓
Email dispatched via EmailJS (or logged to terminal in dev)
       ↓
User enters 6-digit code on verification screen (rate limited to 5 attempts, 60s resend cooldown)
       ↓
Server verifies hash → Account activated (email_verified = True)
       ↓
User enters DM conversation & chats with AI persona
       ↓
Server validates input length (max 500 chars) & isolates user data strictly by user_id
       ↓
Server enforces free quota (20 messages/day)
       ↓
Limit reached → Server returns 429 → Client renders Pro paywall modal
       ↓
User clicks Continue with Pro → Server creates Stripe Checkout Session
       ↓
User completes payment on Stripe → Stripe sends signed webhook
       ↓
Server verifies signature via STRIPE_WEBHOOK_SECRET → Updates user subscription to Pro
       ↓
Unlimited messaging unlocked
```

---

## Environment Variables

### Backend (`backend/.env`)

Copy `backend/.env.example` to `backend/.env` and configure:

| Variable | Description | Example / Default |
| :--- | :--- | :--- |
| `ENVIRONMENT` | Runtime environment | `development` or `production` |
| `DATABASE_URL` | Neon PostgreSQL connection string (or SQLite for dev) | `postgresql://user:pass@ep-xyz.neon.tech/dbname?sslmode=require` |
| `JWT_SECRET` | Secret key for signing session tokens | Strong random 256-bit string |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Session validity duration | `1440` (24 hours) |
| `CORS_ORIGINS` | Comma-separated list of allowed frontend origins | `http://localhost:5173,https://your-texted-app.vercel.app` |
| `COOKIE_SECURE` | Enforce Secure attribute on cookies (set `True` on HTTPS) | `False` (dev) / `True` (production) |
| `COOKIE_SAMESITE` | Cookie SameSite policy | `lax` |
| `LLM_PROVIDER` | AI engine (`mock`, `openai`, `anthropic`) | `mock` (zero setup offline) or `openai` |
| `OPENAI_API_KEY` | OpenAI API Key (if `LLM_PROVIDER=openai`) | `sk-...` |
| `ANTHROPIC_API_KEY`| Anthropic API Key (if `LLM_PROVIDER=anthropic`)| `sk-ant-...` |
| `EMAILJS_SERVICE_ID`| EmailJS Service ID | Optional (falls back to console in dev) |
| `EMAILJS_TEMPLATE_ID`| EmailJS Template ID | Optional |
| `EMAILJS_PUBLIC_KEY`| EmailJS Public Key | Optional |
| `STRIPE_SECRET_KEY`| Stripe Secret Key | `sk_test_...` |
| `STRIPE_WEBHOOK_SECRET`| Stripe Webhook Secret (signing verification) | `whsec_...` |
| `STRIPE_PRICE_ID` | Stripe Recurring Price ID for Pro plan | `price_...` |
| `STRIPE_SUCCESS_URL`| Post-checkout redirect URL | `https://your-texted-app.vercel.app?upgraded=true` |
| `STRIPE_CANCEL_URL` | Checkout cancellation URL | `https://your-texted-app.vercel.app` |

### Frontend (`frontend/.env`)

| Variable | Description | Example |
| :--- | :--- | :--- |
| `VITE_API_URL` | Public HTTPS URL of the deployed FastAPI backend | `https://api.yourdomain.com` (leave blank in dev for localhost) |

> **Security Note**: Never expose Stripe secret keys, database credentials, or LLM keys in frontend environment variables.

---

## Local Development Setup

### 1. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows:
.\.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env

# Run database migrations
alembic upgrade head

# Seed languages and initial scenarios
python -m app.seed_data

# Start FastAPI server
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- API Health Check: http://127.0.0.1:8000/api/health
- API Readiness Check: http://127.0.0.1:8000/api/ready
- Interactive Swagger UI: http://127.0.0.1:8000/api/docs (available in non-production mode)

### 2. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

- Local Web App: http://localhost:5173

---

## Database Migrations (Neon PostgreSQL & SQLite)

Database schemas are managed using **Alembic**.

```bash
cd backend

# Apply migrations to database (PostgreSQL or SQLite)
alembic upgrade head

# Create a new migration after updating models.py
alembic revision --autogenerate -m "description_of_changes"
```

---

## Automated Test Suite

Run the full automated test suite covering authentication, verification, password resets, rate limiting, user data isolation, Stripe signature verification, and quota enforcement:

```bash
cd backend
.\.venv\Scripts\python.exe -m unittest discover tests
```

---

## Production Deployment Guide

### Deploying Frontend to Vercel

1. Push code to GitHub/GitLab.
2. Import repository into [Vercel](https://vercel.com).
3. Set **Root Directory** to `frontend`.
4. Build settings:
   - Framework: **Vite**
   - Build Command: `npm run build`
   - Output Directory: `dist`
5. Configure Environment Variable:
   - `VITE_API_URL`: Your backend API URL (e.g. `https://api.texted.app`).
6. Deploy!

### Deploying Backend to Render / Railway / Fly.io

1. Create a Python Web Service pointing to `backend/`.
2. Set build command:
   ```bash
   pip install -r requirements.txt && alembic upgrade head
   ```
3. Set start command:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port $PORT
   ```
4. Set environment variables from `backend/.env.example`, including your Neon `DATABASE_URL`, `STRIPE_SECRET_KEY`, and `CORS_ORIGINS`.
5. Point Stripe Webhook to: `https://api.yourdomain.com/api/billing/webhook` and copy the signing secret to `STRIPE_WEBHOOK_SECRET`.
