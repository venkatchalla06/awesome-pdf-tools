"use client";
import { useState, useEffect, useCallback, useRef } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

// ── Math CAPTCHA ───────────────────────────────────────────────────────────
function generateCaptcha() {
  const ops = ["+", "-", "×"] as const;
  const op = ops[Math.floor(Math.random() * ops.length)];
  let a = Math.floor(Math.random() * 9) + 1;
  let b = Math.floor(Math.random() * 9) + 1;
  if (op === "-" && b > a) [a, b] = [b, a];
  const answer = op === "+" ? a + b : op === "-" ? a - b : a * b;
  return { question: `${a} ${op} ${b} = ?`, answer };
}

function drawCaptcha(canvas: HTMLCanvasElement, text: string) {
  const ctx = canvas.getContext("2d");
  if (!ctx) return;
  const W = canvas.width, H = canvas.height;
  ctx.fillStyle = "#f0f4ff";
  ctx.fillRect(0, 0, W, H);
  for (let i = 0; i < 40; i++) {
    ctx.beginPath();
    ctx.arc(Math.random() * W, Math.random() * H, Math.random() * 2, 0, Math.PI * 2);
    ctx.fillStyle = `rgba(${Math.random()*150},${Math.random()*150},${Math.random()*200},0.4)`;
    ctx.fill();
  }
  for (let i = 0; i < 3; i++) {
    ctx.beginPath();
    ctx.moveTo(Math.random() * W, Math.random() * H);
    ctx.bezierCurveTo(
      Math.random() * W, Math.random() * H,
      Math.random() * W, Math.random() * H,
      Math.random() * W, Math.random() * H
    );
    ctx.strokeStyle = `rgba(100,120,200,0.3)`;
    ctx.lineWidth = 1.5;
    ctx.stroke();
  }
  const chars = text.split("");
  const charW = W / (chars.length + 1);
  chars.forEach((ch, i) => {
    ctx.save();
    ctx.font = `bold ${20 + Math.random() * 6}px monospace`;
    ctx.fillStyle = `hsl(${220 + Math.random() * 40},60%,35%)`;
    const x = charW * (i + 0.8) + Math.random() * 6 - 3;
    const y = H / 2 + 7 + Math.random() * 6 - 3;
    ctx.translate(x, y);
    ctx.rotate((Math.random() - 0.5) * 0.4);
    ctx.fillText(ch, 0, 0);
    ctx.restore();
  });
}

// ── Password strength ──────────────────────────────────────────────────────
function passwordStrength(pw: string): { score: number; label: string; color: string } {
  if (!pw) return { score: 0, label: "", color: "" };
  let score = 0;
  if (pw.length >= 8) score++;
  if (pw.length >= 12) score++;
  if (/[A-Z]/.test(pw)) score++;
  if (/[0-9]/.test(pw)) score++;
  if (/[^A-Za-z0-9]/.test(pw)) score++;
  if (score <= 1) return { score, label: "Weak", color: "#d93025" };
  if (score <= 3) return { score, label: "Fair", color: "#f29900" };
  if (score === 4) return { score, label: "Good", color: "#1e8e3e" };
  return { score, label: "Strong", color: "#137333" };
}

function EyeIcon({ open }: { open: boolean }) {
  return open ? (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-5 h-5">
      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
      <circle cx="12" cy="12" r="3"/>
    </svg>
  ) : (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-5 h-5">
      <path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94"/>
      <path d="M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19"/>
      <line x1="1" y1="1" x2="23" y2="23"/>
    </svg>
  );
}

const inputCls = `w-full h-12 bg-white border border-[#dadce0] rounded-xl px-4 text-sm text-[#202124]
  focus:outline-none focus:border-[#1a73e8] focus:ring-2 focus:ring-[#1a73e8]/20 transition-all`;

