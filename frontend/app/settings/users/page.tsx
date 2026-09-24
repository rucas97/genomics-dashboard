"use client";
import { useEffect, useState } from "react";
import { isLocal } from "@/lib/mode";
import { apiFetch } from "@/lib/api";

const ROLES = ["admin", "analyst", "viewer"];

export default function LocalUsersPage() {
  const [users, setUsers] = useState<any[]>([]);
  const [me, setMe] = useState<any>(null);
  const [form, setForm] = useState({ email: "", password: "", name: "", role: "analyst" });
  const [showAdd, setShowAdd] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function load() {
    apiFetch("/local-auth/me").then(setMe).catch((e) => setError(e.message));
    apiFetch("/local-auth/users").then(setUsers).catch((e) => setError(e.message));
  }

  useEffect(() => { load(); }, []);

  async function addUser() {
    setBusy(true);
    setError(null);
    try {
      await apiFetch("/local-auth/users", {
        method: "POST",
        body: JSON.stringify(form),
      });
      setForm({ email: "", password: "", name: "", role: "analyst" });
      setShowAdd(false);
      load();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function changeRole(userId: string, role: string) {
    try {
      await apiFetch(`/local-auth/users/${userId}/role?role=${role}`, { method: "PUT" });
      load();
    } catch (e: any) {
      setError(e.message);
    }
  }

  async function removeUser(userId: string) {
    if (!confirm("Remove this user? Their samples and data will be deleted.")) return;
    try {
      await apiFetch(`/local-auth/users/${userId}`, { method: "DELETE" });
      load();
    } catch (e: any) {
      setError(e.message);
    }
  }

  if (!isLocal) {
    return (
      <div className="text-slate-500">
        Local user management is only available in local (desktop) mode.
      </div>
    );
  }

  return (
    <div className="max-w-3xl space-y-6">
      {error && <div className="bg-red-950 border border-red-900 text-red-300 rounded p-3 text-sm">{error}</div>}

      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Local Users ({users.length})</h2>
        <button
          onClick={() => setShowAdd((v) => !v)}
          className="bg-emerald-600 hover:bg-emerald-500 px-4 py-2 rounded text-sm font-medium"
        >
          {showAdd ? "Cancel" : "Add User"}
        </button>
      </div>

      {showAdd && (
        <div className="bg-slate-900 rounded-lg border border-slate-800 p-6 space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-slate-500 block mb-1">Email</label>
              <input
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="text-xs text-slate-500 block mb-1">Name</label>
              <input
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="text-xs text-slate-500 block mb-1">Password</label>
              <input
                type="password"
                value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
                className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="text-xs text-slate-500 block mb-1">Role</label>
              <select
                value={form.role}
                onChange={(e) => setForm({ ...form, role: e.target.value })}
                className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-sm"
              >
                {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
              </select>
            </div>
          </div>
          <button
            onClick={addUser}
            disabled={busy || !form.email || !form.password}
            className="bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 px-4 py-2 rounded text-sm"
          >
            {busy ? "Creating..." : "Create User"}
          </button>
        </div>
      )}

      <div className="bg-slate-900 rounded-lg border border-slate-800 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-800 text-slate-400 text-left">
            <tr>
              <th className="p-3">Email</th>
              <th className="p-3">Name</th>
              <th className="p-3">Role</th>
              <th className="p-3">Last login</th>
              <th className="p-3"></th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id} className="border-t border-slate-800">
                <td className="p-3">{u.email}</td>
                <td className="p-3">{u.name || "—"}</td>
                <td className="p-3">
                  {me?.role === "admin" && u.id !== me.id ? (
                    <select
                      value={u.role}
                      onChange={(e) => changeRole(u.id, e.target.value)}
                      className="bg-slate-950 border border-slate-800 rounded px-2 py-1 text-xs"
                    >
                      {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
                    </select>
                  ) : (
                    <span className="text-xs px-2 py-0.5 bg-slate-800 rounded">{u.role}</span>
                  )}
                </td>
                <td className="p-3 text-slate-500 text-xs">{u.last_login || "never"}</td>
                <td className="p-3 text-right">
                  {me?.role === "admin" && u.id !== me.id && (
                    <button
                      onClick={() => removeUser(u.id)}
                      className="text-xs text-red-400 hover:underline"
                    >
                      Remove
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
