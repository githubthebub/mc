"use client";

import { Goal, DailyEntry } from "@/lib/types";
import { avg } from "@/lib/utils";
import { cn } from "@/lib/utils";

interface Props {
  goal: Goal;
  entries: DailyEntry[];
  onDelete?: () => void;
}

function currentValue(goal: Goal, entries: DailyEntry[]): number {
  if (!entries.length) return 0;
  const recent = entries.slice(0, 7);
  switch (goal.category) {
    case "sleep": return avg(recent.map((e) => e.sleep.hours));
    case "exercise": return avg(recent.map((e) => e.exercise.minutes));
    case "nutrition": return avg(recent.map((e) => e.nutrition.quality));
    case "stress": return avg(recent.map((e) => e.stress));
    case "mood": return avg(recent.map((e) => e.mood));
    case "energy": return avg(recent.map((e) => e.energy));
    default: return 0;
  }
}

export default function GoalProgressBar({ goal, entries, onDelete }: Props) {
  const current = currentValue(goal, entries);
  const pct =
    goal.direction === "higher"
      ? Math.min((current / goal.targetValue) * 100, 100)
      : Math.min(((goal.targetValue * 2 - current) / goal.targetValue) * 100, 100);

  const achieved = goal.direction === "higher"
    ? current >= goal.targetValue
    : current <= goal.targetValue;

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900 p-4 space-y-3">
      <div className="flex items-start justify-between gap-2">
        <div>
          <h4 className="font-medium text-slate-100 text-sm">{goal.label}</h4>
          <p className="text-xs text-slate-500 mt-0.5">
            {goal.direction === "higher" ? "Target" : "Max"}: {goal.targetValue} {goal.unit}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {achieved && (
            <span className="text-xs bg-emerald-500/15 text-emerald-400 px-2 py-0.5 rounded-full font-medium">
              Achieved!
            </span>
          )}
          {onDelete && (
            <button
              onClick={onDelete}
              className="text-slate-600 hover:text-rose-400 transition-colors text-xs"
            >
              ✕
            </button>
          )}
        </div>
      </div>
      <div>
        <div className="flex justify-between text-xs text-slate-500 mb-1.5">
          <span>7-day avg: <span className="text-slate-300 font-medium">{current.toFixed(1)} {goal.unit}</span></span>
          <span>{Math.round(pct)}%</span>
        </div>
        <div className="h-2 rounded-full bg-slate-800 overflow-hidden">
          <div
            className={cn(
              "h-full rounded-full transition-all duration-700",
              achieved ? "bg-emerald-500" : pct > 60 ? "bg-amber-500" : "bg-rose-500"
            )}
            style={{ width: `${pct}%` }}
          />
        </div>
      </div>
    </div>
  );
}
