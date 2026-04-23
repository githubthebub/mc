"use client";

import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from "recharts";
import { DailyEntry } from "@/lib/types";
import { wellnessScore } from "@/lib/storage";
import { formatDate } from "@/lib/utils";

interface Props {
  entries: DailyEntry[];
  metrics?: string[];
}

const metricConfig: Record<string, { color: string; label: string; accessor: (e: DailyEntry) => number }> = {
  score: { color: "#10b981", label: "Wellness Score", accessor: wellnessScore },
  sleep: { color: "#818cf8", label: "Sleep (hrs)", accessor: (e) => e.sleep.hours },
  mood: { color: "#f59e0b", label: "Mood", accessor: (e) => e.mood },
  energy: { color: "#06b6d4", label: "Energy", accessor: (e) => e.energy },
  stress: { color: "#f43f5e", label: "Stress", accessor: (e) => e.stress },
  exercise: { color: "#84cc16", label: "Exercise (min)", accessor: (e) => e.exercise.minutes },
};

const CustomTooltip = ({ active, payload, label }: { active?: boolean; payload?: { name: string; value: number; color: string }[]; label?: string }) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border border-slate-700 bg-slate-900 p-3 shadow-xl text-sm">
      <p className="text-slate-400 mb-2">{label}</p>
      {payload.map((p) => (
        <p key={p.name} style={{ color: p.color }} className="font-medium">
          {p.name}: {typeof p.value === "number" ? p.value.toFixed(1) : p.value}
        </p>
      ))}
    </div>
  );
};

export default function WellnessChart({ entries, metrics = ["score"] }: Props) {
  const sorted = [...entries].sort(
    (a, b) => new Date(a.date).getTime() - new Date(b.date).getTime()
  );

  const data = sorted.map((e) => ({
    date: formatDate(e.date),
    ...Object.fromEntries(
      metrics.map((m) => [metricConfig[m]?.label || m, metricConfig[m]?.accessor(e) ?? 0])
    ),
  }));

  return (
    <ResponsiveContainer width="100%" height={260}>
      <LineChart data={data} margin={{ top: 5, right: 10, left: -20, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="rgb(30 41 59)" />
        <XAxis
          dataKey="date"
          tick={{ fill: "#94a3b8", fontSize: 11 }}
          tickLine={false}
          axisLine={false}
        />
        <YAxis
          tick={{ fill: "#94a3b8", fontSize: 11 }}
          tickLine={false}
          axisLine={false}
        />
        <Tooltip content={<CustomTooltip />} />
        <Legend
          wrapperStyle={{ fontSize: 12, color: "#94a3b8" }}
        />
        {metrics.map((m) => (
          <Line
            key={m}
            type="monotone"
            dataKey={metricConfig[m]?.label || m}
            stroke={metricConfig[m]?.color || "#10b981"}
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4, strokeWidth: 0 }}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}
