import type { Metadata } from "next";
import { Roboto } from "next/font/google";
import "./globals.css";

const roboto = Roboto({
  subsets: ["latin"],
  weight: ["300", "400", "500", "700"],
  variable: "--font-sans",
  display: "swap",
});

export const metadata: Metadata = {
  title: "PDFKit — Free PDF Tools Online",
  description: "Merge, split, compress, convert, OCR and AI-powered PDF tools. Free, fast, secure.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={roboto.variable}>
      <body className="min-h-screen bg-[#f8f9fa]">{children}</body>
    </html>
  );
}
