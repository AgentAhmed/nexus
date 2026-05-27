"""
NEXUS Voice Intelligence Agent
Priority chain:
  1. Groq Whisper API   — free, fast, cloud (set GROQ_API_KEY)
  2. OpenAI Whisper API — paid, set OPENAI_API_KEY
  3. faster-whisper     — local CPU, truly free, no key needed
  4. Demo mode          — built-in transcript, for testing with zero setup
"""
import asyncio
import io
import os
import tempfile
from dataclasses import dataclass
from typing import AsyncGenerator, Callable

from backend.config import GROQ_API_KEY, OPENAI_API_KEY, STT_PROVIDER


@dataclass
class TranscriptChunk:
    text:       str
    speaker_id: str
    start_time: float
    end_time:   float
    is_final:   bool


# ── Groq Whisper (free, recommended) ─────────────────────────────────────────

class GroqVoiceAgent:
    """Groq Whisper API — free tier, very fast, supports 99 languages."""

    async def transcribe_file(self, path: str) -> list[TranscriptChunk]:
        from groq import AsyncGroq
        client = AsyncGroq(api_key=GROQ_API_KEY)
        with open(path, "rb") as f:
            resp = await client.audio.transcriptions.create(
                file=(os.path.basename(path), f),
                model="whisper-large-v3",
                response_format="verbose_json",
                timestamp_granularities=["segment"],
            )
        chunks = []
        for seg in (resp.segments or []):
            chunks.append(TranscriptChunk(
                text=seg.text.strip(), speaker_id="Speaker",
                start_time=seg.start, end_time=seg.end, is_final=True
            ))
        return chunks

    async def stream(self, audio_gen: AsyncGenerator, on_partial=None) -> AsyncGenerator[TranscriptChunk, None]:
        """Groq doesn't do real-time streaming — collect all audio then transcribe."""
        buf = io.BytesIO()
        async for chunk in audio_gen:
            buf.write(chunk)
        buf.seek(0)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(buf.read())
            path = tmp.name
        try:
            for c in await self.transcribe_file(path):
                yield c
        finally:
            os.unlink(path)


# ── OpenAI Whisper (paid fallback) ────────────────────────────────────────────

class OpenAIVoiceAgent:
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

    async def stream(self, audio_gen, on_partial=None):
        buf = io.BytesIO()
        async for chunk in audio_gen:
            buf.write(chunk)
        buf.seek(0)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(buf.read()); path = tmp.name
        try:
            for c in await self.transcribe_file(path):
                yield c
        finally:
            os.unlink(path)


# ── Local faster-whisper (no API, truly free) ─────────────────────────────────

class LocalVoiceAgent:
    """
    faster-whisper runs on CPU. No API key, no cost, no internet needed.
    Install: pip install faster-whisper
    First run downloads the model (~150MB for 'base', ~1.5GB for 'large-v3').
    Use model_size="base" for fast CPU, "large-v3" for best accuracy.
    """
    def __init__(self, model_size: str = "base"):
        self.model_size = os.getenv("WHISPER_MODEL_SIZE", model_size)
        self._model = None

    def _get_model(self):
        if self._model is None:
            from faster_whisper import WhisperModel
            self._model = WhisperModel(self.model_size, device="cpu", compute_type="int8")
            print(f"[Voice] Local Whisper '{self.model_size}' loaded")
        return self._model

    async def transcribe_file(self, path: str) -> list[TranscriptChunk]:
        model = self._get_model()
        # Run sync in executor to not block event loop
        loop = asyncio.get_event_loop()
        segments, _ = await loop.run_in_executor(None, lambda: model.transcribe(path))
        chunks = []
        for seg in segments:
            chunks.append(TranscriptChunk(
                text=seg.text.strip(), speaker_id="Speaker",
                start_time=seg.start, end_time=seg.end, is_final=True
            ))
        return chunks

    async def stream(self, audio_gen, on_partial=None):
        buf = io.BytesIO()
        async for chunk in audio_gen:
            buf.write(chunk)
        buf.seek(0)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(buf.read()); path = tmp.name
        try:
            for c in await self.transcribe_file(path):
                yield c
        finally:
            os.unlink(path)


# ── Demo mode (zero setup, for testing) ───────────────────────────────────────

class DemoVoiceAgent:
    DEMO = [
        TranscriptChunk("Let's start the Q3 business review.", "Sarah", 0, 3, True),
        TranscriptChunk("Cloud infrastructure spend is 12% over budget this quarter.", "John", 3.5, 8, True),
        TranscriptChunk("John, can you prepare a detailed cost breakdown report by Friday?", "Sarah", 8.5, 12, True),
        TranscriptChunk("Sure. I'll also look at optimising our API usage costs.", "John", 12.5, 16, True),
        TranscriptChunk("The GDPR compliance audit is due next month. All vendor contracts need legal review.", "Maria", 16.5, 22, True),
        TranscriptChunk("I'll schedule a legal review session for this week.", "Sarah", 22.5, 26, True),
        TranscriptChunk("Decision: Q4 engineering headcount expansion approved — 3 new hires.", "Sarah", 26.5, 31, True),
        TranscriptChunk("HR should post the job descriptions by end of this week.", "John", 31.5, 35, True),
        TranscriptChunk("Agreed. Also, marketing needs to launch the Q4 campaign by October 15th.", "Sarah", 35.5, 40, True),
    ]

    async def transcribe_file(self, path: str) -> list[TranscriptChunk]:
        await asyncio.sleep(0.3)
        return self.DEMO

    async def stream(self, audio_gen, on_partial=None):
        async for _ in audio_gen:
            pass
        for c in self.DEMO:
            await asyncio.sleep(0.2)
            yield c


# ── Factory ────────────────────────────────────────────────────────────────────

def get_voice_agent():
    if STT_PROVIDER == "groq" and GROQ_API_KEY:
        print("[Voice] Using Groq Whisper (free)")
        return GroqVoiceAgent()
    if STT_PROVIDER == "openai" and OPENAI_API_KEY:
        print("[Voice] Using OpenAI Whisper")
        return OpenAIVoiceAgent()
    if STT_PROVIDER == "local":
        print("[Voice] Using local faster-whisper (CPU)")
        return LocalVoiceAgent()
    print("[Voice] Using demo mode — set GROQ_API_KEY for real transcription")
    return DemoVoiceAgent()


# ── Helpers ────────────────────────────────────────────────────────────────────

def build_transcript(chunks: list[TranscriptChunk], speaker_map: dict = None) -> str:
    speaker_map = speaker_map or {}
    lines, curr_speaker, curr_words = [], None, []
    for c in chunks:
        name = speaker_map.get(c.speaker_id, c.speaker_id)
        if name != curr_speaker:
            if curr_speaker:
                lines.append(f"{curr_speaker}: {' '.join(curr_words)}")
            curr_speaker, curr_words = name, [c.text]
        else:
            curr_words.append(c.text)
    if curr_speaker:
        lines.append(f"{curr_speaker}: {' '.join(curr_words)}")
    return "\n".join(lines)
