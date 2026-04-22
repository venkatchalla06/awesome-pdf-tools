"use client";
import React, { useState, useRef, useCallback, useEffect } from "react";
import {
  ChevronLeft, ChevronRight, Copy, Check, Download,
  FileDown, GitCompare, ZoomIn, ZoomOut, Table2,
  FileText, LayoutTemplate,
} from "lucide-react";
import DocViewer, { DocViewerHandle } from "@/components/DocViewer";
import ChangePanel, { Change } from "@/components/ChangePanel";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

type Span = {
  type: "equal" | "insert" | "delete" | "replace" | "move_from" | "move_to";
  text: string; offset: number; length: number; context?: string; move_id?: number;
};
type Notes = Record<string, { note: string; tag: string }>;
type Result = {
  id: string; file_a_name: string; file_b_name: string;
  original_spans: Span[]; revised_spans: Span[];
  summary: { additions: number; deletions: number; modifications: number; moves: number; total: number };
  notes?: Notes;
};

const CHANGE_TYPES = new Set(["insert", "delete", "replace", "move_from", "move_to"]);

function buildChanges(spans: Span[]): Change[] {
  const out: Change[] = [];
  spans.forEach((span, idx) => {
    if (CHANGE_TYPES.has(span.type) && span.text.trim())
      out.push({ index: out.length, spanIdx: idx, type: span.type as Change["type"], preview: span.text.slice(0, 120).trim() });
  });
  return out;
}

function useDebounce<T>(v: T, ms: number) {
  const [dv, setDv] = useState(v);
  useEffect(() => { const t = setTimeout(() => setDv(v), ms); return () => clearTimeout(t); }, [v, ms]);
  return dv;
}

