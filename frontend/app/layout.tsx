import "./globals.css";
import type { Metadata } from "next";
import RUOBanner from "@/components/RUOBanner";
import ProtectedRoute from "@/components/ProtectedRoute";

export const metadata: Metadata = {
  title: "GenomicsOps",
  description: "Variant interpretation workbench",
  icons: {
    icon: [
      { url: "/favicon-32.png", sizes: "32x32", type: "image/png" },
      { url: "/icon-192.png", sizes: "192x192", type: "image/png" },
    ],
    apple: { url: "/icon-192.png", sizes: "192x192" },
    shortcut: "/favicon.ico",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-slate-950 text-slate-100 flex flex-col min-h-screen">
        <RUOBanner />
        <ProtectedRoute>
          <div className="flex-1">{children}</div>
        </ProtectedRoute>
      </body>
    </html>
  );
}
