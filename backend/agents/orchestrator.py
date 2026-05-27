"""
NEXUS Orchestrator — LangGraph multi-agent state machine
Fully provider-agnostic: swaps LLM by changing PRIMARY_MODEL in .env
"""
import operator, uuid
from typing import TypedDict, Literal, Annotated

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from backend.agents.llm import llm_fast, parse_json_response
from backend.agents.context_agent import ContextAgent
from backend.agents.domain_agents import get_domain_agent
from backend.agents.execution_agent import ExecutionAgent
from backend.observability.tracer import trace_agent_step, METRICS


# ── State ──────────────────────────────────────────────────────────────────────

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


# ── Nodes ──────────────────────────────────────────────────────────────────────

async def node_extract_intent(state: NexusState) -> dict:
    import time; t0 = time.time()
    with trace_agent_step("intent_extraction"):
        messages = [
            {"role": "system", "content": "You are an enterprise meeting analyst. Return ONLY valid JSON."},
            {"role": "user",   "content": f"""
Analyse this meeting transcript and extract structured data.

Transcript:
{state["transcript"]}

Return JSON only:
{{
  "domain": "legal|finance|hr|ops|sales|marketing|general",
  "action_items": ["verb + task + owner where mentioned"],
  "decisions": ["what was agreed or decided"],
  "confidence": 0.85
}}

Rules: domain = ONE best-fit category. confidence = how clear the transcript is (0-1).
"""},
        ]
        raw  = await llm_fast(messages, json_mode=True)
        data = parse_json_response(raw)
        METRICS.record_call("intent_agent", round((time.time()-t0)*1000))
        return {
            "domain":       data.get("domain", "general"),
            "action_items": data.get("action_items", []),
            "decisions":    data.get("decisions", []),
            "confidence":   float(data.get("confidence", 0.5)),
        }


async def node_retrieve_context(state: NexusState) -> dict:
    import time; t0 = time.time()
    with trace_agent_step("rag_retrieval"):
        agent = ContextAgent()
        query = f"{state['domain']} {' '.join(state['action_items'][:5])}"
        chunks_scores = await agent.retrieve_with_scores(query, top_k=5)
        if chunks_scores:
            avg = sum(s for _, s in chunks_scores) / len(chunks_scores)
            METRICS.record_rag(avg)
            context = "\n---\n".join(c for c, _ in chunks_scores)
        else:
            context = ""
        METRICS.record_call("rag_agent", round((time.time()-t0)*1000))
        return {"retrieved_context": context}


async def node_domain_agent(state: NexusState) -> dict:
    import time; t0 = time.time()
    with trace_agent_step(f"domain_{state['domain']}"):
        agent    = get_domain_agent(state["domain"])
        analysis = await agent.analyze(
            transcript=state["transcript"],
            context=state["retrieved_context"],
            action_items=state["action_items"],
        )
        METRICS.record_call(f"domain_{state['domain']}", round((time.time()-t0)*1000))
        return {"domain_analysis": analysis}


async def node_execute(state: NexusState) -> dict:
    import time; t0 = time.time()
    with trace_agent_step("execution"):
        executor = ExecutionAgent()
        results  = await executor.execute_batch(
            state["action_items"], state["domain"], state["domain_analysis"]
        )
        for r in results:
            METRICS.record_execution(r.get("status") == "success")
        METRICS.record_call("execution_agent", round((time.time()-t0)*1000))
        return {"executions_done": results}


async def node_flag_approval(state: NexusState) -> dict:
    return {"pending_approvals": state["action_items"]}


# ── Routing ────────────────────────────────────────────────────────────────────

def route_after_domain(state: NexusState) -> str:
    if not state["action_items"]:
        return "__end__"
    return "execute" if state["confidence"] >= 0.70 else "flag_approval"


# ── Graph ──────────────────────────────────────────────────────────────────────

def build_graph():
    g = StateGraph(NexusState)
    g.add_node("extract_intent",   node_extract_intent)
    g.add_node("retrieve_context", node_retrieve_context)
    g.add_node("domain_agent",     node_domain_agent)
    g.add_node("execute",          node_execute)
    g.add_node("flag_approval",    node_flag_approval)
    g.set_entry_point("extract_intent")
    g.add_edge("extract_intent",   "retrieve_context")
    g.add_edge("retrieve_context", "domain_agent")
    g.add_conditional_edges("domain_agent", route_after_domain,
        {"execute": "execute", "flag_approval": "flag_approval", "__end__": END})
    g.add_edge("execute",       END)
    g.add_edge("flag_approval", END)
    return g.compile(checkpointer=MemorySaver())


NEXUS_GRAPH = build_graph()


async def run_nexus(transcript: str, speaker_map: dict = None, thread_id: str = None) -> NexusState:
    initial = NexusState(
        transcript=transcript, speaker_map=speaker_map or {},
        retrieved_context="", domain="general", domain_analysis="",
        action_items=[], decisions=[], executions_done=[],
        pending_approvals=[], confidence=0.0, error=None,
    )
    config = {"configurable": {"thread_id": thread_id or str(uuid.uuid4())}}
    return await NEXUS_GRAPH.ainvoke(initial, config=config)
