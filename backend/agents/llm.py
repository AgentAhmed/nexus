"""
NEXUS LLM Gateway
One function call works with ANY provider: Groq, Gemini, OpenAI, Anthropic, Ollama.
Change PRIMARY_MODEL in .env to switch provider without touching any agent code.
"""
import json
import re
from litellm import acompletion
from backend.config import PRIMARY_MODEL, FAST_MODEL, EMBEDDING_MODEL, get_litellm_env, has_embeddings

# Initialise LiteLLM auth once
get_litellm_env()


async def llm_chat(
    messages: list[dict],
    model:    str | None = None,
    json_mode: bool = False,
    temperature: float = 0.3,
    max_tokens: int = 2048,
) -> str:
    """
    Call any LLM provider with one unified interface.

    Args:
        messages:    OpenAI-format message list
        model:       override model (default: PRIMARY_MODEL from .env)
        json_mode:   if True, instructs model to return only valid JSON
        temperature: 0.0-1.0
        max_tokens:  max output tokens

    Returns:
        str: the model's response text
    """
    m = model or PRIMARY_MODEL
    kwargs = dict(
        model=m,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    # JSON mode: supported natively by some providers
    if json_mode:
        try:
            kwargs["response_format"] = {"type": "json_object"}
        except Exception:
            pass  # some providers ignore this, we parse manually

    resp = await acompletion(**kwargs)
    return resp.choices[0].message.content or ""


async def llm_fast(messages: list[dict], json_mode: bool = False) -> str:
    """Use the fast/cheap model — good for intent extraction, routing."""
    return await llm_chat(messages, model=FAST_MODEL, json_mode=json_mode)


async def llm_smart(messages: list[dict], json_mode: bool = False) -> str:
    """Use the primary/best model — good for domain analysis, complex reasoning."""
    return await llm_chat(messages, model=PRIMARY_MODEL, json_mode=json_mode)


def parse_json_response(text: str) -> dict:
    """
    Robustly parse JSON from LLM output.
    Handles markdown fences, extra text before/after, etc.
    """
    # Strip markdown fences
    text = re.sub(r"```(?:json)?", "", text).strip().rstrip("```").strip()
    # Find first { ... } block
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {}


# ── Embeddings (for RAG) ────────────────────────────────────────────────────

async def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Generate embeddings using the configured EMBEDDING_MODEL.
    Falls back to sentence-transformers (local) if no API key.
    """
    if has_embeddings():
        return await _embed_litellm(texts)
    return _embed_local(texts)


async def _embed_litellm(texts: list[str]) -> list[list[float]]:
    from litellm import aembedding
    results = []
    # Batch in groups of 50 to respect rate limits
    for i in range(0, len(texts), 50):
        batch = texts[i: i + 50]
        resp  = await aembedding(model=EMBEDDING_MODEL, input=batch)
        results.extend([item["embedding"] for item in resp.data])
    return results


def _embed_local(texts: list[str]) -> list[list[float]]:
    """sentence-transformers — runs on CPU, no API key, free forever."""
    try:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("all-MiniLM-L6-v2")
        return _model.encode(texts, convert_to_numpy=True).tolist()
    except ImportError:
        raise RuntimeError(
            "No embedding provider available. Either set GEMINI_API_KEY / OPENAI_API_KEY "
            "or install sentence-transformers: pip install sentence-transformers"
        )
