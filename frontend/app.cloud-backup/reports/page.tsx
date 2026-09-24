"use client";
import { useEffect, useState } from "react";
import Sidebar from "@/components/Sidebar";
import { apiFetch } from "@/lib/api";

export default function Reports() {
  const [reports, setReports] = useState<any[]>([]);
  const [loading, setLoading] = useState<string | null>(null);

  function load() {
    apiFetch("/reports/").then(setReports).catch(console.error);
  }

  useEffect(() => { load(); }, []);

  async function download(report: any) {
    setLoading(report.id);
    try {
      const res = await apiFetch(`/reports/${report.id}/download`);
      window.open(res.url, "_blank");
    } catch (e: any) {
      alert(e.message);
    } finally {
      setLoading(null);
    }
  }

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 p-8">
        <h1 className="text-2xl font-bold mb-6">Reports</h1>

        <div className="bg-slate-900 rounded-lg border border-slate-800 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-800 text-slate-400 text-left">
              <tr>
                <th className="p-3">Title</th>
                <th className="p-3">Type</th>
                <th className="p-3">Created</th>
                <th className="p-3"></th>
              </tr>
            </thead>
            <tbody>
              {reports.map((r) => (
                <tr key={r.id} className="border-t border-slate-800">
                  <td className="p-3">{r.title}</td>
                  <td className="p-3">
                    <span className="text-xs px-2 py-1 rounded bg-slate-800 text-slate-300">
                      {r.type}
                    </span>
                  </td>
                  <td className="p-3 text-slate-500">
                    {new Date(r.created_at).toLocaleString()}
                  </td>
                  <td className="p-3">
                    <button
                      onClick={() => download(r)}
                      disabled={loading === r.id}
                      className="text-emerald-400 hover:underline text-xs disabled:opacity-50"
                    >
                      {loading === r.id ? "Preparing..." : "Download PDF"}
                    </button>
                  </td>
                </tr>
              ))}
              {reports.length === 0 && (
                <tr>
                  <td colSpan={4} className="p-6 text-slate-500 text-center">
                    No reports yet. Generate one from a sample or cohort page.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </main>
    </div>
  );
}
