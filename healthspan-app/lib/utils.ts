import { DailyEntry } from "./types";
import { clsx, type ClassValue } from "clsx";

export function cn(...inputs: ClassValue[]) {
  return clsx(inputs);
}

export function todayISO(): string {
  return new Date().toISOString().split("T")[0];
}

export function formatDate(isoDate: string): string {
  return new Date(isoDate + "T00:00:00").toLocaleDateString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
  });
}

export function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

export function avg(nums: number[]): number {
  if (!nums.length) return 0;
  return nums.reduce((a, b) => a + b, 0) / nums.length;
}

export function trend(recent: number[], older: number[]): "improving" | "stable" | "declining" {
  const r = avg(recent);
  const o = avg(older);
  if (!o) return "stable";
  const delta = (r - o) / o;
  if (delta > 0.05) return "improving";
  if (delta < -0.05) return "declining";
  return "stable";
}

export function scoreBadgeColor(score: number): string {
  if (score >= 75) return "text-emerald-400";
  if (score >= 50) return "text-amber-400";
  return "text-rose-400";
}

export function trendIcon(t: string): string {
  if (t === "improving") return "↑";
  if (t === "declining") return "↓";
  return "→";
}

export function trendColor(t: string): string {
  if (t === "improving") return "text-emerald-400";
  if (t === "declining") return "text-rose-400";
  return "text-slate-400";
}

export function entryAvgs(entries: DailyEntry[]) {
  if (!entries.length) return null;
  return {
    sleepHours: avg(entries.map((e) => e.sleep.hours)),
    sleepQuality: avg(entries.map((e) => e.sleep.quality)),
    exerciseMinutes: avg(entries.map((e) => e.exercise.minutes)),
    nutritionQuality: avg(entries.map((e) => e.nutrition.quality)),
    water: avg(entries.map((e) => e.nutrition.water)),
    stress: avg(entries.map((e) => e.stress)),
    mood: avg(entries.map((e) => e.mood)),
    energy: avg(entries.map((e) => e.energy)),
    social: avg(entries.map((e) => e.social)),
  };
}
