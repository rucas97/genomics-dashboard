"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  LayoutDashboard, FlaskConical, Dna, Users, PlayCircle,
  FileText, Shield, LogOut, Settings as SettingsIcon,
} from "lucide-react";
import { supabase } from "@/lib/supabase";

const nav = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/samples", label: "Samples", icon: FlaskConical },
  { href: "/variants", label: "Variants", icon: Dna },
  { href: "/cohorts", label: "Cohorts", icon: Users },
  { href: "/pipelines", label: "Pipelines", icon: PlayCircle },
  { href: "/reports", label: "Reports", icon: FileText },
  { href: "/audit", label: "Audit Log", icon: Shield },
  { href: "/settings", label: "Settings", icon: SettingsIcon },
];

export default function Sidebar() {
  const path = usePathname();
  const router = useRouter();

  async function logout() {
    await supabase.auth.signOut();
    router.push("/login");
  }

  return (
    <aside className="w-60 border-r border-slate-800 p-4 flex flex-col">
      <h1 className="text-lg font-bold mb-6 text-emerald-400">GenomicsOps</h1>
      <nav className="space-y-1 flex-1">
        {nav.map(({ href, label, icon: Icon }) => {
          const active = path === href || path.startsWith(href + "/");
          return (
            <Link
              key={href}
              href={href}
              className={`flex items-center gap-3 px-3 py-2 rounded-md text-sm transition ${
                active
                  ? "bg-slate-800 text-emerald-400"
                  : "hover:bg-slate-900 text-slate-300"
              }`}
            >
              <Icon size={16} /> {label}
            </Link>
          );
        })}
      </nav>
      <button
        onClick={logout}
        className="flex items-center gap-3 px-3 py-2 rounded-md text-sm text-slate-400 hover:bg-slate-900"
      >
        <LogOut size={16} /> Sign out
      </button>
    </aside>
  );
}
