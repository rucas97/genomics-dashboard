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
  very_strong: 0, strong: 1, moderate: 2, supporting: 3, standalone: -1,
};

type Tab = "classify" | "simulate" | "explain";

export default function ACMGPanel({ variantId, onClose }: { variantId: string; onClose: () => void }) {
  const [data, setData] = useState<any>(null);
  const [catalog, setCatalog] = useState<any[]>([]);
  const [fired, setFired] = useState<any[]>([]);
  const [simulated, setSimulated] = useState<any>(null);
  const [explanation, setExplanation] = useState<any>(null);
  const [notes, setNotes] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showAdd, setShowAdd] = useState(false);
  const [tab, setTab] = useState<Tab>("classify");

  useEffect(() => {
    apiFetch("/acmg/criteria").then(setCatalog).catch(() => {});
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
    apiFetch(`/acmg/explain/${variantId}`).then(setExplanation).catch(() => {});
  }, [variantId]);

  useEffect(() => {
    if (!variantId || fired.length === 0) {
      setSimulated(null);
      return;
    }
    apiFetch(`/acmg/variant/${variantId}/simulate`, {
      method: "POST",
      body: JSON.stringify({ criteria_fired: fired }),
    }).then(setSimulated).catch(() => {});
  }, [fired, variantId]);

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

  function revert() {
    if (data?.acmg) setFired(data.acmg.criteria_fired || []);
  }

  if (!data && !error) return <PanelShell onClose={onClose}><p className="text-slate-500">Loading...</p></PanelShell>;
  if (error && !data) return <PanelShell onClose={onClose}><p className="text-red-400">{error}</p></PanelShell>;

  const cls = data.acmg.classification;
  const clsColor = CLASS_COLORS[cls] || "bg-slate-800 text-slate-300 border-slate-700";
  const dirty = JSON.stringify(fired.map(c => c.code).sort()) !== JSON.stringify((data.acmg.criteria_fired || []).map((c: any) => c.code).sort());
  const simChanged = simulated && simulated.changed;

  const missingEvidence = [];
  if (!data.variant.gene) missingEvidence.push("Gene annotation");
  if (!data.variant.consequence) missingEvidence.push("Consequence");
  if (!data.variant.impact) missingEvidence.push("Impact");
  if (data.variant.gnomad_af == null) missingEvidence.push("Population frequency (gnomAD)");
  if (!data.variant.clinvar_significance) missingEvidence.push("ClinVar record");

  return (
    <div className="fixed inset-y-0 right-0 w-[560px] bg-slate-950 border-l border-slate-800 overflow-y-auto z-50 flex flex-col">
      {/* Header */}
      <div className="sticky top-0 bg-slate-950 border-b border-slate-800 z-10">
        <div className="p-6 pb-3">
          <div className="flex items-start justify-between mb-3">
            <div>
              <h2 className="text-lg font-bold">ACMG Workbench</h2>
              <p className="text-xs text-slate-500 font-mono mt-1">
                {data.variant.chrom}:{data.variant.pos} {data.variant.ref}/{data.variant.alt}
              </p>
            </div>
            <button onClick={onClose} className="text-slate-400 hover:text-slate-100 text-xl leading-none">×</button>
          </div>

          {/* Classification badges */}
          <div className="flex items-stretch gap-2">
            <div className={`flex-1 border rounded-lg p-3 ${clsColor}`}>
              <div className="text-[10px] uppercase tracking-wide opacity-80">Stored</div>
              <div className="text-lg font-bold">{cls}</div>
              <div className="text-[10px] opacity-80">Confidence: {data.acmg.confidence || "—"}</div>
            </div>
            {simChanged && simulated && (
              <div className={`flex-1 border rounded-lg p-3 ${CLASS_COLORS[simulated.simulated_classification] || ""}`}>
                <div className="text-[10px] uppercase tracking-wide opacity-80">Simulated</div>
                <div className="text-lg font-bold">{simulated.simulated_classification}</div>
                <div className="text-[10px] opacity-80">
                  {simulated.criteria_added.length > 0 && `+${simulated.criteria_added.join(", ")} `}
                  {simulated.criteria_removed.length > 0 && `−${simulated.criteria_removed.join(", ")}`}
                </div>
              </div>
            )}
          </div>

          {/* Tabs */}
          <div className="flex gap-1 mt-4">
            {(["classify", "simulate", "explain"] as Tab[]).map((t) => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={`px-3 py-1.5 text-xs rounded-t border-b-2 transition ${
                  tab === t
                    ? "border-emerald-500 text-emerald-400"
                    : "border-transparent text-slate-400 hover:text-slate-200"
                }`}
              >
                {t === "classify" ? "Criteria" : t === "simulate" ? "What-if" : "Explanation"}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="flex-1 p-6 space-y-6">
        {/* Variant details — always visible */}
        <section>
          <h3 className="text-[10px] uppercase tracking-wider text-slate-500 mb-2">Variant Details</h3>
          <dl className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-sm">
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

        {missingEvidence.length > 0 && (
          <section className="bg-amber-950 border border-amber-900 rounded-lg p-3">
            <div className="text-amber-300 text-xs font-semibold mb-1">⚠ Missing evidence</div>
            <div className="text-xs text-amber-200">{missingEvidence.join(" · ")}</div>
          </section>
        )}

        {/* Tab: Criteria editing */}
        {tab === "classify" && (
          <>
            <section>
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-[10px] uppercase tracking-wider text-slate-500">
                  Criteria Fired ({fired.length})
                </h3>
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
                            <span className="text-[10px] text-slate-500">{c.source}</span>
                          </div>
                          <div className="text-xs text-slate-400 mt-1">{c.evidence}</div>
                        </div>
                        <button onClick={() => removeCriterion(c.code)} className="text-slate-500 hover:text-red-400">×</button>
                      </div>
                    </div>
                  );
                })}
                {fired.length === 0 && (
                  <p className="text-xs text-slate-500 italic">No criteria fired. Result is VUS by default.</p>
                )}
              </div>
            </section>

            <section>
              <h3 className="text-[10px] uppercase tracking-wider text-slate-500 mb-2">Reviewer notes</h3>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Clinical context, segregation data, rationale..."
                rows={3}
                className="w-full bg-slate-900 border border-slate-800 rounded px-3 py-2 text-sm"
              />
            </section>

            {error && <p className="text-red-400 text-xs">{error}</p>}
          </>
        )}

        {/* Tab: What-if simulator */}
        {tab === "simulate" && (
          <section>
            <h3 className="text-[10px] uppercase tracking-wider text-slate-500 mb-2">
              What-if simulator
            </h3>
            <p className="text-xs text-slate-500 mb-4">
              Add or remove criteria on the Criteria tab. The Simulated badge above updates live. Save to commit the change.
            </p>

            {simulated && (
              <div className="space-y-3">
                <div className="bg-slate-900 border border-slate-800 rounded-lg p-4">
                  <div className="text-[10px] uppercase tracking-wide text-slate-500 mb-1">Result</div>
                  <div className="text-sm">
                    <span className="text-slate-400">Stored: </span>
                    <span className="font-semibold">{simulated.stored_classification}</span>
                  </div>
                  <div className="text-sm mt-1">
                    <span className="text-slate-400">Simulated: </span>
                    <span className={`font-semibold ${simulated.changed ? "text-emerald-400" : ""}`}>
                      {simulated.simulated_classification}
                    </span>
                  </div>
                  {simulated.changed && (
                    <div className="mt-2 text-xs text-emerald-400">
                      ✓ This would change the classification
                    </div>
                  )}
                  {!simulated.changed && (
                    <div className="mt-2 text-xs text-slate-500">
                      No change from the stored classification
                    </div>
                  )}
                </div>

                {(simulated.criteria_added.length > 0 || simulated.criteria_removed.length > 0) && (
                  <div className="bg-slate-900 border border-slate-800 rounded-lg p-4 text-xs">
                    {simulated.criteria_added.length > 0 && (
                      <div className="text-emerald-400 mb-1">
                        + Added: {simulated.criteria_added.join(", ")}
                      </div>
                    )}
                    {simulated.criteria_removed.length > 0 && (
                      <div className="text-red-400">
                        − Removed: {simulated.criteria_removed.join(", ")}
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            {explanation?.upgrade_paths?.length > 0 && (
              <div className="mt-6">
                <h4 className="text-[10px] uppercase tracking-wider text-slate-500 mb-2">
                  Single-criterion upgrades
                </h4>
                <div className="space-y-2">
                  {explanation.upgrade_paths.map((u: any, i: number) => (
                    <button
                      key={i}
                      onClick={() => addCriterion(u.add_criterion)}
                      className="w-full text-left bg-slate-900 border border-slate-800 hover:border-emerald-700 rounded-lg p-3 text-xs transition"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-mono font-bold text-emerald-400">
                          + {u.add_criterion}
                        </span>
                        <span className="text-slate-400">→ {u.would_become}</span>
                      </div>
                      <div className="text-slate-500 mt-1">{u.description}</div>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </section>
        )}

        {/* Tab: Explanation */}
        {tab === "explain" && explanation && (
          <section className="space-y-4">
            <div>
              <h3 className="text-[10px] uppercase tracking-wider text-slate-500 mb-2">
                Why this classification
              </h3>
              <p className="text-sm text-slate-300">
                {explanation.classification}
                {explanation.confidence && ` · ${explanation.confidence} confidence`}
              </p>
            </div>

            {explanation.supporting_pathogenic.length > 0 && (
              <div>
                <h4 className="text-xs text-red-400 font-semibold mb-2">
                  Supporting pathogenicity ({explanation.supporting_pathogenic.length})
                </h4>
                <div className="space-y-1.5">
                  {explanation.supporting_pathogenic.map((c: any, i: number) => (
                    <div key={i} className="text-xs bg-slate-900 border border-slate-800 rounded p-2">
                      <span className="font-mono font-bold text-red-400">{c.code}</span>
                      <span className="text-slate-500 ml-2">{c.weight}</span>
                      <div className="text-slate-400 mt-1">{c.evidence}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {explanation.supporting_benign.length > 0 && (
              <div>
                <h4 className="text-xs text-emerald-400 font-semibold mb-2">
                  Supporting benign ({explanation.supporting_benign.length})
                </h4>
                <div className="space-y-1.5">
                  {explanation.supporting_benign.map((c: any, i: number) => (
                    <div key={i} className="text-xs bg-slate-900 border border-slate-800 rounded p-2">
                      <span className="font-mono font-bold text-emerald-400">{c.code}</span>
                      <span className="text-slate-500 ml-2">{c.weight}</span>
                      <div className="text-slate-400 mt-1">{c.evidence}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {explanation.missing_evidence.length > 0 && (
              <div>
                <h4 className="text-xs text-amber-400 font-semibold mb-2">
                  Missing evidence
                </h4>
                <ul className="text-xs text-slate-400 space-y-1">
                  {explanation.missing_evidence.map((m: string, i: number) => (
                    <li key={i}>• {m}</li>
                  ))}
                </ul>
              </div>
            )}

            {explanation.upgrade_paths.length > 0 && (
              <div>
                <h4 className="text-xs text-blue-400 font-semibold mb-2">
                  What would change this
                </h4>
                <ul className="text-xs text-slate-400 space-y-1">
                  {explanation.upgrade_paths.map((u: any, i: number) => (
                    <li key={i}>
                      • Adding <span className="font-mono text-blue-400">{u.add_criterion}</span> → {u.would_become}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </section>
        )}
      </div>

      {/* Footer actions */}
      {tab === "classify" && (
        <div className="sticky bottom-0 bg-slate-950 border-t border-slate-800 p-4 flex gap-2">
          {dirty && (
            <button
              onClick={revert}
              className="bg-slate-800 hover:bg-slate-700 px-4 py-2 rounded text-sm"
            >
              Revert
            </button>
          )}
          <button
            onClick={save}
            disabled={saving || !dirty}
            className="flex-1 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 py-2 rounded text-sm font-medium"
          >
            {saving ? "Saving..." : dirty ? "Save Classification" : "No changes"}
          </button>
        </div>
      )}
    </div>
  );
}

function PanelShell({ children, onClose }: any) {
  return (
    <div className="fixed inset-y-0 right-0 w-[560px] bg-slate-950 border-l border-slate-800 p-6 z-50">
      <div className="flex items-start justify-between mb-4">
        <h2 className="text-lg font-bold">ACMG Workbench</h2>
        <button onClick={onClose} className="text-slate-400 hover:text-slate-100 text-xl">×</button>
      </div>
      {children}
    </div>
  );
}
