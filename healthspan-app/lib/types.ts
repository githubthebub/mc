export interface DailyEntry {
  id: string;
  date: string;
  sleep: {
    hours: number;
    quality: number; // 1-10
  };
  exercise: {
    minutes: number;
    intensity: number; // 1-5
  };
  nutrition: {
    quality: number; // 1-10
    meals: number;
    water: number; // glasses
  };
  stress: number; // 1-10 (lower is better)
  mood: number; // 1-10
  energy: number; // 1-10
  social: number; // 1-5
  notes?: string;
}

export interface Goal {
  id: string;
  category: "sleep" | "exercise" | "nutrition" | "stress" | "mood" | "energy";
  label: string;
  targetValue: number;
  unit: string;
  direction: "higher" | "lower";
  createdAt: string;
}

export interface FeedbackEntry {
  id: string;
  date: string;
  feedback: string;
  highlights: string[];
  actionItems: string[];
  overallScore: number;
  trend: "improving" | "stable" | "declining";
}

export interface UserProfile {
  name: string;
  joinedAt: string;
  streakDays: number;
  lastCheckin?: string;
}
