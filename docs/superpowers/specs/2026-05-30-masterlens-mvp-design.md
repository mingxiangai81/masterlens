# MasterLens MVP Full-Stack Design Spec

**Date:** 2026-05-30
**Status:** Approved
**Scope:** Complete MVP — AI analysis engine, financial data, RAG citations, user system + payments

---

## 1. Overview

MasterLens is a bilingual (CN/EN) AI investment analysis platform that generates "master verdicts" — independent evaluations of any stock through the frameworks of 10 legendary investors (Buffett, Graham, Lynch, Munger, Fisher, Greenblatt, Dalio, Wood, Bogle + portfolio review).

The MVP delivers: input a stock ticker, get a full Wall Street-grade report with master verdicts, financial analysis, and an educational trade plan — all with cited data sources.

## 2. Tech Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Frontend | React 18 + Vite + TailwindCSS | Fast dev, existing landing page styles preserved |
| Backend | Python 3.11+ / FastAPI | Async, high-performance, great AI/data ecosystem |
| AI Engine | Google Gemini API (AI Studio) | Free tier for MVP, user already has access |
| Financial Data | yfinance (primary) + Alpha Vantage (supplementary) | Free, covers US/HK/CN markets |
| Database | Supabase (PostgreSQL) | User has Supabase MCP, handles auth + DB + storage |
| Vector DB | Supabase pgvector extension | RAG citations without extra infra |
| Payments | Stripe Checkout + Webhooks | Industry standard, supports subscriptions + one-time |
| Frontend Deploy | Vercel | User has Vercel MCP |
| Backend Deploy | Railway or Render | Free tier available, Python-friendly |

## 3. System Architecture

```
Browser (React SPA)
    |
    v
FastAPI Backend (Python)
    |
    +---> Gemini API (AI verdicts generation)
    |
    +---> yfinance / Alpha Vantage (financial data)
    |
    +---> Supabase PostgreSQL
    |         +---> users table
    |         +---> reports table (JSONB cached reports)
    |         +---> watchlist table
    |         +---> master_verdicts table
    |         +---> embeddings table (pgvector, for RAG)
    |
    +---> Stripe API (payments + webhooks)
```

## 4. Sub-System Designs

### 4.1 AI Analysis Engine (P1 — Core)

**Endpoint:** `GET /api/analyze/{ticker}?lang=zh|en`

**Flow:**
1. Check cache: if a report for this ticker exists and is < 24 hours old, return it
2. Fetch financial data via yfinance: price, PE, PB, PEG, FCF, ROE, debt ratio, revenue growth, market cap, dividend yield, EPS history, balance sheet summary
3. Build structured prompt for Gemini with the real financial data injected
4. Request Gemini to generate 10 independent master verdicts, each in the master's voice/style
5. Parse response into structured JSON
6. Generate consensus score (weighted average of 10 verdicts)
7. Generate Wall Street report sections: business model, financial health, moat score (1-10), DCF valuation, bull/bear debate, earnings analysis
8. Generate educational trade plan: entry price range, stop-loss logic, position sizing suggestion, time horizon
9. Cache full report to Supabase
10. Return structured JSON response

**Master Verdict Schema (per master):**
```json
{
  "master_name": "Warren Buffett",
  "master_name_zh": "沃伦·巴菲特",
  "framework": "Owner Earnings Model",
  "framework_zh": "所有者收益模型",
  "verdict": "buy|hold|pass",
  "score": 8.5,
  "reasoning_en": "...",
  "reasoning_zh": "...",
  "key_metric": "Owner Earnings Yield: 4.2%"
}
```

