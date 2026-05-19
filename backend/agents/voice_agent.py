"""
NEXUS Voice Intelligence Agent
Primary: Speechmatics real-time WebSocket API (speaker diarization)
Fallback: OpenAI Whisper API (if OPENAI_API_KEY set)
Demo mode: returns a canned response if neither key present
"""
import asyncio
import io
import json
import os
from dataclasses import dataclass
from typing import AsyncGenerator, Callable

from backend.config import SPEECHMATICS_API_KEY, voice_enabled

SPEECHMATICS_RT_URL = "wss://eu2.rt.speechmatics.com/v2"
OPENAI_API_KEY      = os.getenv("OPENAI_API_KEY", "")


@dataclass
class TranscriptChunk:
    text:       str
    speaker_id: str
    start_time: float
    end_time:   float
    is_final:   bool


# ── Speechmatics real-time ────────────────────────────────────────────────────

class SpeechmaticsVoiceAgent:
    """Real-time transcription with full speaker diarization."""

    SESSION_CONFIG = {
        "type": "StartRecognition",
        "transcription_config": {
            "language":        "en",
            "enable_partials": True,
            "max_delay":       2.0,
            "diarization":     "speaker",
            "speaker_diarization_config": {"max_speakers": 8},
            "operating_point": "enhanced",
        },
        "audio_format": {
            "type":        "raw",
            "encoding":    "pcm_f32le",
            "sample_rate": 16000,
        },
    }

    async def stream(
        self,
        audio_gen: AsyncGenerator[bytes, None],
        on_partial: Callable | None = None,
    ) -> AsyncGenerator[TranscriptChunk, None]:
        import websockets
        headers = {"Authorization": f"Bearer {SPEECHMATICS_API_KEY}"}
        queue: asyncio.Queue[TranscriptChunk | None] = asyncio.Queue()

        async def _send(ws):
            await ws.send(json.dumps(self.SESSION_CONFIG))
            async for chunk in audio_gen:
                await ws.send(chunk)
            await ws.send(json.dumps({"type": "EndOfStream", "last_seq_no": 0}))

        async def _receive(ws):
            async for raw in ws:
                msg = json.loads(raw)
                mtype = msg.get("type")
                if mtype == "AddPartialTranscript" and on_partial and msg.get("results"):
                    text    = " ".join(r["alternatives"][0]["content"] for r in msg["results"] if r.get("alternatives"))
                    speaker = msg["results"][0].get("speaker", "S1")
                    if text.strip():
                        on_partial(text, speaker)
                elif mtype == "AddTranscript" and msg.get("results"):
                    text    = " ".join(r["alternatives"][0]["content"] for r in msg["results"] if r.get("alternatives"))
                    speaker = msg["results"][0].get("speaker", "S1")
                    start   = msg["results"][0].get("start_time", 0.0)
                    end     = msg["results"][-1].get("end_time", 0.0)
                    if text.strip():
                        await queue.put(TranscriptChunk(text, speaker, start, end, is_final=True))
                elif mtype == "EndOfTranscript":
                    await queue.put(None)
                    break

        async with websockets.connect(SPEECHMATICS_RT_URL, extra_headers=headers) as ws:
            recv_task = asyncio.create_task(_receive(ws))
            send_task = asyncio.create_task(_send(ws))
            while True:
                item = await queue.get()
                if item is None:
                    break
                yield item
            await asyncio.gather(send_task, recv_task)

    async def transcribe_file(self, path: str) -> list[TranscriptChunk]:
        chunks = []
        async def _gen():
            with open(path, "rb") as f:
                while data := f.read(8192):
                    yield data
                    await asyncio.sleep(0)
        async for c in self.stream(_gen()):
            chunks.append(c)
        return chunks


# ── Whisper fallback ──────────────────────────────────────────────────────────

