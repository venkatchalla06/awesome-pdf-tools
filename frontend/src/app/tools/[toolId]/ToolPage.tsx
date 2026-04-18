"use client";
import { useState } from "react";
import { Tool } from "@/lib/tools";
import { ToolLayout } from "@/components/ToolLayout";
import { DropZone } from "@/components/DropZone";
import { FileList } from "@/components/FileList";
import { ProgressBar } from "@/components/ProgressBar";
import { DownloadButton } from "@/components/DownloadButton";
import { uploadFile, UploadedFile, formatBytes } from "@/lib/upload";
import { useJob } from "@/lib/useJob";
import { api } from "@/lib/api";
import { ToolOptions } from "./ToolOptions";

interface Props { tool: Tool }

function Steps({ step }: { step: 1 | 2 | 3 }) {
  const items = ["Upload", "Process", "Download"];
  return (
    <div className="flex items-center gap-3 mb-8">
      {items.map((label, i) => {
        const n = i + 1;
        const done = n < step;
        const active = n === step;
        return (
          <div key={label} className="flex items-center gap-3">
            <div className={`flex items-center gap-2 transition-all`}>
              <div className={`w-7 h-7 rounded-full flex items-center justify-center text-sm font-medium transition-all
                ${done ? "bg-[#1e8e3e] text-white" : active ? "bg-[#1a73e8] text-white" : "bg-[#e8eaed] text-[#9aa0a6]"}`}>
                {done ? (
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24">
                    <path stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" d="M5 13l4 4L19 7"/>
                  </svg>
                ) : n}
              </div>
              <span className={`text-sm hidden sm:block ${active ? "font-medium text-[#202124]" : "text-[#9aa0a6]"}`}>
                {label}
              </span>
            </div>
            {i < 2 && <div className={`w-8 h-0.5 rounded-full ${done ? "bg-[#1e8e3e]" : "bg-[#e8eaed]"}`} />}
          </div>
        );
      })}
    </div>
  );
}

