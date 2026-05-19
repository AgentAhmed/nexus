"""
NEXUS Configuration
All settings read from environment variables with safe defaults.
The system degrades gracefully when optional APIs are not provided.
"""
import os
from enum import Enum

# ── LLM Provider priority ──────────────────────────────────────────────────────
# System auto-selects based on which keys are present.
# Priority: Gemini > Vultr Serverless > Featherless

GEMINI_API_KEY       = os.getenv("GEMINI_API_KEY", "")
VULTR_API_KEY        = os.getenv("VULTR_API_KEY", "")          # Vultr serverless inference
FEATHERLESS_API_KEY  = os.getenv("FEATHERLESS_API_KEY", "")

SPEECHMATICS_API_KEY = os.getenv("SPEECHMATICS_API_KEY", "")   # optional - falls back to demo mode
SLACK_WEBHOOK_URL    = os.getenv("SLACK_WEBHOOK_URL", "")       # optional
JIRA_BASE_URL        = os.getenv("JIRA_BASE_URL", "")           # optional
JIRA_API_TOKEN       = os.getenv("JIRA_API_TOKEN", "")          # optional
JIRA_USER_EMAIL      = os.getenv("JIRA_USER_EMAIL", "")         # optional

# Vultr Serverless Inference endpoint (OpenAI-compatible)
VULTR_INFERENCE_BASE = "https://api.vultrinference.com/v1"
VULTR_INFERENCE_MODEL = os.getenv("VULTR_INFERENCE_MODEL", "llama-3.1-70b-instruct-fp8")

# Featherless (OpenAI-compatible)
FEATHERLESS_BASE     = "https://api.featherless.ai/v1"
FEATHERLESS_MODEL    = os.getenv("FEATHERLESS_MODEL", "meta-llama/Meta-Llama-3.1-8B-Instruct")

# Gemini models
GEMINI_FLASH_MODEL   = "gemini-1.5-flash"
GEMINI_PRO_MODEL     = "gemini-1.5-pro"

# Storage
CHROMA_PATH          = os.getenv("CHROMA_PATH", "./nexus_chroma_db")
REDIS_URL            = os.getenv("REDIS_URL", "redis://localhost:6379")
POSTGRES_URL         = os.getenv("POSTGRES_URL", "")   # empty = use SQLite

# Observability
ENABLE_PHOENIX       = os.getenv("ENABLE_PHOENIX", "true").lower() == "true"
PHOENIX_PORT         = int(os.getenv("PHOENIX_PORT", "6006"))

# App
APP_HOST             = os.getenv("APP_HOST", "0.0.0.0")
APP_PORT             = int(os.getenv("APP_PORT", "8000"))
FRONTEND_URL         = os.getenv("FRONTEND_URL", "http://localhost:3000")

# ── Provider detection ─────────────────────────────────────────────────────────

def get_primary_llm_provider() -> str:
    """Return the best available LLM provider."""
    if GEMINI_API_KEY:
        return "gemini"
    if VULTR_API_KEY:
        return "vultr"
    if FEATHERLESS_API_KEY:
        return "featherless"
    raise EnvironmentError(
        "No LLM API key found. Set GEMINI_API_KEY, VULTR_API_KEY, or FEATHERLESS_API_KEY."
    )

def get_openai_compat_config() -> dict:
    """
    Returns (base_url, api_key, model) for OpenAI-compatible providers.
    Used by domain agents (Featherless / Vultr fallback).
    """
    if VULTR_API_KEY:
        return {"base_url": VULTR_INFERENCE_BASE, "api_key": VULTR_API_KEY, "model": VULTR_INFERENCE_MODEL}
    if FEATHERLESS_API_KEY:
        return {"base_url": FEATHERLESS_BASE, "api_key": FEATHERLESS_API_KEY, "model": FEATHERLESS_MODEL}
    # Fallback: use Gemini (via google-generativeai, not OpenAI compat)
    return {"base_url": None, "api_key": GEMINI_API_KEY, "model": GEMINI_FLASH_MODEL}

def voice_enabled() -> bool:
    return bool(SPEECHMATICS_API_KEY)

def slack_enabled() -> bool:
    return bool(SLACK_WEBHOOK_URL)

def jira_enabled() -> bool:
    return bool(JIRA_BASE_URL and JIRA_API_TOKEN and JIRA_USER_EMAIL)
