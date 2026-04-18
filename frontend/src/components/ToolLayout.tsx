"use client";
import Link from "next/link";
import Image from "next/image";

interface Props {
  title: string;
  description: string;
  color: string;
  icon?: string;
  bgLight?: string;
  children: React.ReactNode;
}

export function ToolLayout({ title, description, icon, bgLight, children }: Props) {
  return (
    <div className="min-h-screen bg-[#f8f9fa] flex flex-col">

      {/* App bar */}
      <header className="bg-white sticky top-0 z-50"
        style={{ boxShadow: "0 1px 3px rgba(0,0,0,0.12)" }}>
        <div className="max-w-[1440px] mx-auto px-4 sm:px-6 h-16 flex items-center gap-4">
          <Link href="/" className="flex items-center gap-3">
            <img src="/logo-header.png" alt="APEPDCL" className="h-10 w-auto object-contain" />
            <span className="text-lg font-bold text-[#2e3b8e] hidden sm:block tracking-tight leading-tight">Eastern Power Distribution Company of Andhra Pradesh Limited</span>
          </Link>
          <div className="flex items-center gap-2 text-sm text-[#5f6368] ml-2">
            <Link href="/" className="hover:text-[#1a73e8] flex items-center gap-1 transition-colors">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24">
                <path stroke="currentColor" strokeWidth="2" strokeLinecap="round" d="M3 12h18M3 6h18M3 18h12"/>
              </svg>
              <span className="hidden sm:inline">All Tools</span>
            </Link>
            <svg className="w-4 h-4 text-[#dadce0]" fill="none" viewBox="0 0 24 24">
              <path stroke="currentColor" strokeWidth="2" d="M9 6l6 6-6 6"/>
            </svg>
            <span className="text-[#202124] font-medium">{title}</span>
          </div>
        </div>
      </header>

      {/* Hero strip */}
      <div className="bg-white border-b border-[#e8eaed]">
        <div className="max-w-[1440px] mx-auto px-4 sm:px-6 py-6 flex items-center gap-4">
          {icon && bgLight && (
            <div className={`w-14 h-14 ${bgLight} rounded-2xl flex items-center justify-center shrink-0`}>
              <Image src={icon} alt={title} width={30} height={30} className="w-7 h-7" />
            </div>
          )}
          <div>
            <h1 className="text-2xl font-medium text-[#202124]">{title}</h1>
            <p className="text-sm text-[#5f6368] mt-0.5">{description}</p>
          </div>
        </div>
      </div>

      {/* Content */}
      <main className="flex-1 max-w-[1440px] w-full mx-auto px-4 sm:px-6 py-8">
        <div className="max-w-xl">{children}</div>
      </main>
    </div>
  );
}
