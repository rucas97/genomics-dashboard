"use client";
import { useEffect, useState } from "react";
import Sidebar from "@/components/Sidebar";
import { apiFetch } from "@/lib/api";

export default function AuditLog() {
  const [logs, setLogs] = useState<any[]>([]);
  useEffect(() => { apiFetch("/audit/").then(setLogs).catch(console.error); }, []);
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 p-8">
        <h1 className="text-2xl font-bold mb-6">Audit Log</h1>
        <div className="bg-slate-900 rounded-lg border border-slate-800">
          {logs.map((l) => (
            <div key={l.id} className="flex justify-between px-4 py-3 border-b border-slate-800 last:border-0 text-sm">
              <div>
                <span className="text-emerald-400 font-medium">{l.action}</span>
                {l.resource_type && <span className="text-slate-500 ml-2">{l.resource_type} {l.resource_id?.slice(0, 8)}</span>}
              </div>
              <span className="text-slate-500">{new Date(l.created_at).toLocaleString()}</span>
            </div>
          ))}
          {logs.length === 0 && <div className="p-6 text-slate-500">No activity yet.</div>}
        </div>
      </main>
    </div>
  );
}
