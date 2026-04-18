"use client";

interface Props {
  toolId: string;
  options: Record<string, unknown>;
  onChange: (opts: Record<string, unknown>) => void;
}

const inputCls = `w-full h-12 bg-white border border-[#dadce0] rounded-xl px-4 text-sm text-[#202124]
  focus:outline-none focus:border-[#1a73e8] focus:ring-2 focus:ring-[#1a73e8]/20 transition-all`;
const labelCls = "block text-sm font-medium text-[#202124] mb-2";

function Card({ children }: { children: React.ReactNode }) {
  return (
    <div className="mt-4 bg-white rounded-2xl border border-[#e8eaed] p-5 space-y-4"
      style={{ boxShadow: "0 1px 3px rgba(0,0,0,0.06)" }}>
      {children}
    </div>
  );
}

function SegmentControl({ keys, labels, active, onSelect }:
  { keys: (string|number)[]; labels?: string[]; active: unknown; onSelect: (v: string|number) => void }) {
  return (
    <div className="flex gap-2 flex-wrap">
      {keys.map((k, i) => (
        <button key={k} type="button" onClick={() => onSelect(k)}
          className={`flex-1 h-10 rounded-full text-sm font-medium transition-all min-w-[80px]
            ${active === k
              ? "bg-[#1a73e8] text-white shadow-sm"
              : "bg-[#f1f3f4] text-[#5f6368] hover:bg-[#e8eaed]"}`}>
          {labels?.[i] ?? String(k)}
        </button>
      ))}
    </div>
  );
}

