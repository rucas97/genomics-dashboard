"use client";
import { useState } from "react";
import { supabase } from "@/lib/supabase";
import { useRouter } from "next/navigation";

export default function Login() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  async function sendMagicLink() {
    setError(null);
    const { error } = await supabase.auth.signInWithOtp({
      email,
      options: { emailRedirectTo: `${window.location.origin}/dashboard` },
    });
    if (error) setError(error.message); else setSent(true);
  }

  async function guest() {
    const { error } = await supabase.auth.signInAnonymously();
    if (error) setError(error.message); else router.push("/dashboard");
  }

  if (sent) return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-center">
        <h1 className="text-xl font-semibold mb-2">Check your email</h1>
        <p className="text-slate-400">We sent a magic link to {email}</p>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="max-w-sm w-full">
        <h1 className="text-2xl font-bold mb-6">Sign in</h1>
        <input value={email} onChange={(e) => setEmail(e.target.value)} type="email" placeholder="you@lab.org"
          className="w-full bg-slate-900 border border-slate-800 rounded px-3 py-2 mb-3" />
        <button onClick={sendMagicLink} className="w-full bg-emerald-600 hover:bg-emerald-500 py-2 rounded font-medium">
          Send magic link
        </button>
        <button onClick={guest} className="w-full mt-2 text-sm text-slate-400 hover:text-slate-200 py-2">
          Continue as guest
        </button>
        {error && <p className="text-red-400 text-sm mt-3">{error}</p>}
      </div>
    </div>
  );
}
