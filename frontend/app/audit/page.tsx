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
  const [resetting, setResetting] = useState(false);
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
    if (!confirm(`Delete ${selected.size} audit entr${selected.size > 1 ? "ies" : "y"}? Cannot be undone.`)) return;
    setBulkBusy(true);
    try {
      await apiFetch("/audit/bulk-delete", {
        method: "POST",
        body: JSON.stringify({ ids: Array.from(selected) }),
      });
      setSelected(new Set());
    } catch (e: any) {
      // Still refresh — delete may have succeeded
      setError(e.message);
    } finally {
      await load();
      setBulkBusy(false);
    }
  }

  async function resetLog() {
    if (!confirm("Clear the entire audit log? A single entry recording this action will remain.")) return;
    setResetting(true);
    setError(null);
    try {
      await apiFetch("/audit/", { method: "DELETE" });
      setSelected(new Set());
    } catch (e: any) {
      setError(e.message);
    } finally {
      await load();
      setResetting(false);
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
              onClick={resetLog}
              disabled={resetting || logs.length === 0}
              className="bg-red-950 hover:bg-red-900 border border-red-900 disabled:opacity-50 px-4 py-2 rounded text-sm font-medium text-red-300"
            >
              {resetting ? "Clearing..." : "Reset Audit Log"}
            </button>
          </div>
        </div>

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
