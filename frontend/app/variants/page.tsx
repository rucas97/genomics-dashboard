"use client";
import { useEffect, useState } from "react";
import Sidebar from "@/components/Sidebar";
import { apiFetch } from "@/lib/api";

const CLINVAR_CHIPS = [
  { key: "", label: "All" },
  { key: "pathogenic", label: "Pathogenic", color: "bg-red-900 text-red-300" },
  { key: "vus", label: "VUS", color: "bg-amber-900 text-amber-300" },
  { key: "benign", label: "Benign", color: "bg-emerald-900 text-emerald-300" },
];

const IMPACT_CHIPS = [
  { key: "", label: "Any impact" },
  { key: "HIGH", label: "HIGH" },
  { key: "MODERATE", label: "MODERATE" },
  { key: "LOW", label: "LOW" },
];

export default function Variants() {
  const [variants, setVariants] = useState<any[]>([]);
  const [summary, setSummary] = useState<any>(null);
  const [gene, setGene] = useState("");
  const [genePanel, setGenePanel] = useState("");
  const [clinvarClass, setClinvarClass] = useState("");
  const [impact, setImpact] = useState("");
  const [prioritised, setPrioritised] = useState(false);
  const [loading, setLoading] = useState(false);
  const [count, setCount] = useState(0);

  async function search() {
    setLoading(true);
    const params = new URLSearchParams({ limit: "500" });
    if (gene) params.append("gene", gene);
    if (genePanel) params.append("genes", genePanel);
    if (clinvarClass) params.append("clinvar_class", clinvarClass);
    if (impact) params.append("impact", impact);
    if (prioritised) params.append("prioritised", "true");

    try {
      const res = await apiFetch(`/variants/?${params}`);
      setVariants(res.data);
      setCount(res.count ?? res.data.length);

      const s = await apiFetch("/variants/summary");
      setSummary(s);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { search(); }, [clinvarClass, impact, prioritised]);

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 p-8">
        <h1 className="text-2xl font-bold mb-6">Variant Explorer</h1>

        {/* Clinical Summary */}
        {summary && (
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-6">
            <SummaryCard label="Total" value={summary.total} />
            <SummaryCard label="Pathogenic" value={summary.counts.pathogenic} accent="text-red-400" />
            <SummaryCard label="VUS" value={summary.counts.vus} accent="text-amber-400" />
            <SummaryCard label="Benign" value={summary.counts.benign} accent="text-emerald-400" />
            <SummaryCard label="High impact" value={summary.high_impact} accent="text-blue-400" />
          </div>
        )}

        {/* Filter bar */}
        <div className="bg-slate-900 border border-slate-800 rounded-lg p-4 mb-4 space-y-3">
          <div className="flex flex-wrap gap-2 items-center">
            <span className="text-slate-400 text-xs uppercase tracking-wide w-20">ClinVar</span>
            {CLINVAR_CHIPS.map((c) => (
              <button
                key={c.key}
                onClick={() => setClinvarClass(c.key)}
                className={`text-xs px-3 py-1 rounded-full border transition ${
                  clinvarClass === c.key
                    ? "border-emerald-500 bg-emerald-950 text-emerald-300"
                    : "border-slate-700 text-slate-400 hover:border-slate-500"
                }`}
              >
                {c.label}
              </button>
            ))}
          </div>

          <div className="flex flex-wrap gap-2 items-center">
            <span className="text-slate-400 text-xs uppercase tracking-wide w-20">Impact</span>
            {IMPACT_CHIPS.map((c) => (
              <button
                key={c.key}
                onClick={() => setImpact(c.key)}
                className={`text-xs px-3 py-1 rounded-full border transition ${
                  impact === c.key
                    ? "border-emerald-500 bg-emerald-950 text-emerald-300"
                    : "border-slate-700 text-slate-400 hover:border-slate-500"
                }`}
              >
                {c.label}
              </button>
            ))}

            <button
              onClick={() => setPrioritised((v) => !v)}
              className={`ml-auto text-xs px-3 py-1 rounded-full border transition ${
                prioritised
                  ? "border-red-500 bg-red-950 text-red-300"
                  : "border-slate-700 text-slate-400 hover:border-slate-500"
              }`}
            >
              {prioritised ? "★ Prioritised" : "Prioritise"}
            </button>
          </div>

          <div className="flex gap-2">
            <input
              value={gene}
              onChange={(e) => setGene(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && search()}
              placeholder="Single gene (e.g. BRCA1)"
              className="bg-slate-950 border border-slate-800 rounded px-3 py-2 text-sm flex-1"
            />
            <input
              value={genePanel}
              onChange={(e) => setGenePanel(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && search()}
              placeholder="Gene panel: BRCA1,BRCA2,TP53,CFTR"
              className="bg-slate-950 border border-slate-800 rounded px-3 py-2 text-sm flex-1"
            />
            <button
              onClick={search}
              className="bg-emerald-600 hover:bg-emerald-500 px-4 py-2 rounded text-sm"
            >
              {loading ? "..." : "Search"}
            </button>
          </div>
        </div>

        <p className="text-slate-500 text-xs mb-3">{count} variants</p>

        <div className="bg-slate-900 rounded-lg border border-slate-800 overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-800 text-slate-400 text-left">
              <tr>
                <th className="p-3">Chrom</th>
                <th className="p-3">Pos</th>
                <th className="p-3">Ref/Alt</th>
                <th className="p-3">Gene</th>
                <th className="p-3">Consequence</th>
                <th className="p-3">Impact</th>
                <th className="p-3">ClinVar</th>
                <th className="p-3">gnomAD AF</th>
              </tr>
            </thead>
            <tbody>
              {variants.map((v) => (
                <tr key={v.id} className="border-t border-slate-800">
                  <td className="p-3">{v.chrom}</td>
                  <td className="p-3">{v.pos}</td>
                  <td className="p-3 font-mono">{v.ref}/{v.alt}</td>
                  <td className="p-3">{v.gene || "-"}</td>
                  <td className="p-3">{v.consequence || "-"}</td>
                  <td className="p-3">
                    {v.impact ? (
                      <span className={`text-xs px-2 py-0.5 rounded ${
                        v.impact === "HIGH" ? "bg-red-900 text-red-300" :
                        v.impact === "MODERATE" ? "bg-amber-900 text-amber-300" :
                        "bg-slate-800 text-slate-400"
                      }`}>{v.impact}</span>
                    ) : "-"}
                  </td>
                  <td className="p-3">
                    {v.clinvar_significance ? (
                      <span className={`text-xs px-2 py-1 rounded ${
                        v.clinvar_significance.includes("Pathogenic") ? "bg-red-900 text-red-300" :
                        v.clinvar_significance.includes("Benign") ? "bg-emerald-900 text-emerald-300" :
                        v.clinvar_significance.toLowerCase().includes("uncertain") ? "bg-amber-900 text-amber-300" :
                        "bg-slate-800"
                      }`}>{v.clinvar_significance}</span>
                    ) : "-"}
                  </td>
                  <td className="p-3">
                    {v.gnomad_af != null ? Number(v.gnomad_af).toExponential(2) : "-"}
                  </td>
                </tr>
              ))}
              {variants.length === 0 && (
                <tr>
                  <td colSpan={8} className="p-6 text-slate-500 text-center">
                    No variants match these filters.
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

function SummaryCard({ label, value, accent = "text-slate-100" }: any) {
  return (
    <div className="bg-slate-900 rounded-lg border border-slate-800 p-4">
      <div className="text-slate-400 text-xs uppercase tracking-wide">{label}</div>
      <div className={`text-2xl font-bold mt-1 ${accent}`}>{value ?? 0}</div>
    </div>
  );
}
