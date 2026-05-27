"""
NEXUS v2 — Provider-Agnostic Configuration
Supports ANY LLM provider via LiteLLM. Switch providers by changing one env var.

Free options (no credit card needed):
  LLM:        GROQ_API_KEY     → groq/llama-3.3-70b-versatile  (recommended free)
              GEMINI_API_KEY   → gemini/gemini-1.5-flash
              OLLAMA           → ollama/llama3.2  (100% local, truly free)
  STT:        GROQ_API_KEY     → Groq Whisper (same key, free)
              (none)           → local faster-whisper
  Embeddings: GEMINI_API_KEY   → gemini embeddings (free)
              (none)           → sentence-transformers (local)
"""
import os

# ── Primary LLM (LiteLLM model string) ───────────────────────────────────────
# Examples:
#   "groq/llama-3.3-70b-versatile"          ← free, fast, recommended
#   "groq/llama-3.1-8b-instant"             ← free, fastest
#   "gemini/gemini-1.5-flash"               ← free, Google
#   "gemini/gemini-2.0-flash-exp"           ← free, latest Google
#   "openai/gpt-4o-mini"                    ← paid, cheap
#   "anthropic/claude-3-5-haiku-20241022"   ← paid
#   "ollama/llama3.2"                       ← local, truly free (needs Ollama installed)
PRIMARY_MODEL   = os.getenv("PRIMARY_MODEL",   "groq/llama-3.3-70b-versatile")
FAST_MODEL      = os.getenv("FAST_MODEL",      "groq/llama-3.1-8b-instant")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "gemini/text-embedding-004")

# ── API Keys — only set the ones you have ────────────────────────────────────
GROQ_API_KEY      = os.getenv("GROQ_API_KEY",      "")   # free at console.groq.com
GEMINI_API_KEY    = os.getenv("GEMINI_API_KEY",    "")   # free at aistudio.google.com
OPENAI_API_KEY    = os.getenv("OPENAI_API_KEY",    "")   # paid
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")   # paid
OLLAMA_BASE_URL   = os.getenv("OLLAMA_BASE_URL",   "http://localhost:11434")  # local

# ── STT (Speech-to-Text) ─────────────────────────────────────────────────────
# "groq"    → Groq Whisper API (free, fast) — uses GROQ_API_KEY
# "openai"  → OpenAI Whisper API — uses OPENAI_API_KEY
# "local"   → faster-whisper (runs on CPU, no API key needed)
# "demo"    → built-in demo transcript (for testing with no keys at all)
STT_PROVIDER = os.getenv("STT_PROVIDER", "groq" if GROQ_API_KEY else "local")

# ── Vector Store ─────────────────────────────────────────────────────────────
# "chroma"    → ChromaDB local file (default, free, zero setup)
# "supabase"  → Supabase pgvector (free hosted, needs SUPABASE_URL + SUPABASE_KEY)
VECTOR_STORE     = os.getenv("VECTOR_STORE",     "chroma")
CHROMA_PATH      = os.getenv("CHROMA_PATH",      "./nexus_chroma_db")
SUPABASE_URL     = os.getenv("SUPABASE_URL",     "")
SUPABASE_KEY     = os.getenv("SUPABASE_KEY",     "")

# ── Execution integrations (all optional) ────────────────────────────────────
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")
JIRA_BASE_URL     = os.getenv("JIRA_BASE_URL",     "")
JIRA_API_TOKEN    = os.getenv("JIRA_API_TOKEN",    "")
JIRA_USER_EMAIL   = os.getenv("JIRA_USER_EMAIL",   "")
LINEAR_API_KEY    = os.getenv("LINEAR_API_KEY",    "")   # Linear.app (popular with startups)
NOTION_API_KEY    = os.getenv("NOTION_API_KEY",    "")   # Notion
WEBHOOK_URL       = os.getenv("WEBHOOK_URL",        "")  # generic webhook (Zapier, Make, n8n)

# ── Auth (SaaS mode) ─────────────────────────────────────────────────────────
NEXUS_API_KEY     = os.getenv("NEXUS_API_KEY",     "")   # master key for self-hosted
JWT_SECRET        = os.getenv("JWT_SECRET",         "change-this-in-production-please")
ENABLE_AUTH       = os.getenv("ENABLE_AUTH",        "false").lower() == "true"

# ── App ───────────────────────────────────────────────────────────────────────
APP_HOST          = os.getenv("APP_HOST",           "0.0.0.0")
APP_PORT          = int(os.getenv("APP_PORT",       "8000"))
FRONTEND_URL      = os.getenv("FRONTEND_URL",       "http://localhost:3000")
ENABLE_PHOENIX    = os.getenv("ENABLE_PHOENIX",     "false").lower() == "true"
REDIS_URL         = os.getenv("REDIS_URL",          "")  # optional, falls back to in-memory

# ── Provider detection helpers ────────────────────────────────────────────────
def has_llm() -> bool:
    return bool(GROQ_API_KEY or GEMINI_API_KEY or OPENAI_API_KEY or ANTHROPIC_API_KEY)

def has_embeddings() -> bool:
    return bool(GEMINI_API_KEY or OPENAI_API_KEY)

def get_litellm_env() -> None:
    """Set env vars LiteLLM needs to authenticate providers."""
    if GROQ_API_KEY:      os.environ["GROQ_API_KEY"]      = GROQ_API_KEY
    if GEMINI_API_KEY:    os.environ["GEMINI_API_KEY"]     = GEMINI_API_KEY
    if OPENAI_API_KEY:    os.environ["OPENAI_API_KEY"]     = OPENAI_API_KEY
    if ANTHROPIC_API_KEY: os.environ["ANTHROPIC_API_KEY"]  = ANTHROPIC_API_KEY
    if OLLAMA_BASE_URL:   os.environ["OLLAMA_API_BASE"]    = OLLAMA_BASE_URL

def slack_enabled()  -> bool: return bool(SLACK_WEBHOOK_URL)
def jira_enabled()   -> bool: return bool(JIRA_BASE_URL and JIRA_API_TOKEN)
def linear_enabled() -> bool: return bool(LINEAR_API_KEY)
def notion_enabled() -> bool: return bool(NOTION_API_KEY)
def webhook_enabled()-> bool: return bool(WEBHOOK_URL)
