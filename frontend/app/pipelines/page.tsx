"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import Sidebar from "@/components/Sidebar";
import { apiFetch } from "@/lib/api";

export default function Pipelines() {
  const [runs, setRuns] = useState<any[]>([]);
  const [available, setAvailable] = useState<any[]>([]);
  const [samples, setSamples] = useState<any[]>([]);
  const [showCreate, setShowCreate] = useState(false);
  const [pipelineId, setPipelineId] = useState("");
  const [sampleId, setSampleId] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function load() {
    apiFetch("/pipelines/").then(setRuns).catch((e) => setError(e.message));
    apiFetch("/pipelines/available").then(setAvailable).catch(() => {});
    apiFetch("/samples/").then(setSamples).catch(() => {});
  }

  useEffect(() => {
    load();
    const t = setInterval(load, 4000);
    return () => clearInterval(t);
  }, []);

  async function start() {
    if (!pipelineId || !sampleId) return;
    setBusy(true);
    setError(null);
    try {
      await apiFetch("/pipelines/run", {
        method: "POST",
        body: JSON.stringify({ pipeline_id: pipelineId, sample_id: sampleId }),
      });
      setPipelineId("");
      setSampleId("");
      setShowCreate(false);
      setTimeout(load, 500);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  const readySamples = samples.filter((s) => s.status === "ready");

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 p-8">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold">Pipeline Runs</h1>
          <button
            onClick={() => setShowCreate((v) => !v)}
            className="bg-emerald-600 hover:bg-emerald-500 px-4 py-2 rounded text-sm font-medium"
          >
            {showCreate ? "Cancel" : "New Run"}
          </button>
        </div>

        {error && <p className="text-red-400 mb-4 text-sm">{error}</p>}

        {showCreate && (
          <div className="bg-slate-900 border border-slate-800 rounded-lg p-6 mb-6">
            <h2 className="text-lg font-semibold mb-4">Start a Pipeline</h2>

            <div className="text-slate-400 text-sm mb-2">Pipeline</div>
            <div className="space-y-2 mb-4">
              {available.map((p) => (
                <label
                  key={p.id}
                  className={`flex items-start gap-3 px-3 py-2 rounded border cursor-pointer ${
                    pipelineId === p.id
                      ? "border-emerald-500 bg-emerald-950"
                      : "border-slate-800 hover:border-slate-600"
                  }`}
                >
                  <input
                    type="radio"
                    checked={pipelineId === p.id}
                    onChange={() => setPipelineId(p.id)}
                    className="mt-1"
                  />
                  <div>
                    <div className="text-sm font-medium">{p.name}</div>
                    <div className="text-slate-500 text-xs">{p.description}</div>
                  </div>
                </label>
              ))}
            </div>

            <div className="text-slate-400 text-sm mb-2">Sample</div>
            <select
              value={sampleId}
              onChange={(e) => setSampleId(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-sm mb-4"
            >
              <option value="">Select a sample...</option>
              {readySamples.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>

            <button
              onClick={start}
              disabled={busy || !pipelineId || !sampleId}
              className="bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 px-4 py-2 rounded text-sm font-medium"
            >
              {busy ? "Starting..." : "Start Run"}
            </button>
          </div>
        )}

        <div className="bg-slate-900 rounded-lg border border-slate-800 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-800 text-slate-400 text-left">
              <tr>
                <th className="p-3">Pipeline</th>
                <th className="p-3">Status</th>
                <th className="p-3">Started</th>
                <th className="p-3">Finished</th>
                <th className="p-3"></th>
              </tr>
            </thead>
            <tbody>
              {runs.map((r) => (
                <tr key={r.id} className="border-t border-slate-800">
                  <td className="p-3">{r.pipeline_name}</td>
                  <td className="p-3">
                    <span className={`text-xs px-2 py-1 rounded ${
                      r.status === "completed" ? "bg-emerald-900 text-emerald-300" :
                      r.status === "running" ? "bg-blue-900 text-blue-300" :
                      r.status === "failed" ? "bg-red-900 text-red-300" :
                      "bg-slate-800 text-slate-300"
                    }`}>{r.status}</span>
                  </td>
                  <td className="p-3 text-slate-500 text-xs">
                    {r.started_at ? new Date(r.started_at).toLocaleTimeString() : "—"}
                  </td>
                  <td className="p-3 text-slate-500 text-xs">
                    {r.finished_at ? new Date(r.finished_at).toLocaleTimeString() : "—"}
                  </td>
                  <td className="p-3">
                    <Link href={`/pipelines/${r.id}`} className="text-emerald-400 hover:underline text-xs">
                      View →
                    </Link>
                  </td>
                </tr>
              ))}
              {runs.length === 0 && (
                <tr>
                  <td colSpan={5} className="p-6 text-slate-500 text-center">
                    No runs yet. Start one.
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
