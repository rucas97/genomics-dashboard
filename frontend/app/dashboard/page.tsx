"use client";
import { useEffect, useState } from "react";
import Sidebar from "@/components/Sidebar";
import { apiFetch } from "@/lib/api";

export default function Dashboard() {
  const [samples, setSamples] = useState<any[]>([]);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { apiFetch("/samples/").then(setSamples).catch((e) => setError(e.message)); }, []);
  const stats = [
    { label: "Total Samples", value: samples.length },
    { label: "Ready", value: samples.filter((s) => s.status === "ready").length },
    { label: "Processing", value: samples.filter((s) => s.status === "processing").length },
    { label: "Failed", value: samples.filter((s) => s.status === "failed").length },
  ];
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 p-8">
        <h1 className="text-2xl font-bold mb-6">Dashboard</h1>
        {error && <p className="text-red-400 mb-4">{error}</p>}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          {stats.map(({ label, value }) => (
            <div key={label} className="bg-slate-900 rounded-lg p-4 border border-slate-800">
              <div className="text-slate-400 text-sm">{label}</div>
              <div className="text-3xl font-bold text-emerald-400 mt-1">{value}</div>
            </div>
          ))}
        </div>
        <h2 className="text-lg font-semibold mb-3">Recent Samples</h2>
        <div className="bg-slate-900 rounded-lg border border-slate-800">
          {samples.slice(0, 10).map((s) => (
            <div key={s.id} className="flex justify-between px-4 py-3 border-b border-slate-800 last:border-0">
              <span>{s.name}</span>
              <span className={`text-xs px-2 py-1 rounded ${
                s.status === "ready" ? "bg-emerald-900 text-emerald-300" :
                s.status === "processing" ? "bg-amber-900 text-amber-300" :
                s.status === "failed" ? "bg-red-900 text-red-300" : "bg-slate-800"
              }`}>{s.status}</span>
            </div>
          ))}
          {samples.length === 0 && <div className="p-6 text-slate-500 text-sm">No samples yet. Upload one to begin.</div>}
        </div>
      </main>
    </div>
  );
}
