"use client";
import { useState, useEffect, useCallback, useRef } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

// ── Math CAPTCHA generator ─────────────────────────────────────────────────
function generateCaptcha() {
  const ops = ["+", "-", "×"] as const;
  const op = ops[Math.floor(Math.random() * ops.length)];
  let a = Math.floor(Math.random() * 9) + 1;
  let b = Math.floor(Math.random() * 9) + 1;
  if (op === "-" && b > a) [a, b] = [b, a]; // keep positive
  const answer = op === "+" ? a + b : op === "-" ? a - b : a * b;
  return { question: `${a} ${op} ${b} = ?`, answer };
}

// ── Captcha canvas drawing ─────────────────────────────────────────────────
function drawCaptcha(canvas: HTMLCanvasElement, text: string) {
  const ctx = canvas.getContext("2d");
  if (!ctx) return;
  const W = canvas.width, H = canvas.height;

  // Background with subtle noise
  ctx.fillStyle = "#f0f4ff";
  ctx.fillRect(0, 0, W, H);

  // Noise dots
  for (let i = 0; i < 40; i++) {
    ctx.beginPath();
    ctx.arc(Math.random() * W, Math.random() * H, 1, 0, Math.PI * 2);
    ctx.fillStyle = `rgba(100,120,200,${Math.random() * 0.3})`;
    ctx.fill();
  }

  // Wavy lines
  for (let i = 0; i < 3; i++) {
    ctx.beginPath();
    ctx.moveTo(0, H * 0.3 + i * H * 0.2);
    for (let x = 0; x < W; x += 8) {
      ctx.lineTo(x, H * 0.3 + i * H * 0.2 + Math.sin(x / 12 + i) * 5);
    }
    ctx.strokeStyle = `rgba(100,130,220,0.2)`;
    ctx.lineWidth = 1;
    ctx.stroke();
  }

  // Text with slight char-by-char rotation
  const chars = text.split("");
  const totalW = chars.length * 22;
  let startX = (W - totalW) / 2 + 8;

  chars.forEach((ch, i) => {
    ctx.save();
    const x = startX + i * 22;
    const y = H / 2 + 6;
    ctx.translate(x, y);
    ctx.rotate((Math.random() - 0.5) * 0.35);
    ctx.font = `bold ${20 + Math.floor(Math.random() * 4)}px monospace`;
    ctx.fillStyle = ["#1a56db", "#1a56db", "#2563eb", "#1e40af"][Math.floor(Math.random() * 4)];
    ctx.fillText(ch, 0, 0);
    ctx.restore();
  });
}

