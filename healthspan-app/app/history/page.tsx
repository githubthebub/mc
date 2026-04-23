"use client";

import { useEffect, useState } from "react";
import { DailyEntry } from "@/lib/types";
import { getEntries, wellnessScore } from "@/lib/storage";
import { formatDate, avg, trend, trendColor, trendIcon } from "@/lib/utils";
import WellnessChart from "@/components/WellnessChart";

type MetricKey = "score" | "sleep" | "mood" | "energy" | "stress" | "exercise";

const metricOptions: { key: MetricKey; label: string; icon: string }[] = [
  { key: "score", label: "Wellness Score", icon: "⚡" },
  { key: "sleep", label: "Sleep (hrs)", icon: "😴" },
  { key: "mood", label: "Mood", icon: "😊" },
  { key: "energy", label: "Energy", icon: "🔋" },
  { key: "stress", label: "Stress", icon: "😤" },
  { key: "exercise", label: "Exercise (min)", icon: "🏃" },
];

function metricValue(entry: DailyEntry, key: MetricKey): number {
  switch (key) {
    case "score": return wellnessScore(entry);
    case "sleep": return entry.sleep.hours;
    case "mood": return entry.mood;
    case "energy": return entry.energy;
    case "stress": return entry.stress;
    case "exercise": return entry.exercise.minutes;
  }
}

function TrendStat({ label, icon, recent, older }: { label: string; icon: string; recent: number; older: number }) {
  const t = trend([recent], [older]);
  const inv = label === "Stress";
  const adjustedTrend = inv
    ? (recent < older * 0.95 ? "improving" : recent > older * 1.05 ? "declining" : "stable")
    : t;

  return (
    <div className="flex items-center justify-between py-3 border-b border-slate-800 last:border-0">
      <div className="flex items-center gap-2 text-sm text-slate-300">
        <span>{icon}</span>
        <span>{label}</span>
      </div>
      <div className="flex items-center gap-3">
        <span className="text-sm text-slate-400">{older.toFixed(1)} → <span className="text-slate-100 font-medium">{recent.toFixed(1)}</span></span>
        <span className={`text-xs font-medium ${trendColor(adjustedTrend)}`}>
          {trendIcon(adjustedTrend)}
        </span>
      </div>
    </div>
  );
}

export default function History() {
  const [entries, setEntries] = useState<DailyEntry[]>([]);
  const [selectedMetrics, setSelectedMetrics] = useState<MetricKey[]>(["score"]);
  const [range, setRange] = useState<30 | 60 | 90>(30);

  useEffect(() => {
    setEntries(getEntries());
  }, []);

  const ranged = entries.slice(0, range);
  const recent = entries.slice(0, 7);
  const older = entries.slice(7, 14);

  const recentAvgs = {
    score: avg(recent.map((e) => wellnessScore(e))),
    sleep: avg(recent.map((e) => e.sleep.hours)),
    mood: avg(recent.map((e) => e.mood)),
    energy: avg(recent.map((e) => e.energy)),
    stress: avg(recent.map((e) => e.stress)),
    exercise: avg(recent.map((e) => e.exercise.minutes)),
  };
  const olderAvgs = {
    score: avg(older.map((e) => wellnessScore(e))),
    sleep: avg(older.map((e) => e.sleep.hours)),
    mood: avg(older.map((e) => e.mood)),
    energy: avg(older.map((e) => e.energy)),
    stress: avg(older.map((e) => e.stress)),
    exercise: avg(older.map((e) => e.exercise.minutes)),
  };

  function toggleMetric(key: MetricKey) {
    setSelectedMetrics((prev) =>
      prev.includes(key)
        ? prev.length > 1 ? prev.filter((k) => k !== key) : prev
        : [...prev, key]
    );
  }

  if (entries.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-24 gap-4 text-center">
        <div className="text-5xl">📈</div>
        <h2 className="text-xl font-semibold text-slate-200">No data yet</h2>
        <p className="text-slate-400 text-sm max-w-xs">
          Start logging daily check-ins to see your trends and patterns here.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-100">Health Trends</h1>
        <p className="text-slate-400 text-sm mt-0.5">{entries.length} check-ins tracked</p>
      </div>

      {/* Week-over-week comparison */}
      {older.length > 0 && (
        <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
          <h2 className="font-semibold text-slate-200 mb-1 text-sm">Week-over-Week</h2>
          <p className="text-xs text-slate-500 mb-4">Last 7 days vs prior 7 days</p>
          <TrendStat label="Wellness Score" icon="⚡" recent={recentAvgs.score} older={olderAvgs.score} />
          <TrendStat label="Sleep" icon="😴" recent={recentAvgs.sleep} older={olderAvgs.sleep} />
          <TrendStat label="Mood" icon="😊" recent={recentAvgs.mood} older={olderAvgs.mood} />
          <TrendStat label="Energy" icon="🔋" recent={recentAvgs.energy} older={olderAvgs.energy} />
          <TrendStat label="Stress" icon="😤" recent={recentAvgs.stress} older={olderAvgs.stress} />
          <TrendStat label="Exercise (min)" icon="🏃" recent={recentAvgs.exercise} older={olderAvgs.exercise} />
        </div>
      )}

      {/* Chart */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-4">
          <h2 className="font-semibold text-slate-200 text-sm">Trend Chart</h2>
          <div className="flex gap-2">
            {([30, 60, 90] as const).map((r) => (
              <button
                key={r}
                onClick={() => setRange(r)}
                className={`rounded-lg px-2.5 py-1 text-xs font-medium transition-colors ${
                  range === r
                    ? "bg-emerald-500/15 text-emerald-400"
                    : "text-slate-400 hover:bg-slate-800"
                }`}
              >
                {r}d
              </button>
            ))}
          </div>
        </div>

        <div className="flex flex-wrap gap-2 mb-4">
          {metricOptions.map(({ key, label, icon }) => (
            <button
              key={key}
              onClick={() => toggleMetric(key)}
              className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
                selectedMetrics.includes(key)
                  ? "bg-emerald-500/15 text-emerald-400 ring-1 ring-emerald-500/30"
                  : "bg-slate-800 text-slate-400 hover:bg-slate-700"
              }`}
            >
              {icon} {label}
            </button>
          ))}
        </div>

        {ranged.length >= 2 ? (
          <WellnessChart entries={ranged} metrics={selectedMetrics} />
        ) : (
          <div className="py-12 text-center text-slate-500 text-sm">
            Need at least 2 check-ins to show a chart
          </div>
        )}
      </div>

      {/* Recent entries log */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
        <h2 className="font-semibold text-slate-200 mb-4 text-sm">Check-In Log</h2>
        <div className="space-y-2">
          {entries.slice(0, 14).map((e) => {
            const score = wellnessScore(e);
            return (
              <div
                key={e.id}
                className="flex items-center justify-between rounded-xl bg-slate-800/50 px-4 py-3"
              >
                <div className="text-sm text-slate-300">{formatDate(e.date)}</div>
                <div className="flex items-center gap-4 text-xs text-slate-400">
                  <span>😴 {e.sleep.hours}h</span>
                  <span>🏃 {e.exercise.minutes}m</span>
                  <span>😊 {e.mood}/10</span>
                  <span
                    className={`font-bold ${
                      score >= 75 ? "text-emerald-400" : score >= 50 ? "text-amber-400" : "text-rose-400"
                    }`}
                  >
                    {score}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
