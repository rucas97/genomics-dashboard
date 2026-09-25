"use client";
import { useEffect, useState, useRef } from "react";
import Link from "next/link";
import Sidebar from "@/components/Sidebar";
import { apiFetch } from "@/lib/api";

export default function Samples() {
  const [samples, setSamples] = useState<any[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState({ current: 0, total: 0 });
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  async function load() {
    try {
      const data = await apiFetch("/samples/");
      setSamples(data);
      setError(null);
    } catch (e: any) {
      setError(e.message);
    }
  }

  useEffect(() => {
    load();
    const t = setInterval(load, 5000);
    return () => clearInterval(t);
  }, []);

  async function uploadFiles(files: FileList) {
    setUploading(true);
    setError(null);
    const list = Array.from(files);
    setUploadProgress({ current: 0, total: list.length });

    for (let i = 0; i < list.length; i++) {
      const file = list[i];
      setUploadProgress({ current: i + 1, total: list.length });
      try {
        const form = new FormData();
        form.append("file", file);
        await apiFetch("/samples/upload", { method: "POST", body: form });
      } catch (e: any) {
        setError(`Failed to upload ${file.name}: ${e.message}`);
      }
    }

    setUploading(false);
    setUploadProgress({ current: 0, total: 0 });
    setTimeout(load, 500);
  }

  function toggle(id: string) {
    const next = new Set(selected);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    setSelected(next);
  }

  function toggleAll() {
    if (selected.size === samples.length) setSelected(new Set());
    else setSelected(new Set(samples.map((s) => s.id)));
  }

  async function bulkDelete() {
    if (selected.size === 0) return;
    if (!confirm(
      `Delete ${selected.size} sample${selected.size > 1 ? "s" : ""}?\n\n` +
      `This removes the samples AND all their variants, QC data, and reports. ` +
      `This cannot be undone.`
    )) return;
    try {
      await apiFetch("/samples/bulk-delete", {
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

  async function deleteSample(s: any) {
    if (!confirm(`Delete "${s.name}"? This removes the sample, its variants, QC data, and reports. Cannot be undone.`)) return;
    try {
      await apiFetch(`/samples/${s.id}`, { method: "DELETE" });
    } catch (e: any) {
      setError(e.message);
    } finally {
      await load();
    }
  }

  const allSelected = samples.length > 0 && selected.size === samples.length;

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 p-8">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-2xl font-bold">Samples</h1>
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
              onClick={() => inputRef.current?.click()}
              disabled={uploading}
              className="bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 px-4 py-2 rounded text-sm font-medium"
            >
              {uploading
                ? `Uploading ${uploadProgress.current}/${uploadProgress.total}...`
                : "Upload Samples"}
            </button>
            <input
              ref={inputRef}
              type="file"
              hidden
              multiple
              accept=".vcf,.fastq,.fq,.bam,.csv,.gz"
              onChange={(e) => {
                if (e.target.files && e.target.files.length > 0) {
                  uploadFiles(e.target.files);
                  e.target.value = "";
                }
              }}
            />
          </div>
        </div>

        {error && <p className="text-red-400 mb-4 text-sm">{error}</p>}

        <div className="bg-slate-900 rounded-lg border border-slate-800 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-800 text-slate-400 text-left">
              <tr>
                <th className="p-3 w-10">
                  <input type="checkbox" checked={allSelected} onChange={toggleAll} className="cursor-pointer" />
                </th>
                <th className="p-3">Name</th>
                <th className="p-3">Type</th>
                <th className="p-3">Size</th>
                <th className="p-3">Status</th>
                <th className="p-3">Created</th>
                <th className="p-3"></th>
              </tr>
            </thead>
            <tbody>
              {samples.map((s) => (
                <tr key={s.id} className={`border-t border-slate-800 ${selected.has(s.id) ? "bg-slate-800/60" : "hover:bg-slate-800/40"}`}>
                  <td className="p-3">
                    <input type="checkbox" checked={selected.has(s.id)} onChange={() => toggle(s.id)} className="cursor-pointer" />
                  </td>
                  <td className="p-3">
                    <Link href={`/samples/${s.id}`} className="text-emerald-400 hover:underline">{s.name}</Link>
                  </td>
                  <td className="p-3">{s.file_type}</td>
                  <td className="p-3">
                    {s.file_size_bytes ? `${(s.file_size_bytes / 1024).toFixed(1)} KB` : "-"}
                  </td>
                  <td className="p-3">
                    <span className={`text-xs px-2 py-0.5 rounded ${
                      s.status === "ready" ? "bg-emerald-900 text-emerald-300" :
                      s.status === "processing" ? "bg-amber-900 text-amber-300" :
                      s.status === "failed" ? "bg-red-900 text-red-300" :
                      "bg-slate-800 text-slate-300"
                    }`}>{s.status}</span>
                  </td>
                  <td className="p-3 text-slate-500 text-xs">
                    {new Date(s.created_at).toLocaleString()}
                  </td>
                  <td className="p-3 text-right">
                    <button onClick={() => deleteSample(s)} className="text-xs text-red-400 hover:underline">Delete</button>
                  </td>
                </tr>
              ))}
              {samples.length === 0 && (
                <tr><td colSpan={7} className="p-6 text-slate-500 text-center">No samples yet.</td></tr>
              )}
            </tbody>
          </table>
        </div>

        <p className="text-xs text-slate-500 mt-3">
          {samples.length} sample{samples.length !== 1 ? "s" : ""} · Select multiple files to upload at once
        </p>
      </main>
    </div>
  );
}
