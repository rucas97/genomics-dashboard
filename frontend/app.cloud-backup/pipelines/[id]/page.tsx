"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import Sidebar from "@/components/Sidebar";
import { apiFetch } from "@/lib/api";

export default function RunDetail() {
  const params = useParams();
  const id = params.id as string;
  const [run, setRun] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    function load() {
      apiFetch(`/pipelines/${id}`).then(setRun).catch((e) => setError(e.message));
    }
    load();
    const t = setInterval(load, 2000);
    return () => clearInterval(t);
  }, [id]);

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 p-8">
        <Link href="/pipelines" className="text-emerald-400 text-sm hover:underline">
          ← Back to Pipelines
        </Link>

        {error && <p className="text-red-400 mt-4">{error}</p>}
        {!run && !error && <p className="text-slate-500 mt-4">Loading...</p>}

        {run && (
          <>
            <div className="flex items-center justify-between mt-3 mb-6">
              <h1 className="text-2xl font-bold">{run.pipeline_name}</h1>
              <span className={`text-xs px-3 py-1 rounded ${
                run.status === "completed" ? "bg-emerald-900 text-emerald-300" :
                run.status === "running" ? "bg-blue-900 text-blue-300 animate-pulse" :
                run.status === "failed" ? "bg-red-900 text-red-300" :
                "bg-slate-800 text-slate-300"
              }`}>{run.status}</span>
            </div>

            <div className="bg-slate-900 rounded-lg border border-slate-800 p-6 mb-6">
              <dl className="grid grid-cols-2 gap-3 text-sm">
                <dt className="text-slate-400">Sample</dt>
                <dd className="font-mono text-xs">{run.sample_id?.slice(0, 8)}...</dd>
                <dt className="text-slate-400">Started</dt>
                <dd>{run.started_at ? new Date(run.started_at).toLocaleString() : "—"}</dd>
                <dt className="text-slate-400">Finished</dt>
                <dd>{run.finished_at ? new Date(run.finished_at).toLocaleString() : "—"}</dd>
              </dl>
            </div>

            <h2 className="text-lg font-semibold mb-3">Logs</h2>
            <div className="bg-slate-950 rounded-lg border border-slate-800 p-4 font-mono text-xs text-slate-300 whitespace-pre-wrap max-h-[500px] overflow-y-auto">
              {run.logs || "(no output yet)"}
            </div>
          </>
        )}
      </main>
    </div>
  );
}
