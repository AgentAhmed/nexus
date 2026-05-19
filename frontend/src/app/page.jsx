"use client";
import { useState, useCallback, useRef, useEffect } from "react";
import {
  Mic, MicOff, Upload, Play, RefreshCw, Activity,
  CheckCircle, Clock, AlertTriangle, FileText, Zap,
  BarChart3, Users, Shield, DollarSign, Settings
} from "lucide-react";
import { useDashboardWS, useVoiceRecorder, apiPost, apiPostForm, apiGet } from "../lib/api";

// ── Helpers ────────────────────────────────────────────────────────────────────

const DOMAIN_META = {
  legal:   { icon: Shield,      color: "text-yellow-400", bg: "bg-yellow-400/10",  label: "Legal"   },
  finance: { icon: DollarSign,  color: "text-green-400",  bg: "bg-green-400/10",   label: "Finance" },
  hr:      { icon: Users,       color: "text-blue-400",   bg: "bg-blue-400/10",    label: "HR"      },
  ops:     { icon: Settings,    color: "text-purple-400", bg: "bg-purple-400/10",  label: "Ops"     },
  general: { icon: FileText,    color: "text-gray-400",   bg: "bg-gray-400/10",    label: "General" },
};

function Badge({ children, variant = "default" }) {
  const styles = {
    default: "bg-gray-800 text-gray-300",
    success: "bg-green-900/50 text-green-300",
    warning: "bg-yellow-900/50 text-yellow-300",
    error:   "bg-red-900/50 text-red-300",
    nexus:   "bg-nexus/20 text-nexus-light",
  };
  return (
    <span className={`badge ${styles[variant]}`}>{children}</span>
  );
}

function MetricCard({ label, value, sub, icon: Icon, color = "text-nexus" }) {
  return (
    <div className="agent-card flex items-start gap-3">
      <div className={`mt-0.5 ${color}`}><Icon size={18} /></div>
      <div>
        <p className="text-xs text-gray-500 mb-0.5">{label}</p>
        <p className="text-xl font-semibold text-white">{value}</p>
        {sub && <p className="text-xs text-gray-500 mt-0.5">{sub}</p>}
      </div>
    </div>
  );
}

function AgentTimeline({ events }) {
  return (
    <div className="space-y-2 max-h-64 overflow-y-auto pr-1">
      {events.length === 0 && (
        <p className="text-gray-500 text-sm text-center py-6">No agent activity yet. Run a transcript to see agent steps.</p>
      )}
      {events.map((e, i) => (
        <div key={i} className="flex gap-3 items-start">
          <div className="w-1.5 h-1.5 rounded-full bg-nexus mt-2 flex-shrink-0" />
          <div>
            <span className="text-xs font-medium text-nexus-light">{e.agent}</span>
            <span className="text-xs text-gray-400 ml-2">{e.latency}ms</span>
            <p className="text-xs text-gray-300 mt-0.5">{e.note}</p>
          </div>
        </div>
      ))}
    </div>
  );
}

// ── Main Page ──────────────────────────────────────────────────────────────────

