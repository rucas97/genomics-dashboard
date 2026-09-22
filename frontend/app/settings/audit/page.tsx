"use client";
import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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
};

export default function AuditPage() {
  const [rows, setRows] = useState<any[]>([]);
  const [filter, setFilter] = useState("");
  const [actionFilter, setActionFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiFetch("/audit/?limit=500")
      .then(setRows)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  async function exportCsv() {
    const { supabase } = await import("@/lib/supabase");
    const { data: { session } } = await supabase.auth.getSession();
    const token = session?.access_token;
    const res = await fetch(`${API_URL}/compliance/audit/export?format=csv`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) {
      alert("Export failed: " + (await res.text()));
      return;
    }
    const blob = await res.blob();
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = "audit_log.csv";
    link.click();
  }

  const filtered = rows.filter((r) => {
    if (actionFilter && r.action !== actionFilter) return false;
    if (filter) {
      const needle = filter.toLowerCase();
      return (
        (r.action || "").toLowerCase().includes(needle) ||
        (r.resource_type || "").toLowerCase().includes(needle) ||
        (r.resource_id || "").toLowerCase().includes(needle)
      );
    }
    return true;
  });

  const actions = Array.from(new Set(rows.map((r) => r.action))).sort();

  return (
    <div className="max-w-6xl space-y-4">
      <div className="flex gap-2 items-center justify-between">
        <div className="flex gap-2 flex-1">
          <input
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            placeholder="Search by action, resource, ID..."
            className="flex-1 bg-slate-950 border border-slate-800 rounded px-3 py-2 text-sm"
          />
          <select
            value={actionFilter}
            onChange={(e) => setActionFilter(e.target.value)}
            className="bg-slate-950 border border-slate-800 rounded px-3 py-2 text-sm"
          >
            <option value="">All actions</option>
            {actions.map((a) => (
              <option key={a} value={a}>
                {a}
              </option>
            ))}
          </select>
        </div>
        <button
          onClick={exportCsv}
          className="bg-emerald-600 hover:bg-emerald-500 px-4 py-2 rounded text-sm font-medium"
        >
          Export CSV
        </button>
      </div>

      {error && (
        <div className="bg-red-950 border border-red-900 text-red-300 rounded p-3 text-sm">
          {error}
        </div>
      )}

      <div className="bg-slate-900 rounded-lg border border-slate-800 overflow-hidden">
        {loading ? (
          <div className="p-6 text-slate-500">Loading...</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-slate-800 text-slate-400 text-left">
              <tr>
                <th className="p-3">When</th>
                <th className="p-3">Action</th>
                <th className="p-3">Resource</th>
                <th className="p-3">Details</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((r) => (
                <tr key={r.id} className="border-t border-slate-800">
                  <td className="p-3 text-slate-500 text-xs whitespace-nowrap">
                    {new Date(r.created_at).toLocaleString()}
                  </td>
                  <td className="p-3">
                    <span
                      className={`text-xs px-2 py-1 rounded ${
                        ACTION_COLORS[r.action] || "bg-slate-800 text-slate-300"
                      }`}
                    >
                      {r.action}
                    </span>
                  </td>
                  <td className="p-3 text-xs">
                    <div className="text-slate-300">{r.resource_type || "—"}</div>
                    <div className="text-slate-600 font-mono">
                      {r.resource_id ? r.resource_id.slice(0, 8) : ""}
                    </div>
                  </td>
                  <td className="p-3 text-xs text-slate-400 max-w-md truncate">
                    {r.details ? JSON.stringify(r.details) : "—"}
                  </td>
                </tr>
              ))}
              {filtered.length === 0 && (
                <tr>
                  <td colSpan={4} className="p-6 text-slate-500 text-center">
                    No audit entries.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        )}
      </div>

      <p className="text-xs text-slate-500">
        {filtered.length} of {rows.length} entries shown. Audit log is immutable and
        append-only.
      </p>
    </div>
  );
}
