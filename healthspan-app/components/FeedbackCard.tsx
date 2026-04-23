"use client";

import { FeedbackEntry } from "@/lib/types";
import { trendIcon, trendColor, cn } from "@/lib/utils";

interface Props {
  feedback: FeedbackEntry;
  isLoading?: boolean;
}

export default function FeedbackCard({ feedback, isLoading }: Props) {
  if (isLoading) {
    return (
      <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="h-8 w-8 rounded-full bg-emerald-500/20 animate-pulse" />
          <div className="h-4 w-32 rounded bg-slate-800 animate-pulse" />
        </div>
        <div className="space-y-2">
          <div className="h-4 w-full rounded bg-slate-800 animate-pulse" />
          <div className="h-4 w-5/6 rounded bg-slate-800 animate-pulse" />
          <div className="h-4 w-4/6 rounded bg-slate-800 animate-pulse" />
        </div>
      </div>
    );
  }

  const trendClass = trendColor(feedback.trend);

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6 space-y-4">
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-emerald-500/15 text-emerald-400 text-lg">
            🧠
          </div>
          <div>
            <h3 className="font-semibold text-slate-100">AI Health Coach</h3>
            <p className={cn("text-xs font-medium", trendClass)}>
              {trendIcon(feedback.trend)} {feedback.trend.charAt(0).toUpperCase() + feedback.trend.slice(1)} trend
            </p>
          </div>
        </div>
        <div className="flex flex-col items-end">
          <span className="text-2xl font-bold text-emerald-400">{feedback.overallScore}</span>
          <span className="text-xs text-slate-500">wellness score</span>
        </div>
      </div>

      <p className="text-slate-300 leading-relaxed text-sm">{feedback.feedback}</p>

      {feedback.highlights.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-500">Strengths</h4>
          <ul className="space-y-1.5">
            {feedback.highlights.map((h, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-slate-300">
                <span className="mt-0.5 text-emerald-400">✓</span>
                <span>{h}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {feedback.actionItems.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-500">Focus Areas</h4>
          <ul className="space-y-1.5">
            {feedback.actionItems.map((a, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-slate-300">
                <span className="mt-0.5 text-amber-400">→</span>
                <span>{a}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
