"use client";
import { useState, useMemo } from "react";
import Link from "next/link";
import Image from "next/image";
import { TOOLS, TABS, type Tab } from "@/lib/tools";

const POPULAR = ["merge", "compress", "pdf-to-word", "split", "ocr", "jpg-to-pdf"];

// Material 3 tonal colors per category
const TAB_COLORS: Record<string, { chip: string; active: string }> = {
  all:           { chip: "bg-[#e8f0fe] text-[#1a73e8]",      active: "bg-[#1a73e8] text-white" },
  organize:      { chip: "bg-[#e6f4ea] text-[#1e8e3e]",      active: "bg-[#1e8e3e] text-white" },
  optimize:      { chip: "bg-[#fce8e6] text-[#d93025]",      active: "bg-[#d93025] text-white" },
  "convert-from":{ chip: "bg-[#f3e8fd] text-[#9334e6]",      active: "bg-[#9334e6] text-white" },
  "convert-to":  { chip: "bg-[#fef0cd] text-[#e37400]",      active: "bg-[#e37400] text-white" },
  edit:          { chip: "bg-[#e8f0fe] text-[#1a73e8]",      active: "bg-[#1a73e8] text-white" },
  security:      { chip: "bg-[#fce8e6] text-[#d93025]",      active: "bg-[#d93025] text-white" },
  ai:            { chip: "bg-[#fce8f7] text-[#e52592]",      active: "bg-[#e52592] text-white" },
};

export default function Home() {
  const [activeTab, setActiveTab] = useState<Tab>("all");
  const visible = useMemo(() => {
    return TOOLS.filter((t) => t.tabs.includes(activeTab));
  }, [activeTab]);

  return (
    <div className="min-h-screen flex flex-col">

      {/* ── App Bar (Material 3) ── */}
      <header className="bg-white sticky top-0 z-50"
        style={{ boxShadow: "0 1px 3px rgba(0,0,0,0.12), 0 1px 2px rgba(0,0,0,0.08)" }}>
        <div className="max-w-[1440px] mx-auto px-4 sm:px-6 h-16 flex items-center gap-4">
          {/* Logo */}
          <Link href="/" className="flex items-center gap-3 shrink-0">
            <img src="/logo-header.png" alt="APEPDCL" className="h-10 w-auto object-contain" />
            <span className="text-lg font-bold text-[#2e3b8e] hidden sm:block tracking-tight leading-tight">Eastern Power Distribution Company of Andhra Pradesh Limited</span>
          </Link>

          <div className="flex-1" />

          {/* Auth */}
          <div className="flex items-center gap-2 shrink-0">
            <Link href="/login"
              className="hidden sm:flex items-center h-9 px-4 text-sm font-medium text-[#1a73e8]
                         hover:bg-[#e8f0fe] rounded-full transition-colors">
              Log in
            </Link>
            <Link href="/register"
              className="flex items-center h-9 px-5 text-sm font-medium text-white rounded-full transition-all
                         bg-[#1a73e8] hover:bg-[#1557b0] hover:shadow-md"
              style={{ boxShadow: "0 1px 3px rgba(26,115,232,.4)" }}>
              Get started
            </Link>
          </div>
        </div>
      </header>

      {/* ── Category chips ── */}
      <div className="bg-white border-b border-[#e8eaed] sticky top-16 z-40">
        <div className="max-w-[1440px] mx-auto px-4 sm:px-6">
          <div className="flex items-center gap-2 py-3 overflow-x-auto no-scrollbar">
            {TABS.map((tab) => {
              const colors = TAB_COLORS[tab.id] ?? TAB_COLORS.all;
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center gap-1.5 h-8 px-4 rounded-full text-sm font-medium
                    whitespace-nowrap transition-all duration-200 shrink-0
                    ${isActive ? colors.active + " shadow-sm" : "bg-[#f1f3f4] text-[#202124] hover:bg-[#e8eaed]"}`}
                >
                  {isActive && (
                    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 16 16">
                      <path stroke="currentColor" strokeWidth="2" strokeLinecap="round" d="M3 8l4 4 6-6"/>
                    </svg>
                  )}
                  {tab.label}
                </button>
              );
            })}
          </div>
        </div>
      </div>

      <main className="flex-1 max-w-[1440px] w-full mx-auto px-4 sm:px-6 py-6">

        {/* Popular row */}
        {activeTab === "all" && (
          <div className="mb-8 animate-fade-up">
            <p className="text-xs font-medium text-[#5f6368] uppercase tracking-widest mb-3">
              Popular
            </p>
            <div className="flex flex-wrap gap-2">
              {POPULAR.map((id) => {
                const tool = TOOLS.find((t) => t.id === id)!;
                return (
                  <Link key={id} href={`/tools/${id}`}
                    className="flex items-center gap-2 h-9 pl-2 pr-4 rounded-full
                               bg-white border border-[#dadce0] hover:border-[#1a73e8]
                               hover:bg-[#e8f0fe] hover:shadow-sm transition-all group"
                  >
                    <div className={`w-5 h-5 ${tool.bgLight} rounded-full flex items-center justify-center`}>
                      <Image src={tool.icon} alt="" width={12} height={12} className="w-3 h-3" />
                    </div>
                    <span className="text-xs font-medium text-[#202124] group-hover:text-[#1a73e8]">
                      {tool.name}
                    </span>
                  </Link>
                );
              })}
            </div>
          </div>
        )}

        {/* Section heading */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <h2 className="text-base font-medium text-[#202124]">
              {TABS.find((t) => t.id === activeTab)?.label}
            </h2>
            <span className="text-xs text-[#5f6368] bg-[#e8eaed] px-2 py-0.5 rounded-full">
              {visible.length}
            </span>
          </div>
        </div>

        {/* Tool grid */}
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-3 animate-fade-up">
          {visible.map((tool) => (
            <Link
              key={tool.id}
              href={`/tools/${tool.id}`}
              className="group flex flex-col items-center text-center gap-3 p-4 sm:p-5 bg-white rounded-2xl
                         border border-[#e8eaed] hover:border-transparent
                         hover:-translate-y-1 transition-all duration-200 cursor-pointer"
              style={{ boxShadow: "0 1px 2px rgba(0,0,0,0.06)" }}
              onMouseEnter={e => (e.currentTarget.style.boxShadow = "0 4px 16px rgba(0,0,0,0.12)")}
              onMouseLeave={e => (e.currentTarget.style.boxShadow = "0 1px 2px rgba(0,0,0,0.06)")}
            >
              {/* Icon container */}
              <div className={`w-14 h-14 ${tool.bgLight} rounded-2xl flex items-center justify-center
                               group-hover:scale-110 transition-transform duration-200`}>
                <Image src={tool.icon} alt={tool.name} width={28} height={28} className="w-7 h-7" />
              </div>

              <div>
                <p className="text-sm font-medium text-[#202124] leading-snug">{tool.name}</p>
                <p className="text-xs text-[#5f6368] mt-1 leading-snug line-clamp-2">{tool.description}</p>
              </div>
            </Link>
          ))}
        </div>
      </main>

    </div>
  );
}
