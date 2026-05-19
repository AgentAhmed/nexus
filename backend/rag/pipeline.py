"""
NEXUS RAG Pipeline — ChromaDB (local) + Gemini embeddings
Works completely offline/locally without any cloud vector DB.
"""
import hashlib, io, os
from pathlib import Path
import chromadb
from chromadb.config import Settings
import google.generativeai as genai
from backend.config import GEMINI_API_KEY, CHROMA_PATH

genai.configure(api_key=GEMINI_API_KEY)

EMBED_MODEL = "models/text-embedding-004"
COLLECTION  = "nexus_enterprise_kb"


class RAGPipeline:

    def __init__(self):
        self._client = chromadb.PersistentClient(
            path=CHROMA_PATH,
            settings=Settings(anonymized_telemetry=False),
        )
        self._col = self._client.get_or_create_collection(
            name=COLLECTION, metadata={"hnsw:space": "cosine"}
        )

    async def initialize(self):
        print(f"[RAG] ChromaDB ready. Documents: {self._col.count()} chunks")

    # ── Ingest ────────────────────────────────────────────────────────────────

    async def ingest(self, filename: str, content: bytes) -> str:
        text   = self._extract(filename, content)
        if not text.strip():
            return ""
        chunks = self._chunk(text)
        doc_id = hashlib.md5(content).hexdigest()

        # Skip if already ingested (idempotent)
        existing = self._col.get(where={"source": filename})
        if existing["ids"]:
            print(f"[RAG] '{filename}' already indexed, skipping")
            return doc_id

        embeddings = self._embed(chunks, task="retrieval_document")
        self._col.add(
            ids        = [f"{doc_id}_{i}" for i in range(len(chunks))],
            documents  = chunks,
            embeddings = embeddings,
            metadatas  = [{"source": filename, "chunk": i} for i in range(len(chunks))],
        )
        print(f"[RAG] Ingested '{filename}': {len(chunks)} chunks")
        return doc_id

    def _extract(self, filename: str, content: bytes) -> str:
        ext = Path(filename).suffix.lower()
        try:
            if ext == ".pdf":
                from pypdf import PdfReader
                r = PdfReader(io.BytesIO(content))
                return "\n".join(p.extract_text() or "" for p in r.pages)
            if ext in (".docx", ".doc"):
                from docx import Document
                d = Document(io.BytesIO(content))
                return "\n".join(p.text for p in d.paragraphs)
            return content.decode("utf-8", errors="ignore")
        except Exception as exc:
            print(f"[RAG] extract error for {filename}: {exc}")
            return ""

    def _chunk(self, text: str, size: int = 400, overlap: int = 50) -> list[str]:
        words  = text.split()
        chunks = []
        i = 0
        while i < len(words):
            chunk = " ".join(words[i: i + size])
            if len(chunk.strip()) > 40:
                chunks.append(chunk)
            i += size - overlap
        return chunks

    def _embed(self, texts: list[str], task: str = "retrieval_document") -> list[list[float]]:
        # Gemini free tier: 100 req/min, batch up to 100 texts
        all_embs = []
        for i in range(0, len(texts), 50):
            batch = texts[i: i + 50]
            result = genai.embed_content(model=EMBED_MODEL, content=batch, task_type=task)
            all_embs.extend(result["embedding"])
        return all_embs

    # ── Retrieve ──────────────────────────────────────────────────────────────

    async def retrieve(self, query: str, top_k: int = 5) -> list[str]:
        results = self._query(query, top_k)
        return results.get("documents", [[]])[0]

    async def retrieve_with_scores(self, query: str, top_k: int = 5) -> list[tuple[str, float]]:
        results = self._query(query, top_k, include_distances=True)
        docs      = results.get("documents", [[]])[0]
        distances = results.get("distances", [[]])[0]
        scores    = [round(1.0 - d, 4) for d in distances]
        return list(zip(docs, scores))

    def _query(self, query: str, top_k: int, include_distances: bool = False):
        if self._col.count() == 0:
            return {"documents": [[]], "distances": [[]]}
        n = min(top_k, self._col.count())
        q_emb = self._embed([query], task="retrieval_query")[0]
        include = ["documents"]
        if include_distances:
            include.append("distances")
        return self._col.query(query_embeddings=[q_emb], n_results=n, include=include)