**Full Report Schema:**
```json
{
  "ticker": "AAPL",
  "company_name": "Apple Inc.",
  "price": 198.36,
  "currency": "USD",
  "exchange": "NASDAQ",
  "generated_at": "2026-05-30T12:00:00Z",
  "language": "zh",
  "master_verdicts": [...],
  "consensus": {
    "score": 7.2,
    "buy_count": 3,
    "hold_count": 2,
    "pass_count": 1,
    "summary_en": "...",
    "summary_zh": "..."
  },
  "wall_street_report": {
    "business_model": "...",
    "financial_health": { "score": 8, "details": "..." },
    "moat": { "score": 7, "type": "Brand + Ecosystem", "details": "..." },
    "dcf_valuation": { "fair_value": 185, "upside": "-7%", "assumptions": "..." },
    "bull_case": "...",
    "bear_case": "...",
    "earnings_analysis": "..."
  },
  "trade_plan": {
    "disclaimer": "Educational content only, not investment advice",
    "entry_range": { "low": 180, "high": 190 },
    "stop_loss": { "price": 170, "logic": "Below 200-day MA" },
    "take_profit": [{ "price": 210, "ratio": "50%" }, { "price": 230, "ratio": "50%" }],
    "position_size": "Max 5% of portfolio",
    "time_horizon": "12-18 months"
  },
  "data_sources": [
    { "label": "Apple 10-K FY2024", "field": "revenue" },
    { "label": "yfinance real-time", "field": "price" }
  ]
}
```

### 4.2 Financial Data Integration (P2)

**Module:** `services/financial_data.py`

**Primary source — yfinance (free, no API key):**
- `yf.Ticker(symbol).info` — price, PE, PB, market cap, sector
- `yf.Ticker(symbol).financials` — income statement
- `yf.Ticker(symbol).balance_sheet` — assets, liabilities
- `yf.Ticker(symbol).cashflow` — FCF, capex
- `yf.Ticker(symbol).history()` — price history for technical analysis

**Supplementary — Alpha Vantage (free tier, 25 calls/day):**
- News sentiment for the ticker
- Earnings calendar

**Caching strategy:**
- Financial data cached in Supabase `financial_cache` table
- TTL: price data = 15 minutes, fundamentals = 24 hours
- Reduces API calls and speeds up repeat analyses

**Market support:**
- US stocks: ticker as-is (AAPL, TSLA)
- HK stocks: append .HK (0700.HK, 9988.HK)
- CN stocks: append .SS/.SZ (600519.SS, 000858.SZ)

### 4.3 RAG Citation System (P3)

**MVP approach (simplified):**

Phase 1 (MVP): Prompt-injected citations
- Inject real financial numbers from yfinance into the Gemini prompt
- Instruct Gemini to cite these numbers with source labels
- Every number in the report tagged with `data_sources` array
- This gives "soft RAG" — real data cited, but not from actual document embeddings

Phase 2 (post-MVP): Full RAG pipeline
- Fetch 10-K/20-F filings from SEC EDGAR API
- Chunk documents, generate embeddings via Gemini Embedding API
- Store in Supabase pgvector (`embeddings` table)
- At analysis time, retrieve relevant chunks and inject into prompt
- Citations link to specific pages/sections of actual filings

**Embeddings table schema:**
```sql
CREATE TABLE embeddings (
  id BIGSERIAL PRIMARY KEY,
  ticker VARCHAR(20) NOT NULL,
  source_type VARCHAR(50), -- '10-K', '10-Q', 'earnings_call'
  source_label TEXT, -- 'Apple 10-K FY2024, p.31'
  chunk_text TEXT NOT NULL,
  embedding vector(768),
  created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX ON embeddings USING ivfflat (embedding vector_cosine_ops);
```

### 4.4 User System + Payments (P4)

**Authentication:** Supabase Auth
- Email + password registration/login
- Google OAuth (one-click sign in)
- JWT tokens for API authentication

**Database Schema:**

