"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import Sidebar from "@/components/Sidebar";
import QCCharts from "@/components/QCCharts";
import { apiFetch } from "@/lib/api";

export default function SampleDetail() {
  const params = useParams();
  const id = params.id as string;
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [annotating, setAnnotating] = useState(false);
  const [reporting, setReporting] = useState(false);

  useEffect(() => {
    if (!id) return;
    apiFetch(`/samples/${id}`).then(setData).catch((e) => setError(e.message));
  }, [id]);

  async function annotate() {
    setAnnotating(true);
    try {
      await apiFetch(`/annotate/sample/${id}`, { method: "POST" });
      setTimeout(() => window.location.reload(), 12000);
    } catch (e: any) {
      alert(e.message);
      setAnnotating(false);
    }
  }

  async function generateReport() {
    setReporting(true);
    try {
      await apiFetch(`/reports/sample/${id}`, { method: "POST" });
      window.location.href = "/reports";
    } catch (e: any) {
      alert(e.message);
      setReporting(false);
    }
  }

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 p-8">
        <Link href="/samples" className="text-emerald-400 text-sm hover:underline">
          ← Back to Samples
        </Link>
        <div className="flex items-center justify-between mt-3 mb-6">
          <h1 className="text-2xl font-bold">Sample Detail</h1>
          <div className="flex gap-2">
            <button
              onClick={annotate}
              disabled={annotating}
              className="bg-slate-800 hover:bg-slate-700 disabled:opacity-50 px-4 py-2 rounded text-sm font-medium"
            >
              {annotating ? "Annotating (~12s)..." : "Annotate"}
            </button>
            <button
              onClick={generateReport}
              disabled={reporting}
              className="bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 px-4 py-2 rounded text-sm font-medium"
            >
              {reporting ? "Generating..." : "Generate Report"}
            </button>
          </div>
        </div>

        {error && <p className="text-red-400 mb-4">{error}</p>}
        {!data && !error && <p className="text-slate-500">Loading...</p>}
        {data && (
          <>
            <div className="bg-slate-900 rounded-lg border border-slate-800 p-6 mb-6">
              <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wide mb-4">
                Sample Info
              </h2>
              <dl className="grid grid-cols-2 gap-3 text-sm">
                <dt className="text-slate-400">Name</dt><dd>{data.sample.name}</dd>
                <dt className="text-slate-400">Status</dt><dd>{data.sample.status}</dd>
                <dt className="text-slate-400">Type</dt><dd>{data.sample.file_type}</dd>
                <dt className="text-slate-400">Size</dt><dd>{data.sample.file_size_bytes} bytes</dd>
                <dt className="text-slate-400">Created</dt><dd>{new Date(data.sample.created_at).toLocaleString()}</dd>
              </dl>
            </div>

            <h2 className="text-lg font-semibold mb-3">QC Metrics</h2>
            {data.qc && data.qc.length > 0 ? (
              <QCCharts qc={data.qc[0]} />
            ) : (
              <div className="bg-slate-900 rounded-lg border border-slate-800 p-6 text-slate-500 text-sm">
                No QC metrics yet. Upload a VCF to generate them.
              </div>
            )}

            {data.qc && data.qc.length > 0 && (
              <div className="bg-slate-900 rounded-lg border border-slate-800 p-6 mt-6">
                <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wide mb-4">
                  Raw Metrics
                </h3>
                <dl className="grid grid-cols-2 gap-3 text-sm">
                  <dt className="text-slate-400">Variant count</dt><dd>{data.qc[0].variant_count ?? "-"}</dd>
                  <dt className="text-slate-400">SNPs</dt><dd>{data.qc[0].snp_count ?? "-"}</dd>
                  <dt className="text-slate-400">Indels</dt><dd>{data.qc[0].indel_count ?? "-"}</dd>
                  <dt className="text-slate-400">Mean quality</dt><dd>{data.qc[0].mean_coverage ?? "-"}</dd>
                </dl>
              </div>
            )}
          </>
        )}
      </main>
    </div>
  );
}
