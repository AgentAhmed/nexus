"""
NEXUS Orchestrator — LangGraph multi-agent state machine
Flow: transcript → intent extraction → RAG retrieval → domain agent → execution
"""
import asyncio
import json
import re
import uuid
from typing import TypedDict, Literal, Annotated
import operator

import google.generativeai as genai
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from backend.config import GEMINI_API_KEY, GEMINI_FLASH_MODEL, get_primary_llm_provider
from backend.agents.context_agent import ContextAgent
from backend.agents.domain_agents import get_domain_agent
from backend.agents.execution_agent import ExecutionAgent
from backend.observability.tracer import trace_agent_step, METRICS

genai.configure(api_key=GEMINI_API_KEY)
_flash = genai.GenerativeModel(GEMINI_FLASH_MODEL)

# ── State ───────────────────────────────────────────────────────────────────────

class NexusState(TypedDict):
    transcript:        str
    speaker_map:       dict
    retrieved_context: str
    domain:            str
    domain_analysis:   str
    action_items:      Annotated[list[str], operator.add]
    decisions:         Annotated[list[str], operator.add]
    executions_done:   Annotated[list[dict], operator.add]
    pending_approvals: Annotated[list[str], operator.add]
    confidence:        float
    error:             str | None

# ── Nodes ────────────────────────────────────────────────────────────────────────

async def node_extract_intent(state: NexusState) -> dict:
    """Gemini Flash: extract domain, action items, decisions from transcript."""
    import time; t0 = time.time()
    with trace_agent_step("intent_extraction", state["transcript"][:300]):
        prompt = f"""
You are an enterprise meeting analyst. Analyse the transcript below and extract structured data.

Transcript:
{state["transcript"]}

Return ONLY valid JSON (no markdown, no explanation):
{{
  "domain": "legal|finance|hr|ops|general",
  "action_items": ["<action item 1>", "..."],
  "decisions": ["<decision 1>", "..."],
  "confidence": 0.0
}}

Rules:
- domain: pick the ONE that best matches the main topic
- action_items: concrete tasks with a verb (max 10)
- decisions: things that were agreed/decided (max 10)
- confidence: 0.0-1.0 based on how clear the transcript is
"""
        try:
            resp = await _flash.generate_content_async(prompt)
            raw  = resp.text or "{}"
            raw  = re.sub(r"```(?:json)?|```", "", raw).strip()
            data = json.loads(raw)
        except Exception as exc:
            print(f"[intent] parse error: {exc}")
            data = {}

        METRICS.record_call("intent_agent", round((time.time()-t0)*1000))
        return {
            "domain":       data.get("domain", "general"),
            "action_items": data.get("action_items", []),
            "decisions":    data.get("decisions", []),
            "confidence":   float(data.get("confidence", 0.5)),
        }


async def node_retrieve_context(state: NexusState) -> dict:
    """ChromaDB RAG: retrieve enterprise knowledge relevant to this meeting."""
    import time; t0 = time.time()
    with trace_agent_step("rag_retrieval", state["domain"]):
        agent = ContextAgent()
        query = f"{state['domain']} " + " ".join(state["action_items"][:5])
        chunks_with_scores = await agent.retrieve_with_scores(query, top_k=5)
        if chunks_with_scores:
            avg_score = sum(s for _, s in chunks_with_scores) / len(chunks_with_scores)
            METRICS.record_rag(avg_score)
            context = "\n---\n".join(c for c, _ in chunks_with_scores)
        else:
            context = ""
        METRICS.record_call("rag_agent", round((time.time()-t0)*1000))
        return {"retrieved_context": context}


async def node_domain_agent(state: NexusState) -> dict:
    """Specialized domain agent analyses action items with expert knowledge."""
    import time; t0 = time.time()
    with trace_agent_step(f"domain_{state['domain']}", str(state["action_items"])[:200]):
        agent    = get_domain_agent(state["domain"])
        analysis = await agent.analyze(
            transcript=state["transcript"],
            context=state["retrieved_context"],
            action_items=state["action_items"],
        )
        METRICS.record_call(f"domain_{state['domain']}", round((time.time()-t0)*1000))
        return {"domain_analysis": analysis}


async def node_execute(state: NexusState) -> dict:
    """Execution agent: auto-execute high-confidence actions."""
    import time; t0 = time.time()
    with trace_agent_step("execution", str(state["action_items"])[:200]):
        executor = ExecutionAgent()
        results  = await executor.execute_batch(
            action_items=state["action_items"],
            domain=state["domain"],
            analysis=state["domain_analysis"],
        )
        for r in results:
            METRICS.record_execution(r.get("status") == "success")
        METRICS.record_call("execution_agent", round((time.time()-t0)*1000))
        return {"executions_done": results}


async def node_flag_approval(state: NexusState) -> dict:
    """Low-confidence: surface actions for human approval instead of auto-executing."""
    return {"pending_approvals": state["action_items"]}


# ── Routing ───────────────────────────────────────────────────────────────────

def route_after_domain(state: NexusState) -> Literal["execute", "flag_approval", "__end__"]:
    if not state["action_items"]:
        return "__end__"
    if state["confidence"] >= 0.70:
        return "execute"
    return "flag_approval"


# ── Graph ─────────────────────────────────────────────────────────────────────

def build_graph() -> StateGraph:
    g = StateGraph(NexusState)

    g.add_node("extract_intent",   node_extract_intent)
    g.add_node("retrieve_context", node_retrieve_context)
    g.add_node("domain_agent",     node_domain_agent)
    g.add_node("execute",          node_execute)
    g.add_node("flag_approval",    node_flag_approval)

    g.set_entry_point("extract_intent")
    g.add_edge("extract_intent",   "retrieve_context")
    g.add_edge("retrieve_context", "domain_agent")
    g.add_conditional_edges("domain_agent", route_after_domain, {
        "execute":       "execute",
        "flag_approval": "flag_approval",
        "__end__":       END,
    })
    g.add_edge("execute",       END)
    g.add_edge("flag_approval", END)

    return g.compile(checkpointer=MemorySaver())


NEXUS_GRAPH = build_graph()

# ── Public API ────────────────────────────────────────────────────────────────

async def run_nexus(transcript: str, speaker_map: dict, thread_id: str | None = None) -> NexusState:
    thread_id = thread_id or str(uuid.uuid4())
    initial: NexusState = {
        "transcript":        transcript,
        "speaker_map":       speaker_map,
        "retrieved_context": "",
        "domain":            "general",
        "domain_analysis":   "",
        "action_items":      [],
        "decisions":         [],
        "executions_done":   [],
        "pending_approvals": [],
        "confidence":        0.0,
        "error":             None,
    }
    config = {"configurable": {"thread_id": thread_id}}
    result = await NEXUS_GRAPH.ainvoke(initial, config=config)
    return result
