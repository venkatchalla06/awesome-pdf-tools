"use client";
import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";

interface Props {
  accept: Record<string, string[]>;
  multiple?: boolean;
  maxFiles?: number;
  label?: string;
  onFilesSelected: (files: File[]) => void;
}

export function DropZone({ accept, multiple = false, maxFiles = 20, label, onFilesSelected }: Props) {
  const [dragging, setDragging] = useState(false);

  const onDrop = useCallback((accepted: File[]) => {
    setDragging(false);
    if (accepted.length) onFilesSelected(accepted);
  }, [onFilesSelected]);

  const { getRootProps, getInputProps, fileRejections } = useDropzone({
    onDrop, accept, multiple, maxFiles,
    onDragEnter: () => setDragging(true),
    onDragLeave: () => setDragging(false),
  });

  const exts = Object.values(accept).flat().join(", ").toUpperCase();

  return (
    <div className="w-full">
      <div
        {...getRootProps()}
        className={`
          relative w-full min-h-[200px] rounded-3xl border-2 border-dashed cursor-pointer
          flex flex-col items-center justify-center gap-4 p-8
          transition-all duration-200 select-none text-center
          ${dragging
            ? "border-[#1a73e8] bg-[#e8f0fe] scale-[1.01]"
            : "border-[#dadce0] bg-white hover:border-[#1a73e8] hover:bg-[#f8f9ff]"
          }
        `}
        style={{ boxShadow: dragging ? "0 0 0 4px rgba(26,115,232,0.12)" : undefined }}
      >
        <input {...getInputProps()} />

        {/* Icon */}
        <div className={`w-16 h-16 rounded-2xl flex items-center justify-center transition-colors
          ${dragging ? "bg-[#1a73e8]/10" : "bg-[#f1f3f4]"}`}>
          <svg className={`w-8 h-8 transition-colors ${dragging ? "text-[#1a73e8]" : "text-[#80868b]"}`}
            fill="none" viewBox="0 0 24 24">
            <path stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"
              d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"/>
          </svg>
        </div>

        <div>
          <p className={`text-base font-medium transition-colors ${dragging ? "text-[#1a73e8]" : "text-[#202124]"}`}>
            {dragging ? "Drop your file here" : (label ?? "Drag & drop your file here")}
          </p>
          <p className="text-sm text-[#5f6368] mt-1">or</p>
        </div>

        <button type="button"
          className="h-10 px-6 rounded-full text-sm font-medium text-[#1a73e8]
                     bg-[#e8f0fe] hover:bg-[#d2e3fc] transition-colors">
          {multiple ? "Browse files" : "Browse file"}
        </button>

        <p className="text-xs text-[#9aa0a6]">{exts}</p>
      </div>

      {fileRejections.length > 0 && (
        <div className="mt-3 flex items-center gap-2.5 px-4 py-3 bg-[#fce8e6] rounded-xl">
          <svg className="w-4 h-4 text-[#d93025] shrink-0" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9 9V5h2v4H9zm0 4v-2h2v2H9z" clipRule="evenodd"/>
          </svg>
          <p className="text-sm text-[#c5221f]">{fileRejections[0].errors[0].message}</p>
        </div>
      )}
    </div>
  );
}
