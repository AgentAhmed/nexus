"""
NEXUS Domain Expert Agents
Each agent specialises in one enterprise domain.
Uses the LLM Gateway — change provider in .env, no code change needed.
"""
import json
from backend.agents.llm import llm_smart, parse_json_response


BASE_INSTRUCTION = """
You are a specialised enterprise AI agent. Analyse the meeting context and action items.
Return ONLY valid JSON — no markdown, no explanation outside the JSON block.

Required format:
{
  "domain": "<your domain>",
  "risk_level": "low|medium|high",
  "risks": ["<risk 1>", "..."],
  "recommendations": ["<recommendation 1>", "..."],
  "enriched_actions": [
    {"item": "...", "owner": "...", "deadline": "...", "priority": "high|medium|low"}
  ],
  "summary": "<2-3 sentence executive summary>"
}
"""


class BaseDomainAgent:
    DOMAIN        = "general"
    SYSTEM_PROMPT = "You are a helpful enterprise assistant."

    async def analyze(self, transcript: str, context: str, action_items: list[str]) -> str:
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT + "\n\n" + BASE_INSTRUCTION},
            {"role": "user",   "content": f"""
## Enterprise Knowledge Context
{context or "No relevant documents found in knowledge base."}

## Meeting Transcript
{transcript}

## Identified Action Items
{json.dumps(action_items, indent=2)}

Analyse these action items from a {self.DOMAIN.upper()} perspective.
"""},
        ]
        raw = await llm_smart(messages, json_mode=True)
        # Return raw string — orchestrator stores it, execution agent parses it
        return raw


class LegalAgent(BaseDomainAgent):
    DOMAIN = "legal"
    SYSTEM_PROMPT = """You are a senior enterprise legal counsel AI.
Specialise in: contract law, corporate governance, GDPR/SOX/HIPAA compliance,
intellectual property, employment law, and regulatory risk.
Always flag binding legal risks and note when a licensed attorney should be consulted."""


class FinanceAgent(BaseDomainAgent):
    DOMAIN = "finance"
    SYSTEM_PROMPT = """You are a senior enterprise CFO assistant AI.
Specialise in: budget management, financial forecasting, cost-benefit analysis,
cash flow, ROI, financial risk, and spend approval thresholds.
Always quantify financial impact where data is present."""


class HRAgent(BaseDomainAgent):
    DOMAIN = "hr"
    SYSTEM_PROMPT = """You are a senior HR business partner AI.
Specialise in: talent acquisition, performance management, employee relations,
compensation & benefits, org design, DEI, and employment law compliance.
Prioritise employee wellbeing and legal employment obligations."""


class OpsAgent(BaseDomainAgent):
    DOMAIN = "ops"
    SYSTEM_PROMPT = """You are a senior enterprise operations manager AI.
Specialise in: project management, supply chain, process optimisation,
vendor management, IT operations, SLAs, and cross-functional coordination.
Focus on efficiency, timelines, dependencies, and blockers."""


class SalesAgent(BaseDomainAgent):
    DOMAIN = "sales"
    SYSTEM_PROMPT = """You are a senior enterprise sales strategy AI.
Specialise in: pipeline management, deal qualification, customer success,
revenue forecasting, CRM hygiene, and go-to-market execution.
Focus on deal velocity, risk of churn, and next-best actions."""


class MarketingAgent(BaseDomainAgent):
    DOMAIN = "marketing"
    SYSTEM_PROMPT = """You are a senior enterprise marketing strategy AI.
Specialise in: campaign planning, content strategy, demand generation,
brand management, analytics, and growth experiments.
Focus on ROI of spend, channel mix, and measurable outcomes."""


class GeneralAgent(BaseDomainAgent):
    DOMAIN = "general"
    SYSTEM_PROMPT = """You are a senior enterprise executive assistant AI.
Handle cross-functional analysis, strategic planning, and meeting intelligence.
Extract clear action items, decisions, owners, and next steps."""


DOMAIN_AGENTS = {
    "legal":     LegalAgent,
    "finance":   FinanceAgent,
    "hr":        HRAgent,
    "ops":       OpsAgent,
    "sales":     SalesAgent,
    "marketing": MarketingAgent,
    "general":   GeneralAgent,
}

def get_domain_agent(domain: str) -> BaseDomainAgent:
    return DOMAIN_AGENTS.get(domain, GeneralAgent)()
