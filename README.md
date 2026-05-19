# NEXUS — Multi-Agent Enterprise Intelligence System

> 🏆 **AI Agent Olympics Hackathon 2026** · Milan AI Week · Team: **Andromeda**

**NEXUS** listens to enterprise meetings, retrieves relevant knowledge, routes decisions to specialized domain agents, and autonomously executes follow-up actions — closing the full loop from voice → context → reasoning → action.

[![Demo](https://img.shields.io/badge/Live_Demo-▶_Watch-blue)](http://YOUR_DEMO_URL)
[![License: MIT](https://img.shields.io/badge/License-MIT-green)](LICENSE)

---

## 🧩 Hackathon Tracks

| Track | Implementation |
|---|---|
| 🤝 Collaborative Systems | 5 specialized agents + LangGraph orchestrator |
| 🔄 Agentic Workflows | Multi-step state machine with conditional routing |
| 🌍 Enterprise Utility | Meetings → tickets/Slack/email, zero human relay |
| 🧩 Multimodal Intelligence | Voice (Speechmatics) + documents (PDF/DOCX) + text |

---

## ⚡ The Problem

Enterprise managers lose **40% of their day** to fragmented information.  
Meetings produce decisions — but those decisions get buried in transcripts, never reach the right expert, and never trigger automated action.

**NEXUS closes the gap.** Voice → brain → action, fully autonomous.

---

## 🏗️ Architecture

```
Meeting Audio / Transcript
        ↓
[ Voice Intelligence Agent ]  ← Speechmatics RT (speaker diarization)
        ↓
[ Intent Extractor ]          ← Gemini 1.5 Flash (domain, actions, decisions)
        ↓
[ Context Agent (RAG) ]       ← ChromaDB + Gemini embeddings (enterprise KB)
        ↓
[ Domain Expert Agent ]       ← Featherless / Vultr Inference / Gemini
   Legal | Finance | HR | Ops    (specialized reasoning per domain)
        ↓
  confidence ≥ 0.70?
     ↓ yes              ↓ no
[ Execute Agent ]      [ Flag for Human Approval ]
  Jira | Slack | Email     (dashboard approval gate)
        ↓
[ Live Dashboard ]  ← React + WebSocket real-time feed
[ Arize Phoenix ]   ← Full agent trace observability
```

---

## 🛠️ Tech Stack (all open-source / free tier)

| Layer | Tool | Why |
|---|---|---|
| Agent orchestration | LangGraph + LangChain | Stateful multi-agent graphs |
| LLM (orchestrator) | Gemini 1.5 Flash | Fast, free tier, excellent reasoning |
| LLM (domain agents) | Featherless / Vultr Inference | 27k+ specialized OSS models |
| Voice | Speechmatics RT API | Best-in-class diarization |
| Embeddings | Gemini text-embedding-004 | Free, high quality |
| Vector store | ChromaDB | Local, no cloud dependency |
| Backend | FastAPI + WebSocket | Async, real-time capable |
| Frontend | Next.js 14 + Tailwind | Fast, production-grade |
| Observability | Arize Phoenix + OTel | Full LLM trace visibility |
| Deployment | Docker Compose + Vultr VM | One-command deploy |

---

## 🚀 Quick Start

### Option A — Local (no Docker)

```bash
git clone https://github.com/YOUR_USERNAME/nexus.git && cd nexus
cp .env.example .env       # add your GEMINI_API_KEY (minimum required)
pip install -r requirements.txt
uvicorn backend.main:app --reload
# frontend
cd frontend && npm install && npm run dev
```

### Option B — Docker (recommended)

```bash
cp .env.example .env       # fill in keys
docker compose up -d
# Visit http://localhost
```

### Option C — Vultr VM (production)

```bash
ssh root@YOUR_VULTR_IP
curl -sSL https://raw.githubusercontent.com/YOUR_USERNAME/nexus/main/setup.sh | bash
```

---

## 🔑 API Keys — What's Required

| Key | Required? | Free tier | Get it |
|---|---|---|---|
| `GEMINI_API_KEY` | ✅ YES | ✅ Yes | [aistudio.google.com](https://aistudio.google.com/apikey) |
| `VULTR_API_KEY` | Optional | Hackathon $100 | [vultr.com](https://my.vultr.com) |
| `FEATHERLESS_API_KEY` | Optional | Hackathon $25 | [featherless.ai](https://featherless.ai) |
| `SPEECHMATICS_API_KEY` | Optional | Hackathon $200 | [portal.speechmatics.com](https://portal.speechmatics.com) |
| `SLACK_WEBHOOK_URL` | Optional | Free | [api.slack.com](https://api.slack.com/messaging/webhooks) |
| `JIRA_*` | Optional | Free | [id.atlassian.com](https://id.atlassian.com) |

**Minimum to run:** only `GEMINI_API_KEY` — everything else degrades gracefully.

---

## 🔌 API Reference

```
GET  /api/health          Health check
GET  /api/metrics         Agent performance metrics
POST /api/process         Process a meeting transcript
POST /api/upload-audio    Upload audio file → transcribe → process
POST /api/ingest-docs     Add PDFs/DOCX/TXT to knowledge base
POST /api/demo            Run built-in demo (no keys needed)
POST /api/approve         Approve a pending action item

WS   /ws/dashboard        Real-time dashboard feed
WS   /ws/voice/{id}       Live audio streaming + transcription
```

---

## 🔬 Observability

NEXUS ships with Arize Phoenix self-hosted at `:6006`:
- Every agent step traced with OpenTelemetry
- LLM call latency, token counts, retrieval scores all recorded
- Auto-instrumented via `openinference-instrumentation-langchain`

---

## 🗺️ Future Roadmap

- **Healthcare** — clinical meetings → care plans (HIPAA-compliant audit trail)
- **Legal** — negotiation sessions → auto-drafted amendments
- **Finance** — IC calls → investment committee memos with market data
- **Multi-language** — via Speechmatics language models
- **Mobile app** — on-the-go meeting capture

---

## 📄 License

MIT — fully open-source, reproducible, deployable beyond the hackathon.

---

*Built with ❤️ by Team Andromeda at AI Agent Olympics 2026, Milan AI Week*
