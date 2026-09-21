"use client";
import { useEffect, useState } from "react";
import Sidebar from "@/components/Sidebar";
import { apiFetch } from "@/lib/api";

export default function Reports() {
  const [items, setItems] = useState<any[]>([]);
  useEffect(() => { apiFetch("/reports/").then(setItems).catch(console.error); }, []);
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 p-8">
        <h1 className="text-2xl font-bold mb-6">Reports</h1>
        <div className="bg-slate-900 rounded-lg border border-slate-800 p-6 text-slate-500">
          {items.length === 0 ? "Nothing here yet. This module is coming next." : `${items.length} items`}
        </div>
      </main>
    </div>
  );
}