export function ToolPage({ tool }: Props) {
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [uploading, setUploading] = useState(false);
  const [jobId, setJobId] = useState<string | null>(null);
  const [options, setOptions] = useState<Record<string, unknown>>({});
  const [submitError, setSubmitError] = useState<string | null>(null);

  const job = useJob(jobId);
  const isProcessing = jobId && (job.status === "pending" || job.status === "processing");

  const step: 1|2|3 = !jobId ? 1 : job.status === "completed" ? 3 : 2;

  async function handleFilesSelected(selected: File[]) {
    setUploading(true);
    setSubmitError(null);
    try {
      const uploaded = await Promise.all(selected.map(uploadFile));
      setFiles((prev) => [...prev, ...uploaded]);
    } catch (e) {
      setSubmitError(e instanceof Error ? e.message : "Upload failed");
    } finally { setUploading(false); }
  }

  async function handleSubmit() {
    setSubmitError(null);
    try {
      const body: Record<string, unknown> = { ...options };
      const single = ["split","compress","rotate","watermark","protect","unlock",
                      "page-numbers","ocr","pdf-to-jpg","pdf-to-word","word-to-pdf","summarize","translate",
                      "remove-pages","extract-pages","organize","repair","crop","redact","pdf-to-pdfa",
                      "pptx-to-pdf","xlsx-to-pdf","html-to-pdf","pdf-to-pptx"];
      if (single.includes(tool.id)) body.input_key = files[0].s3Key;
      else body.input_keys = files.map((f) => f.s3Key);
      const result = await api.post(`/tools/${tool.id}`, body);
      setJobId(result.id);
    } catch (e) {
      setSubmitError(e instanceof Error ? e.message : "Failed to start job");
    }
  }

  function reset() { setFiles([]); setJobId(null); setSubmitError(null); setOptions({}); }

  const canSubmit = files.length > 0 && !uploading &&
    (tool.id === "merge" ? files.length >= 2 : true);

  return (
    <ToolLayout title={tool.name} description={tool.description}
      color={tool.color} icon={tool.icon} bgLight={tool.bgLight}>
      <Steps step={step} />

      {/* Step 1: Upload */}
      {!jobId && (
        <div className="space-y-4 animate-fade-up">
          <DropZone accept={tool.accept} multiple={tool.multiple} onFilesSelected={handleFilesSelected} />

          {uploading && (
            <div className="flex items-center gap-3 px-4 py-3 bg-[#e8f0fe] rounded-xl">
              <div className="w-4 h-4 rounded-full border-2 border-[#c5d9fb] border-t-[#1a73e8] animate-spin shrink-0" />
              <p className="text-sm text-[#1a73e8] font-medium">Uploading securely…</p>
            </div>
          )}

          {files.length > 0 && (
            <>
              <FileList files={files}
                onRemove={(i) => setFiles((p) => p.filter((_, idx) => idx !== i))}
                onMoveUp={tool.multiple ? (i) => setFiles((p) => { const a=[...p]; [a[i-1],a[i]]=[a[i],a[i-1]]; return a; }) : undefined}
                onMoveDown={tool.multiple ? (i) => setFiles((p) => { const a=[...p]; [a[i],a[i+1]]=[a[i+1],a[i]]; return a; }) : undefined}
              />
              <ToolOptions toolId={tool.id} options={options} onChange={setOptions} />
            </>
          )}

          {submitError && (
            <div className="flex items-start gap-3 px-4 py-3 bg-[#fce8e6] rounded-xl">
              <svg className="w-5 h-5 text-[#d93025] shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9 9V5h2v4H9zm0 4v-2h2v2H9z" clipRule="evenodd"/>
              </svg>
              <p className="text-sm text-[#c5221f]">{submitError}</p>
            </div>
          )}

          {files.length > 0 && (
            <div className="flex items-center gap-3 pt-2">
              <button onClick={handleSubmit} disabled={!canSubmit}
                className="flex items-center gap-2 h-12 px-8 rounded-full text-sm font-medium text-white
                           transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                style={{ background: canSubmit ? "linear-gradient(135deg,#1a73e8,#4285f4)" : undefined,
                         backgroundColor: canSubmit ? undefined : "#dadce0",
                         boxShadow: canSubmit ? "0 2px 8px rgba(26,115,232,.4)" : undefined }}>
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24">
                  <path stroke="currentColor" strokeWidth="2" strokeLinecap="round" d="M5 12h14M12 5l7 7-7 7"/>
                </svg>
                {tool.name}{tool.id === "merge" && files.length >= 2 ? ` (${files.length})` : ""}
              </button>
              <button onClick={reset} className="h-12 px-5 text-sm text-[#5f6368] hover:text-[#202124] rounded-full hover:bg-[#f1f3f4] transition-colors">
                Clear
              </button>
            </div>
          )}
        </div>
      )}

      {/* Step 2: Processing */}
      {isProcessing && (
        <div className="bg-white rounded-2xl border border-[#e8eaed] p-6 animate-fade-up"
          style={{ boxShadow: "0 1px 3px rgba(0,0,0,0.06)" }}>
          <ProgressBar progress={job.progress} label="Processing your file…" />
        </div>
      )}

      {/* Step 3: Done */}
      {job.status === "completed" && job.downloadUrl && (
        <div className="space-y-4 animate-fade-up">
          <DownloadButton
            url={job.downloadUrl}
            filename={String(job.options?.output_filename ?? "result.pdf")}
            extra={
              tool.id === "compress" && job.options?.reduction_pct != null ? (
                <div className="flex items-center gap-2">
                  <svg className="w-4 h-4 text-[#1e8e3e]" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd"/>
                  </svg>
                  <p className="text-sm text-[#137333] font-medium">
                    Size reduced by {String(job.options.reduction_pct)}% · {formatBytes(Number(job.options.compressed_size_bytes))}
                  </p>
                </div>
              ) : tool.id === "summarize" && job.options?.summary_preview ? (
                <p className="text-sm text-[#202124] leading-relaxed">{String(job.options.summary_preview)}…</p>
              ) : undefined
            }
          />
          <button onClick={reset}
            className="flex items-center gap-2 h-10 px-5 rounded-full text-sm font-medium
                       text-[#1a73e8] hover:bg-[#e8f0fe] transition-colors">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24">
              <path stroke="currentColor" strokeWidth="2" strokeLinecap="round" d="M4 4v5h5M20 20v-5h-5M4 9a9 9 0 0115 0M20 15a9 9 0 01-15 0"/>
            </svg>
            Process another file
          </button>
        </div>
      )}

      {job.status === "failed" && (
        <div className="space-y-4 animate-fade-up">
          <div className="flex items-start gap-3 p-5 bg-[#fce8e6] rounded-2xl">
            <svg className="w-5 h-5 text-[#d93025] shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9 9V5h2v4H9zm0 4v-2h2v2H9z" clipRule="evenodd"/>
            </svg>
            <div>
              <p className="text-sm font-medium text-[#c5221f]">Processing failed</p>
              <p className="text-xs text-[#c5221f]/80 mt-0.5">{job.error}</p>
            </div>
          </div>
          <button onClick={reset}
            className="flex items-center gap-2 h-10 px-5 rounded-full text-sm font-medium
                       text-[#1a73e8] bg-[#e8f0fe] hover:bg-[#d2e3fc] transition-colors">
            Try again
          </button>
        </div>
      )}

      {/* Security note */}
      <div className="mt-12 flex items-center gap-2">
        <svg className="w-4 h-4 text-[#1e8e3e]" fill="none" viewBox="0 0 24 24">
          <path stroke="currentColor" strokeWidth="2" d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
        </svg>
        <p className="text-xs text-[#5f6368]">
          Files are encrypted in transit and deleted automatically after 2 hours.
        </p>
      </div>
    </ToolLayout>
  );
}
