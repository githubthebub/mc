"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import {
  getEntries,
  getLatestFeedback,
  getGoals,
  saveFeedback,
  getProfile,
  wellnessScore,
} from "@/lib/storage";
import { DailyEntry, FeedbackEntry, Goal, UserProfile } from "@/lib/types";
import { todayISO, formatDate, cn } from "@/lib/utils";
import FeedbackCard from "@/components/FeedbackCard";
import StatCard from "@/components/StatCard";
import WellnessChart from "@/components/WellnessChart";

export default function Dashboard() {
  const [entries, setEntries] = useState<DailyEntry[]>([]);
  const [feedback, setFeedback] = useState<FeedbackEntry | null>(null);
  const [goals, setGoals] = useState<Goal[]>([]);
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [feedbackLoading, setFeedbackLoading] = useState(false);
  const [feedbackError, setFeedbackError] = useState<string | null>(null);

  useEffect(() => {
    setEntries(getEntries());
    setFeedback(getLatestFeedback() || null);
    setGoals(getGoals());
    setProfile(getProfile());
  }, []);

  const generateFeedback = useCallback(async () => {
    if (!entries.length) return;
    setFeedbackLoading(true);
    setFeedbackError(null);
    try {
      const res = await fetch("/api/feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ entries, goals }),
      });
      if (!res.ok) throw new Error("Failed");
      const fb: FeedbackEntry = await res.json();
      saveFeedback(fb);
      setFeedback(fb);
    } catch {
      setFeedbackError("Could not reach the AI coach. Check your ANTHROPIC_API_KEY environment variable.");
    } finally {
      setFeedbackLoading(false);
    }
  }, [entries, goals]);

  const today = todayISO();
  const hasTodayEntry = entries.some((e) => e.date === today);
  const latestEntry = entries[0];
  const recent = entries.slice(0, 7);
  const todayScore = latestEntry?.date === today ? wellnessScore(latestEntry) : null;
  const weekScore = recent.length
    ? Math.round(recent.reduce((s, e) => s + wellnessScore(e), 0) / recent.length)
    : null;
  const streak = profile?.streakDays ?? 0;
  const totalDays = entries.length;

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">
            Hey, {profile?.name || "Friend"} 👋
          </h1>
          <p className="text-slate-400 text-sm mt-0.5">
            {totalDays === 0
              ? "Start your healthspan journey today"
              : `${totalDays} day${totalDays !== 1 ? "s" : ""} tracked · ${streak} day streak`}
          </p>
        </div>
        {!hasTodayEntry && totalDays > 0 && (
          <Link
            href="/checkin"
            className="shrink-0 rounded-xl bg-emerald-500 px-4 py-2 text-sm font-semibold text-white shadow-lg shadow-emerald-500/20 hover:bg-emerald-400 transition-colors"
          >
            Check In →
          </Link>
        )}
      </div>

      {totalDays === 0 && (
        <div className="rounded-2xl border border-dashed border-slate-700 p-10 text-center">
          <div className="text-5xl mb-4">🌱</div>
          <h2 className="text-xl font-semibold text-slate-200 mb-2">Welcome to HealthSpan</h2>
          <p className="text-slate-400 text-sm mb-6 max-w-sm mx-auto">
            Track your daily health metrics and get AI-powered insights that evolve with you over time.
          </p>
          <Link
            href="/checkin"
            className="inline-flex items-center gap-2 rounded-xl bg-emerald-500 px-6 py-3 font-semibold text-white hover:bg-emerald-400 transition-colors"
          >
            Start Your First Check-In
          </Link>
        </div>
      )}

      {totalDays > 0 && !hasTodayEntry && (
        <div className="rounded-2xl border border-amber-500/30 bg-amber-500/5 p-4 flex items-center gap-3">
          <span className="text-2xl">⏰</span>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-amber-300">No check-in yet today</p>
            <p className="text-xs text-slate-400">Log your metrics to keep your streak alive</p>
          </div>
          <Link href="/checkin" className="shrink-0 text-sm text-amber-400 hover:text-amber-300 font-medium">
            Check In →
          </Link>
        </div>
      )}

      {totalDays > 0 && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <StatCard icon="⚡" label="Wellness Score" value={todayScore ?? weekScore ?? "—"} sub={todayScore ? "Today" : "7-day avg"} color="emerald" />
          <StatCard icon="🔥" label="Day Streak" value={streak} sub="consecutive days" color="amber" />
          <StatCard icon="📅" label="Days Tracked" value={totalDays} sub="total check-ins" color="sky" />
          <StatCard icon="🎯" label="Active Goals" value={goals.length} sub="goals set" color="violet" />
        </div>
      )}

      {latestEntry?.date === today && (
        <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
          <h2 className="font-semibold text-slate-200 mb-4 text-sm uppercase tracking-wider">
            Today · {formatDate(today)}
          </h2>
          <div className="grid grid-cols-3 gap-4 sm:grid-cols-6">
            {[
              { icon: "😴", label: "Sleep", value: `${latestEntry.sleep.hours}h` },
              { icon: "🏃", label: "Exercise", value: `${latestEntry.exercise.minutes}m` },
              { icon: "🥗", label: "Nutrition", value: `${latestEntry.nutrition.quality}/10` },
              { icon: "😤", label: "Stress", value: `${latestEntry.stress}/10` },
              { icon: "😊", label: "Mood", value: `${latestEntry.mood}/10` },
              { icon: "⚡", label: "Energy", value: `${latestEntry.energy}/10` },
            ].map(({ icon, label, value }) => (
              <div key={label} className="text-center">
                <div className="text-2xl mb-1">{icon}</div>
                <div className="text-sm font-semibold text-slate-200">{value}</div>
                <div className="text-xs text-slate-500">{label}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {entries.length >= 3 && (
        <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
          <h2 className="font-semibold text-slate-200 mb-4 text-sm">Wellness Trend</h2>
          <WellnessChart entries={entries.slice(0, 30)} metrics={["score"]} />
        </div>
      )}

      {totalDays > 0 && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold text-slate-200 text-sm">AI Health Coach</h2>
            <button
              onClick={generateFeedback}
              disabled={feedbackLoading}
              className={cn(
                "rounded-lg px-3 py-1.5 text-xs font-medium transition-colors",
                feedbackLoading
                  ? "bg-slate-800 text-slate-500 cursor-not-allowed"
                  : "bg-emerald-500/15 text-emerald-400 hover:bg-emerald-500/25"
              )}
            >
              {feedbackLoading ? "Analyzing..." : feedback ? "Refresh Insights" : "Get Insights"}
            </button>
          </div>

          {feedbackError && (
            <div className="rounded-xl border border-rose-500/30 bg-rose-500/5 p-3 text-sm text-rose-400">
              {feedbackError}
            </div>
          )}
          {feedbackLoading && <FeedbackCard feedback={{} as FeedbackEntry} isLoading />}
          {!feedbackLoading && feedback && <FeedbackCard feedback={feedback} />}
          {!feedbackLoading && !feedback && !feedbackError && (
            <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-6 text-center text-slate-500 text-sm">
              Click "Get Insights" to receive personalized AI coaching based on your data.
            </div>
          )}
        </div>
      )}
    </div>
  );
}
