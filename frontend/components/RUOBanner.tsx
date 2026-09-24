"use client";

export default function RUOBanner() {
  return (
    <div className="bg-amber-950 border border-amber-900 text-amber-300 text-xs px-4 py-2 flex items-center gap-2">
      <span className="font-semibold uppercase tracking-wide">Research Use Only</span>
      <span className="text-amber-400">
        Not for clinical diagnosis, treatment, or patient management.
      </span>
    </div>
  );
}
