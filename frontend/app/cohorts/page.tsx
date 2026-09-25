"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import Sidebar from "@/components/Sidebar";
import { apiFetch } from "@/lib/api";

export default function Cohorts() {
  const [cohorts, setCohorts] = useState<any[]>([]);
  const [samples, setSamples] = useState<any[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [showCreate, setShowCreate] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [sampleSel, setSampleSel] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    try {
      const [c, s] = await Promise.all([
        apiFetch("/cohorts/"),
        apiFetch("/samples/"),
      ]);
      setCohorts(c);
      setSamples(s);
      setError(null);
    } catch (e: any) {
      setError(e.message);
    }
  }

  useEffect(() => { load(); }, []);

  function toggleSample(id: string) {
    setSampleSel((prev) => prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]);
  }

  function toggleCohort(id: string) {
    const next = new Set(selected);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    setSelected(next);
  }

  function toggleAll() {
    if (selected.size === cohorts.length) setSelected(new Set());
    else setSelected(new Set(cohorts.map((c) => c.id)));
  }

  async function create() {
    if (!name.trim() || sampleSel.length < 2) return;
    setBusy(true); setError(null);
    try {
      await apiFetch("/cohorts/", {
        method: "POST",
        body: JSON.stringify({
          name: name.trim(),
          description: description.trim() || null,
          sample_ids: sampleSel,
        }),
      });
      setName(""); setDescription(""); setSampleSel([]); setShowCreate(false);
    } catch (e: any) {
      setError(e.message);
    } finally {
      await load();
      setBusy(false);
    }
  }

  async function bulkDelete() {
    if (selected.size === 0) return;
    if (!confirm(`Delete ${selected.size} cohort${selected.size > 1 ? "s" : ""}? Cannot be undone.`)) return;
    try {
      await apiFetch("/cohorts/bulk-delete", {
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

  async function deleteCohort(cohort: any) {
    if (!confirm(`Delete cohort "${cohort.name}"? Cannot be undone.`)) return;
    try {
      await apiFetch(`/cohorts/${cohort.id}`, { method: "DELETE" });
    } catch (e: any) {
      setError(e.message);
    } finally {
      await load();
    }
  }

  const readySamples = samples.filter((s) => s.status === "ready");
  const allSelected = cohorts.length > 0 && selected.size === cohorts.length;

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 p-8">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold">Cohorts</h1>
          <div className="flex gap-2">
            {selected.size > 0 && (
              <button
                onClick={bulkDelete}
                className="bg-red-950 hover:bg-red-900 border border-red-900 px-4 py-2 rounded text-sm font-medium text-red-300"
              >
                Delete {selected.size} selected
              </button>
            )}
            <button
              onClick={() => setShowCreate((v) => !v)}
              className="bg-emerald-600 hover:bg-emerald-500 px-4 py-2 rounded text-sm font-medium"
            >
              {showCreate ? "Cancel" : "New Cohort"}
            </button>
          </div>
        </div>

        {error && <p className="text-red-400 mb-4 text-sm">{error}</p>}

        {showCreate && (
          <div className="bg-slate-900 border border-slate-800 rounded-lg p-6 mb-6">
            <h2 className="text-lg font-semibold mb-4">Create Cohort</h2>
            <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Cohort name"
              className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 mb-3 text-sm" />
            <textarea value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Description (optional)"
              rows={2} className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 mb-4 text-sm" />
            <div className="text-slate-400 text-sm mb-2">Select samples (need at least 2):</div>
            <div className="space-y-1 mb-4 max-h-60 overflow-y-auto border border-slate-800 rounded p-2">
              {readySamples.map((s) => (
                <label key={s.id} className="flex items-center gap-2 px-2 py-1 hover:bg-slate-800 rounded cursor-pointer text-sm">
                  <input type="checkbox" checked={sampleSel.includes(s.id)} onChange={() => toggleSample(s.id)} />
                  <span>{s.name}</span>
                </label>
              ))}
            </div>
            <button onClick={create} disabled={busy || !name.trim() || sampleSel.length < 2}
              className="bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 px-4 py-2 rounded text-sm font-medium">
              {busy ? "Creating..." : `Create (${sampleSel.length} samples)`}
            </button>
          </div>
        )}

        <div className="bg-slate-900 rounded-lg border border-slate-800 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-800 text-slate-400 text-left">
              <tr>
                <th className="p-3 w-10">
                  <input type="checkbox" checked={allSelected} onChange={toggleAll} className="cursor-pointer" />
                </th>
                <th className="p-3">Name</th>
                <th className="p-3">Samples</th>
                <th className="p-3">Created</th>
                <th className="p-3"></th>
              </tr>
            </thead>
            <tbody>
              {cohorts.map((c) => (
                <tr key={c.id} className={`border-t border-slate-800 ${selected.has(c.id) ? "bg-slate-800/60" : ""}`}>
                  <td className="p-3">
                    <input type="checkbox" checked={selected.has(c.id)} onChange={() => toggleCohort(c.id)} className="cursor-pointer" />
                  </td>
                  <td className="p-3">
                    <Link href={`/cohorts/${c.id}`} className="text-emerald-400 hover:underline">{c.name}</Link>
                  </td>
                  <td className="p-3">{(c.sample_ids || []).length}</td>
                  <td className="p-3 text-slate-500 text-xs">{new Date(c.created_at).toLocaleString()}</td>
                  <td className="p-3">
                    <div className="flex items-center justify-end gap-3">
                      <Link href={`/cohorts/${c.id}`} className="text-emerald-400 text-xs hover:underline">Open →</Link>
                      <button onClick={() => deleteCohort(c)} className="text-red-400 hover:underline text-xs">Delete</button>
                    </div>
                  </td>
                </tr>
              ))}
              {cohorts.length === 0 && (
                <tr><td colSpan={5} className="p-6 text-slate-500 text-center">No cohorts yet.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </main>
    </div>
  );
}
