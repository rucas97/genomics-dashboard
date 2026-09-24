import "./globals.css";
import type { Metadata } from "next";
import RUOBanner from "@/components/RUOBanner";

export const metadata: Metadata = { title: "GenomicsOps" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-slate-950 text-slate-100 flex flex-col min-h-screen">
        <RUOBanner />
        <div className="flex-1">{children}</div>
      </body>
    </html>
  );
}
