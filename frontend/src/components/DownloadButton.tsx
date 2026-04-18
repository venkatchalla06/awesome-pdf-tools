interface Props { url: string; filename: string; extra?: React.ReactNode }

export function DownloadButton({ url, filename, extra }: Props) {
  return (
    <div className="flex flex-col gap-4">
      {/* Success card */}
      <div className="flex items-start gap-4 p-5 bg-[#e6f4ea] rounded-2xl">
        <div className="w-10 h-10 bg-[#1e8e3e] rounded-full flex items-center justify-center shrink-0">
          <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24">
            <path stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" d="M5 13l4 4L19 7"/>
          </svg>
        </div>
        <div>
          <p className="text-base font-medium text-[#137333]">Done! Your file is ready.</p>
          <p className="text-sm text-[#137333]/80 mt-0.5">{filename} has been processed successfully.</p>
        </div>
      </div>

      {extra && (
        <div className="p-4 bg-white rounded-2xl border border-[#e8eaed]"
          style={{ boxShadow: "0 1px 3px rgba(0,0,0,0.06)" }}>
          {extra}
        </div>
      )}

      {/* Download button */}
      <a
        href={url}
        download={filename}
        className="flex items-center justify-center gap-2 h-12 rounded-full text-sm font-medium
                   text-white transition-all"
        style={{ background: "linear-gradient(135deg,#1a73e8,#4285f4)", boxShadow: "0 2px 8px rgba(26,115,232,.4)" }}
        onMouseEnter={e => ((e.currentTarget as HTMLAnchorElement).style.boxShadow = "0 4px 16px rgba(26,115,232,.5)")}
        onMouseLeave={e => ((e.currentTarget as HTMLAnchorElement).style.boxShadow = "0 2px 8px rgba(26,115,232,.4)")}
      >
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24">
          <path stroke="currentColor" strokeWidth="2" strokeLinecap="round" d="M12 4v12M8 12l4 4 4-4M4 20h16"/>
        </svg>
        Download {filename}
      </a>
      <p className="text-center text-xs text-[#9aa0a6]">Link expires in 2 hours</p>
    </div>
  );
}
