"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { DailyEntry } from "@/lib/types";
import { saveEntry, getEntryByDate, updateStreak } from "@/lib/storage";
import { todayISO, generateId, formatDate } from "@/lib/utils";
import MetricSlider from "@/components/MetricSlider";
import { cn } from "@/lib/utils";

const defaultEntry = (): DailyEntry => ({
  id: generateId(),
  date: todayISO(),
  sleep: { hours: 7, quality: 7 },
  exercise: { minutes: 30, intensity: 3 },
  nutrition: { quality: 7, meals: 3, water: 8 },
  stress: 4,
  mood: 7,
  energy: 7,
  social: 3,
  notes: "",
});

export default function CheckIn() {
  const router = useRouter();
  const [entry, setEntry] = useState<DailyEntry>(defaultEntry());
  const [isEditing, setIsEditing] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    const existing = getEntryByDate(todayISO());
    if (existing) {
      setEntry(existing);
      setIsEditing(true);
    }
  }, []);

  function set<K extends keyof DailyEntry>(key: K, value: DailyEntry[K]) {
    setEntry((e) => ({ ...e, [key]: value }));
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    saveEntry(entry);
    if (!isEditing) {
      updateStreak(entry.date);
    }
    setSaved(true);
    setTimeout(() => router.push("/"), 1200);
  }

  if (saved) {
    return (
      <div className="flex flex-col items-center justify-center py-24 gap-4">
        <div className="text-6xl">✅</div>
        <h2 className="text-xl font-semibold text-slate-100">Check-in saved!</h2>
        <p className="text-slate-400 text-sm">Heading to your dashboard...</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-100">
          {isEditing ? "Edit Today's Check-In" : "Daily Check-In"}
        </h1>
        <p className="text-slate-400 text-sm mt-0.5">{formatDate(todayISO())}</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Sleep */}
        <Section title="😴 Sleep">
          <MetricSlider
            label="Hours of sleep"
            value={entry.sleep.hours}
            min={2}
            max={12}
            step={0.5}
            unit="h"
            onChange={(v) => set("sleep", { ...entry.sleep, hours: v })}
            lowLabel="2h"
            highLabel="12h"
          />
          <MetricSlider
            label="Sleep quality"
            value={entry.sleep.quality}
            min={1}
            max={10}
            onChange={(v) => set("sleep", { ...entry.sleep, quality: v })}
            lowLabel="Poor"
            highLabel="Excellent"
            colorScale
          />
        </Section>

        {/* Exercise */}
        <Section title="🏃 Exercise">
          <MetricSlider
            label="Active minutes"
            value={entry.exercise.minutes}
            min={0}
            max={180}
            step={5}
            unit=" min"
            onChange={(v) => set("exercise", { ...entry.exercise, minutes: v })}
            lowLabel="0 min"
            highLabel="3h"
          />
          <MetricSlider
            label="Intensity"
            value={entry.exercise.intensity}
            min={1}
            max={5}
            onChange={(v) => set("exercise", { ...entry.exercise, intensity: v })}
            lowLabel="Light"
            highLabel="Intense"
            colorScale
          />
        </Section>

        {/* Nutrition */}
        <Section title="🥗 Nutrition">
          <MetricSlider
            label="Diet quality"
            value={entry.nutrition.quality}
            min={1}
            max={10}
            onChange={(v) => set("nutrition", { ...entry.nutrition, quality: v })}
            lowLabel="Poor"
            highLabel="Excellent"
            colorScale
          />
          <MetricSlider
            label="Meals eaten"
            value={entry.nutrition.meals}
            min={1}
            max={6}
            onChange={(v) => set("nutrition", { ...entry.nutrition, meals: v })}
            lowLabel="1"
            highLabel="6+"
          />
          <MetricSlider
            label="Water glasses"
            value={entry.nutrition.water}
            min={0}
            max={16}
            unit=" glasses"
            onChange={(v) => set("nutrition", { ...entry.nutrition, water: v })}
            lowLabel="0"
            highLabel="16"
            colorScale
          />
        </Section>

        {/* Mental / Emotional */}
        <Section title="🧠 Mental & Emotional">
          <MetricSlider
            label="Stress level"
            value={entry.stress}
            min={1}
            max={10}
            onChange={(v) => set("stress", v)}
            lowLabel="Calm"
            highLabel="Overwhelmed"
          />
          <MetricSlider
            label="Mood"
            value={entry.mood}
            min={1}
            max={10}
            onChange={(v) => set("mood", v)}
            lowLabel="Low"
            highLabel="Great"
            colorScale
          />
          <MetricSlider
            label="Energy"
            value={entry.energy}
            min={1}
            max={10}
            onChange={(v) => set("energy", v)}
            lowLabel="Exhausted"
            highLabel="Energized"
            colorScale
          />
        </Section>

        {/* Social */}
        <Section title="👥 Social Connection">
          <MetricSlider
            label="Meaningful interactions"
            value={entry.social}
            min={1}
            max={5}
            onChange={(v) => set("social", v)}
            lowLabel="Isolated"
            highLabel="Very connected"
            colorScale
          />
        </Section>

        {/* Notes */}
        <Section title="📝 Notes (optional)">
          <textarea
            value={entry.notes ?? ""}
            onChange={(e) => set("notes", e.target.value)}
            rows={3}
            placeholder="How are you feeling? Anything notable today?"
            className="w-full rounded-xl border border-slate-700 bg-slate-800 px-4 py-3 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/50 resize-none"
          />
        </Section>

        <button
          type="submit"
          className="w-full rounded-xl bg-emerald-500 py-3.5 font-semibold text-white shadow-lg shadow-emerald-500/20 hover:bg-emerald-400 transition-colors"
        >
          {isEditing ? "Update Check-In" : "Save Check-In"}
        </button>
      </form>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5 space-y-5">
      <h2 className="font-semibold text-slate-200">{title}</h2>
      {children}
    </div>
  );
}
