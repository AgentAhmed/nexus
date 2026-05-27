# NEXUS — Meeting-to-Action Intelligence Platform

> Turn every enterprise meeting into autonomous executed outcomes.  
> **Not just transcription. Not just summaries. Actual actions taken.**

[![License: MIT](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11+-blue)](https://python.org)
[![LiteLLM](https://img.shields.io/badge/LLM-Any_Provider-purple)](https://litellm.ai)

---

## The Problem — $37 Trillion of Wasted Work

- **31 hours** per month per employee spent in meetings
- **70% of action items** from meetings are never completed  
- **$37 trillion** lost annually to poor workplace productivity (Gallup)
- Current tools like Otter.ai and Fireflies **only transcribe** — they stop at the meeting door

The gap: someone still has to read the transcript, extract tasks, assign owners, create tickets, and send updates. That person is you. Every. Single. Time.

---

## The Solution — NEXUS

NEXUS is a **multi-agent AI platform** that closes the loop automatically:

```
Meeting audio / transcript
        ↓
[ Voice Agent ]       → Real-time transcription, speaker identification
        ↓
[ Intent Agent ]      → Extracts decisions, action items, domain classification
        ↓
[ Context Agent ]     → Retrieves relevant enterprise knowledge (RAG)
        ↓
[ Domain Expert ]     → Legal / Finance / HR / Ops / Sales / Marketing specialist
        ↓
  High confidence?  ──yes──→ [ Execution Agent ] → Jira / Slack / Linear / Notion
        │ no
        ↓
  [ Human Approval Gate ] → dashboard shows items needing your sign-off
        ↓
[ Live Dashboard ]    → Real-time agent activity, decisions, metrics
```

**One meeting → everything done. No manual follow-up.**

---

## Why NEXUS is Different

| Feature | Otter.ai | Fireflies | Gong | **NEXUS** |
|---|---|---|---|---|
| Transcription | ✅ | ✅ | ✅ | ✅ |
| Summarisation | ✅ | ✅ | ✅ | ✅ |
| Action item detection | ⚠ basic | ⚠ basic | ✅ | ✅ |
| Domain expert analysis | ❌ | ❌ | Sales only | ✅ 6 domains |
| Autonomous execution | ❌ | ❌ | ❌ | ✅ |
| Approval gate | ❌ | ❌ | ❌ | ✅ |
| Self-hostable | ❌ | ❌ | ❌ | ✅ |
| Provider-agnostic LLM | ❌ | ❌ | ❌ | ✅ |
| Open source | ❌ | ❌ | ❌ | ✅ |

---

## Quick Start — Runs in 5 Minutes

### Minimum required: one free API key

```bash
# 1. Get a free Groq API key at console.groq.com (takes 30 seconds)
# 2. Clone and run

git clone https://github.com/YOUR_USERNAME/nexus.git
cd nexus
make setup          # installs everything
# Edit .env → add GROQ_API_KEY=your_key_here
make dev            # starts API + dashboard
```

Open http://localhost:3000 → click **Demo** → see NEXUS in action.

### Or with Docker (no Python setup needed)

```bash
git clone https://github.com/YOUR_USERNAME/nexus.git && cd nexus
cp .env.example .env   # add GROQ_API_KEY
docker compose -f docker-compose.free.yml up -d
```

---

## Supported Providers — Change One Line, Switch Everything

```env
# In .env — switch LLM provider without touching any code:

PRIMARY_MODEL=groq/llama-3.3-70b-versatile    # free, fast ← default
PRIMARY_MODEL=gemini/gemini-2.0-flash-exp      # free, Google latest
PRIMARY_MODEL=openai/gpt-4o-mini               # paid, excellent
PRIMARY_MODEL=anthropic/claude-3-5-haiku-20241022  # paid
PRIMARY_MODEL=ollama/llama3.2                  # local, 100% free, no internet
```

Speech-to-Text:
```env
STT_PROVIDER=groq     # Groq Whisper API (free) ← default
STT_PROVIDER=local    # faster-whisper on CPU (free, no key)
STT_PROVIDER=openai   # OpenAI Whisper API
```

---

## Tech Stack

| Layer | Technology | Why |
|---|---|---|
| Agent orchestration | LangGraph | Stateful, resumable multi-agent graphs |
| LLM (any provider) | LiteLLM | One API for 100+ LLM providers |
| Voice/STT | Groq Whisper / faster-whisper | Free options available |
| Vector store | ChromaDB (local) | Zero-setup, file-based, portable |
| Backend | FastAPI + WebSocket | Async, real-time |
| Frontend | Next.js 14 + Tailwind | Fast, modern |
| Deployment | Docker + any cloud | AWS, Railway, Render, DigitalOcean |

---

## Integrations

**Execution channels** (add as many as you use):

| Integration | What it does |
|---|---|
| Slack | Posts action items to your channels |
| Jira | Creates tickets with domain-based priority |
| Linear | Creates issues (great for engineering/product teams) |
| Notion | Adds tasks to your database |
| Webhook | Generic — connects to Zapier, Make, n8n, anything |

---

## Deployment

### Local (WSL / Mac / Linux)
```bash
make setup && make dev
```

### AWS EC2 Free Tier (12 months free)
```bash
# On your EC2 instance (Ubuntu 22.04, t2.micro or t3.small):
REPO_URL=https://github.com/YOUR_USERNAME/nexus.git bash deploy/setup-aws.sh
```

### Railway (free $5/month credit, easiest)
```bash
railway init && railway up
```

### Render / Fly.io
Works with the included Dockerfile. Set env vars in their dashboard.

---

## API Reference

```
GET  /api/health          Health check + version
GET  /api/metrics         Live agent performance stats
POST /api/process         Process a meeting transcript
POST /api/upload-audio    Upload audio file → auto-transcribe → process
POST /api/ingest-docs     Add PDFs/DOCX/TXT to knowledge base
POST /api/demo            Run built-in demo (no API key needed for this)
POST /api/approve         Approve a pending action item

WS  /ws/dashboard         Real-time dashboard feed (metrics + results)
WS  /ws/voice/{id}        Stream live audio for real-time transcription
```

---

## Architecture — How the Agents Work

```
NexusState (LangGraph)
├── extract_intent       → fast LLM: domain, actions, decisions, confidence
├── retrieve_context     → ChromaDB RAG: pull relevant enterprise knowledge
├── domain_agent         → smart LLM: expert analysis per domain
│   ├── LegalAgent       → compliance, contracts, regulatory risk
│   ├── FinanceAgent     → budget, ROI, spend approval
│   ├── HRAgent          → headcount, performance, employment law
│   ├── OpsAgent         → project delivery, vendor management
│   ├── SalesAgent       → pipeline, CRM, deal strategy
│   └── MarketingAgent   → campaigns, content, growth
├── [if confidence ≥ 70%] execute → Slack / Jira / Linear / Notion / Webhook
└── [if confidence < 70%] flag_approval → dashboard approval gate
```

---

## Roadmap

- [ ] Multi-tenant SaaS (user accounts, usage limits)
- [ ] Stripe billing integration
- [ ] Salesforce + HubSpot CRM integration
- [ ] Mobile app (React Native)
- [ ] Real-time meeting bot (Zoom/Meet/Teams)
- [ ] Recurring meeting pattern analysis
- [ ] Fine-tuned domain models
- [ ] HIPAA compliance mode (healthcare vertical)
- [ ] SOC 2 compliance (enterprise sales)

---

## Contributing

PRs welcome. See [CONTRIBUTING.md](CONTRIBUTING.md).

---

## License

MIT — use it, sell it, build on it.
