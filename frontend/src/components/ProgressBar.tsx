interface Props { progress: number; label?: string }

export function ProgressBar({ progress, label }: Props) {
  return (
    <div className="w-full">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 relative">
            <div className="w-4 h-4 rounded-full border-2 border-[#e8eaed] border-t-[#1a73e8] animate-spin" />
          </div>
          <p className="text-sm font-medium text-[#202124]">{label ?? "Processing…"}</p>
        </div>
        <span className="text-sm font-medium text-[#1a73e8]">{progress}%</span>
      </div>
      <div className="w-full h-2 bg-[#e8eaed] rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-500 ease-out"
          style={{
            width: `${Math.max(4, progress)}%`,
            background: "linear-gradient(90deg, #1a73e8, #4285f4)",
          }}
        />
      </div>
      <p className="text-xs text-[#5f6368] mt-2">
        Your file is being processed securely. Please wait…
      </p>
    </div>
  );
}
