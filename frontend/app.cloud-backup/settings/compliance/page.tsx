"use client";
import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";

export default function CompliancePage() {
  const [me, setMe] = useState<any>(null);
  const [runs, setRuns] = useState<any[]>([]);
  const [consent, setConsent] = useState<any[]>([]);
  const [retention, setRetention] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  function load() {
    apiFetch("/orgs/me").then(setMe).catch((e) => setError(e.message));
    apiFetch("/compliance/retention/runs").then(setRuns).catch(() => {});
    apiFetch("/compliance/consent").then(setConsent).catch(() => {});
  }

  useEffect(() => {
    load();
  }, []);

  async function runRetention(dryRun: boolean) {
    if (
      !dryRun &&
      !confirm(
        "This will permanently delete samples past their retention window. Continue?"
      )
    )
      return;
    setBusy(true);
    setMessage(null);
    setError(null);
    try {
      const res = await apiFetch("/compliance/retention/run", {
        method: "POST",
        body: JSON.stringify({ dry_run: dryRun }),
      });
      setRetention(res);
      setMessage(
        dryRun
          ? `Dry run: would delete ${res.deleted} samples, retain ${res.retained}.`
          : `Retention run complete: ${res.deleted} deleted, ${res.retained} retained.`
      );
      load();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  if (!me && !error) return <p className="text-slate-500">Loading...</p>;
  if (error && !me) return <p className="text-red-400">{error}</p>;

  const isAdmin = ["owner", "admin"].includes(me.role);

  return (
    <div className="max-w-4xl space-y-6">
      {message && (
        <div className="bg-emerald-950 border border-emerald-800 text-emerald-300 rounded p-3 text-sm">
          {message}
        </div>
      )}
      {error && (
        <div className="bg-red-950 border border-red-900 text-red-300 rounded p-3 text-sm">
          {error}
        </div>
      )}

      <div className="bg-slate-900 rounded-lg border border-slate-800 p-6">
        <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wide mb-4">
          Data Retention
        </h2>
        <p className="text-sm text-slate-400 mb-4">
          Samples older than the org&apos;s retention policy (
          {me.org.data_retention_days} days) are eligible for deletion.
          Legal holds are always respected.
        </p>
        {isAdmin && (
          <div className="flex gap-2">
            <button
              onClick={() => runRetention(true)}
              disabled={busy}
              className="bg-slate-800 hover:bg-slate-700 disabled:opacity-50 px-4 py-2 rounded text-sm"
            >
              {busy ? "..." : "Dry Run"}
            </button>
            <button
              onClick={() => runRetention(false)}
              disabled={busy}
              className="bg-red-900 hover:bg-red-800 disabled:opacity-50 px-4 py-2 rounded text-sm"
            >
              {busy ? "..." : "Run Retention Now"}
            </button>
          </div>
        )}
        {!isAdmin && (
          <p className="text-xs text-slate-500">
            Only admins and owners can run retention.
          </p>
        )}
      </div>

      {runs.length > 0 && (
        <div className="bg-slate-900 rounded-lg border border-slate-800 p-6">
          <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wide mb-4">
            Recent Retention Runs
          </h2>
          <table className="w-full text-sm">
            <thead className="text-slate-500 text-left">
              <tr>
                <th className="pb-2">When</th>
                <th className="pb-2">Deleted</th>
                <th className="pb-2">Retained</th>
                <th className="pb-2">Legal holds</th>
                <th className="pb-2">Notes</th>
              </tr>
            </thead>
            <tbody>
              {runs.slice(0, 10).map((r) => (
                <tr key={r.id} className="border-t border-slate-800">
                  <td className="py-2 text-xs text-slate-500">
                    {new Date(r.run_at).toLocaleString()}
                  </td>
                  <td className="py-2">{r.samples_deleted ?? 0}</td>
                  <td className="py-2">{r.samples_retained ?? 0}</td>
                  <td className="py-2">{r.legal_holds_skipped ?? 0}</td>
                  <td className="py-2 text-xs text-slate-500">{r.notes || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="bg-slate-900 rounded-lg border border-slate-800 p-6">
        <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wide mb-4">
          Consent Records ({consent.length})
        </h2>
        {consent.length === 0 ? (
          <p className="text-sm text-slate-500">
            No consent records. Consent can be recorded per sample via the API
            (<code className="text-xs bg-slate-800 px-1 rounded">POST /compliance/consent</code>).
          </p>
        ) : (
          <table className="w-full text-sm">
            <thead className="text-slate-500 text-left">
              <tr>
                <th className="pb-2">Subject</th>
                <th className="pb-2">Type</th>
                <th className="pb-2">Granted</th>
                <th className="pb-2">Status</th>
              </tr>
            </thead>
            <tbody>
              {consent.slice(0, 20).map((c) => (
                <tr key={c.id} className="border-t border-slate-800">
                  <td className="py-2 text-xs">{c.subject_id || "—"}</td>
                  <td className="py-2 text-xs">{c.consent_type}</td>
                  <td className="py-2 text-xs text-slate-500">
                    {new Date(c.granted_at).toLocaleDateString()}
                  </td>
                  <td className="py-2">
                    <span
                      className={`text-xs px-2 py-0.5 rounded ${
                        c.granted && !c.revoked_at
                          ? "bg-emerald-900 text-emerald-300"
                          : "bg-red-900 text-red-300"
                      }`}
                    >
                      {c.granted && !c.revoked_at ? "active" : "revoked"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="bg-slate-900 rounded-lg border border-slate-800 p-6">
        <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wide mb-4">
          GDPR Right to Erasure
        </h2>
        <p className="text-sm text-slate-400 mb-4">
          Delete all data associated with a sample (variants, QC, reports, storage files)
          in one operation. Samples under legal hold are protected.
        </p>
        <p className="text-xs text-slate-500">
          Use{" "}
          <code className="bg-slate-800 px-1 rounded">
            POST /compliance/erase/sample/&#123;id&#125;
          </code>{" "}
          from the API or via a sample detail page action (coming next).
        </p>
      </div>
    </div>
  );
}