// ── Input style ───────────────────────────────────────────────────────────
const inp = `w-full h-12 bg-white border border-[#dadce0] rounded-xl px-4 text-sm text-[#202124]
  focus:outline-none focus:border-[#1a73e8] focus:ring-2 focus:ring-[#1a73e8]/20 transition-all`;

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail]       = useState("");
  const [password, setPassword] = useState("");
  const [showPw, setShowPw]     = useState(false);
  const [remember, setRemember] = useState(false);
  const [captchaInput, setCaptchaInput] = useState("");
  const [captcha, setCaptcha]   = useState(generateCaptcha);
  const [captchaError, setCaptchaError] = useState(false);
  const [error, setError]       = useState("");
  const [loading, setLoading]   = useState(false);
  const [attempts, setAttempts] = useState(0);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  const refreshCaptcha = useCallback(() => {
    setCaptcha(generateCaptcha());
    setCaptchaInput("");
    setCaptchaError(false);
  }, []);

  // Draw captcha on canvas whenever question changes
  useEffect(() => {
    if (canvasRef.current) drawCaptcha(canvasRef.current, captcha.question);
  }, [captcha]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");

    // Validate CAPTCHA
    if (parseInt(captchaInput, 10) !== captcha.answer) {
      setCaptchaError(true);
      refreshCaptcha();
      setAttempts((n) => n + 1);
      return;
    }

    setLoading(true);
    try {
      const { access_token } = await api.post("/auth/login", { email, password });
      if (remember) localStorage.setItem("token", access_token);
      else sessionStorage.setItem("token", access_token);
      router.push("/");
    } catch {
      setError("Incorrect email address or password.");
      setAttempts((n) => n + 1);
      refreshCaptcha();
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex flex-col" style={{ background: "linear-gradient(135deg,#f0f4ff 0%,#f8f9fa 60%,#e8f0fe 100%)" }}>

      {/* Header */}
      <header className="bg-white sticky top-0 z-50" style={{ boxShadow: "0 1px 3px rgba(0,0,0,0.10)" }}>
        <div className="max-w-7xl mx-auto px-4 h-16 flex items-center">
          <Link href="/" className="flex items-center gap-3">
            <img src="/logo-header.png" alt="Logo" className="h-10 w-auto object-contain" onError={(e) => (e.currentTarget.style.display = "none")} />
            <span className="text-lg font-bold text-[#2e3b8e] tracking-tight leading-tight">
              Eastern Power Distribution Company of AP Limited
            </span>
          </Link>
        </div>
      </header>

      {/* Main */}
      <div className="flex-1 flex items-center justify-center px-4 py-16">
        <div className="w-full max-w-sm animate-fade-up">

          {/* Lock icon */}
          <div className="flex justify-center mb-6">
            <div className="w-16 h-16 rounded-2xl flex items-center justify-center"
              style={{ background: "linear-gradient(135deg,#1a73e8,#4285f4)", boxShadow: "0 4px 16px rgba(26,115,232,.35)" }}>
              <svg className="w-8 h-8 text-white" fill="none" viewBox="0 0 24 24">
                <path stroke="currentColor" strokeWidth="2" strokeLinecap="round"
                  d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"/>
              </svg>
            </div>
          </div>

          {/* Card */}
          <div className="bg-white rounded-3xl p-8" style={{ boxShadow: "0 4px 24px rgba(0,0,0,0.10)" }}>
            <div className="mb-7 text-center">
              <h1 className="text-2xl font-semibold text-[#202124]">Welcome back</h1>
              <p className="text-sm text-[#5f6368] mt-1">Sign in to continue to PDFKit</p>
            </div>

            {/* Error banner */}
            {error && (
              <div className="flex items-start gap-3 px-4 py-3 mb-5 bg-[#fce8e6] rounded-xl border border-[#f5c6c3]">
                <svg className="w-5 h-5 text-[#d93025] shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9 9V5h2v4H9zm0 4v-2h2v2H9z" clipRule="evenodd"/>
                </svg>
                <p className="text-sm text-[#c5221f]">{error}</p>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-5">

              {/* Email */}
              <div>
                <label className="block text-sm font-medium text-[#202124] mb-2">Email address</label>
                <input type="email" required value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className={inp} placeholder="you@example.com" autoComplete="email" />
              </div>

              {/* Password */}
              <div>
                <div className="flex justify-between items-center mb-2">
                  <label className="text-sm font-medium text-[#202124]">Password</label>
                  <Link href="/forgot-password" className="text-xs text-[#1a73e8] hover:underline">
                    Forgot password?
                  </Link>
                </div>
                <div className="relative">
                  <input type={showPw ? "text" : "password"} required value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className={inp + " pr-12"} placeholder="••••••••" autoComplete="current-password" />
                  <button type="button" onClick={() => setShowPw(!showPw)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 p-1 text-[#9aa0a6] hover:text-[#5f6368] transition-colors">
                    {showPw ? (
                      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24">
                        <path stroke="currentColor" strokeWidth="2" strokeLinecap="round"
                          d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21"/>
                      </svg>
                    ) : (
                      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24">
                        <path stroke="currentColor" strokeWidth="2" strokeLinecap="round"
                          d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                        <path stroke="currentColor" strokeWidth="2" strokeLinecap="round"
                          d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>
                      </svg>
                    )}
                  </button>
                </div>
              </div>

              {/* CAPTCHA */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="text-sm font-medium text-[#202124]">Security check</label>
                  <button type="button" onClick={refreshCaptcha}
                    className="flex items-center gap-1 text-xs text-[#1a73e8] hover:underline">
                    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24">
                      <path stroke="currentColor" strokeWidth="2" strokeLinecap="round"
                        d="M4 4v5h5M20 20v-5h-5M4 9a9 9 0 0115 0M20 15a9 9 0 01-15 0"/>
                    </svg>
                    Refresh
                  </button>
                </div>
                <div className="flex gap-3 items-stretch">
                  {/* Canvas captcha image */}
                  <div className="relative rounded-xl overflow-hidden border border-[#dadce0] flex-shrink-0"
                    style={{ width: 180, height: 48 }}>
                    <canvas ref={canvasRef} width={180} height={48} className="block" />
                  </div>
                  {/* Answer input */}
                  <input
                    type="number" required
                    value={captchaInput}
                    onChange={(e) => { setCaptchaInput(e.target.value); setCaptchaError(false); }}
                    className={`flex-1 h-12 bg-white border rounded-xl px-4 text-sm text-[#202124]
                      focus:outline-none focus:ring-2 transition-all
                      ${captchaError
                        ? "border-[#d93025] focus:border-[#d93025] focus:ring-[#d93025]/20 bg-[#fff8f8]"
                        : "border-[#dadce0] focus:border-[#1a73e8] focus:ring-[#1a73e8]/20"}`}
                    placeholder="Answer"
                  />
                </div>
                {captchaError && (
                  <p className="text-xs text-[#d93025] mt-1.5 flex items-center gap-1">
                    <svg className="w-3.5 h-3.5 shrink-0" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd"/>
                    </svg>
                    Incorrect answer — a new challenge has been generated
                  </p>
                )}
              </div>

              {/* Remember me */}
              <label className="flex items-center gap-3 cursor-pointer select-none">
                <div onClick={() => setRemember(!remember)}
                  className={`w-5 h-5 rounded border-2 flex items-center justify-center transition-all flex-shrink-0
                    ${remember ? "bg-[#1a73e8] border-[#1a73e8]" : "border-[#dadce0] bg-white"}`}>
                  {remember && (
                    <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24">
                      <path stroke="currentColor" strokeWidth="3" strokeLinecap="round" d="M5 13l4 4L19 7"/>
                    </svg>
                  )}
                </div>
                <span className="text-sm text-[#5f6368]">Keep me signed in</span>
              </label>

              {/* Attempt warning */}
              {attempts >= 3 && (
                <div className="flex items-start gap-2 px-3 py-2.5 bg-[#fef3cd] rounded-xl border border-[#fdd663]">
                  <svg className="w-4 h-4 text-[#b45309] shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd"/>
                  </svg>
                  <p className="text-xs text-[#92400e]">Multiple failed attempts detected. Please solve the CAPTCHA carefully.</p>
                </div>
              )}

              {/* Submit */}
              <button type="submit" disabled={loading || !captchaInput}
                className="w-full h-12 rounded-full text-sm font-semibold text-white transition-all mt-1
                           disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                style={{
                  background: (loading || !captchaInput) ? "#dadce0" : "linear-gradient(135deg,#1a73e8,#4285f4)",
                  boxShadow: (loading || !captchaInput) ? "none" : "0 2px 10px rgba(26,115,232,.4)"
                }}>
                {loading ? (
                  <>
                    <div className="w-4 h-4 rounded-full border-2 border-white/30 border-t-white animate-spin" />
                    Signing in…
                  </>
                ) : (
                  <>
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24">
                      <path stroke="currentColor" strokeWidth="2" strokeLinecap="round"
                        d="M11 16l-4-4m0 0l4-4m-4 4h14m-5 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h7a3 3 0 013 3v1"/>
                    </svg>
                    Sign in
                  </>
                )}
              </button>
            </form>
          </div>

          {/* Footer */}
          <div className="mt-6 text-center space-y-2">
            <p className="text-sm text-[#5f6368]">
              Don&apos;t have an account?{" "}
              <Link href="/register" className="text-[#1a73e8] hover:underline font-medium">
                Create one free
              </Link>
            </p>
            <p className="text-xs text-[#9aa0a6]">
              Protected by CAPTCHA · Your files are encrypted in transit
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