export default function Home() {
  const threadId  = useRef(`session-${Date.now()}`);
  const [transcript,     setTranscript]     = useState("");
  const [liveTranscript, setLiveTranscript] = useState([]);
  const [result,         setResult]         = useState(null);
  const [loading,        setLoading]        = useState(false);
  const [status,         setStatus]         = useState("");
  const [metrics,        setMetrics]        = useState({});
  const [agentEvents,    setAgentEvents]    = useState([]);
  const [activeTab,      setActiveTab]      = useState("transcript");
  const [dragOver,       setDragOver]       = useState(false);

  // ── WebSocket ────────────────────────────────────────────────────────────────
  const connected = useDashboardWS(useCallback((msg) => {
    if (msg.type === "METRICS_UPDATE") {
      setMetrics(msg);
    }
    if (msg.type === "PROCESSING_COMPLETE") {
      setResult(msg);
      setLoading(false);
      setStatus("Complete");
      // Build agent timeline from result
      const events = [
        { agent: "Intent Extractor",   latency: metrics.avg_latency_ms?.intent_agent   || "—", note: `Domain: ${msg.domain}, Confidence: ${(msg.confidence * 100).toFixed(0)}%` },
        { agent: "Context Agent (RAG)",latency: metrics.avg_latency_ms?.rag_agent       || "—", note: `${msg.action_items?.length || 0} action items enriched with enterprise KB` },
        { agent: `${DOMAIN_META[msg.domain]?.label || "Domain"} Agent`, latency: metrics.avg_latency_ms?.[`domain_${msg.domain}`] || "—", note: msg.domain_analysis ? "Analysis complete" : "No analysis" },
        { agent: "Execution Agent",    latency: metrics.avg_latency_ms?.execution_agent || "—", note: `${msg.executions_done?.length || 0} actions executed` },
      ];
      setAgentEvents(prev => [...events, ...prev].slice(0, 20));
    }
    if (msg.type === "VOICE_PARTIAL") {
      setLiveTranscript(prev => {
        const updated = [...prev];
        if (updated.length && updated[updated.length - 1].speaker === msg.speaker && !updated[updated.length - 1].final) {
          updated[updated.length - 1] = { ...updated[updated.length - 1], text: msg.text };
        } else {
          updated.push({ speaker: msg.speaker, text: msg.text, final: false });
        }
        return updated;
      });
    }
    if (msg.type === "VOICE_FINAL") {
      setLiveTranscript(prev => {
        const updated = [...prev];
        if (updated.length && !updated[updated.length - 1].final) {
          updated[updated.length - 1] = { speaker: msg.speaker, text: msg.text, final: true };
        } else {
          updated.push({ speaker: msg.speaker, text: msg.text, final: true });
        }
        return updated;
      });
    }
    if (msg.type === "NEXUS_RESULT") {
      setResult(msg);
      setLoading(false);
      setStatus("Complete");
    }
  }, [metrics]));

  // ── Voice ────────────────────────────────────────────────────────────────────
  const { recording, start: startVoice, stop: stopVoice } = useVoiceRecorder(
    threadId.current,
    useCallback((chunk) => {}, [])
  );

  // ── Process transcript ────────────────────────────────────────────────────────
  const handleProcess = async () => {
    if (!transcript.trim()) return;
    setLoading(true); setResult(null); setStatus("Processing…");
    try {
      await apiPost("/api/process", { transcript, thread_id: threadId.current });
    } catch (e) {
      setStatus(`Error: ${e.message}`); setLoading(false);
    }
  };

  // ── Demo mode ─────────────────────────────────────────────────────────────────
  const handleDemo = async () => {
    setLoading(true); setResult(null); setStatus("Running demo…");
    try {
      const data = await apiPost("/api/demo", {});
      setTranscript(data.transcript || "");
      // Result comes via WebSocket broadcast
    } catch (e) {
      setStatus(`Error: ${e.message}`); setLoading(false);
    }
  };

  // ── File upload ───────────────────────────────────────────────────────────────
  const handleFileUpload = async (files) => {
    const audioExts = ["wav","mp3","mp4","m4a","ogg","webm","flac"];
    const docExts   = ["pdf","docx","txt","md"];
    for (const file of files) {
      const ext = file.name.rsplit?.(".")?.at(-1)?.toLowerCase() || file.name.split(".").pop().toLowerCase();
      const fd  = new FormData();
      if (audioExts.includes(ext)) {
        fd.append("file", file);
        setLoading(true); setStatus(`Transcribing ${file.name}…`);
        try {
          const r = await apiPostForm("/api/upload-audio", fd);
          if (r.transcript) setTranscript(r.transcript);
          setLoading(false); setStatus("Transcription complete");
        } catch (e) { setStatus(`Error: ${e.message}`); setLoading(false); }
      } else if (docExts.includes(ext)) {
        fd.append("files", file);
        setStatus(`Ingesting ${file.name} into knowledge base…`);
        try {
          await apiPostForm("/api/ingest-docs", fd);
          setStatus(`${file.name} added to knowledge base`);
        } catch (e) { setStatus(`Error: ${e.message}`); }
      }
    }
  };

  const domain = result?.domain || "general";
  const DomainIcon = DOMAIN_META[domain]?.icon || FileText;
  const domainColor = DOMAIN_META[domain]?.color || "text-gray-400";

  return (
    <div className="min-h-screen bg-gray-950 flex flex-col">

      {/* Header */}
      <header className="border-b border-gray-800 px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-nexus flex items-center justify-center">
            <Zap size={16} className="text-white" />
          </div>
          <span className="font-semibold text-white tracking-tight">NEXUS</span>
          <span className="text-xs text-gray-500 ml-1">Enterprise Intelligence</span>
        </div>
        <div className="flex items-center gap-3">
          {connected
            ? <span className="flex items-center gap-1.5 text-xs text-green-400"><span className="pulse-dot" />Live</span>
            : <span className="text-xs text-gray-500">Connecting…</span>
          }
          <span className="text-xs text-gray-600">by Andromeda · AI Agent Olympics 2026</span>
        </div>
      </header>

      <div className="flex-1 grid grid-cols-12 gap-0 h-[calc(100vh-52px)]">

        {/* Left panel — Input */}
        <div className="col-span-5 border-r border-gray-800 flex flex-col">
          <div className="flex border-b border-gray-800">
            {["transcript","live","upload"].map(tab => (
              <button key={tab} onClick={() => setActiveTab(tab)}
                className={`px-4 py-2.5 text-xs font-medium capitalize transition-colors ${activeTab===tab ? "text-white border-b-2 border-nexus" : "text-gray-500 hover:text-gray-300"}`}>
                {tab === "live" ? "🎙 Live Voice" : tab === "upload" ? "📎 Upload" : "📝 Transcript"}
              </button>
            ))}
          </div>

          {activeTab === "transcript" && (
            <div className="flex flex-col flex-1 p-4 gap-3">
              <textarea
                className="flex-1 bg-gray-900 border border-gray-800 rounded-lg p-3 text-sm text-gray-200 resize-none focus:outline-none focus:border-nexus font-mono"
                placeholder="Paste your meeting transcript here…&#10;&#10;Example:&#10;John: Let's review the Q3 numbers…&#10;Sarah: Budget is 12% over on cloud spend…"
                value={transcript}
                onChange={e => setTranscript(e.target.value)}
              />
              <div className="flex gap-2">
                <button onClick={handleProcess} disabled={loading || !transcript.trim()}
                  className="flex-1 flex items-center justify-center gap-2 bg-nexus hover:bg-nexus-dark disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-medium py-2.5 rounded-lg transition-colors">
                  {loading ? <RefreshCw size={14} className="animate-spin" /> : <Play size={14} />}
                  {loading ? status : "Run NEXUS"}
                </button>
                <button onClick={handleDemo} disabled={loading}
                  className="px-4 py-2.5 border border-gray-700 hover:border-nexus text-gray-300 text-sm rounded-lg transition-colors">
                  Demo
                </button>
              </div>
            </div>
          )}

          {activeTab === "live" && (
            <div className="flex flex-col flex-1 p-4 gap-3">
              <div className="flex-1 bg-gray-900 border border-gray-800 rounded-lg p-3 overflow-y-auto space-y-2">
                {liveTranscript.length === 0 && (
                  <p className="text-gray-500 text-sm text-center pt-8">Click Start to begin recording…</p>
                )}
                {liveTranscript.map((c, i) => (
                  <div key={i} className={`${!c.final ? "opacity-50" : ""}`}>
                    <span className="text-xs font-medium text-nexus-light">{c.speaker}: </span>
                    <span className="text-sm text-gray-200">{c.text}</span>
                  </div>
                ))}
              </div>
              <button
                onClick={recording ? stopVoice : startVoice}
                className={`flex items-center justify-center gap-2 text-sm font-medium py-2.5 rounded-lg transition-colors ${
                  recording ? "bg-red-600 hover:bg-red-700 text-white" : "bg-nexus hover:bg-nexus-dark text-white"
                }`}>
                {recording ? <><MicOff size={14} /> Stop Recording</> : <><Mic size={14} /> Start Recording</>}
              </button>
            </div>
          )}

          {activeTab === "upload" && (
            <div className="flex flex-col flex-1 p-4 gap-3">
              <div
                onDrop={e => { e.preventDefault(); setDragOver(false); handleFileUpload([...e.dataTransfer.files]); }}
                onDragOver={e => { e.preventDefault(); setDragOver(true); }}
                onDragLeave={() => setDragOver(false)}
                className={`flex-1 border-2 border-dashed rounded-lg flex flex-col items-center justify-center gap-3 cursor-pointer transition-colors ${
                  dragOver ? "border-nexus bg-nexus/5" : "border-gray-700 hover:border-gray-600"
                }`}
                onClick={() => document.getElementById("file-input").click()}>
                <Upload size={24} className="text-gray-500" />
                <div className="text-center">
                  <p className="text-sm text-gray-300">Drop files here or click to browse</p>
                  <p className="text-xs text-gray-500 mt-1">Audio: WAV, MP3, M4A · Docs: PDF, DOCX, TXT</p>
                  <p className="text-xs text-gray-600 mt-0.5">Audio → transcribe + process · Docs → add to knowledge base</p>
                </div>
                <input id="file-input" type="file" multiple className="hidden"
                  accept=".wav,.mp3,.mp4,.m4a,.ogg,.webm,.flac,.pdf,.docx,.txt,.md"
                  onChange={e => handleFileUpload([...e.target.files])} />
              </div>
              {status && (
                <div className="bg-gray-900 border border-gray-800 rounded-lg px-3 py-2 text-xs text-gray-300">{status}</div>
              )}
            </div>
          )}
        </div>

        {/* Right panels */}
        <div className="col-span-7 flex flex-col overflow-hidden">

          {/* Results */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">

            {/* No result state */}
            {!result && !loading && (
              <div className="flex flex-col items-center justify-center h-full gap-4 text-center">
                <div className="w-16 h-16 rounded-2xl bg-nexus/10 flex items-center justify-center">
                  <Zap size={28} className="text-nexus" />
                </div>
                <div>
                  <p className="text-white font-medium">Ready to analyse your meeting</p>
                  <p className="text-gray-500 text-sm mt-1">Paste a transcript, record live audio, or click Demo to see NEXUS in action</p>
                </div>
              </div>
            )}

            {/* Loading */}
            {loading && (
              <div className="flex items-center gap-3 bg-gray-900 border border-gray-800 rounded-xl p-4">
                <RefreshCw size={18} className="text-nexus animate-spin" />
                <span className="text-sm text-gray-300">{status || "Agents working…"}</span>
              </div>
            )}

            {/* Result */}
            {result && (
              <>
                {/* Domain + confidence */}
                <div className="agent-card flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className={`p-2 rounded-lg ${DOMAIN_META[domain]?.bg}`}>
                      <DomainIcon size={18} className={domainColor} />
                    </div>
                    <div>
                      <p className="text-sm font-medium text-white">{DOMAIN_META[domain]?.label} Domain</p>
                      <p className="text-xs text-gray-500">Confidence: {((result.confidence || 0) * 100).toFixed(0)}%</p>
                    </div>
                  </div>
                  <div className="flex gap-2">
                    {result.pending_approvals?.length > 0 && <Badge variant="warning">⚠ Needs approval</Badge>}
                    {result.executions_done?.length > 0 && <Badge variant="success">✓ {result.executions_done.length} executed</Badge>}
                  </div>
                </div>

                {/* Decisions */}
                {result.decisions?.length > 0 && (
                  <div className="agent-card">
                    <h3 className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-3">Decisions Made</h3>
                    <ul className="space-y-2">
                      {result.decisions.map((d, i) => (
                        <li key={i} className="flex gap-2 text-sm text-gray-200">
                          <CheckCircle size={14} className="text-green-400 mt-0.5 flex-shrink-0" />
                          {d}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Action items */}
                {result.action_items?.length > 0 && (
                  <div className="agent-card">
                    <h3 className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-3">Action Items</h3>
                    <ul className="space-y-2">
                      {result.action_items.map((a, i) => {
                        const executed = result.executions_done?.find(e => e.action === a);
                        const pending  = result.pending_approvals?.includes(a);
                        return (
                          <li key={i} className="flex gap-2 items-start text-sm">
                            {executed
                              ? <CheckCircle size={14} className="text-green-400 mt-0.5 flex-shrink-0" />
                              : pending
                              ? <Clock size={14} className="text-yellow-400 mt-0.5 flex-shrink-0" />
                              : <div className="w-3.5 h-3.5 rounded-full border border-gray-600 mt-0.5 flex-shrink-0" />
                            }
                            <span className="text-gray-200">{a}</span>
                            {executed && (
                              <span className="text-xs text-gray-500 ml-auto whitespace-nowrap">via {executed.channel}</span>
                            )}
                          </li>
                        );
                      })}
                    </ul>
                  </div>
                )}

                {/* Pending approvals */}
                {result.pending_approvals?.length > 0 && (
                  <div className="agent-card border-yellow-800">
                    <h3 className="text-xs font-medium text-yellow-500 uppercase tracking-wider mb-3">
                      <AlertTriangle size={12} className="inline mr-1" />Needs Your Approval
                    </h3>
                    <ul className="space-y-2">
                      {result.pending_approvals.map((a, i) => (
                        <li key={i} className="flex gap-2 items-center">
                          <span className="flex-1 text-sm text-gray-200">{a}</span>
                          <button
                            onClick={() => apiPost("/api/approve", { thread_id: result.thread_id, action_item: a })}
                            className="text-xs px-3 py-1 bg-nexus hover:bg-nexus-dark text-white rounded-md transition-colors">
                            Approve
                          </button>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Executions */}
                {result.executions_done?.length > 0 && (
                  <div className="agent-card">
                    <h3 className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-3">Autonomous Executions</h3>
                    <div className="space-y-2">
                      {result.executions_done.map((e, i) => (
                        <div key={i} className="flex gap-2 items-start">
                          <span className={`text-xs px-2 py-0.5 rounded-full ${e.status === "success" ? "bg-green-900/50 text-green-300" : e.status === "simulated" ? "bg-gray-800 text-gray-400" : "bg-red-900/50 text-red-300"}`}>
                            {e.channel || "—"}
                          </span>
                          <span className="text-xs text-gray-400 flex-1">{e.detail}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </>
            )}
          </div>

          {/* Bottom strip — metrics + agent activity */}
          <div className="border-t border-gray-800 grid grid-cols-2 divide-x divide-gray-800">
            {/* Metrics */}
            <div className="p-3">
              <p className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                <BarChart3 size={11} />Metrics
              </p>
              <div className="grid grid-cols-3 gap-2">
                <div className="bg-gray-900 rounded-lg px-2.5 py-2">
                  <p className="text-xs text-gray-500">Sessions</p>
                  <p className="text-sm font-semibold text-white">{metrics.sessions || 0}</p>
                </div>
                <div className="bg-gray-900 rounded-lg px-2.5 py-2">
                  <p className="text-xs text-gray-500">Executions</p>
                  <p className="text-sm font-semibold text-white">{metrics.executions || 0}</p>
                </div>
                <div className="bg-gray-900 rounded-lg px-2.5 py-2">
                  <p className="text-xs text-gray-500">RAG Score</p>
                  <p className="text-sm font-semibold text-white">{metrics.avg_rag_score || "—"}</p>
                </div>
              </div>
            </div>
            {/* Agent activity */}
            <div className="p-3">
              <p className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                <Activity size={11} />Agent Pipeline
              </p>
              <div className="space-y-1.5 max-h-20 overflow-y-auto">
                {agentEvents.slice(0, 4).map((e, i) => (
                  <div key={i} className="flex items-center gap-2">
                    <div className="w-1.5 h-1.5 rounded-full bg-nexus flex-shrink-0" />
                    <span className="text-xs text-gray-400 truncate">{e.agent}</span>
                    {e.latency !== "—" && <span className="text-xs text-gray-600 ml-auto whitespace-nowrap">{e.latency}ms</span>}
                  </div>
                ))}
                {agentEvents.length === 0 && <p className="text-xs text-gray-600">Agent steps appear here…</p>}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
