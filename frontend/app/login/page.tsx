"use client";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Image from "next/image";
import { isLocal, setLocalToken, setLocalUser, getLocalToken } from "@/lib/mode";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function Login() {
  const router = useRouter();
  const [mode, setMode] = useState<"loading" | "cloud" | "local">("loading");

  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [cloudError, setCloudError] = useState<string | null>(null);

  const [localEmail, setLocalEmail] = useState("");
  const [localPassword, setLocalPassword] = useState("");
  const [localError, setLocalError] = useState<string | null>(null);
  const [localBusy, setLocalBusy] = useState(false);

  useEffect(() => {
    if (isLocal) {
      setMode("local");
      if (getLocalToken()) router.push("/dashboard");
    } else {
      setMode("cloud");
    }
  }, [router]);

  async function cloudSignIn() {
    setCloudError(null);
    const { supabase } = await import("@/lib/supabase");
    const { error } = await supabase.auth.signInWithOtp({
      email,
      options: { emailRedirectTo: `${window.location.origin}/dashboard` },
    });
    if (error) setCloudError(error.message);
    else setSent(true);
  }

  async function cloudGuest() {
    setCloudError(null);
    const { supabase } = await import("@/lib/supabase");
    const { error } = await supabase.auth.signInAnonymously();
    if (error) setCloudError(error.message);
    else router.push("/dashboard");
  }

  async function localLogin() {
    setLocalBusy(true);
    setLocalError(null);
    try {
      const res = await fetch(`${API_URL}/local-auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: localEmail.trim(), password: localPassword }),
      });
      if (!res.ok) {
        const text = await res.text();
        setLocalError(text || "Login failed");
        return;
      }
      const data = await res.json();
      setLocalToken(data.token);
      setLocalUser(data.user);
      document.cookie = `genomicsops_local_token=${data.token}; path=/; max-age=604800; SameSite=Lax`;
      router.push("/dashboard");
    } catch (e: any) {
      setLocalError(e.message);
    } finally {
      setLocalBusy(false);
    }
  }

  if (mode === "loading") {
    return <div className="min-h-screen flex items-center justify-center text-slate-500">Loading...</div>;
  }

  function Logo() {
    return (
      <div className="flex flex-col items-center mb-8">
        <img
          src="/logo-sidebar.png"
          alt="GenomicsOps"
          className="w-full max-w-[220px] h-auto"
        />
        <div className="text-[10px] text-amber-500 uppercase tracking-wider mt-3">
          Research Use Only
        </div>
      </div>
    );
  }

  if (mode === "local") {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="max-w-sm w-full">
          <Logo />
          <p className="text-slate-500 text-xs text-center mb-6">Local installation</p>

          <label className="text-xs text-slate-500 block mb-1">Email</label>
          <input
            value={localEmail}
            onChange={(e) => setLocalEmail(e.target.value)}
            type="email"
            placeholder="admin@local"
            className="w-full bg-slate-900 border border-slate-800 rounded px-3 py-2 mb-3"
            autoComplete="username"
          />

          <label className="text-xs text-slate-500 block mb-1">Password</label>
          <input
            value={localPassword}
            onChange={(e) => setLocalPassword(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && localLogin()}
            type="password"
            className="w-full bg-slate-900 border border-slate-800 rounded px-3 py-2 mb-4"
            autoComplete="current-password"
          />

          <button
            onClick={localLogin}
            disabled={localBusy || !localEmail || !localPassword}
            className="w-full bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 py-2 rounded font-medium"
          >
            {localBusy ? "Signing in..." : "Sign in"}
          </button>

          {localError && <p className="text-red-400 text-sm mt-3">{localError}</p>}

          <p className="text-xs text-slate-600 mt-6 text-center">
            Default: <span className="font-mono">admin@local / admin</span>
          </p>
        </div>
      </div>
    );
  }

  if (sent) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="max-w-sm w-full">
          <Logo />
          <div className="text-center">
            <h1 className="text-xl font-semibold mb-2">Check your email</h1>
            <p className="text-slate-400 text-sm">We sent a magic link to {email}</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="max-w-sm w-full">
        <Logo />
        <input
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          type="email"
          placeholder="you@lab.org"
          className="w-full bg-slate-900 border border-slate-800 rounded px-3 py-2 mb-3"
        />
        <button
          onClick={cloudSignIn}
          className="w-full bg-emerald-600 hover:bg-emerald-500 py-2 rounded font-medium"
        >
          Send magic link
        </button>
        <button
          onClick={cloudGuest}
          className="w-full mt-2 text-sm text-slate-400 hover:text-slate-200 py-2"
        >
          Continue as guest
        </button>
        {cloudError && <p className="text-red-400 text-sm mt-3">{cloudError}</p>}
      </div>
    </div>
  );
}
