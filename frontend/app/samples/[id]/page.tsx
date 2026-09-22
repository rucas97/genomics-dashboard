"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import Sidebar from "@/components/Sidebar";
import { apiFetch } from "@/lib/api";

export default function SampleDetail() {
  const params = useParams();
  const id = params.id as string;
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    apiFetch(`/samples/${id}`)
      .then(setData)
      .catch((e) => setError(e.message));
  }, [id]);

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 p-8">
        <Link href="/samples" className="text-emerald-400 text-sm hover:underline">
          ← Back to Samples
        </Link>
        <h1 className="text-2xl font-bold mb-6 mt-3">Sample Detail</h1>
        {error && <p className="text-red-400 mb-4">{error}</p>}
        {!data && !error && <p className="text-slate-500">Loading...</p>}
        {data && (
          <>
            <div className="bg-slate-900 rounded-lg border border-slate-800 p-6 mb-6">
              <dl className="grid grid-cols-2 gap-3 text-sm">
                <dt className="text-slate-400">Name</dt>
                <dd>{data.sample.name}</dd>
                <dt className="text-slate-400">Status</dt>
                <dd>{data.sample.status}</dd>
                <dt className="text-slate-400">Type</dt>
                <dd>{data.sample.file_type}</dd>
                <dt className="text-slate-400">Size</dt>
                <dd>{data.sample.file_size_bytes} bytes</dd>
                <dt className="text-slate-400">Created</dt>
                <dd>{new Date(data.sample.created_at).toLocaleString()}</dd>
              </dl>
            </div>
            <h2 className="text-lg font-semibold mb-3">QC Metrics</h2>
            <div className="bg-slate-900 rounded-lg border border-slate-800 p-6">
              {data.qc && data.qc.length > 0 ? (
                <dl className="grid grid-cols-2 gap-3 text-sm">
                  <dt className="text-slate-400">Variant count</dt>
                  <dd>{data.qc[0].variant_count ?? "-"}</dd>
                  <dt className="text-slate-400">SNPs</dt>
                  <dd>{data.qc[0].snp_count ?? "-"}</dd>
                  <dt className="text-slate-400">Indels</dt>
                  <dd>{data.qc[0].indel_count ?? "-"}</dd>
                  <dt className="text-slate-400">Mean quality</dt>
                  <dd>{data.qc[0].mean_coverage ?? "-"}</dd>
                </dl>
              ) : (
                <p className="text-slate-500 text-sm">No QC metrics yet.</p>
              )}
            </div>
          </>
        )}
      </main>
    </div>
  );
}
