"use client";

import { cn } from "@/lib/utils";

interface Props {
  icon: string;
  label: string;
  value: string | number;
  sub?: string;
  color?: "emerald" | "amber" | "rose" | "sky" | "violet";
  trend?: string;
}

const colorMap = {
  emerald: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
  amber: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  rose: "bg-rose-500/10 text-rose-400 border-rose-500/20",
  sky: "bg-sky-500/10 text-sky-400 border-sky-500/20",
  violet: "bg-violet-500/10 text-violet-400 border-violet-500/20",
};

export default function StatCard({ icon, label, value, sub, color = "emerald", trend }: Props) {
  return (
    <div className={cn("rounded-xl border p-4 space-y-2", colorMap[color])}>
      <div className="flex items-center justify-between">
        <span className="text-xl">{icon}</span>
        {trend && (
          <span className={cn("text-xs font-medium", trend === "↑" ? "text-emerald-400" : trend === "↓" ? "text-rose-400" : "text-slate-400")}>
            {trend}
          </span>
        )}
      </div>
      <div>
        <div className="text-2xl font-bold">{value}</div>
        <div className="text-xs opacity-75">{label}</div>
        {sub && <div className="text-xs opacity-50 mt-0.5">{sub}</div>}
      </div>
    </div>
  );
}
