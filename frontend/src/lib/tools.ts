export interface Tool {
  id: string;
  name: string;
  description: string;
  icon: string;
  color: string;
  bgLight: string;
  tabs: Tab[];
  accept: Record<string, string[]>;
  multiple?: boolean;
}

export type Tab =
  | "all"
  | "organize"
  | "optimize"
  | "convert-to"
  | "convert-from"
  | "edit"
  | "security"
  | "ai";

export interface TabDef {
  id: Tab;
  label: string;
}

export const TABS: TabDef[] = [
  { id: "all",          label: "All PDF Tools" },
  { id: "organize",     label: "Organize PDF" },
  { id: "optimize",     label: "Optimize PDF" },
  { id: "convert-from", label: "Convert from PDF" },
  { id: "convert-to",   label: "Convert to PDF" },
  { id: "edit",         label: "Edit PDF" },
  { id: "security",     label: "PDF Security" },
  { id: "ai",           label: "AI Tools" },
];

export const TOOLS: Tool[] = [
  // ── Organize ───────────────────────────────────────────────────────────────
  {
    id: "merge",
    name: "Merge PDF",
    description: "Combine multiple PDFs into one file",
    icon: "/icons/merge.svg",
    color: "text-[#0f62fe]",
    bgLight: "bg-[#edf5ff]",
    tabs: ["all", "organize"],
    accept: { "application/pdf": [".pdf"] },
    multiple: true,
  },
  {
    id: "split",
    name: "Split PDF",
    description: "Separate pages into individual PDFs",
    icon: "/icons/split.svg",
    color: "text-[#0f62fe]",
    bgLight: "bg-[#edf5ff]",
    tabs: ["all", "organize"],
    accept: { "application/pdf": [".pdf"] },
  },
  {
    id: "remove-pages",
    name: "Remove Pages",
    description: "Delete unwanted pages from a PDF",
    icon: "/icons/remove-pages.svg",
    color: "text-[#0f62fe]",
    bgLight: "bg-[#edf5ff]",
    tabs: ["all", "organize"],
    accept: { "application/pdf": [".pdf"] },
  },
  {
    id: "extract-pages",
    name: "Extract Pages",
    description: "Pull specific pages into a new PDF",
    icon: "/icons/extract-pages.svg",
    color: "text-[#0f62fe]",
    bgLight: "bg-[#edf5ff]",
    tabs: ["all", "organize"],
    accept: { "application/pdf": [".pdf"] },
  },
  {
    id: "organize",
    name: "Organize PDF",
    description: "Reorder pages in a custom sequence",
    icon: "/icons/organize.svg",
    color: "text-[#0f62fe]",
    bgLight: "bg-[#edf5ff]",
    tabs: ["all", "organize"],
    accept: { "application/pdf": [".pdf"] },
  },
  {
    id: "rotate",
    name: "Rotate PDF",
    description: "Rotate one or all PDF pages",
    icon: "/icons/rotate.svg",
    color: "text-[#0f62fe]",
    bgLight: "bg-[#edf5ff]",
    tabs: ["all", "organize"],
    accept: { "application/pdf": [".pdf"] },
  },
  {
    id: "page-numbers",
    name: "Page Numbers",
    description: "Add page numbers to a PDF",
    icon: "/icons/page-numbers.svg",
    color: "text-[#0f62fe]",
    bgLight: "bg-[#edf5ff]",
    tabs: ["all", "organize", "edit"],
    accept: { "application/pdf": [".pdf"] },
  },

  // ── Optimize ───────────────────────────────────────────────────────────────
  {
    id: "compress",
    name: "Compress PDF",
    description: "Reduce PDF file size while preserving quality",
    icon: "/icons/compress.svg",
    color: "text-[#007d79]",
    bgLight: "bg-[#d9fbfb]",
    tabs: ["all", "optimize"],
    accept: { "application/pdf": [".pdf"] },
  },
  {
    id: "repair",
    name: "Repair PDF",
    description: "Fix damaged or corrupted PDF files",
    icon: "/icons/repair.svg",
    color: "text-[#007d79]",
    bgLight: "bg-[#d9fbfb]",
    tabs: ["all", "optimize"],
    accept: { "application/pdf": [".pdf"] },
  },

  // ── Convert from PDF ───────────────────────────────────────────────────────
  {
    id: "pdf-to-word",
    name: "PDF to Word",
    description: "Convert PDF files to editable Word documents",
    icon: "/icons/pdf-to-word.svg",
    color: "text-[#8a3ffc]",
    bgLight: "bg-[#f6f2ff]",
    tabs: ["all", "convert-from"],
    accept: { "application/pdf": [".pdf"] },
  },
  {
    id: "pdf-to-jpg",
    name: "PDF to JPG",
    description: "Convert each PDF page to a JPG image",
    icon: "/icons/pdf-to-jpg.svg",
    color: "text-[#8a3ffc]",
    bgLight: "bg-[#f6f2ff]",
    tabs: ["all", "convert-from"],
    accept: { "application/pdf": [".pdf"] },
  },
  {
    id: "pdf-to-pdfa",
    name: "PDF to PDF/A",
    description: "Convert to archival PDF/A format",
    icon: "/icons/pdf-to-pdfa.svg",
    color: "text-[#8a3ffc]",
    bgLight: "bg-[#f6f2ff]",
    tabs: ["all", "convert-from"],
    accept: { "application/pdf": [".pdf"] },
  },
  {
    id: "pdf-to-pptx",
    name: "PDF to PowerPoint",
    description: "Convert PDF pages to editable PowerPoint slides",
    icon: "/icons/pdf-to-pptx.svg",
    color: "text-[#8a3ffc]",
    bgLight: "bg-[#f6f2ff]",
    tabs: ["all", "convert-from"],
    accept: { "application/pdf": [".pdf"] },
  },

  // ── Convert to PDF ─────────────────────────────────────────────────────────
  {
    id: "word-to-pdf",
    name: "Word to PDF",
    description: "Convert Word documents to PDF format",
    icon: "/icons/word-to-pdf.svg",
    color: "text-[#1192e8]",
    bgLight: "bg-[#e8f4ff]",
    tabs: ["all", "convert-to"],
    accept: {
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
      "application/msword": [".doc"],
    },
  },
  {
    id: "jpg-to-pdf",
    name: "JPG to PDF",
    description: "Convert JPG images to PDF format",
    icon: "/icons/jpg-to-pdf.svg",
    color: "text-[#1192e8]",
    bgLight: "bg-[#e8f4ff]",
    tabs: ["all", "convert-to"],
    accept: { "image/jpeg": [".jpg", ".jpeg"], "image/png": [".png"] },
    multiple: true,
  },
  {
    id: "pptx-to-pdf",
    name: "PowerPoint to PDF",
    description: "Convert presentations to PDF format",
    icon: "/icons/pptx-to-pdf.svg",
    color: "text-[#1192e8]",
    bgLight: "bg-[#e8f4ff]",
    tabs: ["all", "convert-to"],
    accept: {
      "application/vnd.openxmlformats-officedocument.presentationml.presentation": [".pptx"],
      "application/vnd.ms-powerpoint": [".ppt"],
    },
  },
  {
    id: "xlsx-to-pdf",
    name: "Excel to PDF",
    description: "Convert spreadsheets to PDF format",
    icon: "/icons/xlsx-to-pdf.svg",
    color: "text-[#1192e8]",
    bgLight: "bg-[#e8f4ff]",
    tabs: ["all", "convert-to"],
    accept: {
      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [".xlsx"],
      "application/vnd.ms-excel": [".xls"],
    },
  },
  {
    id: "html-to-pdf",
    name: "HTML to PDF",
    description: "Convert web pages or HTML files to PDF",
    icon: "/icons/html-to-pdf.svg",
    color: "text-[#1192e8]",
    bgLight: "bg-[#e8f4ff]",
    tabs: ["all", "convert-to"],
    accept: { "text/html": [".html", ".htm"] },
  },

  // ── Edit ───────────────────────────────────────────────────────────────────
  {
    id: "watermark",
    name: "Watermark PDF",
    description: "Stamp text watermark diagonally on a PDF",
    icon: "/icons/watermark.svg",
    color: "text-[#005d5d]",
    bgLight: "bg-[#d9fbfb]",
    tabs: ["all", "edit"],
    accept: { "application/pdf": [".pdf"] },
  },
  {
    id: "crop",
    name: "Crop PDF",
    description: "Trim margins and crop page boundaries",
    icon: "/icons/crop.svg",
    color: "text-[#005d5d]",
    bgLight: "bg-[#d9fbfb]",
    tabs: ["all", "edit"],
    accept: { "application/pdf": [".pdf"] },
  },
  {
    id: "redact",
    name: "Redact PDF",
    description: "Permanently black out sensitive text",
    icon: "/icons/redact.svg",
    color: "text-[#005d5d]",
    bgLight: "bg-[#d9fbfb]",
    tabs: ["all", "edit", "security"],
    accept: { "application/pdf": [".pdf"] },
  },

  // ── Security ───────────────────────────────────────────────────────────────
  {
    id: "protect",
    name: "Protect PDF",
    description: "Add a password to encrypt your PDF",
    icon: "/icons/protect.svg",
    color: "text-[#da1e28]",
    bgLight: "bg-[#fff1f1]",
    tabs: ["all", "security"],
    accept: { "application/pdf": [".pdf"] },
  },
  {
    id: "unlock",
    name: "Unlock PDF",
    description: "Remove PDF password and restrictions",
    icon: "/icons/unlock.svg",
    color: "text-[#da1e28]",
    bgLight: "bg-[#fff1f1]",
    tabs: ["all", "security"],
    accept: { "application/pdf": [".pdf"] },
  },

  // ── AI ─────────────────────────────────────────────────────────────────────
  {
    id: "ocr",
    name: "OCR PDF",
    description: "Make scanned PDFs searchable with OCR",
    icon: "/icons/ocr.svg",
    color: "text-[#ee5396]",
    bgLight: "bg-[#fff0f7]",
    tabs: ["all", "ai", "edit"],
    accept: { "application/pdf": [".pdf"] },
  },
  {
    id: "summarize",
    name: "AI Summarize",
    description: "Get an instant AI summary of any PDF",
    icon: "/icons/summarize.svg",
    color: "text-[#ee5396]",
    bgLight: "bg-[#fff0f7]",
    tabs: ["all", "ai"],
    accept: { "application/pdf": [".pdf"] },
  },
  {
    id: "translate",
    name: "AI Translate",
    description: "Translate PDF content to any language",
    icon: "/icons/translate.svg",
    color: "text-[#ee5396]",
    bgLight: "bg-[#fff0f7]",
    tabs: ["all", "ai"],
    accept: { "application/pdf": [".pdf"] },
  },
];