export function ToolOptions({ toolId, options, onChange }: Props) {
  const set = (k: string, v: unknown) => onChange({ ...options, [k]: v });

  if (toolId === "split") return (
    <Card>
      <div>
        <label className={labelCls}>Split mode</label>
        <select className={inputCls} onChange={(e) => {
          e.target.value === "every" ? set("every_n_pages", 1) : onChange({});
        }} defaultValue="each">
          <option value="each">One file per page</option>
          <option value="every">Every N pages</option>
        </select>
      </div>
      {options.every_n_pages != null && (
        <div>
          <label className={labelCls}>Pages per file</label>
          <input type="number" min={1} defaultValue={1} className={inputCls}
            onChange={(e) => set("every_n_pages", parseInt(e.target.value))} />
        </div>
      )}
    </Card>
  );

  if (toolId === "compress") return (
    <Card>
      <label className={labelCls}>Compression level</label>
      <SegmentControl keys={["low","recommended","extreme"]} labels={["Low","Recommended","Extreme"]}
        active={options.quality ?? "recommended"} onSelect={(v) => set("quality", v)} />
    </Card>
  );

  if (toolId === "rotate") return (
    <Card>
      <label className={labelCls}>Rotation angle</label>
      <SegmentControl keys={[90,180,270]} labels={["90°","180°","270°"]}
        active={options.angle ?? 90} onSelect={(v) => set("angle", v)} />
    </Card>
  );

  if (toolId === "watermark") return (
    <Card>
      <div>
        <label className={labelCls}>Watermark text</label>
        <input type="text" defaultValue="CONFIDENTIAL" className={inputCls}
          onChange={(e) => set("text", e.target.value)} />
      </div>
      <div>
        <div className="flex justify-between mb-2">
          <label className={labelCls + " mb-0"}>Opacity</label>
          <span className="text-sm text-[#1a73e8] font-medium">
            {Math.round(Number(options.opacity ?? 0.3) * 100)}%
          </span>
        </div>
        <input type="range" min={10} max={100} defaultValue={30} className="w-full"
          onChange={(e) => set("opacity", parseInt(e.target.value) / 100)} />
      </div>
    </Card>
  );

  if (toolId === "protect" || toolId === "unlock") return (
    <Card>
      <label className={labelCls}>
        {toolId === "protect" ? "Password to set" : "Current password (leave blank if none)"}
      </label>
      <input type="password" className={inputCls}
        placeholder={toolId === "protect" ? "Enter a strong password" : "Leave blank if none"}
        onChange={(e) => set("password", e.target.value)} />
    </Card>
  );

  if (toolId === "page-numbers") return (
    <Card>
      <div>
        <label className={labelCls}>Position</label>
        <select className={inputCls} onChange={(e) => set("position", e.target.value)} defaultValue="bottom-center">
          <option value="bottom-center">Bottom Center</option>
          <option value="bottom-right">Bottom Right</option>
          <option value="bottom-left">Bottom Left</option>
          <option value="top-center">Top Center</option>
        </select>
      </div>
      <div>
        <label className={labelCls}>Format</label>
        <input type="text" defaultValue="{n}" className={inputCls + " font-mono"}
          placeholder="{n} or Page {n} of {total}"
          onChange={(e) => set("format", e.target.value)} />
        <p className="mt-1.5 text-xs text-[#9aa0a6]">
          {"{n}"} = page number · {"{total}"} = total pages
        </p>
      </div>
    </Card>
  );

  if (toolId === "ocr") return (
    <Card>
      <label className={labelCls}>Document language</label>
      <select className={inputCls} onChange={(e) => set("language", e.target.value)} defaultValue="eng">
        {[["eng","English"],["fra","French"],["deu","German"],["spa","Spanish"],
          ["ita","Italian"],["por","Portuguese"],["chi_sim","Chinese (Simplified)"],
          ["jpn","Japanese"],["ara","Arabic"]].map(([v,l]) => (
          <option key={v} value={v}>{l}</option>
        ))}
      </select>
    </Card>
  );

  if (toolId === "pdf-to-jpg") return (
    <Card>
      <label className={labelCls}>Image quality</label>
      <SegmentControl keys={[72,150,300]} labels={["72 DPI","150 DPI","300 DPI"]}
        active={options.dpi ?? 150} onSelect={(v) => set("dpi", v)} />
      <p className="text-xs text-[#9aa0a6]">Higher DPI = sharper image, larger file size.</p>
    </Card>
  );

  if (toolId === "summarize") return (
    <Card>
      <label className={labelCls}>Summary style</label>
      <SegmentControl keys={["bullet","paragraph","executive"]} labels={["Bullets","Paragraph","Executive"]}
        active={options.style ?? "bullet"} onSelect={(v) => set("style", v)} />
    </Card>
  );

  if (toolId === "translate") return (
    <Card>
      <label className={labelCls}>Target language</label>
      <select className={inputCls} onChange={(e) => set("target_language", e.target.value)} defaultValue="Spanish">
        {["Spanish","French","German","Italian","Portuguese","Chinese","Japanese",
          "Arabic","Hindi","Russian","Korean","Dutch","Polish"].map((l) => (
          <option key={l} value={l}>{l}</option>
        ))}
      </select>
    </Card>
  );

  if (toolId === "remove-pages") return (
    <Card>
      <label className={labelCls}>Pages to remove</label>
      <input type="text" className={inputCls} placeholder="e.g. 1,3,5-7"
        onChange={(e) => set("pages", e.target.value)} />
      <p className="mt-1.5 text-xs text-[#9aa0a6]">Enter page numbers or ranges separated by commas</p>
    </Card>
  );

  if (toolId === "extract-pages") return (
    <Card>
      <label className={labelCls}>Pages to extract</label>
      <input type="text" className={inputCls} placeholder="e.g. 1-5,7,9"
        onChange={(e) => set("pages", e.target.value)} />
      <p className="mt-1.5 text-xs text-[#9aa0a6]">Enter page numbers or ranges separated by commas</p>
    </Card>
  );

  if (toolId === "organize") return (
    <Card>
      <label className={labelCls}>New page order</label>
      <input type="text" className={inputCls} placeholder="e.g. 3,1,2,4"
        onChange={(e) => set("order", e.target.value)} />
      <p className="mt-1.5 text-xs text-[#9aa0a6]">Enter all page numbers in the desired order</p>
    </Card>
  );

  if (toolId === "crop") return (
    <Card>
      <p className="text-xs text-[#9aa0a6] -mt-1 mb-1">Crop margin as % of page size (0–45%)</p>
      {(["top","bottom","left","right"] as const).map((side) => (
        <div key={side}>
          <div className="flex justify-between mb-1">
            <label className={labelCls + " mb-0 capitalize"}>{side}</label>
            <span className="text-sm text-[#1a73e8] font-medium">{Number(options[side] ?? 0)}%</span>
          </div>
          <input type="range" min={0} max={45} defaultValue={0} className="w-full"
            onChange={(e) => set(side, parseInt(e.target.value))} />
        </div>
      ))}
    </Card>
  );

  if (toolId === "redact") return (
    <Card>
      <label className={labelCls}>Text to redact</label>
      <input type="text" className={inputCls} placeholder="e.g. John Doe, 555-1234, CONFIDENTIAL"
        onChange={(e) => set("terms", e.target.value)} />
      <p className="mt-1.5 text-xs text-[#9aa0a6]">Comma-separated words or phrases to permanently black out</p>
    </Card>
  );

  return null;
}
