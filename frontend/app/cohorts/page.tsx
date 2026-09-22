"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import Sidebar from "@/components/Sidebar";
import { apiFetch } from "@/lib/api";

export default function Cohorts() {
  const [cohorts, setCohorts] = useState<any[]>([]);
  const [samples, setSamples] = useState<any[]>([]);
  const [showCreate, setShowCreate] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [selected, setSelected] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function load() {
    apiFetch("/cohorts/").then(setCohorts).catch((e) => setError(e.message));
    apiFetch("/samples/").then(setSamples).catch(() => {});
  }

  useEffect(() => { load(); }, []);

  function toggle(id: string) {
    setSelected((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  }

  async function create() {
    if (!name.trim() || selected.length < 2) return;
    setBusy(true);
    setError(null);
    try {
      await apiFetch("/cohorts/", {
        method: "POST",
        body: JSON.stringify({
          name: name.trim(),
          description: description.trim() || null,
          sample_ids: selected,
        }),
      });
      setName("");
      setDescription("");
      setSelected([]);
      setShowCreate(false);
      load();
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
          <h1 className="text-2xl font-bold">Cohorts</h1>
          <button
            onClick={() => setShowCreate((v) => !v)}
            className="bg-emerald-600 hover:bg-emerald-500 px-4 py-2 rounded text-sm font-medium"
          >
            {showCreate ? "Cancel" : "New Cohort"}
          </button>
        </div>

        {error && <p className="text-red-400 mb-4 text-sm">{error}</p>}

        {showCreate && (
          <div className="bg-slate-900 border border-slate-800 rounded-lg p-6 mb-6">
            <h2 className="text-lg font-semibold mb-4">Create Cohort</h2>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Cohort name (e.g. Cancer Panel A)"
              className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 mb-3 text-sm"
            />
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Description (optional)"
              rows={2}
              className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 mb-4 text-sm"
            />

            <div className="text-slate-400 text-sm mb-2">
              Select samples (need at least 2):
            </div>
            <div className="space-y-1 mb-4 max-h-60 overflow-y-auto border border-slate-800 rounded p-2">
              {readySamples.map((s) => (
                <label
                  key={s.id}
                  className="flex items-center gap-2 px-2 py-1 hover:bg-slate-800 rounded cursor-pointer text-sm"
                >
                  <input
                    type="checkbox"
                    checked={selected.includes(s.id)}
                    onChange={() => toggle(s.id)}
                  />
                  <span>{s.name}</span>
                  <span className="text-slate-500 text-xs ml-auto">
                    {s.file_type}
                  </span>
                </label>
              ))}
              {readySamples.length === 0 && (
                <div className="text-slate-500 text-sm p-2">
                  No ready samples. Upload a VCF first.
                </div>
              )}
            </div>

            <div className="flex items-center gap-3">
              <button
                onClick={create}
                disabled={busy || !name.trim() || selected.length < 2}
                className="bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 px-4 py-2 rounded text-sm font-medium"
              >
                {busy ? "Creating..." : `Create (${selected.length} samples)`}
              </button>
              <span className="text-slate-500 text-xs">
                Need 2+ samples to compute PCA
              </span>
            </div>
          </div>
        )}

        <div className="bg-slate-900 rounded-lg border border-slate-800 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-800 text-slate-400 text-left">
              <tr>
                <th className="p-3">Name</th>
                <th className="p-3">Samples</th>
                <th className="p-3">Created</th>
                <th className="p-3"></th>
              </tr>
            </thead>
            <tbody>
              {cohorts.map((c) => (
                <tr key={c.id} className="border-t border-slate-800">
                  <td className="p-3">
                    <Link
                      href={`/cohorts/${c.id}`}
                      className="text-emerald-400 hover:underline"
                    >
                      {c.name}
                    </Link>
                    {c.description && (
                      <div className="text-slate-500 text-xs mt-1">
                        {c.description}
                      </div>
                    )}
                  </td>
                  <td className="p-3">{(c.sample_ids || []).length}</td>
                  <td className="p-3 text-slate-500">
                    {new Date(c.created_at).toLocaleString()}
                  </td>
                  <td className="p-3">
                    <Link
                      href={`/cohorts/${c.id}`}
                      className="text-emerald-400 text-xs hover:underline"
                    >
                      Open →
                    </Link>
                  </td>
                </tr>
              ))}
              {cohorts.length === 0 && (
                <tr>
                  <td colSpan={4} className="p-6 text-slate-500 text-center">
                    No cohorts yet. Create one to run PCA.
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
