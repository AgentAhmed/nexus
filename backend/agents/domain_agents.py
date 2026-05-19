"""
NEXUS Domain Expert Agents
Each agent is a specialized LLM expert for one enterprise domain.
Uses Featherless or Vultr Serverless Inference (OpenAI-compatible).
Falls back to Gemini if neither key is present.
"""
import json
from openai import AsyncOpenAI
import google.generativeai as genai
from backend.config import get_openai_compat_config, GEMINI_API_KEY, GEMINI_FLASH_MODEL

# ── Base domain agent ──────────────────────────────────────────────────────────

class BaseDomainAgent:
    DOMAIN      = "general"
    SYSTEM_PROMPT = "You are a helpful enterprise assistant."

    def __init__(self):
        cfg = get_openai_compat_config()
        self._use_openai_compat = cfg["base_url"] is not None
        if self._use_openai_compat:
            self._client = AsyncOpenAI(base_url=cfg["base_url"], api_key=cfg["api_key"])
            self._model  = cfg["model"]
        else:
            genai.configure(api_key=GEMINI_API_KEY)
            self._gemini = genai.GenerativeModel(GEMINI_FLASH_MODEL)

    async def analyze(self, transcript: str, context: str, action_items: list[str]) -> str:
        prompt = f"""
{self.SYSTEM_PROMPT}

## Enterprise Knowledge Context
{context if context else "No relevant documents found."}

## Meeting Transcript
{transcript}

## Identified Action Items
{json.dumps(action_items, indent=2)}

Your task:
1. Analyse the action items from your domain expertise ({self.DOMAIN.upper()})
2. Flag any risks, compliance issues, or important considerations
3. Suggest specific next steps with owners and deadlines
4. Return a structured JSON response:

{{
  "domain": "{self.DOMAIN}",
  "risk_level": "low|medium|high",
  "risks": ["..."],
  "recommendations": ["..."],
  "enriched_actions": [
    {{"item": "...", "owner": "...", "deadline": "...", "priority": "high|medium|low"}}
  ],
  "summary": "2-3 sentence executive summary"
}}
"""
        return await self._call_llm(prompt)

    async def _call_llm(self, prompt: str) -> str:
        if self._use_openai_compat:
            resp = await self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user",   "content": prompt},
                ],
                max_tokens=1024,
                temperature=0.3,
            )
            return resp.choices[0].message.content or ""
        else:
            resp = await self._gemini.generate_content_async(prompt)
            return resp.text or ""


# ── Specialized agents ─────────────────────────────────────────────────────────

class LegalAgent(BaseDomainAgent):
    DOMAIN = "legal"
    SYSTEM_PROMPT = """You are a senior enterprise legal counsel AI. 
You specialise in contract law, corporate governance, regulatory compliance (GDPR, SOX, HIPAA), 
intellectual property, and employment law. 
Always flag potential legal risks and recommend involving human legal counsel for binding decisions.
Respond ONLY with valid JSON."""


class FinanceAgent(BaseDomainAgent):
    DOMAIN = "finance"
    SYSTEM_PROMPT = """You are a senior enterprise CFO assistant AI.
You specialise in budget management, financial forecasting, cost-benefit analysis, 
cash flow management, ROI calculation, and financial risk assessment.
Always quantify financial impact where possible and flag spending that requires approval.
Respond ONLY with valid JSON."""


class HRAgent(BaseDomainAgent):
    DOMAIN = "hr"
    SYSTEM_PROMPT = """You are a senior HR business partner AI.
You specialise in talent acquisition, performance management, employee relations, 
compensation & benefits, organisational design, and employment compliance.
Always consider employee wellbeing and legal employment obligations.
Respond ONLY with valid JSON."""


class OpsAgent(BaseDomainAgent):
    DOMAIN = "ops"
    SYSTEM_PROMPT = """You are a senior enterprise operations manager AI.
You specialise in project management, supply chain, process optimisation, 
vendor management, IT operations, and cross-functional coordination.
Focus on efficiency, timelines, dependencies, and blockers.
Respond ONLY with valid JSON."""


class GeneralAgent(BaseDomainAgent):
    DOMAIN = "general"
    SYSTEM_PROMPT = """You are a senior enterprise executive assistant AI.
You handle cross-functional business analysis, strategic planning, and meeting intelligence.
Extract clear action items, decisions, and next steps from enterprise discussions.
Respond ONLY with valid JSON."""


DOMAIN_AGENT_MAP = {
    "legal":   LegalAgent,
    "finance": FinanceAgent,
    "hr":      HRAgent,
    "ops":     OpsAgent,
    "general": GeneralAgent,
}

def get_domain_agent(domain: str) -> BaseDomainAgent:
    cls = DOMAIN_AGENT_MAP.get(domain, GeneralAgent)
    return cls()
