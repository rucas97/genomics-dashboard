"use client";
import { useEffect, useState } from "react";
import Sidebar from "@/components/Sidebar";
import { apiFetch } from "@/lib/api";

const ACTION_COLORS: Record<string, string> = {
  upload: "bg-blue-900 text-blue-300",
  view: "bg-slate-800 text-slate-400",
  delete: "bg-red-900 text-red-300",
  gdpr_erase: "bg-red-950 text-red-200",
  export: "bg-purple-900 text-purple-300",
  invite: "bg-emerald-900 text-emerald-300",
  change_role: "bg-amber-900 text-amber-300",
  record_consent: "bg-teal-900 text-teal-300",
  retention_run: "bg-indigo-900 text-indigo-300",
  legal_hold_change: "bg-orange-900 text-orange-300",
  clear_audit: "bg-rose-900 text-rose-300",
};

export default function AuditLog() {
  const [logs, setLogs] = useState<any[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [verifying, setVerifying] = useState(false);
  const [verifyResult, setVerifyResult] = useState<any>(null);
  const [bulkBusy, setBulkBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    try {
      const data = await apiFetch("/audit/");
      setLogs(data);
      setError(null);
    } catch (e: any) {
      setError(e.message);
    }
  }

  useEffect(() => { load(); }, []);

  function toggle(id: string) {
    const next = new Set(selected);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    setSelected(next);
  }

  function toggleAll() {
    if (selected.size === logs.length) setSelected(new Set());
    else setSelected(new Set(logs.map((l) => l.id)));
  }

  async function bulkDelete() {
    if (selected.size === 0) return;
    if (!confirm(
      `Delete ${selected.size} audit entr${selected.size > 1 ? "ies" : "y"}?\n\n` +
      `This will break the tamper-evident hash chain from this point forward. ` +
      `The Verify Integrity button will report the break.`
    )) return;
    setBulkBusy(true);
    try {
      await apiFetch("/audit/bulk-delete", {
        method: "POST",
        body: JSON.stringify({ ids: Array.from(selected) }),
      });
      setSelected(new Set());
      setVerifyResult(null);
    } catch (e: any) {
      setError(e.message);
    } finally {
      await load();
      setBulkBusy(false);
    }
  }

  async function verifyIntegrity() {
    setVerifying(true);
    setVerifyResult(null);
    try {
      const res = await apiFetch("/audit/verify");
      setVerifyResult(res);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setVerifying(false);
    }
  }

  const allSelected = logs.length > 0 && selected.size === logs.length;

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 p-8">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold">Audit Log</h1>
          <div className="flex gap-2">
            {selected.size > 0 && (
              <button
                onClick={bulkDelete}
                disabled={bulkBusy}
                className="bg-red-950 hover:bg-red-900 border border-red-900 disabled:opacity-50 px-4 py-2 rounded text-sm font-medium text-red-300"
              >
                {bulkBusy ? "Deleting..." : `Delete ${selected.size} selected`}
              </button>
            )}
            <button
              onClick={verifyIntegrity}
              disabled={verifying}
              className="bg-emerald-950 hover:bg-emerald-900 border border-emerald-900 disabled:opacity-50 px-4 py-2 rounded text-sm font-medium text-emerald-300"
            >
              {verifying ? "Verifying..." : "Verify Integrity"}
            </button>
          </div>
        </div>

        {verifyResult && (
          <div className={`mb-4 rounded p-3 text-sm border ${
            verifyResult.ok
              ? "bg-emerald-950 border-emerald-900 text-emerald-300"
              : "bg-red-950 border-red-900 text-red-300"
          }`}>
            {verifyResult.ok ? (
              <>
                <div className="font-semibold mb-1">✓ Chain verified</div>
                <div className="text-xs opacity-90">
                  {verifyResult.entries_verified} entries · chain head{" "}
                  <span className="font-mono">{verifyResult.chain_head?.slice(0, 16)}...</span>
                </div>
              </>
            ) : (
              <>
                <div className="font-semibold mb-1">✗ Chain broken</div>
                <div className="text-xs opacity-90">
                  {verifyResult.reason} at entry index {verifyResult.broken_at_index}
                  {" "}(id <span className="font-mono">{verifyResult.broken_at_id?.slice(0, 8)}</span>)
                </div>
              </>
            )}
          </div>
        )}

        {error && <p className="text-red-400 mb-4 text-sm">{error}</p>}

        <div className="bg-slate-900 rounded-lg border border-slate-800">
          {logs.length > 0 && (
            <div className="flex items-center gap-3 px-4 py-2 bg-slate-800 border-b border-slate-700 text-xs text-slate-400">
              <input type="checkbox" checked={allSelected} onChange={toggleAll} className="cursor-pointer" />
              <span>Select all {logs.length} entries</span>
            </div>
          )}
          {logs.map((l) => (
            <div
              key={l.id}
              className={`flex justify-between px-4 py-3 border-b border-slate-800 last:border-0 text-sm ${
                selected.has(l.id) ? "bg-slate-800/60" : ""
              }`}
            >
              <div className="flex items-center gap-3">
                <input type="checkbox" checked={selected.has(l.id)} onChange={() => toggle(l.id)} className="cursor-pointer" />
                <span className={`text-xs px-2 py-0.5 rounded ${ACTION_COLORS[l.action] || "bg-slate-800 text-slate-300"}`}>
                  {l.action}
                </span>
                {l.resource_type && (
                  <span className="text-slate-500 text-xs">
                    {l.resource_type}
                    {l.resource_id ? ` · ${l.resource_id.slice(0, 8)}` : ""}
                  </span>
                )}
              </div>
              <span className="text-slate-500 text-xs">
                {new Date(l.created_at).toLocaleString()}
              </span>
            </div>
          ))}
          {logs.length === 0 && (
            <div className="p-6 text-slate-500 text-center">No activity yet.</div>
          )}
        </div>
      </main>
    </div>
  );
}