export default function RegisterPage() {
  const router = useRouter();
  const canvasRef = useRef<HTMLCanvasElement>(null);

  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [agreedTerms, setAgreedTerms] = useState(false);
  const [captchaInput, setCaptchaInput] = useState("");
  const [captcha, setCaptcha] = useState({ question: "", answer: 0 });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const strength = passwordStrength(password);

  const refreshCaptcha = useCallback(() => {
    const c = generateCaptcha();
    setCaptcha(c);
    setCaptchaInput("");
    setTimeout(() => {
      if (canvasRef.current) drawCaptcha(canvasRef.current, c.question);
    }, 0);
  }, []);

  useEffect(() => { refreshCaptcha(); }, [refreshCaptcha]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");

    if (password.length < 8) { setError("Password must be at least 8 characters."); return; }
    if (password !== confirmPassword) { setError("Passwords do not match."); return; }
    if (!agreedTerms) { setError("Please accept the terms and conditions."); return; }
    if (parseInt(captchaInput) !== captcha.answer) {
      setError("Incorrect CAPTCHA answer. Please try again.");
      refreshCaptcha();
      return;
    }

    setLoading(true);
    try {
      const { access_token } = await api.post("/auth/register", { email, password });
      localStorage.setItem("token", access_token);
      router.push("/");
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(msg || "Registration failed. Please try again.");
      refreshCaptcha();
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex flex-col" style={{
      background: "linear-gradient(135deg,#1a73e8 0%,#4285f4 40%,#0d47a1 100%)"
    }}>
      {/* Header */}
      <header className="px-6 py-4">
        <Link href="/" className="flex items-center gap-3">
          <img src="/logo-header.png" alt="APEPDCL" className="h-9 w-auto object-contain" />
          <span className="text-white font-semibold text-sm opacity-90 hidden sm:block">
            Eastern Power Distribution Company of Andhra Pradesh Limited
          </span>
        </Link>
      </header>

      {/* Card */}
      <div className="flex-1 flex items-center justify-center px-4 py-8">
        <div className="w-full max-w-md">
          {/* Icon */}
          <div className="flex justify-center mb-5">
            <div className="w-16 h-16 rounded-full bg-white/20 backdrop-blur flex items-center justify-center">
              <svg viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" className="w-8 h-8">
                <path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"/>
                <circle cx="12" cy="7" r="4"/>
              </svg>
            </div>
          </div>
          <h1 className="text-center text-white text-2xl font-bold mb-1">Create Account</h1>
          <p className="text-center text-white/70 text-sm mb-6">Join us today — free forever</p>

          <div className="bg-white rounded-3xl p-8" style={{ boxShadow: "0 8px 32px rgba(0,0,0,0.18)" }}>

            {error && (
              <div className="flex items-start gap-3 px-4 py-3 mb-5 bg-[#fce8e6] rounded-xl">
                <svg className="w-5 h-5 text-[#d93025] shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9 9V5h2v4H9zm0 4v-2h2v2H9z" clipRule="evenodd"/>
                </svg>
                <p className="text-sm text-[#c5221f]">{error}</p>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Full name */}
              <div>
                <label className="block text-sm font-medium text-[#202124] mb-1.5">Full name</label>
                <input
                  type="text"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  className={inputCls}
                  placeholder="John Doe"
                />
              </div>

              {/* Email */}
              <div>
                <label className="block text-sm font-medium text-[#202124] mb-1.5">
                  Email address <span className="text-[#d93025]">*</span>
                </label>
                <input
                  type="email" required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className={inputCls}
                  placeholder="you@example.com"
                />
              </div>

              {/* Password */}
              <div>
                <label className="block text-sm font-medium text-[#202124] mb-1.5">
                  Password <span className="text-[#d93025]">*</span>
                </label>
                <div className="relative">
                  <input
                    type={showPassword ? "text" : "password"} required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className={inputCls + " pr-12"}
                    placeholder="At least 8 characters"
                  />
                  <button type="button" onClick={() => setShowPassword(v => !v)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-[#9aa0a6] hover:text-[#5f6368] transition-colors">
                    <EyeIcon open={showPassword} />
                  </button>
                </div>
                {password && (
                  <div className="mt-2">
                    <div className="flex gap-1 mb-1">
                      {[1,2,3,4,5].map(i => (
                        <div key={i} className="h-1 flex-1 rounded-full transition-all duration-300"
                          style={{ background: i <= strength.score ? strength.color : "#e8eaed" }} />
                      ))}
                    </div>
                    <p className="text-xs font-medium" style={{ color: strength.color }}>{strength.label}</p>
                  </div>
                )}
              </div>

              {/* Confirm password */}
              <div>
                <label className="block text-sm font-medium text-[#202124] mb-1.5">
                  Confirm password <span className="text-[#d93025]">*</span>
                </label>
                <div className="relative">
                  <input
                    type={showConfirm ? "text" : "password"} required
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    className={inputCls + " pr-12" +
                      (confirmPassword && confirmPassword !== password
                        ? " !border-[#d93025] !ring-2 !ring-[#d93025]/20" : "")}
                    placeholder="Re-enter your password"
                  />
                  <button type="button" onClick={() => setShowConfirm(v => !v)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-[#9aa0a6] hover:text-[#5f6368] transition-colors">
                    <EyeIcon open={showConfirm} />
                  </button>
                </div>
                {confirmPassword && confirmPassword !== password && (
                  <p className="mt-1 text-xs text-[#d93025]">Passwords do not match</p>
                )}
                {confirmPassword && confirmPassword === password && (
                  <p className="mt-1 text-xs text-[#1e8e3e] font-medium">✓ Passwords match</p>
                )}
              </div>

              {/* CAPTCHA */}
              <div>
                <label className="block text-sm font-medium text-[#202124] mb-1.5">Security check</label>
                <div className="flex items-center gap-3">
                  <canvas ref={canvasRef} width={180} height={52}
                    className="rounded-xl border border-[#dadce0] select-none flex-shrink-0" />
                  <button type="button" onClick={refreshCaptcha}
                    className="text-[#1a73e8] hover:text-[#1557b0] transition-colors flex-shrink-0" title="Refresh CAPTCHA">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-5 h-5">
                      <path d="M23 4v6h-6M1 20v-6h6"/>
                      <path d="M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15"/>
                    </svg>
                  </button>
                  <input
                    type="number" required
                    value={captchaInput}
                    onChange={(e) => setCaptchaInput(e.target.value)}
                    className="w-24 h-12 bg-white border border-[#dadce0] rounded-xl px-4 text-sm text-[#202124]
                      focus:outline-none focus:border-[#1a73e8] focus:ring-2 focus:ring-[#1a73e8]/20 transition-all"
                    placeholder="Answer"
                  />
                </div>
              </div>

              {/* Terms */}
              <label className="flex items-start gap-3 cursor-pointer select-none pt-1">
                <input type="checkbox" checked={agreedTerms}
                  onChange={(e) => setAgreedTerms(e.target.checked)}
                  className="mt-0.5 w-4 h-4 accent-[#1a73e8] cursor-pointer flex-shrink-0" />
                <span className="text-sm text-[#5f6368]">
                  I agree to the{" "}
                  <a href="#" className="text-[#1a73e8] hover:underline font-medium">Terms of Service</a>
                  {" "}and{" "}
                  <a href="#" className="text-[#1a73e8] hover:underline font-medium">Privacy Policy</a>
                </span>
              </label>

              <button
                type="submit"
                disabled={loading || !email || !password || !confirmPassword || !agreedTerms}
                className="w-full h-12 rounded-full text-sm font-semibold text-white transition-all mt-2
                           disabled:opacity-50 disabled:cursor-not-allowed"
                style={{
                  background: (loading || !email || !password || !confirmPassword || !agreedTerms)
                    ? "#dadce0" : "linear-gradient(135deg,#1a73e8,#4285f4)",
                  boxShadow: (loading || !email || !password || !confirmPassword || !agreedTerms)
                    ? "none" : "0 2px 8px rgba(26,115,232,.4)"
                }}
              >
                {loading ? (
                  <span className="flex items-center justify-center gap-2">
                    <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none">
                      <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" strokeOpacity=".25"/>
                      <path d="M12 2a10 10 0 0110 10" stroke="currentColor" strokeWidth="4" strokeLinecap="round"/>
                    </svg>
                    Creating account…
                  </span>
                ) : "Create account"}
              </button>
            </form>
          </div>

          <p className="text-sm text-center text-white/80 mt-5">
            Already have an account?{" "}
            <Link href="/login" className="text-white font-semibold hover:underline">
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
