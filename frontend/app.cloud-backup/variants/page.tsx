"use client";
import { useEffect, useState } from "react";
import Sidebar from "@/components/Sidebar";
import ACMGPanel from "@/components/ACMGPanel";
import { apiFetch } from "@/lib/api";

const CLINVAR_CHIPS = [
  { key: "", label: "All" },
  { key: "pathogenic", label: "ClinVar Pathogenic" },
  { key: "vus", label: "ClinVar VUS" },
  { key: "benign", label: "ClinVar Benign" },
];

const ACMG_CHIPS = [
  { key: "", label: "All ACMG" },
  { key: "Pathogenic", label: "Pathogenic" },
  { key: "Likely Pathogenic", label: "Likely P" },
  { key: "VUS", label: "VUS" },
  { key: "Likely Benign", label: "Likely B" },
  { key: "Benign", label: "Benign" },
];

const IMPACT_CHIPS = [
  { key: "", label: "Any impact" },
  { key: "HIGH", label: "HIGH" },
  { key: "MODERATE", label: "MODERATE" },
  { key: "LOW", label: "LOW" },
];

const ACMG_BADGE: Record<string, string> = {
  "Pathogenic": "bg-red-900 text-red-300",
  "Likely Pathogenic": "bg-orange-900 text-orange-300",
  "VUS": "bg-amber-900 text-amber-300",
  "Likely Benign": "bg-teal-900 text-teal-300",
  "Benign": "bg-emerald-900 text-emerald-300",
};

export default function Variants() {
  const [variants, setVariants] = useState<any[]>([]);
  const [summary, setSummary] = useState<any>(null);
  const [gene, setGene] = useState("");
  const [genePanel, setGenePanel] = useState("");
  const [clinvarClass, setClinvarClass] = useState("");
  const [acmgClass, setAcmgClass] = useState("");
  const [impact, setImpact] = useState("");
  const [prioritised, setPrioritised] = useState(false);
  const [loading, setLoading] = useState(false);
  const [count, setCount] = useState(0);
  const [selectedVariant, setSelectedVariant] = useState<string | null>(null);

  async function search() {
    setLoading(true);
    const params = new URLSearchParams({ limit: "500" });
    if (gene) params.append("gene", gene);
    if (genePanel) params.append("genes", genePanel);
    if (clinvarClass) params.append("clinvar_class", clinvarClass);
    if (acmgClass) params.append("acmg_class", acmgClass);
    if (impact) params.append("impact", impact);
    if (prioritised) params.append("prioritised", "true");

    try {
      const res = await apiFetch(`/variants/?${params}`);
      setVariants(res.data);
      setCount(res.count ?? res.data.length);
      setSummary(await apiFetch("/variants/summary"));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    search();
  }, [clinvarClass, acmgClass, impact, prioritised]);

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 p-8">
        <h1 className="text-2xl font-bold mb-6">Variant Explorer</h1>

        {summary && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
            <SummaryCard label="Total" value={summary.total} />
            <SummaryCard label="ClinVar Pathogenic" value={summary.counts.pathogenic} accent="text-red-400" />
            <SummaryCard label="ACMG Pathogenic" value={summary.acmg_counts?.["Pathogenic"] || 0} accent="text-red-400" />
            <SummaryCard label="ACMG VUS" value={summary.acmg_counts?.["VUS"] || 0} accent="text-amber-400" />
          </div>
        )}

        <div className="bg-slate-900 border border-slate-800 rounded-lg p-4 mb-4 space-y-3">
          <div className="flex flex-wrap gap-2 items-center">
            <span className="text-slate-400 text-xs uppercase tracking-wide w-24">ACMG class</span>
            {ACMG_CHIPS.map((c) => (
              <button
                key={c.key}
                onClick={() => setAcmgClass(c.key)}
                className={`text-xs px-3 py-1 rounded-full border transition ${
                  acmgClass === c.key
                    ? "border-emerald-500 bg-emerald-950 text-emerald-300"
                    : "border-slate-700 text-slate-400 hover:border-slate-500"
                }`}
              >
                {c.label}
              </button>
            ))}
          </div>

          <div className="flex flex-wrap gap-2 items-center">
            <span className="text-slate-400 text-xs uppercase tracking-wide w-24">ClinVar</span>
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
            <span className="text-slate-400 text-xs uppercase tracking-wide w-24">Impact</span>
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
          </div>

          <div className="flex gap-2">
            <input
              value={gene}
              onChange={(e) => setGene(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && search()}
              placeholder="Single gene"
              className="bg-slate-950 border border-slate-800 rounded px-3 py-2 text-sm flex-1"
            />
            <input
              value={genePanel}
              onChange={(e) => setGenePanel(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && search()}
              placeholder="Gene panel: BRCA1,BRCA2,TP53"
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

        <p className="text-slate-500 text-xs mb-3">
          {count} variants · click any row to open the ACMG panel
        </p>

        <div className="bg-slate-900 rounded-lg border border-slate-800 overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-800 text-slate-400 text-left">
              <tr>
                <th className="p-3">Position</th>
                <th className="p-3">Ref/Alt</th>
                <th className="p-3">Gene</th>
                <th className="p-3">Consequence</th>
                <th className="p-3">Impact</th>
                <th className="p-3">ClinVar</th>
                <th className="p-3">ACMG</th>
              </tr>
            </thead>
            <tbody>
              {variants.map((v) => (
                <tr
                  key={v.id}
                  onClick={() => setSelectedVariant(v.id)}
                  className="border-t border-slate-800 hover:bg-slate-800 cursor-pointer"
                >
                  <td className="p-3 font-mono text-xs">{v.chrom}:{v.pos}</td>
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
                        "bg-slate-800"
                      }`}>{v.clinvar_significance}</span>
                    ) : "-"}
                  </td>
                  <td className="p-3">
                    {v.acmg_classification ? (
                      <span className={`text-xs px-2 py-1 rounded font-medium ${ACMG_BADGE[v.acmg_classification] || "bg-slate-800"}`}>
                        {v.acmg_classification}
                      </span>
                    ) : "-"}
                  </td>
                </tr>
              ))}
              {variants.length === 0 && (
                <tr>
                  <td colSpan={7} className="p-6 text-slate-500 text-center">
                    No variants match these filters.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </main>

      {selectedVariant && (
        <ACMGPanel variantId={selectedVariant} onClose={() => setSelectedVariant(null)} />
      )}
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
