"use client";
import { UploadedFile, formatBytes } from "@/lib/upload";

interface Props {
  files: UploadedFile[];
  uploading?: boolean[];
  onRemove?: (i: number) => void;
  onMoveUp?: (i: number) => void;
  onMoveDown?: (i: number) => void;
}

export function FileList({ files, uploading, onRemove, onMoveUp, onMoveDown }: Props) {
  if (!files.length) return null;
  return (
    <div className="mt-4 bg-white rounded-2xl border border-[#e8eaed] overflow-hidden"
      style={{ boxShadow: "0 1px 3px rgba(0,0,0,0.06)" }}>
      <div className="px-4 py-2.5 bg-[#f8f9fa] border-b border-[#e8eaed] flex items-center justify-between">
        <span className="text-xs font-medium text-[#5f6368]">
          {files.length} file{files.length > 1 ? "s" : ""} selected
        </span>
      </div>
      <ul className="divide-y divide-[#f1f3f4]">
        {files.map((f, i) => (
          <li key={i} className="flex items-center gap-3 px-4 py-3 hover:bg-[#f8f9fa] transition-colors">
            {/* PDF icon */}
            <div className="w-9 h-9 bg-[#fce8e6] rounded-xl flex items-center justify-center shrink-0">
              <svg className="w-5 h-5 text-[#d93025]" fill="none" viewBox="0 0 24 24">
                <path stroke="currentColor" strokeWidth="1.5" d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/>
                <path stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" d="M14 2v6h6M9 13h6M9 17h4"/>
              </svg>
            </div>

            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-[#202124] truncate">{f.filename}</p>
              <p className="text-xs text-[#9aa0a6]">{formatBytes(f.size)}</p>
            </div>

            {uploading?.[i] && (
              <span className="text-xs text-[#1a73e8] font-medium animate-pulse">Uploading…</span>
            )}

            <div className="flex items-center gap-0.5">
              {onMoveUp && i > 0 && (
                <button onClick={() => onMoveUp(i)}
                  className="w-7 h-7 flex items-center justify-center rounded-full text-[#5f6368] hover:bg-[#e8eaed] transition-colors">
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24">
                    <path stroke="currentColor" strokeWidth="2" strokeLinecap="round" d="M12 19V5M5 12l7-7 7 7"/>
                  </svg>
                </button>
              )}
              {onMoveDown && i < files.length - 1 && (
                <button onClick={() => onMoveDown(i)}
                  className="w-7 h-7 flex items-center justify-center rounded-full text-[#5f6368] hover:bg-[#e8eaed] transition-colors">
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24">
                    <path stroke="currentColor" strokeWidth="2" strokeLinecap="round" d="M12 5v14M5 12l7 7 7-7"/>
                  </svg>
                </button>
              )}
              {onRemove && (
                <button onClick={() => onRemove(i)}
                  className="w-7 h-7 flex items-center justify-center rounded-full text-[#5f6368] hover:bg-[#fce8e6] hover:text-[#d93025] transition-colors">
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24">
                    <path stroke="currentColor" strokeWidth="2" strokeLinecap="round" d="M6 6l12 12M18 6L6 18"/>
                  </svg>
                </button>
              )}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
