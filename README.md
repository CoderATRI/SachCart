# SachCart 🛒✨
> Autonomous Checkout-Truth Agent & Dark Pattern Auditor

SachCart is an autonomous regulatory intelligence agent designed to uncover checkout deception, drip pricing, hidden fees, and dark patterns prohibited under India's **Central Consumer Protection Authority (CCPA) Guidelines 2023**.

Powered by **TinyFish Web Agent** for autonomous browser navigation, **Claude** for regulatory classification, and a fast, modern **FastAPI + Next.js** stack.

---

## 🎯 What SachCart Does

1. **Autonomous Checkout Walkthrough**: Navigates from product listing through cart and guest checkout using the TinyFish Web Agent without relying on fragile scrapers.
2. **CCPA 2023 Compliance Audit**: Detects 13 specified dark patterns plus deceptive price claims:
   - `false_urgency` (fake timers, fabricated scarcity messages)
   - `basket_sneaking` (pre-checked add-ons, unwanted warranties)
   - `confirm_shaming` (manipulative opt-out language)
   - `forced_action` (mandatory account creation / bundled requirements)
   - `subscription_trap` (hidden auto-renewals, difficult cancellation)
   - `interface_interference` (hidden opt-outs, disguised pre-selections)
   - `bait_and_switch` (unavailable listed variants)
   - `drip_pricing` (undisclosed convenience, packaging, or handling fees introduced late)
   - `disguised_advertisement` (sponsored content masked as organic recommendations)
   - `nagging` (repetitive intrusive prompts)
   - `trick_question` (confusing double-negative consent toggles)
   - `saas_billing` (unclear recurring billing terms)
   - `rogue_malware` (deceptive download triggers)
   - `price_claim` (inflated MRPs, fake discount percentage claims)
3. **Price Truth & Competitor Comparison**: Simultaneously queries TinyFish Search to extract prices for the identical product across competitor storefronts.
4. **Deal Integrity Score (0–100)**: Transparent 100-point deduction formula reflecting the audit findings.
5. **Real-Time Live Streaming**: Watch the AI agent navigate the storefront in real time via live video stream or SSE progress updates.

---

## 🏗️ Architecture & Tech Stack

- **Backend**: Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy 2 (async psycopg), Uvicorn.
- **Frontend**: Next.js 15 (App Router, TypeScript, pure CSS design system, 3D interactive tilt cards, SVG circular score dials).
- **Automation & Regulatory AI**:
  - [TinyFish Agent API](https://tinyfish.ai) (`stream_agent_walk`, `search_competitors`, `fetch_page_text`)
  - [Anthropic Claude](https://anthropic.com) (`claude-sonnet-5-5` fact extraction & CCPA classification)
- **Data & Caching**: PostgreSQL 16, Redis 7 (job queue, pub/sub SSE streaming, rate limiting), MinIO S3 (audit screenshots & evidence storage).
- **Telemetry**: OpenTelemetry distributed tracing spans across all external and internal operations.
- **Security**: SSRF protection with strict private/loopback IP blocking, IP rate limiting, and HMAC-authenticated API keys.

---

## 🚀 Quickstart

### Prerequisites
- Windows 11 / Linux / macOS
- Python 3.11+
- Node.js 18+ and npm
- Docker Desktop (daemon running)
- [TinyFish API Key](https://tinyfish.ai)
- [Anthropic API Key](https://console.anthropic.com)

### 1. Configuration
Copy `.env.example` to `.env` and fill in your API keys:

```bash
cp .env.example .env
```

```ini
TINYFISH_API_KEY=your_tinyfish_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here
```

### 2. Launch with One Command (Windows PowerShell)

```powershell
powershell -ExecutionPolicy Bypass -File .\start.ps1
```

`start.ps1` automatically:
1. Validates preflight prerequisites (Python, Node, Docker, ports 3000 & 8000).
2. Spawns PostgreSQL, Redis, and MinIO in Docker containers.
3. Initializes the database schema and S3 buckets.
4. Starts the FastAPI backend (`http://127.0.0.1:8000`), worker daemon, and Next.js frontend (`http://localhost:3000`).
5. Opens `http://localhost:3000` in your default browser.

---

## 📡 API Endpoints

- `POST /api/audits`: Submit product URL for asynchronous audit. Returns `202 Accepted` with audit UUID.
- `GET /api/audits/{id}`: Retrieve audit report, deal integrity score, findings, and competitor comparisons.
- `GET /api/audits/{id}/events`: Server-Sent Events (SSE) stream for live agent progress and streaming URLs.
- `POST /api/audits/{id}/watch`: Toggle weekly price and dark pattern monitoring.
- `GET /api/health`: Health status of database, Redis, and MinIO connections.

---

## 📜 Regulatory Standards Reference
This tool implements detection rules aligned with the **Guidelines for Prevention and Regulation of Dark Patterns, 2023** issued by the Central Consumer Protection Authority (CCPA), Ministry of Consumer Affairs, Food and Public Distribution, Government of India.