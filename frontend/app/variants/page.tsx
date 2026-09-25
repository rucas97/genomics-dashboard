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

type CombineMode = "union" | "intersection";

export default function Variants() {
  const [variants, setVariants] = useState<any[]>([]);
  const [summary, setSummary] = useState<any>(null);
  const [samples, setSamples] = useState<any[]>([]);
  const [selectedSampleIds, setSelectedSampleIds] = useState<string[]>([]);
  const [combineMode, setCombineMode] = useState<CombineMode>("union");
  const [gene, setGene] = useState("");
  const [genePanel, setGenePanel] = useState("");
  const [clinvarClass, setClinvarClass] = useState("");
  const [acmgClass, setAcmgClass] = useState("");
  const [impact, setImpact] = useState("");
  const [prioritised, setPrioritised] = useState(false);
  const [loading, setLoading] = useState(false);
  const [count, setCount] = useState(0);
  const [selectedVariant, setSelectedVariant] = useState<string | null>(null);
  const [showSamplePicker, setShowSamplePicker] = useState(false);

  useEffect(() => {
    apiFetch("/samples/")
      .then((data) => {
        setSamples(data);
        if (data.length > 0 && selectedSampleIds.length === 0) {
          setSelectedSampleIds([data[0].id]);
        }
      })
      .catch(() => {});
  }, []);

  async function search() {
    setLoading(true);
    const params = new URLSearchParams({ limit: "2000" });
    if (selectedSampleIds.length === 1) {
      params.append("sample_id", selectedSampleIds[0]);
    } else if (selectedSampleIds.length > 1) {
      params.append("sample_ids", selectedSampleIds.join(","));
    }
    if (gene) params.append("gene", gene);
    if (genePanel) params.append("genes", genePanel);
    if (clinvarClass) params.append("clinvar_class", clinvarClass);
    if (acmgClass) params.append("acmg_class", acmgClass);
    if (impact) params.append("impact", impact);
    if (prioritised) params.append("prioritised", "true");

    try {
      const res = await apiFetch(`/variants/?${params}`);
      let rows = res.data;

      // Intersection: keep only variants present in every selected sample
      if (combineMode === "intersection" && selectedSampleIds.length > 1) {
        const keyOf = (v: any) => `${v.chrom}:${v.pos}:${v.ref}>${v.alt}`;

        // Fetch each sample separately to know who has what
        const perSample: Record<string, Set<string>> = {};
        for (const sid of selectedSampleIds) {
          const sres = await apiFetch(`/variants/?sample_id=${sid}&limit=2000`);
          perSample[sid] = new Set(sres.data.map(keyOf));
        }

        // Deduplicate rows by variant key first
        const seen = new Set<string>();
        const dedup: any[] = [];
        for (const v of rows) {
          const k = keyOf(v);
          if (seen.has(k)) continue;
          seen.add(k);
          dedup.push(v);
        }

        rows = dedup.filter((v: any) => {
          const k = keyOf(v);
          return selectedSampleIds.every((sid) => perSample[sid]?.has(k));
        });
      }

      setVariants(rows);
      setCount(rows.length);

      const summaryParams = new URLSearchParams();
      if (selectedSampleIds.length === 1) summaryParams.append("sample_id", selectedSampleIds[0]);
      setSummary(await apiFetch(`/variants/summary?${summaryParams}`));
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    search();
  }, [selectedSampleIds, combineMode, clinvarClass, acmgClass, impact, prioritised]);

  function toggleSample(id: string) {
    setSelectedSampleIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  }

  function selectAllSamples() {
    setSelectedSampleIds(samples.map((s) => s.id));
  }

  function clearSamples() {
    setSelectedSampleIds([]);
  }

  function clearFilters() {
    setGene("");
    setGenePanel("");
    setClinvarClass("");
    setAcmgClass("");
    setImpact("");
    setPrioritised(false);
  }

  const hasActiveFilters = gene || genePanel || clinvarClass || acmgClass || impact || prioritised;

  const sampleLabel =
    selectedSampleIds.length === 0
      ? "All samples"
      : selectedSampleIds.length === 1
      ? samples.find((s) => s.id === selectedSampleIds[0])?.name || "1 sample"
      : `${selectedSampleIds.length} samples selected`;

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 p-8">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold">Variant Explorer</h1>
          {hasActiveFilters && (
            <button
              onClick={clearFilters}
              className="text-xs text-slate-400 hover:text-slate-200"
            >
              Clear all filters
            </button>
          )}
        </div>

        {/* Sample multi-select */}
        <div className="bg-slate-900 border border-slate-800 rounded-lg p-4 mb-4">
          <div className="flex items-center gap-3 flex-wrap">
            <span className="text-slate-400 text-xs uppercase tracking-wide">
              Samples
            </span>
            <button
              onClick={() => setShowSamplePicker((v) => !v)}
              className="bg-slate-950 border border-slate-800 rounded px-4 py-2 text-sm hover:border-slate-600 text-left flex-1 max-w-xl flex items-center justify-between"
            >
              <span className="text-slate-300">{sampleLabel}</span>
              <span className="text-slate-500 text-xs">{showSamplePicker ? "▲" : "▼"}</span>
            </button>

            {selectedSampleIds.length > 1 && (
              <div className="flex items-center gap-1 bg-slate-950 border border-slate-800 rounded p-0.5">
                <button
                  onClick={() => setCombineMode("union")}
                  className={`text-xs px-3 py-1.5 rounded transition ${
                    combineMode === "union"
                      ? "bg-emerald-600 text-white"
                      : "text-slate-400 hover:text-slate-200"
                  }`}
                  title="Show every variant present in ANY selected sample"
                >
                  Union
                </button>
                <button
                  onClick={() => setCombineMode("intersection")}
                  className={`text-xs px-3 py-1.5 rounded transition ${
                    combineMode === "intersection"
                      ? "bg-emerald-600 text-white"
                      : "text-slate-400 hover:text-slate-200"
                  }`}
                  title="Show only variants present in EVERY selected sample"
                >
                  Intersection
                </button>
              </div>
            )}

            {selectedSampleIds.length > 0 && (
              <button
                onClick={clearSamples}
                className="text-xs text-slate-500 hover:text-slate-300"
              >
                Clear
              </button>
            )}
          </div>

          {showSamplePicker && (
            <div className="mt-3 bg-slate-950 border border-slate-800 rounded p-3 max-h-72 overflow-y-auto">
              <div className="flex items-center gap-3 mb-2 pb-2 border-b border-slate-800 sticky top-0 bg-slate-950">
                <button
                  onClick={selectAllSamples}
                  className="text-xs text-emerald-400 hover:underline"
                >
                  Select all
                </button>
                <button
                  onClick={clearSamples}
                  className="text-xs text-slate-500 hover:text-slate-300"
                >
                  Clear all
                </button>
                <span className="text-xs text-slate-500 ml-auto">
                  {selectedSampleIds.length} selected
                </span>
              </div>
              {samples.map((s) => (
                <label
                  key={s.id}
                  className="flex items-center gap-3 px-2 py-1.5 hover:bg-slate-800 rounded cursor-pointer text-sm"
                >
                  <input
                    type="checkbox"
                    checked={selectedSampleIds.includes(s.id)}
                    onChange={() => toggleSample(s.id)}
                  />
                  <span className="truncate">{s.name}</span>
                  <span
                    className={`text-xs px-2 py-0.5 rounded ml-auto ${
                      s.status === "ready"
                        ? "bg-emerald-900 text-emerald-300"
                        : s.status === "processing"
                        ? "bg-amber-900 text-amber-300"
                        : s.status === "failed"
                        ? "bg-red-900 text-red-300"
                        : "bg-slate-800 text-slate-300"
                    }`}
                  >
                    {s.status}
                  </span>
                </label>
              ))}
            </div>
          )}
        </div>

        {summary && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
            <SummaryCard label="Total" value={count} />
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
          {count} variants
          {selectedSampleIds.length === 1
            ? ` in ${sampleLabel}`
            : selectedSampleIds.length > 1
            ? ` (${combineMode === "union" ? "union" : "intersection"} of ${selectedSampleIds.length} samples)`
            : " across all samples"}
          {" · click any row to open the ACMG panel"}
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
                        v.clinvar_significance.toLowerCase().includes("uncertain") ? "bg-amber-900 text-amber-300" :
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
