# Karma Cleanse v2.1 — PRD

## Original Problem Statement
Satirical bureaucratic web app — "Emotional Bureaucracy & Administrative Absolution". Multi-step funnel: Landing → Identity → Confession → Processing Ritual → Severity → Protocol Selection → Certificate (with QR code) → Optional scheduled email delivery. Brutalist design.

## Architecture
- **Frontend**: React 19 + React Router + Zustand v5 + Framer Motion + Tailwind + ethers.js v6
- **Backend**: FastAPI + Motor (async MongoDB) + web3.py (Polygon) + Polar SDK + Resend
- **Database**: MongoDB (collections: certificates, scheduled_deliveries, payment_transactions, processed_webhooks)
- **Payments**:
  - **Polar.sh** (card payments via Merchant of Record, Thailand-friendly)
  - **Direct MetaMask USDC on Polygon** (no intermediary, $0.01 gas)
  - NOWPayments backend kept dormant (300+ coin support requires $12+ minimum — not viable for $1/$3/$7 tiers; may revisit with higher tier)

## What's Been Implemented (2026-02-19)
### Backend API
- `POST /api/analyze` — confession severity analysis
- `POST /api/certificate` — create cert with UUID + Registry ID (KR-YYYY-XX####)
- `GET /api/certificate/{uuid}` — internal cert lookup
- `GET /api/verify/{registry_id}` — public verification (omits confession text)
- `POST /api/polar/checkout` + `GET /api/polar/status/{id}` + `POST /api/webhooks/polar` — card payments
- `POST /api/crypto/verify` + `POST /api/crypto/poll` + `GET /api/crypto/config` — direct USDC on Polygon
- `POST /api/nowpayments/invoice` + `POST /api/webhooks/nowpayments` — dormant (not exposed in UI)
- `POST /api/delivery/schedule` + `POST /api/delivery/send-now` — Resend email
- `POST /api/sketch/generate/{cert_uuid}` — fal.ai Flux Schnell sketch generation (paid tier only, idempotent)

### AI Watermark (2026-02-20)
- fal.ai Flux Schnell integration in `sketch_generator.py` generates a personalized minimalist line-art sketch for **paid tier** certificates
- Symbol selection: keyword match in confession (ghost, lie, cheat, forgot, etc.) → fallback to severity-class symbol set
- Deterministic seed (severity + confession length) → same confession yields same sketch
- Rendered as semi-transparent watermark (opacity 0.18, mix-blend-mode multiply) on `CertificateView.js` and `App.js` verification page
- Cached in `certificates.sketch_url` after first generation

### Frontend Pages
- Landing (animated counter, ministry seal)
- IdentityStep (name or anonymous)
- ConfessionStep (rotating placeholders, no AnimatePresence wrapper around textarea)
- ProcessingRitual (animated phrases, fake warning, 7s)
- SeverityResult (color-coded stamp, risk score, protocol)
- ProtocolSelection (4 tiers × 2 payment methods: Card + Direct USDC)
- CertificateView (QR code, share, schedule delivery)
- VerificationPage at `/verify/:registry_id`

### Design (Bureaucratic Brutalism)
- Off-white background (#F4F4F0), black text, red accent (#D92D20)
- Chivo (headings) + IBM Plex Mono (body) Google Fonts
- Red caret-color on input focus
- Color-coded severity stamps (green/grey/amber/red)

## Critical Bugs Fixed
1. **Zustand v5 destructuring** caused funnel to freeze at Confession → Processing. Fixed by switching to individual selectors.
2. **AnimatePresence wrapped textarea** caused cursor focus loss every 3 seconds during placeholder rotation. Removed wrapper.
3. **NOWPayments $12 minimum** prevented $1/$3/$7 crypto payments. Hidden from UI (kept in backend).
4. **Reown AppKit @wagmi/core conflict** with `./tempo` export. Reverted to plain ethers.js + window.ethereum (Reown removed completely).

## Configuration
### Required env vars (`/app/backend/.env`)
- `MONGO_URL`, `DB_NAME`, `CORS_ORIGINS`
- `STRIPE_API_KEY` (test, unused now that we use Polar)
- `RESEND_API_KEY` (placeholder — needs real key for email)
- `BASE_URL=https://cleansing-ritual.preview.emergentagent.com`
- **Polar**: `POLAR_ACCESS_TOKEN`, `POLAR_SERVER=production`, `POLAR_WEBHOOK_SECRET`, `POLAR_PRODUCT_*` (3 IDs)
- **Crypto**: `CRYPTO_RECIPIENT_ADDRESS=0x2c2ef0b3D27822Aac9093BB1218B5510618Bd28e`, `POLYGON_RPC_URL`, `USDC_CONTRACT_ADDRESS`, `POLYGON_CHAIN_ID=137`
- **NOWPayments** (dormant): `NOWPAYMENTS_API_KEY`, `NOWPAYMENTS_IPN_SECRET`, `NOWPAYMENTS_PAYOUT_CURRENCY=usdttrc20`

### Polar Setup
Three products created in user's Polar org (production):
- Standard ($1) — `abdb5109-541c-487d-b242-ad2d9b3a18f5`
- Premium ($3) — `146444ff-dc92-4139-9cde-8eae5470e820`
- Enterprise ($7) — `55ea5c5f-907a-44ea-9e0d-3827ed9741fb`

User must add webhook endpoint manually in Polar dashboard:
- URL: `https://cleansing-ritual.preview.emergentagent.com/api/webhooks/polar`
- Events: `order.paid`
- Replace `POLAR_WEBHOOK_SECRET` placeholder with generated secret

## Prioritized Backlog

- **Plisio** — crypto payment gateway, integrated 2026-02-20
- ✅ Plisio crypto payments (BTC, LTC, BCH, DOGE, USDT TRC/BEP, TRX, TON и др.) — заменил Cryptomus (отказ в модерации)

### P0 (Done)
- ✅ Full 7-step funnel
- ✅ Brutalist UI
- ✅ Polar card payments
- ✅ Plisio crypto payments (replaces failed Cryptomus moderation, 2026-02-20)
- ✅ QR-code certificates + public verification
- ✅ Persistent funnel store
- ✅ fal.ai personalized minimalist watermark for paid tier (verified visually 2026-02-20)
- ✅ Incident report (confession text) displayed on certificate and public verification

### P1 (Next)
- Get real Resend API key for email
- Background worker to actually send `scheduled_deliveries` at `send_at` timestamp
- Polar webhook secret configuration (user action)
- Replace `alert()` with sonner toasts
- Persist Zustand store in localStorage

### P2 (Future)
- Cryptomus integration for low-min crypto ($0.50 minimum)
- LLM confession analysis (Claude/GPT instead of keyword-based)
- Admin dashboard for certificates
- Social share OG-images
- Multi-language (RU/EN)
- PDF download of certificate
- TRON USDT direct integration

## Known Limitations
- Resend API key is placeholder — emails won't actually send
- No cron worker — scheduled emails are recorded only
- Polar webhook secret is placeholder — signatures are not verified (unsafe for prod)
- Stripe still in code path but UI uses Polar
- NOWPayments is in backend but UI buttons removed (min $12 not viable for our tiers)
