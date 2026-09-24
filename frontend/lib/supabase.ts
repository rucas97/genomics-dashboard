"use client";
import { createBrowserClient } from "@supabase/ssr";

// In local mode we don't need Supabase at all. But we still need the
// client object because some components import it. We return a stub that
// throws clearly if anyone actually calls it in local mode.
import { isLocal } from "./mode";

function makeClient() {
  if (isLocal) {
    // Return a stub that throws if used. The app should never call it in local mode.
    return {
      auth: {
        getSession: async () => ({ data: { session: null } }),
        signOut: async () => {},
        signInWithOtp: async () => { throw new Error("Supabase auth not available in local mode"); },
        signInAnonymously: async () => { throw new Error("Supabase auth not available in local mode"); },
        getUser: async () => ({ data: { user: null } }),
      },
      storage: {
        from: () => ({ upload: async () => { throw new Error("Not available in local mode"); } }),
      },
    } as any;
  }
  return createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
  );
}

export const supabase = makeClient();
