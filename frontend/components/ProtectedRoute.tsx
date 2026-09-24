"use client";
import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { isLocal, getLocalToken } from "@/lib/mode";

/**
 * Client-side auth gate.
 * In local mode: checks localStorage token.
 * In cloud mode: checks Supabase session.
 *
 * Replaces middleware.ts for static export compatibility.
 */
export default function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const path = usePathname();
  const [status, setStatus] = useState<"checking" | "authed" | "unauth">("checking");

  useEffect(() => {
    async function check() {
      const isPublic = path === "/" || path.startsWith("/login") || path.startsWith("/landing");

      if (isLocal) {
        const token = getLocalToken();
        if (!token && !isPublic) {
          router.replace("/login");
          setStatus("unauth");
          return;
        }
        if (token && path.startsWith("/login")) {
          router.replace("/dashboard");
          setStatus("authed");
          return;
        }
        setStatus("authed");
        return;
      }

      // Cloud mode
      const { supabase } = await import("@/lib/supabase");
      const { data } = await supabase.auth.getSession();
      const session = data?.session;

      if (!session && !isPublic) {
        router.replace("/login");
        setStatus("unauth");
        return;
      }
      if (session && path.startsWith("/login")) {
        router.replace("/dashboard");
        setStatus("authed");
        return;
      }
      setStatus("authed");
    }

    check();
  }, [path, router]);

  // While checking, render children anyway to avoid a flash of "Loading"
  // The redirect happens on the next tick if unauthenticated.
  return <>{children}</>;
}
