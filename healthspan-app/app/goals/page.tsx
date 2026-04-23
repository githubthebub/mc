"use client";

import { useEffect, useState } from "react";
import { Goal, DailyEntry } from "@/lib/types";
import { getGoals, saveGoal, deleteGoal, getEntries } from "@/lib/storage";
import { generateId } from "@/lib/utils";
import GoalProgressBar from "@/components/GoalProgressBar";

type GoalCategory = Goal["category"];

const categoryOptions: { value: GoalCategory; label: string; icon: string; defaultTarget: number; unit: string; direction: "higher" | "lower" }[] = [
  { value: "sleep", label: "Sleep hours", icon: "😴", defaultTarget: 8, unit: "hrs", direction: "higher" },
  { value: "exercise", label: "Exercise minutes", icon: "🏃", defaultTarget: 45, unit: "min", direction: "higher" },
  { value: "nutrition", label: "Nutrition quality", icon: "🥗", defaultTarget: 8, unit: "/10", direction: "higher" },
  { value: "stress", label: "Stress level (max)", icon: "😤", defaultTarget: 4, unit: "/10", direction: "lower" },
  { value: "mood", label: "Mood", icon: "😊", defaultTarget: 8, unit: "/10", direction: "higher" },
  { value: "energy", label: "Energy", icon: "⚡", defaultTarget: 8, unit: "/10", direction: "higher" },
];

export default function Goals() {
  const [goals, setGoals] = useState<Goal[]>([]);
  const [entries, setEntries] = useState<DailyEntry[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [category, setCategory] = useState<GoalCategory>("sleep");
  const [target, setTarget] = useState(8);

  useEffect(() => {
    setGoals(getGoals());
    setEntries(getEntries());
  }, []);

  function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    const opt = categoryOptions.find((o) => o.value === category)!;
    const goal: Goal = {
      id: generateId(),
      category,
      label: opt.label,
      targetValue: target,
      unit: opt.unit,
      direction: opt.direction,
      createdAt: new Date().toISOString(),
    };
    saveGoal(goal);
    setGoals(getGoals());
    setShowForm(false);
  }

  function handleDelete(id: string) {
    deleteGoal(id);
    setGoals(getGoals());
  }

  const opt = categoryOptions.find((o) => o.value === category)!;

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Goals</h1>
          <p className="text-slate-400 text-sm mt-0.5">Track what matters most to you</p>
        </div>
        <button
          onClick={() => setShowForm((s) => !s)}
          className="rounded-xl bg-emerald-500 px-4 py-2 text-sm font-semibold text-white shadow-lg shadow-emerald-500/20 hover:bg-emerald-400 transition-colors"
        >
          {showForm ? "Cancel" : "+ Add Goal"}
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleAdd} className="rounded-2xl border border-emerald-500/20 bg-slate-900 p-5 space-y-4">
          <h2 className="font-semibold text-slate-200">New Goal</h2>

          <div className="space-y-2">
            <label className="text-sm font-medium text-slate-300">Metric</label>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              {categoryOptions.map((o) => (
                <button
                  key={o.value}
                  type="button"
                  onClick={() => {
                    setCategory(o.value);
                    setTarget(o.defaultTarget);
                  }}
                  className={`rounded-xl border px-3 py-2.5 text-sm font-medium text-left transition-colors ${
                    category === o.value
                      ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-300"
                      : "border-slate-700 bg-slate-800 text-slate-300 hover:bg-slate-700"
                  }`}
                >
                  <span className="mr-1.5">{o.icon}</span>
                  {o.label}
                </button>
              ))}
            </div>
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium text-slate-300">
              Target ({opt.direction === "higher" ? "minimum" : "maximum"}): {target} {opt.unit}
            </label>
            <input
              type="range"
              min={opt.direction === "higher" ? 1 : 1}
              max={opt.unit === "min" ? 120 : opt.unit === "hrs" ? 12 : 10}
              step={opt.unit === "min" ? 5 : opt.unit === "hrs" ? 0.5 : 1}
              value={target}
              onChange={(e) => setTarget(Number(e.target.value))}
              className="w-full h-2 rounded-full appearance-none cursor-pointer"
              style={{
                background: `linear-gradient(to right, rgb(16 185 129) ${((target - 1) / (opt.unit === "min" ? 119 : opt.unit === "hrs" ? 11 : 9)) * 100}%, rgb(51 65 85) ${((target - 1) / (opt.unit === "min" ? 119 : opt.unit === "hrs" ? 11 : 9)) * 100}%)`,
              }}
            />
          </div>

          <button
            type="submit"
            className="w-full rounded-xl bg-emerald-500 py-3 font-semibold text-white hover:bg-emerald-400 transition-colors"
          >
            Add Goal
          </button>
        </form>
      )}

      {goals.length === 0 && !showForm && (
        <div className="rounded-2xl border border-dashed border-slate-700 p-10 text-center">
          <div className="text-4xl mb-3">🎯</div>
          <h2 className="text-lg font-semibold text-slate-200 mb-2">No goals yet</h2>
          <p className="text-slate-400 text-sm max-w-xs mx-auto">
            Set specific health targets to track your progress against what matters most to you.
          </p>
        </div>
      )}

      {goals.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold text-slate-200 text-sm">Your Goals</h2>
            {entries.length === 0 && (
              <p className="text-xs text-slate-500">Log check-ins to see progress</p>
            )}
          </div>
          {goals.map((goal) => (
            <GoalProgressBar
              key={goal.id}
              goal={goal}
              entries={entries}
              onDelete={() => handleDelete(goal.id)}
            />
          ))}
        </div>
      )}

      {/* Guidance section */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
        <h2 className="font-semibold text-slate-200 mb-3 text-sm">Healthspan Essentials</h2>
        <div className="space-y-3">
          {[
            { icon: "😴", title: "Sleep 7-9 hours", desc: "Consistent quality sleep is the #1 longevity lever." },
            { icon: "🏃", title: "150+ min/week activity", desc: "Even brisk walking dramatically reduces all-cause mortality." },
            { icon: "🥗", title: "Whole food nutrition", desc: "Minimize ultra-processed foods and added sugars." },
            { icon: "😤", title: "Manage chronic stress", desc: "Chronic stress accelerates biological aging." },
            { icon: "👥", title: "Social connection", desc: "Loneliness is as harmful as smoking 15 cigarettes/day." },
          ].map(({ icon, title, desc }) => (
            <div key={title} className="flex gap-3">
              <span className="text-lg shrink-0 mt-0.5">{icon}</span>
              <div>
                <p className="text-sm font-medium text-slate-200">{title}</p>
                <p className="text-xs text-slate-400 mt-0.5">{desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
