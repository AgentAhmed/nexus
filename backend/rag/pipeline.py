"""
NEXUS RAG Pipeline - ChromaDB + provider-agnostic embeddings via LLM gateway
Works with Gemini, OpenAI embeddings, or local sentence-transformers (free).
"""
import hashlib, io
from pathlib import Path
import chromadb
from chromadb.config import Settings
from backend.config import CHROMA_PATH
from backend.agents.llm import embed_texts

COLLECTION = "nexus_enterprise_kb"


class RAGPipeline:
    def __init__(self):
        self._client = chromadb.PersistentClient(path=CHROMA_PATH, settings=Settings(anonymized_telemetry=False))
        self._col    = self._client.get_or_create_collection(name=COLLECTION, metadata={"hnsw:space":"cosine"})

    async def initialize(self):
        print(f"[RAG] ChromaDB ready — {self._col.count()} chunks indexed")

    async def ingest(self, filename: str, content: bytes) -> str:
        text   = self._extract(filename, content)
        if not text.strip(): return ""
        doc_id = hashlib.md5(content).hexdigest()
        # Idempotent: skip if already indexed
        if self._col.get(where={"source": filename})["ids"]:
            print(f"[RAG] '{filename}' already indexed"); return doc_id
        chunks = self._chunk(text)
        embs   = await embed_texts(chunks)
        self._col.add(
            ids        = [f"{doc_id}_{i}" for i in range(len(chunks))],
            documents  = chunks,
            embeddings = embs,
            metadatas  = [{"source": filename, "chunk": i} for i in range(len(chunks))],
        )
        print(f"[RAG] Ingested '{filename}': {len(chunks)} chunks")
        return doc_id

    async def retrieve(self, query: str, top_k: int = 5) -> list[str]:
        if self._col.count() == 0: return []
        q_emb = await embed_texts([query])
        res   = self._col.query(query_embeddings=q_emb, n_results=min(top_k, self._col.count()), include=["documents"])
        return res.get("documents", [[]])[0]

    async def retrieve_with_scores(self, query: str, top_k: int = 5) -> list[tuple[str, float]]:
        if self._col.count() == 0: return []
        q_emb = await embed_texts([query])
        res   = self._col.query(query_embeddings=q_emb, n_results=min(top_k, self._col.count()), include=["documents","distances"])
        docs  = res.get("documents",[[]])[0]
        dists = res.get("distances", [[]])[0]
        return list(zip(docs, [round(1-d, 4) for d in dists]))

    def _extract(self, filename: str, content: bytes) -> str:
        ext = Path(filename).suffix.lower()
        try:
            if ext == ".pdf":
                from pypdf import PdfReader
                return "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(content)).pages)
            if ext in (".docx", ".doc"):
                from docx import Document
                return "\n".join(p.text for p in Document(io.BytesIO(content)).paragraphs)
            return content.decode("utf-8", errors="ignore")
        except Exception as e:
            print(f"[RAG] extract error: {e}"); return ""

    def _chunk(self, text: str, size: int = 400, overlap: int = 60) -> list[str]:
        words, chunks, i = text.split(), [], 0
        while i < len(words):
            c = " ".join(words[i:i+size])
            if len(c.strip()) > 40: chunks.append(c)
            i += size - overlap
        return chunks