```sql
-- Users (extends Supabase auth.users)
CREATE TABLE public.profiles (
  id UUID PRIMARY KEY REFERENCES auth.users(id),
  display_name TEXT,
  plan TEXT DEFAULT 'free' CHECK (plan IN ('free', 'single', 'pro', 'lifetime')),
  reports_used_this_month INT DEFAULT 0,
  reports_reset_at TIMESTAMPTZ DEFAULT NOW(),
  stripe_customer_id TEXT,
  language_pref TEXT DEFAULT 'zh',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Cached reports
CREATE TABLE public.reports (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES public.profiles(id),
  ticker VARCHAR(20) NOT NULL,
  language TEXT DEFAULT 'zh',
  report_data JSONB NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  expires_at TIMESTAMPTZ -- for single-report purchases (30 days)
);

-- Watchlist
CREATE TABLE public.watchlist (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES public.profiles(id),
  ticker VARCHAR(20) NOT NULL,
  added_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(user_id, ticker)
);

-- Purchase history
CREATE TABLE public.purchases (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES public.profiles(id),
  stripe_session_id TEXT,
  product_type TEXT CHECK (product_type IN ('single_report', 'pro_monthly', 'pro_annual', 'lifetime')),
  amount_cents INT,
  currency TEXT DEFAULT 'usd',
  status TEXT DEFAULT 'pending',
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Stripe Integration:**
- `POST /api/checkout/single-report` — creates Stripe Checkout session for $9
- `POST /api/checkout/subscribe` — creates subscription checkout ($19/mo or $179/yr)
- `POST /api/checkout/lifetime` — one-time $299 payment
- `POST /api/webhook/stripe` — handles payment confirmation, updates user plan

**Free tier limits:**
- 3 reports per month (tracked by `reports_used_this_month`, reset monthly)
- 10 watchlist items max
- 2 master quick verdicts per month
- Full report content visible, but detailed reasoning locked (soft paywall)

**Paywall triggers:**
- 4th report request → upgrade prompt
- 11th watchlist item → upgrade prompt
- First "trade plan" click → hard upgrade gate
- Full master reasoning → soft lock (show conclusion, hide reasoning)

## 5. API Routes

```
# Auth
POST   /api/auth/register          — email + password signup
POST   /api/auth/login             — email + password login
POST   /api/auth/google            — Google OAuth callback
GET    /api/auth/me                — current user profile

# Analysis (core)
GET    /api/analyze/{ticker}       — generate full report (?lang=zh|en)
GET    /api/quote/{ticker}         — quick price + basic metrics
GET    /api/masters/{ticker}       — master verdicts only (quick view)

# Watchlist
GET    /api/watchlist              — list user watchlist
POST   /api/watchlist/{ticker}     — add to watchlist
DELETE /api/watchlist/{ticker}     — remove from watchlist

# Reports
GET    /api/reports                — list user's past reports
GET    /api/reports/{id}           — get specific report

# Payments
POST   /api/checkout/single-report — Stripe checkout for $9 single report
POST   /api/checkout/subscribe     — Stripe checkout for Pro subscription
POST   /api/checkout/lifetime      — Stripe checkout for $299 lifetime
POST   /api/webhook/stripe         — Stripe webhook handler

