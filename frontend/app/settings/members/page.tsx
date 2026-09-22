"use client";
import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";

const ROLES = ["admin", "analyst", "viewer"];

export default function MembersPage() {
  const [me, setMe] = useState<any>(null);
  const [members, setMembers] = useState<any[]>([]);
  const [invitations, setInvitations] = useState<any[]>([]);
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("analyst");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  function load() {
    apiFetch("/orgs/me").then(setMe).catch((e) => setError(e.message));
    apiFetch("/orgs/me/members").then(setMembers).catch(() => {});
    apiFetch("/orgs/me/invitations").then(setInvitations).catch(() => {});
  }

  useEffect(() => {
    load();
  }, []);

  async function invite() {
    if (!email) return;
    setBusy(true);
    setError(null);
    try {
      await apiFetch("/orgs/me/invitations", {
        method: "POST",
        body: JSON.stringify({ email: email.trim(), role }),
      });
      setEmail("");
      load();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function revoke(id: string) {
    try {
      await apiFetch(`/orgs/me/invitations/${id}`, { method: "DELETE" });
      load();
    } catch (e: any) {
      setError(e.message);
    }
  }

  async function changeRole(userId: string, newRole: string) {
    try {
      await apiFetch(`/orgs/me/members/${userId}/role`, {
        method: "PUT",
        body: JSON.stringify({ role: newRole }),
      });
      load();
    } catch (e: any) {
      setError(e.message);
    }
  }

  async function remove(userId: string) {
    if (!confirm("Remove this member from the organization?")) return;
    try {
      await apiFetch(`/orgs/me/members/${userId}`, { method: "DELETE" });
      load();
    } catch (e: any) {
      setError(e.message);
    }
  }

  if (!me && !error) return <p className="text-slate-500">Loading...</p>;
  if (error && !me) return <p className="text-red-400">{error}</p>;

  const isAdmin = ["owner", "admin"].includes(me.role);

  return (
    <div className="max-w-4xl space-y-6">
      {error && (
        <div className="bg-red-950 border border-red-900 text-red-300 rounded p-3 text-sm">
          {error}
        </div>
      )}

      {isAdmin && (
        <div className="bg-slate-900 rounded-lg border border-slate-800 p-6">
          <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wide mb-4">
            Invite a Member
          </h2>
          <div className="flex gap-2">
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="colleague@lab.org"
              className="flex-1 bg-slate-950 border border-slate-800 rounded px-3 py-2 text-sm"
            />
            <select
              value={role}
              onChange={(e) => setRole(e.target.value)}
              className="bg-slate-950 border border-slate-800 rounded px-3 py-2 text-sm"
            >
              {ROLES.map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </select>
            <button
              onClick={invite}
              disabled={busy || !email}
              className="bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 px-4 py-2 rounded text-sm font-medium"
            >
              {busy ? "..." : "Invite"}
            </button>
          </div>
          <p className="text-xs text-slate-500 mt-2">
            Invitations expire after 14 days. The user accepts with a token after signing in.
          </p>
        </div>
      )}

      <div className="bg-slate-900 rounded-lg border border-slate-800 p-6">
        <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wide mb-4">
          Members ({members.length})
        </h2>
        <table className="w-full text-sm">
          <thead className="text-slate-500 text-left">
            <tr>
              <th className="pb-2">Email</th>
              <th className="pb-2">Role</th>
              <th className="pb-2">Status</th>
              <th className="pb-2"></th>
            </tr>
          </thead>
          <tbody>
            {members.map((m) => {
              const profile = m.profiles || {};
              return (
                <tr key={m.id} className="border-t border-slate-800">
                  <td className="py-2">{profile.email || m.user_id?.slice(0, 8)}</td>
                  <td className="py-2">
                    {isAdmin && m.role !== "owner" ? (
                      <select
                        value={m.role}
                        onChange={(e) => changeRole(m.user_id, e.target.value)}
                        className="bg-slate-950 border border-slate-800 rounded px-2 py-1 text-xs"
                      >
                        {ROLES.map((r) => (
                          <option key={r} value={r}>
                            {r}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <span className="text-xs px-2 py-0.5 bg-slate-800 rounded">
                        {m.role}
                      </span>
                    )}
                  </td>
                  <td className="py-2">
                    <span
                      className={`text-xs px-2 py-0.5 rounded ${
                        m.status === "active"
                          ? "bg-emerald-900 text-emerald-300"
                          : "bg-slate-800"
                      }`}
                    >
                      {m.status}
                    </span>
                  </td>
                  <td className="py-2 text-right">
                    {isAdmin && m.role !== "owner" && (
                      <button
                        onClick={() => remove(m.user_id)}
                        className="text-xs text-red-400 hover:underline"
                      >
                        Remove
                      </button>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {isAdmin && invitations.length > 0 && (
        <div className="bg-slate-900 rounded-lg border border-slate-800 p-6">
          <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wide mb-4">
            Pending Invitations ({invitations.length})
          </h2>
          <table className="w-full text-sm">
            <thead className="text-slate-500 text-left">
              <tr>
                <th className="pb-2">Email</th>
                <th className="pb-2">Role</th>
                <th className="pb-2">Expires</th>
                <th className="pb-2"></th>
              </tr>
            </thead>
            <tbody>
              {invitations.map((inv) => (
                <tr key={inv.id} className="border-t border-slate-800">
                  <td className="py-2">{inv.email}</td>
                  <td className="py-2 text-xs">{inv.role}</td>
                  <td className="py-2 text-xs text-slate-500">
                    {inv.expires_at
                      ? new Date(inv.expires_at).toLocaleDateString()
                      : "—"}
                  </td>
                  <td className="py-2 text-right">
                    <button
                      onClick={() => revoke(inv.id)}
                      className="text-xs text-red-400 hover:underline"
                    >
                      Revoke
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
