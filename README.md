# Karma Cleanse v2.1

> Emotional Bureaucracy & Administrative Absolution

A satirical bureaucratic web application that issues "karmic absolution certificates" through a multi-step ritual.

## ✨ Features

- 7-step funnel: Landing → Identity → Confession → Processing → Severity → Protocol → Certificate
- Severity classification (Low / Moderate / High / Critical)
- Registry IDs (`KR-2026-XX1234` format)
- QR-code certificates with public verification at `/verify/:registry_id`
- Two payment methods:
  - 💳 Card payments via Polar.sh (Merchant of Record)
  - 🦊 Direct USDC on Polygon via MetaMask
- Scheduled email delivery (Resend)
- Brutalist UI (IBM Plex Mono + Chivo)

## 🚀 Quick Start

### Backend
```bash
cd backend
pip install -r requirements.txt
# Configure backend/.env (see env section)
uvicorn server:app --reload --port 8001
```

### Frontend
```bash
cd frontend
yarn install
# Add REACT_APP_BACKEND_URL to frontend/.env
yarn start
```

## 🔐 Required Environment Variables

### Backend (`backend/.env`)
```
MONGO_URL=mongodb://localhost:27017
DB_NAME=karma_cleanse
CORS_ORIGINS=http://localhost:3000
BASE_URL=https://yourdomain.com

# Polar.sh
POLAR_ACCESS_TOKEN=polar_oat_...
POLAR_SERVER=production
POLAR_WEBHOOK_SECRET=polar_whs_...
POLAR_PRODUCT_STANDARD=...
POLAR_PRODUCT_PREMIUM=...
POLAR_PRODUCT_ENTERPRISE=...

# Crypto (Polygon USDC)
CRYPTO_RECIPIENT_ADDRESS=0x...
POLYGON_RPC_URL=https://polygon-bor-rpc.publicnode.com
USDC_CONTRACT_ADDRESS=0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359
POLYGON_CHAIN_ID=137

# Email (optional)
RESEND_API_KEY=re_...
SENDER_EMAIL=onboarding@resend.dev
```

### Frontend (`frontend/.env`)
```
REACT_APP_BACKEND_URL=https://yourdomain.com
```

## 🛠 Tech Stack

- **Frontend**: React 19, Zustand, Framer Motion, Tailwind, ethers.js v6
- **Backend**: FastAPI, Motor (MongoDB), web3.py
- **Payments**: Polar.sh, direct Polygon USDC
- **Email**: Resend

## 📋 Key API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/analyze` | Analyze confession → severity |
| POST | `/api/certificate` | Create certificate |
| GET | `/api/verify/{registry_id}` | Public verification |
| POST | `/api/polar/checkout` | Card payment via Polar |
| POST | `/api/crypto/verify` | Verify USDC tx |
| POST | `/api/delivery/schedule` | Schedule email |

## ⚠️ Disclaimer

> Karma Cleanse is not legally recognized in most jurisdictions.

This is a satirical art project. Not therapy. Not legal advice.

## 📜 License

MIT
