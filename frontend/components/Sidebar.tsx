"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import {
  LayoutDashboard, FlaskConical, Dna, Users, PlayCircle,
  FileText, Shield, LogOut, Settings as SettingsIcon,
  Wifi, WifiOff, Key, HelpCircle,
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
  const [license, setLicense] = useState<any>(null);
  const [support, setSupport] = useState<any>(null);

  useEffect(() => {
    fetch(`${API_URL}/license/status`)
      .then((r) => r.json())
      .then(setLicense)
      .catch(() => setLicense(null));
    fetch(`${API_URL}/support`)
      .then((r) => r.json())
      .then(setSupport)
      .catch(() => setSupport(null));
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

  const tierColor = !license?.valid
    ? "text-red-400"
    : license.tier === "enterprise"
    ? "text-purple-400"
    : license.tier === "trial"
    ? "text-amber-400"
    : "text-emerald-400";

  const networkIcon = !license?.valid ? <WifiOff size={10} /> : <Wifi size={10} />;
  const networkLabel = !license?.valid
    ? "Offline · No license"
    : license.network_policy === "full"
    ? "Online · Full network"
    : "Online · Annotation only";

  return (
    <aside className="w-60 border-r border-slate-800 flex flex-col">
      <div className="p-4 border-b border-slate-800">
        <Link href="/dashboard" className="flex items-center justify-center mb-2">
          <img
            src="/logo-sidebar.png"
            alt="GenomicsOps"
            className="w-full max-w-[160px] h-auto mx-auto"
          />
        </Link>

        <div className="text-[10px] text-amber-500 uppercase tracking-wider text-center">
          Research Use Only
        </div>

        {license && (
          <Link
            href="/license"
            className={`flex items-center justify-center gap-1.5 mt-3 text-[10px] uppercase tracking-wider hover:underline ${tierColor}`}
          >
            {networkIcon}
            {networkLabel}
          </Link>
        )}

        {license?.valid && license.days_remaining !== null && license.days_remaining < 14 && (
          <Link
            href="/license"
            className="flex items-center justify-center gap-1.5 mt-1 text-[10px] text-amber-400 hover:underline"
          >
            <Key size={10} />
            {license.days_remaining <= 0
              ? "Grace period"
              : `${license.days_remaining} days left`}
          </Link>
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

      <div className="border-t border-slate-800 p-3 space-y-1">
        <Link
          href="/faq"
          className="flex items-center gap-3 px-3 py-2 rounded-md text-sm text-slate-400 hover:bg-slate-900"
        >
          <HelpCircle size={16} /> FAQ
        </Link>
        {support && (
          <a
            href={support.url || `mailto:${support.email}?subject=GenomicsOps Support`}
            target={support.url ? "_blank" : undefined}
            rel="noopener noreferrer"
            className="flex items-center gap-3 px-3 py-2 rounded-md text-sm text-slate-400 hover:bg-slate-900"
          >
            <HelpCircle size={16} /> Support
          </a>
        )}
        <Link
          href="/license"
          className="flex items-center gap-3 px-3 py-2 rounded-md text-sm text-slate-400 hover:bg-slate-900"
        >
          <Key size={16} /> License
        </Link>
        <button
          onClick={logout}
          className="w-full flex items-center gap-3 px-3 py-2 rounded-md text-sm text-slate-400 hover:bg-slate-900"
        >
          <LogOut size={16} /> Sign out
        </button>
      </div>
    </aside>
  );
}
