"""
NEXUS Context Agent
Retrieves relevant enterprise knowledge for a given query using ChromaDB RAG.
"""
from backend.rag.pipeline import RAGPipeline

_pipeline: RAGPipeline | None = None


def get_pipeline() -> RAGPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = RAGPipeline()
    return _pipeline


class ContextAgent:
    """Thin wrapper so orchestrator uses a consistent agent interface."""

    async def retrieve(self, query: str, top_k: int = 5) -> list[str]:
        pipeline = get_pipeline()
        try:
            return await pipeline.retrieve(query, top_k=top_k)
        except Exception as exc:
            print(f"[ContextAgent] RAG retrieval failed: {exc}")
            return []

    async def retrieve_with_scores(self, query: str, top_k: int = 5) -> list[tuple[str, float]]:
        pipeline = get_pipeline()
        try:
            return await pipeline.retrieve_with_scores(query, top_k=top_k)
        except Exception as exc:
            print(f"[ContextAgent] RAG retrieval failed: {exc}")
            return []
