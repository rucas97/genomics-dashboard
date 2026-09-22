"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import Sidebar from "@/components/Sidebar";
import { apiFetch } from "@/lib/api";
import {
  ScatterChart, Scatter, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ZAxis,
  BarChart, Bar, PieChart, Pie, Cell, Legend,
} from "recharts";

const CLASS_COLORS: Record<string, string> = {
  pathogenic: "#ef4444",
  vus: "#f59e0b",
  benign: "#10b981",
  other: "#64748b",
};

export default function CohortDetail() {
  const params = useParams();
  const id = params.id as string;
  const [cohort, setCohort] = useState<any>(null);
  const [pca, setPca] = useState<any>(null);
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [statsLoading, setStatsLoading] = useState(false);
  const [reporting, setReporting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    apiFetch(`/cohorts/${id}`).then(setCohort).catch((e) => setError(e.message));
  }, [id]);

  async function runPca() {
    setLoading(true);
    setError(null);
    try {
      setPca(await apiFetch(`/cohorts/${id}/pca`));
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  async function runStats() {
    setStatsLoading(true);
    setError(null);
    try {
      setStats(await apiFetch(`/cohorts/${id}/stats`));
    } catch (e: any) {
      setError(e.message);
    } finally {
      setStatsLoading(false);
    }
  }

  async function generateReport() {
    setReporting(true);
    try {
      await apiFetch(`/reports/cohort/${id}`, { method: "POST" });
      window.location.href = "/reports";
    } catch (e: any) {
      alert(e.message);
      setReporting(false);
    }
  }

  const pieData = stats
    ? Object.entries(stats.classification)
        .map(([k, v]) => ({ name: k.toUpperCase(), value: v as number }))
        .filter((d) => d.value > 0)
    : [];

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
              <div className="flex gap-2">
                <button
                  onClick={generateReport}
                  disabled={reporting}
                  className="bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 px-4 py-2 rounded text-sm font-medium"
                >
                  {reporting ? "Generating..." : "Generate Report"}
                </button>
                <button
                  onClick={runStats}
                  disabled={statsLoading}
                  className="bg-slate-800 hover:bg-slate-700 disabled:opacity-50 px-4 py-2 rounded text-sm font-medium"
                >
                  {statsLoading ? "Computing..." : "Load Stats"}
                </button>
                <button
                  onClick={runPca}
                  disabled={loading}
                  className="bg-slate-800 hover:bg-slate-700 disabled:opacity-50 px-4 py-2 rounded text-sm font-medium"
                >
                  {loading ? "Computing PCA..." : "Run PCA"}
                </button>
              </div>
            </div>

            <div className="bg-slate-900 rounded-lg border border-slate-800 p-6 mb-6">
              <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wide mb-4">
                Cohort Info
              </h2>
              <dl className="grid grid-cols-3 gap-3 text-sm">
                <dt className="text-slate-400">Samples</dt>
                <dd>{(cohort.sample_ids || []).length}</dd>
                <dt className="text-slate-400">Created</dt>
                <dd>{new Date(cohort.created_at).toLocaleString()}</dd>
              </dl>
            </div>

            {stats && (
              <>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                  <div className="bg-slate-900 rounded-lg border border-slate-800 p-6">
                    <div className="text-slate-400 text-sm mb-3">Classification Breakdown</div>
                    <ResponsiveContainer width="100%" height={180}>
                      <PieChart>
                        <Pie
                          data={pieData}
                          dataKey="value"
                          nameKey="name"
                          cx="50%"
                          cy="50%"
                          innerRadius={40}
                          outerRadius={70}
                          paddingAngle={2}
                        >
                          {pieData.map((d, i) => (
                            <Cell key={i} fill={CLASS_COLORS[d.name.toLowerCase()] || "#64748b"} />
                          ))}
                        </Pie>
                        <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: 6, fontSize: 12 }} />
                        <Legend wrapperStyle={{ fontSize: 11 }} />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>

                  <div className="md:col-span-2 bg-slate-900 rounded-lg border border-slate-800 p-6">
                    <div className="text-slate-400 text-sm mb-3">Top Mutated Genes</div>
                    <ResponsiveContainer width="100%" height={180}>
                      <BarChart data={stats.top_genes.slice(0, 8)}>
                        <CartesianGrid stroke="#1e293b" vertical={false} />
                        <XAxis dataKey="gene" stroke="#64748b" fontSize={11} />
                        <YAxis stroke="#64748b" fontSize={11} />
                        <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: 6, fontSize: 12 }} />
                        <Bar dataKey="count" fill="#10b981" radius={[4, 4, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                <div className="bg-slate-900 rounded-lg border border-slate-800 p-6 mb-6">
                  <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wide mb-4">
                    Gene Enrichment ({stats.n_samples} samples)
                  </h3>
                  <table className="w-full text-sm">
                    <thead className="text-slate-500 text-left">
                      <tr>
                        <th className="pb-2">Gene</th>
                        <th className="pb-2">Variants</th>
                        <th className="pb-2">Samples with variant</th>
                        <th className="pb-2">Frequency</th>
                      </tr>
                    </thead>
                    <tbody>
                      {stats.top_genes.map((g: any) => (
                        <tr key={g.gene} className="border-t border-slate-800">
                          <td className="py-2 text-emerald-400 font-medium">{g.gene}</td>
                          <td className="py-2">{g.count}</td>
                          <td className="py-2">{g.sample_count}/{stats.n_samples}</td>
                          <td className="py-2">{g.sample_pct}%</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {stats.shared_variants.length > 0 && (
                  <div className="bg-slate-900 rounded-lg border border-slate-800 p-6 mb-6">
                    <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wide mb-4">
                      Shared Variants Across Cohort
                    </h3>
                    <table className="w-full text-sm">
                      <thead className="text-slate-500 text-left">
                        <tr>
                          <th className="pb-2">Variant</th>
                          <th className="pb-2">Gene</th>
                          <th className="pb-2">Samples</th>
                          <th className="pb-2">Frequency</th>
                        </tr>
                      </thead>
                      <tbody>
                        {stats.shared_variants.map((v: any) => (
                          <tr key={v.variant} className="border-t border-slate-800">
                            <td className="py-2 font-mono text-xs">{v.variant}</td>
                            <td className="py-2">{v.gene || "-"}</td>
                            <td className="py-2">{v.sample_count}/{stats.n_samples}</td>
                            <td className="py-2">{v.sample_pct}%</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </>
            )}

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
                      <XAxis type="number" dataKey="x" name="PC1" stroke="#64748b" fontSize={12}
                        label={{ value: `PC1 (${((pca.explained_variance?.[0] ?? 0) * 100).toFixed(1)}%)`,
                          position: "insideBottom", offset: -10, fill: "#94a3b8", fontSize: 12 }} />
                      <YAxis type="number" dataKey="y" name="PC2" stroke="#64748b" fontSize={12}
                        label={{ value: `PC2 (${((pca.explained_variance?.[1] ?? 0) * 100).toFixed(1)}%)`,
                          angle: -90, position: "insideLeft", fill: "#94a3b8", fontSize: 12 }} />
                      <ZAxis range={[120, 120]} />
                      <Tooltip content={({ payload }) => {
                        if (!payload || !payload.length) return null;
                        const p = payload[0].payload;
                        return (
                          <div className="bg-slate-950 border border-slate-800 rounded p-2 text-xs">
                            <div className="text-emerald-400 font-medium">{p.name}</div>
                            <div className="text-slate-400">PC1: {p.x.toFixed(3)}</div>
                            <div className="text-slate-400">PC2: {p.y.toFixed(3)}</div>
                          </div>
                        );
                      }} />
                      <Scatter data={pca.points} fill="#10b981" />
                    </ScatterChart>
                  </ResponsiveContainer>
                  <p className="text-slate-500 text-xs mt-3 text-center">
                    {pca.n_samples} samples · {pca.n_variants} variants · hover a point to see the sample
                  </p>
                </div>
              </>
            )}
          </>
        )}
      </main>
    </div>
  );
}
