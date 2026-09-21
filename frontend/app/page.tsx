import Link from "next/link";
export default function Home() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-6">
      <h1 className="text-4xl font-bold text-emerald-400 mb-4">GenomicsOps</h1>
      <p className="text-slate-400 mb-8 max-w-md text-center">
        Self-serve genomics analytics for research labs and biotech.
      </p>
      <Link href="/dashboard" className="bg-emerald-600 hover:bg-emerald-500 px-6 py-3 rounded-lg font-medium">
        Open Dashboard
      </Link>
    </div>
  );
}
