"""
NEXUS Backend API — FastAPI
REST endpoints + WebSocket for real-time dashboard
"""
import asyncio, json, uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.config import FRONTEND_URL
from backend.agents.orchestrator import run_nexus
from backend.agents.voice_agent import get_voice_agent, build_transcript, TranscriptChunk
from backend.rag.pipeline import RAGPipeline
from backend.observability.tracer import init_observability, METRICS

_rag: RAGPipeline | None = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _rag
    init_observability("nexus-hackathon")
    _rag = RAGPipeline()
    await _rag.initialize()
    yield

app = FastAPI(title="NEXUS API", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ── WebSocket connection manager ───────────────────────────────────────────────

_connections: list[WebSocket] = []

async def broadcast(msg: dict):
    dead = []
    for ws in _connections:
        try:
            await ws.send_json(msg)
        except Exception:
            dead.append(ws)
    for ws in dead:
        _connections.remove(ws)

# ── Models ─────────────────────────────────────────────────────────────────────

class ProcessRequest(BaseModel):
    transcript:  str
    speaker_map: dict = {}
    thread_id:   str  = ""

class ApproveRequest(BaseModel):
    thread_id:   str
    action_item: str

# ── REST ───────────────────────────────────────────────────────────────────────

@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}

@app.get("/api/metrics")
async def metrics():
    return METRICS.snapshot()

@app.post("/api/process")
async def process(req: ProcessRequest):
    """Process a meeting transcript through the full NEXUS pipeline."""
    if not req.transcript.strip():
        raise HTTPException(400, "transcript is required")
    METRICS.sessions += 1
    thread_id = req.thread_id or str(uuid.uuid4())
    try:
        result = await run_nexus(req.transcript, req.speaker_map, thread_id)
        payload = {
            "type":             "PROCESSING_COMPLETE",
            "thread_id":        thread_id,
            "domain":           result.get("domain", "general"),
            "decisions":        result.get("decisions", []),
            "action_items":     result.get("action_items", []),
            "executions_done":  result.get("executions_done", []),
            "pending_approvals":result.get("pending_approvals", []),
            "confidence":       result.get("confidence", 0),
            "domain_analysis":  result.get("domain_analysis", ""),
        }
        await broadcast(payload)
        return payload
    except Exception as exc:
        raise HTTPException(500, str(exc))

@app.post("/api/upload-audio")
async def upload_audio(file: UploadFile = File(...)):
    """Upload an audio file → transcribe → run NEXUS."""
    import tempfile, os
    content = await file.read()
    suffix  = "." + file.filename.rsplit(".", 1)[-1] if "." in file.filename else ".wav"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name
    try:
        agent  = get_voice_agent()
        chunks = await agent.transcribe_file(tmp_path)
        text   = build_transcript(chunks)
        result = await run_nexus(text, {}, str(uuid.uuid4()))
        return {**result, "transcript": text}
    finally:
        os.unlink(tmp_path)

@app.post("/api/ingest-docs")
async def ingest_docs(files: list[UploadFile] = File(...)):
    """Ingest enterprise docs (PDF/DOCX/TXT) into the knowledge base."""
    ingested = []
    for f in files:
        content = await f.read()
        doc_id  = await _rag.ingest(f.filename, content)
        ingested.append({"filename": f.filename, "doc_id": doc_id, "status": "ok" if doc_id else "skipped"})
    return {"ingested": ingested}

@app.post("/api/demo")
async def run_demo():
    """Run NEXUS on a built-in demo transcript — useful for testing without any APIs."""
    DEMO = """Sarah: Alright team, let's get through the Q3 review quickly.
John: Cloud spend is 12% over budget. We need a cost breakdown report.
Sarah: John, please prepare that by Friday and share with the finance team.
Maria: On the legal side, our GDPR audit is due next month. All vendor contracts need review.
Sarah: Maria, schedule a legal review session this week.
John: Agreed. Also, HR needs to send out the new remote work policy by end of week.
Sarah: Decision made — Q4 engineering headcount expansion approved for 3 new hires.
Maria: I'll start the job postings in the HR system today."""
    result = await run_nexus(DEMO, {"Sarah": "Sarah (CEO)", "John": "John (CFO)", "Maria": "Maria (COO)"})
    return {**result, "transcript": DEMO, "is_demo": True}

@app.post("/api/approve")
async def approve_action(req: ApproveRequest):
    """Human-in-the-loop: manually approve a pending action for execution."""
    from backend.agents.execution_agent import ExecutionAgent
    executor = ExecutionAgent()
    result   = await executor.execute(req.action_item, "general", "")
    await broadcast({"type": "ACTION_EXECUTED", "thread_id": req.thread_id, "result": result})
    return result

# ── WebSocket — dashboard ──────────────────────────────────────────────────────

@app.websocket("/ws/dashboard")
async def dashboard_ws(ws: WebSocket):
    await ws.accept()
    _connections.append(ws)
    # Send initial metrics snapshot
    await ws.send_json({"type": "METRICS_UPDATE", **METRICS.snapshot()})
    try:
        async def push_metrics():
            while True:
                await asyncio.sleep(3)
                try:
                    await ws.send_json({"type": "METRICS_UPDATE", **METRICS.snapshot()})
                except Exception:
                    break
        task = asyncio.create_task(push_metrics())
        async for raw in ws.iter_text():
            try:
                msg = json.loads(raw)
                if msg.get("type") == "ping":
                    await ws.send_json({"type": "pong"})
            except Exception:
                pass
    except WebSocketDisconnect:
        pass
    finally:
        task.cancel()
        if ws in _connections:
            _connections.remove(ws)

# ── WebSocket — live voice stream ──────────────────────────────────────────────

@app.websocket("/ws/voice/{thread_id}")
async def voice_ws(ws: WebSocket, thread_id: str):
    await ws.accept()
    agent        = get_voice_agent()
    chunks: list[TranscriptChunk] = []

    async def audio_gen():
        async for data in ws.iter_bytes():
            yield data

    def on_partial(text: str, speaker: str):
        asyncio.ensure_future(ws.send_json({"type": "VOICE_PARTIAL", "text": text, "speaker": speaker}))

    try:
        async for chunk in agent.stream(audio_gen(), on_partial=on_partial):
            chunks.append(chunk)
            await ws.send_json({
                "type":    "VOICE_FINAL",
                "text":    chunk.text,
                "speaker": chunk.speaker_id,
                "start":   chunk.start_time,
                "end":     chunk.end_time,
            })
    except WebSocketDisconnect:
        pass

    if chunks:
        transcript = build_transcript(chunks)
        result     = await run_nexus(transcript, {}, thread_id)
        try:
            await ws.send_json({"type": "NEXUS_RESULT", "transcript": transcript, **result})
        except Exception:
            pass