# Admin
GET    /api/health                 — health check
```

## 6. Frontend Pages

| Route | Page | Description |
|-------|------|-------------|
| `/` | Landing | Existing landing page converted to React component |
| `/login` | Auth | Login / Register with email or Google |
| `/analyze/:ticker` | Report | Full report view: master verdicts + Wall Street report + trade plan |
| `/dashboard` | Dashboard | User's watchlist + report history + usage stats |
| `/pricing` | Pricing | Pricing page with Stripe checkout buttons |

## 7. Project Structure

```
masterlens/
├── frontend/                  # React + Vite
│   ├── src/
│   │   ├── components/
│   │   │   ├── Landing.jsx         # Existing landing page as component
│   │   │   ├── Navbar.jsx
│   │   │   ├── MasterVerdict.jsx   # Single master card
│   │   │   ├── VerdictGrid.jsx     # All master verdicts
│   │   │   ├── ConsensusScore.jsx  # Consensus visualization
│   │   │   ├── WallStreetReport.jsx
│   │   │   ├── TradePlan.jsx
│   │   │   ├── TickerInput.jsx
│   │   │   ├── WatchlistPanel.jsx
│   │   │   ├── PricingCard.jsx
│   │   │   └── PaywallGate.jsx
│   │   ├── pages/
│   │   │   ├── Home.jsx
│   │   │   ├── Analyze.jsx
│   │   │   ├── Dashboard.jsx
│   │   │   ├── Pricing.jsx
│   │   │   └── Login.jsx
│   │   ├── services/
│   │   │   ├── api.js              # Axios API client
│   │   │   └── supabase.js         # Supabase client for auth
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── index.html
│   ├── tailwind.config.js
│   ├── vite.config.js
│   └── package.json
│
├── backend/                   # Python FastAPI
│   ├── app/
│   │   ├── main.py                 # FastAPI app, CORS, routes
│   │   ├── config.py               # Environment variables
│   │   ├── routes/
│   │   │   ├── analysis.py         # /api/analyze, /api/quote, /api/masters
│   │   │   ├── auth.py             # /api/auth/*
│   │   │   ├── watchlist.py        # /api/watchlist/*
│   │   │   ├── reports.py          # /api/reports/*
│   │   │   └── payments.py         # /api/checkout/*, /api/webhook/stripe
│   │   ├── services/
│   │   │   ├── gemini_engine.py    # Gemini API calls + prompt engineering
│   │   │   ├── financial_data.py   # yfinance + Alpha Vantage
│   │   │   ├── master_prompts.py   # 10 master framework prompts
│   │   │   ├── report_builder.py   # Assembles full report from parts
│   │   │   ├── rag_service.py      # Citation/embedding logic
│   │   │   └── stripe_service.py   # Stripe checkout + webhook
│   │   ├── models/
│   │   │   ├── schemas.py          # Pydantic models
│   │   │   └── database.py         # Supabase client
│   │   └── prompts/
│   │       ├── buffett.py          # Buffett framework prompt
│   │       ├── graham.py           # Graham framework prompt
│   │       ├── lynch.py            # Lynch framework prompt
│   │       ├── munger.py           # Munger framework prompt
│   │       ├── fisher.py           # Fisher framework prompt
│   │       ├── greenblatt.py       # Greenblatt framework prompt
│   │       ├── dalio.py            # Dalio framework prompt
│   │       ├── wood.py             # Wood framework prompt
│   │       ├── bogle.py            # Bogle framework prompt
│   │       └── wall_street.py      # Wall Street report + trade plan prompt
│   ├── requirements.txt
│   ├── .env.example
│   └── Dockerfile
│
├── docs/
│   └── superpowers/specs/
│       └── 2026-05-30-masterlens-mvp-design.md
│
├── index.html                 # Original landing page (kept as reference)
└── README.md
```

## 8. Environment Variables

```
# Backend (.env)
GEMINI_API_KEY=...
SUPABASE_URL=...
SUPABASE_SERVICE_KEY=...
STRIPE_SECRET_KEY=...
STRIPE_WEBHOOK_SECRET=...
ALPHA_VANTAGE_API_KEY=...         # Optional, free tier
FRONTEND_URL=http://localhost:5173 # CORS origin

# Frontend (.env)
VITE_API_URL=http://localhost:8000
VITE_SUPABASE_URL=...
VITE_SUPABASE_ANON_KEY=...
VITE_STRIPE_PUBLISHABLE_KEY=...
```

## 9. MVP Scope Boundaries

**In scope (MVP):**
- Single stock analysis with 10 master verdicts
- Wall Street report (business model, DCF, moat, bull/bear)
- Educational trade plan
- Bilingual output (zh/en)
- User registration + login
- Free tier (3 reports/month) + paywall
- Stripe payment (all 4 tiers)
- Report caching (24h)
- Basic watchlist
- Soft RAG (prompt-injected real data with source labels)

**Out of scope (post-MVP):**
- Full RAG with document embeddings from SEC filings
- Portfolio X-Ray (multi-stock analysis)
- Community features
- Public performance tracking
- Real-time price alerts
- Mobile app
- A-stock market support (regulatory complexity)
