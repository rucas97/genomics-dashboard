"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import Sidebar from "@/components/Sidebar";

const tabs = [
  { href: "/settings", label: "Organization" },
  { href: "/settings/members", label: "Members" },
  { href: "/settings/audit", label: "Audit Log" },
  { href: "/settings/compliance", label: "Compliance" },
];

export default function SettingsLayout({ children }: { children: React.ReactNode }) {
  const path = usePathname();
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1">
        <div className="border-b border-slate-800 px-8 pt-8">
          <h1 className="text-2xl font-bold mb-4">Settings</h1>
          <nav className="flex gap-1">
            {tabs.map((t) => {
              const active = path === t.href;
              return (
                <Link
                  key={t.href}
                  href={t.href}
                  className={`px-4 py-2 text-sm rounded-t-md border-b-2 transition ${
                    active
                      ? "border-emerald-500 text-emerald-400"
                      : "border-transparent text-slate-400 hover:text-slate-200"
                  }`}
                >
                  {t.label}
                </Link>
              );
            })}
          </nav>
        </div>
        <div className="p-8">{children}</div>
      </main>
    </div>
  );
}
