"""
NEXUS Observability
- Arize Phoenix (self-hosted on Vultr, optional)
- OpenTelemetry spans for every agent step
- In-memory metrics always available for the dashboard WebSocket
"""
import contextlib
import time
from typing import Generator, Any
from backend.config import ENABLE_PHOENIX, PHOENIX_PORT

_phoenix_started = False


def init_observability(project: str = "nexus") -> None:
    global _phoenix_started
    if _phoenix_started or not ENABLE_PHOENIX:
        return
    try:
        import phoenix as px
        from phoenix.otel import register
        from openinference.instrumentation.langchain import LangChainInstrumentor

        px.launch_app(port=PHOENIX_PORT)
        tracer_provider = register(
            project_name=project,
            endpoint=f"http://localhost:{PHOENIX_PORT}/v1/traces",
        )
        LangChainInstrumentor().instrument(tracer_provider=tracer_provider)
        _phoenix_started = True
        print(f"[NEXUS] Phoenix observability → http://localhost:{PHOENIX_PORT}")
    except ImportError:
        print("[NEXUS] arize-phoenix not installed — observability disabled")
    except Exception as exc:
        print(f"[NEXUS] Phoenix init failed: {exc} — continuing without observability")


# ── Span context manager ───────────────────────────────────────────────────────

@contextlib.contextmanager
def trace_agent_step(step: str, preview: str = "", meta: dict | None = None) -> Generator[Any, None, None]:
    """Wraps any agent step in an OTel span when Phoenix is active."""
    try:
        from opentelemetry import trace
        tracer = trace.get_tracer("nexus.agents")
        with tracer.start_as_current_span(f"nexus.{step}") as span:
            span.set_attribute("input.preview", preview[:400])
            span.set_attribute("step.name",     step)
            if meta:
                for k, v in meta.items():
                    span.set_attribute(f"meta.{k}", str(v))
            try:
                yield span
            except Exception as exc:
                span.record_exception(exc)
                raise
    except Exception:
        # OTel not available — just run without tracing
        yield None


# ── In-memory metrics (always available) ──────────────────────────────────────

class _Metrics:
    def __init__(self):
        self.agent_calls:  dict[str, int]   = {}
        self.latencies:    dict[str, list]  = {}
        self.token_totals: dict[str, int]   = {}
        self.rag_scores:   list[float]      = []
        self.executions:   int              = 0
        self.errors:       int              = 0
        self.sessions:     int              = 0

    def record_call(self, agent: str, latency_ms: float, tokens: int = 0):
        self.agent_calls[agent] = self.agent_calls.get(agent, 0) + 1
        self.latencies.setdefault(agent, []).append(latency_ms)
        self.token_totals[agent] = self.token_totals.get(agent, 0) + tokens

    def record_rag(self, score: float):
        self.rag_scores.append(score)

    def record_execution(self, success: bool):
        self.executions += 1
        if not success:
            self.errors += 1

    def snapshot(self) -> dict:
        avg = {a: round(sum(l)/len(l), 1) for a, l in self.latencies.items() if l}
        return {
            "agent_calls":    self.agent_calls,
            "avg_latency_ms": avg,
            "token_totals":   self.token_totals,
            "avg_rag_score":  round(sum(self.rag_scores)/max(len(self.rag_scores),1), 3),
            "executions":     self.executions,
            "errors":         self.errors,
            "sessions":       self.sessions,
        }

    def reset(self):
        self.__init__()


METRICS = _Metrics()
