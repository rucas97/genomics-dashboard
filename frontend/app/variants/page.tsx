"use client";
import { useEffect, useState } from "react";
import Sidebar from "@/components/Sidebar";
import { apiFetch } from "@/lib/api";

export default function Variants() {
  const [variants, setVariants] = useState<any[]>([]);
  const [gene, setGene] = useState("");
  const [loading, setLoading] = useState(false);
  const [count, setCount] = useState(0);
  async function search() {
    setLoading(true);
    const params = new URLSearchParams({ limit: "100" });
    if (gene) params.append("gene", gene);
    try {
      const res = await apiFetch(`/variants/?${params}`);
      setVariants(res.data); setCount(res.count ?? res.data.length);
    } finally { setLoading(false); }
  }
  useEffect(() => { search(); }, []);
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 p-8">
        <h1 className="text-2xl font-bold mb-6">Variant Explorer</h1>
        <div className="flex gap-2 mb-4">
          <input value={gene} onChange={(e) => setGene(e.target.value)} onKeyDown={(e) => e.key === "Enter" && search()}
            placeholder="Filter by gene (e.g. BRCA1)"
            className="bg-slate-900 border border-slate-800 rounded px-3 py-2 text-sm flex-1" />
          <button onClick={search} className="bg-emerald-600 hover:bg-emerald-500 px-4 py-2 rounded text-sm">
            {loading ? "..." : "Search"}
          </button>
        </div>
        <p className="text-slate-500 text-xs mb-3">{count} variants</p>
        <div className="bg-slate-900 rounded-lg border border-slate-800 overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-800 text-slate-400 text-left">
              <tr>
                <th className="p-3">Chrom</th><th className="p-3">Pos</th><th className="p-3">Ref/Alt</th>
                <th className="p-3">Gene</th><th className="p-3">Consequence</th><th className="p-3">ClinVar</th><th className="p-3">gnomAD AF</th>
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
                    {v.clinvar_significance ? (
                      <span className={`text-xs px-2 py-1 rounded ${
                        v.clinvar_significance.includes("Pathogenic") ? "bg-red-900 text-red-300" :
                        v.clinvar_significance.includes("Benign") ? "bg-emerald-900 text-emerald-300" : "bg-slate-800"
                      }`}>{v.clinvar_significance}</span>
                    ) : "-"}
                  </td>
                  <td className="p-3">{v.gnomad_af != null ? Number(v.gnomad_af).toExponential(2) : "-"}</td>
                </tr>
              ))}
              {variants.length === 0 && <tr><td colSpan={7} className="p-6 text-slate-500 text-center">No variants. Upload a VCF first.</td></tr>}
            </tbody>
          </table>
        </div>
      </main>
    </div>
  );
}
