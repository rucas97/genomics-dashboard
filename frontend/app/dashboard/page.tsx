"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import Sidebar from "@/components/Sidebar";
import { apiFetch } from "@/lib/api";

export default function Dashboard() {
  const [samples, setSamples] = useState<any[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiFetch("/samples/").then(setSamples).catch((e) => setError(e.message));
  }, []);

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

        {samples.length === 0 ? (
          <div className="bg-slate-900 rounded-lg border border-slate-800 p-16 text-center">
            <img
              src="/logo-sidebar.png"
              alt="GenomicsOps"
              className="max-w-[240px] h-auto mx-auto mb-6 opacity-90"
            />
            <h2 className="text-lg font-semibold mb-2">Welcome to GenomicsOps</h2>
            <p className="text-slate-400 text-sm mb-6 max-w-md mx-auto">
              Upload your first VCF to get started. We&apos;ll parse variants,
              compute QC metrics, and classify them with transparent ACMG logic.
            </p>
            <Link
              href="/samples"
              className="inline-block bg-emerald-600 hover:bg-emerald-500 px-6 py-3 rounded font-medium"
            >
              Upload a Sample
            </Link>
          </div>
        ) : (
          <>
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
                <Link
                  key={s.id}
                  href={`/samples/${s.id}`}
                  className="flex justify-between px-4 py-3 border-b border-slate-800 last:border-0 hover:bg-slate-800/40"
                >
                  <span>{s.name}</span>
                  <span className={`text-xs px-2 py-1 rounded ${
                    s.status === "ready" ? "bg-emerald-900 text-emerald-300" :
                    s.status === "processing" ? "bg-amber-900 text-amber-300" :
                    s.status === "failed" ? "bg-red-900 text-red-300" : "bg-slate-800"
                  }`}>{s.status}</span>
                </Link>
              ))}
            </div>
          </>
        )}
      </main>
    </div>
  );
}
