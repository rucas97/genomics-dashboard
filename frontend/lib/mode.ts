/**
 * Mode detection. The frontend decides cloud vs local based on:
 * 1. NEXT_PUBLIC_MODE env var (if set)
 * 2. Presence of Supabase env vars (fallback)
 */
export const MODE =
  process.env.NEXT_PUBLIC_MODE ||
  (process.env.NEXT_PUBLIC_SUPABASE_URL ? "cloud" : "local");

export const isLocal = MODE === "local";
export const isCloud = MODE === "cloud";

const LOCAL_TOKEN_KEY = "genomicsops_local_token";

export function getLocalToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(LOCAL_TOKEN_KEY);
}

export function setLocalToken(token: string) {
  if (typeof window === "undefined") return;
  localStorage.setItem(LOCAL_TOKEN_KEY, token);
}

export function clearLocalToken() {
  if (typeof window === "undefined") return;
  localStorage.removeItem(LOCAL_TOKEN_KEY);
}

export function getLocalUser(): any | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem("genomicsops_local_user");
  if (!raw) return null;
  try { return JSON.parse(raw); } catch { return null; }
}

export function setLocalUser(user: any) {
  if (typeof window === "undefined") return;
  localStorage.setItem("genomicsops_local_user", JSON.stringify(user));
}

export function clearLocalUser() {
  if (typeof window === "undefined") return;
  localStorage.removeItem("genomicsops_local_user");
}