function DropZoneSimple({ label, file, onFile, color }: { label: string; file: File | null; onFile: (f: File) => void; color: string }) {
  const ref = useRef<HTMLInputElement>(null);
  return (
    <div
      className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-colors
        ${file ? "border-green-400 bg-green-50" : `border-${color}-300 hover:border-${color}-400 hover:bg-${color}-50`}`}
      onClick={() => ref.current?.click()}
      onDrop={e => { e.preventDefault(); const f = e.dataTransfer.files[0]; if (f) onFile(f); }}
      onDragOver={e => e.preventDefault()}
    >
      <input ref={ref} type="file" className="hidden"
        accept=".pdf,.docx,.doc,.txt,.xlsx,.html,.htm,.md"
        onChange={e => { const f = e.target.files?.[0]; if (f) onFile(f); }} />
      {file
        ? <p className="text-sm font-medium text-green-700">✓ {file.name}</p>
        : <>
            <p className="text-sm font-semibold text-gray-600">{label}</p>
            <p className="text-xs text-gray-400 mt-1">PDF, DOCX, TXT, XLSX, HTML, MD</p>
          </>
      }
    </div>
  );
}

export default function ComparePage() {
  const [appState, setAppState] = useState<"upload" | "loading" | "result" | "error">("upload");
  const [fileA, setFileA] = useState<File | null>(null);
  const [fileB, setFileB] = useState<File | null>(null);
  const [result, setResult] = useState<Result | null>(null);
  const [error, setError] = useState("");
  const [curChange, setCurChange] = useState(0);
  const [copied, setCopied] = useState(false);
  const [progress, setProgress] = useState(0);
  const [notes, setNotes] = useState<Notes>({});
  const [zoom, setZoom] = useState(1);
  const [showPanel, setShowPanel] = useState(true);

  const origRef = useRef<DocViewerHandle>(null);
  const revRef = useRef<DocViewerHandle>(null);
  const syncLock = useRef(false);

  const allChanges = result ? buildChanges(result.original_spans) : [];
  const changeSpanIndices = allChanges.map(c => c.spanIdx);

  const debouncedNotes = useDebounce(notes, 1500);
  useEffect(() => {
    if (!result || !Object.keys(debouncedNotes).length) return;
    fetch(`${API}/compare/${result.id}/notes`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ notes: debouncedNotes }),
    }).catch(() => {});
  }, [debouncedNotes, result?.id]);

  useEffect(() => {
    if (appState !== "result") return;
    const h = (e: KeyboardEvent) => {
      if (!e.ctrlKey && !e.metaKey) return;
      if (e.key === "ArrowRight") { e.preventDefault(); setCurChange(c => Math.min(allChanges.length - 1, c + 1)); }
      if (e.key === "ArrowLeft") { e.preventDefault(); setCurChange(c => Math.max(0, c - 1)); }
      if (e.key === "=") { e.preventDefault(); setZoom(z => Math.min(1.5, +(z + 0.1).toFixed(1))); }
      if (e.key === "-") { e.preventDefault(); setZoom(z => Math.max(0.6, +(z - 0.1).toFixed(1))); }
    };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, [appState, allChanges.length]);

  const handleCompare = async () => {
    if (!fileA || !fileB) return;
    setAppState("loading"); setProgress(10);
    try {
      const tick = setInterval(() => setProgress(p => Math.min(p + 8, 85)), 400);
      const form = new FormData();
      form.append("file_a", fileA);
      form.append("file_b", fileB);
      const cmpRes = await fetch(`${API}/compare`, { method: "POST", body: form });
      if (!cmpRes.ok) throw new Error((await cmpRes.json()).detail || "Comparison failed");
      const cmp = await cmpRes.json();
      clearInterval(tick); setProgress(95);
      const fullRes = await fetch(`${API}/compare/${cmp.id}`);
      const full: Result = await fullRes.json();
      setProgress(100); setResult(full);
      setNotes(full.notes ?? {}); setCurChange(0); setAppState("result");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Comparison failed");
      setAppState("error");
    }
  };

  const handleScroll = useCallback((from: "orig" | "rev", top: number) => {
    if (syncLock.current) return;
    syncLock.current = true;
    if (from === "orig") revRef.current?.scrollTo(top);
    else origRef.current?.scrollTo(top);
    setTimeout(() => { syncLock.current = false; }, 50);
  }, []);

  const navigate = (dir: 1 | -1) =>
    setCurChange(c => Math.max(0, Math.min(allChanges.length - 1, c + dir)));

  const reset = () => {
    setFileA(null); setFileB(null); setResult(null);
    setNotes({}); setError(""); setAppState("upload"); setProgress(0); setZoom(1);
  };

  if (appState === "upload" || appState === "error") return (
    <div className="min-h-screen flex flex-col bg-gray-100">
      <header className="bg-[#1e3a5f] text-white px-6 py-3.5 flex items-center gap-3 shadow-lg">
        <GitCompare className="w-6 h-6 text-blue-300" />
        <span className="text-lg font-bold tracking-tight">Compare Documents</span>
      </header>
      <main className="flex-1 flex items-center justify-center px-4 py-16">
        <div className="bg-white rounded-2xl shadow-2xl p-10 w-full max-w-xl">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-10 h-10 bg-[#1e3a5f] rounded-xl flex items-center justify-center">
              <GitCompare className="w-5 h-5 text-blue-300" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-gray-900">Compare Documents</h1>
              <p className="text-xs text-gray-500">Word-level diff — PDF, DOCX, TXT, XLSX, HTML, MD</p>
            </div>
          </div>
          <div className="flex flex-col gap-4">
            <DropZoneSimple label="Original Document" file={fileA} onFile={setFileA} color="blue" />
            <div className="flex items-center gap-3">
              <div className="flex-1 h-px bg-gray-200" />
              <span className="text-xs text-gray-400 font-medium">vs</span>
              <div className="flex-1 h-px bg-gray-200" />
            </div>
            <DropZoneSimple label="Revised Document" file={fileB} onFile={setFileB} color="green" />
          </div>
          {appState === "error" && (
            <div className="mt-5 p-4 bg-red-50 border border-red-200 rounded-xl text-sm text-red-700">
              ⚠ {error}
            </div>
          )}
          <button onClick={handleCompare} disabled={!fileA || !fileB}
            className="mt-7 w-full py-3.5 rounded-xl bg-[#1e3a5f] hover:bg-[#162d4a] text-white
              font-semibold text-base transition disabled:opacity-40 disabled:cursor-not-allowed shadow-md">
            Compare →
          </button>
          <div className="mt-6 grid grid-cols-3 gap-2 text-center">
            {[["🔍","Word-level diff"],["⇅","Move detection"],["📄","DOCX export"],
              ["🔗","Shareable links"],["🏷️","Notes & tags"],["📊","CSV report"]
            ].map(([icon, label]) => (
              <div key={label} className="text-xs text-gray-500 bg-gray-50 rounded-lg py-2 px-1">
                <div className="text-base mb-0.5">{icon}</div>{label}
              </div>
            ))}
          </div>
        </div>
      </main>
    </div>
  );

  if (appState === "loading") return (
    <div className="min-h-screen flex flex-col bg-gray-100">
      <header className="bg-[#1e3a5f] text-white px-6 py-3.5 flex items-center gap-3 shadow-lg">
        <GitCompare className="w-6 h-6 text-blue-300" />
        <span className="text-lg font-bold">Compare Documents</span>
      </header>
      <main className="flex-1 flex items-center justify-center">
        <div className="bg-white rounded-2xl shadow-xl p-10 w-full max-w-sm text-center">
          <svg className="animate-spin w-12 h-12 mx-auto mb-5 text-[#1e3a5f]" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2.5" strokeOpacity="0.15"/>
            <path d="M12 2a10 10 0 0 1 10 10" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"/>
          </svg>
          <h2 className="text-base font-bold text-gray-800 mb-1">Comparing documents…</h2>
          <p className="text-xs text-gray-500 mb-5">Extracting text · detecting moves · computing diff</p>
          <div className="w-full bg-gray-100 rounded-full h-1.5">
            <div className="bg-[#1e3a5f] h-1.5 rounded-full transition-all duration-300" style={{ width: `${progress}%` }} />
          </div>
        </div>
      </main>
    </div>
  );

  if (!result) return null;

  return (
    <div className="h-screen flex flex-col" style={{ background: "#1a202c" }}>
      <header className="flex items-center gap-1 px-3 py-1.5 bg-[#1e3a5f] shadow-lg flex-shrink-0 border-b border-[#162d4a]">
        <div className="flex items-center gap-2 pr-3 border-r border-white/10 mr-1">
          <GitCompare className="w-5 h-5 text-blue-300" />
          <span className="text-sm font-bold text-white hidden md:block">DocCompare</span>
        </div>
        <div className="hidden lg:flex items-center gap-1.5 text-xs text-slate-400 mr-2">
          <FileText className="w-3.5 h-3.5" />
          <span className="max-w-[120px] truncate">{result.file_a_name}</span>
          <span className="text-slate-600">vs</span>
          <FileText className="w-3.5 h-3.5" />
          <span className="max-w-[120px] truncate">{result.file_b_name}</span>
        </div>
        <div className="flex-1" />
        <div className="flex items-center bg-white/10 rounded-md px-1 gap-0.5 mr-1">
          <button className="toolbar-btn px-2 py-1" onClick={() => setZoom(z => Math.max(0.6, +(z - 0.1).toFixed(1)))}>
            <ZoomOut className="w-3.5 h-3.5" />
          </button>
          <span className="text-xs text-slate-300 font-mono w-10 text-center select-none">{Math.round(zoom * 100)}%</span>
          <button className="toolbar-btn px-2 py-1" onClick={() => setZoom(z => Math.min(1.5, +(z + 0.1).toFixed(1)))}>
            <ZoomIn className="w-3.5 h-3.5" />
          </button>
        </div>
        <div className="flex items-center bg-white/10 rounded-md gap-0.5 mr-1">
          <button className="toolbar-btn px-2 py-1.5" onClick={() => navigate(-1)} disabled={curChange === 0}>
            <ChevronLeft className="w-4 h-4" />
          </button>
          <span className="text-xs font-mono text-slate-200 tabular-nums px-1 min-w-[54px] text-center">
            {allChanges.length === 0 ? "No Δ" : `${curChange + 1} / ${allChanges.length}`}
          </span>
          <button className="toolbar-btn px-2 py-1.5" onClick={() => navigate(1)} disabled={curChange >= allChanges.length - 1}>
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
        <div className="w-px h-5 bg-white/10 mx-1" />
        <button className={`toolbar-btn ${showPanel ? "bg-white/20" : ""}`} onClick={() => setShowPanel(v => !v)}>
          <LayoutTemplate className="w-3.5 h-3.5" /><span className="hidden md:block">Changes</span>
        </button>
        <button className="toolbar-btn" onClick={() => { navigator.clipboard.writeText(window.location.href); setCopied(true); setTimeout(() => setCopied(false), 2000); }}>
          {copied ? <Check className="w-3.5 h-3.5 text-green-300" /> : <Copy className="w-3.5 h-3.5" />}
          <span className="hidden md:block">{copied ? "Copied!" : "Share"}</span>
        </button>
        <button className="toolbar-btn" onClick={() => window.open(`${API}/compare/${result.id}/export/docx`, "_blank")}>
          <FileDown className="w-3.5 h-3.5" /><span className="hidden md:block">DOCX</span>
        </button>
        <button className="toolbar-btn" onClick={() => window.open(`${API}/compare/${result.id}/export/csv`, "_blank")}>
          <Table2 className="w-3.5 h-3.5" /><span className="hidden md:block">CSV</span>
        </button>
        <div className="w-px h-5 bg-white/10 mx-1" />
        <button className="toolbar-btn text-slate-400 hover:text-white" onClick={reset}>New</button>
      </header>

      <div className="flex items-center gap-3 px-4 py-1.5 bg-[#2d3748] border-b border-[#1a202c] text-[11px] flex-shrink-0 flex-wrap">
        <span className="text-slate-500 font-semibold">Legend</span>
        {[["diff-delete","Deleted"],["diff-insert","Inserted"],["diff-replace","Modified"],
          ["diff-move-from","Moved (from)"],["diff-move-to","Moved (to)"]
        ].map(([cls, label]) => (
          <span key={cls} className={`${cls} px-2 py-0.5 rounded text-[11px]`}>{label}</span>
        ))}
        <span className="ml-auto text-slate-600 text-[10px] hidden md:block">Ctrl+←/→ navigate · Ctrl+± zoom</span>
      </div>

      <div className="flex-1 flex overflow-hidden">
        <div className="flex-1 min-w-0 flex flex-col border-r border-[#1a202c]">
          <DocViewer ref={origRef} spans={result.original_spans} side="original"
            title={`ORIGINAL — ${result.file_a_name}`} zoom={zoom}
            currentChangeIndex={curChange} changeSpanIndices={changeSpanIndices}
            onScroll={(top) => handleScroll("orig", top)} />
        </div>
        <div className="flex-1 min-w-0 flex flex-col border-r border-[#1a202c]">
          <DocViewer ref={revRef} spans={result.revised_spans} side="revised"
            title={`REVISED — ${result.file_b_name}`} zoom={zoom}
            currentChangeIndex={curChange} changeSpanIndices={changeSpanIndices}
            onScroll={(top) => handleScroll("rev", top)} />
        </div>
        {showPanel && (
          <aside className="w-72 flex-shrink-0 flex flex-col overflow-hidden border-l border-[#1a202c]">
            <ChangePanel summary={result.summary} changes={allChanges}
              currentChangeIndex={curChange} notes={notes}
              onNavigate={setCurChange}
              onNoteChange={(spanIdx, entry) =>
                setNotes(prev => ({ ...prev, [String(spanIdx)]: entry }))}
            />
          </aside>
        )}
      </div>
    </div>
  );
}
