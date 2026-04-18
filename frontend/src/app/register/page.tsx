"use client";
import { useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

export default function RegisterPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (password.length < 8) { setError("Password must be at least 8 characters."); return; }
    setLoading(true);
    setError("");
    try {
      const { access_token } = await api.post("/auth/register", { email, password });
      localStorage.setItem("token", access_token);
      router.push("/");
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(msg || "Registration failed. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-[#f8f9fa] flex flex-col">
      {/* App bar */}
      <header className="bg-white sticky top-0 z-50" style={{ boxShadow: "0 1px 3px rgba(0,0,0,0.12)" }}>
        <div className="max-w-7xl mx-auto px-4 h-16 flex items-center">
          <Link href="/" className="flex items-center gap-3">
            <img src="/logo-header.png" alt="APEPDCL" className="h-10 w-auto object-contain" />
            <span className="text-lg font-bold text-[#2e3b8e] tracking-tight leading-tight">Eastern Power Distribution Company of Andhra Pradesh Limited</span>
          </Link>
        </div>
      </header>

      {/* Content */}
      <div className="flex-1 flex items-center justify-center px-4 py-16">
        <div className="w-full max-w-sm animate-fade-up">
          {/* Card */}
          <div className="bg-white rounded-3xl p-8" style={{ boxShadow: "0 2px 12px rgba(0,0,0,0.08)" }}>
            <div className="mb-8">
              <h1 className="text-2xl font-medium text-[#202124]">Create account</h1>
              <p className="text-sm text-[#5f6368] mt-1">No credit card required · Free forever</p>
            </div>

            {error && (
              <div className="flex items-start gap-3 px-4 py-3 mb-6 bg-[#fce8e6] rounded-xl">
                <svg className="w-5 h-5 text-[#d93025] shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9 9V5h2v4H9zm0 4v-2h2v2H9z" clipRule="evenodd"/>
                </svg>
                <p className="text-sm text-[#c5221f]">{error}</p>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-5">
              <div>
                <label className="block text-sm font-medium text-[#202124] mb-2">Email address</label>
                <input
                  type="email" required
                  value={email} onChange={(e) => setEmail(e.target.value)}
                  className="w-full h-12 bg-white border border-[#dadce0] rounded-xl px-4 text-sm text-[#202124]
                             focus:outline-none focus:border-[#1a73e8] focus:ring-2 focus:ring-[#1a73e8]/20 transition-all"
                  placeholder="you@example.com"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-[#202124] mb-2">Password</label>
                <input
                  type="password" required
                  value={password} onChange={(e) => setPassword(e.target.value)}
                  className="w-full h-12 bg-white border border-[#dadce0] rounded-xl px-4 text-sm text-[#202124]
                             focus:outline-none focus:border-[#1a73e8] focus:ring-2 focus:ring-[#1a73e8]/20 transition-all"
                  placeholder="At least 8 characters"
                />
                <p className="mt-1.5 text-xs text-[#9aa0a6]">Minimum 8 characters</p>
              </div>

              <button
                type="submit" disabled={loading}
                className="w-full h-12 rounded-full text-sm font-medium text-white transition-all
                           disabled:opacity-50 disabled:cursor-not-allowed mt-2"
                style={{
                  background: loading ? "#dadce0" : "linear-gradient(135deg,#1a73e8,#4285f4)",
                  boxShadow: loading ? "none" : "0 2px 8px rgba(26,115,232,.4)"
                }}
              >
                {loading ? "Creating account…" : "Create account"}
              </button>
            </form>
          </div>

          <p className="text-sm text-center text-[#5f6368] mt-6">
            Already have an account?{" "}
            <Link href="/login" className="text-[#1a73e8] hover:underline font-medium">
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
