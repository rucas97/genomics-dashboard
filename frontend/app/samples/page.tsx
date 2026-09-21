"use client";
import { useEffect, useState, useRef } from "react";
import Sidebar from "@/components/Sidebar";
import { apiFetch } from "@/lib/api";

export default function Samples() {
  const [samples, setSamples] = useState<any[]>([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const load = () => apiFetch("/samples/").then(setSamples).catch((e) => setError(e.message));
  useEffect(() => { load(); const t = setInterval(load, 5000); return () => clearInterval(t); }, []);
  async function upload(file: File) {
    setUploading(true); setError(null);
    const form = new FormData(); form.append("file", file);
    try { await apiFetch("/samples/upload", { method: "POST", body: form }); setTimeout(load, 1500); }
    catch (e: any) { setError(e.message); }
    finally { setUploading(false); }
  }
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 p-8">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-2xl font-bold">Samples</h1>
          <button onClick={() => inputRef.current?.click()} disabled={uploading}
            className="bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 px-4 py-2 rounded text-sm font-medium">
            {uploading ? "Uploading..." : "Upload Sample"}
          </button>
          <input ref={inputRef} type="file" hidden accept=".vcf,.fastq,.fq,.bam,.csv"
            onChange={(e) => e.target.files?.[0] && upload(e.target.files[0])} />
        </div>
        {error && <p className="text-red-400 mb-4 text-sm">{error}</p>}
        <div className="bg-slate-900 rounded-lg border border-slate-800 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-800 text-slate-400 text-left">
              <tr><th className="p-3">Name</th><th className="p-3">Type</th><th className="p-3">Size</th><th className="p-3">Status</th><th className="p-3">Created</th></tr>
            </thead>
            <tbody>
              {samples.map((s) => (
                <tr key={s.id} className="border-t border-slate-800">
                  <td className="p-3">{s.name}</td>
                  <td className="p-3">{s.file_type}</td>
                  <td className="p-3">{s.file_size_bytes ? `${(s.file_size_bytes / 1024).toFixed(1)} KB` : "-"}</td>
                  <td className="p-3">{s.status}</td>
                  <td className="p-3 text-slate-500">{new Date(s.created_at).toLocaleString()}</td>
                </tr>
              ))}
              {samples.length === 0 && <tr><td colSpan={5} className="p-6 text-slate-500 text-center">No samples yet.</td></tr>}
            </tbody>
          </table>
        </div>
      </main>
    </div>
  );
}
