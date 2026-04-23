import { DailyEntry, FeedbackEntry, Goal, UserProfile } from "./types";

const KEYS = {
  entries: "hs_entries",
  feedback: "hs_feedback",
  goals: "hs_goals",
  profile: "hs_profile",
} as const;

function load<T>(key: string, fallback: T): T {
  if (typeof window === "undefined") return fallback;
  try {
    const raw = localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
}

function save<T>(key: string, value: T): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(key, JSON.stringify(value));
}

// Daily entries
export function getEntries(): DailyEntry[] {
  return load<DailyEntry[]>(KEYS.entries, []).sort(
    (a, b) => new Date(b.date).getTime() - new Date(a.date).getTime()
  );
}

export function getEntryByDate(date: string): DailyEntry | undefined {
  return getEntries().find((e) => e.date === date);
}

export function saveEntry(entry: DailyEntry): void {
  const entries = load<DailyEntry[]>(KEYS.entries, []);
  const idx = entries.findIndex((e) => e.id === entry.id);
  if (idx >= 0) {
    entries[idx] = entry;
  } else {
    entries.push(entry);
  }
  save(KEYS.entries, entries);
}

export function getRecentEntries(days = 30): DailyEntry[] {
  const cutoff = Date.now() - days * 86400000;
  return getEntries().filter((e) => new Date(e.date).getTime() >= cutoff);
}

// Feedback
export function getFeedback(): FeedbackEntry[] {
  return load<FeedbackEntry[]>(KEYS.feedback, []).sort(
    (a, b) => new Date(b.date).getTime() - new Date(a.date).getTime()
  );
}

export function saveFeedback(entry: FeedbackEntry): void {
  const feedback = load<FeedbackEntry[]>(KEYS.feedback, []);
  feedback.push(entry);
  // Keep last 90 days of feedback
  const cutoff = Date.now() - 90 * 86400000;
  save(
    KEYS.feedback,
    feedback.filter((f) => new Date(f.date).getTime() >= cutoff)
  );
}

export function getLatestFeedback(): FeedbackEntry | undefined {
  return getFeedback()[0];
}

// Goals
export function getGoals(): Goal[] {
  return load<Goal[]>(KEYS.goals, []);
}

export function saveGoal(goal: Goal): void {
  const goals = load<Goal[]>(KEYS.goals, []);
  const idx = goals.findIndex((g) => g.id === goal.id);
  if (idx >= 0) {
    goals[idx] = goal;
  } else {
    goals.push(goal);
  }
  save(KEYS.goals, goals);
}

export function deleteGoal(id: string): void {
  save(
    KEYS.goals,
    load<Goal[]>(KEYS.goals, []).filter((g) => g.id !== id)
  );
}

// Profile
export function getProfile(): UserProfile {
  return load<UserProfile>(KEYS.profile, {
    name: "Friend",
    joinedAt: new Date().toISOString(),
    streakDays: 0,
  });
}

export function saveProfile(profile: UserProfile): void {
  save(KEYS.profile, profile);
}

export function updateStreak(todayDate: string): number {
  const profile = getProfile();
  const entries = getEntries();
  if (entries.length === 0) {
    const updated = { ...profile, streakDays: 1, lastCheckin: todayDate };
    saveProfile(updated);
    return 1;
  }
  const yesterday = new Date(todayDate);
  yesterday.setDate(yesterday.getDate() - 1);
  const yStr = yesterday.toISOString().split("T")[0];
  const hasYesterday = entries.some((e) => e.date === yStr);
  const streak = hasYesterday ? profile.streakDays + 1 : 1;
  saveProfile({ ...profile, streakDays: streak, lastCheckin: todayDate });
  return streak;
}

// Compute a simple wellness score for an entry (0-100)
export function wellnessScore(entry: DailyEntry): number {
  const sleepScore =
    Math.min(entry.sleep.hours / 8, 1) * 0.5 +
    (entry.sleep.quality / 10) * 0.5;
  const exerciseScore = Math.min(entry.exercise.minutes / 45, 1);
  const nutritionScore =
    (entry.nutrition.quality / 10) * 0.6 +
    Math.min(entry.nutrition.water / 8, 1) * 0.4;
  const stressScore = (10 - entry.stress) / 10;
  const moodScore = entry.mood / 10;
  const energyScore = entry.energy / 10;
  const socialScore = entry.social / 5;

  const weighted =
    sleepScore * 0.2 +
    exerciseScore * 0.2 +
    nutritionScore * 0.15 +
    stressScore * 0.2 +
    moodScore * 0.1 +
    energyScore * 0.1 +
    socialScore * 0.05;

  return Math.round(weighted * 100);
}
