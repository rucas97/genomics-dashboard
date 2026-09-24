"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import {
  LayoutDashboard, FlaskConical, Dna, Users, PlayCircle,
  FileText, Shield, LogOut, Settings as SettingsIcon, WifiOff, Wifi,
} from "lucide-react";
import { isLocal, clearLocalToken, clearLocalUser } from "@/lib/mode";
import { supabase } from "@/lib/supabase";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const clinicalNav = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/samples", label: "Samples", icon: FlaskConical },
  { href: "/variants", label: "Variant Workbench", icon: Dna },
  { href: "/reports", label: "Reports", icon: FileText },
];

const researchNav = [
  { href: "/cohorts", label: "Cohorts & PCA", icon: Users },
  { href: "/pipelines", label: "Pipelines", icon: PlayCircle },
];

const adminNav = [
  { href: "/audit", label: "Audit Log", icon: Shield },
  { href: "/settings", label: "Settings", icon: SettingsIcon },
];

export default function Sidebar() {
  const path = usePathname();
  const router = useRouter();
  const [offline, setOffline] = useState<boolean | null>(null);

  useEffect(() => {
    fetch(`${API_URL}/health`)
      .then((r) => r.json())
      .then((d) => setOffline(d.offline))
      .catch(() => setOffline(null));
  }, []);

  async function logout() {
    if (isLocal) {
      clearLocalToken();
      clearLocalUser();
      document.cookie = "genomicsops_local_token=; path=/; max-age=0";
    } else {
      await supabase.auth.signOut();
    }
    router.push("/login");
  }

  function NavLink({ href, label, icon: Icon }: any) {
    const active = path === href || path.startsWith(href + "/");
    return (
      <Link
        href={href}
        className={`flex items-center gap-3 px-3 py-2 rounded-md text-sm transition ${
          active ? "bg-slate-800 text-emerald-400" : "hover:bg-slate-900 text-slate-300"
        }`}
      >
        <Icon size={16} /> {label}
      </Link>
    );
  }

  return (
    <aside className="w-60 border-r border-slate-800 flex flex-col">
      <div className="p-4 border-b border-slate-800">
        <h1 className="text-lg font-bold text-emerald-400">GenomicsOps</h1>
        <div className="text-[10px] text-amber-500 uppercase tracking-wider mt-1">
          Research Use Only
        </div>
        {offline !== null && (
          <div
            className={`flex items-center gap-1.5 mt-2 text-[10px] uppercase tracking-wider ${
              offline ? "text-red-400" : "text-emerald-500"
            }`}
          >
            {offline ? <WifiOff size={10} /> : <Wifi size={10} />}
            {offline ? "Offline · Network blocked" : "Online"}
          </div>
        )}
      </div>

      <nav className="flex-1 p-3 space-y-4 overflow-y-auto">
        <div>
          <div className="text-[10px] uppercase tracking-wider text-slate-500 px-3 mb-1">Clinical</div>
          <div className="space-y-1">{clinicalNav.map((n) => <NavLink key={n.href} {...n} />)}</div>
        </div>
        <div>
          <div className="text-[10px] uppercase tracking-wider text-slate-500 px-3 mb-1">Research</div>
          <div className="space-y-1">{researchNav.map((n) => <NavLink key={n.href} {...n} />)}</div>
        </div>
        <div>
          <div className="text-[10px] uppercase tracking-wider text-slate-500 px-3 mb-1">Admin</div>
          <div className="space-y-1">{adminNav.map((n) => <NavLink key={n.href} {...n} />)}</div>
        </div>
      </nav>

      <button
        onClick={logout}
        className="flex items-center gap-3 px-3 py-3 mx-3 mb-3 rounded-md text-sm text-slate-400 hover:bg-slate-900 border-t border-slate-800"
      >
        <LogOut size={16} /> Sign out
      </button>
    </aside>
  );
}
