"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import Sidebar from "@/components/Sidebar";
import { apiFetch } from "@/lib/api";
import {
  ScatterChart, Scatter, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ZAxis,
} from "recharts";

export default function CohortDetail() {
  const params = useParams();
  const id = params.id as string;
  const [cohort, setCohort] = useState<any>(null);
  const [pca, setPca] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    apiFetch(`/cohorts/${id}`).then(setCohort).catch((e) => setError(e.message));
  }, [id]);

  async function runPca() {
    setLoading(true);
    setError(null);
    try {
      const res = await apiFetch(`/cohorts/${id}/pca`);
      setPca(res);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 p-8">
        <Link href="/cohorts" className="text-emerald-400 text-sm hover:underline">
          ← Back to Cohorts
        </Link>

        {!cohort && !error && <p className="text-slate-500 mt-4">Loading...</p>}
        {error && <p className="text-red-400 mt-4">{error}</p>}

        {cohort && (
          <>
            <div className="flex items-center justify-between mt-3 mb-6">
              <div>
                <h1 className="text-2xl font-bold">{cohort.name}</h1>
                {cohort.description && (
                  <p className="text-slate-400 text-sm mt-1">{cohort.description}</p>
                )}
              </div>
              <button
                onClick={runPca}
                disabled={loading}
                className="bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 px-4 py-2 rounded text-sm font-medium"
              >
                {loading ? "Computing PCA..." : "Run PCA"}
              </button>
            </div>

            <div className="bg-slate-900 rounded-lg border border-slate-800 p-6 mb-6">
              <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wide mb-4">
                Cohort Info
              </h2>
              <dl className="grid grid-cols-2 gap-3 text-sm">
                <dt className="text-slate-400">Samples</dt>
                <dd>{(cohort.sample_ids || []).length}</dd>
                <dt className="text-slate-400">Created</dt>
                <dd>{new Date(cohort.created_at).toLocaleString()}</dd>
              </dl>
            </div>

            {pca?.error && (
              <div className="bg-red-950 border border-red-900 text-red-300 rounded-lg p-4 mb-6 text-sm">
                {pca.error}
              </div>
            )}

            {pca?.points && pca.points.length > 0 && (
              <>
                <h2 className="text-lg font-semibold mb-3">PCA — Sample Clustering</h2>
                <div className="bg-slate-900 rounded-lg border border-slate-800 p-6 mb-6">
                  <ResponsiveContainer width="100%" height={400}>
                    <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
                      <CartesianGrid stroke="#1e293b" />
                      <XAxis
                        type="number"
                        dataKey="x"
                        name="PC1"
                        stroke="#64748b"
                        fontSize={12}
                        label={{
                          value: `PC1 (${((pca.explained_variance?.[0] ?? 0) * 100).toFixed(1)}%)`,
                          position: "insideBottom",
                          offset: -10,
                          fill: "#94a3b8",
                          fontSize: 12,
                        }}
                      />
                      <YAxis
                        type="number"
                        dataKey="y"
                        name="PC2"
                        stroke="#64748b"
                        fontSize={12}
                        label={{
                          value: `PC2 (${((pca.explained_variance?.[1] ?? 0) * 100).toFixed(1)}%)`,
                          angle: -90,
                          position: "insideLeft",
                          fill: "#94a3b8",
                          fontSize: 12,
                        }}
                      />
                      <ZAxis range={[120, 120]} />
                      <Tooltip
                        cursor={{ strokeDasharray: "3 3" }}
                        contentStyle={{
                          background: "#0f172a",
                          border: "1px solid #1e293b",
                          borderRadius: 6,
                          fontSize: 12,
                        }}
                        formatter={(value: any, name: string) => {
                          if (name === "x" || name === "y")
                            return [Number(value).toFixed(3), name.toUpperCase()];
                          return [value, name];
                        }}
                        labelFormatter={() => ""}
                        content={({ payload }) => {
                          if (!payload || !payload.length) return null;
                          const p = payload[0].payload;
                          return (
                            <div className="bg-slate-950 border border-slate-800 rounded p-2 text-xs">
                              <div className="text-emerald-400 font-medium">{p.name}</div>
                              <div className="text-slate-400">
                                PC1: {p.x.toFixed(3)}
                              </div>
                              <div className="text-slate-400">
                                PC2: {p.y.toFixed(3)}
                              </div>
                            </div>
                          );
                        }}
                      />
                      <Scatter data={pca.points} fill="#10b981" />
                    </ScatterChart>
                  </ResponsiveContainer>
                  <p className="text-slate-500 text-xs mt-3 text-center">
                    {pca.n_samples} samples · {pca.n_variants} variants · hover a point to see the sample
                  </p>
                </div>

                <h2 className="text-lg font-semibold mb-3">Sample Coordinates</h2>
                <div className="bg-slate-900 rounded-lg border border-slate-800 overflow-hidden">
                  <table className="w-full text-sm">
                    <thead className="bg-slate-800 text-slate-400 text-left">
                      <tr>
                        <th className="p-3">Sample</th>
                        <th className="p-3">PC1</th>
                        <th className="p-3">PC2</th>
                      </tr>
                    </thead>
                    <tbody>
                      {pca.points.map((p: any) => (
                        <tr key={p.sample_id} className="border-t border-slate-800">
                          <td className="p-3">{p.name}</td>
                          <td className="p-3 font-mono text-xs">{p.x.toFixed(4)}</td>
                          <td className="p-3 font-mono text-xs">{p.y.toFixed(4)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            )}

            {pca && !pca.points && !pca.error && (
              <div className="bg-slate-900 rounded-lg border border-slate-800 p-6 text-slate-500 text-sm">
                No PCA results. Click "Run PCA" to compute.
              </div>
            )}
          </>
        )}
      </main>
    </div>
  );
}
