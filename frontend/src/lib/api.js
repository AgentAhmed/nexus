"use client";
import { useEffect, useRef, useState, useCallback } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const WS  = process.env.NEXT_PUBLIC_WS_URL  || "ws://localhost:8000";

// ── API helpers ────────────────────────────────────────────────────────────────

export async function apiPost(path, body) {
  const r = await fetch(`${API}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function apiPostForm(path, formData) {
  const r = await fetch(`${API}${path}`, { method: "POST", body: formData });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function apiGet(path) {
  const r = await fetch(`${API}${path}`);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

// ── Dashboard WebSocket hook ───────────────────────────────────────────────────

export function useDashboardWS(onMessage) {
  const wsRef    = useRef(null);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    let ws;
    let retryTimer;

    const connect = () => {
      ws = new WebSocket(`${WS}/ws/dashboard`);
      wsRef.current = ws;

      ws.onopen    = () => setConnected(true);
      ws.onclose   = () => { setConnected(false); retryTimer = setTimeout(connect, 3000); };
      ws.onerror   = () => ws.close();
      ws.onmessage = (e) => { try { onMessage(JSON.parse(e.data)); } catch {} };
    };

    connect();
    return () => { clearTimeout(retryTimer); ws?.close(); };
  }, []);

  return connected;
}

// ── Voice recording hook ───────────────────────────────────────────────────────

export function useVoiceRecorder(threadId, onChunk) {
  const [recording, setRecording] = useState(false);
  const wsRef      = useRef(null);
  const mediaRef   = useRef(null);
  const processorRef = useRef(null);
  const ctxRef     = useRef(null);

  const start = useCallback(async () => {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const ctx    = new AudioContext({ sampleRate: 16000 });
    ctxRef.current = ctx;

    const ws = new WebSocket(`${WS}/ws/voice/${threadId}`);
    wsRef.current = ws;
    ws.onmessage = (e) => { try { onChunk(JSON.parse(e.data)); } catch {} };

    await new Promise(r => { ws.onopen = r; });

    const source    = ctx.createMediaStreamSource(stream);
    const processor = ctx.createScriptProcessor(4096, 1, 1);
    processorRef.current = processor;
    mediaRef.current     = stream;

    processor.onaudioprocess = (e) => {
      if (ws.readyState !== WebSocket.OPEN) return;
      const f32 = e.inputBuffer.getChannelData(0);
      ws.send(f32.buffer);
    };

    source.connect(processor);
    processor.connect(ctx.destination);
    setRecording(true);
  }, [threadId, onChunk]);

  const stop = useCallback(() => {
    processorRef.current?.disconnect();
    ctxRef.current?.close();
    mediaRef.current?.getTracks().forEach(t => t.stop());
    wsRef.current?.close();
    setRecording(false);
  }, []);

  return { recording, start, stop };
}
