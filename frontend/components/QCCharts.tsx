"use client";
import {
  PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis,
  Tooltip, ResponsiveContainer, CartesianGrid,
} from "recharts";

type QC = {
  variant_count?: number;
  snp_count?: number;
  indel_count?: number;
  mean_coverage?: number;
};

const COLORS = ["#10b981", "#f59e0b", "#3b82f6", "#ef4444"];

export default function QCCharts({ qc }: { qc: QC }) {
  const variantData = [
    { name: "SNPs", value: qc.snp_count ?? 0 },
    { name: "Indels", value: qc.indel_count ?? 0 },
  ].filter((d) => d.value > 0);

  const qualityData = [
    { name: "Mean Quality", value: Number(qc.mean_coverage ?? 0) },
  ];

  const total = qc.variant_count ?? 0;

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      {/* Total variants */}
      <div className="bg-slate-900 rounded-lg border border-slate-800 p-6">
        <div className="text-slate-400 text-sm mb-2">Total Variants</div>
        <div className="text-5xl font-bold text-emerald-400">{total}</div>
        <div className="text-slate-500 text-xs mt-2">
          {qc.snp_count ?? 0} SNPs · {qc.indel_count ?? 0} Indels
        </div>
      </div>

      {/* SNP vs Indel pie */}
      <div className="bg-slate-900 rounded-lg border border-slate-800 p-6">
        <div className="text-slate-400 text-sm mb-3">SNP / Indel Split</div>
        {variantData.length > 0 ? (
          <ResponsiveContainer width="100%" height={160}>
            <PieChart>
              <Pie
                data={variantData}
                dataKey="value"
                nameKey="name"
                cx="50%"
                cy="50%"
                innerRadius={40}
                outerRadius={65}
                paddingAngle={3}
              >
                {variantData.map((_, i) => (
                  <Cell key={i} fill={COLORS[i % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  background: "#0f172a",
                  border: "1px solid #1e293b",
                  borderRadius: 6,
                  fontSize: 12,
                }}
              />
            </PieChart>
          </ResponsiveContainer>
        ) : (
          <div className="text-slate-500 text-sm">No variants yet</div>
        )}
      </div>

      {/* Mean quality bar */}
      <div className="bg-slate-900 rounded-lg border border-slate-800 p-6">
        <div className="text-slate-400 text-sm mb-3">Mean Quality Score</div>
        {qualityData[0].value > 0 ? (
          <ResponsiveContainer width="100%" height={160}>
            <BarChart data={qualityData}>
              <CartesianGrid stroke="#1e293b" vertical={false} />
              <XAxis dataKey="name" stroke="#64748b" fontSize={11} />
              <YAxis stroke="#64748b" fontSize={11} />
              <Tooltip
                contentStyle={{
                  background: "#0f172a",
                  border: "1px solid #1e293b",
                  borderRadius: 6,
                  fontSize: 12,
                }}
              />
              <Bar dataKey="value" fill="#10b981" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <div className="text-slate-500 text-sm">No quality data</div>
        )}
      </div>
    </div>
  );
}
