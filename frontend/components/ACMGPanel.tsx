"use client";
import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";

const CLASS_COLORS: Record<string, string> = {
  "Pathogenic": "bg-red-900 text-red-200 border-red-700",
  "Likely Pathogenic": "bg-orange-900 text-orange-200 border-orange-700",
  "VUS": "bg-amber-900 text-amber-200 border-amber-700",
  "Likely Benign": "bg-teal-900 text-teal-200 border-teal-700",
  "Benign": "bg-emerald-900 text-emerald-200 border-emerald-700",
};

const WEIGHT_ORDER: Record<string, number> = {
  "very_strong": 0, "strong": 1, "moderate": 2, "supporting": 3, "standalone": -1,
};

export default function ACMGPanel({ variantId, onClose }: { variantId: string; onClose: () => void }) {
  const [data, setData] = useState<any>(null);
  const [catalog, setCatalog] = useState<any[]>([]);
  const [fired, setFired] = useState<any[]>([]);
  const [notes, setNotes] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showAdd, setShowAdd] = useState(false);

  useEffect(() => {
    apiFetch(`/acmg/criteria`).then(setCatalog).catch(() => {});
  }, []);

  useEffect(() => {
    if (!variantId) return;
    apiFetch(`/acmg/variant/${variantId}`)
      .then((res) => {
        setData(res);
        setFired(res.acmg.criteria_fired || []);
        setNotes(res.acmg.notes || "");
      })
      .catch((e) => setError(e.message));
  }, [variantId]);

  function addCriterion(code: string) {
    if (fired.some((c) => c.code === code)) return;
    setFired([...fired, { code, source: "manual", evidence: "Manually added" }]);
    setShowAdd(false);
  }

  function removeCriterion(code: string) {
    setFired(fired.filter((c) => c.code !== code));
  }

  async function save() {
    setSaving(true);
    setError(null);
    try {
      await apiFetch(`/acmg/variant/${variantId}`, {
        method: "PUT",
        body: JSON.stringify({ criteria_fired: fired, notes: notes || null }),
      });
      const refreshed = await apiFetch(`/acmg/variant/${variantId}`);
      setData(refreshed);
      setFired(refreshed.acmg.criteria_fired || []);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  }

  if (!data && !error) {
    return (
      <div className="fixed inset-y-0 right-0 w-[520px] bg-slate-950 border-l border-slate-800 p-6 overflow-y-auto">
        <p className="text-slate-500">Loading...</p>
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="fixed inset-y-0 right-0 w-[520px] bg-slate-950 border-l border-slate-800 p-6">
        <p className="text-red-400">{error}</p>
        <button onClick={onClose} className="mt-4 text-slate-400">Close</button>
      </div>
    );
  }

  const cls = data.acmg.classification;
  const clsColor = CLASS_COLORS[cls] || "bg-slate-800 text-slate-300 border-slate-700";

  const missingEvidence = [];
  if (!data.variant.gene) missingEvidence.push("gene annotation");
  if (!data.variant.consequence) missingEvidence.push("consequence");
  if (!data.variant.impact) missingEvidence.push("impact");
  if (data.variant.gnomad_af == null) missingEvidence.push("population frequency (gnomAD)");
  if (!data.variant.clinvar_significance) missingEvidence.push("ClinVar record");

  return (
    <div className="fixed inset-y-0 right-0 w-[520px] bg-slate-950 border-l border-slate-800 overflow-y-auto z-50">
      <div className="sticky top-0 bg-slate-950 border-b border-slate-800 p-6 z-10">
        <div className="flex items-start justify-between mb-4">
          <div>
            <h2 className="text-lg font-bold">ACMG Classification</h2>
            <p className="text-xs text-slate-500 font-mono mt-1">
              {data.variant.chrom}:{data.variant.pos} {data.variant.ref}/{data.variant.alt}
            </p>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-100 text-xl leading-none">×</button>
        </div>

        <div className={`border rounded-lg p-4 ${clsColor}`}>
          <div className="text-xs uppercase tracking-wide opacity-80">Classification</div>
          <div className="text-2xl font-bold mt-1">{cls}</div>
          <div className="text-xs mt-2 opacity-90">Confidence: {data.acmg.confidence || "—"}</div>
          {data.acmg.auto_classification && data.acmg.auto_classification !== cls && (
            <div className="text-xs mt-1 opacity-90">
              Auto: {data.acmg.auto_classification} (manually overridden)
            </div>
          )}
        </div>
      </div>

      <div className="p-6 space-y-6">
        {/* Variant details */}
        <section>
          <h3 className="text-xs uppercase tracking-wide text-slate-400 mb-2">Variant Details</h3>
          <dl className="grid grid-cols-2 gap-2 text-sm">
            <dt className="text-slate-500">Gene</dt>
            <dd>{data.variant.gene || <span className="text-red-400">missing</span>}</dd>
            <dt className="text-slate-500">Consequence</dt>
            <dd>{data.variant.consequence || <span className="text-red-400">missing</span>}</dd>
            <dt className="text-slate-500">Impact</dt>
            <dd>{data.variant.impact || <span className="text-red-400">missing</span>}</dd>
            <dt className="text-slate-500">gnomAD AF</dt>
            <dd>{data.variant.gnomad_af != null ? Number(data.variant.gnomad_af).toExponential(2) : <span className="text-red-400">missing</span>}</dd>
            <dt className="text-slate-500">ClinVar</dt>
            <dd>{data.variant.clinvar_significance || <span className="text-red-400">missing</span>}</dd>
            <dt className="text-slate-500">MANE Select</dt>
            <dd className="font-mono text-xs">{data.variant.mane_select || "—"}</dd>
          </dl>
        </section>

        {/* Missing evidence warning */}
        {missingEvidence.length > 0 && (
          <section className="bg-amber-950 border border-amber-900 rounded-lg p-4">
            <div className="text-amber-300 text-xs font-semibold mb-2">⚠ Missing evidence for classification</div>
            <ul className="text-xs text-amber-200 space-y-1">
              {missingEvidence.map((m) => <li key={m}>• {m}</li>)}
            </ul>
            <p className="text-xs text-amber-400 mt-2">
              Variants with missing evidence default to VUS. Annotate this sample or add criteria manually.
            </p>
          </section>
        )}

        {/* Criteria fired */}
        <section>
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-xs uppercase tracking-wide text-slate-400">Criteria Fired ({fired.length})</h3>
            <button
              onClick={() => setShowAdd((v) => !v)}
              className="text-xs text-emerald-400 hover:underline"
            >
              {showAdd ? "Cancel" : "+ Add criterion"}
            </button>
          </div>

          {showAdd && (
            <div className="bg-slate-900 border border-slate-800 rounded-lg p-2 mb-3 max-h-60 overflow-y-auto">
              {catalog
                .filter((c) => !fired.some((f) => f.code === c.code))
                .sort((a, b) => WEIGHT_ORDER[a.weight] - WEIGHT_ORDER[b.weight])
                .map((c) => (
                  <button
                    key={c.code}
                    onClick={() => addCriterion(c.code)}
                    className="w-full text-left px-2 py-2 hover:bg-slate-800 rounded text-xs"
                  >
                    <div className="flex items-center gap-2">
                      <span className="font-mono font-bold text-emerald-400">{c.code}</span>
                      <span className={`text-[10px] px-1.5 py-0.5 rounded ${
                        c.category === "pathogenic" ? "bg-red-900 text-red-300" : "bg-emerald-900 text-emerald-300"
                      }`}>{c.category}</span>
                      <span className="text-slate-500">{c.weight}</span>
                    </div>
                    <div className="text-slate-400 mt-1">{c.desc}</div>
                  </button>
                ))}
            </div>
          )}

          {fired.length === 0 && (
            <p className="text-xs text-slate-500 italic">No criteria fired. Result is VUS by default.</p>
          )}

          <div className="space-y-2">
            {fired.map((c) => {
              const meta = catalog.find((x) => x.code === c.code);
              return (
                <div key={c.code} className="bg-slate-900 border border-slate-800 rounded-lg p-3">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-bold text-emerald-400">{c.code}</span>
                        <span className={`text-[10px] px-1.5 py-0.5 rounded ${
                          meta?.category === "pathogenic" ? "bg-red-900 text-red-300" :
                          meta?.category === "benign" ? "bg-emerald-900 text-emerald-300" :
                          "bg-slate-800 text-slate-400"
                        }`}>{meta?.weight || "—"}</span>
                        {c.source === "auto" && (
                          <span className="text-[10px] text-slate-500">auto</span>
                        )}
                        {c.source === "manual" && (
                          <span className="text-[10px] text-blue-400">manual</span>
                        )}
                      </div>
                      <div className="text-xs text-slate-400 mt-1">{c.evidence}</div>
                    </div>
                    <button
                      onClick={() => removeCriterion(c.code)}
                      className="text-slate-500 hover:text-red-400 text-sm"
                    >
                      ×
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </section>

        {/* Suggestions */}
        {data.suggestions?.length > 0 && (
          <section>
            <h3 className="text-xs uppercase tracking-wide text-slate-400 mb-2">
              What would change this
            </h3>
            <ul className="text-xs text-slate-400 space-y-1">
              {data.suggestions.map((s: string, i: number) => (
                <li key={i}>• {s}</li>
              ))}
            </ul>
          </section>
        )}

        {/* Notes */}
        <section>
          <h3 className="text-xs uppercase tracking-wide text-slate-400 mb-2">Reviewer notes</h3>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Add clinical context, segregation data, or rationale..."
            rows={3}
            className="w-full bg-slate-900 border border-slate-800 rounded px-3 py-2 text-sm"
          />
        </section>

        {error && <p className="text-red-400 text-xs">{error}</p>}

        <button
          onClick={save}
          disabled={saving}
          className="w-full bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 py-3 rounded text-sm font-medium"
        >
          {saving ? "Saving..." : "Save Classification"}
        </button>
      </div>
    </div>
  );
}