class WhisperVoiceAgent:
    """Batch transcription via OpenAI Whisper API. No speaker diarization."""

    async def transcribe_file(self, path: str) -> list[TranscriptChunk]:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        with open(path, "rb") as f:
            resp = await client.audio.transcriptions.create(
                model="whisper-1", file=f, response_format="verbose_json"
            )
        chunks = []
        for seg in getattr(resp, "segments", []):
            chunks.append(TranscriptChunk(
                text=seg["text"].strip(), speaker_id="Speaker",
                start_time=seg["start"], end_time=seg["end"], is_final=True
            ))
        return chunks

    async def stream(self, audio_gen, on_partial=None) -> AsyncGenerator[TranscriptChunk, None]:
        """Whisper doesn't do real-time; collect all audio then transcribe."""
        buf = io.BytesIO()
        async for chunk in audio_gen:
            buf.write(chunk)
        buf.seek(0)
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(buf.read())
            tmp_path = tmp.name
        for c in await self.transcribe_file(tmp_path):
            yield c


# ── Demo mode ─────────────────────────────────────────────────────────────────

class DemoVoiceAgent:
    """Returns a realistic demo transcript — use when no STT API is available."""

    DEMO_TRANSCRIPT = [
        TranscriptChunk("Alright everyone, let's get started with the Q3 review.", "S1", 0.0, 4.0, True),
        TranscriptChunk("Sarah, can you walk us through the budget variance?", "S1", 4.5, 8.0, True),
        TranscriptChunk("Sure. We're 12% over budget on cloud infrastructure. I think we need to review our Vultr spend.", "S2", 8.5, 14.0, True),
        TranscriptChunk("Okay. John, please prepare a cost breakdown report by Friday.", "S1", 14.5, 18.0, True),
        TranscriptChunk("Got it. I'll also check if we can optimise the serverless inference usage.", "S3", 18.5, 23.0, True),
        TranscriptChunk("Good. On the legal side — the GDPR audit is due next month. Legal team needs to review all vendor contracts.", "S1", 23.5, 30.0, True),
        TranscriptChunk("I'll schedule a review session with the legal team this week.", "S2", 30.5, 34.0, True),
        TranscriptChunk("Perfect. Let's also make sure HR sends out the new remote work policy by end of week.", "S1", 34.5, 39.0, True),
        TranscriptChunk("Decision: we're approved to expand the engineering team by 3 headcount in Q4.", "S1", 39.5, 44.0, True),
    ]

    async def transcribe_file(self, path: str) -> list[TranscriptChunk]:
        await asyncio.sleep(0.5)  # simulate processing
        return self.DEMO_TRANSCRIPT

    async def stream(self, audio_gen, on_partial=None) -> AsyncGenerator[TranscriptChunk, None]:
        async for _ in audio_gen:
            pass  # drain
        for chunk in self.DEMO_TRANSCRIPT:
            await asyncio.sleep(0.3)
            yield chunk


# ── Factory ────────────────────────────────────────────────────────────────────

def get_voice_agent():
    if voice_enabled():
        return SpeechmaticsVoiceAgent()
    if OPENAI_API_KEY:
        print("[Voice] Using Whisper fallback")
        return WhisperVoiceAgent()
    print("[Voice] No STT API found — using demo mode")
    return DemoVoiceAgent()


# ── Transcript builder ────────────────────────────────────────────────────────

def build_transcript(chunks: list[TranscriptChunk], speaker_map: dict[str, str] = None) -> str:
    speaker_map = speaker_map or {}
    lines, curr_speaker, curr_words = [], None, []
    for c in chunks:
        name = speaker_map.get(c.speaker_id, c.speaker_id)
        if name != curr_speaker:
            if curr_speaker:
                lines.append(f"{curr_speaker}: {' '.join(curr_words)}")
            curr_speaker = name
            curr_words   = [c.text]
        else:
            curr_words.append(c.text)
    if curr_speaker:
        lines.append(f"{curr_speaker}: {' '.join(curr_words)}")
    return "\n".join(lines)
