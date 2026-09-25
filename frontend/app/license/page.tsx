"use client";
import { useEffect, useState } from "react";
import Sidebar from "@/components/Sidebar";
import { apiFetch } from "@/lib/api";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const TIER_INFO = [
  {
    id: "trial",
    name: "Trial",
    tagline: "7 days, full access",
    features: [
      "Variant annotation",
      "ACMG classification",
      "FHIR / JSON / HL7 export",
      "Up to 5 samples",
    ],
    color: "border-amber-700",
  },
  {
    id: "standard",
    name: "Standard",
    tagline: "For individual researchers and small labs",
    features: [
      "Everything in Trial",
      "Unlimited samples",
      "Multi-user access",
      "PDF reports",
      "Priority support",
    ],
    color: "border-emerald-700",
  },
  {
    id: "enterprise",
    name: "Enterprise",
    tagline: "For labs with integration and compliance needs",
    features: [
      "Everything in Standard",
      "Full network access",
      "Custom integrations (LIMS, EHR)",
      "On-prem deployment",
      "Dedicated support",
    ],
    color: "border-purple-700",
  },
];

export default function LicensePage() {
  const [status, setStatus] = useState<any>(null);
  const [machine, setMachine] = useState<string>("");
  const [tokenText, setTokenText] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  function load() {
    fetch(`${API_URL}/license/status`).then((r) => r.json()).then(setStatus).catch(() => {});
    fetch(`${API_URL}/license/machine`).then((r) => r.json()).then((d) => setMachine(d.machine_fingerprint)).catch(() => {});
  }

  useEffect(() => { load(); }, []);

  async function activate() {
    setBusy(true); setMessage(null); setError(null);
    try {
      const parsed = JSON.parse(tokenText.trim());
      await apiFetch("/license/activate", {
        method: "POST",
        body: JSON.stringify({ token: parsed }),
      });
      setMessage("License activated.");
      setTokenText("");
      load();
    } catch (e: any) {
      setError(e.message || "Failed to parse license token");
    } finally {
      setBusy(false);
    }
  }

  async function deactivate() {
    if (!confirm("Remove the current license from this machine?")) return;
    setBusy(true);
    try {
      await apiFetch("/license/deactivate", { method: "POST" });
      setMessage("License removed.");
      load();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  function copyMachine() {
    navigator.clipboard.writeText(machine);
    setMessage("Machine fingerprint copied. Send this to activate your license.");
    setTimeout(() => setMessage(null), 3000);
  }

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 p-8">
        <h1 className="text-2xl font-bold mb-6">License</h1>

        {message && (
          <div className="bg-emerald-950 border border-emerald-800 text-emerald-300 rounded p-3 text-sm mb-4">
            {message}
          </div>
        )}
        {error && (
          <div className="bg-red-950 border border-red-900 text-red-300 rounded p-3 text-sm mb-4">
            {error}
          </div>
        )}

        <div className="bg-slate-900 rounded-lg border border-slate-800 p-6 mb-6">
          <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wide mb-4">
            Current License
          </h2>
          {status ? (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-slate-400 text-sm">Tier</span>
                <span className={`text-sm font-semibold ${
                  !status.valid ? "text-red-400" :
                  status.tier === "enterprise" ? "text-purple-400" :
                  status.tier === "trial" ? "text-amber-400" : "text-emerald-400"
                }`}>
                  {status.tier}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-400 text-sm">Status</span>
                <span className="text-sm">
                  {status.valid ? "Active" : "Not activated"}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-400 text-sm">Network policy</span>
                <span className="text-sm font-mono">{status.network_policy}</span>
              </div>
              {status.expires_at && (
                <div className="flex items-center justify-between">
                  <span className="text-slate-400 text-sm">Expires</span>
                  <span className="text-sm">
                    {new Date(status.expires_at).toLocaleDateString()}
                    {status.days_remaining !== null && (
                      <span className={`ml-2 ${status.days_remaining < 14 ? "text-amber-400" : "text-slate-500"}`}>
                        ({status.days_remaining} days)
                      </span>
                    )}
                  </span>
                </div>
              )}
              {status.customer_email && (
                <div className="flex items-center justify-between">
                  <span className="text-slate-400 text-sm">Licensed to</span>
                  <span className="text-sm">{status.customer_email}</span>
                </div>
              )}
              {status.grace_period_active && (
                <div className="bg-amber-950 border border-amber-900 text-amber-300 rounded p-3 text-xs">
                  ⚠ License expired — running in grace period. Renew to avoid disruption.
                </div>
              )}
              {status.valid && (
                <button
                  onClick={deactivate}
                  disabled={busy}
                  className="mt-3 text-xs text-red-400 hover:underline"
                >
                  Deactivate license on this machine
                </button>
              )}
            </div>
          ) : (
            <p className="text-slate-500 text-sm">Loading...</p>
          )}
        </div>

        <div className="bg-slate-900 rounded-lg border border-slate-800 p-6 mb-6">
          <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wide mb-4">
            Your Machine Fingerprint
          </h2>
          <p className="text-xs text-slate-500 mb-3">
            Send this to us at{" "}
            <a href="mailto:support@genomicsops.io" className="text-emerald-400 hover:underline">
              support@genomicsops.io
            </a>{" "}
            to receive your license. We'll send back a license file you can paste below.
          </p>
          <div className="flex gap-2">
            <input
              value={machine}
              readOnly
              className="flex-1 bg-slate-950 border border-slate-800 rounded px-3 py-2 text-xs font-mono"
            />
            <button
              onClick={copyMachine}
              className="bg-emerald-600 hover:bg-emerald-500 px-4 py-2 rounded text-xs font-medium"
            >
              Copy
            </button>
          </div>
        </div>

        <div className="bg-slate-900 rounded-lg border border-slate-800 p-6 mb-6">
          <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wide mb-4">
            Activate a License
          </h2>
          <p className="text-xs text-slate-500 mb-3">
            Paste the license token you received from us.
          </p>
          <textarea
            value={tokenText}
            onChange={(e) => setTokenText(e.target.value)}
            placeholder='{"payload": {...}, "signature": "..."}'
            rows={6}
            className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-xs font-mono mb-3"
          />
          <button
            onClick={activate}
            disabled={busy || !tokenText.trim()}
            className="bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 px-4 py-2 rounded text-sm font-medium"
          >
            {busy ? "Activating..." : "Activate"}
          </button>
        </div>

        <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wide mb-4">
          Available Plans
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {TIER_INFO.map((t) => (
            <div key={t.id} className={`bg-slate-900 border-2 rounded-lg p-5 ${t.color}`}>
              <div className="text-lg font-bold mb-1">{t.name}</div>
              <div className="text-xs text-emerald-400 mb-4">{t.tagline}</div>
              <ul className="text-xs text-slate-400 space-y-1.5">
                {t.features.map((f) => <li key={f}>✓ {f}</li>)}
              </ul>
            </div>
          ))}
        </div>
        <p className="text-xs text-slate-500 mt-4">
          Contact{" "}
          <a href="mailto:sales@genomicsops.io" className="text-emerald-400 hover:underline">
            sales@genomicsops.io
          </a>{" "}
          for pricing.
        </p>
      </main>
    </div>
  );
}
