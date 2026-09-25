"use client";
import { useEffect, useState } from "react";
import Sidebar from "@/components/Sidebar";
import { apiFetch } from "@/lib/api";
import { isLocal, getLocalToken } from "@/lib/mode";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function Reports() {
  const [reports, setReports] = useState<any[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    try {
      const data = await apiFetch("/reports/");
      setReports(data);
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
    if (selected.size === reports.length) setSelected(new Set());
    else setSelected(new Set(reports.map((r) => r.id)));
  }

  async function bulkDelete() {
    if (selected.size === 0) return;
    if (!confirm(`Delete ${selected.size} report${selected.size > 1 ? "s" : ""}? The PDF files will be removed permanently.`)) return;
    try {
      await apiFetch("/reports/bulk-delete", {
        method: "POST",
        body: JSON.stringify({ ids: Array.from(selected) }),
      });
      setSelected(new Set());
    } catch (e: any) {
      setError(e.message);
    } finally {
      await load();
    }
  }

  async function download(report: any) {
    setLoading(report.id);
    try {
      const headers: Record<string, string> = {};
      if (isLocal) {
        const token = getLocalToken();
        if (token) headers.Authorization = `Bearer ${token}`;
      } else {
        const { supabase } = await import("@/lib/supabase");
        const { data: { session } } = await supabase.auth.getSession();
        if (session?.access_token) headers.Authorization = `Bearer ${session.access_token}`;
      }
      const res = await fetch(`${API_URL}/reports/${report.id}/download`, { headers });
      if (!res.ok) { alert(`Download failed: ${await res.text()}`); return; }
      const ct = res.headers.get("content-type") || "";
      if (ct.includes("application/pdf")) {
        const blob = await res.blob();
        const link = document.createElement("a");
        link.href = URL.createObjectURL(blob);
        link.download = `${report.title}.pdf`;
        link.click();
        URL.revokeObjectURL(link.href);
      } else {
        const data = await res.json();
        if (data.url) window.open(data.url, "_blank");
      }
    } catch (e: any) {
      alert(e.message);
    } finally {
      setLoading(null);
    }
  }

  async function deleteReport(report: any) {
    if (!confirm(`Delete "${report.title}"? The PDF will be removed permanently.`)) return;
    setDeleting(report.id);
    try {
      await apiFetch(`/reports/${report.id}`, { method: "DELETE" });
    } catch (e: any) {
      setError(e.message);
    } finally {
      await load();
      setDeleting(null);
    }
  }

  const allSelected = reports.length > 0 && selected.size === reports.length;

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 p-8">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold">Reports</h1>
          {selected.size > 0 && (
            <button
              onClick={bulkDelete}
              className="bg-red-950 hover:bg-red-900 border border-red-900 px-4 py-2 rounded text-sm font-medium text-red-300"
            >
              Delete {selected.size} selected
            </button>
          )}
        </div>

        {error && <p className="text-red-400 mb-4 text-sm">{error}</p>}

        <div className="bg-slate-900 rounded-lg border border-slate-800 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-800 text-slate-400 text-left">
              <tr>
                <th className="p-3 w-10">
                  <input type="checkbox" checked={allSelected} onChange={toggleAll} className="cursor-pointer" />
                </th>
                <th className="p-3">Title</th>
                <th className="p-3">Type</th>
                <th className="p-3">Created</th>
                <th className="p-3"></th>
              </tr>
            </thead>
            <tbody>
              {reports.map((r) => (
                <tr key={r.id} className={`border-t border-slate-800 ${selected.has(r.id) ? "bg-slate-800/60" : "hover:bg-slate-800/40"}`}>
                  <td className="p-3">
                    <input type="checkbox" checked={selected.has(r.id)} onChange={() => toggle(r.id)} className="cursor-pointer" />
                  </td>
                  <td className="p-3">{r.title}</td>
                  <td className="p-3">
                    <span className="text-xs px-2 py-1 rounded bg-slate-800 text-slate-300">{r.type}</span>
                  </td>
                  <td className="p-3 text-slate-500 text-xs">{new Date(r.created_at).toLocaleString()}</td>
                  <td className="p-3">
                    <div className="flex items-center justify-end gap-3">
                      <button onClick={() => download(r)} disabled={loading === r.id}
                        className="text-emerald-400 hover:underline text-xs disabled:opacity-50">
                        {loading === r.id ? "Preparing..." : "Download"}
                      </button>
                      <button onClick={() => deleteReport(r)} disabled={deleting === r.id}
                        className="text-red-400 hover:underline text-xs disabled:opacity-50">
                        {deleting === r.id ? "Deleting..." : "Delete"}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {reports.length === 0 && (
                <tr><td colSpan={5} className="p-6 text-slate-500 text-center">No reports yet.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </main>
    </div>
  );
}
