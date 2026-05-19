# Karma Cleanse v2.1 — Product Requirements Document

## Original Problem Statement
Sаtirical bureaucratic web app — "Emotional Bureaucracy & Administrative Absolution". Users go through a funnel: Landing → Identity Registry → Incident Declaration → Processing Ritual → Severity Classification → Protocol Selection (free/paid) → Certificate (with QR code) → Optional Scheduled Email Delivery. Tone: serious, bureaucratic, absurd. Design: Brutalist (light theme, off-white background, black text, red accents, monospace fonts).

## Architecture
- **Frontend**: React 19 + React Router + Zustand v5 + Framer Motion + Tailwind CSS
- **Backend**: FastAPI + Motor (async MongoDB)
- **Database**: MongoDB (collections: certificates, scheduled_deliveries, payment_transactions)
- **Payment**: Stripe via `emergentintegrations` library (test key configured)
- **Email**: Resend (placeholder API key — needs real key for production email delivery)
- **Design**: Bureaucratic Brutalism — Chivo (headings) + IBM Plex Mono (body)

## User Personas
- **Anonymous Confessor**: wants quick absurd emotional release without giving real identity
- **Named Subject**: wants a registered certificate they can share/keep
- **Premium User**: wants permanent certified absolution with QR verification

## Core Requirements (Static)
1. Multi-step funnel with state management (Zustand)
2. Severity analysis via keyword-based algorithm (no LLM in MVP)
3. Registry ID generation: KR-YYYY-XX#### format
4. Stripe checkout with 3 paid tiers ($1, $3, $7) + free tier
5. Public verification page at `/verify/:registry_id`
6. Scheduled email delivery (1-168 hours delay)
7. QR code on certificates linking to verification page

## What's Been Implemented (2026-02-19)
### Backend API Endpoints
- `POST /api/analyze` — analyzes confession text, returns severity classification
- `POST /api/certificate` — creates certificate with UUID + Registry ID
- `GET /api/certificate/{uuid}` — fetches certificate by UUID
- `GET /api/verify/{registry_id}` — public verification (excludes confession text)
- `POST /api/checkout/session` — creates Stripe checkout for paid tier
- `GET /api/checkout/status/{session_id}` — polls payment status
- `POST /api/webhook/stripe` — handles Stripe webhook events
- `POST /api/delivery/schedule` — schedules email delivery
- `POST /api/delivery/send-now` — immediate email send (Resend)

### Frontend Pages/Components
- Landing — ministry seal, animated live counter, CTA button
- IdentityStep — name input + "Remain Anonymous" button
- ConfessionStep — textarea with rotating placeholders, char count (0-500)
- ProcessingRitual — 7-second animation, progress bar, fake warning sequence
- SeverityResult — color-coded CLASS stamp (Low/Mod/High/Critical), risk score, protocol, diagnostics
- ProtocolSelection — 4 tier cards (Free/$1/$3/$7)
- CertificateView — full certificate with QR code, share, schedule delivery
- VerificationPage — public route at `/verify/:registry_id`

### Design (Bureaucratic Brutalism)
- Off-white background (#F4F4F0), black text, red accent (#D92D20)
- Chivo (headings, uppercase, font-black), IBM Plex Mono (body)
- Sharp rounded-none borders, no shadows
- Color-coded severity stamps (green/grey/amber/red)
- Ministry of Karma Cleanse official seal asset

## Test Results
- **Backend**: 12/12 pytest tests PASS (100%)
- **Frontend**: Full free-tier funnel works end-to-end (Landing → Certificate → Verification)
- **Stripe**: Checkout endpoint verified, returns 200 + redirect URL
- **Bug fixed**: Zustand v5 incompatibility (individual selectors required)

## Prioritized Backlog

### P0 (Done)
- ✅ Full funnel UI
- ✅ Backend APIs with MongoDB
- ✅ Stripe integration (test mode)
- ✅ QR code certificates
- ✅ Public verification page
- ✅ Brutalist design

### P1 (Future)
- Provide real Resend API key for actual email sending
- Replace `alert()` with toast notifications (sonner is already installed)
- Add React StrictMode guard against double /api/analyze call (use AbortController/ref)
- Persist funnel state in localStorage (currently resets on refresh)
- Add error UI on certificate creation failure / checkout failure
- Background cron worker to process `scheduled_deliveries` (currently records only)

### P2 (Nice to Have)
- LLM-based confession analysis (GPT/Claude) instead of keyword-based
- Admin dashboard for viewing certificates
- Social sharing previews (OG images)
- Internationalization (English + Russian)
- Certificate download as PDF
- Email template customization per tier
- Analytics tracking (PostHog/Vercel Analytics)

## Known Limitations
- Resend API key is placeholder — actual email sending will fail (records still saved)
- StrictMode causes double API calls in dev (harmless, doesn't affect production)
- No cron worker yet — scheduled deliveries stored but not auto-sent
- Stripe redirects to external page (paid tier path not auto-tested e2e)
