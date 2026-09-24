"use client";
import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";

export default function OrgSettings() {
  const [data, setData] = useState<any>(null);
  const [form, setForm] = useState<any>({});
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiFetch("/orgs/me")
      .then((res) => {
        setData(res);
        setForm({
          name: res.org.name || "",
          hipaa_enabled: res.org.hipaa_enabled || false,
          gdpr_enabled: res.org.gdpr_enabled || false,
          data_retention_days: res.org.data_retention_days || 365,
          billing_email: res.org.billing_email || "",
          technical_contact: res.org.technical_contact || "",
        });
      })
      .catch((e) => setError(e.message));
  }, []);

  async function save() {
    setSaving(true);
    setMessage(null);
    setError(null);
    try {
      await apiFetch("/orgs/me/settings", {
        method: "PUT",
        body: JSON.stringify(form),
      });
      setMessage("Settings saved.");
      setData(await apiFetch("/orgs/me"));
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  }

  if (!data && !error) return <p className="text-slate-500">Loading...</p>;
  if (error && !data) return <p className="text-red-400">{error}</p>;

  const isAdmin = ["owner", "admin"].includes(data.role);

  return (
    <div className="max-w-3xl space-y-6">
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
          Organization
        </h2>
        <div className="space-y-4">
          <div>
            <label className="text-xs text-slate-500 block mb-1">Name</label>
            <input
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              disabled={!isAdmin}
              className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-sm disabled:opacity-50"
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs text-slate-500 block mb-1">Slug</label>
              <input
                value={data.org.slug}
                disabled
                className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-sm text-slate-500"
              />
            </div>
            <div>
              <label className="text-xs text-slate-500 block mb-1">Plan</label>
              <input
                value={data.org.plan}
                disabled
                className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-sm text-slate-500"
              />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs text-slate-500 block mb-1">Billing email</label>
              <input
                value={form.billing_email}
                onChange={(e) => setForm({ ...form, billing_email: e.target.value })}
                disabled={!isAdmin}
                className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-sm disabled:opacity-50"
              />
            </div>
            <div>
              <label className="text-xs text-slate-500 block mb-1">Technical contact</label>
              <input
                value={form.technical_contact}
                onChange={(e) => setForm({ ...form, technical_contact: e.target.value })}
                disabled={!isAdmin}
                className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-sm disabled:opacity-50"
              />
            </div>
          </div>
        </div>
      </div>

      <div className="bg-slate-900 rounded-lg border border-slate-800 p-6">
        <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wide mb-4">
          Compliance
        </h2>
        <div className="space-y-4">
          <label className="flex items-start gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={form.hipaa_enabled}
              onChange={(e) => setForm({ ...form, hipaa_enabled: e.target.checked })}
              disabled={!isAdmin}
              className="mt-1 rounded"
            />
            <div>
              <div className="text-sm">HIPAA mode</div>
              <div className="text-xs text-slate-500">
                Enable HIPAA-required audit and retention settings
              </div>
            </div>
          </label>
          <label className="flex items-start gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={form.gdpr_enabled}
              onChange={(e) => setForm({ ...form, gdpr_enabled: e.target.checked })}
              disabled={!isAdmin}
              className="mt-1 rounded"
            />
            <div>
              <div className="text-sm">GDPR mode</div>
              <div className="text-xs text-slate-500">
                Enable right-to-erasure and consent tracking
              </div>
            </div>
          </label>
          <div>
            <label className="text-xs text-slate-500 block mb-1">
              Default data retention (days)
            </label>
            <input
              type="number"
              value={form.data_retention_days}
              onChange={(e) =>
                setForm({ ...form, data_retention_days: parseInt(e.target.value) || 365 })
              }
              disabled={!isAdmin}
              className="w-40 bg-slate-950 border border-slate-800 rounded px-3 py-2 text-sm disabled:opacity-50"
            />
            <p className="text-xs text-slate-500 mt-1">
              Samples older than this are eligible for automatic deletion.
            </p>
          </div>
        </div>
      </div>

      {isAdmin && (
        <button
          onClick={save}
          disabled={saving}
          className="bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 px-6 py-2 rounded text-sm font-medium"
        >
          {saving ? "Saving..." : "Save Changes"}
        </button>
      )}
      {!isAdmin && (
        <p className="text-xs text-slate-500">
          Only admins and owners can edit these settings.
        </p>
      )}
    </div>
  );
}
